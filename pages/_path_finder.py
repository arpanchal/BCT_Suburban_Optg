"""
Path Finder Engine — WR Mumbai Suburban Railway
Finds available time slots for introducing new trains on existing lines.
"""
import json, os
from bisect import bisect_left
from collections import defaultdict

# ── Line / Track Definitions ──────────────────────────────────────────────────
# Per operational rules provided:
# DNLL / UPLL  :  CCG ↔ VR   (Down/Up Local Line, 4-track section)
# DNTL / UPTL  :  CCG ↔ DRD  (Down/Up Through Line, 4-track section)
# DNHB / UPHB  :  BA  ↔ GMN  (Harbour Branch)
# 5L / 6L      :  BDTS–ADH–BVI (5th/6th lines, special section)
#
# Crossing rules for DOWN trains:
#   DNLL → DNHB: can cross at BA or ADH
#   DNHB → DNLL: can rejoin at ADH
# For UP trains:
#   UPHB → UPLL: cross at ADH only

LINES_META = {
    'DNLL': {
        'label':     'Down Local Line',
        'direction': 'DOWN',
        'desc':      'CCG → VR (slow trains, all local stops)',
        'color':     '#00C853',
        'route': ['CCG','MEL','CYR','GTR','BCL','BCT','MX','PL','PBHD','DDR',
                  'MRU','MM','BA','BDTS','KHAR','STC','VLP','ADH',
                  'JOS','RMAR','GMN','MDD','KILE','BVI','DIC','MIRA',
                  'BYR','NIG','BSR','NSP','VR'],
        'offsets': {'CCG':0,'MEL':3,'CYR':5,'GTR':8,'BCL':10,'BCT':13,
                    'MX':16,'PL':19,'PBHD':22,'DDR':24,'MRU':26,'MM':29,
                    'BA':33,'BDTS':36,'KHAR':39,'STC':41,'VLP':44,'ADH':49,
                    'JOS':52,'RMAR':55,'GMN':57,'MDD':61,'KILE':64,'BVI':70,
                    'DIC':74,'MIRA':79,'BYR':84,'NIG':90,'BSR':95,'NSP':100,'VR':107},
    },
    'UPLL': {
        'label':     'Up Local Line',
        'direction': 'UP',
        'desc':      'VR → CCG (slow trains, all local stops)',
        'color':     '#FF6D00',
        'route': ['VR','NSP','BSR','NIG','BYR','MIRA','DIC','BVI','KILE','MDD',
                  'GMN','RMAR','JOS','ADH','VLP','STC','KHAR','BDTS','BA',
                  'MM','MRU','DDR','PBHD','PL','MX','BCT','BCL','GTR','CYR','MEL','CCG'],
        'offsets': {'VR':0,'NSP':7,'BSR':12,'NIG':18,'BYR':23,'MIRA':28,'DIC':33,
                    'BVI':37,'KILE':43,'MDD':46,'GMN':50,'RMAR':52,'JOS':55,
                    'ADH':58,'VLP':63,'STC':66,'KHAR':68,'BDTS':71,'BA':74,
                    'MM':77,'MRU':80,'DDR':83,'PBHD':85,'PL':87,'MX':90,
                    'BCT':93,'BCL':96,'GTR':99,'CYR':101,'MEL':104,'CCG':107},
    },
    'DNTL': {
        'label':     'Down Through Line',
        'direction': 'DOWN',
        'desc':      'CCG → DRD (fast trains, skips slow-only stops)',
        'color':     '#2979FF',
        'route': ['CCG','MEL','CYR','GTR','BCL','BCT','DDR','BA','ADH',
                  'JOS','RMAR','GMN','MDD','KILE','BVI','DIC','MIRA',
                  'BYR','NIG','BSR','NSP','VR','VTN','SAH','KLV','PLG','UOI','BOR','VGN','DRD'],
        'offsets': {'CCG':0,'MEL':3,'CYR':5,'GTR':8,'BCL':10,'BCT':13,'DDR':24,
                    'BA':30,'ADH':39,'JOS':43,'RMAR':46,'GMN':48,'MDD':52,
                    'KILE':55,'BVI':61,'DIC':65,'MIRA':70,'BYR':75,'NIG':81,
                    'BSR':86,'NSP':91,'VR':98,'VTN':105,'SAH':111,'KLV':116,
                    'PLG':124,'UOI':130,'BOR':137,'VGN':145,'DRD':156},
    },
    'UPTL': {
        'label':     'Up Through Line',
        'direction': 'UP',
        'desc':      'DRD → CCG (fast trains)',
        'color':     '#FF4081',
        'route': ['DRD','VGN','BOR','UOI','PLG','KLV','SAH','VTN','VR','NSP','BSR',
                  'NIG','BYR','MIRA','DIC','BVI','KILE','MDD','GMN','RMAR','JOS',
                  'ADH','BA','DDR','BCT','BCL','GTR','CYR','MEL','CCG'],
        'offsets': {'DRD':0,'VGN':11,'BOR':19,'UOI':26,'PLG':32,'KLV':40,'SAH':45,
                    'VTN':51,'VR':58,'NSP':65,'BSR':70,'NIG':75,'BYR':81,
                    'MIRA':86,'DIC':91,'BVI':95,'KILE':101,'MDD':104,'GMN':108,
                    'RMAR':110,'JOS':113,'ADH':116,'BA':126,'DDR':132,
                    'BCT':143,'BCL':146,'GTR':149,'CYR':151,'MEL':154,'CCG':156},
    },
    'DNHB': {
        'label':     'Down Harbour Branch',
        'direction': 'DOWN',
        'desc':      'BA → GMN (via KHAR, STC, VLP, ADH)',
        'color':     '#FFD600',
        'route': ['BA','KHAR','STC','VLP','ADH','JOS','RMAR','GMN'],
        'offsets': {'BA':0,'KHAR':4,'STC':7,'VLP':10,'ADH':15,'JOS':19,'RMAR':22,'GMN':26},
    },
    'UPHB': {
        'label':     'Up Harbour Branch',
        'direction': 'UP',
        'desc':      'GMN → BA (via RMAR, JOS, ADH, VLP, STC, KHAR)',
        'color':     '#AA00FF',
        'route': ['GMN','RMAR','JOS','ADH','VLP','STC','KHAR','BA'],
        'offsets': {'GMN':0,'RMAR':4,'JOS':7,'ADH':12,'VLP':17,'STC':20,'KHAR':23,'BA':27},
    },
}

