# -*- coding: utf-8 -*-
"""Weby na enginu KVS (Kernel Video Sharing): YourLesbians, Lesbian8, PornTrex.

Přehrávají se jen nešifrované odkazy video_url (get_file); zašifrované "function/0/..." ne.
"""
import re
from urllib.parse import quote, urlsplit, parse_qsl

from resources.lib import common


class KVSSite(common.Site):
    VIDEO_RE = ''          # regex odkazu na video (skupina 1 = URL)
    MENU = []              # (popisek, cesta) výpisů
    CATEGORIES = '/categories/'
    CAT_RE = ''            # regex (odkaz, název[, náhled])
    SEARCH = '/search/{q}/'

    def menu(self, sub=None):
        items = [(label, 'list', {'url': self.absolute(path)}) for label, path in self.MENU]
        items += [('Kategorie', 'categories', {'url': self.absolute(self.CATEGORIES)}), ('Hledat', 'search', {})]
        return items

    def _next_url(self, url, page):
        cur = 1
        for k, v in parse_qsl(urlsplit(url).query):
            if k.startswith('from') and v.isdigit():
                cur = int(v)
        best = None
        for block, params in re.findall(r'data-block-id="([^"]+)"[^>]*data-parameters="([^"]+)"', page):
            pairs = [p.split(':', 1) for p in params.split(';') if ':' in p]
            num = next((int(v) for k, v in pairs if k.startswith('from') and v.isdigit()), None)
            if num and num > cur and (best is None or num < best[0]):
                best = (num, block, pairs)
        if best:
            num, block, pairs = best
            query = ['mode=async', 'function=get_block', 'block_id=' + block]
            for k, v in pairs:
                for key in k.split('+'):
                    query.append('%s=%s' % (key, quote(v.lstrip('0') or v)))
            return url.split('?', 1)[0] + '?' + '&'.join(query)
        m = re.search(r'<link rel="next" href="([^"]+)"', page) or \
            re.search(r'<a[^>]+class="[^"]*\bnext\b[^"]*"[^>]*href="([^"#][^"]*)"', page) or \
            re.search(r'<a[^>]+href="([^"#][^"]*)"[^>]*class="[^"]*\bnext\b', page)
        return self.absolute(m.group(1)) if m else None

    def get_videos(self, url):
        page = self.fetch(url)
        matches = list(re.finditer(self.VIDEO_RE, page))
        videos, seen = [], {}
        for i, m in enumerate(matches):
            vurl = self.absolute(m.group(1))
            end = matches[i + 1].start() if i + 1 < len(matches) else m.start() + 3000
            block = page[max(0, m.start() - 200):min(end, m.start() + 3000)]
            if vurl in seen:
                continue
            title = common.pick_title(block[200:])
            thumb = re.search(r'(?:data-original|data-src|src)="((?:https?:)?//[^"]+\.(?:jpg|jpeg|webp|png)[^"]*)"', block)
            dur = re.search(r'class="[^"]*(?:duration|time)[^"]*"[^>]*>(?:\s*<[^>]+>)*\s*([\d:]{4,8})', block)
            hd = re.search(r'class="[^"]*(?:is-hd|hd)[^"]*"[^>]*>\s*([^<]{1,6})<', block)
            th = thumb.group(1) if thumb else ''
            v = {
                'url': vurl,
                'title': title or vurl.rstrip('/').rsplit('/', 1)[-1].replace('-', ' '),
                'thumb': ('https:' + th if th.startswith('//') else th).replace(' ', '%20'),
                'duration': common.duration_seconds(dur.group(1)) if dur else 0,
                'quality': common.clean(hd.group(1)) if hd else '',
            }
            seen[vurl] = v
            videos.append(v)
        return videos, self._next_url(url, page), 0

    def get_categories(self, url):
        page = self.fetch(url)
        cats, seen = [], set()
        for m in re.finditer(self.CAT_RE, page, re.S):
            href, name = m.group(1), m.group(2)
            img = m.group(3) if m.lastindex and m.lastindex >= 3 else ''
            u = self.absolute(href)
            if u in seen:
                continue
            seen.add(u)
            cats.append({'url': u, 'title': common.clean(name), 'thumb': (img or '').replace(' ', '%20'), 'count': ''})
        return sorted(cats, key=lambda c: c['title'].lower())

    def search_url(self, query):
        return self.absolute(self.SEARCH.format(q=quote(query.replace(' ', '-'))))

    def get_streams(self, url):
        page = self.fetch(url)
        headers = self.play_headers(url)
        streams = []
        for key in ('video_url', 'video_alt_url', 'video_alt_url2', 'video_alt_url3', 'video_alt_url4'):
            m = re.search(r"\b%s\s*:\s*'([^']+)'" % key, page)
            if not m or m.group(1).startswith('function/'):
                continue  # zašifrované odkazy KVS nepodporujeme
            lab = re.search(r"\b%s_text\s*:\s*'([^']*)'" % key, page)
            h = common.height_of(lab.group(1)) if lab else 0
            if not h:
                h = common.height_of(re.search(r'_(\d{3,4})p\.mp4', m.group(1)).group(1)) \
                    if re.search(r'_(\d{3,4})p\.mp4', m.group(1)) else 480
            streams.append({'height': h, 'url': m.group(1), 'type': 'mp4', 'headers': headers})
        info = {}
        t = re.search(r'<meta property="og:title" content="([^"]+)"', page)
        if t:
            info['title'] = common.clean(t.group(1))
        th = re.search(r"preview_url\s*:\s*'([^']+)'", page) or \
            re.search(r'<meta property="og:image" content="([^"]+)"', page)
        if th:
            info['thumb'] = th.group(1)
        return common.sort_streams(streams), info


