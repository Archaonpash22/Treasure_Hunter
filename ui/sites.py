"""Site catalogue (poi_data/sites/*.json, built by tools/build_sites.py): labels, colours, filtering."""
import json
import os

# Epochs in chronological order: key -> (German label, colour group)
EPOCHS = {
    'palaeolithic': ('Altsteinzeit', 'stone'),
    'mesolithic': ('Mittelsteinzeit', 'stone'),
    'neolithic': ('Jungsteinzeit', 'stone'),
    'bronze_age': ('Bronzezeit', 'bronze'),
    'urnfield': ('Urnenfelderzeit', 'bronze'),
    'hallstatt': ('Hallstattzeit', 'iron'),
    'latene': ('Latènezeit (Kelten)', 'iron'),
    'iron_age': ('Eisenzeit / vorrömisch', 'iron'),
    'roman': ('Römerzeit', 'roman'),
    'migration_period': ('Völkerwanderung / Spätantike', 'early'),
    'early_medieval': ('Frühmittelalter', 'early'),
    'high_medieval': ('Hochmittelalter', 'medieval'),
    'late_medieval': ('Spätmittelalter', 'medieval'),
    'medieval': ('Mittelalter (allgemein)', 'medieval'),
    'modern': ('Neuzeit', 'modern'),
    'world_wars': ('Weltkriege', 'wars'),
    'prehistoric': ('Vorgeschichte (undatiert)', 'stone'),
    'protohistoric': ('Frühgeschichte (undatiert)', 'early'),
    'unknown': ('Ohne Datierung', 'unknown'),
}
EPOCH_COLORS = {'stone': '#b08d5f', 'bronze': '#d69a3c', 'iron': '#7fb07a', 'roman': '#d0605a', 'early': '#a184cf',
                'medieval': '#5f93d6', 'modern': '#6fb3b8', 'wars': '#9aa0a8', 'unknown': '#e6e1d6'}

TYPES = {
    'tumulus': 'Grabhügel', 'megalith': 'Großsteingrab / Dolmen', 'cemetery': 'Gräberfeld', 'viereckschanze': 'Viereckschanze',
    'oppidum': 'Oppidum', 'hillfort': 'Wallanlage / Ringwall', 'castle_site': 'Burgstall / Motte', 'castle': 'Burg / Burgruine',
    'roman_fort': 'Kastell / Militärlager', 'villa_rustica': 'Villa rustica', 'road': 'Straße / Station',
    'settlement': 'Siedlung', 'sanctuary': 'Heiligtum / Tempel', 'deserted_village': 'Wüstung', 'mining': 'Bergbau / Pinge',
    'hoard': 'Depotfund / Hort', 'coin_find': 'Münzfund', 'sconce': 'Schanze', 'landwehr': 'Landwehr', 'hollow_way': 'Hohlweg',
    'battlefield': 'Schlachtfeld', 'bunker': 'Bunker', 'archaeological_site': 'Archäologische Stätte (allgemein)',
}

CULTURES = {
    'celts': 'Kelten', 'romans': 'Römer', 'germanic': 'Germanen', 'alamanni': 'Alamannen', 'bavarii': 'Bajuwaren',
    'franks': 'Franken', 'slavs': 'Slawen', 'etruscans': 'Etrusker',
}

SITES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'poi_data', 'sites')


def load_sites():
    """All entries of all source files; returns (entries, {source: count})."""
    entries, per_source = [], {}
    if not os.path.isdir(SITES_DIR):
        return entries, per_source
    for name in sorted(os.listdir(SITES_DIR)):
        if not name.endswith('.json'):
            continue
        with open(os.path.join(SITES_DIR, name), encoding='utf-8') as f:
            data = json.load(f)
        for e in data:
            e['epoch'] = [ep for ep in e.get('epoch') or [] if ep in EPOCHS] or ['unknown']
            if e.get('type') not in TYPES:
                e['type'] = 'archaeological_site'
        entries += data
        if data:
            per_source[data[0].get('source', name)] = len(data)
    return entries, per_source


def counts(entries):
    """{epoch: {type: n}} – an entry counts under each of its epochs."""
    out = {}
    for e in entries:
        for ep in e['epoch']:
            bucket = out.setdefault(ep, {})
            bucket[e['type']] = bucket.get(e['type'], 0) + 1
    return out


def select(entries, pairs, culture=None, text=''):
    """Entries with (epoch, type) in pairs, optionally of one culture and containing text."""
    text = text.strip().lower()
    out = []
    for e in entries:
        if not any((ep, e['type']) in pairs for ep in e['epoch']):
            continue
        if culture and culture not in (e.get('culture') or []):
            continue
        if text and text not in (e['name'] + ' ' + (e.get('desc') or '')).lower():
            continue
        out.append(e)
    return out


def for_map(entries):
    """Compact records for the page: colour by the oldest epoch, labels resolved."""
    out = []
    for e in entries:
        first = e['epoch'][0]
        out.append({
            'n': e['name'], 'la': e['lat'], 'lo': e['lon'],
            'c': EPOCH_COLORS[EPOCHS[first][1]],
            'e': ', '.join(EPOCHS[ep][0] for ep in e['epoch']),
            't': TYPES[e['type']],
            'k': ', '.join(CULTURES.get(c, c) for c in e.get('culture') or []),
            'd': (e.get('desc') or '')[:220], 's': e.get('source', ''), 'u': e.get('url', ''),
        })
    return out
