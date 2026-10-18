# -*- coding: utf-8 -*-
"""Seznam podporovaných webů (pořadí = pořadí v hlavním menu)."""
from resources.lib.sites import freevideo, xvideos, xnxx, xhamster, pornhub, eporner, aylo, yourlesbians

SITES = [freevideo.site, yourlesbians.site, xhamster.site, pornhub.site, xvideos.site, xnxx.site,
         eporner.site, aylo.youporn, aylo.redtube, aylo.tube8]
BY_ID = {s.ID: s for s in SITES}


def get(site_id):
    return BY_ID.get(site_id or 'freevideo', freevideo.site)
