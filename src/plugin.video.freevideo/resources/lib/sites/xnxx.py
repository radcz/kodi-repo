# -*- coding: utf-8 -*-
"""XNXX.com (podle modulu xnxx z Cumination, GPL-3.0)."""
import json
import re
from urllib.parse import quote

from resources.lib import common
from resources.lib.sites.xvideos import parse_xv_videos, xv_streams


class XNXX(common.Site):
    ID = 'xnxx'
    NAME = 'XNXX'
    BASE_URL = 'https://www.xnxx.com/'
    LANG = 'cs-CZ,cs;q=0.9,en;q=0.6'

    def menu(self, sub=None):
        return [
            ('Nejsledovanější', 'list', {'url': self.BASE_URL + 'hits'}),
            ('Nejlepší tento měsíc', 'list', {'url': self.BASE_URL + 'best'}),
            ('Výběr dne', 'list', {'url': self.BASE_URL + 'todays-selection'}),
            ('Kategorie', 'categories', {'url': self.BASE_URL}),
            ('Hledat', 'search', {}),
        ]

    def get_videos(self, url):
        page = self.fetch(url)
        nxt = None
        m = re.search(r'class="pagination[^"]*"(.*?)(?:</ul>|</div>)', page, re.S)
        if m:
            href = common.next_after_active(m.group(1))
            nxt = self.absolute(href) if href else None
        return parse_xv_videos(self, page), nxt, 0

    def get_categories(self, url):
        page = self.fetch(url)
        m = re.search(r'cats\.write_thumb_block_list\((\[.*?\])\s*[,)]', page, re.S)
        if not m:
            raise common.ScraperError('XNXX: seznam kategorií nenalezen.')
        try:
            items = json.loads(m.group(1))
        except ValueError:
            raise common.ScraperError('XNXX: neplatný seznam kategorií.')
        cats = []
        for it in items:
            if not it.get('u') or not it.get('tf'):
                continue
            cats.append({'url': self.absolute(it['u']), 'title': common.clean(it['tf']),
                         'thumb': it.get('i', ''), 'count': ''})
        return sorted(cats, key=lambda c: c['title'].lower())

    def search_url(self, query):
        return self.BASE_URL + 'search/' + quote(query.replace(' ', '+'), safe='+')

    def get_streams(self, url):
        return xv_streams(self, url)


site = XNXX()
