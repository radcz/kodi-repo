# -*- coding: utf-8 -*-
"""Stahování na pozadí s frontou (převzato z doplňku Video FREE).

Jeden stahovací proces najednou; další videa se řadí do fronty. Průběh je
v nenápadném okně vpravo nahoře, Kodi jde mezitím normálně používat.
"""
import json
import os
import re
import time

import requests
import xbmc
import xbmcgui
import xbmcvfs

CHUNK = 1024 * 1024
TIMEOUT = 20
WINDOW = xbmcgui.Window(10000)
PROP_RUNNING = 'plugin.video.prehrajto.dl_running'
PROP_CANCEL = 'plugin.video.prehrajto.dl_cancel'
PROP_PAUSE = 'plugin.video.prehrajto.dl_pause'


def download_state():
    """'running', 'paused' nebo '' (nic neběží)."""
    if WINDOW.getProperty(PROP_RUNNING) != '1':
        return ''
    return 'paused' if WINDOW.getProperty(PROP_PAUSE) == '1' else 'running'


class SkipVideo(Exception):
    """Video nesplňuje požadovanou kvalitu - přeskočí se (není to chyba)."""


class Downloader:
    """resolver(item) -> {'url', 'headers', 'cookies', 'ext', 'subtitle'}"""

    def __init__(self, addon, profile, log, notify, resolver, setting_id='download'):
        self.addon = addon
        self.profile = profile
        self.queue_file = os.path.join(profile, 'download_queue.json')
        self.log = log
        self.notify = notify
        self.resolver = resolver
        self.setting_id = setting_id

    def folder(self, ask=True):
        path = self.addon.getSetting(self.setting_id)
        if not path and ask:
            path = xbmcgui.Dialog().browse(3, 'Kam ukládat stažená videa?', 'files')
            if path:
                self.addon.setSetting(self.setting_id, path)
        return path

    # --- fronta ---

    def _load(self):
        try:
            with open(self.queue_file, 'r', encoding='utf-8') as f:
                return [i for i in json.load(f) if isinstance(i, dict) and i.get('url')]
        except (OSError, ValueError):
            return []

    def _save(self, items):
        os.makedirs(self.profile, exist_ok=True)
        with open(self.queue_file, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False)

    def enqueue(self, items):
        if not self.folder():
            self.notify('Není nastavena složka pro stahování.', xbmcgui.NOTIFICATION_ERROR)
            return
        queue = self._load()
        known = {i['url'] for i in queue}
        added = [i for i in items if i['url'] not in known]
        self._save(queue + added)
        if WINDOW.getProperty(PROP_RUNNING) == '1':
            self.notify('Přidáno do fronty stahování: %d' % len(added))
            return
        self.run()

    def queued(self):
        return len(self._load())

    def cancel(self):
        WINDOW.clearProperty(PROP_PAUSE)
        had_queue = bool(self._load())
        self._save([])
        if WINDOW.getProperty(PROP_RUNNING) == '1':
            WINDOW.setProperty(PROP_CANCEL, '1')
            self.notify('Stahování se ruší...')
        elif had_queue:
            self._cleanup_parts()
            self.notify('Fronta stahování zrušena.')
        else:
            self.notify('Nic se nestahuje.')

    def pause(self):
        if WINDOW.getProperty(PROP_RUNNING) != '1':
            self.notify('Nic se nestahuje.')
            return
        WINDOW.setProperty(PROP_PAUSE, '1')
        self.notify('Stahování pozastaveno.')

    def resume(self):
        WINDOW.clearProperty(PROP_PAUSE)
        if WINDOW.getProperty(PROP_RUNNING) == '1':
            self.notify('Stahování pokračuje.')
        elif self._load():
            self.run()  # např. po restartu Kodi: fronta zůstala, rozstažené soubory navážou
        else:
            self.notify('Fronta stahování je prázdná.')

    def _cleanup_parts(self):
        folder = self.folder(ask=False)
        if not folder or '://' in folder or not os.path.isdir(folder):
            return
        for name in os.listdir(folder):
            if name.endswith('.part'):
                try:
                    os.remove(os.path.join(folder, name))
                except OSError:
                    pass

    def _wait_if_paused(self, monitor, progress, heading, text, pct=0):
        """Čeká, dokud je stahování pozastavené. Vrací False, když se mezitím zrušilo."""
        while WINDOW.getProperty(PROP_PAUSE) == '1':
            if self._cancelled(monitor):
                return False
            progress.update(pct, heading + ' – POZASTAVENO', text)
            if monitor.waitForAbort(1):
                return False
        return not self._cancelled(monitor)

    def run(self):
        WINDOW.setProperty(PROP_RUNNING, '1')
        WINDOW.clearProperty(PROP_CANCEL)
        WINDOW.clearProperty(PROP_PAUSE)
        monitor = xbmc.Monitor()
        progress = xbmcgui.DialogProgressBG()
        progress.create('Prehraj.to', 'Připravuji stahování...')
        done = failed = skipped = 0
        try:
            while not monitor.abortRequested() and WINDOW.getProperty(PROP_CANCEL) != '1':
                queue = self._load()
                if not queue:
                    break
                item = queue[0]
                heading = 'Stahuji %d/%d' % (done + failed + skipped + 1, done + failed + skipped + len(queue))
                if not self._wait_if_paused(monitor, progress, heading, item.get('title', '')):
                    break
                try:
                    ok = self._download(item, progress, heading, monitor)
                    if monitor.abortRequested():
                        break  # Kodi se vypíná: položka zůstane ve frontě a po restartu se naváže
                    if ok:
                        done += 1
                    else:
                        failed += 1
                except SkipVideo as exc:
                    skipped += 1
                    self.log('Přeskakuji %s: %s' % (item.get('url'), exc))
                except Exception as exc:  # chyba jednoho videa nesmí zastavit frontu
                    failed += 1
                    self.log('Stahování selhalo (%s): %s' % (item.get('url'), exc), xbmc.LOGWARNING)
                    self.notify('Nepodařilo se stáhnout: %s' % item.get('title', ''), xbmcgui.NOTIFICATION_ERROR)
                self._save([i for i in self._load() if i['url'] != item['url']])
        finally:
            progress.close()
            WINDOW.clearProperty(PROP_RUNNING)
            WINDOW.clearProperty(PROP_PAUSE)
            cancelled = WINDOW.getProperty(PROP_CANCEL) == '1'
            WINDOW.clearProperty(PROP_CANCEL)
        if cancelled:
            self.notify('Stahování zrušeno. Staženo: %d' % done)
        elif done or failed or skipped:
            self.notify('Stahování dokončeno: %d OK%s%s' % (
                done, ', %d chyb' % failed if failed else '',
                ', %d přeskočeno (menší než 2K)' % skipped if skipped else ''))

    def _cancelled(self, monitor):
        return monitor.abortRequested() or WINDOW.getProperty(PROP_CANCEL) == '1'

    def _download(self, item, progress, heading, monitor):
        folder = self.folder(ask=False)
        if not folder:
            raise IOError('není nastavena složka pro stahování')
        progress.update(0, heading, item.get('title', ''))
        src = self.resolver(item)
        if not src or not src.get('url'):
            raise IOError('nenalezen odkaz ke stažení')
        title = item.get('title') or 'video'
        base = safe_filename(title) + (' [%s]' % src['label'] if src.get('label') else '')
        target = join_path(folder, base + '.' + (src.get('ext') or 'mp4'))
        if xbmcvfs.exists(target):
            self.log('Už staženo: %s' % target)
            return True
        if src.get('subtitle'):
            try:
                sub = requests.get(src['subtitle'], timeout=TIMEOUT, headers=src.get('headers'))
                sub.raise_for_status()
                f = xbmcvfs.File(join_path(folder, base + '.srt'), 'wb')
                f.write(bytearray(sub.content))
                f.close()
            except Exception as exc:
                self.log('Titulky se nepodařilo stáhnout: %s' % exc, xbmc.LOGWARNING)
        part = target + '.part'
        self.log('Stahuji %s -> %s' % (src['url'][:100], target))
        local = '://' not in part
        got = os.path.getsize(part) if local and os.path.exists(part) else 0
        if got:
            self.log('Navazuji na rozstažený soubor (%d B)' % got)
        f = open(part, 'ab' if got else 'wb') if local else xbmcvfs.File(part, 'wb')
        ok = False
        resp = None
        try:
            resp, got, size = self._open_range(src, f, got, local)
            last, start = 0, time.time()  # průběh ukázat hned po prvním bloku dat
            start_got = got
            while True:
                paused = False
                for chunk in resp.iter_content(CHUNK):
                    if self._cancelled(monitor):
                        return False
                    if WINDOW.getProperty(PROP_PAUSE) == '1':
                        paused = True
                        break
                    if not chunk:
                        continue
                    if local:
                        f.write(chunk)
                    elif not f.write(bytearray(chunk)):
                        raise IOError('nelze zapisovat do %s' % part)
                    got += len(chunk)
                    if time.time() - last > 1:
                        last = time.time()
                        pct = int(got * 100 / size) if size else 0
                        speed = (got - start_got) / max(time.time() - start, 0.1) / 1048576
                        progress.update(pct, heading, '%s  (%s / %s, %.1f MB/s)' % (
                            title, fmt_size(got), fmt_size(size) if size else '?', speed))
                if not paused:
                    break
                # pozastaveno: zavřít spojení, počkat, pak získat čerstvý odkaz a navázat
                resp.close()
                pct = int(got * 100 / size) if size else 0
                if not self._wait_if_paused(monitor, progress, heading, '%s  (%s / %s)' % (
                        title, fmt_size(got), fmt_size(size) if size else '?'), pct):
                    return False
                src = self.resolver(item) or src
                resp, got, size = self._open_range(src, f, got, local)
                start, start_got = time.time(), got
            if size and got < size:
                raise IOError('stahování přerušeno (%d z %d B)' % (got, size))
            ok = True
        finally:
            f.close()
            if resp is not None:
                resp.close()
            if not ok and not monitor.abortRequested():
                xbmcvfs.delete(part)
        if not xbmcvfs.rename(part, target):
            raise IOError('nelze přejmenovat %s' % part)
        return True

    def _open_range(self, src, f, got, local):
        """Otevře soubor od bajtu got; když server Range neumí, začne znovu od nuly."""
        headers = dict(src.get('headers') or {})
        if got:
            headers['Range'] = 'bytes=%d-' % got
        resp = requests.get(src['url'], stream=True, timeout=TIMEOUT, headers=headers, cookies=src.get('cookies'))
        resp.raise_for_status()
        if got and resp.status_code != 206:
            self.log('Server neumí navázat stahování, začínám znovu')
            if local:
                f.seek(0)
                f.truncate()
            got = 0
        length = int(resp.headers.get('Content-Length') or 0)
        return resp, got, (got + length if length else 0)


def fmt_size(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return ('%.0f %s' if unit in ('B', 'KB') else '%.1f %s') % (n, unit)
        n /= 1024.0


def safe_filename(title):
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '', title).strip(' .')
    return re.sub(r'\s+', ' ', name)[:150] or 'video'


def join_path(folder, name):
    sep = '\\' if ('\\' in folder and '/' not in folder) else '/'
    return folder.rstrip('/\\') + sep + name
