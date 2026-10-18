# -*- coding: utf-8 -*-
# Copyright: (c) 2020, SylvainCecchetto, wwark
# GNU General Public License v2.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-2.0.txt)


import xbmc, xbmcaddon, xbmcvfs, xbmcgui
import os, re, json, glob, requests
import xml.etree.ElementTree as ET

from resources.lib.util import *
from resources.lib import extract

addon_id = 'plugin.video.sosac-2'
SKIN_ID = 'skin.estuary-sosac'
addon = xbmcaddon.Addon(addon_id)
addonPath = xbmcvfs.translatePath(addon.getAddonInfo('path'))
addonsPath = xbmcvfs.translatePath('special://home/addons')
skinPath = os.path.join(addonsPath, SKIN_ID)
sourcesPath = xbmcvfs.translatePath('special://profile/sources.xml')

languagePathEn = os.path.join(addonPath, "resources", "language", "resource.language.en_gb", "strings.po")
languagePathCZ = os.path.join(addonPath, "resources", "language", "resource.language.cs_cz", "strings.po")

DOMAIN = ["https://kodi-api.sosac.to/settings","https://tv.sosac.ph/settings.json","https://sosac.eu/settings.json",
    "https://tv.prehraj.net/settings.json","https://tv.pustsi.me/settings.json","https://www.tvserialy.net/settings.json",
        "http://178.17.171.217/settings.json"]

# Zdroje ve Správci souborů (Nastavení -> Správce souborů), aby se nemusely zadávat ručně.
FILE_SOURCES = [
    ("radcz repozitář", "https://radcz.github.io/kodi-repo/"),
    ("https://kodi.sosac.to", "https://kodi.sosac.to/"),
    ("http://kodi.crocody.com/ - Prehraj.to", "http://kodi.crocody.com/"),
    ("https://dobbelina.github.io/", "https://dobbelina.github.io/"),
    ("https://k.slyguy.xyz/ - HBO", "https://k.slyguy.xyz/"),
]

SOURCES_TEMPLATE = """<sources>
    <programs><default pathversion="1"></default></programs>
    <video><default pathversion="1"></default></video>
    <music><default pathversion="1"></default></music>
    <pictures><default pathversion="1"></default></pictures>
    <files><default pathversion="1"></default></files>
    <games><default pathversion="1"></default></games>
</sources>
"""


def version_tuple(ver):
    return tuple(int(x) for x in re.findall(r'\d+', ver or "0"))


def autorun_addon():
    try :
        if int(addon.getSetting("start-boot")) == 0:
            xbmc.executebuiltin('RunAddon(%s)' % addon_id)
    except ValueError :
        pass


def bundled_skin():
    # Nejnovější skin přibalený v resources/extras (skin.estuary-sosac-X.Y.Z.zip).
    zips = glob.glob(os.path.join(addonPath, "resources", "extras", SKIN_ID + "-*.zip"))
    if not zips :
        return None, None
    zips.sort(key=lambda p: version_tuple(os.path.basename(p)[len(SKIN_ID):]))
    zip_path = zips[-1]
    return zip_path, os.path.basename(zip_path)[len(SKIN_ID) + 1:-4]


def installed_skin_version():
    try :
        with open(os.path.join(skinPath, "addon.xml"), encoding="utf-8") as f :
            return re.search(r'<addon[^>]*\sversion="([^"]+)"', f.read()).group(1)
    except Exception :
        return None


def skin_install():
    zip_path, bundled_ver = bundled_skin()
    if not zip_path :
        return
    installed_ver = installed_skin_version()
    if installed_ver and version_tuple(installed_ver) >= version_tuple(bundled_ver) :
        if not xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % SKIN_ID) :
            enable_skin()
        return

    xbmc.log("Sosac: instaluji %s %s (bylo %s)" % (SKIN_ID, bundled_ver, installed_ver), xbmc.LOGINFO)
    if not extract.allNoProgress(zip_path, addonsPath) :
        return
    # Kodi nově rozbalený skin zaregistruje hned, bez nutnosti restartu.
    xbmc.executebuiltin('UpdateLocalAddons', True)
    enable_skin()


def enable_skin():
    monitor = xbmc.Monitor()
    for _ in range(20) :
        response = json.loads(xbmc.executeJSONRPC(json.dumps({"jsonrpc":"2.0","id":1,
            "method":"Addons.SetAddonEnabled","params":{"addonid":SKIN_ID,"enabled":True}})))
        if "error" not in response and xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % SKIN_ID) :
            return True
        if monitor.waitForAbort(0.5) :
            break
    xbmc.log("Sosac: skin %s se nepodařilo povolit" % SKIN_ID, xbmc.LOGWARNING)
    return False


