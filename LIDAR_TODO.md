# LiDAR-Layer für Europa

Ziel: für jedes Land und jede Region die feinste frei nutzbare Geländeschummerung (DGM aus Laserscanning).
Reihenfolge (festgelegt 2026-10-19):
1. Deutschland ✅ (alle 16 Länder ≥ 1 m, BW/NW 25 cm)
2. Österreich ✅ (überall ≥ 1 m, Tirol/OÖ 0,5 m, Vorarlberg 25 cm)
3. Italien ✅ (21 Regionen/Provinzen; LiDAR in BZ, TN, FVG, ER, Toskana, Sardinien; Rest 2–10 m)
4. Kroatien ✅ (DGU-LiDAR 1 m landesweit außer Donau-Streifen; Wasserzeichen wird abgeschnitten)
5. Niederlande ✅ (AHN4 0,5 m landesweit, PDOK-WCS, selbst geschummert; Lücken mit AHN5 5 m gefüllt)
6. Frankreich ✅ (IGN LiDAR HD 0,5 m auf 93,5 %, selbst geschummert; Rest RGE ALTI 1 m)
7. Spanien ✅ (PNOA-LiDAR 2 m landesweit + 0,5 m ab Zoom 18 wo beflogen; Katalonien/Navarra 0,5 m, Galicien 1 m)
8. Portugal ✅ (DGT-LiDAR 0,5 m auf ~87 % via Mapterhorn; Nordosten/Côa 30 m, Madeira 10 m)
9. Schweiz ✅ (swissALTI3D 0,5 m inkl. Liechtenstein; ZH/SO/BS 0,25 m, Genf 0,2 m)
10. danach alle übrigen EU-Länder, in Gruppen:
    - Slowenien ✅ (ARSO 1 m), Tschechien ✅ (ČÚZK DMR 5G 2 m), Slowakei ✅ (1 m überall, 0,5 m DMR 6.0 auf ~26 %)
    - Belgien ✅ (Flandern+Brüssel 25 cm, Wallonien 0,5 m), Luxemburg ✅ (0,5 m 2024), Dänemark ✅ (DHM 0,4 m via Mapterhorn)
    - Polen ✅ (GUGiK NMT 1 m via Mapterhorn), Rumänien ✅ teilweise (LAKI 0,5 m in 12 Kreisen), Ungarn/Bulgarien ➖ (kein offenes DGM, nur GLO-30 30 m)
    - Schweden ✅ (Markhöjdmodell 1 m via Mapterhorn), Finnland ✅ (MML 2 m), Estland ✅ (1 m), Lettland/Litauen ➖ (nur 20–30 m)
    - Irland ✅ teilweise (GSI-LiDAR in Blöcken, ~19 % DTM), Zypern ✅ (DLS DTM 1 m im Süden), Malta ✅ (LiDAR 1 m), Griechenland ➖ (nur GLO-30)

Damit sind alle 27 EU-Länder plus Schweiz/Liechtenstein angelegt (28 Länder, 437 Regionen).

In der App sind alle LiDAR-Regionen anfangs aus und werden unter Karte › LiDAR einzeln eingeschaltet;
das Grundrelief jedes Landes füllt alles andere.

## Deutschland (`assets/countries/europe/germany.py`)

