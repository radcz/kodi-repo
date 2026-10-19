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

class DownloadPaused(Exception) :
    pass

class DownloadSkipped(Exception) :
    # video nesplňuje požadovanou kvalitu (např. není ve 4K)
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
    # {cesta: {"title", "percent" (-1 = čeká), "status", "done_mb", "total_mb", "speed", "stale"}}
    # status: queued / active / paused / error ; "stale" = aktivní, ale bez aktualizace (Kodi zavřené)
    data = _read_progress()
    now = time.time()
    changed = False
    for dest, entry in list(data.items()) :
        age = now - entry.get("ts", 0)
        keep = 30 * 86400 if entry.get("status") in ("paused", "error") or os.path.exists(part_path(dest)) else 86400
        if age > keep :
            del data[dest]; changed = True
            continue
        entry["stale"] = entry.get("status") not in ("paused", "error") and age > STALE_SECONDS
    if changed :
        _write_progress(data)
    return data

def part_path(dest) :
    return dest + ".part"

def is_running(entry) :
    return entry.get("status") in ("active", "queued") and not entry.get("stale")

def cancel_download(dest) :
    # běžící stahování se ukončí samo (zjistí příznak), pozastavené/přerušené uklidíme hned
    data = progress_all()
    entry = data.get(dest)
    if entry is None :
        return False
    if is_running(entry) :
        progress_update(dest, cancel=True)
    else :
        progress_remove(dest)
        try :
            if os.path.exists(part_path(dest)) : os.remove(part_path(dest))
        except OSError :
            pass
    return True

def pause_download(dest) :
    entry = progress_all().get(dest)
    if entry is None :
        return False
    if is_running(entry) :
        progress_update(dest, pause=True)
    return True

def _fmt_mb(mb) :
    return "%.1f GB" % (mb / 1024.0) if mb >= 1024 else "%d MB" % mb

def _http_download(url, part, hook) :
    """Stáhne url do souboru part; když part existuje, naváže přes HTTP Range."""
    offset = os.path.getsize(part) if os.path.exists(part) else 0
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0 Safari/537.36"}
    if offset :
        headers["Range"] = "bytes=%d-" % offset
    with requests.get(url, headers=headers, stream=True, timeout=30) as r :
        if r.status_code == 416 and offset :
            return offset, offset          # soubor je už celý
        r.raise_for_status()
        if offset and r.status_code != 206 :
            offset = 0                     # server navázání neumí: od začátku
        length = int(r.headers.get("Content-Length") or 0)
        total = offset + length if length else 0
        done = offset
        hook(done, total)
        with open(part, "ab" if offset else "wb") as f :
            for chunk in r.iter_content(chunk_size=1024 * 1024) :
                if not chunk :
                    continue
                f.write(chunk)
                done += len(chunk)
                hook(done, total)
    if total and done < total :
        raise IOError("neúplné stažení %d / %d" % (done, total))
    return done, total

def downloadTh(vid_name, url, dest, owner=None, info=None):
    """Stáhne jedno video do dest (přes dest.part). Průběh ukazuje lištou v rohu Kodi
    a zapisuje do down_progress.json. Vrací True (staženo), False (chyba/zrušeno/pozastaveno).
    info = údaje pro pozdější navázání (např. link a kvalita u Sosacu)."""
    vid_id = threading.current_thread().name
    lastPd[vid_id] = 0
    part = part_path(dest)
    prev = _read_progress().get(dest, {})
    if prev.get("cancel") :
        cancel_download(dest)
        return False
    if prev.get("pause") and prev.get("status") == "queued" :
        progress_update(dest, status="paused", pause=False)
        return False
    fields = dict(title=vid_name, status="active", url=url, pause=False, cancel=False, owner=owner)
    if info :
        fields["info"] = info
    if not os.path.exists(part) :
        fields.update(percent=0, done_mb=0, total_mb=0, speed=0)
    progress_update(dest, **fields)
    state = {"last_pct": -1, "last_write": 0, "t0": time.time(), "start": None, "notified": 0}
    bar = None
    try :
        bar = xbmcgui.DialogProgressBG()
        bar.create(translate(30402), "%s - %s" % (vid_name, translate(30076)))
    except Exception as e :
        debug("progress bar error %s"%e, 2)
        bar = None

    def hook(done, total) :
        if state["start"] is None :
            state["start"] = done          # rychlost počítat jen z nově stažených dat
        pct = int(min(done * 100 / total, 100)) if total > 0 else 0
        now = time.time()
        if pct == state["last_pct"] and now - state["last_write"] < 3 :
            return
        state["last_pct"] = pct
        elapsed = max(now - state["t0"], 0.001)
        speed = (done - state["start"]) / 1048576.0 / elapsed
        done_mb, total_mb = done / 1048576.0, total / 1048576.0
        entry = progress_update(dest, percent=pct, done_mb=round(done_mb, 1), total_mb=round(total_mb, 1), speed=round(speed, 2))
        state["last_write"] = now
        if entry.get("cancel") :
            raise DownloadCancelled()
        if entry.get("pause") :
            raise DownloadPaused()
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

    ok = False
    try :
        _http_download(url, part, hook)
        os.replace(part, dest)
        progress_remove(dest)
        ok = True
        notify(vid_name, translate(30078), time=4000)
        try :
            updDownList(url)
        except Exception as e :
            debug("updDownList error %s"%e, 2)
    except DownloadPaused :
        progress_update(dest, status="paused", pause=False, speed=0)
        notify(vid_name, translate(30454), time=4000)
    except DownloadCancelled :
        progress_remove(dest)
        try :
            if os.path.exists(part) : os.remove(part)
        except OSError :
            pass
        notify(vid_name, translate(30441), time=4000)
    except Exception as e  :
        debug("download error %s"%str(e), 2)
        if os.path.exists(part) and os.path.getsize(part) > 0 :
            # rozstahovaný soubor necháme, jde na něj navázat přes "Pokračovat"
            progress_update(dest, status="error", pause=False, speed=0)
        else :
            progress_remove(dest)
            try :
                if os.path.exists(part) : os.remove(part)
            except OSError :
                pass
        notify(vid_name, translate(30079), time=5000)
    finally :
        if bar :
            try : bar.close()
            except Exception : pass
    return ok

