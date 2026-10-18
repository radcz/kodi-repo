import os, time, re, json, requests
import threading
import xbmcgui, xbmcvfs, xbmcplugin
from urllib.request import urlretrieve
from resources.lib.util import *
#from resources.lib.plugin import get_url
lastPd = {}
lastP = 0
nb_downl = 10    
a = 0
lock = threading.RLock()

def updDownList(url) :
    if xbmcvfs.exists(downListPath) :
            with open(downListPath, 'r', encoding="utf-8") as f :
                content = f.read()
            sais_list = re.findall("(?s)'(https.*?)'.*?'(.*?)'",content)
            f = open(downListPath, 'w', encoding="utf-8")  
            for i in  sais_list :
                if url not in i :                           
                    f.write(str(i) + "\n")                
            f.close()
            
PROGRESS_FILE = os.path.join(profilepath, "down_progress.json")
STALE_SECONDS = 600   # záznam bez aktualizace déle než 10 min = přerušené stahování

class DownloadCancelled(Exception) :
    pass

def _read_progress() :
    try :
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f :
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception :
        return {}

def _write_progress(data) :
    try :
        tmp = PROGRESS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f :
            json.dump(data, f)
        os.replace(tmp, PROGRESS_FILE)
    except Exception as e :
        debug("progress write error %s"%e, 2)

def progress_update(dest, **fields) :
    # sdílený stav stahování pro výpis "Stažené" (i mezi různými spuštěními doplňku)
    with lock :
        data = _read_progress()
        entry = data.get(dest, {})
        entry.update(fields)
        now = time.time()
        entry["ts"] = now
        data[dest] = entry
        owner = entry.get("owner")
        if owner :
            # položky stejné fronty jsou "živé", dokud fronta stahuje
            for other in data.values() :
                if other.get("owner") == owner :
                    other["ts"] = now
        _write_progress(data)
        return entry

def progress_remove(dest) :
    with lock :
        data = _read_progress()
        if dest in data :
            del data[dest]
            _write_progress(data)

def progress_all() :
    # {cesta: {"title", "percent" (-1 = čeká ve frontě), "done_mb", "total_mb", "speed", "stale"}}
    data = _read_progress()
    now = time.time()
    changed = False
    for dest, entry in list(data.items()) :
        age = now - entry.get("ts", 0)
        if age > 86400 :
            del data[dest]; changed = True
            continue
        entry["stale"] = age > STALE_SECONDS
    if changed :
        _write_progress(data)
    return data

def cancel_download(dest) :
    if dest in _read_progress() :
        progress_update(dest, cancel=True)
        return True
    return False

def _fmt_mb(mb) :
    return "%.1f GB" % (mb / 1024.0) if mb >= 1024 else "%d MB" % mb

def downloadTh(vid_name, url, dest, owner=None):
    """Stáhne jedno video. Průběh ukazuje lištou v rohu Kodi a zapisuje do down_progress.json."""
    vid_id = threading.current_thread().name
    lastPd[vid_id] = 0
    state = {"last_pct": -1, "last_write": 0, "t0": time.time(), "notified": 0}
    bar = None
    try :
        bar = xbmcgui.DialogProgressBG()
        bar.create(translate(30402), "%s - %s" % (vid_name, translate(30076)))
    except Exception as e :
        debug("progress bar error %s"%e, 2)
        bar = None
    if owner is None and _read_progress().get(dest, {}).get("cancel") :
        return False
    progress_update(dest, title=vid_name, percent=0, done_mb=0, total_mb=0, speed=0, owner=owner)

    def hook(numblocks, blocksize, filesize) :
        done = numblocks * blocksize
        pct = int(min(done * 100 / filesize, 100)) if filesize > 0 else 0
        now = time.time()
        if pct == state["last_pct"] and now - state["last_write"] < 5 :
            return
        state["last_pct"] = pct
        elapsed = max(now - state["t0"], 0.001)
        speed = done / 1048576.0 / elapsed
        done_mb, total_mb = done / 1048576.0, (filesize / 1048576.0 if filesize > 0 else 0)
        entry = progress_update(dest, percent=pct, done_mb=round(done_mb, 1), total_mb=round(total_mb, 1), speed=round(speed, 2))
        state["last_write"] = now
        if entry.get("cancel") :
            raise DownloadCancelled()
        if bar :
            try :
                msg = "%s  %d %%" % (vid_name, pct)
                if total_mb :
                    msg += "  (%s / %s, %.1f MB/s)" % (_fmt_mb(done_mb), _fmt_mb(total_mb), speed)
                bar.update(pct, translate(30402), msg)
            except Exception :
                pass
        # původní oznámení po X % (nastavení "download-notify")
        try :
            if addon.getSetting('download-notify') == 'true' :
                step = down_int[int(addon.getSetting('download-notify-every') or 0)]
                if 0 < pct < 100 and pct - state["notified"] >= step :
                    state["notified"] = pct
                    notify(vid_name, "%s %s" % (translate(30077), pct), time=2000)
        except Exception :
            pass

    result = None
    cancelled = False
    try :
        result = urlretrieve(url, dest, hook)
    except DownloadCancelled :
        cancelled = True
        notify(vid_name, translate(30441), time=4000)
    except Exception as e  :
        debug("download retrieve error %s"%str(e), 2)
        notify(vid_name, translate(30079), time=5000)
    finally :
        if bar :
            try : bar.close()
            except Exception : pass
        progress_remove(dest)

    if (cancelled or not result) and os.path.exists(dest) :
        try : os.remove(dest)
        except OSError : pass
    if result and not cancelled :
        notify(vid_name, translate(30078), time=4000)
        try :
            updDownList(url)
        except Exception as e :
            debug("updDownList error %s"%e, 2)
    return bool(result) and not cancelled

