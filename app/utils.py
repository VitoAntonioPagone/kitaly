import re
import unicodedata

from app.models import map_national_team, NATIONAL_TEAM_PAIRS

TYPE_LABELS_IT = {
    'Shirt': 'Maglia',
    'Training Top': "Capo d'allenamento",
    'Polo Shirt': 'Polo',
    'T-Shirt': 'Maglietta',
    'Sweatshirt': 'Felpa',
    'Hoodie': 'Felpa con cappuccio',
    'Coat': 'Giacca',
    '1/4 Zip': '1/4 Zip',
    'Track Jacket': 'Giacca di Tuta',
    'Tracksuit': 'Tuta',
    'Bottoms': 'Pantaloni',
    'Shorts': 'Pantaloncini',
    'Gilet': 'Smanicato',
    'Vest': 'Canottiera',
    'Accessory': 'Accessorio',
    'Accessories': 'Accessorio',
    'Accessorio': 'Accessorio',
}

FEATURE_LABELS_IT = {
    'Home': 'Casa',
    'Away': 'Trasferta',
    'Third': 'Terza',
    'Fourth': 'Quarta',
    'Goalkeeper': 'Portiere',
    'GK': 'Portiere',
}

SLEEVE_LABELS_IT = {
    'L/S': 'Maniche Lunghe',
    'S/S': 'Maniche Corte',
}

SLEEVE_LABELS_EN = {
    'L/S': 'Long Sleeve',
    'S/S': 'Short Sleeve',
}

COLOR_LABELS_IT = {
    'black': 'Nero',
    'white': 'Bianco',
    'red': 'Rosso',
    'blue': 'Blu',
    'yellow': 'Giallo',
    'green': 'Verde',
    'purple': 'Viola',
    'orange': 'Arancione',
    'grey': 'Grigio',
    'gray': 'Grigio',
    'gold': 'Oro',
    'silver': 'Argento',
    'navy': 'Blu Navy',
    'burgundy': 'Bordeaux',
}

_SEASON_START_YEAR_REGEX = re.compile(r'((?:19|20)\d{2})')
_SIZE_ORDER = {
    'XXS': 0,
    'XS': 1,
    'S': 2,
    'M': 3,
    'L': 4,
    'XL': 5,
    'XXL': 6,
    '3XL': 7,
    '4XL': 8,
    '5XL': 9,
}
_ACCESSORY_TYPE_KEYS = {
    'accessory',
    'accessories',
    'accessorio',
    'accessori',
}


def _normalize_team_key(value):
    if not value:
        return ''
    key = re.sub(r'\s+', ' ', str(value).strip().lower())
    key = key.replace('.', '')
    return key.strip()


TEAM_NAME_EN_MAP = {}
for en_name, it_name in NATIONAL_TEAM_PAIRS:
    TEAM_NAME_EN_MAP[_normalize_team_key(en_name)] = en_name
    TEAM_NAME_EN_MAP[_normalize_team_key(it_name)] = en_name

def slugify_text(value):
    if not value:
        return ''
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug

def type_label(value, locale):
    if not value:
        return ''
    label = value
    if label == 'Training Shirt':
        label = 'Training Top'
    if locale == 'it':
        return TYPE_LABELS_IT.get(label, label)
    return label

def season_sort_key(value):
    if value is None:
        return (float('inf'), '')

    text = str(value).strip()
    if not text:
        return (float('inf'), '')

    match = _SEASON_START_YEAR_REGEX.search(text)
    if match:
        return (int(match.group(1)), text.lower())

    return (float('inf'), text.lower())

def size_sort_key(value):
    if value is None:
        return (float('inf'), '')

    text = str(value).strip()
    if not text:
        return (float('inf'), '')

    normalized = text.upper().replace('.', '').replace(' ', '')
    return (_SIZE_ORDER.get(normalized, 100), normalized)

def is_accessory_type(value):
    if value is None:
        return False
    key = str(value).strip().lower()
    return key in _ACCESSORY_TYPE_KEYS

def type_label_or_shirt(value, locale):
    if value:
        return type_label(value, locale)
    return 'Maglia' if locale == 'it' else 'Shirt'

def feature_label(value, locale):
    if not value:
        return ''
    if locale == 'it':
        return FEATURE_LABELS_IT.get(value, value)
    return value

def sleeve_label(value, locale):
    if not value:
        return ''
    if locale == 'it':
        return SLEEVE_LABELS_IT.get(value, value)
    return SLEEVE_LABELS_EN.get(value, value)

def color_label(value, locale):
    if not value:
        return ''
    if locale != 'it':
        return value
    key = str(value).strip().lower()
    return COLOR_LABELS_IT.get(key, value)

def team_name_localized(shirt, locale):
    team_name = getattr(shirt, 'squadra', None)
    if not team_name:
        return team_name
    if locale == 'it' and getattr(shirt, 'nazionale', False):
        return map_national_team(team_name)
    return team_name


def team_name_localized_value(name, locale):
    if not name:
        return name
    if locale == 'it':
        return map_national_team(name)
    key = _normalize_team_key(name)
    return TEAM_NAME_EN_MAP.get(key, name)

def competition_label_localized(shirt, locale):
    campionato = getattr(shirt, 'campionato', None)
    if not campionato:
        return campionato
    key = str(campionato).strip().lower()
    is_national = getattr(shirt, 'nazionale', False) or key in ['nazionali', 'nazionale', 'national teams', 'national team']
    if locale == 'en' and is_national:
        return 'National Teams'
    if locale == 'it' and key in ['national teams', 'national team']:
        return 'Nazionali'
    return campionato

def build_shirt_slug(shirt, locale):
    parts = []
    if getattr(shirt, 'player_name', None):
        parts.append(shirt.player_name)
    if getattr(shirt, 'maniche', None):
        parts.append(sleeve_label(shirt.maniche, locale))
    team_name = team_name_localized(shirt, locale)
    if team_name:
        parts.append(team_name)
    if getattr(shirt, 'brand', None):
        parts.append(shirt.brand)
    if getattr(shirt, 'tipologia', None):
        parts.append(shirt.tipologia)
    parts.append(type_label_or_shirt(getattr(shirt, 'type', None), locale))
    competition = competition_label_localized(shirt, locale)
    if competition:
        parts.append(competition)
    if getattr(shirt, 'colore', None):
        parts.append(color_label(shirt.colore, locale))
    if getattr(shirt, 'taglia', None):
        parts.append(shirt.taglia)
    if getattr(shirt, 'stagione', None):
        parts.append(shirt.stagione)
    if getattr(shirt, 'player_issued', False):
        parts.append('Player Issue' if locale == 'en' else 'Player Issue')

    slug = slugify_text(' '.join([p for p in parts if p]))
    return slug or str(getattr(shirt, 'id', '') or '')
