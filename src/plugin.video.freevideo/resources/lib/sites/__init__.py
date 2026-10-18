# -*- coding: utf-8 -*-
"""Seznam podporovaných webů."""
from resources.lib.sites import freevideo, xvideos, xnxx, xhamster, pornhub, eporner

SITES = [freevideo.site, xvideos.site, xnxx.site, xhamster.site, pornhub.site, eporner.site]
BY_ID = {s.ID: s for s in SITES}


def get(site_id):
    return BY_ID.get(site_id or 'freevideo', freevideo.site)