| # | Land | Status | Quelle / Auflösung |
|---|------|--------|--------------------|
| 1 | Baden-Württemberg (BW) | ✅ fertig | LGL-BW DGM 25 cm Schummerung (bis Zoom 19) |
| 2 | Bayern (BY) | ✅ fertig | LDBV Geländerelief aus DGM1 (1 m, bis Zoom 17); nichts Feineres offen |
| 3 | Saarland (SL) | ✅ fertig | LVGL `sl_shaded_relief_2025`, Laserdaten 2025, ~0,5 m (bis Zoom 18); URL ist ein Geoportal-Proxy-Hash |
| 4 | Rheinland-Pfalz (RP) | ✅ fertig | LVermGeo `rp_shade1m`, DGM 1 m (bis Zoom 17) |
| 5 | Hessen (HE) | ✅ berechnet | DGM1-Höhen per WCS (inspire-hessen.de), Schummerung rechnet die App selbst (`dem_shade.py`), ab Zoom 11 |
| 6 | Thüringen (TH) | ✅ 1 m | TLBG-DGM1 über Mapterhorn-Höhenkacheln, selbst geschummert (Landesdienst hat nur DGM2) |
| 7 | Sachsen (SN) | ✅ fertig | GeoSN `relief_standard`, DGM1 1 m (Server rendert bis Zoom 18 scharf) |
| 8 | Nordrhein-Westfalen (NW) | ✅ fertig | Geobasis NRW DGM-Schummerung 25 cm (bis Zoom 19) |
| 9 | Sachsen-Anhalt (ST) | ✅ berechnet | DGM1-Höhen als Float-GeoTIFF per WMS `ST_DGM1`, Schummerung selbst gerechnet |
| 10 | Berlin (BE) | ✅ fertig | über LGB-Dienst BB-BE (Berlins eigener Layer ist nur 30 % deckend) |
| 11 | Brandenburg (BB) | ✅ fertig | LGB `dgmshade`, DGM 1 m (bis Zoom 17) |
| 12 | Niedersachsen (NI) | ✅ 1 m | LGLN-DGM1 über Mapterhorn (0,3–1 s statt 5–13 s beim LGLN-WCS) |
| 13 | Bremen (HB) | ✅ 1 m | DGM1 Land Bremen über Mapterhorn (kein offizieller Live-Dienst) |
| 14 | Hamburg (HH) | ✅ fertig | LGV `wms_gelaendemodelle_schummerung`, 1 m, Gebäude herausgerechnet |
| 15 | Mecklenburg-Vorpommern (MV) | ✅ 1 m | DGM1-Höhen per WCS (`INTERPOLATION=BILINEAR`), selbst geschummert, kein Wasserzeichen |
| 16 | Schleswig-Holstein (SH) | ✅ 1 m | DGM1 über Mapterhorn, ohne die 20-fache Überhöhung des Landesdienstes |

Bestandsaufnahme 2026-10-18: kein Land bietet offen etwas Feineres als BW/NW (25 cm), alle anderen 1 m.
**Mapterhorn** (`tiles.mapterhorn.com`, Terrarium-WebP bis z16 ≈ 1,2 m/px) enthält die DGM1 aller 16 Länder;
Layer-Typ `dem_terrarium` in `dem_shade.py`. Nutzungsbedingungen für Direktzugriffe sind nicht dokumentiert –
für große Offline-Pakete lieber deren PMTiles-Downloads nehmen.

## Österreich (`assets/countries/europe/austria.py`, geprüft 2026-10-18)

Grundrelief basemap.at `bmapgelaende` (aus den ALS-DGMs der Länder, ≈1 m, bis Zoom 17) deckt das ganze Land.
Landesgrenzen: BEV VGD 01.04.2026 (`austria_states.json`, gemeinsame Kanten, 7 m vereinfacht).

| Land | Status | Quelle |
|------|--------|--------|
| Vorarlberg | ✅ 25 cm | VoGIS `schummerung_2023_gelaende_25cm` |
| Tirol | ✅ 50 cm | tiris `Image_Schummerung_Gelaendemodell` |
| Oberösterreich | ✅ ≈50 cm | DORIS ArcGIS MapServer `/export` (Typ `arcgis_map`) |
| Steiermark | ✅ 1 m | GIS-Steiermark `als_schummerung` |
| Salzburg | ➖ | Landesdienst zeigt in Pinzgau/Pongau/Lungau nur ein Gittermuster, WMS 503 → basemap.at |
| Kärnten | ➖ | WMTS nur in EPSG:31258 → basemap.at (Umprojektion wäre möglich) |
| Niederösterreich, Burgenland, Wien | ➖ | kein Schummerungsdienst → basemap.at |
| (BEV ALS-DTM WMS) | ⚠️ | Schlüssel öffentlich, Nutzung laut Metadaten anmeldepflichtig → nicht verwendet |

Geprüft 2026-10-19: Mapterhorn hat Salzburg (1 m), Kärnten, OÖ, Burgenland (5 m) und Österreich 10 m;
Vergleich in Kärnten mit basemap.at zeigt dasselbe 1-m-Detail → kein Gewinn, basemap.at bleibt Grundrelief.
NÖ und Wien: keine offenen DGM feiner als basemap.at. Österreich ist damit am offen verfügbaren Optimum.