def ensure_sources():
    # Přidá chybějící zdroje do sources.xml. Každý se přidá jen jednou, takže
    # zdroj, který uživatel sám smaže, se už znovu nevrací.
    done = [x for x in addon.getSetting("sources_added").split("|") if x]
    todo = [(name, path) for name, path in FILE_SOURCES if path not in done]
    if not todo :
        return
    try :
        if xbmcvfs.exists(sourcesPath) :
            tree = ET.parse(sourcesPath)
        else :
            tree = ET.ElementTree(ET.fromstring(SOURCES_TEMPLATE))
        root = tree.getroot()
        files = root.find("files")
        if files is None :
            files = ET.SubElement(root, "files")
            ET.SubElement(files, "default", {"pathversion": "1"})
        existing = {(s.findtext("path") or "").rstrip("/") for s in files.findall("source")}

        added = 0
        for name, path in todo :
            if path.rstrip("/") not in existing :
                source = ET.SubElement(files, "source")
                ET.SubElement(source, "name").text = name
                ET.SubElement(source, "path", {"pathversion": "1"}).text = path
                ET.SubElement(source, "allowsharing").text = "true"
                added += 1
            done.append(path)

        if added :
            if hasattr(ET, "indent") :   # Python 3.9+ (Kodi 19 na některých zařízeních má 3.8)
                ET.indent(tree, space="    ")
            tree.write(sourcesPath, encoding="utf-8")
            notify(translate(30402), translate(30414), 10000)
        addon.setSetting("sources_added", "|".join(done))
    except Exception as e :
        xbmc.log("Sosac: zdroje se nepodařilo přidat %s" % e, xbmc.LOGWARNING)


def patch_strings(path, data, patterns):
    with open(path, "r", encoding="utf-8") as f :
        original = f.read()
    text = original
    for ctx, key in (("30200", "streaming_provider_label"), ("30202", "domain_label")) :
        try :
            label = re.findall('(?s)msgctxt "#%s".*?msgid.*?"(.*?) User' % ctx, text)[0]
            if label != data[key] :
                text = text.replace(label, data[key])
        except (IndexError, KeyError) :
            pass
    for pat, repl in patterns :
        text = re.sub(pat, repl, text)
    if text != original :
        with open(path, "w", encoding="utf-8") as f :
            f.write(text)


def domain_save() :
    data = {}
    for item in DOMAIN :
        try :
            data = requests.get(item, timeout=10).json()
            if data.get("domain") and data.get("streaming_provider") :
                addon.setSetting("sosac_domain", data["domain"])
                addon.setSetting("streaming_provider", data["streaming_provider"])
                addon.setSetting("domain_actif", item)
                break
        except Exception as e:
            xbmc.log('domain_save error %s %s' % (item, e), xbmc.LOGWARNING)
            data = {}

    if not data :
        return

    common = [
        ('Account with this username and password does not exist on .*?"',
         'Account with this username and password does not exist on %s"' % data["domain"]),
        ('User account with this username and password does not exist on .*?"',
         'User account with this username and password does not exist on %s"' % data["streaming_provider"]),
    ]
    czech = [
        ('Pro neomezené přehrávání si prosím prodlužte premium na .*?/premium."',
         'Pro neomezené přehrávání si prosím prodlužte premium na %s/premium."' % data["streaming_provider"]),
        ('Heslo si můžete obnovit na .*?/recoverpassword',
         'Heslo si můžete obnovit na %s/recoverpassword' % data["streaming_provider"]),
        ('Heslo si můžete obnovit na .*?_',
         'Heslo si můžete obnovit na %s_' % data["domain"]),
    ]
    for path, patterns in ((languagePathEn, common), (languagePathCZ, common + czech)) :
        try :
            patch_strings(path, data, patterns)
        except Exception as e :
            xbmc.log('domain_save strings.po error %s' % e, xbmc.LOGWARNING)


if __name__ == '__main__':

    domain_save()
    skin_install()
    ensure_sources()
    autorun_addon()

    monitor = xbmc.Monitor()

    def set_skin(skin_id) :
        xbmc.executeJSONRPC(json.dumps({"jsonrpc":"2.0","id":1,"method":"Settings.SetSettingValue",
            "params":{"setting":"lookandfeel.skin","value":skin_id}}))

    # Výchozí: vzhled Sosacu (vychází z Estuary) jednou nastavit natrvalo. Každé přepnutí
    # vzhledu totiž Kodi potvrzuje dotazem "Ponechat vzhled?", což při přechodu mezi
    # doplňky vyskakovalo pořád dokola.
    if addon.getSetting("auto-skin") != "true" :
        if addon.getSetting("skin_fixed") != "true" and xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % SKIN_ID) :
            addon.setSetting("skin_fixed", "true")
            if xbmc.getSkinDir() != SKIN_ID :
                set_skin(SKIN_ID)

    while not monitor.abortRequested():
        # původní chování (jen když ho uživatel zapne v nastavení)
        if addon.getSetting("auto-skin") == "true" and xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % SKIN_ID) :
            plugin_name = xbmc.getInfoLabel('Container.PluginName')
            skindir = xbmc.getSkinDir()
            if "sosac-2" in plugin_name and skindir != SKIN_ID:
                addon.setSetting("skin", skindir)
                set_skin(SKIN_ID)
            elif plugin_name and "sosac-2" not in plugin_name and skindir == SKIN_ID:
                last_skin = addon.getSetting("skin")
                if last_skin and last_skin != SKIN_ID:
                    set_skin(last_skin)

        if monitor.waitForAbort(1):
            break
