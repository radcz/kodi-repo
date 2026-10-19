# -*- coding: utf-8 -*-
"""Stahování videí (MP4 i HLS) na pozadí s jednoduchou frontou (jeden stahovací proces najednou)."""
import json
import os
import re
import time
from urllib.parse import urljoin

import requests
import xbmc
import xbmcgui
import xbmcvfs

from resources.lib import common, sites

CHUNK = 1024 * 1024
WINDOW = xbmcgui.Window(10000)
PROP_RUNNING = 'plugin.video.freevideo.dl_running'
PROP_CANCEL = 'plugin.video.freevideo.dl_cancel'
PROP_PAUSE = 'plugin.video.freevideo.dl_pause'


class PartFile:
    """Rozstažený soubor .part; lokální soubory umí pokračovat (append), síťové začnou znovu."""

    def __init__(self, path, resume=False):
        self.path = path
        self.local = '://' not in path
        self.resumed = bool(resume and self.local and os.path.exists(path))
        if self.local:
            self.f = open(path, 'ab' if self.resumed else 'wb')
        else:
            self.f = xbmcvfs.File(path, 'wb')

    def size(self):
        return os.path.getsize(self.path) if self.local and os.path.exists(self.path) else 0

    def truncate(self):
        if self.local:
            self.f.seek(0)
            self.f.truncate()

    def write(self, data):
        if self.local:
            self.f.write(data)
            return True
        return self.f.write(bytearray(data))

    def close(self):
        self.f.close()


def download_state():
    """'running', 'paused' nebo '' (nic neběží)."""
    if WINDOW.getProperty(PROP_RUNNING) != '1':
        return ''
    return 'paused' if WINDOW.getProperty(PROP_PAUSE) == '1' else 'running'


class SkipVideo(Exception):
    """Video nesplňuje požadovanou kvalitu - přeskočí se (není to chyba)."""


