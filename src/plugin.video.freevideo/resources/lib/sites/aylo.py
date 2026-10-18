# -*- coding: utf-8 -*-
"""YouPorn, RedTube a Tube8 - weby na stejné platformě jako Pornhub (společný parser)."""
import re
from urllib.parse import quote_plus

from resources.lib import common


class AyloSite(common.Site):
    COOKIES = {'age_verified': '1', 'accessAgeDisclaimerPH': '1', 'accessAgeDisclaimerUK': '1'}
    LATEST = ''        # cesta výpisu nejnovějších
    POPULAR = ''       # cesta výpisu nejsledovanějších
    CATEGORIES = ''    # stránka se seznamem kategorií
    CAT_RE = ''        # regex (odkaz, název) nebo (název, odkaz) podle CAT_NAME_FIRST
    CAT_NAME_FIRST = False
    SEARCH = ''        # šablona hledání s {q}

    def menu(self, sub=None):
        items = [('Nejnovější', 'list', {'url': self.absolute(self.LATEST)})]
        if self.POPULAR:
            items.append(('Nejsledovanější', 'list', {'url': self.absolute(self.POPULAR)}))
        items += [('Kategorie', 'categories', {'url': self.absolute(self.CATEGORIES)}),
                  ('Hledat', 'search', {})]
        return items

    def get_videos(self, url):
        page = self.fetch(url)
        videos, seen = [], set()
        parts = page.split('data-testid="plw_video_thumbnail_link"')
        for i in range(1, len(parts)):
            # odkaz bývá těsně před nebo za atributem data-testid
            head = parts[i - 1][-400:]
            block = parts[i][:5000]
            m = re.search(r'href="([^"]+)"', block[:600]) or re.search(r'href="([^"]+)"[^>]*$', head)
            if not m or m.group(1).startswith(('#', 'javascript')):
                continue
            url_ = self.absolute(m.group(1))
            if url_ in seen or '/channels/' in url_ or '/pornstar' in url_:
                continue
            seen.add(url_)
            title = re.search(r'\balt="([^"]+)"', block) or re.search(r'\btitle="([^"]+)"', block)
            thumb = re.search(r'data-(?:src|o_thumb|poster|thumb_url)="(https[^"]+)"', block)
            dur = re.search(r'(?:duration|video_duration)[^>]*>\s*(?:<span[^>]*>)?\s*(\d{1,2}:\d{2}(?::\d{2})?)', block) or \
                re.search(r'>\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*<', block)
            hd = re.search(r'>\s*(4K|HD|1080p|720p)\s*<', block)
            videos.append({
                'url': url_,
                'title': common.clean(title.group(1)) if title else url_,
                'thumb': thumb.group(1).replace('&amp;', '&') if thumb else '',
                'duration': common.duration_seconds(dur.group(1)) if dur else 0,
                'quality': hd.group(1) if hd else '',
            })
        n = re.search(r'<link rel="next" href="([^"]+)"', page)
        return videos, (self.absolute(n.group(1)) if n else None), 0

    def get_categories(self, url):
        page = self.fetch(url)
        cats, seen = [], set()
        for a, b in re.findall(self.CAT_RE, page, re.S):
            href, name = (b, a) if self.CAT_NAME_FIRST else (a, b)
            u = self.absolute(href)
            name = common.clean(name)
            if u in seen or not name:
                continue
            seen.add(u)
            cats.append({'url': u, 'title': name, 'thumb': '', 'count': ''})
        return sorted(cats, key=lambda c: c['title'].lower())

    def search_url(self, query):
        return self.absolute(self.SEARCH.format(q=quote_plus(query)))

    def get_streams(self, url):
        page = self.fetch(url)
        headers = self.play_headers(url)
        streams = []
        m = re.search(r'"format":"mp4","videoUrl":"([^"]+)"', page)
        if m:
            media = self.fetch(self.absolute(m.group(1).replace('\\/', '/')), headers={'Referer': url}, json=True)
            for s in media if isinstance(media, list) else []:
                if isinstance(s, dict) and s.get('videoUrl'):
                    streams.append({'height': common.height_of(s.get('quality') or s.get('height')),
                                    'url': s['videoUrl'], 'type': 'mp4', 'headers': headers})
        info = {}
        t = re.search(r'<meta property="og:title" content="([^"]+)"', page)
        if t:
            info['title'] = common.clean(t.group(1))
        th = re.search(r'<meta property="og:image" content="([^"]+)"', page)
        if th:
            info['thumb'] = th.group(1)
        return common.sort_streams(streams), info


class YouPorn(AyloSite):
    ID = 'youporn'
    NAME = 'YouPorn'
    BASE_URL = 'https://www.youporn.com/'
    LESBIAN_MENU = [('Lesbičky', '/category/lesbian/')]
    LATEST = '/browse/time/'
    POPULAR = '/most_viewed/'
    CATEGORIES = '/categories/'
    CAT_RE = r'<a class="menu_elem_text" href="(/category/[^"]+/)"[^>]*>\s*<span>([^<]+)</span>'
    SEARCH = '/search/?query={q}'


class RedTube(AyloSite):
    ID = 'redtube'
    NAME = 'RedTube'
    BASE_URL = 'https://www.redtube.com/'
    LESBIAN_MENU = [('Lesbičky', '/redtube/lesbian')]
    LATEST = '/newest'
    POPULAR = '/mostviewed'
    CATEGORIES = '/categories'
    CAT_RE = r'aria-label="([^"]+)" href="(/redtube/[a-z0-9\-]+)"'
    CAT_NAME_FIRST = True
    SEARCH = '/?search={q}'


class Tube8(AyloSite):
    ID = 'tube8'
    NAME = 'Tube8'
    BASE_URL = 'https://www.tube8.com/'
    LESBIAN_MENU = [('Lesbičky', '/cat/lesbian/')]
    LATEST = '/newest.html'
    POPULAR = '/mostviewed.html'
    CATEGORIES = '/cat/lesbian/'  # samostatná stránka kategorií neexistuje, seznam je v menu výpisu
    SEARCH = '/searches.html/?q={q}'

    def get_categories(self, url):
        # název podle adresy (/cat/big-tits/ -> Big Tits), text odkazů se na webu špatně páruje
        page = self.fetch(url)
        slugs = sorted(set(re.findall(r'href="(?:https://www\.tube8\.com)?/cat/([a-z0-9\-]+)/"', page)))
        return [{'url': self.absolute('/cat/%s/' % s), 'title': s.replace('-', ' ').title(), 'thumb': '', 'count': ''}
                for s in slugs]


youporn = YouPorn()
redtube = RedTube()
tube8 = Tube8()