# Which stations belong to each line (for section filters)
LINE_ENDPOINT_RULES = {
    'DNLL': ('CCG', 'VR'),
    'UPLL': ('VR',  'CCG'),
    'DNTL': ('CCG', 'DRD'),
    'UPTL': ('DRD', 'CCG'),
    'DNHB': ('BA',  'GMN'),
    'UPHB': ('GMN', 'BA'),
}

# Crossover possibilities (downstream, upstream)
# DOWN: DNLL→DNHB at BA or ADH; DNHB→DNLL at ADH
# UP:   UPHB→UPLL at ADH only
CROSSOVERS = {
    'DNLL→DNHB': ['BA', 'ADH'],
    'DNHB→DNLL': ['ADH'],
    'UPHB→UPLL': ['ADH'],
}


def load_occupancy(stops, line: str) -> dict:
    """
    For a given line code, return dict:
      {station: sorted list of occupied minutes (0-1439)}
    """
    meta = LINES_META.get(line, {})
    direction = meta.get('direction', '')
    route_set = set(meta.get('route', []))
    occ = defaultdict(set)
    for s in stops:
        if s.get('line') != line: continue
        if s.get('direction') != direction: continue
        stn = s.get('station', '')
        if stn not in route_set: continue
        occ[stn].add(s['minutes'] % 1440)
    return {stn: sorted(times) for stn, times in occ.items()}


def check_departure(dep_min: int, route: list, offsets: dict,
                    occupancy: dict, min_headway: int) -> tuple:
    """
    Check if departure at dep_min (from route[0]) is feasible.
    Returns (min_gap_found, bottleneck_station) or (None, blocking_station).
    """
    worst_gap = 9999
    bottleneck = route[0]
    for stn in route:
        off = offsets.get(stn)
        if off is None: continue
        occ = occupancy.get(stn, [])
        if not occ: continue
        arr = (dep_min + off) % 1440
        pos = bisect_left(occ, arr)
        # Previous train time (wrapping midnight)
        prev_t = occ[pos - 1] if pos > 0 else occ[-1] - 1440
        # Next train time (wrapping midnight)
        next_t = occ[pos] if pos < len(occ) else occ[0] + 1440
        gap_before = arr - prev_t
        gap_after  = next_t - arr
        if gap_before < min_headway or gap_after < min_headway:
            return None, stn
        g = min(gap_before, gap_after)
        if g < worst_gap:
            worst_gap = g
            bottleneck = stn
    return worst_gap, bottleneck


