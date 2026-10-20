# -*- coding: UTF-8 -*-

import sys, os, requests, json, time
from hashlib import md5
import urllib.parse
import xbmcaddon
import xbmcgui
import xbmcvfs
import xbmc

# Bez časového limitu Kodi při nedostupném serveru visí donekonečna.
REQUEST_TIMEOUT = 20
_orig_session_request = requests.Session.request
def _request_with_timeout(self, method, url, **kwargs):
    kwargs.setdefault('timeout', REQUEST_TIMEOUT)
    return _orig_session_request(self, method, url, **kwargs)
requests.Session.request = _request_with_timeout

addon_id = 'plugin.video.sosac-2'
#addon_name_ = translate(30402) #'Sosac.TV'
addon = xbmcaddon.Addon(addon_id)
addonPath = xbmcvfs.translatePath(addon.getAddonInfo('path'))
artPath = xbmcvfs.translatePath(os.path.join(addonPath,"resources","icons"))
imgPath = xbmcvfs.translatePath(os.path.join(addonPath,"resources","images"))
libPath = xbmcvfs.translatePath(os.path.join(addonPath,"resources","lib"))
profilepath = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
addon_lang = addon.getLocalizedString
__set__ = addon.getSetting
dialog = xbmcgui.Dialog()

settings = {'downloads': __set__('downloads'), 'quality': __set__(
    'quality'), 'subs': __set__('subs') == 'true', 'lang': __set__('language')}

qual_orig = ["2160p(UHD)","1080p(FHD)","720p(HD)","480p(SD)","2160p(UHD HDR)"]
audio_quality_orig = ["stereo", "surround"]
dubb_orig = ["CZECH","SLOVAK","ENGLISH"]
topic_orig = ["NO","CZECH","SLOVAK"]
yesno = ["YES","NO"]
preferred_audio_quality = "stereo"

sosac_domain = __set__("sosac_domain")
streaming_provider = __set__("streaming_provider")
domain_actif = __set__("domain_actif")
#STREAMUJ_API = "https://www.streamuj.tv/json_api_player.php?"
#SOSAC_API = "https://kodi-api.sosac.to/"
STREAMUJ_API = f"https://{streaming_provider}/json_api_player.php?"
SOSAC_API = f"https://{sosac_domain}/"
SOSAC_MOVIES = "https://movies.sosac.tv/images/75x109/movie-"
SOSAC_SERIES = "http://movies.sosac.tv/images/558x313/serial-"
streamujtv_user = __set__('streamujtv_user')
streamujtv_pass = __set__('streamujtv_pass')
streamujtv_location = __set__('streamujtv_location')
try :
    streamujtv_location = str(int(streamujtv_location) + 1)
except ValueError :
    streamujtv_location = "1"
sosac_user = __set__('sosac_user')
sosac_pass = __set__('sosac_pass')

try : 
    auto_stream = __set__('auto-stream')
    quality = qual_orig[int(__set__('quality'))]
    try :
        preferred_audio_quality = audio_quality_orig[int(__set__('audio-quality'))]
    except :
        preferred_audio_quality = "stereo"
    first_dubbing = dubb_orig[int(__set__('first-dubbing'))]
    second_dubbing = dubb_orig[int(__set__('second-dubbing'))]
    auto_subtitles = __set__('auto-subtitles')
    first_subtitles = dubb_orig[int(__set__('first-subtitles'))]
    second_subtitles = dubb_orig[int(__set__('second-subtitles'))]
    next_episode = __set__('next-episode')
except :
    pass
try :
    current_topic = topic_orig[int(__set__('current-topic'))]
except (ValueError, IndexError) :
    current_topic = topic_orig[0]  # nastavení current-topic v settings.xml chybí
down_int = [10, 20, 30, 40, 50]

    
COUNTRY_DICT = {
    "Czech Republic":1, "USA":2, "Slovakia":3, "Great Britain":4, "Germany":5,"Spain":6, "America":7,
    "France":8, "Italia":9, "Canada":10, "Romania":11, "Japan":12, "HongKong":13, "Turkey":14,
    "Austria":15, "Denmark":16, "Netherlands":17, "Belgium":18, "Ireland":19,
    "Egypt":20, "Switzerland":21, "Peru":22,"Luxembourg":23, "JAR":24,
    "New Zealand":25, "China":26, "Ukraine":27, "Finland":28,"Sweden":29,"Russia":30}

