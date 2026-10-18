# -*- coding: utf-8 -*-
"""Eporner.com (podle modulu eporner z Cumination, GPL-3.0)."""
import re
from urllib.parse import quote

from resources.lib import common


def _base36(num):
    table = '0123456789abcdefghijklmnopqrstuvwxyz'
    out = ''
    while num:
        num, r = divmod(num, 36)
        out = table[r] + out
    return out or '0'


class Eporner(common.Site):
    ID = 'eporner'
    NAME = 'Eporner'
    BASE_URL = 'https://www.eporner.com/'
    LESBIAN_MENU = [('Lesbičky', '/cat/lesbians/'),
                    ('Lesbičky – nejlépe hodnocené', '/cat/lesbians/SORT-top-rated/')]

    def menu(self, sub=None):
        return [
            ('Nejnovější', 'list', {'url': self.BASE_URL + 'cat/all/'}),
            ('Populární', 'list', {'url': self.BASE_URL + 'cat/popular-videos/'}),
            ('Nejlépe hodnocené', 'list', {'url': self.BASE_URL + 'cat/top-rated/'}),
            ('4K Ultra HD', 'list', {'url': self.BASE_URL + 'cat/4k-porn/'}),
            ('Kategorie', 'categories', {'url': self.BASE_URL + 'cats/'}),
            ('Hledat', 'search', {}),
        ]

    def get_videos(self, url):
        page = self.fetch(url)
        videos, seen = [], set()
        for vid in page.split('data-vp=')[1:]:
            vid = vid[:3000]
            u = re.search(r'href="(/(?:hd-porn|video-)[^"]+)"', vid)
            if not u:
                continue
            url_ = self.absolute(u.group(1))
            if url_ in seen:
                continue
            seen.add(url_)
            thumb = re.search(r'<img[^>]+(?:data-src|src)="(http[^"]+)"', vid)
            title = re.search(r'\balt="([^"]+)"', vid) or re.search(r'class="mbtit"><a[^>]*>([^<]+)<', vid)
            q = re.search(r'title="Quality"><span>([^<]+)<', vid)
            dur = re.search(r'title="Duration">([^<]+)<', vid)
            videos.append({
                'url': url_,
                'title': common.clean(title.group(1)) if title else url_,
                'thumb': thumb.group(1) if thumb else '',
                'duration': common.duration_seconds(dur.group(1)) if dur else 0,
                'quality': q.group(1) if q else '',
            })
        n = re.search(r"href='([^']+)' class='nmnext' title='Next page'", page)
        nxt = self.absolute(n.group(1)) if n else None
        return videos, nxt, 0

    def get_categories(self, url):
        page = self.fetch(url)
        cats = []
        for href, name, img in re.findall(
                r'class="ctbinner"[^=]+href="([^"]+)" title="([^"]+)"[^:]+img src="([^"]+)"', page, re.S):
            cats.append({'url': self.absolute(href), 'title': common.clean(name), 'thumb': img, 'count': ''})
        return sorted(cats, key=lambda c: c['title'].lower())

    def search_url(self, query):
        return self.BASE_URL + 'search/' + quote(query.replace(' ', '-')) + '/'

    def get_streams(self, url):
        page = self.fetch(url)
        m = re.search(r"vid\s*=\s*'([^']+)'.+?hash\s*=\s*'([0-9a-fA-F]{32})'", page, re.S)
        if not m:
            raise common.ScraperError('Eporner: video nenalezeno (možná bylo smazáno).')
        vid, h = m.groups()
        hsh = ''.join(_base36(int(h[i:i + 8], 16)) for i in range(0, 32, 8))
        data = self.fetch('%sxhr/video/%s?hash=%s&domain=www.eporner.com&fallback=false&embed=true'
                          '&supportedFormats=dash,mp4' % (self.BASE_URL, vid, hsh),
                          headers={'Referer': url}, json=True)
        headers = self.play_headers(url)
        streams = []
        for label, src in ((data.get('sources') or {}).get('mp4') or {}).items():
            if isinstance(src, dict) and src.get('src'):
                streams.append({'height': common.height_of(label), 'url': src['src'], 'type': 'mp4',
                                'headers': headers})
        info = {}
        t = re.search(r'<meta property="og:title" content="([^"]+)"', page)
        if t:
            info['title'] = common.clean(t.group(1)).replace(' - EPORNER', '')
        th = re.search(r'<meta property="og:image" content="([^"]+)"', page)
        if th:
            info['thumb'] = th.group(1)
        return common.sort_streams(streams), info


site = Eporner()