## Italien (`assets/countries/europe/italy.py`, geprüft 2026-10-19)

Grenzen: ISTAT 01.01.2026 (`italy_regions.json`, Bozen/Trient getrennt). Grundrelief TINITALY 10 m.
Der nationale MASE/PST-A-LiDAR-WMS liefert derzeit nur leere Bilder (Datenbank ausgefallen) → nicht verwendet, später prüfen.

| Region | Stand | Quelle |
|---|---|---|
| Südtirol (IT-BZ) | ✅ 0,5 m Täler / 2,5 m sonst | geoservices.buergernetz.bz.it, CC0 |
| Trentino (IT-TN) | ✅ ~1 m | SIAT `dtm_315_wg` |
| Friaul-JV (IT-36) | ✅ 0,5 m | IRDAT `Hillshade` (LiDAR 2017–20) |
| Emilia-Romagna (IT-45) | ✅ 0,5 m auf ~70 % | ImageServer DtmRER2025_26, 2022, 2023_24, Bologna; sonst 5 m |
| Toskana (IT-52) | ✅ 1 m LiDAR (Mitte/Osten/Versilia), DSM 1 m in den Lücken | Geoscopio (Wasserzeichen wird abgeschnitten) |
| Sardinien (IT-88) | ✅ 1 m auf ~50 % | Geoserver `DTM_1M_MOSAICO_OMBRE` (STYLES=raster) |
| Sizilien (IT-82) | 2 m | SITR MDT 2013 über Mapterhorn |
| Aostatal (IT-23) | 2 m | über Mapterhorn |
| Piemont, Lombardei | 5 m | über Mapterhorn |
| Kampanien (IT-72) | 5 m | ImageServer CTR 2020 |
| Basilikata (IT-77) | 5 m | RSDI (grün getönt → in Graustufen umgerechnet) |
| Venetien, Ligurien, Umbrien, Marken, Latium, Abruzzen, Molise, Apulien | ➖ | kein offener Dienst → TINITALY 10 m |
| Kalabrien | ➖ | Geoportal nicht erreichbar, später erneut prüfen |

## Niederlande (`assets/countries/europe/netherlands.py`, geprüft 2026-10-19)

- AHN4 DTM 0,5 m (Befliegung 2020–22) als Höhen per PDOK-WCS `dtm_05m` (`INTERPOLATION=BILINEAR`, CC0), von der App
  geschummert (zFactor 2,5 fürs Flachland). Gebäude/Wasser sind im DTM Lücken → transparent (`transparentNoData`),
  darunter AHN5 5 m (gefüllt) über Mapterhorn als Grundrelief.
- Provinzen und Landesgrenze: PDOK Bestuurlijke Gebieden (Kadaster, CC BY 4.0), inkl. IJsselmeer/Wattenmeer.
- Optisch besser, aber nur unter Esri-NL-Bedingungen: Esri-ImageServer AHN4/AHN5/AHN6 mit fertiger Schummerung
  und gefüllten Lücken (AHN5/6 aktueller, Teilabdeckung) → nicht eingebaut, Lizenz offen.

## Kroatien (`assets/countries/europe/croatia.py`, geprüft 2026-10-19)

- DGU `services/dmr/ows` Layer `Hillshade`: LiDAR-DGM 1 m (Befliegung 2021–23), ganzes Land außer ~690 km² an der
  Donau (Flugbeschränkung: Ost-Baranja, Vukovar, Ilok). „GEOPORTAL“-Wasserzeichen mittig → `wms_crop` mit
  cropLeft 1300; der Kachel-Cache schneidet es beim Abruf ab und speichert nur den sauberen 512er-Ausschnitt.
- Kein WCS (abgeschaltet), keine Rohhöhen. Grundrelief: Copernicus GLO-30 über Mapterhorn (bis App-Zoom 13).
- Gespanschaften HR-01 … HR-21 aus dem DGU-Raumeinheitenregister (INSPIRE AU, „Otvorena dozvola“).

## Frankreich (`assets/countries/europe/france.py`, geprüft 2026-10-19)

- IGN LiDAR HD MNT 0,5 m als Float32 per Géoplateforme WMS-R (`IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93`,
  FORMAT image/tiff, Etalab 2.0), von der App geschummert; NoData (-9999) transparent. Abdeckung 93,5 % der Metropole,
  Lücken: West-Finistère/Morbihan (Carnac), Morvan (Bibracte), Limousin/Creuse, Nord, Ost-Île-de-France.