COUNTRY_DICT_old = {
    "Czech Republic":"cs","USA":"us","Slovakia":"sk","Great Britain":"uk","Germany":"de","Spain":"es","America":"en",
    "France":"fr","Italia":"it","Canada":"ca","Romania":"ro","Japan":"ja","HongKong":"cn","Turkey":"tr",
    "Austria":"de","Denmark":"dk","Netherlands":"nl","Belgium":"be","Ireland":"ie",
    "Egypt":"eg","Switzerland":"ch","Peru":"pe","Luxembourg":"lu","JAR":"za",
    "New Zealand":"nz","China":"cn","Ukraine":"ua","Finland":"fi","Sweden":"se","Russia":"ru"}
country_list = ["cs","us","sk","uk","de","es","en","fr","it","ca","ro","ja","cn","tr",
    "de","dk","nl","be","ie","eg","ch","pe","lu","za","nz","cn","ua","fi","se","ru"]

sort_list ={
"popularity":"v1","CSFD rating":"v2","IMDB rating":"v3","movie budget":"v4",
"movie revenue":"v5","alphabet":"v6","date added":"v7","best match":""}
SORT_Listv = ["v1","-v1","v2","-v2","v3","-v3","v4","-v4","v5","-v5","v6","-v6","v7","-v7",""]
SORT_Listsv = ["v1","-v1","v2","-v2","v3","-v3","v4","-v6","v5","-v7",""]

dub_list1 = ['CZECH', 'SLOVAK', 'ENGLISH', 'CHINESE', 'GERMAN', 'GREEK', 'SPANISH', 'FINNISH', 'FRENCH', 'CROATIAN', 'INDU', 'ITALIAN',\
             'JAPANESE', 'KOREAN', 'DUTCH', 'NORWEGIAN','POLISH', 'PORTUGUESE', 'RUSSIAN', 'TURKISH', 'VIETNAMESE']

DUBBING = {
    'CZECH': 'cz',
     'SLOVAK': 'sk',
     'ENGLISH': 'en',
     'CHINESE': 'cn',
     'GERMAN': 'de',
     'GREEK': 'el',
     'SPANISH': 'es',
     'FINNISH': 'fi',
     'FRENCH': 'fr',
     'CROATIAN': 'hr',
     'INDU': 'id',
     'ITALIAN': 'it',
     'JAPANESE': 'ja',
     'KOREAN': 'ko',
     'DUTCH': 'nl',
     'NORWEGIAN': 'no',
     'POLISH': 'pl',
     'PORTUGUESE': 'pt',
     'RUSSIAN': 'ru',
     'TURKISH': 'tr',
     'VIETNAMESE': 'vi'}

sort_dict ={
"popularity":"v1","CSFD rating":"v2","IMDB rating":"v3","movie budget":"v4","movie revenue":"v5","alphabet":"v6","date added":"v7","best match":""}
sort_dicts ={
"popularity":"v1","popularity descending":"-v1","CSFD rating":"v2","CSFD rating descending":"-v2","IMDB rating":"v3","IMDB rating descending":"-v3",
"alphabet":"v4","alphabet descending":"-v6","date added":"v5","date added descending":"-v7","best match":""}

genre1 = ["action","adventure","animation","biography","cartoons","comedy","crime","disaster","documentary","drama","erotic",
  "experimental","fairytales","family","fantasy","history","horror","imax","krimi","music","mystery",
  "psychological","publicistic","realitytv","romance","sci-fi","sport","talkshow","thriller","war","western"]

country_list0 = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30]

