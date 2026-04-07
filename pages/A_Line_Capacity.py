import streamlit as st
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _utils import _stops_mtime, _meta_mtime, load_stops, load_meta, STATIONS, HALT_STNS, CAT_COLORS, LINES_DEF, CARS_OPTIONS, cars_filter_label
from _chart_builder import build_chart_html
from collections import defaultdict
import pandas as pd

st.set_page_config(page_title="Line Capacity", layout="wide")
st.title("🛤️ Line Capacity Chart")
st.caption("Per-line Marey chart. Red zones = headway < threshold. "
           "Hover conflicts for details. Tag Mail/Express in 🏷️ Category Editor.")

stops = load_stops(_mtime=_stops_mtime())
meta  = load_meta(_mtime=_meta_mtime())

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🛤️ Line Capacity")

LINE_OPTIONS = {v["label"]: k for k, v in LINES_DEF.items()}
sel_line_label = st.sidebar.selectbox("Select Line", list(LINE_OPTIONS.keys()))
LINE_CODE = LINE_OPTIONS[sel_line_label]

train_cats   = st.sidebar.multiselect("Category",
                   list(CAT_COLORS.keys()),
                   default=["LOCAL","AC_LOCAL","DRD","MAIL","EXPRESS"])
cars_filter  = st.sidebar.multiselect("Cars", CARS_OPTIONS, default=CARS_OPTIONS)
train_types  = st.sidebar.multiselect("Train Type", ["SLOW","FAST","M/E"], default=["SLOW","FAST","M/E"])

t_start = st.sidebar.number_input("Start hour", 0, 24, 4, 1)
t_end   = st.sidebar.number_input("End hour (>24 = next day)", 1, 26, 24, 1)
if t_end <= t_start: t_end = t_start + 1
t_min = int(t_start)*60;  t_max = int(t_end)*60

CONFLICT_GAP = st.sidebar.slider("Conflict threshold (min)", 2, 15, 3)

sel_stns     = st.sidebar.multiselect("Stations (blank = all)", STATIONS, default=[])
display_stns = sel_stns if sel_stns else STATIONS

cell_h        = st.sidebar.slider("Row height (px)", 12, 48, 22)
cell_w        = st.sidebar.slider("px per minute",    1,  8,  2)
show_labels   = st.sidebar.checkbox("Train numbers", True)
label_min_gap = st.sidebar.slider("Min label gap (px)", 20, 200, 55)
show_markers  = st.sidebar.checkbox("Minute reference dots & ticks", True)
print_mode    = st.sidebar.checkbox("🖨️ Print mode (white bg)", False)

train_cars_cat = {tr: cars_filter_label(m.get("ac",""), m.get("cars","")) for tr, m in meta.items()}

# ── Filter ────────────────────────────────────────────────────────────────────
def filter_for_line():
    out = []
    for s in stops:
        if s.get("line") != LINE_CODE: continue
        if s.get("train_cat","LOCAL") not in train_cats: continue
        if s["station"] not in display_stns: continue
        if s["type"] and s["type"] not in train_types: continue
        if train_cars_cat.get(s["train"],"12 CAR") not in cars_filter: continue
        m  = s["minutes"];  dm = s.get("dep_minutes", m)
        if not (t_min <= m <= t_max or t_min <= dm <= t_max): continue
        out.append(s)
    return out

filtered = filter_for_line()

# ── Conflict detection ────────────────────────────────────────────────────────
stn_trains = defaultdict(list)
for s in filtered:
    if s.get("stop_type","stop") == "stop":
        stn_trains[s["station"]].append(s)

conflicts = []
for stn, slist in stn_trains.items():
    slist.sort(key=lambda x: x["minutes"])
    for i in range(1, len(slist)):
        gap = slist[i]["minutes"] - slist[i-1]["minutes"]
        if gap < CONFLICT_GAP:
            conflicts.append({
                "Station":   stn,
                "Train 1":   slist[i-1]["train"],
                "Time 1":    slist[i-1]["time"],
                "Cat 1":     slist[i-1].get("train_cat","LOCAL"),
                "Train 2":   slist[i]["train"],
                "Time 2":    slist[i]["time"],
                "Cat 2":     slist[i].get("train_cat","LOCAL"),
                "Gap (min)": gap,
            })

