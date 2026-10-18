# -*- coding: utf-8 -*-
"""Sestaví statický Kodi repozitář (addons.xml, addons.xml.md5, ZIPy) pro GitHub Pages.

Použití:
    python3 tools/build_repo.py [--url https://raw.githubusercontent.com/radcz/kodi-repo/main/]

--url je veřejná adresa, kde bude obsah složky repo/ hostován (končí lomítkem); výchozí je GitHub radcz/kodi-repo.
Výsledek: složka repo/ (nahrát na hosting) + kopie ZIPů v kořeni složky freevideo/.
"""
import argparse
import hashlib
import os
import re
import shutil
import zipfile
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
SRC = os.path.join(ROOT, 'src')
OUT = os.path.join(ROOT, 'repo')
DEFAULT_URL = 'https://raw.githubusercontent.com/radcz/kodi-repo/main/'
# id doplňku -> zdrojová složka
ADDONS = {
    'plugin.video.freevideo': os.path.join(SRC, 'plugin.video.freevideo'),
    'plugin.video.sosac-2': os.path.normpath(os.path.join(ROOT, '..', 'plugin.video.sosac-2')),
    'repository.radek': os.path.join(SRC, 'repository.radek'),
}
SKIP = {'__pycache__', '.DS_Store', '.git', 'tests'}
SKIP_EXT = ('.pyc', '.bak')

REPO_ADDON_XML = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="repository.radek" name="[COLOR deepskyblue]Radek[/COLOR] [COLOR hotpink]Repository[/COLOR]" version="{version}" provider-name="Radek">
    <extension point="xbmc.addon.repository" name="Radek Repository">
        <dir>
            <info compressed="false">{url}addons.xml</info>
            <checksum>{url}addons.xml.md5</checksum>
            <datadir zip="true">{url}</datadir>
        </dir>
    </extension>
    <extension point="xbmc.addon.metadata">
        <summary lang="cs_CZ">Vlastní repozitář doplňků (Video FREE, Sosac.TV s opravami)</summary>
        <summary lang="en_GB">Personal add-on repository</summary>
        <description lang="cs_CZ">Repozitář s doplňky Video FREE a Sosac.TV (opravená verze) a jejich aktualizacemi.</description>
        <description lang="en_GB">Repository with the Video FREE and patched Sosac.TV add-ons and their updates.</description>
        <platform>all</platform>
        <assets>
            <icon>icon.png</icon>
        </assets>
    </extension>
</addon>
'''


def addon_version(addon_dir):
    return ET.parse(os.path.join(addon_dir, 'addon.xml')).getroot().get('version')


def make_zip(addon_id, dest_dir):
    src = ADDONS[addon_id]
    version = addon_version(src)
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, '%s-%s.zip' % (addon_id, version))
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for base, dirs, files in os.walk(src):
            dirs[:] = sorted(d for d in dirs if d not in SKIP)
            for name in sorted(files):
                if name in SKIP or name.endswith(SKIP_EXT):
                    continue
                full = os.path.join(base, name)
                zf.write(full, os.path.join(addon_id, os.path.relpath(full, src)))
    return path, version


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default=DEFAULT_URL, help='veřejná URL repozitáře (končí /)')
    ap.add_argument('--repo-version', default='1.0.1')
    args = ap.parse_args()
    url = args.url if args.url.endswith('/') else args.url + '/'

    with open(os.path.join(SRC, 'repository.radek', 'addon.xml'), 'w', encoding='utf-8') as f:
        f.write(REPO_ADDON_XML.format(url=url, version=args.repo_version))

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    xml_parts = []
    for addon_id in ADDONS:
        zip_path, version = make_zip(addon_id, os.path.join(OUT, addon_id))
        shutil.copy2(zip_path, ROOT)
        for asset in ('icon.png', 'fanart.jpg', 'fanart.png'):
            a = os.path.join(ADDONS[addon_id], asset)
            if os.path.exists(a):
                shutil.copy2(a, os.path.join(OUT, addon_id, asset))
        with open(os.path.join(ADDONS[addon_id], 'addon.xml'), encoding='utf-8') as f:
            xml = f.read()
        xml = re.sub(r'^<\?xml[^>]*\?>\s*', '', xml).strip()
        xml_parts.append(xml)
        print('  %s %s -> %s' % (addon_id, version, os.path.relpath(zip_path, ROOT)))

    addons_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n' + \
        '\n\n'.join(xml_parts) + '\n</addons>\n'
    data = addons_xml.encode('utf-8')
    ET.fromstring(data)  # kontrola platnosti XML
    with open(os.path.join(OUT, 'addons.xml'), 'wb') as f:
        f.write(data)
    with open(os.path.join(OUT, 'addons.xml.md5'), 'w') as f:
        f.write(hashlib.md5(data).hexdigest())

    # jednoduchá stránka pro prohlížeč / zdroj souborů v Kodi
    repo_zip = 'repository.radek/repository.radek-%s.zip' % args.repo_version
    with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write('<!DOCTYPE html><html><head><meta charset="utf-8"><title>Radek Kodi repo</title></head>'
                '<body><h1>Radek Kodi repozitář</h1><ul>'
                '<li><a href="%s">%s</a></li>'
                '<li><a href="addons.xml">addons.xml</a></li></ul></body></html>\n'
                % (repo_zip, os.path.basename(repo_zip)))
    open(os.path.join(OUT, '.nojekyll'), 'w').close()
    print('Repozitář sestaven ve složce repo/ pro URL %s' % url)


if __name__ == '__main__':
    main()
