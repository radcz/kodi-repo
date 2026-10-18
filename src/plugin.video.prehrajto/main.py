# -*- coding: utf-8 -*-
"""Prehraj.to pro Kodi - česká verze s úpravami (stahování na pozadí, výběr více videí, náhledy).

Původní doplněk: WrightDerby (plugin.video.prehrajto 2.0.5).
"""

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
import os
import json
import shutil
from urllib.parse import urlencode, quote, urlparse, parse_qsl, urljoin
from urllib.request import urlopen
import re
import datetime
from bs4 import BeautifulSoup
import requests
import unicodedata
import time
import hashlib
import hjson
import xbmcvfs

from resources.lib.downloader import Downloader


_url = sys.argv[0]
_handle = int(sys.argv[1]) if len(sys.argv) > 1 else -1

ADDON_ID = 'plugin.video.prehrajto'
addon = xbmcaddon.Addon(id=ADDON_ID)
ADDON_PATH = xbmcvfs.translatePath('special://home/addons/' + ADDON_ID)
# data ukládáme do addon_data (přežijí aktualizaci doplňku a nedostanou se do ZIPu)
PROFILE = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
ICON = os.path.join(ADDON_PATH, 'icon.png')

ls = addon.getSetting("ls") or "50"
history_path = os.path.join(PROFILE, 'history.txt')
subtitles_path = os.path.join(PROFILE, 'subtitles.txt')
cookie_cache_path = os.path.join(PROFILE, 'session.json')
resume_path = os.path.join(PROFILE, 'resume.json')

BASE_URL = 'https://prehraj.to'
TIMEOUT = 20
COOKIE_TTL = 6 * 3600  # uložené přihlášení platí 6 hodin

UPDATE_URL = 'http://kodi.crocody.com/version.json'
REGISTRATION_URL = 'https://shorturl.at/3kTcF'
TMDB = 'https://api.themoviedb.org/3/{}?api_key=1f0150a5f78d4adc2407911989fdb66c&language=cs-CZ{}'

gid = {
    28: "Akční", 12: "Dobrodružný", 16: "Animovaný", 35: "Komedie",
    80: "Krimi", 99: "Dokumentární", 18: "Drama", 10751: "Rodinný",
    14: "Fantasy", 36: "Historický", 27: "Horor", 10402: "Hudební",
    9648: "Mysteriózní", 10749: "Romantický", 878: "Sci-fi",
    10770: "Televizní film", 53: "Thriller", 10752: "Válečný", 37: "Western",
    10759: "Akční a dobrodružný", 10762: "Pro děti", 10763: "Zprávy",
    10764: "Reality", 10765: "Sci-fi a fantasy", 10766: "Telenovela",
    10767: "Talk show", 10768: "Válka a politika",
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'cs,sk;q=0.9,en;q=0.8',
}


# ---------------------------------------------------------------------------
# Pomocné funkce
# ---------------------------------------------------------------------------

def log(msg, level=xbmc.LOGINFO):
    xbmc.log('[{}] {}'.format(ADDON_ID, msg), level)


def notify(msg, icon=xbmcgui.NOTIFICATION_INFO, time_ms=4000, sound=False):
    xbmcgui.Dialog().notification('Prehraj.to', msg, icon, time_ms, sound=sound)


def notify_error(msg):
    notify(msg, icon=xbmcgui.NOTIFICATION_ERROR, time_ms=5000)


def migrate_old_data():
    """Starší verze ukládaly data do složky doplňku - přesuneme je do addon_data."""
    old_dir = os.path.join(ADDON_PATH, 'resources')
    for name in ('history.txt', 'session.json', 'resume.json', 'subtitles.txt'):
        old, new = os.path.join(old_dir, name), os.path.join(PROFILE, name)
        try:
            if os.path.exists(old):
                os.makedirs(PROFILE, exist_ok=True)
                if not os.path.exists(new):
                    shutil.move(old, new)
                else:
                    os.remove(old)
        except Exception as e:
            log('Přesun {} se nepovedl: {}'.format(name, e), xbmc.LOGWARNING)


def _version_tuple(v):
    try:
        return tuple(int(x) for x in v.strip().split('.'))
    except Exception:
        return (0,)


def check_for_update():
    """Jen upozorní, že autor původního doplňku vydal novější verzi (max. 1x denně)."""
    stamp = os.path.join(PROFILE, 'update_check.txt')
    try:
        if os.path.exists(stamp) and time.time() - os.path.getmtime(stamp) < 86400:
            return
        os.makedirs(PROFILE, exist_ok=True)
        open(stamp, 'w').close()
        data = requests.get(UPDATE_URL, timeout=8).json()
        remote = data.get('version', '0')
        current = addon.getAddonInfo('version')
        log('Kontrola aktualizace originálu: tato={}, server={}'.format(current, remote))
        if _version_tuple(remote) > _version_tuple(current)[:len(_version_tuple(remote))]:
            notify('Autor vydal novou verzi originálu {} (slovensky)'.format(remote), time_ms=6000)
    except Exception as e:
        log('Kontrola aktualizace selhala (nevadí): {}'.format(e), xbmc.LOGDEBUG)


def encode(string):
    line = unicodedata.normalize('NFKD', string)
    return ''.join(c for c in line if not unicodedata.combining(c))