############################################
def set_preferred_audio_stream():
    # Select preferred audio by the real channel count reported by Kodi.
    # Stereo = 1-2 channels, Surround = more than 2 channels.
    # If the requested type is not present, keep Kodi's current audio stream.
    try :
        preference = preferred_audio_quality if preferred_audio_quality in ("stereo", "surround") else "stereo"
        player_id = None

        # onAVStarted should already have an active player, but retry briefly
        # because some devices expose JSON-RPC player data a little later.
        for _ in range(8):
            request = json.dumps({"jsonrpc":"2.0", "method":"Player.GetActivePlayers", "id":1})
            response = json.loads(xbmc.executeJSONRPC(request))
            for active_player in response.get("result", []):
                if active_player.get("type") == "video":
                    player_id = active_player.get("playerid")
                    break
            if player_id is not None:
                break
            xbmc.sleep(250)

        if player_id is None:
            debug("preferred audio: no active video player", 2)
            return False

        streams = []
        for _ in range(8):
            request = json.dumps({
                "jsonrpc":"2.0",
                "method":"Player.GetProperties",
                "params":{"playerid":player_id, "properties":["audiostreams", "currentaudiostream"]},
                "id":1
            })
            response = json.loads(xbmc.executeJSONRPC(request))
            streams = response.get("result", {}).get("audiostreams", []) or []
            if streams:
                break
            xbmc.sleep(250)

        if not streams:
            debug("preferred audio: Kodi reported no audio streams", 2)
            return False

        candidates = []
        for stream in streams:
            try :
                channels = int(stream.get("channels", 0) or 0)
                index = int(stream.get("index", -1))
            except :
                continue

            if index < 0:
                continue
            if preference == "surround" and channels > 2:
                candidates.append((channels, index))
            elif preference == "stereo" and channels > 0 and channels <= 2:
                candidates.append((channels, index))

        if not candidates:
            debug("preferred audio: %s stream is not available"%preference, 2)
            return False

        # Prefer the best match: maximum channels for surround, exactly 2 for stereo.
        if preference == "surround":
            candidates.sort(key=lambda x: (x[0], -x[1]), reverse=True)
        else:
            candidates.sort(key=lambda x: (x[0] == 2, x[0], -x[1]), reverse=True)

        channels, stream_index = candidates[0]
        request = json.dumps({
            "jsonrpc":"2.0",
            "method":"Player.SetAudioStream",
            "params":{"playerid":player_id, "stream":stream_index},
            "id":1
        })
        response = json.loads(xbmc.executeJSONRPC(request))
        if "error" in response:
            debug("preferred audio: Player.SetAudioStream error %s"%response.get("error"), 2)
            return False

        debug("preferred audio: selected %s stream index=%s channels=%s"%(preference,stream_index,channels), 2)
        return True
    except Exception as e :
        debug("preferred audio: selection error %s"%str(e), 2)
        return False

############################################
def get_icon(icon) :
    return os.path.join(artPath,icon)

def debug(text,level):
    # Ladicí výpisy jen do ladicího logu. Dřív šly jako ERROR do kodi.log vždy,
    # včetně URL s uživatelským jménem a otiskem hesla.
    xbmc.log("Sosac: " + str(text), xbmc.LOGDEBUG)

def notify(title, message, time=5000):
    try:
        xbmcgui.Dialog().notification(title, message, time=time)
    except Exception as e:
        debug(" error notify %s"%e,2)

def translate(text):
      return addon.getLocalizedString(text)

def tr(text_id, *args):
    # překlad s parametry; chybějící nebo vadný překlad nesmí shodit doplněk
    text = addon.getLocalizedString(text_id)
    try :
        return text % args if args else text
    except (TypeError, ValueError) :
        return (text + " " + " ".join(str(a) for a in args)).strip()

def isMatrix():
    try:
        version = xbmc.getInfoLabel('system.buildversion')
        if version[0:2] >= '19':
            return True
        else:
            return False
    except:
        return False


def isNexus():
    try:
        version = xbmc.getInfoLabel('system.buildversion')
        if version[0:2] >= '20':
            return True
        else:
            return False
    except:
        return False

try :
    if not os.path.isdir(profilepath) : os.makedirs(profilepath)
    # výchozí úložiště = Offline v Kodi (funguje i na iPadu)
    moviesPath = os.path.join(profilepath,"movies")
    seriesPath = os.path.join(profilepath,"series")
    moviesSub = os.path.join(profilepath,"moviessub")
    seriesSub = os.path.join(profilepath,"seriessub")
    movie_data = xbmcvfs.translatePath(os.path.join(profilepath,"movie_data.json"))
    if not xbmcvfs.exists(movie_data) :
        f_data = {}
        f_data["test"] = "test"
        with open(movie_data, "w", encoding="utf-8") as fdata :
            json.dump(f_data, fdata, indent=4)
            #fdata.write(json.dumps(f_data))
    serial_data = xbmcvfs.translatePath(os.path.join(profilepath,"serial_data.json"))
    if not xbmcvfs.exists(serial_data) :
        f_data = {}
        f_data["test"] = "test"
        with open(serial_data, "w", encoding="utf-8") as fdata :
            json.dump(f_data, fdata, indent=4)
            #fdata.write(json.dumps(f_data))

    movie_search = xbmcvfs.translatePath(os.path.join(profilepath,"movie_search.txt"))
    serial_search = xbmcvfs.translatePath(os.path.join(profilepath,"serial_search.txt"))
    if not os.path.isdir(moviesPath) : os.mkdir(moviesPath)
    if not os.path.isdir(seriesPath) : os.mkdir(seriesPath)
    if not os.path.isdir(moviesSub) : os.mkdir(moviesSub)
    if not os.path.isdir(seriesSub) : os.mkdir(seriesSub)
