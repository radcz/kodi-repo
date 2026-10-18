# -*- coding: utf-8 -*-
"""YourLesbians.com - čistě lesbický web (engine KVS; podle modulu z Cumination, GPL-3.0)."""
import re
from urllib.parse import quote, urlsplit, parse_qsl

from resources.lib import common


class YourLesbians(common.Site):
    ID = 'yourlesbians'
    NAME = 'YourLesbians'
    BASE_URL = 'https://yourlesbians.com/'
    LESBIAN_MENU = [('Nejnovější', '/lesbian-videos/')]

    def menu(self, sub=None):
        return [
            ('Nejnovější', 'list', {'url': self.absolute('/lesbian-videos/')}),
            ('Nejpopulárnější', 'list', {'url': self.absolute('/most-popular/')}),
            ('Nejlépe hodnocené', 'list', {'url': self.absolute('/top-rated/')}),
            ('Kategorie', 'categories', {'url': self.absolute('/categories/')}),
            ('Hledat', 'search', {}),
        ]

    def _next_url(self, url, page):
        """KVS stránkuje přes AJAX: ?mode=async&function=get_block&block_id=...&from=N"""
        cur = 1
        q = dict(parse_qsl(urlsplit(url).query))
        for k, v in q.items():
            if k.startswith('from') and v.isdigit():
                cur = int(v)
        best = None
        for block, params in re.findall(r'data-block-id="([^"]+)"[^>]*data-parameters="([^"]+)"', page):
            pairs = [p.split(':', 1) for p in params.split(';') if ':' in p]
            num = next((int(v) for k, v in pairs if k.startswith('from') and v.isdigit()), None)
            if num and num > cur and (best is None or num < best[0]):
                best = (num, block, pairs)
        if not best:
            return None
        num, block, pairs = best
        query = ['mode=async', 'function=get_block', 'block_id=' + block]
        for k, v in pairs:
            for key in k.split('+'):
                query.append('%s=%s' % (key, quote(v)))
        return url.split('?', 1)[0] + '?' + '&'.join(query)

    def get_videos(self, url):
        page = self.fetch(url)
        videos, seen = [], set()
        for block in page.split('<div class="thumb')[1:]:
            block = block[:3000]
            m = re.search(r'href="(https://yourlesbians\.com/video/[^"]+)"', block)
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            title = re.search(r'\btitle="([^"]+)"', block) or re.search(r'\balt="([^"]+)"', block)
            thumb = re.search(r'data-original="([^"]+)"', block)
            dur = re.search(r'class="time">\s*([\d:]+)', block)
            hd = re.search(r'class="(?:hd|is-hd)[^"]*">\s*([^<]+)<', block)
            videos.append({
                'url': m.group(1),
                'title': common.clean(title.group(1)) if title else m.group(1),
                'thumb': thumb.group(1).replace(' ', '%20') if thumb else '',
                'duration': common.duration_seconds(dur.group(1)) if dur else 0,
                'quality': common.clean(hd.group(1)) if hd else '',
            })
        return videos, self._next_url(url, page), 0

    def get_categories(self, url):
        page = self.fetch(url)
        cats, seen = [], set()
        for href, name, img in re.findall(
                r'<a href="(https://yourlesbians\.com/categories/[^"]+/)" title="([^"]+)">.*?data-original="([^"]+)"',
                page, re.S):
            if href in seen:
                continue
            seen.add(href)
            cats.append({'url': href, 'title': common.clean(name), 'thumb': img.replace(' ', '%20'), 'count': ''})
        return sorted(cats, key=lambda c: c['title'].lower())

    def search_url(self, query):
        return self.absolute('/search/%s/' % quote(query.replace(' ', '-')))

    def get_streams(self, url):
        page = self.fetch(url)
        headers = self.play_headers(url)
        streams = []
        for key, label in (('video_url', 'video_url_text'), ('video_alt_url', 'video_alt_url_text'),
                           ('video_alt_url2', 'video_alt_url2_text'), ('video_alt_url3', 'video_alt_url3_text')):
            m = re.search(r"\b%s\s*:\s*'([^']+)'" % key, page)
            if not m or m.group(1).startswith('function/'):
                continue  # zašifrované odkazy KVS nepodporujeme
            lab = re.search(r"\b%s\s*:\s*'([^']*)'" % label, page)
            h = common.height_of(lab.group(1)) if lab else 0
            streams.append({'height': h or 480, 'url': m.group(1), 'type': 'mp4', 'headers': headers})
        info = {}
        t = re.search(r'<meta property="og:title" content="([^"]+)"', page)
        if t:
            info['title'] = common.clean(t.group(1))
        th = re.search(r"preview_url\s*:\s*'([^']+)'", page) or \
            re.search(r'<meta property="og:image" content="([^"]+)"', page)
        if th:
            info['thumb'] = th.group(1)
        return common.sort_streams(streams), info


site = YourLesbians()
