# -*- coding: utf-8 -*-
"""Video FREE - doplněk pro Kodi 21 (FreeVideo.cz, xVideos, XNXX, xHamster, Pornhub, Eporner)."""
import json
import os
import sys
from urllib.parse import parse_qsl, urlencode, quote

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib import common, sites
from resources.lib.downloader import Downloader

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ICON = ADDON.getAddonInfo('icon')
FANART = ADDON.getAddonInfo('fanart')
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
HISTORY_FILE = os.path.join(PROFILE, 'search_history.json')

BASE = sys.argv[0]
HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 else -1

QUALITY_VALUES = [0, 2160, 1080, 720, 540]  # index nastavení -> max. výška (0 = nejvyšší)


def log(msg, level=xbmc.LOGINFO):
    xbmc.log('[%s] %s' % (ADDON_ID, msg), level)


def build_url(**query):
    return BASE + '?' + urlencode(query)


def notify(msg, icon=xbmcgui.NOTIFICATION_ERROR):
    xbmcgui.Dialog().notification(ADDON_NAME, msg, icon, 5000)


def site_icon(site):
    path = os.path.join(ADDON_PATH, 'resources', 'media', site.ID + '.png')
    return path if os.path.exists(path) else ICON


def add_dir(label, query, thumb=None, plot=''):
    li = xbmcgui.ListItem(label)
    li.setArt({'icon': thumb or ICON, 'thumb': thumb or ICON, 'fanart': FANART})
    if plot:
        li.getVideoInfoTag().setPlot(plot)
    xbmcplugin.addDirectoryItem(HANDLE, build_url(**query), li, isFolder=True)


def add_action(label, query, thumb=None):
    """Položka, která po kliknutí jen spustí akci (nic nepřehrává, neotevírá složku)."""
    li = xbmcgui.ListItem(label)
    li.setArt({'icon': thumb or ICON, 'thumb': thumb or ICON, 'fanart': FANART})
    xbmcplugin.addDirectoryItem(HANDLE, build_url(**query), li, isFolder=False)


def end_dir(content='', cache=True):
    if content:
        xbmcplugin.setContent(HANDLE, content)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=cache)


def fail_dir(msg):
    log(msg, xbmc.LOGWARNING)
    notify(msg)
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)


def downloader():
    return Downloader(ADDON, PROFILE, log, notify)


# --- obrazovky ---

def main_menu():
    for site in sites.SITES:
        add_dir(site.NAME, {'action': 'site', 'site': site.ID}, thumb=site_icon(site))
    folder = downloader().folder(ask=False)
    if folder:
        li = xbmcgui.ListItem('Stažená videa')
        li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
        xbmcplugin.addDirectoryItem(HANDLE, folder, li, isFolder=True)
    add_action('[COLOR gray]Zrušit stahování[/COLOR]', {'action': 'download_cancel'})
    end_dir()


def site_menu(site, sub=None):
    icon = site_icon(site)
    for label, action, params in site.menu(sub):
        if action == 'search':
            add_dir(label, {'action': 'search_menu', 'site': site.ID}, thumb=icon)
        elif action == 'menu':
            add_dir(label, dict(params, action='site', site=site.ID), thumb=icon)
        else:
            add_dir(label, dict(params, action=action, site=site.ID), thumb=icon)
    end_dir()


