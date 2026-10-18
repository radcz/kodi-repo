import sys, json, os, shutil
from datetime import datetime as dt
from datetime import timedelta
import threading
import xbmc, xbmcvfs
from resources.lib import plugin
from resources.lib.plugin import upd_download
from resources.lib.util import *
addon_id = 'plugin.video.sosac-2'
addon_name_ = 'Sosac.TV'
addon = xbmcaddon.Addon(addon_id)
__set__ = addon.getSetting
start_boot = __set__('start-boot')
check_episodes = [12,1,3,7,30]
del_day = check_episodes[int(__set__('check-episodes'))]
addonPath = xbmcvfs.translatePath(addon.getAddonInfo('path'))
HOME = xbmcvfs.translatePath("special://home")
addonsPath = xbmcvfs.translatePath('special://home/addons')
servicezipPath = xbmcvfs.translatePath(os.path.join(addonPath, "resources","extras","service.autoexec.zip"))
servicePath = xbmcvfs.translatePath(os.path.join(addonsPath, "service.autoexec/"))
initAddon = __set__("ouv")
fl_upd = __set__("fl_update")
dat_upd = __set__("dat_update")
if dat_upd == "" : dat_upd = "0"
hr_upd = __set__("hr_update")
if hr_upd == "" : hr_upd = "0"
fl_db = __set__("fl_db")

dtnow = dt.now()
today = dtnow.strftime("%Y-%m-%d")

# Původně se tu při každém otevření složky přepisoval globální advancedsettings.xml
# (Kodi pak nikde neukládal pozice ani zhlédnutí) a mazaly se všechny záložky
# přehrávání v MyVideos*.db, i u ostatních doplňků. Sosac si pozice ukládá na serveru.

date_del = dt.now() - timedelta(days=del_day)
dt_del = int(date_del.timestamp())
dt_upd = int(dtnow.timestamp())

if del_day == 12 :
    der_dat = int(dat_upd) + 43200
    xbmc.log("dafault  upd_download der_dat %s"%str(der_dat), xbmc.LOGDEBUG)
    #if int(dat_upd) <= dt_del and dt_upd >= der_dat :
    if dt_upd >= der_dat :
        xbmc.log("dafault  upd_download 12h start %s"%str(der_dat), xbmc.LOGDEBUG)
        thread = threading.Thread(target = upd_download,  args =[del_day])
        thread.start()
        addon.setSetting("fl_update",today)
        dt_upd = int(dtnow.timestamp())
        addon.setSetting("dat_update",str(dt_upd))

elif int(dat_upd) <= dt_del and fl_upd != today :
        thread = threading.Thread(target = upd_download,  args =[del_day])
        thread.start()
        addon.setSetting("fl_update",today)
        dt_upd = int(dtnow.timestamp())
        addon.setSetting("dat_update",str(dt_upd))


plugin.run()
