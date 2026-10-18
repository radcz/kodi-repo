# -*- coding: utf-8 -*-
"""Video FREE - doplněk pro Kodi 21 (zdroj: freevideo.cz)."""
import json
import os
import sys
from urllib.parse import parse_qsl, urlencode, quote

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib import scraper
from resources.lib.downloader import Downloader

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
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


def add_dir(label, query, thumb=None, plot=''):
    li = xbmcgui.ListItem(label)
    li.setArt({'icon': thumb or ICON, 'thumb': thumb or ICON, 'fanart': FANART})
    if plot:
        li.getVideoInfoTag().setPlot(plot)
    xbmcplugin.addDirectoryItem(HANDLE, build_url(**query), li, isFolder=True)


def end_dir(content='', cache=True):
    if content:
        xbmcplugin.setContent(HANDLE, content)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=cache)


def fail_dir(msg):
    log(msg, xbmc.LOGWARNING)
    notify(msg)
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)


# --- obrazovky ---

def main_menu():
    add_dir('Nejnovější', {'action': 'list', 'url': scraper.newest_url()})
    add_dir('Nejnavštěvovanější', {'action': 'list', 'url': scraper.popular_url()})
    add_dir('Kategorie', {'action': 'categories', 'url': scraper.categories_url()})
    add_dir('Hledat', {'action': 'search_menu'})
    add_dir('Další sekce', {'action': 'sections'})
    folder = downloader().folder(ask=False)
    if folder:
        li = xbmcgui.ListItem('Stažená videa')
        li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
        xbmcplugin.addDirectoryItem(HANDLE, folder, li, isFolder=True)
    add_action('[COLOR gray]Zrušit stahování[/COLOR]', {'action': 'download_cancel'})
    end_dir()


def add_action(label, query):
    """Položka, která po kliknutí jen spustí akci (nic nepřehrává, neotevírá složku)."""
    li = xbmcgui.ListItem(label)
    li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
    xbmcplugin.addDirectoryItem(HANDLE, build_url(**query), li, isFolder=False)


def downloader():
    return Downloader(ADDON, PROFILE, log, notify)


def sections_menu():
    for name, path in scraper.SECTIONS[1:]:
        add_dir(name, {'action': 'section', 'path': path})
    end_dir()


def section_menu(path):
    add_dir('Nejnovější', {'action': 'list', 'url': scraper.newest_url(path)})
    add_dir('Nejnavštěvovanější', {'action': 'list', 'url': scraper.popular_url(path)})
    add_dir('Kategorie', {'action': 'categories', 'url': scraper.categories_url(path)})
    end_dir()


def list_videos(url, page_no=1):
    try:
        videos, next_url, pages = scraper.get_videos(url)
    except scraper.ScraperError as exc:
        return fail_dir(str(exc))
    log('Výpis %s: %d videí, další strana: %s' % (url, len(videos), bool(next_url)))
    if not videos:
        notify('Nic nenalezeno.', xbmcgui.NOTIFICATION_INFO)
    multi = 'RunPlugin(%s)' % build_url(action='download_multi', url=url)
    if videos:
        add_action('[COLOR deepskyblue]Stáhnout více videí z této stránky...[/COLOR]',
                   {'action': 'download_multi', 'url': url})
    for v in videos:
        label = v['title']
        tags = [t for t in (v['quality'], 'CZ' if v['cz'] else '') if t]
        if tags:
            label += '  [COLOR gray][%s][/COLOR]' % ', '.join(tags)
        li = xbmcgui.ListItem(label)
        li.setArt({'thumb': v['thumb'], 'icon': v['thumb'], 'poster': v['thumb'],
                   'fanart': v['thumb'] or FANART})
        tag = li.getVideoInfoTag()
        tag.setTitle(v['title'])
        tag.setMediaType('video')
        if v['duration']:
            tag.setDuration(v['duration'])
        li.setProperty('IsPlayable', 'true')
        li.addContextMenuItems([
            ('Přehrát ve vybrané kvalitě',
             'PlayMedia(%s)' % build_url(action='play', url=v['url'], ask='1')),
            ('Stáhnout', 'RunPlugin(%s)' % build_url(action='download', url=v['url'], title=v['title'])),
            ('Stáhnout více z této stránky...', multi),
        ])
        xbmcplugin.addDirectoryItem(HANDLE, build_url(action='play', url=v['url']), li, isFolder=False)
    if next_url:
        nxt = page_no + 1
        label = '[B]Další >>[/B]  (strana %d%s)' % (nxt, ' z %d' % pages if pages else '')
        add_dir(label, {'action': 'list', 'url': next_url, 'page': nxt})
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_DURATION)
    end_dir('videos', cache=False)