except Exception as e :
    debug("downfolder error %s"%e, 2)

############################################
# Úložiště stažených videí
#   0 = Offline v Kodi (složka doplňku, funguje i na iPadu / Apple TV)
#   1 = Složka v počítači (nastavení "downloads")
ROOT_OFFLINE = 0
ROOT_PC = 1
OFFLINE_ROOT = profilepath

def pc_root() :
    path = __set__("downloads")
    if not path :
        return ""
    path = xbmcvfs.translatePath(path)
    # výchozí hodnota nastavení ukazuje do složky doplňku = to je offline úložiště
    if os.path.normpath(path) == os.path.normpath(OFFLINE_ROOT) :
        return ""
    return path

def root_base(idx) :
    if int(idx) == ROOT_PC and pc_root() :
        # do podsložky "Sosac", ať vybraná složka (třeba Plocha) není zaplněná movies/series/…
        pc = pc_root()
        return pc if os.path.basename(os.path.normpath(pc)) == "Sosac" else os.path.join(pc, "Sosac")
    return OFFLINE_ROOT

def down_paths(idx) :
    base = root_base(idx)
    paths = {}
    for name in ("movies", "series", "moviessub", "seriessub") :
        paths[name] = os.path.join(base, name)
        try :
            if not os.path.isdir(paths[name]) : os.makedirs(paths[name])
        except Exception as e :
            debug("down_paths mkdir error %s"%e, 2)
    return paths

def available_roots() :
    return [ROOT_OFFLINE, ROOT_PC] if pc_root() else [ROOT_OFFLINE]

def is_apple_mobile() :
    # Apple TV (tvOS) a iPad/iPhone (iOS): žádná "složka v počítači", stahuje se do Kodi
    try :
        return xbmc.getCondVisibility("System.Platform.TVOS") or xbmc.getCondVisibility("System.Platform.IOS")
    except Exception :
        return False

def choose_root() :
    # Kam stahovat: podle nastavení "download-target" (0 = zeptat se, 1 = offline, 2 = počítač).
    target = __set__("download-target") or "0"
    if target == "1" or (target == "0" and is_apple_mobile() and not pc_root()) :
        return ROOT_OFFLINE
    if target == "2" :
        idx = ROOT_PC
    else :
        pc = pc_root()
        options = [translate(30415), translate(30416) + (f" ({pc})" if pc else "")]
        idx = dialog.select(translate(30417), options)
        if idx < 0 :
            return None
    if idx == ROOT_PC and not pc_root() :
        path = dialog.browse(3, translate(30418), "files")
        if not path :
            return None
        addon.setSetting("downloads", path)
    return idx

xbmcpath = xbmcvfs.translatePath(os.path.join("special://xbmc","skin.estuary"))
skinpath = xbmcvfs.translatePath("special://skin")

ADVANCEDSETTINGS = xbmcvfs.translatePath(os.path.join("special://userdata","advancedsettings.xml"))
downListPath = xbmcvfs.translatePath(os.path.join(profilepath,"downList"))

addon_name_ = translate(30402) #'Sosac.TV'

#########################################
def sosachash() :
    if len(sosac_user) == 0 or len(sosac_pass) == 0:
        repse = dialog.yesno(addon_name_,translate(30404))
        if repse  :
            addon.openSettings()
            return None
        else : return None
        
    # set streamujtv credentials
    
    passwordForApi = md5(f"{sosac_user}:{sosac_pass}".encode('utf-8')).hexdigest()
    passwordForApi2 = md5((passwordForApi + 'EWs5yVD4QF2sshGm22EWVa').encode('utf-8'))
    sosac_passwordhash = passwordForApi2.hexdigest()
    if sosac_passwordhash : 
        stream_url = f"{SOSAC_API}movies/lists/queue?pocet=1&stranka=1&username={sosac_user}&password={sosac_passwordhash}"
        return stream_url
    else : exit()