class Downloader:
    def __init__(self, addon, profile, log, notify):
        self.addon = addon
        self.queue_file = os.path.join(profile, 'download_queue.json')
        self.profile = profile
        self.log = log
        self.notify = notify

    # --- nastavení ---

    def folder(self, ask=True):
        # nastavení doplňku má přednost; záložní soubor pro případ, že Kodi
        # ještě nenačetlo nová nastavení (doplněk aktualizovaný bez restartu)
        path = self.addon.getSetting('download_path') or self._config().get('download_path', '')
        if not path and ask:
            path = xbmcgui.Dialog().browse(3, 'Kam ukládat stažená videa?', 'files')
            if path:
                try:
                    self.addon.setSetting('download_path', path)
                except Exception as exc:
                    self.log('Nelze uložit nastavení: %s' % exc, xbmc.LOGWARNING)
                self._save_config({'download_path': path})
        return path

    def _config(self):
        try:
            with open(os.path.join(self.profile, 'download.json'), 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_config(self, data):
        try:
            os.makedirs(self.profile, exist_ok=True)
            with open(os.path.join(self.profile, 'download.json'), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError as exc:
            self.log('Nelze uložit %s: %s' % ('download.json', exc), xbmc.LOGWARNING)

    EXACT_1080 = 5  # volba „Jen přesně 1080p (jiné přeskočit)“

    def quality_mode(self):
        try:
            return int(self.addon.getSetting('download_quality') or self.EXACT_1080)
        except ValueError:
            return self.EXACT_1080

    def max_height(self):
        values = [0, 2160, 1080, 720, 540]
        mode = self.quality_mode()
        return values[mode] if 0 <= mode < len(values) else 1080

    def choose_stream(self, streams):
        """Stream ke stažení; v režimu „jen 1080p“ vyhodí SkipVideo, když video 1080p nemá."""
        if self.quality_mode() == self.EXACT_1080:
            full_hd = [s for s in streams if 1000 <= s['height'] <= 1100]
            if not full_hd:
                have = ', '.join('%dp' % s['height'] for s in streams if s['height']) or 'neznámá'
                raise SkipVideo('není v 1080p (má %s)' % have)
            return full_hd[0]
        return common.pick_stream(streams, self.max_height())

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
        """items: seznam {'url', 'title'}; spustí zpracování fronty, pokud už neběží."""
        if not self.folder():
            self.notify('Není nastavena složka pro stahování.')
            return
        queue = self._load()
        known = {i['url'] for i in queue}
        added = [i for i in items if i['url'] not in known]
        self._save(queue + added)
        if WINDOW.getProperty(PROP_RUNNING) == '1':
            self.notify('Přidáno do fronty stahování: %d' % len(added), xbmcgui.NOTIFICATION_INFO)
            return
        self.run()

    def queued(self):
        return len(self._load())

    def cancel(self):
        WINDOW.clearProperty(PROP_PAUSE)
        if WINDOW.getProperty(PROP_RUNNING) == '1':
            WINDOW.setProperty(PROP_CANCEL, '1')
            self._save([])
            self.notify('Stahování se ruší...', xbmcgui.NOTIFICATION_INFO)
        elif self._load():
            self._cleanup_parts()
            self._save([])
            self.notify('Fronta stahování zrušena.', xbmcgui.NOTIFICATION_INFO)
        else:
            self.notify('Nic se nestahuje.', xbmcgui.NOTIFICATION_INFO)

    def pause(self):
        if WINDOW.getProperty(PROP_RUNNING) != '1':
            self.notify('Nic se nestahuje.', xbmcgui.NOTIFICATION_INFO)
            return
        WINDOW.setProperty(PROP_PAUSE, '1')
        self.notify('Stahování pozastaveno.', xbmcgui.NOTIFICATION_INFO)

    def resume(self):
        WINDOW.clearProperty(PROP_PAUSE)
        if WINDOW.getProperty(PROP_RUNNING) == '1':
            self.notify('Stahování pokračuje.', xbmcgui.NOTIFICATION_INFO)
        elif self._load():
            # např. po restartu Kodi: fronta zůstala uložená, rozstažené soubory navážou
            self.run()
        else:
            self.notify('Fronta stahování je prázdná.', xbmcgui.NOTIFICATION_INFO)

    def _cleanup_parts(self):
        folder = self.folder(ask=False)
        if not folder or '://' in folder or not os.path.isdir(folder):
            return
        for name in os.listdir(folder):
            if name.endswith('.part') or name.endswith('.part.idx'):
                try:
                    os.remove(os.path.join(folder, name))
                except OSError:
                    pass

    def _wait_if_paused(self, monitor, progress, heading, text, pct=0):
        """Čeká, dokud je stahování pozastavené. Vrací False, když se mezitím zrušilo."""
        if WINDOW.getProperty(PROP_PAUSE) != '1':
            return not self._cancelled(monitor)
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
        progress.create('Video FREE', 'Připravuji stahování...')
        done = failed = skipped = 0
        try:
            while not monitor.abortRequested() and WINDOW.getProperty(PROP_CANCEL) != '1':
                queue = self._load()
                if not queue:
                    break
                item = queue[0]
                total = done + failed + skipped + len(queue)
                heading = 'Stahuji %d/%d' % (done + failed + skipped + 1, total)
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
                    self.notify('Nepodařilo se stáhnout: %s' % item.get('title', ''))
                self._save([i for i in self._load() if i['url'] != item['url']])
        finally:
            progress.close()
            WINDOW.clearProperty(PROP_RUNNING)
            WINDOW.clearProperty(PROP_PAUSE)
            cancelled = WINDOW.getProperty(PROP_CANCEL) == '1'
            WINDOW.clearProperty(PROP_CANCEL)
        if cancelled:
            self.notify('Stahování zrušeno. Staženo: %d' % done, xbmcgui.NOTIFICATION_INFO)
        elif done or failed or skipped:
            self.notify('Stahování dokončeno: %d OK%s%s' % (
                done, ', %d chyb' % failed if failed else '',
                ', %d přeskočeno (není 1080p)' % skipped if skipped else ''), xbmcgui.NOTIFICATION_INFO)

    def _cancelled(self, monitor):
        return monitor.abortRequested() or WINDOW.getProperty(PROP_CANCEL) == '1'

    def _download(self, item, progress, heading, monitor):
        folder = self.folder(ask=False)
        if not folder:
            raise IOError('Není nastavena složka pro stahování')
        site = sites.get(item.get('site'))
        streams, info = site.get_streams(item['url'])
        if not streams:
            raise IOError('video nemá stream')
        stream = self.choose_stream(streams)
        title = item.get('title') or info.get('title') or 'video'
        hls = stream['type'] == 'hls'
        playlist = None
        if hls:
            playlist = self._media_playlist(site, stream)
        ext = '.mp4' if not hls or playlist['init'] else '.ts'
        name = safe_filename(title) + (' [%dp]' % stream['height'] if stream['height'] else '') + ext
        target = join_path(folder, name)
        if xbmcvfs.exists(target):
            self.log('Už staženo: %s' % target)
            return True
        part = target + '.part'
        progress.update(0, heading, title)
        self.log('Stahuji (%s, %dp) %s -> %s' % (stream['type'], stream['height'], stream['url'], target))
        ok = False
        f = PartFile(part, resume=True)
        if f.resumed:
            self.log('Navazuji na rozstažený soubor (%d B)' % f.size())
        try:
            if hls:
                ok = self._write_hls(f, part, playlist, stream, progress, heading, title, monitor)
            else:
                ok = self._write_mp4(f, part, stream, progress, heading, title, monitor)
        finally:
            f.close()
            if not ok and not monitor.abortRequested():
                xbmcvfs.delete(part)
                xbmcvfs.delete(part + '.idx')
        if not ok:
            return False
        xbmcvfs.delete(part + '.idx')
        if not xbmcvfs.rename(part, target):
            raise IOError('nelze přejmenovat %s' % part)
        return True

    def _write(self, f, part, data):
        if not f.write(data):
            raise IOError('nelze zapisovat do %s' % part)

    def _open_range(self, stream, f, got):
        """Otevře MP4 od bajtu got; když server Range neumí, začne znovu od nuly."""
        headers = dict(stream.get('headers') or {})
        if got:
            headers['Range'] = 'bytes=%d-' % got
        resp = requests.get(stream['url'], stream=True, timeout=common.TIMEOUT, headers=headers)
        resp.raise_for_status()
        if got and resp.status_code != 206:
            self.log('Server neumí navázat stahování, začínám znovu')
            f.truncate()
            got = 0
        length = int(resp.headers.get('Content-Length') or 0)
        size = got + length if length else 0
        return resp, got, size

    def _write_mp4(self, f, part, stream, progress, heading, title, monitor):
        got = f.size() if f.resumed else 0
        resp, got, size = self._open_range(stream, f, got)
        try:
            last = 0
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
                    self._write(f, part, chunk)
                    got += len(chunk)
                    if time.time() - last > 1:
                        last = time.time()
                        pct = int(got * 100 / size) if size else 0
                        progress.update(pct, heading, '%s  (%d / %d MB)' % (title, got >> 20, size >> 20))
                if not paused:
                    break
                # pozastaveno: spojení zavřít, počkat a pak navázat od staženého místa
                resp.close()
                pct = int(got * 100 / size) if size else 0
                if not self._wait_if_paused(monitor, progress, heading, '%s  (%d / %d MB)' % (
                        title, got >> 20, size >> 20), pct):
                    return False
                resp, got, size = self._open_range(stream, f, got)
            if size and got < size:
                raise IOError('stahování přerušeno (%d z %d B)' % (got, size))
            return True
        finally:
            resp.close()

    def _media_playlist(self, site, stream):
        """Načte media playlist HLS: seznam segmentů a případný inicializační segment."""
        text = site.fetch(stream['url'], headers=stream.get('headers'))
        if '#EXT-X-STREAM-INF' in text:  # ještě hlavní playlist -> vezmi nejlepší variantu
            variants = common.hls_variants(site, stream['url'], stream.get('headers'))
            stream = dict(stream, url=variants[0][1])
            text = site.fetch(stream['url'], headers=stream.get('headers'))
        for line in text.splitlines():
            if line.startswith('#EXT-X-KEY') and 'METHOD=NONE' not in line:
                raise IOError('video je šifrované, stáhnout ho nelze (přehrát ano)')
        init = None
        m = re.search(r'#EXT-X-MAP:.*?URI="([^"]+)"', text)
        if m:
            init = urljoin(stream['url'], m.group(1))
        segs = [urljoin(stream['url'], l.strip()) for l in text.splitlines()
                if l.strip() and not l.startswith('#')]
        if not segs:
            raise IOError('HLS playlist je prázdný')
        return {'init': init, 'segments': segs}

    def _get(self, url, headers, tries=3):
        for attempt in range(tries):
            try:
                r = requests.get(url, timeout=common.TIMEOUT, headers=headers)
                r.raise_for_status()
                return r.content
            except requests.RequestException:
                if attempt == tries - 1:
                    raise
                time.sleep(1 + attempt)

    def _write_hls(self, f, part, playlist, stream, progress, heading, title, monitor):
        headers = stream.get('headers')
        done_segs = 0
        if f.resumed:
            try:
                with open(part + '.idx', 'r') as idx:
                    done_segs = int(idx.read().strip() or 0)
            except (OSError, ValueError):
                f.truncate()
        if not done_segs:
            f.truncate()
            if playlist['init']:
                self._write(f, part, self._get(playlist['init'], headers))
        segs = playlist['segments']
        got = f.size()
        last = 0
        for i, seg in enumerate(segs):
            if i < done_segs:
                continue  # už staženo před pozastavením / restartem
            pct = int(i * 100 / len(segs))
            if not self._wait_if_paused(monitor, progress, heading, '%s  (%d / %d částí)' % (title, i, len(segs)), pct):
                return False
            data = self._get(seg, headers)
            self._write(f, part, data)
            if f.local:
                f.f.flush()
                with open(part + '.idx', 'w') as idx:
                    idx.write(str(i + 1))
            got += len(data)
            if time.time() - last > 1 or i == len(segs) - 1:
                last = time.time()
                progress.update(int((i + 1) * 100 / len(segs)), heading,
                                '%s  (%d / %d částí, %d MB)' % (title, i + 1, len(segs), got >> 20))
        return True


def safe_filename(title):
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '', title).strip(' .')
    return re.sub(r'\s+', ' ', name)[:120] or 'video'


def join_path(folder, name):
    sep = '\\' if ('\\' in folder and '/' not in folder) else '/'
    return folder.rstrip('/\\') + sep + name
