# -*- coding: utf-8 -*-
"""Oblíbená videa s hodnocením 1-3 hvězdičky (napříč všemi weby)."""
import json
import os
import time

STAR_COLOR = 'gold'


def stars_label(n):
    """Hvězdičky pro popisek v Kodi: ★★☆ apod."""
    n = max(0, min(3, int(n or 0)))
    return '[COLOR %s]%s[/COLOR][COLOR gray]%s[/COLOR]' % (STAR_COLOR, '★' * n, '☆' * (3 - n))


class Favorites:
    def __init__(self, profile):
        self.path = os.path.join(profile, 'favorites.json')
        self.profile = profile

    def _load(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [i for i in data if isinstance(i, dict) and i.get('url')]
        except (OSError, ValueError):
            return []

    def _save(self, items):
        os.makedirs(self.profile, exist_ok=True)
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def all(self, stars=None):
        """Oblíbené seřazené: víc hvězdiček nahoře, v rámci stejných nejnovější nahoře."""
        items = self._load()
        if stars:
            items = [i for i in items if int(i.get('stars', 0)) == int(stars)]
        return sorted(items, key=lambda i: (-int(i.get('stars', 0)), -float(i.get('added', 0))))

    def stars_of(self, url):
        for i in self._load():
            if i['url'] == url:
                return int(i.get('stars', 0))
        return 0

    def stars_map(self):
        return {i['url']: int(i.get('stars', 0)) for i in self._load()}

    def counts(self):
        out = {1: 0, 2: 0, 3: 0}
        for i in self._load():
            s = int(i.get('stars', 0))
            if s in out:
                out[s] += 1
        return out

    def set(self, video, stars):
        """Přidá/změní hodnocení (1-3); 0 = odebrat."""
        items = [i for i in self._load() if i['url'] != video['url']]
        old = next((i for i in self._load() if i['url'] == video['url']), None)
        if stars:
            entry = {k: video.get(k) for k in ('site', 'url', 'title', 'thumb', 'duration', 'quality') if video.get(k)}
            entry['stars'] = int(stars)
            entry['added'] = old.get('added') if old else time.time()
            items.append(entry)
        self._save(items)
