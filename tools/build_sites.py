"""Build the site catalogue for the "Fundstellen" panel (poi_data/sites/*.json).

Sources (all open, see the 'license' of every entry):
  - Wikidata (CC0): archaeological sites, castles, Roman forts, barrows, ... in DE, AT, CH, IT
  - Pleiades (CC BY 3.0): ancient places with dating (mostly Roman)
  - OpenStreetMap via Overpass (ODbL): bunkers, hollow ways, battlefields, archaeological sites in DE/AT/CH
  - Nomisma.org (ODbL / CC BY): coin hoards of the Roman Empire (CHRE), Republic (CHRR) and Greek hoards
    (IGCH); located at the findspot's place (town level), as the hoard databases publish them

Bavarian ground monuments (Wikidata P4244, the BLfD list) are left out on purpose: the app shows them
as the official red areas of the BLfD service, so they would only appear twice.

Run:  python tools/build_sites.py [wikidata] [pleiades] [osm] [nomisma] [legacy]     (default: all)
"""
import csv
import gzip
import io
import json
import os
import re
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'poi_data', 'sites')
CACHE = os.path.join(ROOT, 'tools', '_cache')
UA = {'User-Agent': 'TreasureHunter/1.0 (desktop app; site catalogue builder)'}

COUNTRIES = {'Q183': 'DE', 'Q40': 'AT', 'Q39': 'CH', 'Q38': 'IT'}

# Wikidata class -> (type, default epochs, default cultures)
WD_CLASSES = {
    'Q839954': ('archaeological_site', [], []),
    'Q13530412': ('viereckschanze', ['latene'], ['celts']),
    'Q192601': ('oppidum', ['latene'], ['celts']),
    'Q88205': ('roman_fort', ['roman'], ['romans']),
    'Q252021': ('villa_rustica', ['roman'], ['romans']),
    'Q194029': ('road', ['roman'], ['romans']),
    'Q1363360': ('hillfort', [], []),
    'Q744099': ('hillfort', [], []),
    'Q332128': ('hillfort', [], []),
    'Q19285917': ('hillfort', [], []),
    'Q91432': ('hillfort', ['early_medieval'], []),
    'Q1015644': ('castle_site', ['medieval'], []),
    'Q92062': ('castle_site', ['high_medieval'], []),
    'Q23413': ('castle', ['medieval'], []),
    'Q17715832': ('castle', ['medieval'], []),
    'Q34023': ('tumulus', ['prehistoric'], []),
    'Q10521078': ('megalith', ['neolithic'], []),
    'Q101659': ('megalith', ['neolithic'], []),
    'Q350895': ('deserted_village', ['medieval'], []),
    'Q325017': ('mining', [], []),
    'Q1183485': ('mining', [], []),
    'Q164099': ('hoard', [], []),
    'Q91203': ('sconce', ['modern'], []),
    'Q749151': ('landwehr', ['late_medieval'], []),
    'Q4895508': ('battlefield', [], []),
    'Q91122': ('bunker', ['world_wars'], []),
}

# Epochs found in German descriptions / names (chronological).
EPOCH_PATTERNS = [
    ('palaeolithic', r'Paläolith|Altsteinzeit'),
    ('mesolithic', r'Mesolith|Mittelsteinzeit'),
    ('neolithic', r'Neolith|Jungsteinzeit|Linearbandkeram|Glockenbecher|Schnurkeram|Michelsberg|Kupferzeit|Großsteingrab|Megalith'),
    ('bronze_age', r'Bronzezeit|bronzezeitl'),
    ('urnfield', r'Urnenfelder'),
    ('hallstatt', r'Hallstatt'),
    ('latene', r'Lat[eèé]ne|[Kk]elt'),
    ('roman', r'[Rr]ömisch|Römer|Kaiserzeit|Kastell|Limes|[Rr]oman'),
    ('migration_period', r'Völkerwanderung|Spätantike'),
    ('early_medieval', r'frühen Mittelalter|Frühmittelalter|frühmittelalterl|Merowinger|Reihengräber|Karoling|[Ss]lawisch'),
    ('high_medieval', r'hohen Mittelalter|Hochmittelalter|hochmittelalterl'),
    ('late_medieval', r'späten Mittelalter|Spätmittelalter|spätmittelalterl'),
    ('medieval', r'Mittelalter|mittelalterl|[Mm]edieval|medievale'),
    ('modern', r'Neuzeit|neuzeitl|Dreißigjährig|Napoleon'),
    ('world_wars', r'Weltkrieg|Westwall|Wehrmacht|Bunker|Flak'),
    ('prehistoric', r'vorgeschichtlich|[Pp]rähistor|[Pp]rehistor'),
    ('protohistoric', r'frühgeschichtlich'),
]
CULTURE_PATTERNS = {
    'celts': r'Lat[eèé]ne|[Kk]elt|Viereckschanze|Oppidum',
    'romans': r'[Rr]ömisch|Römer|Kastell|Limes|Villa rustica|[Rr]oman',
    'germanic': r'[Gg]erman',
    'alamanni': r'[Aa]laman',
    'bavarii': r'[Bb]aiuwar|[Bb]ajuwar',
    'franks': r'[Ff]ränkisch|Franken|Merowinger|Karoling',
    'slavs': r'[Ss]law',
    'etruscans': r'[Ee]trusk|[Ee]trusc',
}