class YourLesbians(KVSSite):
    ID = 'yourlesbians'
    NAME = 'YourLesbians'
    BASE_URL = 'https://yourlesbians.com/'
    LESBIAN_MENU = [('Nejnovější', '/lesbian-videos/')]
    VIDEO_RE = r'href="(https://yourlesbians\.com/video/[^"]+)"'
    MENU = [('Nejnovější', '/lesbian-videos/'), ('Nejpopulárnější', '/most-popular/'),
            ('Nejlépe hodnocené', '/top-rated/')]
    CAT_RE = r'<a href="(https://yourlesbians\.com/categories/[^"]+/)" title="([^"]+)">.*?data-original="([^"]+)"'


class Lesbian8(KVSSite):
    ID = 'lesbian8'
    NAME = 'Lesbian8'
    BASE_URL = 'https://www.lesbian8.com/'
    LESBIAN_MENU = [('Nejnovější', '/latest-updates/')]
    VIDEO_RE = r'href="(https://www\.lesbian8\.com/videos/\d+/[^"]+)"'
    MENU = [('Nejnovější', '/latest-updates/'), ('Nejsledovanější', '/most-popular/'),
            ('Nejlépe hodnocené', '/top-rated/')]
    CAT_RE = r'<a class="item" href="(https://www\.lesbian8\.com/categories/[^"]+/)" title="([^"]+)"'


class PornTrex(KVSSite):
    ID = 'porntrex'
    NAME = 'PornTrex'
    BASE_URL = 'https://www.porntrex.com/'
    LESBIAN_MENU = [('Lesbičky', '/categories/lesbian/')]
    VIDEO_RE = r'href="(https://www\.porntrex\.com/video/\d+/[^"]+)"'
    MENU = [('Nejnovější', '/latest-updates/'), ('Nejsledovanější', '/most-popular/'),
            ('Nejlépe hodnocené', '/top-rated/')]
    CAT_RE = r'href="(https://www\.porntrex\.com/categories/[^"]+/)"[^>]*>\s*(?:<[^>]+>\s*)*([^<]{2,40})<'


yourlesbians = YourLesbians()
lesbian8 = Lesbian8()
porntrex = PornTrex()
