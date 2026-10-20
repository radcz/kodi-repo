# -*- coding: utf-8 -*-
"""Video FREE - doplněk pro Kodi 21 (FreeVideo.cz, YourLesbians, xHamster, Pornhub, xVideos, XNXX,
Eporner, YouPorn, RedTube, Tube8). Lesbické výpisy a kategorie jsou vždy nahoře."""
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
from resources.lib.downloader import Downloader, download_state
from resources.lib.favorites import Favorites, stars_label

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
LES = '[COLOR hotpink]%s[/COLOR]'


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


def favorites():
    return Favorites(PROFILE)


# --- obrazovky ---

def main_menu():
    total = sum(favorites().counts().values())
    add_dir('[COLOR gold][B]★ Oblíbené[/B][/COLOR]  [COLOR gray](%d)[/COLOR]' % total, {'action': 'fav_menu'}, thumb=ICON)
    add_dir(LES % '[B]Lesbičky – všechny weby[/B]', {'action': 'lesbian_all'}, thumb=ICON)
    for site in sites.SITES:
        add_dir(site.NAME, {'action': 'site', 'site': site.ID}, thumb=site_icon(site))
    folder = downloader().folder(ask=False)
    if folder:
        li = xbmcgui.ListItem('Stažená videa')
        li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
        xbmcplugin.addDirectoryItem(HANDLE, folder, li, isFolder=True)
    add_download_controls()
    end_dir()


def add_download_controls():
    """Pozastavit / Pokračovat / Zrušit podle stavu stahování."""
    state = download_state()
    queued = downloader().queued()
    if state == 'running':
        add_action('[COLOR yellow]Pozastavit stahování[/COLOR]  [COLOR gray](%d ve frontě)[/COLOR]' % queued,
                   {'action': 'download_pause'})
    elif state == 'paused':
        add_action('[COLOR lime]Pokračovat ve stahování[/COLOR]  [COLOR gray](pozastaveno, %d ve frontě)[/COLOR]'
                   % queued, {'action': 'download_resume'})
    elif queued:
        add_action('[COLOR lime]Pokračovat ve stahování[/COLOR]  [COLOR gray](%d ve frontě)[/COLOR]' % queued,
                   {'action': 'download_resume'})
    add_action('[COLOR gray]Zrušit stahování[/COLOR]', {'action': 'download_cancel'})


def lesbian_all():
    """Lesbické výpisy všech webů na jednom místě."""
    for site in sites.SITES:
        entries = site.lesbian_menu()
        if not entries:
            continue
        label, action, params = entries[0]
        add_dir(LES % site.NAME + '  [COLOR gray]%s[/COLOR]' % label,
                dict(params, action=action, site=site.ID), thumb=site_icon(site))
    end_dir()


def site_menu(site, sub=None):
    icon = site_icon(site)
    if sub is None:
        for label, action, params in site.lesbian_menu():
            add_dir(LES % label, dict(params, action=action, site=site.ID), thumb=icon)
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
    page_q = {'action': 'download_page', 'site': site.ID, 'url': url}
    if videos:
        add_action('[COLOR deepskyblue]Stáhnout celou stránku (%d videí)[/COLOR]' % len(videos), page_q)
        add_action('[COLOR deepskyblue]Stáhnout více videí z této stránky...[/COLOR]', multi_q)
    fav = favorites().stars_map()
    for v in videos:
        add_video_item(site.ID, v, fav.get(v['url'], 0), [
            ('Stáhnout více z této stránky...', 'RunPlugin(%s)' % build_url(**multi_q)),
            ('Stáhnout celou stránku', 'RunPlugin(%s)' % build_url(**page_q)),
        ])
    if next_url:
        nxt = page_no + 1
        label = '[B]Další >>[/B]  (strana %d%s)' % (nxt, ' z %d' % pages if pages else '')
        add_dir(label, {'action': 'list', 'site': site.ID, 'url': next_url, 'page': nxt})
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_DURATION)
    end_dir('videos', cache=False)