- Darunter RGE ALTI 1 m (+ ältere LiDAR-HD-Blöcke) über Mapterhorn. RGE ALTI direkt vom IGN-WMS ist unbrauchbar
  (Nearest-Neighbour-Streifen). Kein WCS bei der Géoplateforme.
- Schneller, aber hinterherhinkend: fertige WMTS-Schummerung `…LIDAR-HD…SHADOW` (Alésia fehlt dort noch).
- Regionen: IGN ADMIN EXPRESS COG 2026 (13 Regionen, Grenzen enden an der Küste).

## Spanien (`assets/countries/europe/spain.py`, geprüft 2026-10-19)

- IGN bietet live keine brauchbaren Rohhöhen (WMS-TIFF nur RGB, WCS nur 5 m in ganzen Metern) und keine LiDAR-Schummerung.
- Mapterhorn enthält die IGN-PNOA-Modelle: MDT02 (2 m) überall → Grundrelief bis Zoom 16; MDT50 (0,5 m, 3. Abdeckung
  2022–25) in großen Teilen → eigener Layer ab Zoom 18 (sonst 404, Basis scheint durch; teils hochgerechnete 2-m-Streifen).
- Regional feiner: Katalonien ICGC 0,5 m (WMS), Navarra IDENA 0,5 m (WMS), Galicien IDEG 1 m (ImageServer, fertige Schummerung).
- Nicht verwendet: Kantabrien (1 m, nur nicht-kommerziell), Kanaren GRAFCAN (nicht-kommerziell, DSM-Einfärbung),
  Andalusien/Baskenland/Balearen/Asturien (nicht besser als Mapterhorn), Aragón (Portal nicht erreichbar).
- Grenzen: IGN BDDAE (CC BY 4.0), 17 Autonome Gemeinschaften + Ceuta/Melilla.

## Portugal (`assets/countries/europe/portugal.py`, geprüft 2026-10-19)

- DGT veröffentlicht das LiDAR-MDT (0,5 m / 2 m, Flüge 2024–25) nur als Download hinter Login (CDD), kein Live-Dienst.
- Mapterhorn enthält das DGT-MDT 50 cm für ~87 % des Festlands (Lücke: Nordosten östlich ~7,3° W – Bragança,
  Ost-Guarda mit Côa-Tal, NO-Castelo Branco – und ein Fleck bei Arouca). Dort Copernicus GLO-30 (30 m) als Grundrelief.
- Madeira 10 m (IGP) über Mapterhorn, Azoren nur 30 m. Distrikte PT-01 … PT-18 + PT-20/PT-30 aus DGT CAOP 2025.
- Sobald Mapterhorn die neueren DGT-Kacheln übernimmt (CDD hat schon das ganze Festland), schließt sich die NO-Lücke.

## Schweiz und Liechtenstein (`assets/countries/europe/switzerland.py`, geprüft 2026-10-19)

- swisstopo swissALTI3D Reliefschattierung (multidirektional) 0,5 m als gecachter WMTS bis Zoom 18, CH + LI vollständig,
  außerhalb transparent, OGD. Jeder Kanton listet diesen Layer, damit er pro Kanton schaltbar ist.
- Feiner (OGD): Zürich DTM 2022 0,25 m (WMS), Genf LiDAR 2025 0,2 m (ImageServer, außerhalb schwarz → zugeschnitten),
  Solothurn 2019 0,25 m (Norden fehlt), Basel-Stadt 2024 0,25 m.
- Nicht verwendet: LU/BL 0,25 m (zu blass), AG/BE (kein Gewinn), NE/FR/SH (älter), Liechtensteins eigener WMS
  (nicht feiner, nur nicht-kommerziell). Kein WCS bei swisstopo; Mapterhorn hat dieselben Daten (für die Analyse).
- Grenzen: swissBOUNDARIES3D 2026-01, 26 Kantone + LI, Seen in den Kantonen, Büsingen/Campione als Löcher.

## Slowenien, Tschechien, Slowakei (geprüft 2026-10-19)

