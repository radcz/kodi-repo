# -*- coding: utf-8 -*-
"""Sestaví celý veřejný Kodi repozitář radcz/kodi-repo (GitHub Pages + raw.githubusercontent).

Použití (z libovolné složky):
    python3 tools/build_all.py

Výsledek přímo v kořeni repozitáře:
  addons.xml, addons.xml.md5      - čte Kodi (radcz Repository)
  <id doplňku>/<id>-<verze>.zip   - ZIPy pro aktualizace z repozitáře
  *.zip v kořeni + index.html     - instalace přes zdroj https://radcz.github.io/kodi-repo/
                                    (Apple TV, iPad i jiné Kodi bez počítače)
  src/                            - zdrojové kódy doplňků

Přihlašovací údaje se nikam nekopírují: berou se jen zdroje doplňků, nikdy userdata/addon_data.
"""
import hashlib
import os
import re
import shutil
import zipfile
from xml.etree import ElementTree as ET

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
WORK = os.path.normpath(os.path.join(REPO, '..', '..'))          # ~/Desktop/KODI -SOSAČ
URL = 'https://raw.githubusercontent.com/radcz/kodi-repo/main/'
REPO_VERSION = '1.0.3'

# doplňky v addons.xml (instalace a aktualizace přes radcz Repository)
ADDONS = {
    'repository.radek': os.path.join(WORK, 'freevideo', 'src', 'repository.radek'),
    'plugin.video.sosac-2': os.path.join(WORK, 'plugin.video.sosac-2'),
    'plugin.video.freevideo': os.path.join(WORK, 'freevideo', 'src', 'plugin.video.freevideo'),
    'plugin.video.prehrajto': os.path.join(WORK, 'prehrajto', 'src', 'plugin.video.prehrajto'),  # česká verze
    'repository.dobbelina': os.path.join(WORK, 'repozitare', 'repository.dobbelina'),
    # HBO Max: repozitář SlyGuy jde instalovat přímo z radcz Repository (samotné slyguy.max
    # a script.module.slyguy se sem nekopírují, aktualizují se ze SlyGuy)
    'repository.slyguy': os.path.join(WORK, 'repozitare', 'repository.slyguy'),
}
# jen ZIP ke stažení (aktualizují se ze svých vlastních zdrojů)
EXTRA = {
    'repository.sosacRepo': os.path.join(WORK, 'repozitare', 'repository.sosacRepo'),
    'repository.prehraj.to': os.path.join(WORK, 'repozitare', 'repository.prehraj.to'),
}
SKIP_DIRS = {'__pycache__', '.git', 'tests', 'addon_data', 'userdata'}
# session.json apod. ukládala původní verze Prehraj.to do složky doplňku (přihlášení!) - nikdy nebalit
SKIP_FILES = {'.DS_Store', 'settings.xml.bak', 'session.json', 'history.txt', 'resume.json', 'subtitles.txt',
              'update_check.txt', 'download_queue.json'}
SKIP_EXT = ('.pyc', '.bak', '.tmp')

REPO_ADDON_XML = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="repository.radek" name="[COLOR deepskyblue]radcz[/COLOR] [COLOR hotpink]Repository[/COLOR]" version="{version}" provider-name="radcz">
    <extension point="xbmc.addon.repository" name="radcz Repository">
        <dir>
            <info compressed="false">{url}addons.xml</info>
            <checksum>{url}addons.xml.md5</checksum>
            <datadir zip="true">{url}</datadir>
        </dir>
    </extension>
    <extension point="xbmc.addon.metadata">
        <summary lang="cs_CZ">Repozitář doplňků radcz (Sosac.TV, Prehraj.to česky, Video FREE, Dobbelina)</summary>
        <summary lang="en_GB">radcz add-on repository</summary>
        <description lang="cs_CZ">Opravený Sosac.TV, česká verze Prehraj.to, Video FREE a repozitář Dobbelina s aktualizacemi. Funguje na Macu, Windows, Androidu, Apple TV i iPadu.</description>
        <description lang="en_GB">Patched Sosac.TV, Czech Prehraj.to, Video FREE and the Dobbelina repository with updates. Works on macOS, Windows, Android, Apple TV and iPad.</description>
        <platform>all</platform>
        <assets>
            <icon>icon.png</icon>
        </assets>
    </extension>
