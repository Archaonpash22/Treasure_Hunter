# LiDAR-Layer für Europa

Ziel: für jedes Land und jede Region die feinste frei nutzbare Geländeschummerung (DGM aus Laserscanning).
Reihenfolge (festgelegt 2026-10-19):
1. Deutschland ✅ (alle 16 Länder ≥ 1 m, BW/NW 25 cm)
2. Österreich ✅ (überall ≥ 1 m, Tirol/OÖ 0,5 m, Vorarlberg 25 cm)
3. Italien ⏳ (Regionen; bisher Toskana, Emilia-Romagna, TINITALY 10 m)
4. Kroatien
5. Niederlande (AHN)
6. Frankreich (IGN LiDAR HD)
7. Spanien (PNOA-LiDAR)
8. Portugal
9. Schweiz (bisher swissALTI3D-Schummerung landesweit)
10. danach alle übrigen EU-Länder

In der App sind alle LiDAR-Regionen anfangs aus und werden im Panel „Gelände“ einzeln eingeschaltet;
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
