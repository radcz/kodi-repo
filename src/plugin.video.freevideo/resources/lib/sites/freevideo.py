# -*- coding: utf-8 -*-
"""FreeVideo.cz - obal nad původním scraperem."""
from resources.lib import common, scraper


class FreeVideo(common.Site):
    ID = 'freevideo'
    NAME = 'FreeVideo.cz'
    BASE_URL = scraper.BASE_URL + '/'

    def menu(self, sub=None):
        if sub == 'sections':
            return [(name, 'menu', {'sub': path}) for name, path in scraper.SECTIONS[1:]]
        path = sub or '/vase-videa/'
        items = [
            ('Nejnovější', 'list', {'url': scraper.newest_url(path)}),
            ('Nejnavštěvovanější', 'list', {'url': scraper.popular_url(path)}),
            ('Kategorie', 'categories', {'url': scraper.categories_url(path)}),
        ]
        if sub is None:
            items += [('Hledat', 'search', {}), ('Další sekce', 'menu', {'sub': 'sections'})]
        return items

    def get_videos(self, url):
        try:
            return scraper.get_videos(url)
        except scraper.ScraperError as exc:
            raise common.ScraperError(str(exc))

    def get_categories(self, url):
        try:
            return scraper.get_categories(url)
        except scraper.ScraperError as exc:
            raise common.ScraperError(str(exc))

    def search_url(self, query):
        return scraper.search_url(query)

    def get_streams(self, url):
        try:
            streams, info = scraper.get_streams(url)
        except scraper.ScraperError as exc:
            raise common.ScraperError(str(exc))
        headers = {'User-Agent': scraper.USER_AGENT, 'Referer': scraper.BASE_URL + '/'}
        return [{'height': h, 'url': u, 'type': 'mp4', 'headers': headers} for h, u in streams], info


site = FreeVideo()
