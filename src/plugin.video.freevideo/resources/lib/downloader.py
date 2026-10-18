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

    def max_height(self):
        values = [0, 2160, 1080, 720, 540]
        try:
            return values[int(self.addon.getSetting('download_quality') or 2)]
        except (ValueError, IndexError):
            return 1080

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

    def cancel(self):
        if WINDOW.getProperty(PROP_RUNNING) == '1':
            WINDOW.setProperty(PROP_CANCEL, '1')
            self._save([])
            self.notify('Stahování se ruší...', xbmcgui.NOTIFICATION_INFO)
        else:
            self._save([])
            self.notify('Nic se nestahuje.', xbmcgui.NOTIFICATION_INFO)

    def run(self):
        WINDOW.setProperty(PROP_RUNNING, '1')
        WINDOW.clearProperty(PROP_CANCEL)
        monitor = xbmc.Monitor()
        progress = xbmcgui.DialogProgressBG()
        progress.create('Video FREE', 'Připravuji stahování...')
        done = failed = 0
        try:
            while not monitor.abortRequested() and WINDOW.getProperty(PROP_CANCEL) != '1':
                queue = self._load()
                if not queue:
                    break
                item = queue[0]
                total = done + failed + len(queue)
                heading = 'Stahuji %d/%d' % (done + failed + 1, total)
                try:
                    if self._download(item, progress, heading, monitor):
                        done += 1
                    else:
                        failed += 1
                except Exception as exc:  # chyba jednoho videa nesmí zastavit frontu
                    failed += 1
                    self.log('Stahování selhalo (%s): %s' % (item.get('url'), exc), xbmc.LOGWARNING)
                    self.notify('Nepodařilo se stáhnout: %s' % item.get('title', ''))
                self._save([i for i in self._load() if i['url'] != item['url']])
        finally:
            progress.close()
            WINDOW.clearProperty(PROP_RUNNING)
            cancelled = WINDOW.getProperty(PROP_CANCEL) == '1'
            WINDOW.clearProperty(PROP_CANCEL)
        if cancelled:
            self.notify('Stahování zrušeno. Staženo: %d' % done, xbmcgui.NOTIFICATION_INFO)
        elif done or failed:
            self.notify('Stahování dokončeno: %d OK%s' % (done, ', %d chyb' % failed if failed else ''),
                        xbmcgui.NOTIFICATION_INFO)

    def _cancelled(self, monitor):
        return monitor.abortRequested() or WINDOW.getProperty(PROP_CANCEL) == '1'

    def _download(self, item, progress, heading, monitor):
        folder = self.folder(ask=False)
        if not folder:
            raise IOError('Není nastavena složka pro stahování')
        site = sites.get(item.get('site'))
        streams, info = site.get_streams(item['url'])
        stream = common.pick_stream(streams, self.max_height())
        if not stream:
            raise IOError('video nemá stream')
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
        f = xbmcvfs.File(part, 'wb')
        try:
            if hls:
                ok = self._write_hls(f, part, playlist, stream, progress, heading, title, monitor)
            else:
                ok = self._write_mp4(f, part, stream, progress, heading, title, monitor)
        finally:
            f.close()
            if not ok:
                xbmcvfs.delete(part)
        if not ok:
            return False
        if not xbmcvfs.rename(part, target):
            raise IOError('nelze přejmenovat %s' % part)
        return True

    def _write(self, f, part, data):
        if not f.write(bytearray(data)):
            raise IOError('nelze zapisovat do %s' % part)

    def _write_mp4(self, f, part, stream, progress, heading, title, monitor):
        resp = requests.get(stream['url'], stream=True, timeout=common.TIMEOUT, headers=stream.get('headers'))
        try:
            resp.raise_for_status()
            size = int(resp.headers.get('Content-Length') or 0)
            got = 0
            last = 0
            for chunk in resp.iter_content(CHUNK):
                if self._cancelled(monitor):
                    return False
                if not chunk:
                    continue
                self._write(f, part, chunk)
                got += len(chunk)
                if time.time() - last > 1:
                    last = time.time()
                    pct = int(got * 100 / size) if size else 0
                    progress.update(pct, heading, '%s  (%d / %d MB)' % (title, got >> 20, size >> 20))
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
        if playlist['init']:
            self._write(f, part, self._get(playlist['init'], headers))
        segs = playlist['segments']
        got = 0
        last = 0
        for i, seg in enumerate(segs):
            if self._cancelled(monitor):
                return False
            data = self._get(seg, headers)
            self._write(f, part, data)
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