- **Slowenien** (`slovenia.py`): ARSO LiDAR-Schummerung DMR 1 m (LSS 2011–15), ArcGIS /export, ab Zoom 10; darunter dasselbe
  DMR über Mapterhorn. 12 statistische Regionen (NUTS-3-Schlüssel SI031…SI044, GURS). CLSS 2023–25 (0,5 m) noch ohne Live-Dienst.
- **Tschechien** (`czechia.py`): ČÚZK DMR 5G (LiDAR 2009–13, Raster 2 m) als WMS `dmr5g:GrayscaleHillshade`; Grundrelief
  DMR 4G 5 m über Mapterhorn. 14 Kraje (RÚIAN). Kein WCS.
- **Slowakei** (`slovakia.py`): DMR 5.0 1 m flächendeckend über Mapterhorn; DMR 6.0 0,5 m (ZBGIS-Kachelcache, eingefärbt →
  Graustufen) auf ~26 % (West/Mitte, Lose bis 2025), Košice/Prešov folgen mit dem Winterflug 2025/26 → Liste der Kraje anpassen.

## Belgien, Luxemburg, Dänemark (geprüft 2026-10-19)

- **Belgien** (`belgium.py`): DHMV II Hillshade 25 cm (Flandern + Brüssel, WMS, JPEG opak), Wallonie MNT 2021–22 Hillshade 0,5 m
  (WMS, ab Zoom 12); Grundrelief Mapterhorn. Grenzen: Statbel 2025 (3 Regionen).
- **Luxemburg** (`luxembourg.py`): ACT „Ombrage (MNT) 2024“ 0,5 m, WMS-Layer-ID `2978` (interne ID, kann sich ändern), CC0.
  12 Kantone (ACT INSPIRE AU, CC0).
- **Dänemark** (`denmark.py`): amtliche Dienste (Dataforsyningen DHM WMS/WCS) nur mit Token → DHM/Terræn 0,4 m über Mapterhorn.
  Lücke um Tønder (~22×5 km, nur ~10 m). Grenzen aus OpenStreetMap (DAWA abgeschaltet, DAGI mit Token), ODbL.

## Polen, Ungarn, Rumänien, Bulgarien (geprüft 2026-10-19)

- **Polen** (`poland.py`): GUGiK NMT 1 m (LiDAR) über Mapterhorn (~97 %, zFactor 2), GUGiK-WMS-Schummerung füllt Masowien
  (langsam, kein Massenabruf). Grundrelief NMT 5 m. 16 Woiwodschaften (GUGiK PRG).
- **Ungarn** (`hungary.py`): LiDAR und DDM 5 m nur kostenpflichtig (geoshop.hu); offenes DDM25 schlechter als GLO-30 →
  nur Copernicus GLO-30. 19 Komitate + Budapest (Lechner INSPIRE AU).
- **Rumänien** (`romania.py`): ANCPI-Geoportal seit dem e-Terra-Ausfall (08/2026) offline. LAKI II 0,5 m über Mapterhorn in
  12 Kreisen (Arad, Bihor, Hunedoara voll; Alba, Cluj, Gorj, Caraș-Severin, Timiș teilweise …), sonst GLO-30. Später ANCPI erneut prüfen.
- **Bulgarien** (`bulgaria.py`): kein offenes DGM (INSPIRE-Dienst zugangsbeschränkt/gebührenpflichtig) → nur GLO-30. 28 Oblasti (AGKK).

## Nordeuropa und Baltikum (geprüft 2026-10-19)

- **Schweden** (`sweden.py`): Lantmäteriet Markhöjdmodell 1 m (CC0) über Mapterhorn; im Norden (Västerbotten/Norrbotten) nur
  Grid 15. Der Schummerungsdienst von Lantmäteriet braucht ein Geotorget-Konto; der Proxy der Webkarte „Min karta“ würde den
  Login nur umgehen und wird nicht genutzt. 21 Län (SCB DeSO an OSM-Küste geschnitten, ~100 m genau).
- **Finnland** (`finland.py`): MML Korkeusmalli 2 m über Mapterhorn (MML-Dienste nur mit API-Key oder EPSG:3067). 19 Maakunta
  (Statistik Finnland 1:1 Mio., Binnengrenzen grob).