</addon>
'''


def addon_info(src):
    root = ET.parse(os.path.join(src, 'addon.xml')).getroot()
    return root.get('id'), root.get('version')


def make_zip(src, dest_dir):
    addon_id, version = addon_info(src)
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, '%s-%s.zip' % (addon_id, version))
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for base, dirs, files in os.walk(src):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(files):
                if name in SKIP_FILES or name.endswith(SKIP_EXT):
                    continue
                full = os.path.join(base, name)
                zf.write(full, os.path.join(addon_id, os.path.relpath(full, src)))
    return path, version


def clean_old():
    for name in os.listdir(REPO):
        full = os.path.join(REPO, name)
        if name.endswith('.zip') or name in ('addons.xml', 'addons.xml.md5', 'index.html'):
            os.remove(full)
        elif os.path.isdir(full) and (name.startswith('plugin.') or name.startswith('repository.')):
            shutil.rmtree(full)


def copy_sources():
    dst_root = os.path.join(REPO, 'src')
    if os.path.isdir(dst_root):
        shutil.rmtree(dst_root)
    for addon_id, src in list(ADDONS.items()):
        if addon_id.startswith('plugin.') or addon_id == 'repository.radek':
            shutil.copytree(src, os.path.join(dst_root, addon_id),
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.bak', '.DS_Store', 'tests'))


def main():
    with open(os.path.join(ADDONS['repository.radek'], 'addon.xml'), 'w', encoding='utf-8') as f:
        f.write(REPO_ADDON_XML.format(url=URL, version=REPO_VERSION))

    clean_old()
    xml_parts, flat = [], []
    for addon_id, src in ADDONS.items():
        zip_path, version = make_zip(src, os.path.join(REPO, addon_id))
        for asset in ('icon.png', 'fanart.jpg', 'fanart.png'):
            a = os.path.join(src, asset)
            if os.path.exists(a):
                shutil.copy2(a, os.path.join(REPO, addon_id, asset))
        with open(os.path.join(src, 'addon.xml'), encoding='utf-8') as f:
            xml_parts.append(re.sub(r'^<\?xml[^>]*\?>\s*', '', f.read()).strip())
        shutil.copy2(zip_path, REPO)
        flat.append(os.path.basename(zip_path))
        print('  %-26s %-9s (v addons.xml)' % (addon_id, version))
    for addon_id, src in EXTRA.items():
        zip_path, version = make_zip(src, REPO)
        flat.append(os.path.basename(zip_path))
        print('  %-26s %-9s (jen ZIP)' % (addon_id, version))

    data = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n' +
            '\n\n'.join(xml_parts) + '\n</addons>\n').encode('utf-8')
    ET.fromstring(data)  # kontrola platnosti XML
    with open(os.path.join(REPO, 'addons.xml'), 'wb') as f:
        f.write(data)
    with open(os.path.join(REPO, 'addons.xml.md5'), 'w') as f:
        f.write(hashlib.md5(data).hexdigest())

    # Stránka pro zdroj v Kodi: Kodi z HTML bere jen odkazy, jejichž text je přesně
    # název souboru, proto jsou ZIPy v kořeni a odkazy bez dalšího textu.
    first = ['repository.radek-%s.zip' % REPO_VERSION]
    order = first + sorted(x for x in flat if x not in first)
    links = '\n'.join('<a href="%s">%s</a><br>' % (n, n) for n in order)
    with open(os.path.join(REPO, 'index.html'), 'w', encoding='utf-8') as f:
        f.write('<!DOCTYPE html>\n<html><head><meta charset="utf-8"><title>radcz Kodi repo</title></head>\n'
                '<body>\n<h1>radcz Kodi repozitář</h1>\n<p>V Kodi přidejte zdroj https://radcz.github.io/kodi-repo/ '
                'a nainstalujte ze ZIPu nejdřív repository.radek.</p>\n%s\n</body></html>\n' % links)
    open(os.path.join(REPO, '.nojekyll'), 'w').close()
    copy_sources()
    print('Hotovo: %d ZIPů v kořeni, addons.xml s %d doplňky.' % (len(flat), len(xml_parts)))


if __name__ == '__main__':
    main()