def add_video_item(site_id, v, stars=0, extra_ctx=None, show_site=False):
    """Jedno video ve výpisu (běžný výpis i oblíbené)."""
    label = v['title']
    if stars:
        label = stars_label(stars) + '  ' + label
    tags = [t for t in (v.get('quality'), 'CZ' if v.get('cz') else '') if t]
    if show_site:
        tags.insert(0, sites.get(site_id).NAME)
    if tags:
        label += '  [COLOR gray][%s][/COLOR]' % ', '.join(tags)
    li = xbmcgui.ListItem(label)
    thumb = v.get('thumb') or ''
    li.setArt({'thumb': thumb, 'icon': thumb, 'poster': thumb, 'fanart': thumb or FANART})
    tag = li.getVideoInfoTag()
    tag.setTitle(v['title'])
    tag.setMediaType('video')
    if v.get('duration'):
        tag.setDuration(int(v['duration']))
    if stars:
        tag.setUserRating(int(stars))
    li.setProperty('IsPlayable', 'true')
    fav_q = {'action': 'fav_set', 'site': site_id, 'url': v['url'], 'title': v['title'], 'thumb': thumb,
             'duration': v.get('duration') or 0, 'quality': v.get('quality') or ''}
    li.addContextMenuItems([
        ('[COLOR gold]Oblíbené – hvězdičky...[/COLOR]', 'RunPlugin(%s)' % build_url(**fav_q)),
        ('Přehrát ve vybrané kvalitě', 'PlayMedia(%s)' % build_url(action='play', site=site_id, url=v['url'], ask='1')),
        ('Stáhnout', 'RunPlugin(%s)' % build_url(action='download', site=site_id, url=v['url'], title=v['title'])),
    ] + (extra_ctx or []) + [
        ('Pozastavit / pokračovat ve stahování', 'RunPlugin(%s)' % build_url(action='download_toggle')),
        ('Zrušit stahování', 'RunPlugin(%s)' % build_url(action='download_cancel')),
    ])
    xbmcplugin.addDirectoryItem(HANDLE, build_url(action='play', site=site_id, url=v['url']), li, isFolder=False)


# --- oblíbené ---

def fav_menu():
    counts = favorites().counts()
    total = sum(counts.values())
    add_dir('[B]Všechny oblíbené[/B]  [COLOR gray](%d, nejlepší nahoře)[/COLOR]' % total,
            {'action': 'fav_list', 'stars': 0}, thumb=ICON)
    for n in (3, 2, 1):
        add_dir('%s  [COLOR gray](%d)[/COLOR]' % (stars_label(n), counts[n]), {'action': 'fav_list', 'stars': n},
                thumb=ICON)
    end_dir()


def fav_list(stars=0):
    items = favorites().all(int(stars) or None)
    if not items:
        notify('Zatím tu nic není. Video přidáte v kontextovém menu: Oblíbené – hvězdičky...',
               xbmcgui.NOTIFICATION_INFO)
    else:
        add_action('[COLOR deepskyblue]Stáhnout všechna tato videa (%d)[/COLOR]' % len(items),
                   {'action': 'fav_download', 'stars': stars})
    for v in items:
        add_video_item(v.get('site') or 'freevideo', v, v.get('stars', 0), show_site=True)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_VIDEO_USER_RATING)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_DURATION)
    end_dir('videos', cache=False)


def fav_set(params):
    fav = favorites()
    current = fav.stars_of(params['url'])
    options = ['%s  1 hvězdička' % stars_label(1), '%s  2 hvězdičky' % stars_label(2),
               '%s  3 hvězdičky' % stars_label(3)]
    if current:
        options.append('[COLOR red]Odebrat z oblíbených[/COLOR]')
    sel = xbmcgui.Dialog().select('Oblíbené: %s' % params.get('title', ''), options,
                                  preselect=current - 1 if current else -1)
    if sel < 0:
        return
    stars = 0 if sel == 3 else sel + 1
    video = {'site': params.get('site'), 'url': params['url'], 'title': params.get('title', ''),
             'thumb': params.get('thumb', ''), 'quality': params.get('quality', '')}
    try:
        video['duration'] = int(float(params.get('duration') or 0))
    except ValueError:
        pass
    fav.set(video, stars)
    notify(('Oblíbené: %s' % ('★' * stars)) if stars else 'Odebráno z oblíbených', xbmcgui.NOTIFICATION_INFO)
    xbmc.executebuiltin('Container.Refresh')


def fav_download(stars=0):
    items = favorites().all(int(stars) or None)
    if not items:
        return
    if not xbmcgui.Dialog().yesno(ADDON_NAME, 'Stáhnout všech %d oblíbených videí?' % len(items)):
        return
    downloader().enqueue([{'site': v.get('site') or 'freevideo', 'url': v['url'], 'title': v['title']}
                          for v in items])


