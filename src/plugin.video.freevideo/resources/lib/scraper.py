# -*- coding: utf-8 -*-
"""Scraper webu freevideo.cz - nezávislý na Kodi (testovatelný samostatně)."""
import html
import re
from urllib.parse import urljoin, quote_plus

import requests

BASE_URL = 'https://freevideo.cz'
TIMEOUT = 20
USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

# Sekce webu: (název, cesta)
SECTIONS = [
    ('Hetero', '/vase-videa/'),
    ('Lesbičky', '/lesbicky/vase-videa/'),
    ('Gay', '/gay/vase-videa/'),
    ('Transsexuálové', '/transsexualove/vase-videa/'),
    ('Bisexuálové', '/bisexualove/vase-videa/'),
]


class ScraperError(Exception):
    pass


_session = None


def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept-Language': 'cs-CZ,cs;q=0.9,en;q=0.5',
        })
    return _session


def absolute(url):
    return urljoin(BASE_URL + '/', url)


def fetch(url):
    try:
        resp = _get_session().get(absolute(url), timeout=TIMEOUT)
    except requests.Timeout:
        raise ScraperError('Server neodpověděl včas (timeout %d s).' % TIMEOUT)
    except requests.RequestException as exc:
        raise ScraperError('Chyba připojení: %s' % exc)
    if resp.status_code == 404:
        raise ScraperError('Stránka nenalezena (404).')
    if resp.status_code != 200:
        raise ScraperError('Server vrátil chybu HTTP %d.' % resp.status_code)
    resp.encoding = resp.encoding or 'utf-8'
    return resp.text


def _clean(text):
    text = re.sub(r'<[^>]+>', '', text or '')
    return html.unescape(re.sub(r'\s+', ' ', text)).strip()


def _duration_seconds(text):
    parts = [p for p in (text or '').strip().split(':') if p.isdigit()]
    secs = 0
    for p in parts:
        secs = secs * 60 + int(p)
    return secs


def _next_page(page):
    m = re.search(r'<a href="([^"]+)" class="pagination__next"', page)
    return absolute(html.unescape(m.group(1))) if m else None


def _page_count(page):
    m = re.search(r'data-pages="(\d+)"', page)
    return int(m.group(1)) if m else 0


def parse_videos(page):
    """Vrátí (seznam videí, URL další stránky, počet stránek)."""
    videos = []
    seen = set()
    blocks = page.split('<div class="video video-preview">')[1:]
    for block in blocks:
        # konec bloku = první uzavírací </a>
        block = block.split('</a>', 1)[0]
        m = re.search(r'<a href="([^"]+\.html)"', block)
        if not m:
            continue
        url = absolute(html.unescape(m.group(1)))
        if url in seen or 'freevideo.cz' not in url:
            continue
        seen.add(url)
        title = re.search(r'class="video__description">(.*?)</h5>', block, re.S)
        thumb = re.search(r'background-image:\s*url\(([^)]+)\)', block)
        dur = re.search(r'video__tag--duration">\s*([\d:]+)', block)
        quality = re.search(r'data-quality="([^"]+)"', block)
        videos.append({
            'url': url,
            'title': _clean(title.group(1)) if title else url.rsplit('/', 1)[-1],
            'thumb': html.unescape(thumb.group(1)).strip('\'"') if thumb else '',
            'duration': _duration_seconds(dur.group(1)) if dur else 0,
            'quality': quality.group(1) if quality else '',
            'cz': 'badge--cz' in block,
        })
    return videos, _next_page(page), _page_count(page)


def parse_categories(page):
    cats = []
    seen = set()
    pattern = re.compile(
        r'<a href="([^"]+)" class="category">(.*?)</a>', re.S)
    for m in pattern.finditer(page):
        url = absolute(html.unescape(m.group(1)))
        if url in seen:
            continue
        seen.add(url)
        body = m.group(2)
        name = re.search(r'class="category__description">(.*?)</h5>', body, re.S)
        thumb = re.search(r'data-original="([^"]+)"', body) or \
            re.search(r'background-image:\s*url\(([^)]+)\)', body)
        count = re.search(r'class="category__count">(.*?)</div>', body, re.S)
        cats.append({
            'url': url,
            'title': _clean(name.group(1)) if name else m.group(1),
            'thumb': html.unescape(thumb.group(1)) if thumb else '',
            'count': _clean(count.group(1)) if count else '',
        })
    return cats


def parse_streams(page):
    """Vrátí seznam (výška, URL) seřazený od nejvyšší kvality a info o videu."""
    streams = []
    for m in re.finditer(r'<source\b([^>]*)>', page):
        attrs = m.group(1)
        src = re.search(r'\bsrc="([^"]+)"', attrs)
        if not src or 'type="video/mp4"' not in attrs:
            continue
        size = re.search(r'\bsize="(\d+)"', attrs) or re.search(r'(\d{3,4})p\.mp4', src.group(1))
        streams.append((int(size.group(1)) if size else 0, html.unescape(src.group(1))))
    streams.sort(key=lambda s: s[0], reverse=True)
    info = {}
    m = re.search(r'<meta property="og:description" content="([^"]*)"', page)
    if m:
        info['plot'] = html.unescape(m.group(1)).strip()
    m = re.search(r'<h1>(.*?)</h1>', page, re.S)
    if m:
        info['title'] = _clean(m.group(1))
    m = re.search(r'<meta property="og:image" content="([^"]+)"', page)
    if m:
        info['thumb'] = html.unescape(m.group(1))
    return streams, info


def pick_stream(streams, max_height):
    """Nejlepší stream nepřesahující max_height (0 = bez omezení)."""
    if not streams:
        return None
    if max_height:
        for h, url in streams:
            if h <= max_height:
                return url
    return streams[0][1] if not max_height else streams[-1][1]


# --- adresy výpisů ---

def newest_url(section='/vase-videa/'):
    return absolute(section + 'nejnovejsi/')


def popular_url(section='/vase-videa/'):
    return absolute(section + 'nejnavstevovanejsi/')


def categories_url(section='/vase-videa/'):
    return absolute(section + 'kategorie/')


def search_url(query):
    return absolute('/vase-videa/vyhledavani/?q=' + quote_plus(query))


# --- pohodlné funkce ---

def get_videos(url):
    return parse_videos(fetch(url))


def get_categories(url):
    return parse_categories(fetch(url))


def get_streams(video_url):
    return parse_streams(fetch(video_url))
