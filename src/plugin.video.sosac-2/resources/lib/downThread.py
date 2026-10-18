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
            
def downloadTh(vid_name, url, dest):
    global lastPd
    thread_act2 = threading.enumerate()
    debug("downloadTh threading.enumerate %s"%thread_act2, 2)
    vid_id = threading.current_thread().name
    lastPd[vid_id] = 0
    
    result = None
    try :
        result = urlretrieve(url,dest,lambda nb, bs, fs, url=url: _pbhook(nb,bs,fs,url,vid_name))
    except Exception as e  :
        debug("download retrieve error %s"%str(e), 2)
        notify(vid_name,"%s"%translate(30079),time=5000)
    
    if not result and os.path.exists(dest) : os.remove(dest)
    '''
    else :
        updDownList(url)
        
    '''
    debug("downloadTh %s"%(threading.current_thread().name),2)
          
        
 
def _pbhook(numblocks, blocksize, filesize, url,vid_name):
    global lastP,lastPd
    try : 
        lock.acquire()
        v_id = threading.current_thread().name
        #debug("_pbhook 00 lastP[v_id] %s %s"%(v_id,lastPd[v_id]),2)
        if not lastPd[v_id]  : lastPd[v_id] = 0
        lastP = lastPd[v_id]
        #debug("_pbhook 01 lastP[vid_name] %s %s"%(vid_name,lastPd[vid_name]),2)
    except Exception as e :
        debug("download _pbhook exception %s"%str(e), 2)
    notifyEnabled = addon.getSetting('download-notify') == 'true'
    notifyEvery = addon.getSetting('download-notify-every')
    notifyPercent = down_int[int(notifyEvery)]
    try:
        #tt = threading.current_thread().name
        #debug("_pbhook 1 %s"%(threading.current_thread().name),2)
        percent = min((numblocks*blocksize*100)/filesize, 100) if filesize > 0 else 0
        if notifyEnabled:
            #if int(percent) > 0 and ((percent-lastP[vid_name]) >= int(notifyPercent)) :
            if int(percent) > 0 and ((percent-lastP) >= int(notifyPercent)) :
                #message = ' %s percent  - %s KB/s %s' % (percent,speed, esTime)
                #notify(message, filename)
                
                lastP = int(percent)
                try :
                    lastPd[v_id] = int(percent)
                except Exception as e :
                    debug("download _pbhook lastP[v_id] = int(percent) exception %s"%str(e), 2)
                print("passage pour percent ",percent)
                
                notify(vid_name,"%s %s "%(translate(30077),str(int(percent))),time=2000)

        if int(percent) >= int(100) :
            notify(vid_name,"%s %s"%(translate(30078),str(percent)),time=2000)
            try :
                updDownList(url)
            except Exception as e :
                debug("_pbhook updDownList exception %s"%str(e), 2)
            #return True
        #debug("_pbhook 2 %s"%(threading.current_thread().name),2)
        '''
        try :
            debug("_pbhook 3 lastP[v_id] %s %s"%(vid_name,lastPd[v_id]),2)
        except Exception as e :
            debug("download _pbhook 3 exception ", str(e))
        '''
        lock.release()
    except Exception as e :
        debug("_pbhook download exception %s"%str(e), 2)
        try : lock.release()
        except RuntimeError : pass
        percent = locals().get("percent", 0)
        if int(percent) >= int(100) :
            notify(vid_name,"%s %s"%(translate(30078),str(percent)),time=2000)
            return True
        else :
            notify(vid_name,"%s %s"%(translate(30079),str(percent)),time=2000)
            return False
    
    
    

    
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
            try :
                url = it["resolve"]() if callable(it["resolve"]) else it["resolve"]
                if not url :
                    raise Exception("no stream url")
                notify(title, "%s (%s/%s)" % (translate(30076), n, total), time=3000)
                lastPd[threading.current_thread().name] = 0
                downloadTh(title, url, it["dest"])
                if os.path.isfile(it["dest"]) and os.path.getsize(it["dest"]) > 0 :
                    done += 1
                    if it.get("subs") :
                        try :
                            it["subs"]()
                        except Exception as e :
                            debug("run_queue subs error %s"%e, 2)
            except Exception as e :
                debug("run_queue item error %s %s"%(title, e), 2)
                notify(title, translate(30079), time=3000)
        notify(translate(30402), tr(30419, done, total), time=8000)

    if not items :
        return None
    notify(translate(30402), tr(30431, len(items)), time=4000)
    th = threading.Thread(target=worker, name="sosac-queue")
    th.start()
    return th
