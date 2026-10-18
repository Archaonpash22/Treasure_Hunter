# LiDAR-Layer pro Bundesland (Süd → Nord)

Ziel: für jedes Land die feinste frei nutzbare Geländeschummerung (DGM aus Laserscanning) als Terrain-Layer.
Alle Länderlayer liegen in einem Stapel über dem bundesweiten BKG-Relief (`assets/countries/europe/germany.py`).

| # | Land | Status | Quelle / Auflösung |
|---|------|--------|--------------------|
| 1 | Baden-Württemberg (BW) | ✅ fertig | LGL-BW DGM 25 cm Schummerung (bis Zoom 19) |
| 2 | Bayern (BY) | ✅ fertig | LDBV Geländerelief aus DGM1 (1 m, bis Zoom 17); nichts Feineres offen |
| 3 | Saarland (SL) | ✅ fertig | LVGL `sl_shaded_relief_2025`, Laserdaten 2025, ~0,5 m (bis Zoom 18); URL ist ein Geoportal-Proxy-Hash |
| 4 | Rheinland-Pfalz (RP) | ✅ fertig | LVermGeo `rp_shade1m`, DGM 1 m (bis Zoom 17) |
| 5 | Hessen (HE) | ➖ kein Dienst | HVBG bietet nur farbiges DGM; BKG bleibt; DGM1 offen als WCS/Download |
| 6 | Thüringen (TH) | ✅ fertig | TLBG `DGM2`, 2 m (bis Zoom 16); weißer Rand außerhalb TH wird transparent gemacht |
| 7 | Sachsen (SN) | ✅ fertig | GeoSN `relief_standard`, DGM1, ~0,5 m Pixel (bis Zoom 18) |
| 8 | Nordrhein-Westfalen (NW) | ✅ fertig | Geobasis NRW DGM-Schummerung 25 cm (bis Zoom 19) |
| 9 | Sachsen-Anhalt (ST) | ➖ kein LiDAR-Dienst | nur DGM5-Relief (= BKG-Niveau), BKG bleibt; DGM1 nur als Download/WCS |
| 10 | Berlin (BE) | ✅ fertig | über LGB-Dienst BB-BE (Berlins eigener Layer ist nur 30 % deckend) |
| 11 | Brandenburg (BB) | ✅ fertig | LGB `dgmshade`, DGM 1 m (bis Zoom 17) |
| 12 | Niedersachsen (NI) | ➖ kein offener Dienst | LGLN-Schummerung nur mit Vertrag; BKG bleibt; DGM1 als COG-Download |
| 13 | Bremen (HB) | ➖ kein offener Dienst | nur DGM-Farbdarstellung / DOM-Schummerung; BKG bleibt |
| 14 | Hamburg (HH) | ✅ fertig | LGV DGM-Schummerung 1 m (bis Zoom 17) |
| 15 | Mecklenburg-Vorpommern (MV) | ✅ fertig | LAiV `schummerung_NW`, DGM1; eingebranntes Wasserzeichen wird abgeschnitten |
| 16 | Schleswig-Holstein (SH) | ✅ fertig | GDI-SH `WMS_SH_DGM` Layer 4, DGM1 20-fach überhöht; Lizenz des Dienstes nicht dokumentiert |

## Performance (erledigt)
- WMS-Layer mit 512-px-Kacheln (≈2,5× Durchsatz bei langsamen Servern), eigener Cache-Ordner `<layer>@512`
- Keine Leer-Wiederholung (1 s Pause) für Länderlayer, die außerhalb ihres Landes legitim leer sind
- `maxNativeZoom` passend zur Datenauflösung (BKG 16, 1-m-Daten 17)
- Layer außerhalb des Bildausschnitts werden nicht geladen
- Grenzdaten lokal gecacht (`border_cache/`), Grenzlinien per Canvas