def _pbhook(numblocks, blocksize, filesize, url, vid_name):
    # ponecháno kvůli kompatibilitě, průběh teď řeší downloadTh
    return None

def downloadFil(url, dest, info=None):
    thread_act = threading.enumerate()
    print("Main thread name: {}".format(threading.current_thread().name))
    
    vid_name = dest.split("/")[-1] #if "/" in dest else dest.split("\\")[-1]
    vid_name = vid_name.replace(".mp4","")
    vid_name = vid_name.split("-")[0]
    vid_title = get_title(dest)    
    threading.Thread(target = downloadTh, name=vid_name, args =[vid_title, url,dest], kwargs={"info": info}).start()
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
        skipped = 0
        monitor = xbmc.Monitor()
        for n, it in enumerate(items, 1) :
            if monitor.abortRequested() :
                break
            title = it.get("title") or os.path.basename(it["dest"])
            flags = _read_progress().get(it["dest"], {})
            if flags.get("cancel") :
                cancel_download(it["dest"])
                continue
            if flags.get("pause") :
                progress_update(it["dest"], status="paused", pause=False)
                continue
            try :
                url = it["resolve"]() if callable(it["resolve"]) else it["resolve"]
                if not url :
                    raise Exception("no stream url")
                notify(title, "%s (%s/%s)" % (translate(30076), n, total), time=3000)
                lastPd[threading.current_thread().name] = 0
                if downloadTh(title, url, it["dest"], owner, it.get("info")) :
                    done += 1
                    if it.get("subs") :
                        try :
                            it["subs"]()
                        except Exception as e :
                            debug("run_queue subs error %s"%e, 2)
            except DownloadSkipped :
                skipped += 1
                progress_remove(it["dest"])
                notify(title, translate(30451), time=3000)
            except Exception as e :
                debug("run_queue item error %s %s"%(title, e), 2)
                if os.path.exists(part_path(it["dest"])) :
                    progress_update(it["dest"], status="error", speed=0)   # jde zkusit znovu přes Pokračovat
                else :
                    progress_remove(it["dest"])
                notify(title, translate(30079), time=3000)
        summary = tr(30419, done, total)
        if skipped :
            summary += ", " + tr(30453, skipped)
        notify(translate(30402), summary, time=8000)

    if not items :
        return None
    owner = "%s-%s" % (os.getpid(), int(time.time() * 1000))
    for it in items :
        old = _read_progress().get(it["dest"], {})
        fields = dict(title=it.get("title") or os.path.basename(it["dest"]), status="queued", speed=0, cancel=False, pause=False, owner=owner)
        if it.get("info") :
            fields["info"] = it["info"]
        if not os.path.exists(part_path(it["dest"])) :
            fields.update(percent=-1, done_mb=0, total_mb=0)
        elif "percent" not in old :
            fields["percent"] = 0
        progress_update(it["dest"], **fields)
    notify(translate(30402), tr(30431, len(items)), time=4000)
    th = threading.Thread(target=worker, name="sosac-queue")
    th.start()
    return th
