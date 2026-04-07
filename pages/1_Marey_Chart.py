import streamlit as st
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _utils import _stops_mtime, _meta_mtime, load_stops, load_meta, STATIONS, HALT_STNS, CAT_COLORS, LINES_DEF, CARS_OPTIONS, cars_filter_label
from _chart_builder import build_chart_html
from collections import defaultdict, Counter

st.set_page_config(page_title="Marey Chart", layout="wide", initial_sidebar_state="expanded")
stops = load_stops(_mtime=_stops_mtime())
meta  = load_meta(_mtime=_meta_mtime())

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🗺️ Marey Chart")
chart_mode   = st.sidebar.radio("Direction", ["Both UP & DOWN","DOWN Only","UP Only"])
train_types  = st.sidebar.multiselect("Train Type",     ["SLOW","FAST","M/E"], default=["SLOW","FAST","M/E"])
train_cats   = st.sidebar.multiselect("Category",       list(CAT_COLORS.keys()),
                                       default=["LOCAL","AC_LOCAL","DRD","MAIL","EXPRESS"])
cars_filter  = st.sidebar.multiselect("Cars",           CARS_OPTIONS, default=CARS_OPTIONS)

# Line filter — "All Lines" means no line restriction
ALL_LINE_CODES = sorted(LINES_DEF.keys())
line_options   = ["All Lines"] + ALL_LINE_CODES
line_filter_raw = st.sidebar.multiselect(
    "Line (blank = all lines)",
    options=ALL_LINE_CODES,
    default=[],
    format_func=lambda c: f"{c} — {LINES_DEF[c]['label']}",
    help="Filter to stops on specific lines only. Multi-select allowed.",
)
line_filter = set(line_filter_raw) if line_filter_raw else None  # None = no filter

st.sidebar.markdown("**Time Window**")
st.sidebar.caption("End > 24 shows trains crossing midnight")
t_start = st.sidebar.number_input("Start hour", 0, 24, 0, 1)
t_end   = st.sidebar.number_input("End hour (>24 = next day)", 1, 26, 24, 1)
if t_end <= t_start: t_end = t_start + 1
t_min = int(t_start)*60;  t_max = int(t_end)*60

sel_stns     = st.sidebar.multiselect("Stations (blank = all)", STATIONS, default=[])
display_stns = sel_stns if sel_stns else STATIONS

st.sidebar.markdown("**Display**")
cell_h         = st.sidebar.slider("Row height (px)", 12, 48, 20)
cell_w         = st.sidebar.slider("px per minute",    1,  8,  2)
show_labels    = st.sidebar.checkbox("Train numbers on lines", True)
label_min_gap  = st.sidebar.slider("Min label gap (px)", 20, 200, 60)
show_markers   = st.sidebar.checkbox("Minute reference dots & ticks", True)
print_mode     = st.sidebar.checkbox("🖨️ Print mode (white bg)", False)

st.sidebar.markdown("---")
st.sidebar.markdown("**🔦 Highlight Train**")
all_train_nos  = sorted(meta.keys())
highlight_train = st.sidebar.selectbox(
    "Select train to highlight",
    ["(none)"] + all_train_nos,
    index=0,
    help="Selected train will blink with a glow on the chart"
)
if highlight_train == "(none)": highlight_train = ""

# ── Build cars lookup ─────────────────────────────────────────────────────────
train_cars_cat = {tr: cars_filter_label(m.get("ac",""), m.get("cars","")) for tr, m in meta.items()}

# ── Filter ────────────────────────────────────────────────────────────────────
def filter_stops():
    out = []
    for s in stops:
        if chart_mode == "DOWN Only" and s["direction"] != "DOWN": continue
        if chart_mode == "UP Only"   and s["direction"] != "UP":   continue
        if s["type"] and s["type"] not in train_types: continue  # M/E included
        if s.get("train_cat","LOCAL") not in train_cats: continue
        if s["station"] not in display_stns: continue
        if train_cars_cat.get(s["train"],"12 CAR") not in cars_filter: continue
        if line_filter is not None and s.get("line","") not in line_filter: continue
        m  = s["minutes"];  dm = s.get("dep_minutes", m)
        if not (t_min <= m <= t_max or t_min <= dm <= t_max): continue
        out.append(s)
    return out

filtered = filter_stops()

