# -*- coding: utf-8 -*-
"""Pornhub.com (podle modulu pornhub z Cumination, GPL-3.0)."""
import re
from urllib.parse import quote_plus

from resources.lib import common


class Pornhub(common.Site):
    ID = 'pornhub'
    NAME = 'Pornhub'
    BASE_URL = 'https://www.pornhub.com/'
    LESBIAN_MENU = [('Lesbičky – nejnovější', '/video?c=27&o=cm'),
                    ('Lesbičky – nejsledovanější', '/video?c=27&o=mv'),
                    ('Lesbičky – nejlépe hodnocené', '/video?c=27&o=tr')]
    # potvrzení věku 18+ (stejné jako kliknutí na „Je mi 18“)
    COOKIES = {'accessAgeDisclaimerPH': '1', 'accessAgeDisclaimerUK': '1'}

    def menu(self, sub=None):
        return [
            ('Nejnovější', 'list', {'url': self.BASE_URL + 'video?o=cm'}),
            ('Nejsledovanější', 'list', {'url': self.BASE_URL + 'video?o=mv'}),
            ('Nejlépe hodnocené', 'list', {'url': self.BASE_URL + 'video?o=tr'}),
            ('Kategorie', 'categories', {'url': self.BASE_URL + 'categories'}),
            ('Hledat', 'search', {}),
        ]

    def get_videos(self, url):
        page = self.fetch(url)
        m = re.search(r'videos\s*search-video-thumbs.*?">(.*?)<div\s*class="reset">', page, re.S)
        block = m.group(1) if m else page
        videos, seen = [], set()
        for item in block.split('class="pcVideoListItem')[1:]:
            if 'premiumIcon' in item:  # placená videa nejdou přehrát
                continue
            u = re.search(r'<a href="(/view_video\.php\?viewkey=[^"]+)"', item)
            if not u:
                continue
            url_ = self.absolute(u.group(1))
            if url_ in seen:
                continue
            seen.add(url_)
            title = re.search(r'\btitle="([^"]+)"', item)
            thumb = re.search(r'data-mediumthumb="([^"]+)"', item) or re.search(r'<img[^>]+src="(https[^"]+)"', item)
            dur = re.search(r'(?:data-title="Video Duration">|class="duration">)([^<]+)<', item)
            hd = 'HD' if 'hd-thumbnail' in item or 'class="hd' in item else ''
            videos.append({
                'url': url_,
                'title': common.clean(title.group(1)) if title else url_,
                'thumb': thumb.group(1).replace('&amp;', '&') if thumb else '',
                'duration': common.duration_seconds(dur.group(1)) if dur else 0,
                'quality': hd,
            })
        n = re.search(r'<li\s*class="page_next">\s*<a\s*href="([^"]+)"', page)
        nxt = self.absolute(n.group(1)) if n else None
        return videos, nxt, 0

    def get_categories(self, url):
        page = self.fetch(url)
        cats, seen = [], set()
        for href, name, img, count in re.findall(
                r'<div class="category-wrapper.*?href="([^"]+)"\s*alt="([^"]+)".*?src="([^"]+).+?<var>([^<]+)<',
                page, re.S):
            u = self.absolute(href)
            if u in seen:
                continue
            seen.add(u)
            cats.append({'url': u, 'title': common.clean(name), 'thumb': img, 'count': count.strip()})
        return sorted(cats, key=lambda c: c['title'].lower())

    def search_url(self, query):
        return self.BASE_URL + 'video/search?search=' + quote_plus(query)

    def get_streams(self, url):
        page = self.fetch(url)
        headers = self.play_headers(url)
        streams = []
        m = re.search(r'"format":"mp4","videoUrl":"([^"]+)"', page)
        if m:
            media = self.fetch(m.group(1).replace('\\/', '/'), headers={'Referer': url}, json=True)
            for s in media if isinstance(media, list) else []:
                if isinstance(s, dict) and s.get('videoUrl'):
                    streams.append({'height': common.height_of(s.get('quality') or s.get('height')),
                                    'url': s['videoUrl'], 'type': 'mp4', 'headers': headers})
        if not streams and ('premium' in page.lower() and 'videoUrl' not in page):
            raise common.ScraperError('Video je jen pro Premium uživatele.')
        info = {}
        t = re.search(r'<meta property="og:title" content="([^"]+)"', page)
        if t:
            info['title'] = common.clean(t.group(1))
        th = re.search(r'<meta property="og:image" content="([^"]+)"', page)
        if th:
            info['thumb'] = th.group(1)
        return common.sort_streams(streams), info


site = Pornhub()