def _pbhook(numblocks, blocksize, filesize, url, vid_name):
    # ponecháno kvůli kompatibilitě, průběh teď řeší downloadTh
    return None

def downloadFil(url, dest):
    thread_act = threading.enumerate()
    print("Main thread name: {}".format(threading.current_thread().name))
    
    vid_name = dest.split("/")[-1] #if "/" in dest else dest.split("\\")[-1]
    vid_name = vid_name.replace(".mp4","")
    vid_name = vid_name.split("-")[0]
    vid_title = get_title(dest)    
    threading.Thread(target = downloadTh, name=vid_name, args =[vid_title, url,dest]).start()
    notify(vid_title,translate(30076),time=5000)


def downloadFil2(url, dest):
    thread_act = threading.enumerate()
    vid_name1 = dest if "/" in dest else dest.replace("\\","/")
    vid_name = vid_name1.split("/")[-1] #if "/" in dest else dest.split("\\")[-1]
    vid_name = vid_name.replace(".mp4","")
    vid_name = vid_name.split("-")[0]
    vid_title = get_title(dest)
    notify(vid_title,translate(30076),time=5000)
    threading.Thread(target = downloadTh,  name=vid_name,args =[vid_title, url,dest]).start()    
    #th.setDaemon(True)
    #th.start()
    debug("Main thread name: {}".format(threading.current_thread().name),2)


def run_queue(items) :
    """Stáhne položky postupně (jedno video po druhém) ve vlákně na pozadí.

    items: seznam slovníků {"title", "dest", "resolve", "subs"}
      resolve - URL videa, nebo funkce, která ho zjistí až těsně před stažením
                (odkazy ze streamovací služby po čase vyprší)
      subs    - volitelná funkce, která uloží titulky
    """
    def worker() :
        total = len(items)
        done = 0
        monitor = xbmc.Monitor()
        for n, it in enumerate(items, 1) :
            if monitor.abortRequested() :
                break
            title = it.get("title") or os.path.basename(it["dest"])
            if _read_progress().get(it["dest"], {}).get("cancel") :
                progress_remove(it["dest"])
                continue
            try :
                url = it["resolve"]() if callable(it["resolve"]) else it["resolve"]
                if not url :
                    raise Exception("no stream url")
                notify(title, "%s (%s/%s)" % (translate(30076), n, total), time=3000)
                lastPd[threading.current_thread().name] = 0
                if downloadTh(title, url, it["dest"], owner) :
                    done += 1
                    if it.get("subs") :
                        try :
                            it["subs"]()
                        except Exception as e :
                            debug("run_queue subs error %s"%e, 2)
            except Exception as e :
                debug("run_queue item error %s %s"%(title, e), 2)
                progress_remove(it["dest"])
                notify(title, translate(30079), time=3000)
        notify(translate(30402), tr(30419, done, total), time=8000)

    if not items :
        return None
    owner = "%s-%s" % (os.getpid(), int(time.time() * 1000))
    for it in items :
        progress_update(it["dest"], title=it.get("title") or os.path.basename(it["dest"]), percent=-1, done_mb=0, total_mb=0, speed=0, cancel=False, owner=owner)
    notify(translate(30402), tr(30431, len(items)), time=4000)
    th = threading.Thread(target=worker, name="sosac-queue")
    th.start()
    return th
