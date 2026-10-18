# radcz Kodi Repository

Veřejný repozitář doplňků pro [Kodi](https://kodi.tv) 19, 20 a 21. Funguje na **Apple TV, iPadu/iPhonu, Macu, Windows, Androidu i Linuxu**.

| Doplněk | Verze | Popis |
|---|---|---|
| `repository.radek` | 1.0.3 | tento repozitář, přes který se doplňky instalují a aktualizují |
| `plugin.video.sosac-2` | 3.1.2.6 | Sosac.TV s opravami, stahováním offline a průběhem stahování |
| `plugin.video.prehrajto` | 2.0.5.1 | Prehraj.to česky: hledání s náhledy, stahování na pozadí, výběr více videí (vyžaduje Premium) |
| `plugin.video.freevideo` | 1.5.0 | Video FREE: 14 webů (FreeVideo.cz, YourLesbians, Lesbian8, xHamster, Pornhub, PornTrex, xVideos, XNXX, Eporner, YouPorn, RedTube, Tube8, YouJizz, PornOne), lesbické výpisy vždy nahoře, přehrávání i stahování |
| `repository.dobbelina` | 1.0.4.1 | repozitář Dobbelina (Cumination) s vlastní ikonou |
| `repository.slyguy` | 0.0.9 | repozitář SlyGuy, z něj se instaluje HBO Max (viz níže) |

Ke stažení jsou také `repository.sosacRepo` a `repository.prehraj.to`.

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

## Sosac.TV 3.1.2.6: co je nového a opraveno oproti 3.1.2

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
