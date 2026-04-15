import streamlit as st
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from _utils import (
    _stops_mtime, _meta_mtime, load_stops, load_meta, get_trains_dict,
    STATIONS, STN_INDEX, LINES_DEF, CAT_COLORS, CARS_OPTIONS,
    cars_filter_label, fmt_min
)
import pandas as pd

# ──────────────────────────────────────────────────────────────────────────────
st.title("🔍 Trains Between Stations")
st.caption("Find all trains running between two stations with comprehensive filter options")

# ── Load data ─────────────────────────────────────────────────────────────────
stops = load_stops(_mtime=_stops_mtime())
meta  = load_meta(_mtime=_meta_mtime())

# Build {train: [stops sorted by minutes]} — use the shared cached helper
_raw_train_stops = get_trains_dict(_mtime=_stops_mtime())
# Sort each train's stops by minutes (get_trains_dict doesn't guarantee order)
train_stops = {tr: sorted(sl, key=lambda x: x["minutes"]) for tr, sl in _raw_train_stops.items()}

# ── Sidebar: Station selectors ────────────────────────────────────────────────
st.sidebar.title("🔍 Trains Between Stations")
st.sidebar.markdown("### 🚉 Stations")

# Internal state keys (NOT widget keys) so we can safely swap before render
if "_eb_from" not in st.session_state:
    st.session_state["_eb_from"] = "BA" if "BA" in STATIONS else STATIONS[0]
if "_eb_to" not in st.session_state:
    st.session_state["_eb_to"]   = "BVI" if "BVI" in STATIONS else STATIONS[min(5, len(STATIONS)-1)]

def _do_swap():
    st.session_state["_eb_from"], st.session_state["_eb_to"] = (
        st.session_state["_eb_to"], st.session_state["_eb_from"]
    )

def _sync_from(): st.session_state["_eb_from"] = st.session_state["_w_from"]
def _sync_to():   st.session_state["_eb_to"]   = st.session_state["_w_to"]

from_idx = STATIONS.index(st.session_state["_eb_from"]) if st.session_state["_eb_from"] in STATIONS else 0
to_idx   = STATIONS.index(st.session_state["_eb_to"])   if st.session_state["_eb_to"]   in STATIONS else 0

from_stn = st.sidebar.selectbox(
    "**FROM Station**", STATIONS, index=from_idx,
    key="_w_from", on_change=_sync_from
)
to_stn = st.sidebar.selectbox(
    "**TO Station**", STATIONS, index=to_idx,
    key="_w_to", on_change=_sync_to
)

st.sidebar.button("⇄ Swap", key="swap_btn", on_click=_do_swap, use_container_width=True)

st.sidebar.markdown("---")

# ── Sidebar: Time window ──────────────────────────────────────────────────────
st.sidebar.markdown("### 🕐 Time Window")
use_time = st.sidebar.toggle("Filter by departure time", value=False)
if use_time:
    t_from_str = st.sidebar.text_input("From time (HH:MM)", value="06:00")
    t_to_str   = st.sidebar.text_input("To time   (HH:MM)", value="23:59")
    try:
        hf, mf = map(int, t_from_str.split(":"))
        ht, mt = map(int, t_to_str.split(":"))
        t_from_min = hf * 60 + mf
        t_to_min   = ht * 60 + mt
    except:
        st.sidebar.error("Use HH:MM format")
        t_from_min, t_to_min = 0, 1439
else:
    t_from_min, t_to_min = 0, 1439

st.sidebar.markdown("---")

# ── Sidebar: Filters ──────────────────────────────────────────────────────────
st.sidebar.markdown("### 🎛️ Filters")

direction_f = st.sidebar.radio(
    "Direction",
    ["Auto (infer)", "DOWN", "UP", "Both"],
    index=0,
    horizontal=True,
)

type_opts = ["SLOW", "FAST", "M/E"]
type_filter = st.sidebar.multiselect(
    "Train Type",
    type_opts,
    default=type_opts,
    help="SLOW = slow suburban, FAST = fast suburban, M/E = Mail/Express"
)

cat_opts = list(CAT_COLORS.keys())
cat_filter = st.sidebar.multiselect(
    "Category",
    cat_opts,
    default=[c for c in cat_opts if c != "EMPTY"],
    format_func=lambda c: CAT_COLORS[c]["label"]
)

cars_filter = st.sidebar.multiselect(
    "Cars",
    CARS_OPTIONS,
    default=CARS_OPTIONS
)