def epochs_from(text):
    found = [k for k, rx in EPOCH_PATTERNS if re.search(rx, text or '')]
    if 'medieval' in found and any(e in found for e in ('early_medieval', 'high_medieval', 'late_medieval')):
        found.remove('medieval')
    return found


def cultures_from(text):
    return [k for k, rx in CULTURE_PATTERNS.items() if re.search(rx, text or '')]


def merge(*lists):
    out = []
    for lst in lists:
        for x in lst:
            if x not in out:
                out.append(x)
    return out


# ---------------------------------------------------------------- Bavaria (to avoid duplicates)

def _load_bavaria():
    path = os.path.join(ROOT, 'assets', 'countries', 'europe', 'germany_states.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)['DE-BY']


BAVARIA = None


def in_bavaria(lat, lon):
    global BAVARIA
    if BAVARIA is None:
        BAVARIA = _load_bavaria()
    if not (47.2 <= lat <= 50.6 and 8.9 <= lon <= 13.9):
        return False
    inside = False
    for ring in BAVARIA:
        j = len(ring) - 1
        for i in range(len(ring)):
            yi, xi = ring[i]
            yj, xj = ring[j]
            if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
    return inside


# ---------------------------------------------------------------- Wikidata

def sparql(query, tries=4):
    for i in range(tries):
        try:
            r = requests.post('https://query.wikidata.org/sparql', data={'query': query},
                              headers={**UA, 'Accept': 'application/sparql-results+json'}, timeout=180)
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(15 * (i + 1))
                continue
            r.raise_for_status()
            return r.json()['results']['bindings']
        except requests.RequestException as e:
            print('  retry', e)
            time.sleep(10)
    raise RuntimeError('Wikidata query failed')


def build_wikidata():
    entries = {}
    for cls, (typ, default_epochs, default_cultures) in WD_CLASSES.items():
        for cq, cc in COUNTRIES.items():
            query = f"""
SELECT ?i ?c ?lde ?lother ?d ?art WHERE {{
  ?i wdt:P31 wd:{cls}; wdt:P17 wd:{cq}; wdt:P625 ?c .
  FILTER NOT EXISTS {{ ?i wdt:P4244 [] }}
  OPTIONAL {{ ?i rdfs:label ?lde FILTER(lang(?lde) = "de") }}
  OPTIONAL {{ ?i rdfs:label ?lother FILTER(lang(?lother) IN ("it", "en")) }}
  OPTIONAL {{ ?i schema:description ?d FILTER(lang(?d) = "de") }}
  OPTIONAL {{ ?art schema:about ?i; schema:isPartOf <https://de.wikipedia.org/> }}
}}"""
            cache = os.path.join(CACHE, f'wd_{cls}_{cc}.json')
            if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 7 * 86400:
                with open(cache, encoding='utf-8') as f:
                    rows = json.load(f)
            else:
                rows = sparql(query)
                os.makedirs(CACHE, exist_ok=True)
                with open(cache, 'w', encoding='utf-8') as f:
                    json.dump(rows, f)
            n = 0
            for b in rows:
                qid = b['i']['value'].rsplit('/', 1)[-1]
                m = re.match(r'\s*Point\(\s*([-+\d.eE]+)\s+([-+\d.eE]+)\s*\)', b['c']['value'])
                if not m:
                    continue  # coordinates on another globe or malformed
                lon, lat = float(m.group(1)), float(m.group(2))
                name = (b.get('lde') or b.get('lother') or {}).get('value') or qid
                desc = (b.get('d') or {}).get('value', '')
                text = name + ' ' + desc
                e = entries.get(qid)
                if e is None:
                    e = entries[qid] = {
                        'id': f'wd:{qid}', 'name': name, 'lat': round(lat, 6), 'lon': round(lon, 6),
                        'epoch': [], 'culture': [], 'type': typ, 'country': cc, 'source': 'Wikidata',
                        'url': (b.get('art') or {}).get('value') or f'https://www.wikidata.org/wiki/{qid}',
                        'desc': desc, 'license': 'CC0',
                    }
                    n += 1
                elif e['type'] == 'archaeological_site' and typ != 'archaeological_site':
                    e['type'] = typ  # the more specific class wins
                e['epoch'] = merge(e['epoch'], epochs_from(text), default_epochs)
                e['culture'] = merge(e['culture'], cultures_from(text), default_cultures)
            print(f'  {cls} {cc}: {len(rows)} rows, {n} new')
            time.sleep(1)
    for e in entries.values():
        e['epoch'] = e['epoch'] or ['unknown']
        if 'latene' in e['epoch'] and 'celts' not in e['culture']:
            e['culture'].append('celts')
        if 'roman' in e['epoch'] and 'romans' not in e['culture']:
            e['culture'].append('romans')
    return list(entries.values())


# ---------------------------------------------------------------- Pleiades

PLEIADES_URL = 'https://atlantides.org/downloads/pleiades/dumps/pleiades-places-latest.csv.gz'
PLEIADES_PERIODS = {
    'archaic': 'iron_age', 'classical': 'iron_age', 'hellenistic-republican': 'roman', 'roman': 'roman',
    'late-antique': 'migration_period', 'mediaeval-byzantine': 'early_medieval', 'modern': 'modern',
    'bronze-age': 'bronze_age', 'neolithic': 'neolithic', 'iron-age': 'iron_age',
}
PLEIADES_TYPES = [
    ('fort', 'roman_fort'), ('fortress', 'roman_fort'), ('castrum', 'roman_fort'), ('villa', 'villa_rustica'),
    ('road', 'road'), ('station', 'road'), ('bridge', 'road'), ('tumulus', 'tumulus'), ('cemetery', 'cemetery'),
    ('tomb', 'cemetery'), ('mine', 'mining'), ('quarry', 'mining'), ('temple', 'sanctuary'), ('sanctuary', 'sanctuary'),
    ('oppidum', 'oppidum'), ('hillfort', 'hillfort'), ('settlement', 'settlement'), ('urban', 'settlement'),
    ('city', 'settlement'), ('vicus', 'settlement'),
]
# Rough boxes of DE, AT, CH, IT (Pleiades has no country field; neighbours slightly overlap)
BOXES = {'DE': (47.2, 55.1, 5.8, 15.1), 'AT': (46.3, 49.1, 9.5, 17.2), 'CH': (45.8, 47.9, 5.9, 10.5),
         'IT': (36.6, 47.1, 6.6, 18.6)}


def build_pleiades():
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, 'pleiades-places-latest.csv.gz')
    if not os.path.exists(path) or time.time() - os.path.getmtime(path) > 30 * 86400:
        r = requests.get(PLEIADES_URL, headers=UA, timeout=300)
        r.raise_for_status()
        with open(path, 'wb') as f:
            f.write(r.content)
    csv.field_size_limit(10 ** 8)
    out = []
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                lat, lon = float(r['reprLat']), float(r['reprLong'])
            except (TypeError, ValueError):
                continue
            country = next((c for c, (a, b, w, e) in BOXES.items() if a <= lat <= b and w <= lon <= e), None)
            if not country:
                continue
            ftypes = (r.get('featureTypes') or '').lower()
            typ = next((t for key, t in PLEIADES_TYPES if key in ftypes), 'archaeological_site')
            periods = [p.strip() for p in (r.get('timePeriodsKeys') or '').split(',') if p.strip()]
            epochs = merge([PLEIADES_PERIODS[p] for p in periods if p in PLEIADES_PERIODS]) or ['unknown']
            if typ == 'roman_fort' and 'roman' not in epochs:
                typ = 'hillfort'
            cultures = ['romans'] if 'roman' in epochs else []
            pid = r.get('id') or r.get('path', '').rsplit('/', 1)[-1]
            desc = (r.get('description') or '').strip()
            out.append({
                'id': f'pleiades:{pid}', 'name': r.get('title') or pid, 'lat': round(lat, 6), 'lon': round(lon, 6),
                'epoch': epochs, 'culture': cultures, 'type': typ, 'country': country, 'source': 'Pleiades',
                'url': f'https://pleiades.stoa.org/places/{pid}', 'desc': desc[:300],
                'precision': r.get('locationPrecision') or '', 'license': 'CC BY 3.0',
            })
    return out