def find_paths(stops: list, line: str, from_stn: str, to_stn: str,
               min_headway: int = 5, time_start: int = 0, time_end: int = 1440) -> list:
    """
    Find all available departure windows for a new train on `line`
    from from_stn to to_stn, with at least min_headway minutes clearance.

    Returns list of dicts:
      { dep_start, dep_end, window_mins, min_gap, bottleneck,
        key_times: {station: "HH:MM"} }
    """
    meta = LINES_META.get(line)
    if not meta:
        return []

    full_route = meta['route']
    offsets    = meta['offsets']

    # Trim route to from_stn → to_stn
    try:
        i0 = full_route.index(from_stn)
        i1 = full_route.index(to_stn)
    except ValueError:
        return []
    if i0 > i1:
        i0, i1 = i1, i0
    route = full_route[i0: i1 + 1]

    # Re-zero offsets to from_stn
    base_off = offsets.get(from_stn, 0)
    local_off = {s: offsets[s] - base_off for s in route if s in offsets}

    occupancy = load_occupancy(stops, line)

    # Scan
    feasible = []  # (dep_min, gap, bottleneck)
    for dep in range(time_start, min(time_end, 1440)):
        gap, btn = check_departure(dep, route, local_off, occupancy, min_headway)
        if gap is not None:
            feasible.append((dep, gap, btn))

    if not feasible:
        return []

    # Merge consecutive minutes into windows
    KEY_STNS = [route[0], route[len(route)//4], route[len(route)//2],
                route[3*len(route)//4], route[-1]]
    KEY_STNS = list(dict.fromkeys(KEY_STNS))  # deduplicate preserving order

    windows = []
    i = 0
    while i < len(feasible):
        s_dep, s_gap, s_btn = feasible[i]
        j = i
        min_gap_in_window = s_gap
        while j + 1 < len(feasible) and feasible[j+1][0] - feasible[j][0] == 1:
            j += 1
            min_gap_in_window = min(min_gap_in_window, feasible[j][1])

        e_dep = feasible[j][0]
        mid   = (s_dep + e_dep) // 2

        key_times = {}
        for stn in KEY_STNS:
            off = local_off.get(stn, 0)
            t   = (mid + off) % 1440
            key_times[stn] = f"{t // 60:02d}:{t % 60:02d}"

        # Classify by tightness
        if min_gap_in_window >= 10:
            classification = 'WIDE'
        elif min_gap_in_window >= 6:
            classification = 'MEDIUM'
        else:
            classification = 'TIGHT'

        windows.append({
            'dep_start':      s_dep,
            'dep_end':        e_dep,
            'dep_start_str':  f"{s_dep // 60:02d}:{s_dep % 60:02d}",
            'dep_end_str':    f"{e_dep // 60:02d}:{e_dep % 60:02d}",
            'window_mins':    e_dep - s_dep + 1,
            'min_gap':        min_gap_in_window,
            'classification': classification,
            'key_times':      key_times,
            'route':          route,
            'line':           line,
            'from_stn':       from_stn,
            'to_stn':         to_stn,
        })
        i = j + 1

    return windows


def suggest_multi_segment_path(stops: list, from_stn: str, to_stn: str,
                                 direction: str, train_type: str,
                                 min_headway: int = 5) -> list:
    """
    Suggest which line(s) to use for a new train from from_stn to to_stn.
    Returns list of segment dicts with recommended line and path windows.
    """
    from pages._path_finder import LINES_META, LINE_ENDPOINT_RULES
    
    all_stations = ['CCG','MEL','CYR','GTR','BCL','BCT','MX','PL','PBHD','DDR',
                    'MRU','MM','BA','BDTS','KHAR','STC','VLP','ADH',
                    'JOS','RMAR','GMN','MDD','KILE','BVI','DIC','MIRA',
                    'BYR','NIG','BSR','NSP','VR','VTN','SAH','KLV','PLG',
                    'UOI','BOR','VGN','DRD']
    stn_idx = {s: i for i, s in enumerate(all_stations)}

    # Determine primary line based on direction + type
    if direction == 'DOWN':
        primary = 'DNLL' if train_type == 'SLOW' else 'DNTL'
    else:
        primary = 'UPLL' if train_type == 'SLOW' else 'UPTL'

    windows = find_paths(stops, primary, from_stn, to_stn,
                         min_headway=min_headway)
    return [{
        'line': primary,
        'label': LINES_META[primary]['label'],
        'from_stn': from_stn,
        'to_stn': to_stn,
        'windows': windows,
    }]