# AC filter
ac_opts = ["AC", "Non-AC"]
ac_filter = st.sidebar.multiselect(
    "AC / Non-AC",
    ac_opts,
    default=ac_opts
)

# DRD filter
drd_filter = st.sidebar.multiselect(
    "DRD Branch",
    ["DRD", "Non-DRD"],
    default=["DRD", "Non-DRD"]
)

line_opts = sorted(LINES_DEF.keys())
line_filter = st.sidebar.multiselect(
    "Line (blank = all)",
    line_opts,
    default=[],
    format_func=lambda c: f"{c} — {LINES_DEF[c]['label']}"
)

st.sidebar.markdown("---")
sort_by = st.sidebar.selectbox(
    "Sort results by",
    ["Departure time", "Train number", "Duration (fastest first)", "Type"]
)
show_halts_only = st.sidebar.toggle(
    "Only trains that HALT at both stations\n(exclude pass-through)", value=False
)

# ──────────────────────────────────────────────────────────────────────────────
# ── Core logic ────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────

if from_stn == to_stn:
    st.warning("⚠️ Please select different FROM and TO stations.")
    st.stop()

from_idx = STN_INDEX.get(from_stn, -1)
to_idx   = STN_INDEX.get(to_stn,   -1)

# Infer intended direction from station order
if direction_f == "Auto (infer)":
    inferred_dir = "DOWN" if from_idx < to_idx else "UP"
elif direction_f == "Both":
    inferred_dir = None   # no direction filter
else:
    inferred_dir = direction_f

# Pre-build per-train metadata lookup
train_cars_cat = {
    tr: cars_filter_label(m.get("ac", ""), m.get("cars", ""))
    for tr, m in meta.items()
}

results = []

for train_no, tstops in train_stops.items():
    m = meta.get(train_no, {})

    # ── Meta-level filters ────────────────────────────────────────────────────
    tr_type = m.get("type", "")
    tr_cat  = m.get("train_cat", "LOCAL")
    tr_cars = train_cars_cat.get(train_no, "12 CAR")
    tr_ac   = m.get("ac", "")
    tr_drd  = m.get("drd", "")
    tr_line = m.get("line", "")
    tr_dir  = m.get("direction", "")

    if tr_type not in type_filter:
        continue
    if tr_cat not in cat_filter:
        continue
    if tr_cars not in cars_filter:
        continue
    ac_label = "AC" if tr_ac == "AC" else "Non-AC"
    if ac_label not in ac_filter:
        continue
    drd_label = "DRD" if tr_drd == "DRD" else "Non-DRD"
    if drd_label not in drd_filter:
        continue
    if line_filter and m.get("line", "") not in line_filter:
        continue
    if inferred_dir and tr_dir and tr_dir != inferred_dir:
        continue

    # ── Find FROM and TO stops in this train's stop list ─────────────────────
    from_stop = None
    to_stop   = None

    for s in tstops:
        if s["station"] == from_stn:
            if show_halts_only and s.get("stop_type") == "pass":
                continue
            if from_stop is None:
                from_stop = s
        if s["station"] == to_stn:
            if show_halts_only and s.get("stop_type") == "pass":
                continue
            if to_stop is None:
                to_stop = s

    if from_stop is None or to_stop is None:
        continue

    # Ensure sequence makes sense (FROM comes before TO in minutes)
    if from_stop["minutes"] >= to_stop["minutes"]:
        continue

    # Time window filter (on departure from FROM station)
    dep_min = from_stop["minutes"] % 1440
    if not (t_from_min <= dep_min <= t_to_min):
        continue

    duration_min = to_stop["minutes"] - from_stop["minutes"]

    results.append({
        "train":       train_no,
        "from_time":   from_stop["time"],
        "to_time":     to_stop["time"],
        "dep_min":     from_stop["minutes"],
        "arr_min":     to_stop["minutes"],
        "duration":    duration_min,
        "direction":   tr_dir,
        "type":        tr_type,
        "ac":          tr_ac,
        "drd":         tr_drd,
        "cars":        m.get("cars", ""),
        "cat":         tr_cat,
        "line":        tr_line,
        "from_stn_m":  m.get("from_stn", ""),
        "to_stn_m":    m.get("to_stn", ""),
        "set_no":      m.get("set_no", ""),
        "platform":    m.get("platform", ""),
        "link":        m.get("link", ""),
        "from_halt":   from_stop.get("stop_type", ""),
        "to_halt":     to_stop.get("stop_type", ""),
    })

# ── Sort ──────────────────────────────────────────────────────────────────────
if sort_by == "Departure time":
    results.sort(key=lambda r: r["dep_min"])