# ── Build compact JS data ─────────────────────────────────────────────────────
def build_data(stops_sub):
    stn_idx = {s: i for i, s in enumerate(display_stns)}
    all_by_tr = defaultdict(list)
    dwl_by_tr = defaultdict(list)

    def sort_min(s):
        """Minute used to sort stops in travel order."""
        stp = s.get("stop_type","stop")
        if stp == "dwell": return s.get("arr_minutes", s["minutes"])
        if stp == "dep":   return s.get("dep_minutes",  s["minutes"])
        if stp == "arr":   return s.get("arr_minutes",  s["minutes"])
        return s["minutes"]

    def stop_coords(s, yi):
        """Return list of [x,y,time] for this stop.
        Dwell → TWO points (arr + dep) creating horizontal segment on polyline.
        All others → ONE point."""
        stp = s.get("stop_type","stop")
        if stp == "dwell":
            return [
                [s.get("arr_minutes", s["minutes"]), yi, s.get("arr_time", s["time"])],
                [s.get("dep_minutes", s["minutes"]), yi, s.get("dep_time", s["time"])],
            ]
        elif stp == "dep":
            return [[s.get("dep_minutes", s["minutes"]), yi, s.get("dep_time", s["time"])]]
        elif stp == "arr":
            return [[s.get("arr_minutes", s["minutes"]), yi, s.get("arr_time", s["time"])]]
        else:
            return [[s["minutes"], yi, s["time"]]]

    for s in stops_sub:
        if s["station"] not in stn_idx: continue
        stp = s.get("stop_type","stop")
        all_by_tr[s["train"]].append(s)
        if stp in ("dwell","dep","arr","pass"):
            dwl_by_tr[s["train"]].append(s)

    # Compact: [train, dir, type, cat, ac, from, to, [[x,y,time], ...]]
    # Dwell stops produce TWO coords → horizontal segment on the polyline
    lines = []
    for tr in sorted(all_by_tr):
        pts = sorted(all_by_tr[tr], key=sort_min)
        if not pts: continue
        m0 = pts[0]
        coords = []
        for p in pts:
            coords.extend(stop_coords(p, stn_idx[p["station"]]))
        lines.append([tr, m0["direction"], m0["type"],
                      m0.get("train_cat","LOCAL"), m0["ac"],
                      m0["from_stn"], m0["to_stn"], coords])

    # Compact dwell: [tr, y, dir, type, stp, x1, x2, at, dt, cat]
    dwells = []
    for tr, dpts in dwl_by_tr.items():
        for s in dpts:
            if s["station"] not in stn_idx: continue
            yi  = stn_idx[s["station"]]
            stp = s.get("stop_type","pass")
            x1  = s.get("arr_minutes", s.get("dep_minutes", s["minutes"]))
            x2  = s.get("dep_minutes", x1)
            dwells.append([tr, yi, s["direction"], s["type"], stp, x1, x2,
                           s.get("arr_time",""), s.get("dep_time",""),
                           s.get("train_cat","LOCAL")])
    return json.dumps(lines), json.dumps(dwells)

lines_json, dwells_json = build_data(filtered)
lines_kb = len(lines_json)/1024

# Build 15-car train set
car15_trains = [tr for tr, m in meta.items() if cars_filter_label(m.get("ac",""), m.get("cars","")) == "15 CAR"]
car15_json = json.dumps(car15_trains)

# Build category colour & label JSON
cat_col_json   = json.dumps({c: {"slow": v["slow"], "fast": v["fast"]} for c, v in CAT_COLORS.items()})
cat_label_json = json.dumps({k: v["label"] for k, v in CAT_COLORS.items()})

def hlabel(h): return f"{h:02d}:00" if h < 24 else f"{h-24:02d}:00⁺"
hticks_json = json.dumps([{"m": h*60, "l": hlabel(h)} for h in range(int(t_start), int(t_end)+1)])

# ── Page layout ───────────────────────────────────────────────────────────────
st.title("🗺️ Marey Chart — Station × Time")
trains_shown = len(set(s["train"] for s in filtered))
overnight    = sorted(set(s["train"] for s in filtered if s["minutes"] >= 1440))

# Count unique trains per category (not stops)
uniq_trains = {}
for s in filtered:
    tr = s["train"]
    if tr not in uniq_trains:
        uniq_trains[tr] = {"cat": s.get("train_cat", "LOCAL"), "type": s.get("type", "SLOW")}

uniq_cat   = Counter(v["cat"]  for v in uniq_trains.values())
uniq_type  = Counter(v["type"] for v in uniq_trains.values())

suburban_count = uniq_type.get("SLOW", 0) + uniq_type.get("FAST", 0)
me_count       = uniq_type.get("M/E", 0)

c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("Stops",         f"{len(filtered):,}")
c2.metric("Trains",        f"{trains_shown:,}")
c3.metric("Suburban",      f"{suburban_count:,}")
c4.metric("Mail/Express",  f"{me_count:,}")
c5.metric("DOWN",          f"{sum(1 for s in filtered if s['direction']=='DOWN'):,}")
c6.metric("UP",            f"{sum(1 for s in filtered if s['direction']=='UP'):,}")

# Category legend with unique train counts
pills = " &nbsp;·&nbsp; ".join(
    f'<span style="color:{CAT_COLORS[c]["slow"]};font-weight:700">{CAT_COLORS[c]["label"]}: {n:,}</span>'
    for c, n in uniq_cat.most_common() if c in CAT_COLORS
)
if pills:
    st.markdown(pills, unsafe_allow_html=True)

if not filtered:
    st.warning("No stops match filters. Widen time window or adjust filters.")
else:
    if line_filter:
        line_labels = " + ".join(f"**{c}** ({LINES_DEF[c]['label']})" for c in sorted(line_filter))
        st.info(f"🛤️ Line filter active: {line_labels} — showing only stops on selected line(s)")
    if overnight:
        st.info(f"🌙 {len(overnight)} overnight trains: {', '.join(overnight[:15])}{'…' if len(overnight)>15 else ''}")

    html = build_chart_html(
        lines_json=lines_json,
        dwells_json=dwells_json,
        conflicts_json="[]",
        stns_json=json.dumps(display_stns),
        halt_json=json.dumps(list(HALT_STNS)),
        hticks_json=hticks_json,
        cat_col_json=cat_col_json,
        cat_label_json=cat_label_json,
        t_min=t_min, t_max=t_max,
        cell_h=cell_h, cell_w=cell_w,
        show_labels=show_labels,
        label_min_gap=label_min_gap,
        print_mode=print_mode,
        show_minute_markers=show_markers,
        car15_json=car15_json,
        highlight_train=highlight_train,
        chart_id="marey",
    )
    st.components.v1.html(html, height=780, scrolling=False)
