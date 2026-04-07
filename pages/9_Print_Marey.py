import streamlit as st
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _utils import _stops_mtime, _meta_mtime, load_stops, load_meta, STATIONS, HALT_STNS, CAT_COLORS, LINES_DEF, CARS_OPTIONS, cars_filter_label
from _chart_builder import build_chart_html
from collections import defaultdict

st.set_page_config(page_title="Print Marey Chart", layout="wide")
st.title("🖨️ Print Marey Chart — White Background")
st.caption("Optimised for large/continuous paper. Ctrl+P → Save as PDF. SVG export available for vector editing.")

stops = load_stops(_mtime=_stops_mtime())
meta  = load_meta(_mtime=_meta_mtime())

st.sidebar.title("🖨️ Print Settings")
direction    = st.sidebar.radio("Direction", ["Both","DOWN Only","UP Only"])
train_type   = st.sidebar.multiselect("Train Type",  ["SLOW","FAST","M/E"], default=["SLOW","FAST","M/E"])
train_cats   = st.sidebar.multiselect("Category",    list(CAT_COLORS.keys()),
                                       default=["LOCAL","AC_LOCAL","DRD","MAIL","EXPRESS"])
cars_filter  = st.sidebar.multiselect("Cars",        CARS_OPTIONS, default=CARS_OPTIONS)

ALL_LINE_CODES = sorted(LINES_DEF.keys())
line_filter_raw = st.sidebar.multiselect(
    "Line (blank = all lines)",
    options=ALL_LINE_CODES,
    default=[],
    format_func=lambda c: f"{c} — {LINES_DEF[c]['label']}",
    help="Filter to stops on specific lines only. Multi-select allowed.",
)
line_filter = set(line_filter_raw) if line_filter_raw else None

st.sidebar.markdown("**Time Slices**")
t_start = st.sidebar.number_input("Start hour", 0, 24, 0, 1)
t_end   = st.sidebar.number_input("End hour (>24 = next day)", 1, 26, 24, 1)
if t_end <= t_start: t_end = t_start + 1
t_min, t_max = int(t_start)*60, int(t_end)*60

sel_stns     = st.sidebar.multiselect("Stations (blank = all)", STATIONS, default=[])
display_stns = sel_stns if sel_stns else STATIONS

st.sidebar.markdown("**Layout**")
cell_h        = st.sidebar.slider("Row height (px)",    12, 40, 18)
cell_w        = st.sidebar.slider("px per minute",       1,  6,  2)
show_labels   = st.sidebar.checkbox("Train numbers on lines", True)
label_min_gap = st.sidebar.slider("Min label gap (px)", 20, 200, 70)
show_markers  = st.sidebar.checkbox("Minute reference dots & ticks", True)

st.sidebar.markdown("---")
st.sidebar.markdown("**🔦 Highlight Train**")
highlight_train = st.sidebar.selectbox(
    "Select train to highlight",
    ["(none)"] + sorted(meta.keys()),
    index=0,
)
if highlight_train == "(none)": highlight_train = ""

train_cars_cat = {tr: cars_filter_label(m.get("ac",""), m.get("cars","")) for tr, m in meta.items()}

def filter_stops():
    out = []
    for s in stops:
        if direction == "DOWN Only" and s["direction"] != "DOWN": continue
        if direction == "UP Only"   and s["direction"] != "UP":   continue
        if s["type"] and s["type"] not in train_type: continue
        if s.get("train_cat","LOCAL") not in train_cats: continue
        if s["station"] not in display_stns: continue
        if train_cars_cat.get(s["train"],"12 CAR") not in cars_filter: continue
        if line_filter is not None and s.get("line","") not in line_filter: continue
        m  = s["minutes"];  dm = s.get("dep_minutes", m)
        if not (t_min <= m <= t_max or t_min <= dm <= t_max): continue
        out.append(s)
    return out

filtered = filter_stops()

def build_data(stops_sub):
    stn_idx = {s: i for i, s in enumerate(display_stns)}
    all_by_tr = defaultdict(list)
    dwl_by_tr = defaultdict(list)

    def sort_min(s):
        stp = s.get("stop_type","stop")
        if stp == "dwell": return s.get("arr_minutes", s["minutes"])
        if stp == "dep":   return s.get("dep_minutes",  s["minutes"])
        if stp == "arr":   return s.get("arr_minutes",  s["minutes"])
        return s["minutes"]

    def stop_coords(s, yi):
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
car15_trains = [tr for tr, m in meta.items() if cars_filter_label(m.get("ac",""), m.get("cars","")) == "15 CAR"]
car15_json = json.dumps(car15_trains)
cat_col_json   = json.dumps({c: {"slow": v["slow"], "fast": v["fast"]} for c, v in CAT_COLORS.items()})
cat_label_json = json.dumps({k: v["label"] for k, v in CAT_COLORS.items()})

def hlabel(h): return f"{h:02d}:00" if h < 24 else f"{h-24:02d}:00⁺"
hticks_json = json.dumps([{"m": h*60, "l": hlabel(h)} for h in range(int(t_start), int(t_end)+1)])

trains_shown = len(set(s["train"] for s in filtered))
line_info = ""
if line_filter:
    line_info = " · Lines: " + ", ".join(f"{c} ({LINES_DEF[c]['label']})" for c in sorted(line_filter))
st.info(f"**{trains_shown} trains** · **{len(display_stns)} stations** · "
        f"**{int(t_end-t_start)}h window** · Print mode ON (white background){line_info}")

if not filtered:
    st.warning("No stops match filters.")
else:
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
        print_mode=True,
        show_minute_markers=show_markers,
        car15_json=car15_json,
        highlight_train=highlight_train,
        chart_id="print",
    )
    st.components.v1.html(html, height=820, scrolling=False)

st.markdown("---")
st.markdown("""
**🖨️ Printing tips:**
- **Ctrl+P** → paper size **A0 / custom roll** → margins **None** → uncheck headers/footers
- For PDF: choose **Save as PDF** as the printer
- **Time slices**: print 04:00–12:00, 12:00–20:00, 20:00–26:00 for three sheets
- **⬇️ SVG** button = vector file openable in Inkscape / Illustrator for editing before printing
- **⬇️ PNG** button = raster image for quick sharing
""")