elif sort_by == "Train number":
    results.sort(key=lambda r: r["train"])
elif sort_by == "Duration (fastest first)":
    results.sort(key=lambda r: r["duration"])
elif sort_by == "Type":
    order = {"FAST": 0, "SLOW": 1, "M/E": 2}
    results.sort(key=lambda r: (order.get(r["type"], 9), r["dep_min"]))

# ──────────────────────────────────────────────────────────────────────────────
# ── Header summary ────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────

dir_arrow = "→" if (inferred_dir == "DOWN" or inferred_dir is None) else "←"
st.markdown(
    f"""
    <div style="background:linear-gradient(135deg,#1a1f3c,#0d1b2a);
                border:1px solid #2a3a5c;border-radius:12px;padding:20px 28px;margin-bottom:20px">
      <div style="font-size:28px;font-weight:800;color:#e8f0fe;letter-spacing:.5px">
        {from_stn} &nbsp;<span style="color:#7c9fff">{dir_arrow}</span>&nbsp; {to_stn}
      </div>
      <div style="font-size:13px;color:#8899bb;margin-top:4px">
        {inferred_dir or 'Both directions'} &nbsp;·&nbsp;
        {"⏰ " + t_from_str + " – " + t_to_str if use_time else "Full day"} &nbsp;·&nbsp;
        {', '.join(type_filter)} &nbsp;·&nbsp;
        {', '.join(cars_filter)}
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ── KPI metrics row ───────────────────────────────────────────────────────────
total = len(results)
slow_n  = sum(1 for r in results if r["type"] == "SLOW")
fast_n  = sum(1 for r in results if r["type"] == "FAST")
me_n    = sum(1 for r in results if r["type"] == "M/E")
ac_n    = sum(1 for r in results if r["ac"] == "AC")
avg_dur = int(sum(r["duration"] for r in results) / total) if total else 0
min_dur = min((r["duration"] for r in results), default=0)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("🚆 Total Trains",   str(total))
c2.metric("🐢 Slow",           str(slow_n))
c3.metric("⚡ Fast",           str(fast_n))
c4.metric("🚂 M/E",            str(me_n))
c5.metric("🔵 AC Trains",      str(ac_n))
c6.metric("⏱ Fastest (min)",   str(min_dur) if total else "—")

st.markdown("---")

if not results:
    st.warning(
        f"No trains found between **{from_stn}** and **{to_stn}** with the selected filters.\n\n"
        "Try relaxing the filters (Type, Cars, Category, or time window)."
    )
    st.stop()

# ── View toggle ───────────────────────────────────────────────────────────────
view_tab, table_tab = st.tabs(["🃏 Card View", "📋 Table View"])

# ── Helper: badge HTML ────────────────────────────────────────────────────────
def badge(text, bg, fg="#000"):
    return (f'<span style="background:{bg};color:{fg};padding:2px 7px;'
            f'border-radius:3px;font-size:11px;font-weight:700;margin-right:3px">{text}</span>')

TYPE_COLORS  = {"SLOW": "#90CAF9", "FAST": "#FFD54F", "M/E": "#FF8A65"}
DIR_COLORS   = {"DOWN": "#4CAF50", "UP": "#FF7043"}

# ──────────────────────────────────────────────────────────────────────────────
# ── Card View ─────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
with view_tab:
    st.markdown(
        f"<div style='color:#8899bb;font-size:13px;margin-bottom:12px'>"
        f"Showing <b style='color:#e8f0fe'>{total}</b> trains from "
        f"<b style='color:#7c9fff'>{from_stn}</b> to "
        f"<b style='color:#7c9fff'>{to_stn}</b></div>",
        unsafe_allow_html=True
    )

    for r in results:
        dir_col  = DIR_COLORS.get(r["direction"], "#aaa")
        type_col = TYPE_COLORS.get(r["type"], "#ccc")
        cat_info = CAT_COLORS.get(r["cat"], CAT_COLORS["LOCAL"])
        cat_col  = cat_info["fast"] if r["type"] == "FAST" else cat_info["slow"]

        ac_badge  = badge("AC", "#29B6F6")      if r["ac"]  == "AC"  else ""
        drd_badge = badge("DRD", "#FF7043")     if r["drd"] == "DRD" else ""
        pass_from = badge("PASS", "#555", "#aaa") if r["from_halt"] == "pass" else ""
        pass_to   = badge("PASS", "#555", "#aaa") if r["to_halt"]   == "pass" else ""

        dur_str = f"{r['duration']} min"
        nd_from = " ⁺¹" if r["dep_min"] >= 1440 else ""
        nd_to   = " ⁺¹" if r["arr_min"] >= 1440 else ""

        st.markdown(f"""
<div style="background:linear-gradient(135deg,#151a2d,#0f1520);
     border-left:4px solid {dir_col};border-radius:8px;
     padding:12px 18px;margin:5px 0;
     display:flex;align-items:center;gap:18px;flex-wrap:wrap;">

  <!-- Times -->
  <div style="min-width:130px">
    <div style="font-size:22px;font-weight:800;color:{dir_col}">
      {r['from_time']}{nd_from}
      <span style="font-size:14px;color:#556">→</span>
      {r['to_time']}{nd_to}
    </div>
    <div style="font-size:11px;color:#667;margin-top:2px">⏱ {dur_str}</div>
  </div>

  <!-- Badges -->
  <div style="min-width:180px">
    {badge(r['direction'], dir_col)}
    {badge(r['type'], type_col)}
    {badge(cat_info['label'], cat_col, '#000')}
    {ac_badge}{drd_badge}
  </div>

  <!-- Train info -->
  <div style="color:#dde;font-size:13px;min-width:160px">
    Train <b style="color:#7c9fff">{r['train']}</b>
    &nbsp;·&nbsp; {r['from_stn_m']} → {r['to_stn_m']}
  </div>

  <!-- Meta -->
  <div style="color:#667;font-size:11px;line-height:1.8">
    Set: {r['set_no']} &nbsp;·&nbsp; Cars: {r['cars']}
    &nbsp;·&nbsp; Plat: {r['platform']}
    &nbsp;·&nbsp; Link: {r['link']}
    {('&nbsp;·&nbsp; Line: ' + r['line']) if r['line'] else ''}
  </div>

  <!-- Halt badges -->
  <div style="font-size:11px;color:#556">
    {from_stn}: {pass_from or badge('HALT','#2e7d32','#c8e6c9')}
    &nbsp;
    {to_stn}: {pass_to or badge('HALT','#2e7d32','#c8e6c9')}
  </div>
</div>""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# ── Table View ────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
with table_tab:
    rows = []
    for r in results:
        rows.append({
            "Train No.":    r["train"],
            f"Dep ({from_stn})": r["from_time"],
            f"Arr ({to_stn})":   r["to_time"],
            "Dur (min)":    r["duration"],
            "Direction":    r["direction"],
            "Type":         r["type"],
            "Category":     CAT_COLORS.get(r["cat"], {}).get("label", r["cat"]),
            "AC":           "✅" if r["ac"] == "AC" else "",
            "DRD":          "✅" if r["drd"] == "DRD" else "",
            "Cars":         r["cars"],
            "Line":         r["line"],
            "Origin":       r["from_stn_m"],
            "Destination":  r["to_stn_m"],
            "Set No.":      r["set_no"],
            "Platform":     r["platform"],
            "Link":         r["link"],
            f"{from_stn} stop": r["from_halt"].upper() if r["from_halt"] else "HALT",
            f"{to_stn} stop":   r["to_halt"].upper()   if r["to_halt"]   else "HALT",
        })

    df = pd.DataFrame(rows)

    # Highlight fast trains
    def highlight_row(row):
        if row["Type"] == "FAST":
            return ["background-color:#1a1800;color:#FFD54F"] * len(row)
        elif row["Type"] == "M/E":
            return ["background-color:#1a0f00;color:#FF8A65"] * len(row)
        elif row.get("AC") == "✅":
            return ["background-color:#001a2a;color:#90CAF9"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(highlight_row, axis=1)

    st.dataframe(styled, use_container_width=True, height=min(60 + len(rows) * 36, 700))

    col_dl1, col_dl2 = st.columns(2)
    col_dl1.download_button(
        "⬇️ Download CSV",
        df.to_csv(index=False),
        f"trains_{from_stn}_to_{to_stn}.csv",
        "text/csv",
        use_container_width=True
    )
    col_dl2.download_button(
        "⬇️ Download JSON",
        json.dumps(results, indent=2),
        f"trains_{from_stn}_to_{to_stn}.json",
        "application/json",
        use_container_width=True
    )

# ── Footer summary ────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<div style='color:#556;font-size:12px;text-align:center'>"
    f"Data from <b>stops_data.json</b> + <b>train_meta.json</b> — "
    f"Total trains matched: <b style='color:#7c9fff'>{total}</b>"
    f"</div>",
    unsafe_allow_html=True
)
