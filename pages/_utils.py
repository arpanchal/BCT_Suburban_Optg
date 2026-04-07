import json
import os
import streamlit as st
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(__file__))

STATIONS = [
    'CCG','MEL','CYR','GTR','BCL','BCT','MX','PL','PBHD','DDR',
    'MRU','MM','BA','BDTS','KHAR','STC','VLP','ADH',
    'JOS','RMAR','GMN','MDD','KILE','BVI',
    'DIC','MIRA','BYR','NIG','BSR','NSP','VR',
    'VTN','SAH','KLV','PLG','UOI','BOR','VGN','DRD'
]

# All stations that have ARR/DEP variants (halt stations for M/E and DRD trains)
HALT_STNS = {
    'DDR','ADH','BVI','BYR','BSR','NSP','VR',
    'VTN','SAH','KLV','PLG','UOI','BOR','VGN','DRD'
}

STN_INDEX = {s: i for i, s in enumerate(STATIONS)}

# Line definitions
LINES_DEF = {
    'DNTL': {'label': 'Down Through Line',   'color': '#1565C0', 'color_fast': '#2979FF'},
    'DNLL': {'label': 'Down Local Line',     'color': '#2E7D32', 'color_fast': '#00C853'},
    'UPTL': {'label': 'Up Through Line',     'color': '#AD1457', 'color_fast': '#FF4081'},
    'UPLL': {'label': 'Up Local Line',       'color': '#BF360C', 'color_fast': '#FF6D00'},
    'DNHB': {'label': 'Down Harbour Branch', 'color': '#F57F17', 'color_fast': '#FFD600'},
    'UPHB': {'label': 'Up Harbour Branch',   'color': '#6A1B9A', 'color_fast': '#AA00FF'},
    '5L':   {'label': '5th Line',            'color': '#00695C', 'color_fast': '#1DE9B6'},
    '6L':   {'label': '6th Line',            'color': '#4527A0', 'color_fast': '#7C4DFF'},
    'MAIN': {'label': 'Main (shared)',       'color': '#37474F', 'color_fast': '#78909C'},
    'AUTO': {'label': 'Auto',                'color': '#757575', 'color_fast': '#9E9E9E'},
}

# Train category colours — MAIL is now a primary category
CAT_COLORS = {
    'LOCAL':    {'slow': '#4CAF50', 'fast': '#00E676', 'label': 'Local'},
    'AC_LOCAL': {'slow': '#29B6F6', 'fast': '#00E5FF', 'label': 'AC Local'},
    'DRD':      {'slow': '#FF7043', 'fast': '#FF3D00', 'label': 'DRD Branch'},
    'MAIL':     {'slow': '#E65100', 'fast': '#FF6D00', 'label': 'Mail/Express (M/E)'},
    'EXPRESS':  {'slow': '#FF4081', 'fast': '#FF0044', 'label': 'Express'},
    'EMPTY':    {'slow': '#78909C', 'fast': '#90A4AE', 'label': 'Empty'},
}

CARS_OPTIONS = ['12 CAR', '12 CAR AC', '15 CAR']

def cars_filter_label(ac, cars):
    c = str(cars).strip()
    a = str(ac).strip()
    if '15' in c:    return '15 CAR'
    if a == 'AC':    return '12 CAR AC'
    return '12 CAR'

@st.cache_data
def load_stops(_mtime=None):
    """Load stops from JSON. Pass file mtime so cache invalidates on regeneration."""
    with open(os.path.join(BASE, "stops_data.json")) as f:
        return json.load(f)["stops"]

@st.cache_data
def load_meta(_mtime=None):
    """Load train metadata. Pass file mtime so cache invalidates on regeneration."""
    with open(os.path.join(BASE, "train_meta.json")) as f:
        return json.load(f)

def _stops_mtime():
    """Return mtime of stops_data.json so callers can bust the cache."""
    p = os.path.join(BASE, "stops_data.json")
    return os.path.getmtime(p) if os.path.exists(p) else 0

def _meta_mtime():
    """Return mtime of train_meta.json."""
    p = os.path.join(BASE, "train_meta.json")
    return os.path.getmtime(p) if os.path.exists(p) else 0

@st.cache_data
def get_trains_dict(_mtime=None):
    stops = load_stops(_mtime=_mtime)
    d = defaultdict(list)
    for s in stops:
        d[s["train"]].append(s)
    return dict(d)

def fmt_min(m):
    real = m % 1440
    return f"{real//60:02d}:{real%60:02d}"

def stop_color(stop):
    cat  = stop.get('train_cat', 'LOCAL')
    typ  = stop.get('type', 'SLOW')
    cols = CAT_COLORS.get(cat, CAT_COLORS['LOCAL'])
    return cols['fast'] if typ == 'FAST' else cols['slow']

def line_color(line, typ='SLOW'):
    ld = LINES_DEF.get(line, LINES_DEF['AUTO'])
    return ld['color_fast'] if typ == 'FAST' else ld['color']