def passhash() :
    if len(sosac_user) == 0 or len(sosac_pass) == 0:
        repse = dialog.yesno(addon_name_,translate(30404))
        if repse  : addon.openSettings()
        exit()

    # set sosac credentials
    passwordForApi = md5(f"{sosac_user}:{sosac_pass}".encode('utf-8')).hexdigest()
    passwordForApi2 = md5((passwordForApi + 'EWs5yVD4QF2sshGm22EWVa').encode('utf-8'))
    sosac_passwordhash = passwordForApi2.hexdigest()

    # Účet stačí ověřit jednou. Dřív se před KAŽDÝM dotazem stahoval celý seznam
    # 100 populárních filmů jen kvůli kontrole hesla, což vše zdvojnásobovalo.
    if __set__("account_ok") == f"{sosac_domain}|{sosac_passwordhash}" :
        return sosac_passwordhash

    stream_url = f"{SOSAC_API}movies/lists/popular?pocet=1&stranka=1&username={sosac_user}&password={sosac_passwordhash}"
    source = requests.get(stream_url)
    debug("passhash %s "%source.status_code, 2)
    if source.status_code == 403 :
        repse = dialog.yesno(addon_name_,translate(30404))
        if repse  :
            addon.openSettings()
        exit()
    elif source.status_code == 401 :
        repse = dialog.yesno(addon_name_,translate(30405))
        if repse  :
            addon.openSettings()
        exit()
    try :
        data = json.loads(source.text)
        if data[0]["w"] == None :
            debug('data["w"] %s'%data[0]["w"],2)
            repse = dialog.yesno(addon_name_,translate(30405))
            if repse  :
                addon.openSettings()
            exit()
    except (ValueError, KeyError, IndexError, TypeError) as e:
        debug('passhash data error %s'%e,2)
        return sosac_passwordhash

    addon.setSetting("account_ok", f"{sosac_domain}|{sosac_passwordhash}")
    return sosac_passwordhash

def set_streamujtv_info(stream):
    if len(streamujtv_user) == 0 or len(streamujtv_pass) == 0:
        repse = dialog.yesno(addon_name_,translate(30404))
        if repse  : addon.openSettings()
        else : exit()

    if len(streamujtv_user) > 0 and len(streamujtv_pass) > 0:
        # set streamujtv credentials
        m = md5()
        m.update(streamujtv_pass.encode('utf-8'))
        h = m.hexdigest()
    else : h = ""
    
    if stream :
        if streamujtv_location in ['1', '2']:
            location = streamujtv_location
        else : location = 1
        stream_url = f"{STREAMUJ_API}action=get-video-links&d=19&link={stream}&login={streamujtv_user}&password={h}&location={location}"
    elif h  :
        stream_url = f"{STREAMUJ_API}action=check-user&password={h}&login={streamujtv_user}&passwordinmd5=1"
    else : exit()
    return stream_url

def set_sosac_info(stream,**kwargs):
    sosac_passwordhash = passhash()
    page = kwargs['arg3'] if 'arg3' in kwargs else "1"
    
    
    if  "a-z" == stream:
        letter = kwargs['arg2'].lower()
        stream_url = f"{SOSAC_API}movies/lists/a-z?l={letter}&pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"
    elif "by-year" == stream :
        year = kwargs['arg2']
        stream_url = f"{SOSAC_API}movies/lists/by-year?y={year}&pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"
    elif "by-quality" == stream :
        quality = kwargs['arg2']
        stream_url = f"{SOSAC_API}movies/lists/by-quality?q={quality}&pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"
    elif "by-genre" == stream :
        genrev = kwargs['arg2']
        genre = genre1[int(genrev)]
        stream_url = f"{SOSAC_API}movies/lists/by-genre?g={genre}&pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"
    elif "search" == stream :
        keyword = kwargs['arg2']
        stream_url = f"{SOSAC_API}movies/simple-search?q={keyword}&pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"
    elif "advancedsearch" == stream :
        search = urllib.parse.quote_plus(__set__('adv_keyword'))
        debug(" params %s"%search,2)
        yearfrom = __set__('adv_from')
        yearto = __set__('adv_to')
        debug(" params %s"%yearto,2)
        year = f"{int(yearfrom)},{int(yearto)}" if yearto != "" else yearfrom
        genre = genre1[int(__set__('adv_genre'))-1] if  int(__set__('adv_genre')) != 0 else ""
        debug("__set__('adv_quality') %s"%__set__('adv_quality'), 2)
        quality = "" if  __set__('adv_quality') == "All" or __set__('adv_quality') == "Vše" else __set__('adv_quality').lower()
        debug("__set__('adv_origin') %s"%__set__('adv_origin'), 2)
        country = country_list[int(__set__('adv_origin'))-1 ] if  int(__set__('adv_origin')) != 0 else "" 
        #country = COUNTRY_DICT[__set__('adv_origin')] if  __set__('adv_origin') != "All" else ""
        dubv = dub_list1[int(__set__('adv_lang'))-1 ] if  int(__set__('adv_lang')) != 0 else "" 
        language = DUBBING[dubv] if  dubv != "" else ""
        debug(" params %s"%language,2)
        director = urllib.parse.quote_plus(__set__('adv_director'))
        scriptwriter = urllib.parse.quote_plus(__set__('adv_writer'))
        actor = urllib.parse.quote_plus(__set__('adv_actor'))
        sort_set = int(__set__('adv_sort'))
        sort_v = SORT_Listv[sort_set] 
        stream_url = f"{SOSAC_API}movies/advanced-search?k={search}&y={year}&g={genre}&q={quality}&c={country}&l={language}&d={director}&s={scriptwriter}&a={actor}&pocet=10&stranka={page}&o={sort_v}&username={sosac_user}&password={sosac_passwordhash}"
        #stream_url = stream_url.replace("&","&amp;")
    elif "watching-time" == stream :
        _id = kwargs['arg2']
        stream_url = f"{SOSAC_API}movies/{_id}/watching-time?username={sosac_user}&password={sosac_passwordhash}&d=19"
    elif stream == "into-queue" :
        _id = kwargs['arg2']
        stream_url = f"{SOSAC_API}movies/{_id}/into-queue?username={sosac_user}&password={sosac_passwordhash}"
        respse = requests.post(stream_url,data={})
        return
    elif stream == "off-queue" :
        _id = kwargs['arg2']
        stream_url = f"{SOSAC_API}movies/{_id}/off-queue?username={sosac_user}&password={sosac_passwordhash}"
        respse = requests.post(stream_url,data={})
        return
    elif stream == "id":
        _id = kwargs['arg2']
        stream_url = f"{SOSAC_API}movies/{_id}?username={sosac_user}&password={sosac_passwordhash}"

    else : 
        stream_url = f"{SOSAC_API}movies/lists/{stream}?pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"

    debug("stream_url %s"%stream_url,2)
    return stream_url


