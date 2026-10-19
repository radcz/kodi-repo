# -*- coding: utf-8 -*-
"""radcz instalátor: z jednoho ZIPu nainstaluje repozitáře a doplňky.

1) rozbalí přibalené ZIPy repozitářů do složky doplňků Kodi a zapne je,
2) obnoví repozitáře,
3) z radcz Repository nainstaluje doplňky (Kodi samo doinstaluje knihovny).
"""
import json
import os
import zipfile

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
NAME = 'radcz instalátor'
PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
ZIPS = os.path.join(PATH, 'resources', 'zips')
DONE_FLAG = os.path.join(PROFILE, 'hotovo.txt')

# repozitáře z přibalených ZIPů (pořadí = pořadí instalace)
REPOS = ['repository.radek', 'repository.sosacRepo', 'repository.prehraj.to', 'repository.dobbelina',
         'repository.slyguy']
# doplňky, které se nainstalují z repozitářů (Kodi vybere nejvyšší verzi = verze z radcz Repository)
ADDONS = [('plugin.video.sosac-2', 'Sosac.TV'), ('plugin.video.prehrajto', 'Prehraj.to (česky)'),
          ('plugin.video.freevideo', 'Video FREE')]


def log(msg, level=xbmc.LOGINFO):
    xbmc.log('[%s] %s' % (ADDON_ID, msg), level)


def jsonrpc(method, **params):
    req = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(req)))
    except ValueError:
        return {}


def has_addon(addon_id):
    # System.HasAddon nejde: Kodi podmínky převádí na malá písmena (repository.sosacRepo by nenašel)
    res = jsonrpc('Addons.GetAddonDetails', addonid=addon_id, properties=['enabled'])
    return bool((res.get('result') or {}).get('addon'))


def addon_enabled(addon_id):
    res = jsonrpc('Addons.GetAddonDetails', addonid=addon_id, properties=['enabled'])
    return bool(((res.get('result') or {}).get('addon') or {}).get('enabled'))


def wait_for(cond, seconds, monitor, progress=None, pct=0, text=''):
    for _ in range(int(seconds * 2)):
        if cond():
            return True
        if progress:
            progress.update(pct, text)
        if monitor.waitForAbort(0.5):
            return False
    return cond()


def already_done():
    return os.path.exists(DONE_FLAG)


def mark_done():
    try:
        os.makedirs(PROFILE, exist_ok=True)
        with open(DONE_FLAG, 'w') as f:
            f.write('ok')
    except OSError as exc:
        log('Nelze uložit příznak dokončení: %s' % exc, xbmc.LOGWARNING)


def repo_zip(repo_id):
    for name in sorted(os.listdir(ZIPS)) if os.path.isdir(ZIPS) else []:
        if name.startswith(repo_id + '-') and name.endswith('.zip'):
            return os.path.join(ZIPS, name)
    return None


def extract_repo(repo_id):
    """Rozbalí ZIP repozitáře do special://home/addons (jen když tam ještě není)."""
    path = repo_zip(repo_id)
    if not path:
        log('ZIP repozitáře %s chybí' % repo_id, xbmc.LOGWARNING)
        return False
    dest = xbmcvfs.translatePath('special://home/addons')
    with zipfile.ZipFile(path) as zf:
        for member in zf.namelist():
            # bezpečnost: jen soubory uvnitř složky doplňku
            if not member.startswith(repo_id + '/') or '..' in member:
                continue
            zf.extract(member, dest)
    log('Rozbalen %s' % os.path.basename(path))
    return True


def run(ask=True, first_run=False):
    monitor = xbmc.Monitor()
    dialog = xbmcgui.Dialog()
    missing_repos = [r for r in REPOS if not has_addon(r) or not addon_enabled(r)]
    missing_addons = [(a, n) for a, n in ADDONS if not has_addon(a)]
    if not missing_repos and not missing_addons:
        if not first_run:
            dialog.ok(NAME, 'Všechno je už nainstalované:\nradcz Repository, Sosac.TV, Prehraj.to a Video FREE.')
        mark_done()
        return
    if ask:
        names = ', '.join(n for _, n in missing_addons) or 'jen repozitáře'
        if not dialog.yesno(NAME, 'Nainstalovat vše najednou?\n\nRepozitáře: radcz, Sosac, Prehraj.to, Dobbelina, '
                                  'SlyGuy (HBO Max)\nDoplňky: %s\n\nKodi se může u každého doplňku zeptat '
                                  '„Nainstalovat?“ - potvrďte Ano.' % names):
            mark_done()  # při dalším startu Kodi se znovu neptat; ručně jde spustit z Programů
            return

    progress = xbmcgui.DialogProgressBG()
    progress.create(NAME, 'Přidávám repozitáře...')
    report = []
    try:
        # 1) repozitáře
        new = [r for r in missing_repos if not has_addon(r)]
        for repo in new:
            extract_repo(repo)
        if new:
            xbmc.executebuiltin('UpdateLocalAddons')
            wait_for(lambda: all(has_addon(r) for r in new), 30, monitor, progress, 10, 'Načítám repozitáře...')
        for i, repo in enumerate(missing_repos):
            if has_addon(repo) and not addon_enabled(repo):
                jsonrpc('Addons.SetAddonEnabled', addonid=repo, enabled=True)
            ok = wait_for(lambda: addon_enabled(repo), 10, monitor, progress, 15 + i * 5, 'Zapínám %s...' % repo)
            report.append('%s %s' % ('[COLOR lime]OK[/COLOR]' if ok else '[COLOR red]CHYBA[/COLOR]', repo))
        # 2) obnovit obsah repozitářů
        progress.update(40, NAME, 'Načítám seznam doplňků z repozitářů...')
        xbmc.executebuiltin('UpdateAddonRepos')
        monitor.waitForAbort(8)
        # 3) doplňky z radcz Repository (Kodi doinstaluje i knihovny)
        for i, (addon_id, name) in enumerate(missing_addons):
            pct = 50 + i * 15
            progress.update(pct, NAME, 'Instaluji %s...' % name)
            xbmc.executebuiltin('InstallAddon(%s)' % addon_id, True)
            ok = wait_for(lambda: has_addon(addon_id), 180, monitor, progress, pct, 'Instaluji %s...' % name)
            report.append('%s %s' % ('[COLOR lime]OK[/COLOR]' if ok else '[COLOR red]NENAINSTALOVÁNO[/COLOR]', name))
            log('Instalace %s: %s' % (addon_id, 'OK' if ok else 'neúspěch'))
    finally:
        progress.close()
    mark_done()
    failed = [r for r in report if 'COLOR red' in r]
    msg = '\n'.join(report)
    if failed:
        msg += '\n\nCo se nenainstalovalo, zkuste znovu: Doplňky -> Programy -> radcz instalátor.'
    else:
        msg += '\n\nHotovo. Doporučuji restartovat Kodi.\nPřihlášení zadejte v nastavení Sosac.TV a Prehraj.to.'
    dialog.ok(NAME, msg)