# ---------------------------------------------------------------- OpenStreetMap

OVERPASS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
OSM_QUERIES = [
    ('bunker', 'nwr["military"="bunker"]'),
    ('hollow_way', 'nwr["historic"="hollow_way"]'),
    ('battlefield', 'nwr["historic"="battlefield"]'),
    ('archaeological_site', 'nwr["historic"="archaeological_site"]'),
]
OSM_SITE_TYPES = {'tumulus': 'tumulus', 'fortification': 'hillfort', 'settlement': 'settlement', 'villa': 'villa_rustica',
                  'necropolis': 'cemetery', 'megalith': 'megalith', 'mineral_extraction': 'mining', 'castle': 'castle_site',
                  'bastion': 'sconce', 'roman_villa': 'villa_rustica', 'crannog': 'settlement'}
OSM_CIVILIZATION = {'roman': ('roman', 'romans'), 'ancient_roman': ('roman', 'romans'), 'celtic': ('latene', 'celts'),
                    'la_tene': ('latene', 'celts'), 'hallstatt': ('hallstatt', ''), 'hallstatt_culture': ('hallstatt', ''),
                    'bronze_age': ('bronze_age', ''), 'bronze-age': ('bronze_age', ''), 'neolithic': ('neolithic', ''),
                    'prehistoric': ('prehistoric', ''), 'medieval': ('medieval', ''), 'early_medieval': ('early_medieval', ''),
                    'slavic': ('early_medieval', 'slavs'), 'germanic': ('', 'germanic'), 'iron_age': ('iron_age', ''),
                    'urnfield': ('urnfield', '')}


