# -*- coding: utf-8 -*-
"""YouJizz a PornOne - jednoduché HTML výpisy, přímé MP4."""
import json
import re
from urllib.parse import quote, quote_plus

from resources.lib import common


class YouJizz(common.Site):
    ID = 'youjizz'
    NAME = 'YouJizz'
    BASE_URL = 'https://www.youjizz.com/'
    LESBIAN_MENU = [('Lesbičky', '/categories/lesbian-1.html')]

    def menu(self, sub=None):
        return [
            ('Nejnovější', 'list', {'url': self.absolute('/newest-clips/1.html')}),
            ('Nejpopulárnější', 'list', {'url': self.absolute('/most-popular/1.html')}),
            ('Kategorie', 'categories', {'url': self.absolute('/newest-clips/1.html')}),
            ('Hledat', 'search', {}),
        ]

    def get_videos(self, url):
        page = self.fetch(url)
        videos, seen = [], set()
        for block in page.split('class="video-thumb"')[1:]:
            block = block[:4000]
            m = re.search(r'href="(/videos/[^"]+\.html)"', block)
            if not m:
                continue
            u = self.absolute(m.group(1))
            if u in seen:
                continue
            seen.add(u)
            title = re.search(r'class="video-title">\s*<a[^>]*>([^<]+)<', block)
            thumb = re.search(r'data-original="([^"]+)"', block)
            dur = re.search(r'class="time">(?:<[^>]+>|&nbsp;|\s)*([\d:]+)', block)
            th = thumb.group(1) if thumb else ''
            videos.append({'url': u, 'title': common.clean(title.group(1)) if title else u,
                           'thumb': 'https:' + th if th.startswith('//') else th,
                           'duration': common.duration_seconds(dur.group(1)) if dur else 0, 'quality': ''})
        n = re.search(r'<a[^>]+class="[^"]*\bnext\b[^"]*"[^>]*href="([^"#][^"]*)"', page) or \
            re.search(r'<a[^>]+href="([^"#][^"]*)"[^>]*class="[^"]*\bnext\b', page)
        return videos, (self.absolute(n.group(1)) if n else None), 0

    def get_categories(self, url):
        page = self.fetch(url)
        cats, seen = [], set()
        for href, name in re.findall(r'href="(/categories/[a-z0-9\-]+-1\.html)"[^>]*>\s*([^<]+)<', page):
            u = self.absolute(href)
            if u not in seen:
                seen.add(u)
                cats.append({'url': u, 'title': common.clean(name).title(), 'thumb': '', 'count': ''})
        for name, path in (('Lesbian', '/categories/lesbian-1.html'),):
            if self.absolute(path) not in seen:
                cats.append({'url': self.absolute(path), 'title': name, 'thumb': '', 'count': ''})
        return sorted(cats, key=lambda c: c['title'].lower())

    def search_url(self, query):
        return self.absolute('/search/%s-1.html' % quote(query.replace(' ', '-')))

    def get_streams(self, url):
        page = self.fetch(url)
        headers = self.play_headers(url)
        m = re.search(r'dataEncodings\s*=\s*(\[.*?\]);', page, re.S)
        streams = []
        try:
            encs = json.loads(m.group(1)) if m else []
        except ValueError:
            encs = []
        for e in encs:
            fn = (e or {}).get('filename') or ''
            if not fn:
                continue
            fn = 'https:' + fn if fn.startswith('//') else fn
            kind = 'hls' if '.m3u8' in fn else 'mp4'
            streams.append({'height': common.height_of(e.get('quality') or e.get('name')), 'url': fn,
                            'type': kind, 'headers': headers})
        info = {}
        t = re.search(r'<title>([^<]+)</title>', page)
        if t:
            info['title'] = common.clean(t.group(1)).split(' - YouJizz')[0]
        return common.sort_streams(streams), info


class PornOne(common.Site):
    ID = 'pornone'
    NAME = 'PornOne'
    BASE_URL = 'https://pornone.com/'
    LESBIAN_MENU = [('Lesbičky', '/lesbian/')]

    def menu(self, sub=None):
        return [
            ('Nejnovější', 'list', {'url': self.absolute('/newest/')}),
            ('Kategorie', 'categories', {'url': self.absolute('/categories/')}),
            ('Hledat', 'search', {}),
        ]

    def get_videos(self, url):
        page = self.fetch(url)
        videos, seen = [], set()
        for m in re.finditer(r'<a href="(https://pornone\.com/[a-z0-9\-]+/[a-z0-9\-]+/\d+/)[^"]*"[^>]*class="[^"]*videocard', page):
            u = m.group(1)
            if u in seen:
                continue
            seen.add(u)
            block = page[m.start():m.start() + 5000]
            nxt = block.find('videocard', 300)
            block = block[:nxt] if nxt > 0 else block
            title = common.pick_title(block)
            thumb = re.search(r'data-src="(https://[^"]+\.(?:jpg|webp)[^"]*)"', block)
            dur = re.search(r'class="durlabel">(?:<[^>]+>)*\s*([\d:]+)', block)
            name = title or u.rstrip('/').split('/')[-2].replace('-', ' ')
            videos.append({'url': u, 'title': name, 'thumb': thumb.group(1) if thumb else '',
                           'duration': common.duration_seconds(dur.group(1)) if dur else 0,
                           'quality': 'HD' if 'hd.svg' in block[:1500] else ''})
        n = re.search(r'<link rel="next" href="([^"]+)"', page)
        return videos, (self.absolute(n.group(1)) if n else None), 0

    def get_categories(self, url):
        page = self.fetch(url)
        cats, seen = [], set()
        for href, img, name in re.findall(
                r'<a href="(/[a-z0-9\-]+/)" class="popbop relative[^"]*">\s*<img[^>]*?(?:data-src="([^"]+)")?[^>]*alt="Video category ([^"]+)"',
                page):
            u = self.absolute(href)
            if u not in seen:
                seen.add(u)
                cats.append({'url': u, 'title': common.clean(name), 'thumb': img or '', 'count': ''})
        return sorted(cats, key=lambda c: c['title'].lower())

    def search_url(self, query):
        return self.absolute('/search?q=' + quote_plus(query))

    def get_streams(self, url):
        page = self.fetch(url)
        headers = self.play_headers(url)
        streams = []
        for src, attrs in re.findall(r'<source[^>]+src="([^"]+)"([^>]*)>', page):
            if '.mp4' not in src and '.m3u8' not in src:
                continue
            res = re.search(r'(?:res|label|title)="([^"]*)"', attrs)
            h = common.height_of(res.group(1)) if res else 0
            if not h:
                m = re.search(r'_(\d+)x(\d+)_', src)
                h = int(m.group(2)) if m else 0
            streams.append({'height': h, 'url': src.replace('&amp;', '&'), 'type': 'hls' if '.m3u8' in src else 'mp4',
                            'headers': headers})
        info = {}
        t = re.search(r'<meta property="og:title" content="([^"]+)"', page)
        if t:
            info['title'] = common.clean(t.group(1))
        th = re.search(r'<meta property="og:image" content="([^"]+)"', page)
        if th:
            info['thumb'] = th.group(1)
        return common.sort_streams(streams), info


youjizz = YouJizz()
pornone = PornOne()
