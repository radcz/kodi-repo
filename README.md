# radcz Kodi Repository

Veřejný repozitář doplňků pro [Kodi](https://kodi.tv) 19, 20 a 21. Funguje na **Apple TV, iPadu/iPhonu, Macu, Windows, Androidu i Linuxu**.

| Doplněk | Verze | Popis |
|---|---|---|
| `repository.radek` | 1.0.3 | tento repozitář, přes který se doplňky instalují a aktualizují |
| `plugin.video.sosac-2` | 3.1.2.9 | Sosac.TV s opravami, stahováním offline ve 4K; stahování jde pozastavit, pokračovat (i po restartu Kodi) a zrušit |
| `plugin.video.prehrajto` | 2.0.5.3 | Prehraj.to česky: hledání s náhledy, stahování jen ve 4K/2K, celá stránka najednou; stahování jde pozastavit, pokračovat (i po restartu Kodi) a zrušit (vyžaduje Premium) |
| `plugin.video.freevideo` | 1.8.0 | Video FREE: 14 webů, Oblíbené s hvězdičkami 1–3 úplně nahoře, lesbické výpisy vždy nahoře, stahování celé stránky, jen přesně 1080p; stahování jde pozastavit, pokračovat (i po restartu Kodi) a zrušit |
| `repository.dobbelina` | 1.0.4.1 | repozitář Dobbelina (Cumination) s vlastní ikonou |
| `repository.slyguy` | 0.0.9 | repozitář SlyGuy, z něj se instaluje HBO Max (viz níže) |

Ke stažení jsou také `repository.sosacRepo` a `repository.prehraj.to`.

## Instalace jedním ZIPem (nainstaluje všechno)

**Stáhnout: [plugin.program.radcz.instalator-1.0.0.zip](https://radcz.github.io/kodi-repo/plugin.program.radcz.instalator-1.0.0.zip)**

1. Kodi → **Nastavení → Systém → Doplňky** → zapnout **Neznámé zdroje**.
2. **Doplňky → ikona otevřené krabice → Instalovat ze ZIP souboru** → `plugin.program.radcz.instalator-1.0.0.zip`
   (na Apple TV / iPadu nejdřív ve Správci souborů přidejte zdroj `https://radcz.github.io/kodi-repo/` a ZIP vyberte z něj).
3. Instalátor se sám spustí a zeptá **„Nainstalovat vše najednou?“** → **Ano**. Přidá repozitáře radcz, Sosac, Prehraj.to,
   Dobbelina a SlyGuy (HBO Max) a nainstaluje **Sosac.TV, Prehraj.to (česky) a Video FREE** i s knihovnami.
   Kodi se může u každého doplňku zeptat „Nainstalovat?“ → **Ano**.
4. Restartujte Kodi a v nastavení Sosac.TV a Prehraj.to zadejte přihlášení.

Instalátor jde kdykoli spustit znovu (**Doplňky → Programy → radcz instalátor**), doinstaluje, co chybí.

**Adresa zdroje pro Kodi: `https://radcz.github.io/kodi-repo/`**

V repozitáři nejsou žádná hesla. Přihlašovací údaje k Sosacu a Streamuj.tv zadáte až v Kodi v nastavení doplňku.

---

## Instalace (stejná na Apple TV, iPadu i ostatních Kodi)

1. **Nastavení (ozubené kolo) → Systém → Doplňky** → zapnout **Neznámé zdroje** → potvrdit **Ano**.
2. **Nastavení → Správce souborů → Přidat zdroj → `<Žádný>`** → napsat
   `https://radcz.github.io/kodi-repo/` → **OK** → název zdroje `radcz` → **OK**.
3. **Doplňky → ikona otevřené krabice (vlevo nahoře) → Instalovat ze ZIP souboru → `radcz`**
   → **`repository.radek-1.0.3.zip`**. Počkejte na hlášku „Doplněk povolen“.
4. **Instalovat z repozitáře → radcz Repository → Video doplňky** → **Sosac.TV** (a podle chuti **Video FREE**) → **Instalovat**.
   Kodi samo doinstaluje potřebné knihovny (requests, six, routing) z oficiálního repozitáře Kodi.
5. **Restartujte Kodi.** Sosac při prvním startu nainstaluje svůj vzhled a přidá do Správce souborů zdroje
   (radcz, Sosac, Prehraj.to, dobbelina, SlyGuy).
6. **Doplňky → Sosac.TV → Nastavení → Účty**: zadejte jméno a heslo k Sosacu a Streamuj.tv.

Další repozitáře (Dobbelina, Prehraj.to, SlyGuy) nainstalujete stejně, v kroku 3 jen vyberete jejich ZIP.

### Apple TV

- Kodi pro Apple TV se instaluje mimo App Store (na tvOS není oficiálně). Postup najdete na [kodi.wiki: tvOS](https://kodi.wiki/view/TvOS).
- Text se píše ovladačem nebo přes **Klávesnici Apple TV** na iPhonu (nabídne se sama při psaní adresy).
- Kontextové menu (Stáhnout, Smazat, Zrušit stahování) otevřete **podržením středu ovladače**.
- Stahuje se rovnou **Offline do Kodi**. Pozor: tvOS může při nedostatku místa uložená data aplikací mazat, offline videa proto berte jako dočasná.

### iPad / iPhone

- Kodi pro iPadOS se instaluje mimo App Store ([kodi.wiki: iOS](https://kodi.wiki/view/IOS)).
- Stahuje se rovnou **Offline do Kodi** a videa pak jdou přehrát i bez internetu.
- Kontextové menu otevřete **dlouhým podržením** položky.

### Mac, Windows, Android, Linux

- Při stahování si můžete vybrat **Offline v Kodi** nebo **Do složky v počítači** (ukládá se do podsložky `Sosac`).
- Volbu lze nastavit natrvalo: **Sosac.TV → Nastavení → Stahování → Kam stahovat**.

### Aktualizace

Kodi si nové verze stahuje z tohoto repozitáře samo. Ručně: **Doplňky → Moje doplňky → Sosac.TV → Aktualizovat**.

### HBO Max

1. **Doplňky → Instalovat z repozitáře → radcz Repository → Repozitáře → SlyGuy Repository → Instalovat**.
2. **Instalovat z repozitáře → SlyGuy Repository → Video doplňky → HBO Max → Instalovat**.

- Je potřeba předplatné HBO Max; přihlásíte se přímo v doplňku.
- Funguje na **Macu, Windows a Androidu** (ochranu Widevine Kodi doinstaluje přes InputStream Helper při prvním přehrání).
- Na **Apple TV a iPadu** Kodi Widevine nejspíš nepodporuje, takže tam HBO Max asi nepůjde přehrát. Tam použijte oficiální aplikaci HBO Max.
- HBO Max a jeho knihovny se aktualizují přímo od SlyGuy, ne z tohoto repozitáře.

---

## Sosac.TV 3.1.2.9: co je nového a opraveno oproti 3.1.2

- **Kvalita v seznamech:** u každého videa je za jazykem vidět kvalita (4K zlatě, 1080p zeleně, 720p, 480p).
- **Místní profily:** jeden účet Sosac, ale víc diváků. Hlavní profil je sdílený se sosac.tv, další profily (Profil 2, později třeba Profil 3) si zhlédnuté a pozice „pokračovat od“ pamatují jen v daném Kodi. Každé zařízení si pamatuje svůj profil. Přepíná se v hlavním menu Sosacu nahoře (*Profil: …*).
- **Apple TV a iPad:** stahuje se rovnou offline do Kodi. Kompatibilita s Kodi 19 (Python 3.8).
- **Kvalita stahování:** *Jen 4K* (výchozí; videa bez 4K se přeskočí), *4K, jinak nejlepší dostupná* nebo *Vybrat ručně*. Sosac nabízí 4K, 1080p, 720p a 480p, kvalita 1440p tam není.
- **Průběh stahování:** lišta s procenty, MB a rychlostí v rohu Kodi. Ve *Stažených* je přehled probíhajících a čekajících stahování a volba *Zrušit stahování*.
- **Stahování:** *Offline v Kodi* nebo *složka v počítači*, *Stáhnout vše na této stránce*, *Stáhnout vybrané…*, fronta po jednom.
- **Mazání stažených:** *Smazat vybrané…*, *Smazat vše v této složce*, *Smazat celou složku*, *Smazat všechno stažené*.
- Při přepínání mezi doplňky už nevyskakuje „Ponechat vzhled?“.
- Do logu Kodi se už nezapisuje uživatelské jméno ani otisk hesla.
- Opraveno problikávání, zvýraznění položky v menu, mazání pozic přehrávání u jiných doplňků, zamrzání bez časového limitu, výběr jazyka a kvality streamu, ukládání titulků a pády při stahování seriálů.

Původní doplněk: sosac.tv (licence GPL). Tato verze je neoficiální úprava pro vlastní použití.

## Struktura

- `index.html` a `*.zip` v kořeni: instalace přes zdroj v Kodi
- `addons.xml`, `addons.xml.md5`, `<doplněk>/`: data repozitáře, která čte Kodi
- `src/`: zdrojové kódy doplňků
- `tools/build_all.py`: sestavení celého repozitáře