def list_categories(site, url):
    try:
        lesbian, others = site.categories_with_lesbian_first(url)
    except common.ScraperError as exc:
        return fail_dir(str(exc))
    # lesbické kategorie vždy nahoře a zvýrazněné, ostatní pod nimi
    for c, les in [(c, True) for c in lesbian] + [(c, False) for c in others]:
        label = (LES % c['title'] if les else c['title']) + \
            ('  [COLOR gray](%s)[/COLOR]' % c['count'] if c['count'] else '')
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
    if site.LESBIAN_MENU and site.ID not in ('yourlesbians', 'lesbian8'):
        add_dir(LES % '[B]Hledat jen lesbické na %s...[/B]' % site.NAME, {'action': 'search', 'site': site.ID, 'les': '1'})
    add_dir('[B]Nové hledání na %s...[/B]' % site.NAME, {'action': 'search', 'site': site.ID})
    for q in load_history():
        li = xbmcgui.ListItem(q)
        li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
        li.addContextMenuItems([
            ('Smazat z historie', 'RunPlugin(%s)' % build_url(action='history_del', q=q)),
        ])
        xbmcplugin.addDirectoryItem(HANDLE, build_url(action='search', site=site.ID, q=q), li, isFolder=True)
    end_dir(cache=False)


def search(site, query=None, lesbian=False):
    if not query:
        heading = ('Hledat lesbická videa na %s' if lesbian else 'Hledat na %s') % site.NAME
        query = xbmcgui.Dialog().input(heading, type=xbmcgui.INPUT_ALPHANUM).strip()
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        if query:
            # výsledky pod vlastní URL s dotazem, aby se při návratu znovu neptal
            xbmc.executebuiltin('Container.Update(%s)' % build_url(action='search', site=site.ID, q=query,
                                                                    les='1' if lesbian else ''))
        return
    history = [q for q in load_history() if q.lower() != query.lower()]
    save_history([query] + history)
    if lesbian and not common.is_lesbian(query):
        query = '%s %s' % (query, site.LESBIAN_SEARCH)
    list_videos(site, site.search_url(query))


def history_delete(query):
    save_history([q for q in load_history() if q != query])
    xbmc.executebuiltin('Container.Refresh')


# --- stahování ---

def download_page(site, url):
    """Všechna videa ze stránky do fronty stahování (po jednom potvrzení)."""
    try:
        videos, _, _ = site.get_videos(url)
    except common.ScraperError as exc:
        notify(str(exc))
        return
    if not videos:
        notify('Na stránce nejsou žádná videa.', xbmcgui.NOTIFICATION_INFO)
        return
    rule = ''
    if downloader().quality_mode() == Downloader.EXACT_1080:
        rule = '\nStahují se jen videa v 1080p, ostatní se přeskočí.'
    if not xbmcgui.Dialog().yesno(ADDON_NAME, 'Stáhnout všech %d videí z této stránky?%s' % (len(videos), rule)):
        return
    downloader().enqueue([{'site': site.ID, 'url': v['url'], 'title': v['title']} for v in videos])


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
        search(site, params.get('q'), params.get('les') == '1')
    elif action == 'fav_menu':
        fav_menu()
    elif action == 'fav_list':
        fav_list(params.get('stars', 0))
    elif action == 'fav_set':
        fav_set(params)
    elif action == 'fav_download':
        fav_download(params.get('stars', 0))
    elif action == 'lesbian_all':
        lesbian_all()
    elif action == 'history_del':
        history_delete(params.get('q', ''))
    elif action == 'download':
        downloader().enqueue([{'site': site.ID, 'url': params['url'], 'title': params.get('title', '')}])
    elif action == 'download_multi':
        download_multi(site, params['url'])
    elif action == 'download_page':
        download_page(site, params['url'])
    elif action == 'download_cancel':
        downloader().cancel()
        xbmc.executebuiltin('Container.Refresh')
    elif action == 'download_pause':
        downloader().pause()
        xbmc.executebuiltin('Container.Refresh')
    elif action == 'download_resume':
        xbmc.executebuiltin('Container.Refresh')
        downloader().resume()
    elif action == 'download_toggle':
        if download_state() == 'running':
            downloader().pause()
        else:
            downloader().resume()
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