def overpass(query, cache_name):
    """Elements for an Overpass query; successful answers are cached, a timeout remark counts as failure."""
    path = os.path.join(CACHE, f'osm_{cache_name}.json')
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < 7 * 86400:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    for url in OVERPASS * 3:
        try:
            r = requests.post(url, data={'data': query}, headers=UA, timeout=400)
            if r.status_code == 200:
                d = r.json()
                if 'remark' in d and not d.get('elements'):
                    print('  overpass', url, d['remark'][:80])
                else:
                    os.makedirs(CACHE, exist_ok=True)
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(d['elements'], f)
                    return d['elements']
            else:
                print('  overpass', url, r.status_code)
        except (requests.RequestException, ValueError) as e:
            print('  overpass', url, e)
        time.sleep(30)
    print(f'  !! {cache_name} failed, left out')
    return []


DE_STATES = ['DE-BW', 'DE-BY', 'DE-BE', 'DE-BB', 'DE-HB', 'DE-HH', 'DE-HE', 'DE-MV', 'DE-NI', 'DE-NW', 'DE-RP',
             'DE-SL', 'DE-SN', 'DE-ST', 'DE-SH', 'DE-TH']


def build_osm(skip_wikidata_ids):
    out = []
    for cc in ('DE', 'AT', 'CH'):
        for typ, selector in OSM_QUERIES:
            if cc == 'DE' and typ in ('bunker', 'archaeological_site'):
                # big result sets: one query per state keeps each answer within the server's limits
                elements = []
                for st in DE_STATES:
                    q = f'[out:json][timeout:300];area["ISO3166-2"="{st}"]->.a;{selector}(area.a);out tags center;'
                    elements += overpass(q, f'{st}_{typ}')
                seen = set()
                elements = [e for e in elements if not ((e['type'], e['id']) in seen or seen.add((e['type'], e['id'])))]
            else:
                q = f'[out:json][timeout:360];area["ISO3166-1"="{cc}"][admin_level=2]->.a;{selector}(area.a);out tags center;'
                elements = overpass(q, f'{cc}_{typ}')
            n = 0
            for el in elements:
                tags = el.get('tags', {})
                if tags.get('wikidata') in skip_wikidata_ids:
                    continue
                lat = el.get('lat') or (el.get('center') or {}).get('lat')
                lon = el.get('lon') or (el.get('center') or {}).get('lon')
                if lat is None:
                    continue
                t = typ
                epochs, cultures = [], []
                if typ == 'archaeological_site':
                    if cc == 'DE' and in_bavaria(lat, lon):
                        continue  # covered by the official Bavarian monument areas
                    t = OSM_SITE_TYPES.get(tags.get('archaeological_site') or tags.get('site_type'), 'archaeological_site')
                    civ = (tags.get('historic:civilization') or '').lower().replace(' ', '_')
                    for part in re.split(r'[;,]', civ):
                        ep, cu = OSM_CIVILIZATION.get(part.strip(), ('', ''))
                        if ep:
                            epochs.append(ep)
                        if cu:
                            cultures.append(cu)
                elif typ == 'bunker':
                    epochs = ['world_wars']
                name = tags.get('name') or tags.get('name:de') or {
                    'bunker': 'Bunker', 'hollow_way': 'Hohlweg', 'battlefield': 'Schlachtfeld'}.get(typ, 'Fundstätte')
                text = name + ' ' + tags.get('description', '') + ' ' + tags.get('historic:period', '')
                epochs = merge(epochs, epochs_from(text)) or ['unknown']
                cultures = merge(cultures, cultures_from(text))
                out.append({
                    'id': f"osm:{el['type'][0]}{el['id']}", 'name': name, 'lat': round(lat, 6), 'lon': round(lon, 6),
                    'epoch': epochs, 'culture': cultures, 'type': t, 'country': cc, 'source': 'OpenStreetMap',
                    'url': f"https://www.openstreetmap.org/{el['type']}/{el['id']}",
                    'desc': tags.get('description', '')[:300], 'license': 'ODbL',
                })
                n += 1
            print(f'  OSM {cc} {typ}: {len(elements)} elements, {n} kept')
            time.sleep(5)
    return out