- **Estland** (`estonia.py`): Kõrgusmudel 1 m (LiDAR 2021-24) über Mapterhorn, zFactor 2; Amtsdienste nur EPSG:3301. 15 Maakond.
- **Lettland** (`latvia.py`): LĢIA-Höhen nur mit Lizenzvertrag, LVM-Relief-WMS abgeschaltet → Mapterhorn bis Zoom 13 (20 m oder
  GLO-30). 5 Planungsregionen (VZD 2026, eigene Schlüssel LV-KUR/LAT/RIG/VID/ZEM).
- **Litauen** (`lithuania.py`): geoportal.lt-Relief nur mit Login, DTM-LT nur nichtkommerziell in Esri-Software → nur GLO-30.
  10 Bezirke (Registrų centras 2026).

## Irland, Griechenland, Zypern, Malta (geprüft 2026-10-19)

- **Irland** (`ireland.py`): GSI-ImageServer (CC BY 4.0), kein landesweites Modell: Westmeath 25 cm (Uisneach), Heritage
  0,125–1 m (Brú na Bóinne u. a., 13 Counties), Phase 2 1 m, OPW 2 m (Küste/Flüsse), TII 2 m (Straßenkorridore), NASC-DSM 2 m
  (Oberflächenmodell). TII/Phase 2 malen NoData schwarz → URL-Endung `exportImage?noData=0&f=image&_=`. Rest GLO-30.
- **Griechenland** (`greece.py`): kein offenes DGM (Ktimatologio-WMS nur Orthofotos, INSPIRE-Dienste 404) → nur GLO-30.
  13 Regionen + Athos (OSM, an Küste geschnitten).
- **Zypern** (`cyprus.py`): DLS DTM 2019 1 m über Mapterhorn für CY-01…05 (Kyrenia/Norden ohne Daten), sonst GLO-30. Ob das DTM
  aus LiDAR stammt, ist nicht dokumentiert.
- **Malta** (`malta.py`): Planning Authority LiDAR-DTM 1 m 2012 als WCS (wetransform/rasdaman, Achsen E/N, Pyramide `_2`…`_32`).
  Lizenz uneinheitlich (INSPIRE: frei; GeoPortal: CC BY-NC-ND) – offen. Drei Inseln als Regionen (OSM).

## Speicherbedarf für ein ganzes Land (gemessen 2026-10-18)

Kachelanzahl exakt aus dem Landespolygon, mittlere Kachelgröße aus 8–24 echten Stichproben je Zoomstufe
(512-px-Kacheln, so wie die App speichert). Nur der LiDAR-Layer; das BKG-Relief darunter kommt nur in
HE/NI/HB/ST und unter Zoom 14 dazu (je Land 0,2–7 GB als PNG).

| Land | bis Zoom | Kacheln | PNG (vorher) | JPEG (jetzt) | davon bis Z17 | Download ca.* |
|------|----------|---------|-------------|--------------|---------------|---------------|
| Bayern | 17 | 0,59 Mio. | 84 GB | **8,7 GB** | 8,7 GB | 58 h |
| Baden-Württemberg | 19 | 4,67 Mio. | 659 GB | **116 GB** | 7,8 GB | 280 h |
| Nordrhein-Westfalen | 19 | 5,03 Mio. | 970 GB | **154 GB** | 14 GB | 82 h |
| Sachsen | 18 | 0,67 Mio. | 131 GB | **35 GB** | 8,8 GB | 6 h |
| Saarland | 18 | 0,09 Mio. | 14 GB | 14 GB (PNG, Server-JPEG ist größer) | 4,0 GB | 3 h |
| Rheinland-Pfalz | 17 | 0,17 Mio. | 28 GB | **5,3 GB** | 5,3 GB | 2 h |
| Brandenburg + Berlin | 17 | 0,30 Mio. | 44 GB | **8,1 GB** | 8,1 GB | 13 h |
| Mecklenburg-Vorpommern | 17 | 0,24 Mio. | 45 GB | **3,9 GB** | 3,9 GB | 6 h |
| Schleswig-Holstein | 17 | 0,17 Mio. | 31 GB | **13,7 GB** | 13,7 GB | 2 h |
| Thüringen | 16 | 0,04 Mio. | 6 GB | **0,8 GB** | 0,8 GB | 2 h |
| Hamburg | 17 | 0,01 Mio. | 1,2 GB | **0,2 GB** | 0,2 GB | <1 h |
| **Summe** | | **12 Mio.** | **≈2 TB** | **≈360 GB** | **≈75 GB** | |