def list_videos(site, url, page_no=1):
    try:
        videos, next_url, pages = site.get_videos(url)
    except common.ScraperError as exc:
        return fail_dir(str(exc))
    log('Výpis %s: %d videí, další strana: %s' % (url, len(videos), bool(next_url)))
    if not videos:
        notify('Nic nenalezeno.', xbmcgui.NOTIFICATION_INFO)
    multi_q = {'action': 'download_multi', 'site': site.ID, 'url': url}
    if videos:
        add_action('[COLOR deepskyblue]Stáhnout více videí z této stránky...[/COLOR]', multi_q)
    for v in videos:
        label = v['title']
        tags = [t for t in (v.get('quality'), 'CZ' if v.get('cz') else '') if t]
        if tags:
            label += '  [COLOR gray][%s][/COLOR]' % ', '.join(tags)
        li = xbmcgui.ListItem(label)
        li.setArt({'thumb': v['thumb'], 'icon': v['thumb'], 'poster': v['thumb'],
                   'fanart': v['thumb'] or FANART})
        tag = li.getVideoInfoTag()
        tag.setTitle(v['title'])
        tag.setMediaType('video')
        if v.get('duration'):
            tag.setDuration(v['duration'])
        li.setProperty('IsPlayable', 'true')
        li.addContextMenuItems([
            ('Přehrát ve vybrané kvalitě',
             'PlayMedia(%s)' % build_url(action='play', site=site.ID, url=v['url'], ask='1')),
            ('Stáhnout', 'RunPlugin(%s)' % build_url(action='download', site=site.ID, url=v['url'],
                                                     title=v['title'])),
            ('Stáhnout více z této stránky...', 'RunPlugin(%s)' % build_url(**multi_q)),
        ])
        xbmcplugin.addDirectoryItem(HANDLE, build_url(action='play', site=site.ID, url=v['url']), li,
                                    isFolder=False)
    if next_url:
        nxt = page_no + 1
        label = '[B]Další >>[/B]  (strana %d%s)' % (nxt, ' z %d' % pages if pages else '')
        add_dir(label, {'action': 'list', 'site': site.ID, 'url': next_url, 'page': nxt})
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_DURATION)
    end_dir('videos', cache=False)


def list_categories(site, url):
    try:
        cats = site.get_categories(url)
    except common.ScraperError as exc:
        return fail_dir(str(exc))
    for c in cats:
        label = c['title'] + ('  [COLOR gray](%s)[/COLOR]' % c['count'] if c['count'] else '')
        add_dir(label, {'action': 'list', 'site': site.ID, 'url': c['url']}, thumb=c['thumb'] or site_icon(site))
    end_dir('files', cache=False)


# --- hledání ---

def load_history():
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [q for q in data if isinstance(q, str)]
    except (OSError, ValueError):
        return []


def save_history(items):
    try:
        os.makedirs(PROFILE, exist_ok=True)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(items[:20], f, ensure_ascii=False)
    except OSError as exc:
        log('Nelze uložit historii hledání: %s' % exc, xbmc.LOGWARNING)


def search_menu(site):
    add_dir('[B]Nové hledání na %s...[/B]' % site.NAME, {'action': 'search', 'site': site.ID})
    for q in load_history():
        li = xbmcgui.ListItem(q)
        li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
        li.addContextMenuItems([
            ('Smazat z historie', 'RunPlugin(%s)' % build_url(action='history_del', q=q)),
        ])
        xbmcplugin.addDirectoryItem(HANDLE, build_url(action='search', site=site.ID, q=q), li, isFolder=True)
    end_dir(cache=False)


def search(site, query=None):
    if not query:
        query = xbmcgui.Dialog().input('Hledat na %s' % site.NAME, type=xbmcgui.INPUT_ALPHANUM).strip()
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        if query:
            # výsledky pod vlastní URL s dotazem, aby se při návratu znovu neptal
            xbmc.executebuiltin('Container.Update(%s)' % build_url(action='search', site=site.ID, q=query))
        return
    history = [q for q in load_history() if q.lower() != query.lower()]
    save_history([query] + history)
    list_videos(site, site.search_url(query))


def history_delete(query):
    save_history([q for q in load_history() if q != query])
    xbmc.executebuiltin('Container.Refresh')


# --- stahování ---