# ── Build data ────────────────────────────────────────────────────────────────
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

    # Conflict marks for chart overlay
    conflict_marks = []
    for c in conflicts:
        si = stn_idx.get(c["Station"])
        if si is None: continue
        t1 = next((s["minutes"] for s in filtered
                   if s["train"]==c["Train 1"] and s["station"]==c["Station"]), None)
        t2 = next((s["minutes"] for s in filtered
                   if s["train"]==c["Train 2"] and s["station"]==c["Station"]), None)
        if t1 and t2:
            conflict_marks.append({
                "y": si, "x1": t1, "x2": t2, "gap": c["Gap (min)"],
                "tr1": c["Train 1"], "tr2": c["Train 2"],
                "time1": c["Time 1"], "time2": c["Time 2"],
            })
    return json.dumps(lines), json.dumps(dwells), json.dumps(conflict_marks)

lines_json, dwells_json, conflicts_json = build_data(filtered)
cat_col_json   = json.dumps({c: {"slow": v["slow"], "fast": v["fast"]} for c, v in CAT_COLORS.items()})
cat_label_json = json.dumps({k: v["label"] for k, v in CAT_COLORS.items()})

def hlabel(h): return f"{h:02d}:00" if h < 24 else f"{h-24:02d}:00⁺"
hticks_json = json.dumps([{"m": h*60, "l": hlabel(h)} for h in range(int(t_start), int(t_end)+1)])

line_color = LINES_DEF.get(LINE_CODE, {}).get("color","#aaa")

# ── Page layout ───────────────────────────────────────────────────────────────
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Line",           sel_line_label)
c2.metric("Trains on line", len(set(s["train"] for s in filtered)))
c3.metric("Stops",          f"{len(filtered):,}")
c4.metric("Conflicts",      len(conflicts),
           delta=f"< {CONFLICT_GAP} min", delta_color="inverse")
busy = max(stn_trains, key=lambda s: len(stn_trains[s])) if stn_trains else "—"
c5.metric("Busiest station", busy, f"{len(stn_trains.get(busy,[]))} trains")

if not filtered:
    st.warning(f"No trains on {sel_line_label} with current filters. "
               "Use 🏷️ Category Editor to assign trains to this line.")
else:
    html = build_chart_html(
        lines_json=lines_json,
        dwells_json=dwells_json,
        conflicts_json=conflicts_json,
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
        conflict_gap=CONFLICT_GAP,
        show_minute_markers=show_markers,
        chart_title=sel_line_label,
        chart_id="linecap",
    )
    st.components.v1.html(html, height=760, scrolling=False)

# ── Conflict & Margin tables ──────────────────────────────────────────────────
st.markdown("---")
col1, col2 = st.columns([2,1])
with col1:
    st.markdown(f"### 🔴 Conflicts on {sel_line_label} (gap < {CONFLICT_GAP} min)")
    if conflicts:
        df_c = pd.DataFrame(conflicts).sort_values("Gap (min)")
        st.dataframe(df_c, use_container_width=True, height=300)
        st.download_button("⬇️ Conflict CSV", df_c.to_csv(index=False),
                           f"conflicts_{LINE_CODE}.csv", "text/csv")
    else:
        st.success(f"✅ No conflicts — all headways ≥ {CONFLICT_GAP} min")

with col2:
    st.markdown("### 📊 Margin Analysis")
    if stn_trains:
        margin_rows = []
        for stn, slist in sorted(stn_trains.items(),
                                  key=lambda x: STATIONS.index(x[0]) if x[0] in STATIONS else 99):
            slist.sort(key=lambda x: x["minutes"])
            gaps = [slist[i]["minutes"]-slist[i-1]["minutes"] for i in range(1,len(slist))]
            if gaps:
                margin_rows.append({
                    "Station":  stn,
                    "Trains":   len(slist),
                    "Min gap":  min(gaps),
                    "Avg gap":  round(sum(gaps)/len(gaps),1),
                    "< 3 min":  sum(1 for g in gaps if g < 3),
                    "3–10 min": sum(1 for g in gaps if 3<=g<10),
                    "> 10 min": sum(1 for g in gaps if g >= 10),
                })
        df_m = pd.DataFrame(margin_rows)
        st.dataframe(df_m, use_container_width=True, height=300)
        st.download_button("⬇️ Margin CSV", df_m.to_csv(index=False),
                           f"margin_{LINE_CODE}.csv", "text/csv")