def list_categories(url):
    try:
        cats = scraper.get_categories(url)
    except scraper.ScraperError as exc:
        return fail_dir(str(exc))
    for c in cats:
        label = c['title'] + ('  [COLOR gray](%s)[/COLOR]' % c['count'] if c['count'] else '')
        add_dir(label, {'action': 'list', 'url': c['url']}, thumb=c['thumb'])
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


def search_menu():
    add_dir('[B]Nové hledání...[/B]', {'action': 'search'})
    for q in load_history():
        li = xbmcgui.ListItem(q)
        li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
        li.addContextMenuItems([
            ('Smazat z historie', 'RunPlugin(%s)' % build_url(action='history_del', q=q)),
        ])
        xbmcplugin.addDirectoryItem(HANDLE, build_url(action='search', q=q), li, isFolder=True)
    end_dir(cache=False)


def search(query=None):
    if not query:
        query = xbmcgui.Dialog().input('Hledat na FreeVideo.cz', type=xbmcgui.INPUT_ALPHANUM).strip()
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        if query:
            # výsledky pod vlastní URL s dotazem, aby se při návratu znovu neptal
            xbmc.executebuiltin('Container.Update(%s)' % build_url(action='search', q=query))
        return
    history = [q for q in load_history() if q.lower() != query.lower()]
    save_history([query] + history)
    list_videos(scraper.search_url(query))


def history_delete(query):
    save_history([q for q in load_history() if q != query])
    xbmc.executebuiltin('Container.Refresh')


# --- stahování ---

def download_multi(url):
    try:
        videos, _, _ = scraper.get_videos(url)
    except scraper.ScraperError as exc:
        notify(str(exc))
        return
    if not videos:
        return
    labels = []
    for v in videos:
        dur = '%d:%02d' % divmod(v['duration'], 60) if v['duration'] else ''
        labels.append('%s  [COLOR gray]%s[/COLOR]' % (v['title'], dur))
    chosen = xbmcgui.Dialog().multiselect('Vyber videa ke stažení', labels)
    if not chosen:
        return
    downloader().enqueue([{'url': videos[i]['url'], 'title': videos[i]['title']} for i in chosen])


# --- přehrávání ---

def play(url, ask=False):
    try:
        streams, info = scraper.get_streams(url)
    except scraper.ScraperError as exc:
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
        labels = ['%dp' % h if h else 'neznámá' for h, _ in streams]
        sel = xbmcgui.Dialog().select('Vyber kvalitu', labels)
        if sel < 0:
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
            return
        stream = streams[sel][1]
    else:
        stream = scraper.pick_stream(streams, QUALITY_VALUES[q_index])
    log('Přehrávám %s' % stream)
    path = stream + '|User-Agent=' + quote(scraper.USER_AGENT) + '&Referer=' + quote(scraper.BASE_URL + '/')
    li = xbmcgui.ListItem(info.get('title', ''), path=path)
    li.setMimeType('video/mp4')
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
    log('Akce: %s' % (params or 'hlavní menu'), xbmc.LOGDEBUG)
    if action is None:
        main_menu()
    elif action == 'list':
        list_videos(params['url'], int(params.get('page', 1)))
    elif action == 'categories':
        list_categories(params['url'])
    elif action == 'sections':
        sections_menu()
    elif action == 'section':
        section_menu(params['path'])
    elif action == 'search_menu':
        search_menu()
    elif action == 'search':
        search(params.get('q'))
    elif action == 'history_del':
        history_delete(params.get('q', ''))
    elif action == 'download':
        downloader().enqueue([{'url': params['url'], 'title': params.get('title', '')}])
    elif action == 'download_multi':
        download_multi(params['url'])
    elif action == 'download_cancel':
        downloader().cancel()
    elif action == 'play':
        play(params['url'], params.get('ask') == '1')
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