# ---------------------------------------------------------------- Nomisma (coin hoards)

NOMISMA_QUERY = """PREFIX nmo: <http://nomisma.org/ontology#> PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#> PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX void: <http://rdfs.org/ns/void#> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?h ?label ?lat ?long ?close ?place ?ds WHERE {
  ?h a nmo:Hoard; skos:prefLabel ?label; nmo:hasFindspot/crm:P7_took_place_at ?pl .
  ?pl crm:P89_falls_within ?g . ?g geo:location ?loc . ?loc geo:lat ?lat; geo:long ?long .
  OPTIONAL { ?pl rdfs:label ?place } OPTIONAL { ?h nmo:hasClosingDate ?close } OPTIONAL { ?h void:inDataset ?ds }
  FILTER(?lat > 36 && ?lat < 55.5 && ?long > 5.5 && ?long < 19) }"""
NOMISMA_DATASETS = {'chre': 'Coin Hoards of the Roman Empire', 'chrr': 'Coin Hoards of the Roman Republic',
                    'coinhoards': 'Inventory of Greek Coin Hoards'}


def _hoard_epoch(year, dataset):
    if year is None:
        return ['roman'] if dataset in ('chre', 'chrr') else ['unknown']
    if year < -27:
        return ['roman'] if dataset == 'chrr' else ['iron_age']
    if year <= 476:
        return ['roman']
    return ['early_medieval'] if year <= 1000 else ['medieval']


