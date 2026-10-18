# -*- coding: utf-8 -*-
"""Seznam podporovaných webů (pořadí = pořadí v hlavním menu, čistě lesbické weby nahoře)."""
from resources.lib.sites import freevideo, xvideos, xnxx, xhamster, pornhub, eporner, aylo, kvs, tubes

SITES = [freevideo.site, kvs.yourlesbians, kvs.lesbian8, xhamster.site, pornhub.site, kvs.porntrex,
         xvideos.site, xnxx.site, eporner.site, aylo.youporn, aylo.redtube, aylo.tube8, tubes.youjizz, tubes.pornone]
BY_ID = {s.ID: s for s in SITES}


def get(site_id):
    return BY_ID.get(site_id or 'freevideo', freevideo.site)