def download_multi(site, url):
    try:
        videos, _, _ = site.get_videos(url)
    except common.ScraperError as exc:
        notify(str(exc))
        return
    if not videos:
        return
    labels = []
    for v in videos:
        dur = '%d:%02d' % divmod(v['duration'], 60) if v.get('duration') else ''
        labels.append('%s  [COLOR gray]%s[/COLOR]' % (v['title'], dur))
    chosen = xbmcgui.Dialog().multiselect('Vyber videa ke stažení', labels)
    if not chosen:
        return
    downloader().enqueue([{'site': site.ID, 'url': videos[i]['url'], 'title': videos[i]['title']}
                          for i in chosen])


# --- přehrávání ---

def kodi_path(stream):
    headers = stream.get('headers') or {}
    if not headers:
        return stream['url']
    return stream['url'] + '|' + '&'.join('%s=%s' % (k, quote(v, safe='')) for k, v in headers.items())


def play(site, url, ask=False):
    try:
        streams, info = site.get_streams(url)
    except common.ScraperError as exc:
        notify(str(exc))
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    if not streams:
        notify('Video nemá dostupný stream (možná bylo smazáno).')
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    try:
        q_index = int(ADDON.getSetting('quality') or 0)
    except ValueError:
        q_index = 0
    if ask or q_index >= len(QUALITY_VALUES):
        labels = ['%s  [COLOR gray]%s[/COLOR]' % ('%dp' % s['height'] if s['height'] else 'neznámá',
                                                  s['type'].upper()) for s in streams]
        sel = xbmcgui.Dialog().select('Vyber kvalitu', labels)
        if sel < 0:
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
            return
        stream = streams[sel]
    else:
        stream = common.pick_stream(streams, QUALITY_VALUES[q_index])
    log('Přehrávám %s (%dp, %s)' % (stream['url'], stream['height'], stream['type']))
    li = xbmcgui.ListItem(info.get('title', ''), path=kodi_path(stream))
    li.setMimeType('application/vnd.apple.mpegurl' if stream['type'] == 'hls' else 'video/mp4')
    li.setContentLookup(False)
    tag = li.getVideoInfoTag()
    tag.setTitle(info.get('title', ''))
    tag.setPlot(info.get('plot', ''))
    tag.setMediaType('video')
    if info.get('thumb'):
        li.setArt({'thumb': info['thumb'], 'fanart': info['thumb']})
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def router(paramstring):
    params = dict(parse_qsl(paramstring))
    action = params.get('action')
    site = sites.get(params.get('site'))  # starší odkazy bez 'site' patří FreeVideo.cz
    log('Akce: %s' % (params or 'hlavní menu'), xbmc.LOGDEBUG)
    if action is None:
        main_menu()
    elif action == 'site':
        site_menu(site, params.get('sub'))
    elif action == 'sections':  # zpětná kompatibilita 1.x
        site_menu(sites.get('freevideo'), 'sections')
    elif action == 'section':
        site_menu(sites.get('freevideo'), params.get('path'))
    elif action == 'list':
        list_videos(site, params['url'], int(params.get('page', 1)))
    elif action == 'categories':
        list_categories(site, params['url'])
    elif action == 'search_menu':
        search_menu(site)
    elif action == 'search':
        search(site, params.get('q'))
    elif action == 'history_del':
        history_delete(params.get('q', ''))
    elif action == 'download':
        downloader().enqueue([{'site': site.ID, 'url': params['url'], 'title': params.get('title', '')}])
    elif action == 'download_multi':
        download_multi(site, params['url'])
    elif action == 'download_cancel':
        downloader().cancel()
    elif action == 'play':
        play(site, params['url'], params.get('ask') == '1')
    else:
        log('Neznámá akce: %s' % action, xbmc.LOGWARNING)
        main_menu()


if __name__ == '__main__':
    try:
        router(sys.argv[2][1:] if len(sys.argv) > 2 else '')
    except Exception as exc:  # poslední záchrana, ať Kodi nezamrzne na výpisu
        import traceback
        log('Neočekávaná chyba: %s\n%s' % (exc, traceback.format_exc()), xbmc.LOGERROR)
        notify('Neočekávaná chyba: %s' % exc)
