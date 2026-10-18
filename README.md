# Radek Kodi Repository

Vlastní repozitář doplňků pro [Kodi](https://kodi.tv) (testováno na Kodi 21 „Omega“).

| Doplněk | Verze | Popis |
|---|---|---|
| `plugin.video.freevideo` | 1.1.0 | FreeVideo.cz: výpisy, kategorie, hledání, přehrávání |
| `plugin.video.sosac-2` | 3.1.2.3 | Sosac.TV s opravami a stahováním (viz níže) |
| `repository.radek` | 1.0.1 | samotný repozitář, díky kterému se doplňky aktualizují |

## Instalace do Kodi

1. **Nastavení → Systém → Doplňky** → zapnout **Neznámé zdroje**.
2. **Nastavení → Správce souborů → Přidat zdroj** → zadat
   `https://radcz.github.io/kodi-repo/` (název třeba `radek`).
3. **Doplňky → Instalovat ze ZIP souboru** → `radek` → `repository.radek` → `repository.radek-1.0.1.zip`.
4. **Doplňky → Instalovat z repozitáře → Radek Repository** → vybrat doplněk.

ZIP repozitáře jde stáhnout i přímo:
[repository.radek-1.0.1.zip](repository.radek/repository.radek-1.0.1.zip)

## Sosac.TV 3.1.2.3: co je nového a opraveno oproti 3.1.2

- **Stahování:** volba *Offline v Kodi* (funguje i na iPadu) nebo *složka v počítači*; tlačítka *Stáhnout vše na této stránce* a *Stáhnout vybrané…* u filmů i dílů; stahování ve frontě po jednom.
- **Průběh stahování:** lišta s procenty, MB a rychlostí v rohu Kodi; ve *Stažených* přehled probíhajících a čekajících stahování a *Zrušit stahování*. Do počítače se stahuje do podsložky `Sosac`.
- **Mazání stažených:** *Smazat vybrané…*, *Smazat vše v této složce*, *Smazat celou složku* (kontextové menu) a *Smazat všechno stažené*.
- Vzhled Sosacu se nastaví jednou natrvalo, takže při přepínání mezi doplňky už nevyskakuje „Ponechat vzhled?“ (původní přepínání lze zapnout v nastavení).
- Ladicí výpisy už se nezapisují do běžného logu Kodi (dřív v něm bylo uživatelské jméno a otisk hesla).
- Odstraněno problikávání: služba se každou sekundu pokoušela přepnout na skin, který Kodi ještě nezaregistroval.
- Opraveno zvýraznění vybrané položky v menu (skin `skin.estuary-sosac` 3.0.1).
- Doplněk už nemaže všechny uložené pozice přehrávání v Kodi (i u jiných doplňků) a nepřepisuje `advancedsettings.xml`.
- Síťové dotazy mají časový limit a účet se ověřuje jen jednou, ne před každým dotazem.
- Přehrávání: správný výběr jazyka a kvality, náhradní stream, ošetření prázdné odpovědi a neznámého jazyka.
- Neúspěšné spuštění videa už nesmaže na serveru pozici „pokračovat od“.
- Dotaz „pokračovat / od začátku“ se objeví před spuštěním videa.
- Opravy pádů (chybějící `self`, nedefinované proměnné při stahování seriálů, poškozený jazykový soubor).
- Do Správce souborů se automaticky přidají zdroje Sosac, Prehraj.to, dobbelina a SlyGuy.

Původní doplněk: sosac.tv (licence GPL). Tato verze je neoficiální úprava pro vlastní použití.

## Struktura

- kořen repozitáře: `addons.xml`, `addons.xml.md5` a ZIPy doplňků (to čte Kodi)
- `src/`: zdrojové kódy doplňků
- `tools/build_repo.py`: sestavení `addons.xml` a ZIPů