def set_sosac_ser(stream,**kwargs):
    sosac_passwordhash = passhash()
    episodes = kwargs['arg3']
    page = kwargs['arg5'] if 'arg5' in kwargs else "1"
    
    if  "a-z" == stream:
        letter = kwargs['arg2'].lower()
        stream_url = f"{SOSAC_API}serials/lists/a-z?l={letter}&pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"
    elif "by-year" == stream :
        year = kwargs['arg2']
        stream_url = f"{SOSAC_API}serials/lists/by-year?y={year}&pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"
    elif "by-quality" == stream :
        quality = kwargs['arg2']
        stream_url = f"{SOSAC_API}serials/lists/by-quality?q={quality}&pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"
    elif "by-genre" == stream :
        genrev = kwargs['arg2']
        genre = genre1[int(genrev)]
        stream_url = f"{SOSAC_API}serials/lists/by-genre?g={genre}&pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"
    elif "search" == stream :
        keyword = kwargs['arg2']
        stream_url = f"{SOSAC_API}serials/simple-search?q={keyword}&pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"
    elif "advancedsearch" == stream : 
        search = urllib.parse.quote_plus(__set__('adv_keywords'))
        #debug(" params %s"%search,2)
        yearfrom = __set__('adv_froms')
        yearto = __set__('adv_tos')
        #debug(" params %s"%yearto,2)
        year = f"{int(yearfrom)},{int(yearto)}" if yearto != "" else yearfrom
        genre = genre1[int(__set__('adv_genres'))-1] if  int(__set__('adv_genres')) != 0 else ""
        quality = "" if  __set__('adv_qualitys') == "All" or __set__('adv_qualitys') == "Vše" else __set__('adv_qualitys').lower()
        country = country_list[int(__set__('adv_origins'))-1 ] if  int(__set__('adv_origins')) != 0 else "" 
        dubv = dub_list1[int(__set__('adv_langs'))-1 ] if  int(__set__('adv_langs')) != 0 else "" 
        language = DUBBING[dubv] if  dubv != "" else ""
        debug(" params %s"%language,2)
        director = urllib.parse.quote_plus(__set__('adv_directors'))
        scriptwriter = urllib.parse.quote_plus(__set__('adv_writers'))
        actor = urllib.parse.quote_plus(__set__('adv_actors'))
        sort_set = int(__set__('adv_sorts'))
        sort_v = SORT_Listsv[sort_set] 
        stream_url = f"{SOSAC_API}serials/advanced-search?k={search}&y={year}&g={genre}&q={quality}&c={country}&l={language}&d={director}&s={scriptwriter}&a={actor}&pocet=10&stranka={page}&o={sort_v}&username={sosac_user}&password={sosac_passwordhash}"
        #stream_url = stream_url.replace("&","&amp;")
        #stream_url = f"{SOSAC_API}serials/advanced-search?k={search}&y={year}&g={genre}&q={quality}&c={country}&l={language}&d={director}&s={scriptwriter}&a={actor}&pocet=10&stranka=1&o={sorted}&username={sosac_user}&password={sosac_passwordhash}"
    elif "by-date" == stream :
        date_from = kwargs['arg2']
        debug("by-date date_from %s"%date_from,2)
        date_to = kwargs['arg3']
        debug("by-date date_to %s"%date_to,2)
        stream_url = f"{SOSAC_API}episodes/lists/by-date?f={date_from}&t={date_to}&pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"         
    elif (stream == "watching-time") and ("episodes" == episodes) :
        _id = kwargs['arg2']
        stream_url = f"{SOSAC_API}episodes/{_id}/watching-time?username={sosac_user}&password={sosac_passwordhash}&d=19"
    elif stream == "watching-time" :
        _id = kwargs['arg2']
        stream_url = f"{SOSAC_API}serials/{_id}/watching-time?username={sosac_user}&password={sosac_passwordhash}&d=19"
    elif stream == "into-queue" :
        _id = kwargs['arg2']
        stream_url = f"{SOSAC_API}serials/{_id}/into-queue?username={sosac_user}&password={sosac_passwordhash}"
        respse = requests.post(stream_url,data={})
        debug("stream_url %s"%stream_url,2)
        return
    elif stream == "off-queue" :
        _id = kwargs['arg2']
        stream_url = f"{SOSAC_API}serials/{_id}/off-queue?username={sosac_user}&password={sosac_passwordhash}"
        respse = requests.post(stream_url,data={})
        debug("stream_url %s"%stream_url,2)
        return

    elif "episodes" == episodes :
        _id = kwargs['arg2'] 
        if _id != "22" :
            stream_url = f"{SOSAC_API}episodes/{_id}?username={sosac_user}&password={sosac_passwordhash}"
        else :
            stream_url = f"{SOSAC_API}episodes/lists/{stream}?pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"


    else : 
        stream_url = f"{SOSAC_API}serials/lists/{stream}?pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"

    debug("stream_url %s"%stream_url,2)    
    return stream_url

