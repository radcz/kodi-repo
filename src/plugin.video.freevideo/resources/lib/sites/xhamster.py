# -*- coding: utf-8 -*-
"""xHamster.com (podle modulu xhamster z Cumination, GPL-3.0)."""
import json
import re
from urllib.parse import quote

from resources.lib import common


def _initials(page):
    m = re.search(r'window\.initials\s*=\s*(\{.*?\});\s*</script>', page, re.S)
    if not m:
        raise common.ScraperError('xHamster: data stránky nenalezena.')
    try:
        return json.loads(m.group(1))
    except ValueError:
        raise common.ScraperError('xHamster: neplatná data stránky.')


def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            for x in _walk(v):
                yield x
    elif isinstance(obj, list):
        for v in obj:
            for x in _walk(v):
                yield x


class XHamster(common.Site):
    ID = 'xhamster'
    NAME = 'xHamster'
    BASE_URL = 'https://xhamster.com/'

    def menu(self, sub=None):
        return [
            ('Nejnovější', 'list', {'url': self.BASE_URL + 'newest'}),
            ('Nejlepší', 'list', {'url': self.BASE_URL + 'best'}),
            ('Kategorie', 'categories', {'url': self.BASE_URL + 'categories'}),
            ('Hledat', 'search', {}),
        ]

    def get_videos(self, url):
        data = _initials(self.fetch(url))
        thumbs = None
        for d in _walk(data):
            v = d.get('videoThumbProps')
            if isinstance(v, list) and v and isinstance(v[0], dict) and v[0].get('pageURL'):
                if thumbs is None or len(v) > len(thumbs):
                    thumbs = v
        videos = []
        for v in thumbs or []:
            if v.get('isBlockedByGeo'):
                continue
            q = '4K' if v.get('isUHD') else ('HD' if v.get('isHD') else '')
            videos.append({
                'url': v['pageURL'],
                'title': common.clean(v.get('title', '')),
                'thumb': v.get('thumbURL') or v.get('imageURL') or '',
                'duration': common.duration_seconds(v.get('duration') or 0),
                'quality': q,
            })
        nxt, pages = None, 0
        for d in _walk(data):
            p = d.get('paginationProps') or d.get('paginationComponent') or d.get('pagination')
            if isinstance(p, dict) and p.get('pageLinkTemplate'):
                cur = int(p.get('currentPageNumber') or p.get('active') or 1)
                pages = int(p.get('lastPageNumber') or p.get('maxPages') or 0)
                if not pages or cur < pages:
                    nxt = p['pageLinkTemplate'].replace('{#}', str(cur + 1))
                break
        return videos, nxt, pages

    def get_categories(self, url):
        data = _initials(self.fetch(url))
        cats, seen = [], set()
        for d in _walk(data):
            lst = d.get('list')
            if not isinstance(lst, dict):
                continue
            for items in lst.values():
                for c in items if isinstance(items, list) else []:
                    if isinstance(c, dict) and c.get('url') and c.get('name') and c['url'] not in seen:
                        seen.add(c['url'])
                        cats.append({'url': c['url'], 'title': common.clean(c['name']),
                                     'thumb': c.get('thumbUrl', '') or '', 'count': ''})
        if not cats:
            raise common.ScraperError('xHamster: seznam kategorií nenalezen.')
        return sorted(cats, key=lambda c: c['title'].lower())

    def search_url(self, query):
        return self.BASE_URL + 'search/' + quote(query)

    def get_streams(self, url):
        page = self.fetch(url)
        if 'This video was deleted' in page or 'Video is not available' in page:
            raise common.ScraperError('Video bylo smazáno nebo není dostupné.')
        headers = self.play_headers(url)
        streams = []
        m = re.search(r'<link rel="preload" href="([^"]+\.m3u8[^"]*)"', page)
        if m:
            master = m.group(1).replace('.av1.', '.h264.').replace('&amp;', '&')
            streams = common.hls_streams(self, master, headers)
        else:
            # záložní cesta: přímé MP4 v datech přehrávače (bez dešifrování)
            data = _initials(page)
            for d in _walk(data):
                std = d.get('standard') if isinstance(d.get('standard'), dict) else None
                for s in (std or {}).get('h264', []) or []:
                    if isinstance(s, dict) and str(s.get('url', '')).startswith('http'):
                        streams.append({'height': common.height_of(s.get('quality')), 'url': s['url'],
                                        'type': 'mp4', 'headers': headers})
        info = {}
        t = re.search(r'<meta property="og:title" content="([^"]+)"', page)
        if t:
            info['title'] = common.clean(t.group(1))
        th = re.search(r'<meta property="og:image" content="([^"]+)"', page)
        if th:
            info['thumb'] = th.group(1)
        return common.sort_streams(streams), info


site = XHamster()
