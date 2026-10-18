# -*- coding: utf-8 -*-
"""xVideos.com (podle modulu xvideos z Cumination, GPL-3.0)."""
import re
from urllib.parse import quote_plus

from resources.lib import common


def parse_xv_videos(site, page):
    """Výpis videí pro xVideos i XNXX (oba weby mají staré i nové šablony)."""
    videos, seen = [], set()
    blocks = re.split(r'<div\s+id="video_|id="video-thumb-', page)[1:]
    for block in blocks:
        block = block.split('xv.thumbs.prepareVideo', 1)[0][:6000]
        m = re.search(r'href="(/video[.\-][^"]+)"', block)
        if not m:
            continue
        url = site.absolute(m.group(1))
        if url in seen:
            continue
        seen.add(url)
        title = re.search(r'<a[^>]+href="/video[^"]+"[^>]*\btitle="([^"]+)"', block) or \
            re.search(r'\btitle="([^"]+)"', block) or re.search(r'\balt="([^"]+)"', block)
        thumb = re.search(r'data-src="([^"]+\.jpg[^"]*)"', block) or re.search(r'data-srcset="([^"]+\.jpg)"', block)
        dur = re.search(r'class="duration">\s*\(?([^<)]+)', block) or \
            re.search(r'(?:metadata"[^>]*>|class="left">)(?:.|\n)*?(\d+\s*(?:h|min|sec)[^<\-]*)', block)
        quality = re.search(r'(?:video-hd-mark|video-hd)"[^>]*>(?:<span[^>]*>.*?</span>)?\s*(\d+p)', block, re.S) or \
            re.search(r'>\s*(\d{3,4}p)\s*<', block)
        videos.append({
            'url': url,
            'title': common.clean(title.group(1)) if title else url.rsplit('/', 1)[-1],
            'thumb': (thumb.group(1).replace('THUMBNUM', '1')) if thumb else '',
            'duration': common.duration_seconds(common.clean(dur.group(1))) if dur else 0,
            'quality': quality.group(1) if quality else '',
        })
    return videos


def xv_streams(site, url):
    page = site.fetch(url)
    headers = site.play_headers(url)
    streams = []
    hls = re.search(r"html5player\.setVideoHLS\('([^']+)'", page)
    if hls:
        try:
            streams += common.hls_streams(site, hls.group(1), headers)
        except common.ScraperError:
            pass
    for fn, h in (('setVideoUrlHigh', 480), ('setVideoUrlLow', 360)):
        m = re.search(r"html5player\.%s\('([^']+)'" % fn, page)
        if m:
            label = re.search(r'mp4_(\w+)\.mp4', m.group(1))
            height = {'sd': 360, 'hd': 720, 'lowq': 240}.get(label.group(1), h) if label else h
            streams.append({'height': height, 'url': m.group(1), 'type': 'mp4', 'headers': headers})
    info = {}
    t = re.search(r"html5player\.setVideoTitle\('(.*?)'\);", page)
    if t:
        info['title'] = common.clean(t.group(1))
    th = re.search(r'<meta property="og:image" content="([^"]+)"', page)
    if th:
        info['thumb'] = th.group(1)
    return common.sort_streams(streams), info


class XVideos(common.Site):
    ID = 'xvideos'
    NAME = 'xVideos'
    BASE_URL = 'https://www.xvideos.com/'
    LANG = 'cs-CZ,cs;q=0.9,en;q=0.6'

    def menu(self, sub=None):
        return [
            ('Nejnovější', 'list', {'url': self.BASE_URL}),
            ('Kategorie', 'categories', {'url': self.BASE_URL}),
            ('Hledat', 'search', {}),
        ]

    def get_videos(self, url):
        page = self.fetch(url)
        m = re.search(r'href="([^"]+)"\s+class="no-page next-page', page)
        nxt = self.absolute(m.group(1)) if m and not m.group(1).startswith('#') else None
        return parse_xv_videos(self, page), nxt, 0

    def get_categories(self, url):
        page = self.fetch(url)
        cats, seen = [], set()
        for href, name in re.findall(r'<a href="(/c/[^"]+)"[^>]*>([^<]+)<', page):
            u = self.absolute(href)
            if u not in seen:
                seen.add(u)
                cats.append({'url': u, 'title': common.clean(name), 'thumb': '', 'count': ''})
        return sorted(cats, key=lambda c: c['title'].lower())

    def search_url(self, query):
        return self.BASE_URL + '?k=' + quote_plus(query)

    def get_streams(self, url):
        return xv_streams(self, url)


site = XVideos()