def set_sosac_epi(sais_id) :
    sosac_passwordhash = passhash()
    sais_id = int(sais_id)
    stream_url = f"{SOSAC_API}serials/{sais_id}?username={sosac_user}&password={sosac_passwordhash}"
    debug("set_sosac_epi stream_url %s"%stream_url,2)
    return stream_url

def set_sosac_guide(day,page) :
    sosac_passwordhash = passhash()
    stream_url = f"{SOSAC_API}tv/program?d={day}&pocet=100&stranka={page}&username={sosac_user}&password={sosac_passwordhash}"
    debug("set_sosac_guide stream_url %s"%stream_url,2)
    return stream_url

############################################
# Místní profily: jeden účet Sosac, ale víc diváků.
# Profil "main" ukládá zhlédnutí na server Sosacu (sdílené se sosac.tv a ostatními
# zařízeními). Ostatní profily si zhlédnutí a pozice "pokračovat od" ukládají jen
# v tomto Kodi (soubor watch_<id>.json), takže se navzájem nepřepisují.
MAIN_PROFILE = "main"
PROFILES_FILE = os.path.join(profilepath, "profiles.json")

def _json_load(path, default) :
    try :
        with open(path, "r", encoding="utf-8") as f :
            return json.load(f)
    except Exception :
        return default

def _json_save(path, data) :
    try :
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f :
            json.dump(data, f)
        os.replace(tmp, path)
    except Exception as e :
        debug("json save error %s %s"%(path, e), 2)

def load_profiles() :
    data = _json_load(PROFILES_FILE, None)
    if not isinstance(data, dict) or not data.get("profiles") :
        data = {"active": MAIN_PROFILE,
                "profiles": [{"id": MAIN_PROFILE, "name": translate(30461)},
                             {"id": "p2", "name": translate(30462)}]}
        _json_save(PROFILES_FILE, data)
    return data

def save_profiles(data) :
    _json_save(PROFILES_FILE, data)

def active_profile() :
    data = load_profiles()
    for p in data["profiles"] :
        if p["id"] == data.get("active") :
            return p
    return data["profiles"][0]