def build_nomisma():
    r = requests.get('https://nomisma.org/query', params={'query': NOMISMA_QUERY},
                     headers={**UA, 'Accept': 'application/sparql-results+json'}, timeout=300)
    r.raise_for_status()
    hoards = {}
    for b in r.json()['results']['bindings']:
        uri = b['h']['value']
        if uri in hoards:
            continue
        ds_uri = (b.get('ds') or {}).get('value', '')
        dataset = 'chre' if 'chre' in ds_uri else 'chrr' if 'chrr' in ds_uri else 'coinhoards'
        try:
            year = int((b.get('close') or {}).get('value'))
        except (TypeError, ValueError):
            year = None
        lat, lon = float(b['lat']['value']), float(b['long']['value'])
        place = (b.get('place') or {}).get('value') or b['label']['value']
        epochs = _hoard_epoch(year, dataset)
        when = '' if year is None else (f'{-year} v. Chr.' if year < 0 else f'{year} n. Chr.')
        hoards[uri] = {
            'id': 'nomisma:' + uri.rsplit('/', 1)[-1], 'name': f'Hortfund {place}', 'lat': round(lat, 5), 'lon': round(lon, 5),
            'epoch': epochs, 'culture': ['romans'] if 'roman' in epochs else [], 'type': 'hoard',
            'country': next((c for c, (a, bb, w, e) in BOXES.items() if a <= lat <= bb and w <= lon <= e), ''),
            'source': 'Nomisma', 'url': uri,
            'desc': (f'Münzhort, Schlussmünze {when}. ' if when else 'Münzhort. ') +
                    f'{NOMISMA_DATASETS[dataset]} ({b["label"]["value"]}). Lage nur auf Ortsebene.',
            'precision': 'place', 'license': 'Nomisma.org (ODbL / CC BY)',
        }
    return list(hoards.values())


# ---------------------------------------------------------------- the app's earlier coin / treasure lists

LEGACY_COIN_FILES = {
    # file under poi_data -> (type, epochs, cultures)
    'celts/kelten_münze.json': ('coin_find', ['latene'], ['celts']),
    'romans/römer_münze.json': ('coin_find', ['roman'], ['romans']),
    'celts/kelten_treasure.json': ('hoard', ['latene'], ['celts']),
    'romans/römer_schatz.json': ('hoard', ['roman'], ['romans']),
}


def build_legacy_coins():
    out = []
    for rel, (typ, epochs, cultures) in LEGACY_COIN_FILES.items():
        path = os.path.join(ROOT, 'poi_data', rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as f:
            items = json.load(f)
        for i, it in enumerate(items):
            coords = it.get('location_coordinates') or {}
            lat, lon = it.get('lat', coords.get('latitude')), it.get('lon', coords.get('longitude'))
            if lat is None or lon is None:
                continue
            name = it.get('name') or it.get('artifact') or it.get('location') or 'Fund'
            text = re.sub(r'Vorlage:\S+', '', it.get('zusammenfassung') or it.get('description') or '').strip()
            out.append({
                'id': f'legacy:{os.path.basename(rel)}:{i}', 'name': name, 'lat': round(float(lat), 6),
                'lon': round(float(lon), 6), 'epoch': epochs, 'culture': cultures, 'type': typ, 'country': '',
                'source': 'Wikipedia', 'url': it.get('url') or it.get('wikipedia_url') or
                (f"https://www.wikidata.org/wiki/{it['wikidata_id']}" if it.get('wikidata_id') else ''),
                'desc': text[:300], 'license': 'Wikipedia (CC BY-SA)',
            })
    return out


def save(name, entries):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f'{name}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, separators=(',', ':'))
    print(f'{name}: {len(entries)} entries -> {path} ({os.path.getsize(path) / 1e6:.1f} MB)')


def main(which):
    if 'wikidata' in which:
        print('Wikidata ...')
        save('wikidata', build_wikidata())
    if 'pleiades' in which:
        print('Pleiades ...')
        save('pleiades', build_pleiades())
    if 'osm' in which:
        print('OpenStreetMap ...')
        skip = set()
        wd_path = os.path.join(OUT_DIR, 'wikidata.json')
        if os.path.exists(wd_path):
            with open(wd_path, encoding='utf-8') as f:
                skip = {e['id'][3:] for e in json.load(f)}
        save('osm', build_osm(skip))
    if 'legacy' in which:
        print('Earlier coin / treasure lists ...')
        save('muenzen_horte', build_legacy_coins())
    if 'nomisma' in which:
        print('Nomisma ...')
        save('nomisma', build_nomisma())


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main(set(sys.argv[1:]) or {'wikidata', 'pleiades', 'osm', 'nomisma', 'legacy'})
