# -*- coding: utf-8 -*-
"""Společné funkce pro všechny weby (HTTP, HLS, délky videí). Nezávislé na Kodi."""
import html
import re
from urllib.parse import urljoin

import requests

TIMEOUT = 20
USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')


class ScraperError(Exception):
    pass


class Site:
    """Základ modulu webu: HTTP session s UA, časovým limitem a srozumitelnými chybami."""
    ID = ''
    NAME = ''
    BASE_URL = ''
    LANG = 'en-US,en;q=0.8'
    COOKIES = {}

    def __init__(self):
        self._session = None

    @property
    def session(self):
        if self._session is None:
            s = requests.Session()
            s.headers.update({'User-Agent': USER_AGENT, 'Accept-Language': self.LANG})
            domain = re.sub(r'^https?://(www\.)?', '.', self.BASE_URL).split('/')[0]
            for k, v in self.COOKIES.items():
                s.cookies.set(k, v, domain=domain)
            self._session = s
        return self._session

    def absolute(self, url):
        return urljoin(self.BASE_URL, html.unescape(url or ''))

    def fetch(self, url, headers=None, json=False):
        try:
            resp = self.session.get(self.absolute(url), headers=headers, timeout=TIMEOUT)
        except requests.Timeout:
            raise ScraperError('%s neodpověděl včas (timeout %d s).' % (self.NAME, TIMEOUT))
        except requests.RequestException as exc:
            raise ScraperError('Chyba připojení k %s: %s' % (self.NAME, exc))
        if resp.status_code == 404:
            raise ScraperError('Stránka nenalezena (404).')
        if resp.status_code in (403, 503) and 'Just a moment' in resp.text[:2000]:
            raise ScraperError('%s je chráněný proti robotům (Cloudflare), nelze načíst.' % self.NAME)
        if resp.status_code != 200:
            raise ScraperError('%s vrátil chybu HTTP %d.' % (self.NAME, resp.status_code))
        if json:
            try:
                return resp.json()
            except ValueError:
                raise ScraperError('%s vrátil neplatná data.' % self.NAME)
        resp.encoding = resp.encoding or 'utf-8'
        return resp.text

    # rozhraní, které weby implementují
    def menu(self, sub=None):
        """Seznam položek (popisek, akce, parametry). Akce: list, categories, search, menu."""
        raise NotImplementedError

    def get_videos(self, url):
        """Vrátí (videa, URL další stránky, počet stránek nebo 0)."""
        raise NotImplementedError

    def get_categories(self, url):
        raise NotImplementedError

    def search_url(self, query):
        raise NotImplementedError

    def get_streams(self, url):
        """Vrátí (streamy seřazené od nejvyšší kvality, info o videu).
        Stream = {'height': int, 'url': str, 'type': 'mp4'|'hls', 'headers': {...}}"""
        raise NotImplementedError

    def play_headers(self, referer=None):
        return {'User-Agent': USER_AGENT, 'Referer': referer or self.BASE_URL}


# --- pomocné funkce ---

def clean(text):
    text = re.sub(r'<[^>]+>', '', text or '')
    return html.unescape(re.sub(r'\s+', ' ', text)).strip()


def duration_seconds(text):
    """'7:25', '1:02:03', '11 min', '45 sec', '1 h 5 min', '21min', 3735 -> sekundy."""
    if isinstance(text, (int, float)):
        return int(text)
    text = (text or '').strip().lower()
    if not text:
        return 0
    if re.fullmatch(r'\d+(:\d+){1,2}', text):
        secs = 0
        for p in text.split(':'):
            secs = secs * 60 + int(p)
        return secs
    total = 0
    for num, unit in re.findall(r'(\d+)\s*(h|hod|min|m|s|sec)', text):
        total += int(num) * {'h': 3600, 'hod': 3600, 'min': 60, 'm': 60}.get(unit, 1)
    if not total and text.isdigit():
        total = int(text)
    return total


def height_of(label):
    """'1080p', '720p(60fps)', '4k', 'hd' -> výška v pixelech."""
    label = str(label or '').lower()
    if '4k' in label or '2160' in label:
        return 2160
    m = re.search(r'(\d{3,4})', label)
    return int(m.group(1)) if m else 0


def hls_variants(site, master_url, headers=None):
    """Rozloží hlavní HLS playlist na varianty [(výška, URL media playlistu)] od nejvyšší."""
    text = site.fetch(master_url, headers=headers)
    if '#EXT-X-STREAM-INF' not in text:
        return [(0, master_url)]
    out = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith('#EXT-X-STREAM-INF'):
            continue
        uri = next((l.strip() for l in lines[i + 1:] if l.strip() and not l.startswith('#')), None)
        if not uri:
            continue
        name = re.search(r'NAME="([^"]+)"', line)
        res = re.search(r'RESOLUTION=(\d+)x(\d+)', line)
        h = height_of(name.group(1)) if name else 0
        if not h and res:
            h = int(res.group(2))
            # 1934x1074 apod. zaokrouhlit na běžnou výšku
            for std in (2160, 1440, 1080, 720, 480, 360, 240, 144):
                if abs(h - std) <= std * 0.03:
                    h = std
                    break
        out.append((h, urljoin(master_url, uri)))
    out.sort(key=lambda x: x[0], reverse=True)
    return out


def hls_streams(site, master_url, headers=None):
    return [{'height': h, 'url': u, 'type': 'hls', 'headers': headers or site.play_headers()}
            for h, u in hls_variants(site, master_url, headers)]


def pick_stream(streams, max_height):
    """Nejlepší stream nepřesahující max_height (0 = nejvyšší); jinak ten nejnižší."""
    if not streams:
        return None
    if not max_height:
        return streams[0]
    for s in streams:
        if s['height'] <= max_height:
            return s
    return streams[-1]


def sort_streams(streams):
    """Seřadí od nejvyšší kvality, při stejné výšce dá přednost MP4 (lépe se stahuje)."""
    seen = set()
    out = []
    for s in sorted(streams, key=lambda s: (s['height'], s['type'] == 'mp4'), reverse=True):
        if s['url'] in seen:
            continue
        seen.add(s['url'])
        out.append(s)
    return out


def next_after_active(html_text, active_patterns=(r'class="active"', r'class="current"')):
    """V bloku stránkování najde odkaz hned za aktivní stránkou."""
    for pat in active_patterns:
        m = re.search(pat + r'[^>]*>.*?</a>(.*?)href="([^"#][^"]*)"', html_text, re.S)
        if m and len(m.group(1)) < 200:
            return m.group(2)
    return None