def is_local_profile() :
    return active_profile()["id"] != MAIN_PROFILE

def _watch_file(pid=None) :
    return os.path.join(profilepath, "watch_%s.json" % (pid or active_profile()["id"]))

def local_watch_all(pid=None) :
    data = _json_load(_watch_file(pid), {})
    data.setdefault("movies", {}); data.setdefault("episodes", {})
    return data

def local_watch_set(kind, item_id, w=None, meta=None) :
    # kind = "movies" / "episodes"; ukládá pozici a údaje pro výpis Rozkoukané/Historie
    kind = "movies" if kind == "movies" else "episodes"
    data = local_watch_all()
    entry = data[kind].get(str(item_id), {"w": 0})
    if w is not None :
        entry["w"] = int(w)
        entry["t"] = int(time.time())
    if meta :
        keep = ("_id", "l", "n", "ne", "dl", "i", "ie", "b", "p", "y", "g", "ep", "s", "d", "q", "c", "m", "r", "o", "oi", "f", "h", "e", "k", "t", "mp", "cp")
        entry["meta"] = dict((k, v) for k, v in meta.items() if k in keep)
        if meta.get("dl") : entry["dl"] = meta["dl"]
    data[kind][str(item_id)] = entry
    _json_save(_watch_file(), data)

def _kind_for_url(url) :
    path = url.split("?")[0]
    if "/tv/program" in path : return None
    if "/episodes/" in path : return "episodes"
    if "/serials/lists" in path or "/serials/simple-search" in path or "/serials/advanced-search" in path : return "serials"
    if "/serials/" in path : return "serial-detail"
    if "/movies/" in path : return "movies"
    return None

def apply_local_watch(obj, url) :
    """Ve odpovědi serveru nahradí pole "w" (zhlédnuto/pozice) hodnotami místního profilu."""
    store = local_watch_all()
    child_kind = {"movie": "movies", "episode": "episodes", "serial": "serials", "info": "serials"}
    def walk(o, kind) :
        if isinstance(o, list) :
            for x in o : walk(x, kind)
        elif isinstance(o, dict) :
            if "_id" in o and "w" in o and kind in ("movies", "episodes", "serials") :
                k = "episodes" if (kind == "episodes" or "ep" in o) else kind
                if k == "serials" :
                    o["w"] = 0
                else :
                    o["w"] = store[k].get(str(o["_id"]), {}).get("w", 0)
            for key, val in o.items() :
                if isinstance(val, (dict, list)) :
                    sub = child_kind.get(key)
                    if sub is None :
                        sub = "episodes" if kind in ("serial-detail", "serials") else kind
                    walk(val, sub)
    walk(obj, _kind_for_url(url))
    return obj

def set_sosac_watchTime(type_id, stream_id, time_val) :
    if is_local_profile() :
        local_watch_set(type_id, stream_id, w=time_val)
        debug("profile %s: local watch %s %s %s"%(active_profile()["id"], type_id, stream_id, time_val), 1)
        return
    sosac_passwordhash = passhash()
    time_val = int(time_val)
    data = {"time":int(time_val)}
    stream_url = f"{SOSAC_API}{type_id}/{stream_id}/watching-time?username={sosac_user}&password={sosac_passwordhash}&d=19"
    hdrs = {'Content-Type': 'application/json'}
    respse = requests.post(stream_url, json=data, headers=hdrs)
    debug("mark as watched time_val %s %s"%(time_val,stream_url),2)
    #debug("mark as watched repse %s"%respse.status_code,2)
    return

def get_title(dest) :
    not_name = os.path.basename(dest)
    item_id = not_name.split("-")[0]
    is_movie = os.path.basename(os.path.dirname(dest)) == "movies"
    link = set_sosac_info("id",**{'arg2':item_id}) if is_movie else set_sosac_ser("",**{'arg2':item_id,'arg3':"episodes",'arg4':""})
    debug("downloadFil link %s"%link,2)
    source = requests.get(link).text
    data = json.loads(source)
    vid_title = data["n"]["cs"][0] if type(data["n"]["cs"]) == type([]) else data["n"]["cs"]
    if not is_movie :
        epi_nb = str(data["ep"]) if len(str(data["ep"])) > 1 else "0" + str(data["ep"])
        sai_nb = str(data["s"]) if len(str(data["s"])) > 1 else "0" + str(data["s"])                    
        vid_title = f'{vid_title} {sai_nb}x{epi_nb}'
    return vid_title
    