\* mit den 6 parallelen Downloads der App, aus den gemessenen Antwortzeiten hochgerechnet; die
Server schwanken stark (BW 0,25–2 s pro Kachel), also nur Größenordnung.

## Grenzsystem (erledigt)
- Landespolygone aus BKG VG250 (Land + Bodden/Watt/Seen, 5 m vereinfacht) in `germany_states.json`;
  Nachbarländer teilen exakt dieselbe Grenzlinie → keine Lücken, keine Überlappung
- Jeder Länderlayer hat `clipTo`: Kacheln ganz außerhalb werden gar nicht angefragt, Grenzkacheln
  im Browser exakt auf das Land maskiert, Kacheln im Inneren unverändert
- Bounding-Boxen der Layer werden automatisch aus den Polygonen berechnet
- Downloader und Platzschätzung zählen nur Kacheln, die das Land berühren
- Deutschland-Umriss (VG250 inkl. Küstengewässer) entscheidet, ob die Kartenmitte in Deutschland
  liegt; liegt sie im Nachbarland, kommen die (zugeschnittenen) deutschen Layer trotzdem oben drauf,
  sobald Deutschland im Bild ist (Salzburg, Basel, Saarland/Frankreich)
- Ergebnis: Naht BW/BY bei Ulm liegt jetzt exakt auf der Donau, MV-Meeresblöcke sind weg

## Performance (erledigt)
- WMS-Layer mit 512-px-Kacheln (≈2,5× Durchsatz bei langsamen Servern), eigener Cache-Ordner `<layer>@512`
- Länderlayer als JPEG statt PNG: 4–10× kleiner und vom Server schneller geliefert (BW 1,2 s → 0,25 s)
- Keine Leer-Wiederholung (1 s Pause) für Länderlayer, die außerhalb ihres Landes legitim leer sind
- `maxNativeZoom` passend zur Datenauflösung (BKG 16, 1-m-Daten 17)
- Layer außerhalb des Bildausschnitts werden nicht geladen; Kacheln außerhalb des Landes auch nicht
- BKG-Relief ab Zoom 14 nur noch in HE/NI/HB/ST (überall sonst lag es unsichtbar unter deckendem LiDAR)
- Kacheln, die aus dem Bild gescrollt sind, brechen ihren Download ab (gibt Verbindungen frei)
- Grenzdaten lokal gecacht (`border_cache/`), Grenzlinien per Canvas

## Weitere Geschwindigkeitsideen (offen)
1. **Proxy bricht Upstream nicht ab:** Wenn der Browser eine Kachel abbricht, holt der Proxy sie trotzdem
   fertig und belegt den Server weiter. Abbruch durchreichen oder Warteschlange nach Aktualität sortieren.
2. **Vorausladen im Leerlauf:** Wenn alles geladen ist, die nächste Zoomstufe bzw. den Rand rund um die
   Ansicht in den Cache holen, damit Zoomen/Verschieben sofort Bilder zeigt.
3. **Browser-Cache länger:** Der Proxy schickt `max-age=3600`; LiDAR-Kacheln ändern sich praktisch nie,
   30 Tage würden lokale Proxy-Anfragen sparen (kleiner Effekt, trivial).
4. **Parallelität pro Server:** Downloader nutzt fest 6 Threads für alle; NRW/SN/RP antworten in 0,2–0,3 s
   und vertragen mehr, BY/BW/BB brauchen 1–2 s. Adaptiv pro Server würde Bulk-Downloads deutlich verkürzen.
5. **Bayern nur eine Darstellung:** Zoom 14 nutzt Schräglicht, ab 15 kombiniert – zwei Cache-Sätze für
   dieselben Daten. Eine Darstellung für alle Zooms spart Platz und Anfragen beim Zoomwechsel.
6. **Eigene Kacheln für HE/NI/ST:** Dort gibt es DGM1 als offenen Download; einmal selbst gerechnete
   Schummerung (z. B. mit GDAL) als lokale Kacheln wäre schneller als jeder WMS – und feiner als BKG 5 m.
7. **Saarland-URL** ist ein Geoportal-Proxy-Hash und könnte sich ändern – bei Ausfällen zuerst prüfen.