def safe_request_get(url, cookies=None, allow_redirects=True, headers=None):
    """requests.get s časovým limitem a srozumitelnými chybami."""
    h = dict(HEADERS)
    if headers:
        h.update(headers)
    try:
        resp = requests.get(url, cookies=cookies, headers=h, allow_redirects=allow_redirects, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp
    except requests.exceptions.Timeout:
        log('Vypršel časový limit: {}'.format(url), xbmc.LOGERROR)
        raise
    except requests.exceptions.ConnectionError as e:
        log('Chyba připojení: {} - {}'.format(url, e), xbmc.LOGERROR)
        raise
    except requests.exceptions.HTTPError as e:
        log('HTTP chyba: {} - {}'.format(url, e), xbmc.LOGERROR)
        raise


def get_url(**kwargs):
    return '{0}?{1}'.format(_url, urlencode(kwargs))


def convert_size(number_of_bytes):
    if number_of_bytes < 0:
        return '0 B'
    step = 1024.0
    number_of_bytes = float(number_of_bytes)
    unit = 'B'
    for u in ['KB', 'MB', 'GB', 'TB']:
        if number_of_bytes / step >= 1:
            number_of_bytes /= step
            unit = u
        else:
            break
    return '{:.1f} {}'.format(number_of_bytes, unit)


def set_video_info(list_item, **info):
    """Kodi 20+: InfoTagVideo místo zastaralého setInfo."""
    tag = list_item.getVideoInfoTag()
    if info.get('title'):
        tag.setTitle(info['title'])
    tag.setMediaType(info.get('mediatype', 'video'))
    if info.get('plot'):
        tag.setPlot(info['plot'])
    if info.get('year'):
        try:
            tag.setYear(int(info['year']))
        except ValueError:
            pass
    if info.get('genre'):
        tag.setGenres([g.strip() for g in info['genre'].split('/') if g.strip()])
    if info.get('rating'):
        try:
            tag.setRating(float(info['rating']))
        except ValueError:
            pass
    if info.get('duration'):
        tag.setDuration(int(info['duration']))


def _duration_seconds(text):
    secs = 0
    for p in (text or '').strip().split(':'):
        if p.isdigit():
            secs = secs * 60 + int(p)
    return secs


# ---------------------------------------------------------------------------
# Přihlášení a Premium
# ---------------------------------------------------------------------------

def _cred_fingerprint(email, password):
    """Otisk údajů - při změně e-mailu/hesla se uložené přihlášení zahodí."""
    return hashlib.md5((email + ':' + password).encode('utf-8')).hexdigest()


def load_cached_session(email, password):
    try:
        if not os.path.exists(cookie_cache_path):
            return None
        with open(cookie_cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get('cred') != _cred_fingerprint(email, password):
            return None
        if time.time() - data.get('timestamp', 0) > COOKIE_TTL:
            return None
        cookies = requests.utils.cookiejar_from_dict(data.get('cookies', {}))
        return {'cookies': cookies, 'status_text': data.get('status_text', '')}
    except Exception as e:
        log('Nepodařilo se načíst uložené přihlášení: {}'.format(e), xbmc.LOGDEBUG)
        return None


def save_cached_session(email, password, cookies, status_text):
    try:
        os.makedirs(os.path.dirname(cookie_cache_path), exist_ok=True)
        data = {
            'cred': _cred_fingerprint(email, password),
            'timestamp': time.time(),
            'cookies': requests.utils.dict_from_cookiejar(cookies),
            'status_text': status_text,
        }
        with open(cookie_cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception as e:
        log('Nepodařilo se uložit přihlášení: {}'.format(e), xbmc.LOGWARNING)


def clear_cached_session():
    try:
        if os.path.exists(cookie_cache_path):
            os.remove(cookie_cache_path)
    except Exception:
        pass


def _parse_account_soup(soup):
    """Ze stránky prehraj.to zjistí (přihlášen, premium, text o zbývající době)."""
    logged_in = False
    for a in soup.find_all('a'):
        href = (a.get('href') or '').lower()
        txt = (a.get_text() or '').lower()
        if 'logout' in href or 'odhlas' in href or 'odhlás' in txt or 'odhlas' in txt:
            logged_in = True
            break
    premium = False
    status_text = ''
    links_bar = soup.find('ul', {'class': 'header__links'})
    if links_bar:
        green = links_bar.find('span', {'class': 'color-green'})
        if green:
            premium = True
            logged_in = True
            status_text = green.get_text(strip=True)
    return logged_in, premium, status_text


def fetch_account_status():
    """Přihlásí se uloženými údaji. Vrací dict logged_in/premium/status_text/cookies."""
    email = addon.getSetting('email')
    password = addon.getSetting('password')
    login_headers = {'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json'}
    login_data = {
        'password': password,
        'email': email,
        'remember_login': 'on',
        'login': 'Prihlásiť sa',  # hodnota tlačítka formuláře na webu, neměnit
        '_do': 'loginDialog-login-loginForm-submit',
    }
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(BASE_URL + '/', timeout=TIMEOUT)
    session.post(BASE_URL + '/?frm=loginDialog-login-loginForm', data=login_data, headers=login_headers,
                 timeout=TIMEOUT)
    res = session.post(BASE_URL + '/', timeout=TIMEOUT)
    soup = BeautifulSoup(res.content, 'html.parser')
    logged_in, premium, status_text = _parse_account_soup(soup)
    return {'logged_in': logged_in, 'premium': premium, 'status_text': status_text, 'cookies': session.cookies}


def check_premium_with_cookies(cookies):
    res = requests.get(BASE_URL + '/', cookies=cookies, headers=HEADERS, timeout=TIMEOUT)
    soup = BeautifulSoup(res.content, 'html.parser')
    logged_in, premium, status_text = _parse_account_soup(soup)
    return {'logged_in': logged_in, 'premium': premium, 'status_text': status_text, 'cookies': cookies}


def get_premium(quiet=False):
    email = addon.getSetting("email")
    if not email:
        return 0, None
    password = addon.getSetting('password')
    if not password:
        notify_error('Premium: není nastavené heslo')
        return 0, None

    # 1) uložené cookies ověříme jedním rychlým požadavkem
    cached = load_cached_session(email, password)
    if cached:
        try:
            status = check_premium_with_cookies(cached['cookies'])
            if status['premium']:
                log('Premium ověřeno přes uložené přihlášení')
                save_cached_session(email, password, cached['cookies'], status['status_text'])
                return 1, cached['cookies']
            elif status['logged_in']:
                clear_cached_session()
                notify('Premium účet vypršel')
                return 0, cached['cookies']
            clear_cached_session()
        except Exception as e:
            log('Ověření Premium přes cookies selhalo, používám uložené: {}'.format(e), xbmc.LOGWARNING)
            return 1, cached['cookies']

    # 2) plné přihlášení
    try:
        status = fetch_account_status()
        if status['premium']:
            save_cached_session(email, password, status['cookies'], status['status_text'])
            if not quiet:
                notify('Premium: ' + (status['status_text'] or 'aktivní'))
            return 1, status['cookies']
        clear_cached_session()
        notify('Premium účet není aktivní')
        return 0, status['cookies']
    except Exception as e:
        log('Chyba přihlášení Premium: {}'.format(e), xbmc.LOGERROR)
        notify_error('Chyba přihlášení: ' + str(e))
        return 0, None


def test_login():
    """Volá se z nastavení („Otestovat přihlášení“)."""
    email = addon.getSetting('email')
    password = addon.getSetting('password')
    if not email or not password:
        xbmcgui.Dialog().ok('Prehraj.to – test přihlášení', 'Nejdřív zadejte e-mail a heslo v nastavení.')
        return
    clear_cached_session()
    progress = xbmcgui.DialogProgress()
    progress.create('Prehraj.to', 'Ověřuji přihlášení...')
    try:
        status = fetch_account_status()
    except Exception as e:
        progress.close()
        log('Test přihlášení selhal: {}'.format(e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Prehraj.to – test přihlášení', 'Chyba připojení k prehraj.to:\n' + str(e))
        return
    progress.close()
    if status['premium']:
        save_cached_session(email, password, status['cookies'], status['status_text'])
        xbmcgui.Dialog().ok('Prehraj.to – test přihlášení',
                            'Úspěšně přihlášen jako:\n{}\n\nPREMIUM je AKTIVNÍ.\nZbývá: {}'.format(
                                email, status['status_text'] or 'aktivní'))
    elif status['logged_in']:
        xbmcgui.Dialog().ok('Prehraj.to – test přihlášení',
                            'Přihlášen jako:\n{}\n\nPREMIUM není aktivní.\n'
                            'Předplatné si můžete pořídit na:\n{}'.format(email, REGISTRATION_URL))
    else:
        xbmcgui.Dialog().ok('Prehraj.to – test přihlášení', 'Přihlášení SELHALO.\nZkontrolujte e-mail a heslo.')


def prompt_registration():
    msg = ('Pro přehrávání videí je potřeba PREMIUM účet na prehraj.to.\n'
           'Přihlašovací údaje zadejte v nastavení doplňku.\n\n'
           'Nemáte účet? Registrace:\n' + REGISTRATION_URL)
    xbmcgui.Dialog().ok('Prehraj.to – vyžaduje PREMIUM', msg)


def ensure_premium(quiet=False):
    if not addon.getSetting('email'):
        prompt_registration()
        return False, None
    premium, cookies = get_premium(quiet)
    if premium != 1:
        prompt_registration()
        return False, None
    return True, cookies


# ---------------------------------------------------------------------------
# Získání odkazu na video
# ---------------------------------------------------------------------------

def _extract_video_url_from_script(script_text):
    strategies = [
        re.compile(r'file\s*:\s*["\']([^"\']+\.(?:mp4|mkv|avi|m3u8|ts)[^"\']*)["\']', re.IGNORECASE),
        re.compile(r'src\s*:\s*["\']([^"\']+\.(?:mp4|mkv|avi|m3u8|ts)[^"\']*)["\']', re.IGNORECASE),
        re.compile(r'"file"\s*:\s*"([^"]+\.(?:mp4|mkv|avi|m3u8|ts)[^"]*)"', re.IGNORECASE),
        re.compile(r'<source[^>]+src=["\']([^"\']+\.(?:mp4|mkv|avi|m3u8|ts)[^"\']*)["\']', re.IGNORECASE),
        re.compile(r'["\']?(https?://[^"\'>\s]+\.(?:mp4|mkv|avi|m3u8|ts)(?:\?[^"\'>\s]*)?)["\']?', re.IGNORECASE),
    ]
    for pattern in strategies:
        matches = pattern.findall(script_text)
        if matches:
            return matches[-1]  # poslední bývá nejvyšší kvalita
    return None


def _extract_subtitle_url_from_script(script_text):
    try:
        match = re.search(r'var\s+tracks\s*=\s*(\[.*?\])\s*;', script_text, re.DOTALL)
        if match:
            parsed = json.loads(json.dumps(hjson.loads(match.group(1))))
            if parsed and isinstance(parsed, list) and 'src' in parsed[0]:
                return parsed[0]['src']
    except Exception as e:
        log('Nepodařilo se získat titulky: {}'.format(e), xbmc.LOGDEBUG)
    return ''


def get_link(html_content):
    """Z HTML stránky videa vrátí (URL videa, URL titulků). ValueError, když video chybí."""
    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8', errors='replace')
    soup = BeautifulSoup(html_content, 'html.parser')
    file1 = None
    file2 = ''
    sources_pattern = re.compile(r'var\s+sources\s*=\s*\[', re.DOTALL)
    for script_tag in soup.find_all('script'):
        script_text = script_tag.string or ''
        if sources_pattern.search(script_text):
            file1 = _extract_video_url_from_script(script_text)
            if file1:
                break
    if not file1:
        for script_tag in soup.find_all('script'):
            file1 = _extract_video_url_from_script(script_tag.string or '')
            if file1:
                break
    if not file1:
        video_tag = soup.find('video')
        if video_tag:
            file1 = video_tag.get('src') or ''
            if not file1 and video_tag.find('source'):
                file1 = video_tag.find('source').get('src', '')
    if not file1:
        log('Na stránce chybí odkaz na video. Začátek HTML: {}'.format(html_content[:300]), xbmc.LOGERROR)
        raise ValueError('Odkaz na video nebyl na stránce prehraj.to nalezen')
    for script_tag in soup.find_all('script'):
        script_text = script_tag.string or ''
        if 'var tracks' in script_text:
            file2 = _extract_subtitle_url_from_script(script_text)
            if file2:
                break
    try:
        os.makedirs(os.path.dirname(subtitles_path), exist_ok=True)
        with open(subtitles_path, 'w', encoding='utf-8') as f:
            f.write(file2)
    except Exception as e:
        log('Nelze zapsat titulky: {}'.format(e), xbmc.LOGWARNING)
    return file1, file2


def premium_file_url(page_url, cookies, fallback):
    """Premium: přímý odkaz ?do=download (původní kvalita, bez omezení rychlosti)."""
    try:
        res = requests.get(page_url + '?do=download', cookies=cookies, headers=HEADERS,
                           allow_redirects=False, timeout=TIMEOUT)
        location = res.headers.get('Location')
        if location:
            return urljoin(BASE_URL, location)
        log('Přímý Premium odkaz nenalezen, používám stream', xbmc.LOGWARNING)
    except Exception as e:
        log('Chyba získání Premium odkazu: {}'.format(e), xbmc.LOGWARNING)
    return fallback


def _make_listitem_with_sub(file_url, sub_url):
    listitem = xbmcgui.ListItem(path=file_url)
    if sub_url:
        listitem.setSubtitles([sub_url])
    return listitem


# ---------------------------------------------------------------------------
# Pokračování v přehrávání (pozice podle stabilního ID videa)
# ---------------------------------------------------------------------------

RESUME_MIN_SEC = 30
RESUME_END_MARGIN = 60


def _resume_id(link):
    return urlparse(link).path.strip('/')


def _load_resume_db():
    try:
        if os.path.exists(resume_path):
            with open(resume_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log('Nelze načíst pozice přehrávání: {}'.format(e), xbmc.LOGDEBUG)
    return {}


def _save_resume_db(db):
    try:
        os.makedirs(os.path.dirname(resume_path), exist_ok=True)
        with open(resume_path, 'w', encoding='utf-8') as f:
            json.dump(db, f)
    except Exception as e:
        log('Nelze uložit pozice přehrávání: {}'.format(e), xbmc.LOGWARNING)


def get_resume_point(link):
    entry = _load_resume_db().get(_resume_id(link))
    if entry:
        return float(entry.get('position', 0)), float(entry.get('total', 0))
    return 0.0, 0.0


def set_resume_point(link, position, total):
    db = _load_resume_db()
    vid = _resume_id(link)
    if total > 0 and position >= total - RESUME_END_MARGIN:
        db.pop(vid, None)
    elif position >= RESUME_MIN_SEC:
        db[vid] = {'position': round(position, 1), 'total': round(total, 1)}
    if len(db) > 200:
        db = dict(list(db.items())[-200:])
    _save_resume_db(db)


def _monitor_playback(link):
    player = xbmc.Player()
    monitor = xbmc.Monitor()
    waited = 0
    while not player.isPlaying():
        if monitor.waitForAbort(1) or waited >= 15:
            return
        waited += 1
    last_pos, total = 0.0, 0.0
    while player.isPlaying():
        try:
            last_pos = player.getTime()
            total = player.getTotalTime()
        except Exception:
            break
        if total > 0:
            set_resume_point(link, last_pos, total)
        if monitor.waitForAbort(5):
            break
    if total > 0:
        set_resume_point(link, last_pos, total)


def _fmt_time(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return '{}:{:02d}:{:02d}'.format(h, m, s) if h else '{}:{:02d}'.format(m, s)


def play_video_premium(link, cookies):
    clean_link = BASE_URL + urlparse(link).path
    log('Premium přehrávání: {}'.format(clean_link))
    try:
        file, sub = get_link(safe_request_get(clean_link, cookies=cookies).content)
        file = premium_file_url(clean_link, cookies, file)
        listitem = _make_listitem_with_sub(file, sub)
        position, total = get_resume_point(link)
        if position >= RESUME_MIN_SEC and (total == 0 or position < total - RESUME_END_MARGIN):
            choice = xbmcgui.Dialog().contextmenu([
                'Pokračovat od {}'.format(_fmt_time(position)),
                'Přehrát od začátku',
            ])
            if choice == 0:
                listitem.setProperty('ResumeTime', str(position))
                listitem.setProperty('TotalTime', str(total if total > 0 else position + 1))
            elif choice == 1:
                set_resume_point(link, 0, total)
        xbmcplugin.setResolvedUrl(_handle, True, listitem)
        _monitor_playback(link)
    except ValueError as e:
        clear_cached_session()
        log('Chyba zpracování stránky: {}'.format(e), xbmc.LOGERROR)
        notify_error(str(e))
        xbmcplugin.setResolvedUrl(_handle, False, xbmcgui.ListItem())
    except Exception as e:
        clear_cached_session()
        log('Chyba přehrávání (Premium): {}'.format(e), xbmc.LOGERROR)
        notify_error('Chyba přehrávání: ' + str(e))
        xbmcplugin.setResolvedUrl(_handle, False, xbmcgui.ListItem())


# ---------------------------------------------------------------------------
# Stahování (fronta na pozadí)
# ---------------------------------------------------------------------------

def resolve_download(item):
    """Pro frontu stahování: najde přímý odkaz na soubor a titulky."""
    is_premium, cookies = ensure_premium(quiet=True)
    if not is_premium:
        raise IOError('vyžaduje Premium účet')
    page = BASE_URL + urlparse(item['url']).path
    file, sub = get_link(safe_request_get(page, cookies=cookies).content)
    file = premium_file_url(page, cookies, file)
    path = urlparse(file).path
    ext = path.rsplit('.', 1)[-1].lower() if '.' in path.rsplit('/', 1)[-1] else 'mp4'
    if not re.fullmatch(r'[a-z0-9]{2,4}', ext):
        ext = 'mp4'
    return {'url': file, 'headers': HEADERS, 'cookies': cookies, 'ext': ext, 'subtitle': sub}


def downloader():
    return Downloader(addon, PROFILE, log, notify, resolve_download)


def title_from_url(url):
    part = urlparse(url).path.strip('/').split('/')[0]
    return part.replace('-', ' ') or 'video'


def download_multi(page_url):
    cookies = None
    if addon.getSetting('email'):
        premium, cookies = get_premium(quiet=True)
        cookies = cookies if premium else None
    try:
        videos, _ = fetch_search_page(page_url, cookies)
    except Exception as e:
        log('Výběr videí ke stažení selhal: {}'.format(e), xbmc.LOGWARNING)
        videos = []
    if not videos:
        notify('Na stránce nejsou žádná videa')
        return
    labels = ['{}  [COLOR gray]{}[/COLOR]'.format(v['title'], v['info']) for v in videos]
    chosen = xbmcgui.Dialog().multiselect('Vyberte videa ke stažení', labels)
    if not chosen:
        return
    downloader().enqueue([{'url': videos[i]['url'], 'title': videos[i]['title']} for i in chosen])


# ---------------------------------------------------------------------------
# Hledání a historie
# ---------------------------------------------------------------------------

def history():
    for q in load_history():
        list_item = xbmcgui.ListItem(label=q)
        list_item.addContextMenuItems([
            ('Smazat z historie', 'RunPlugin({})'.format(get_url(action='history_del', name=q))),
        ])
        xbmcplugin.addDirectoryItem(_handle, get_url(action='listing_search', name=q), list_item, True)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc=False)


def load_history():
    try:
        with open(history_path, 'r', encoding='utf-8') as f:
            return [x for x in f.read().splitlines() if x.strip()]
    except Exception:
        return []


def _write_history(items):
    try:
        os.makedirs(os.path.dirname(history_path), exist_ok=True)
        with open(history_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(items))
    except Exception as e:
        log('Nelze zapsat historii: {}'.format(e), xbmc.LOGWARNING)


def _save_to_history(q):
    lh = [x for x in load_history() if x.lower() != q.lower()]
    _write_history(([q] + lh)[:20])


class LoginRequired(Exception):
    pass


def fetch_search_page(page_url, cookies=None):
    """Jedna stránka výsledků: (videa, URL další stránky)."""
    resp = safe_request_get(page_url, cookies=cookies)
    if 'backlink=' in resp.url:
        # další strany výsledků web ukazuje jen přihlášeným
        raise LoginRequired()
    soup = BeautifulSoup(resp.content, 'html.parser')
    videos = []
    for box in soup.find_all('div', class_='video__picture--container'):
        a = box.find('a', class_='video--link') or box.find('a', href=True)
        if not a or not a.get('href'):
            continue
        title_tag = box.find('h3', class_='video__title')
        title = (title_tag.get_text(strip=True) if title_tag else '') or a.get('title', '') or title_from_url(a['href'])
        img = box.find('img', class_='thumb1') or box.find('img')
        thumb = (img.get('src') or img.get('data-src') or '') if img else ''
        size = box.find(class_='video__tag--size')
        dur = box.find(class_='video__tag--time')
        fmt = box.find(class_='format__text')
        size_t = size.get_text(strip=True) if size else ''
        dur_t = dur.get_text(strip=True) if dur else ''
        fmt_t = fmt.get_text(strip=True) if fmt else ''
        videos.append({
            'url': urljoin(BASE_URL, a['href']),
            'title': title,
            'thumb': thumb.replace('.cz//', '.cz/'),
            'duration': _duration_seconds(dur_t),
            'info': ' · '.join(x for x in (size_t, dur_t, fmt_t) if x),
        })
    nxt = soup.find('a', title='Zobrazit další')
    next_url = urljoin(BASE_URL, nxt['href']) if nxt and nxt.get('href') else None
    return videos, next_url


def search(name, page_url=None, page_no=1):
    if not page_url:
        if name == 'None':
            q = xbmcgui.Dialog().input('Zadejte název filmu nebo seriálu', type=xbmcgui.INPUT_ALPHANUM).strip()
            xbmcplugin.endOfDirectory(_handle, succeeded=False)
            if q:
                # výsledky pod vlastní adresou, aby se při návratu znovu neptal
                xbmc.executebuiltin('Container.Update({})'.format(get_url(action='listing_search', name=q)))
            return
        q = encode(name)
        _save_to_history(name)
        page_url = '{}/hledej/{}'.format(BASE_URL, quote(q))

    cookies = None
    if addon.getSetting('email'):
        premium, cookies = get_premium(quiet=True)
        cookies = cookies if premium else None

    videos, next_url = [], page_url
    first_page = page_url
    try:
        # načítej stránky, dokud nemáme aspoň tolik videí, kolik je v nastavení
        while next_url and len(videos) < int(ls):
            page, next_url = fetch_search_page(next_url, cookies)
            videos += page
            if not page:
                break
    except LoginRequired:
        next_url = None
        if not videos:
            notify('Další strany výsledků jsou jen pro přihlášené (nastavte účet)')
            xbmcplugin.endOfDirectory(_handle, succeeded=False)
            return
    except requests.exceptions.HTTPError as e:
        busy = e.response is not None and e.response.status_code == 429
        log('Chyba hledání: {}'.format(e), xbmc.LOGWARNING if busy else xbmc.LOGERROR)
        if not videos:
            notify_error('Prehraj.to omezil počet dotazů, zkuste to za chvíli' if busy else
                         'Chyba připojení k prehraj.to')
            xbmcplugin.endOfDirectory(_handle, succeeded=False)
            return
    except Exception as e:
        log('Chyba hledání: {}'.format(e), xbmc.LOGERROR)
        if not videos:
            notify_error('Chyba připojení k prehraj.to')
            xbmcplugin.endOfDirectory(_handle, succeeded=False)
            return

    log('Hledání {}: {} videí (první: {}), další strana: {}'.format(
        first_page, len(videos), videos[0]['url'] if videos else '-', bool(next_url)))
    if not videos:
        notify('Nic nenalezeno')
    else:
        li = xbmcgui.ListItem('[COLOR deepskyblue]Stáhnout více videí z této stránky...[/COLOR]')
        li.setArt({'icon': ICON, 'thumb': ICON})
        xbmcplugin.addDirectoryItem(_handle, get_url(action='download_multi', url=first_page), li, False)

    xbmcplugin.setContent(_handle, 'videos')
    for v in videos:
        list_item = xbmcgui.ListItem(label='{}  [COLOR gray]({})[/COLOR]'.format(v['title'], v['info']))
        set_video_info(list_item, title=v['title'], mediatype='video', duration=v['duration'])
        list_item.setArt({'thumb': v['thumb'], 'icon': v['thumb'], 'poster': v['thumb']})
        list_item.setProperty('IsPlayable', 'true')
        list_item.addContextMenuItems([
            ('Stáhnout', 'RunPlugin({})'.format(get_url(action='download', url=v['url'], title=v['title']))),
            ('Stáhnout více z této stránky...', 'RunPlugin({})'.format(get_url(action='download_multi', url=first_page))),
            ('Uložit do knihovny', 'RunPlugin({})'.format(get_url(action='library', url=v['url']))),
            ('QR kód streamu', 'RunPlugin({})'.format(get_url(action='qr', url=v['url']))),
        ])
        xbmcplugin.addDirectoryItem(_handle, get_url(action='play', link=v['url']), list_item, False)
    if next_url:
        li = xbmcgui.ListItem('[B]Další >>[/B]  (strana {})'.format(page_no + 1))
        xbmcplugin.addDirectoryItem(_handle, get_url(action='listing_search', name=name, page_url=next_url,
                                                     page=page_no + 1), li, True)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_DURATION)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc=False)


# ---------------------------------------------------------------------------
# Filmy a seriály (TMDB)
# ---------------------------------------------------------------------------

def tmdb_get(path, extra=''):
    return json.loads(urlopen(TMDB.format(path, extra), timeout=TIMEOUT).read())


def tmdb_episodes(name, type, ses_num, fanart, thumb):
    try:
        res = tmdb_get('tv/{}/season/{}'.format(type, ses_num))
    except Exception as e:
        log('Chyba TMDB epizody: {}'.format(e), xbmc.LOGERROR)
        notify_error('Chyba načítání epizod')
        xbmcplugin.endOfDirectory(_handle)
        return
    for category in res.get('episodes', []):
        if category.get('name') in ('Speciály', 'Špeciály'):
            continue
        list_item = xbmcgui.ListItem(label=category['name'])
        list_item.setArt({'thumb': thumb, 'icon': thumb, 'fanart': fanart})
        full_name = '{} S{}E{}'.format(name, str(category['season_number']).zfill(2),
                                       str(category['episode_number']).zfill(2))
        xbmcplugin.addDirectoryItem(_handle, get_url(action='listing_search', name=full_name, type=type),
                                    list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def tmdb_seasons(name, type):
    try:
        res = tmdb_get('tv/{}'.format(type))
    except Exception as e:
        log('Chyba TMDB série: {}'.format(e), xbmc.LOGERROR)
        notify_error('Chyba načítání sérií')
        xbmcplugin.endOfDirectory(_handle)
        return
    fanart = 'https://image.tmdb.org/t/p/w1280' + res['backdrop_path'] if res.get('backdrop_path') else ''
    for category in res.get('seasons', []):
        if category.get('name') in ('Speciály', 'Špeciály'):
            continue
        list_item = xbmcgui.ListItem(label=category['name'])
        thumb = 'http://image.tmdb.org/t/p/w342' + category['poster_path'] if category.get('poster_path') else ''
        list_item.setArt({'thumb': thumb, 'icon': thumb, 'fanart': fanart})
        url = get_url(action='listing_episodes', name=name, type=type,
                      ses_num=str(category['season_number']), fanart=fanart, thumb=thumb)
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def _build_tmdb_item(category, title_key, date_key, type_):
    title = category.get(title_key)
    if not title:
        return None
    genre = ' / '.join(gid[g] for g in category.get('genre_ids', []) if g in gid)
    year = (category.get(date_key) or '').split('-')[0]
    fanart = 'https://image.tmdb.org/t/p/w1280' + category['backdrop_path'] if category.get('backdrop_path') else ''
    thumb = 'http://image.tmdb.org/t/p/w342' + category['poster_path'] if category.get('poster_path') else ''
    list_item = xbmcgui.ListItem(label=title)
    set_video_info(list_item, mediatype='movie' if type_ == 'movie' else 'tvshow', title=title,
                   plot=category.get('overview', ''), year=year, genre=genre,
                   rating=str(category.get('vote_average', ''))[:3])
    list_item.setArt({'thumb': thumb, 'icon': thumb, 'poster': thumb, 'fanart': fanart})
    return list_item, title, year


def _tmdb_listing(path, extra, page, title_key, date_key, kind, next_query):
    p = int(page)
    try:
        res = tmdb_get(path, extra + '&page={}'.format(p))
    except Exception as e:
        log('Chyba TMDB {}: {}'.format(path, e), xbmc.LOGERROR)
        notify_error('Chyba načítání z TMDB')
        xbmcplugin.endOfDirectory(_handle)
        return
    xbmcplugin.setContent(_handle, 'movies' if kind == 'movie' else 'tvshows')
    for category in res.get('results', []):
        result = _build_tmdb_item(category, title_key, date_key, kind)
        if not result:
            continue
        list_item, title, year = result
        if kind == 'movie':
            url = get_url(action='listing_search', name='{} {}'.format(title, year).strip(), type=kind)
        else:
            url = get_url(action='listing_seasons', name=title, type=category['id'])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    if p < int(res.get('total_pages') or p + 1):
        xbmcplugin.addDirectoryItem(_handle, get_url(**dict(next_query, page=str(p + 1))),
                                    xbmcgui.ListItem(label='[B]Další >>[/B]  (strana {})'.format(p + 1)), True)
    xbmcplugin.endOfDirectory(_handle)


def tmdb_serie(page, type):
    _tmdb_listing('tv/{}'.format(type), '', page, 'name', 'first_air_date', 'tv',
                  {'action': 'listing_tmdb_serie', 'type': type})


def tmdb_movie(page, type):
    _tmdb_listing('movie/{}'.format(type), '', page, 'title', 'release_date', 'movie',
                  {'action': 'listing_tmdb_movie', 'type': type})


def tmdb_genre(page, type, id):
    title_key, date_key = ('title', 'release_date') if type == 'movie' else ('name', 'first_air_date')
    _tmdb_listing('discover/{}'.format(type), '&with_genres={}'.format(id), page, title_key, date_key, type,
                  {'action': 'listing_genre', 'type': type, 'id': id})


def tmdb_year(page, type, id):
    if type == 'movie':
        title_key, date_key, fy = 'title', 'release_date', 'primary_release_year'
    else:
        title_key, date_key, fy = 'name', 'first_air_date', 'first_air_date_year'
    _tmdb_listing('discover/{}'.format(type), '&{}={}'.format(fy, id), page, title_key, date_key, type,
                  {'action': 'listing_year', 'type': type, 'id': id})


def genres_category(type):
    try:
        res = tmdb_get('genre/{}/list'.format(type))
    except Exception as e:
        log('Chyba TMDB žánry: {}'.format(e), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(_handle)
        return
    for category in res.get('genres', []):
        list_item = xbmcgui.ListItem(label=category['name'].capitalize())
        xbmcplugin.addDirectoryItem(_handle, get_url(action='listing_genre', id=str(category['id']), type=type,
                                                     page='1'), list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def years_category(type):
    year = datetime.datetime.today().year
    for y in [year - i for i in range(101)]:
        xbmcplugin.addDirectoryItem(_handle, get_url(action='listing_year', type=type, id=str(y), page='1'),
                                    xbmcgui.ListItem(label=str(y)), True)
    xbmcplugin.endOfDirectory(_handle)


def search_tmdb(name, type):
    stitle = 'filmu' if name == 'movie' else 'seriálu'
    q = xbmcgui.Dialog().input('Zadejte název ' + stitle, type=xbmcgui.INPUT_ALPHANUM).strip()
    if not q:
        xbmcplugin.endOfDirectory(_handle, succeeded=False)
        return
    try:
        res = tmdb_get('search/{}'.format(name), '&page=1&include_adult=false&query={}'.format(quote(q)))
    except Exception as e:
        log('Chyba hledání TMDB: {}'.format(e), xbmc.LOGERROR)
        notify_error('Chyba hledání na TMDB')
        xbmcplugin.endOfDirectory(_handle, succeeded=False)
        return
    xbmcplugin.setContent(_handle, 'movies' if name == 'movie' else 'tvshows')
    for category in res.get('results', []):
        if name == 'movie':
            result = _build_tmdb_item(category, 'title', 'release_date', 'movie')
            if result:
                list_item, title, year = result
                xbmcplugin.addDirectoryItem(_handle, get_url(action='listing_search', name='{} {}'.format(
                    title, year).strip(), type=type), list_item, True)
        else:
            result = _build_tmdb_item(category, 'name', 'first_air_date', 'tv')
            if result:
                list_item, title, year = result
                xbmcplugin.addDirectoryItem(_handle, get_url(action='listing_seasons', name=title,
                                                             type=category['id']), list_item, True)
    xbmcplugin.endOfDirectory(_handle)


def _simple_menu(items):
    for label, action, name, type_ in items:
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': ICON, 'thumb': ICON})
        xbmcplugin.addDirectoryItem(_handle, get_url(action=action, name=name, type=type_), li, True)
    xbmcplugin.endOfDirectory(_handle)


def movie_category():
    _simple_menu([
        ('Nejlépe hodnocené', 'listing_tmdb_movie', '1', 'top_rated'),
        ('Oblíbené', 'listing_tmdb_movie', '1', 'popular'),
        ('Novinky', 'listing_tmdb_movie', '1', 'upcoming'),
        ('Žánry', 'listing_genre_category', 'movie', ''),
        ('Podle roku', 'listing_year_category', 'movie', ''),
        ('Hledat', 'search_tmdb', 'movie', '1'),
    ])


def serie_category():
    _simple_menu([
        ('Nejlépe hodnocené', 'listing_tmdb_serie', '1', 'top_rated'),
        ('Oblíbené', 'listing_tmdb_serie', '1', 'popular'),
        ('Právě vysílané', 'listing_tmdb_serie', '1', 'on_the_air'),
        ('Žánry', 'listing_genre_category', 'tv', ''),
        ('Podle roku', 'listing_year_category', 'tv', ''),
        ('Hledat', 'search_tmdb', 'tv', '1'),
    ])


def menu():
    check_for_update()
    items = [('Hledat', 'listing_search', 'None', '')]
    if load_history():
        items.append(('Historie hledání', 'listing_history', 'None', ''))
    items += [('Filmy', 'listing_movie_category', '', ''), ('Seriály', 'listing_serie_category', '', '')]
    for label, action, name, type_ in items:
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': ICON, 'thumb': ICON})
        xbmcplugin.addDirectoryItem(_handle, get_url(action=action, name=name, type=type_), li, True)
    folder = addon.getSetting('download')
    if folder:
        li = xbmcgui.ListItem('Stažená videa')
        li.setArt({'icon': ICON, 'thumb': ICON})
        xbmcplugin.addDirectoryItem(_handle, folder, li, True)
    li = xbmcgui.ListItem('[COLOR gray]Zrušit stahování[/COLOR]')
    li.setArt({'icon': ICON, 'thumb': ICON})
    xbmcplugin.addDirectoryItem(_handle, get_url(action='download_cancel'), li, False)
    xbmcplugin.endOfDirectory(_handle)


# ---------------------------------------------------------------------------
# Směrovač
# ---------------------------------------------------------------------------

def save_to_library(url):
    lib_path = addon.getSetting('library')
    if not lib_path:
        notify_error('Nastavte složku pro knihovnu')
        return
    q = xbmcgui.Dialog().input('Zadejte název a rok filmu', title_from_url(url), type=xbmcgui.INPUT_ALPHANUM).strip()
    if not q:
        return
    try:
        f = xbmcvfs.File(os.path.join(lib_path, re.sub(r'[\\/:*?"<>|]', '', q) + '.strm'), 'w')
        f.write('plugin://{}/?action=play&link={}'.format(ADDON_ID, url))
        f.close()
        notify('Uloženo do knihovny')
    except Exception as e:
        log('Chyba zápisu do knihovny: {}'.format(e), xbmc.LOGERROR)
        notify_error('Chyba uložení: ' + str(e))


def show_qr(url):
    is_premium, qr_cookies = ensure_premium()
    if not is_premium:
        return
    try:
        file, sub = get_link(safe_request_get(url, cookies=qr_cookies).content)
        qr_link = 'https://api.qrserver.com/v1/create-qr-code/?size=500x500&format=png&data=' + quote(file, safe='')
        xbmc.executebuiltin('ShowPicture(' + qr_link + ')')
    except Exception as e:
        log('Chyba QR kódu: {}'.format(e), xbmc.LOGERROR)
        notify_error('Chyba vytvoření QR kódu: ' + str(e))


def router(paramstring):
    migrate_old_data()
    params = dict(parse_qsl(paramstring))
    if not params:
        menu()
        return
    action = params.get('action', '')
    log('Akce: {}'.format(action))

    if action == 'test_login':
        test_login()
    elif action == 'listing_search':
        search(params.get('name', 'None'), params.get('page_url'), int(params.get('page', 1)))
    elif action == 'listing_history':
        history()
    elif action == 'history_del':
        _write_history([x for x in load_history() if x != params.get('name')])
        xbmc.executebuiltin('Container.Refresh')
    elif action == 'listing_episodes':
        tmdb_episodes(params['name'], params['type'], params['ses_num'], params['fanart'], params['thumb'])
    elif action == 'listing_seasons':
        tmdb_seasons(params['name'], params['type'])
    elif action == 'listing_year':
        tmdb_year(params['page'], params['type'], params['id'])
    elif action == 'listing_year_category':
        years_category(params['name'])
    elif action == 'listing_movie_category':
        movie_category()
    elif action == 'listing_serie_category':
        serie_category()
    elif action == 'listing_genre_category':
        genres_category(params['name'])
    elif action == 'listing_genre':
        tmdb_genre(params['page'], params['type'], params['id'])
    elif action == 'listing_tmdb_movie':
        tmdb_movie(params.get('page') or params['name'], params['type'])
    elif action == 'listing_tmdb_serie':
        tmdb_serie(params.get('page') or params['name'], params['type'])
    elif action == 'search_tmdb':
        search_tmdb(params['name'], params['type'])
    elif action == 'play':
        link = params.get('link', '')
        if not link:
            notify_error('Chybí odkaz na video')
            xbmcplugin.setResolvedUrl(_handle, False, xbmcgui.ListItem())
            return
        is_premium, cookies = ensure_premium()
        if not is_premium:
            xbmcplugin.setResolvedUrl(_handle, False, xbmcgui.ListItem())
            return
        play_video_premium(link, cookies)
    elif action == 'library':
        save_to_library(params['url'])
    elif action == 'qr':
        show_qr(params['url'])
    elif action == 'download':
        downloader().enqueue([{'url': params['url'], 'title': params.get('title') or title_from_url(params['url'])}])
    elif action == 'download_multi':
        download_multi(params['url'])
    elif action == 'download_cancel':
        downloader().cancel()
    else:
        log('Neznámá akce: {}'.format(action), xbmc.LOGWARNING)
        menu()


if __name__ == '__main__':
    try:
        router(sys.argv[2][1:] if len(sys.argv) > 2 else '')
    except Exception as exc:  # poslední záchrana, ať Kodi nezamrzne
        import traceback
        log('Neočekávaná chyba: {}\n{}'.format(exc, traceback.format_exc()), xbmc.LOGERROR)
        notify_error('Neočekávaná chyba: {}'.format(exc))
