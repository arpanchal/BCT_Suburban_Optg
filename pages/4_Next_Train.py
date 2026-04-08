import streamlit as st
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _utils import _stops_mtime, _meta_mtime, load_stops, load_meta, STATIONS, CARS_OPTIONS, cars_filter_label, HALT_STNS
from collections import defaultdict

# st.set_page_config(page_title="Next Train", layout="wide")
st.title("⏱️ Next Train from Station")
st.caption("Type a time and station to see upcoming departures — useful for real-time staff queries")

stops = load_stops(_mtime=_stops_mtime())
meta  = load_meta(_mtime=_meta_mtime())

col1, col2, col3 = st.columns([2,2,1])
with col1:
    sel_stn = st.selectbox("Station", STATIONS, index=STATIONS.index("BA"))
with col2:
    query_time = st.text_input("From time (HH:MM)", value="08:00")
with col3:
    direction = st.radio("Direction", ["Both","DOWN","UP"], horizontal=True)

cars_filter = st.sidebar.multiselect("Cars", CARS_OPTIONS, default=CARS_OPTIONS)
n_trains = st.slider("Show next N trains", 5, 50, 15)

try:
    qh, qm = map(int, query_time.split(":"))
    q_min = qh * 60 + qm
except:
    st.error("Enter time as HH:MM"); st.stop()

# Get all stops at this station
train_cars_cat = {tr: cars_filter_label(m.get("ac",""), m.get("cars","")) for tr, m in meta.items()}
stn_stops = [s for s in stops if s["station"] == sel_stn and train_cars_cat.get(s["train"],"12 CAR") in cars_filter]
if direction != "Both":
    stn_stops = [s for s in stn_stops if s["direction"] == direction]

# Get stops from query time onwards (wrap around midnight)
upcoming = [s for s in stn_stops if s["minutes"] >= q_min]
upcoming.sort(key=lambda x: x["minutes"])
upcoming = upcoming[:n_trains]

if not upcoming:
    st.info(f"No more trains at {sel_stn} after {query_time}. Showing from start of day:")
    upcoming = sorted(stn_stops, key=lambda x: x["minutes"])[:n_trains]

st.markdown(f"### Upcoming trains at **{sel_stn}** from {query_time}")

# Build display cards
for s in upcoming:
    m = meta.get(s["train"], {})
    wait = s["minutes"] - q_min
    wait_str = f"+{wait} min" if wait >= 0 else "—"
    dir_col  = "#4CAF50" if s["direction"]=="DOWN" else "#FF7043"
    type_col = "#00E676" if s["type"]=="FAST" else "#aaaaaa"
    ac_badge = "🔵 AC" if s["ac"]=="AC" else ""
    nd_badge = " ⁺¹" if s["minutes"]>=1440 else ""

    st.markdown(f"""
<div style="background:#1a1f2e;border-left:4px solid {dir_col};border-radius:6px;
            padding:10px 16px;margin:4px 0;display:flex;align-items:center;gap:20px">
  <div style="font-size:22px;font-weight:800;color:{dir_col};min-width:70px">{s['time']}{nd_badge}</div>
  <div style="min-width:50px;color:#aaa;font-size:12px">{wait_str}</div>
  <div style="min-width:80px">
    <span style="background:{dir_col};color:#000;padding:2px 7px;border-radius:3px;font-size:11px;font-weight:700">{s['direction']}</span>
    &nbsp;<span style="background:{type_col};color:#000;padding:2px 7px;border-radius:3px;font-size:11px;font-weight:700">{s['type']}</span>
    &nbsp;{ac_badge}
  </div>
  <div style="color:#eee;font-size:13px;min-width:140px">
    Train <b>{s['train']}</b> &nbsp;·&nbsp; {m.get('from_stn','?')} → {m.get('to_stn','?')}
  </div>
  <div style="color:#aaa;font-size:11px">
    Set: {m.get('set_no','?')} &nbsp;·&nbsp; Cars: {m.get('cars','?')} &nbsp;·&nbsp;
    Plat: {m.get('platform','?')} &nbsp;·&nbsp; Link: {m.get('link','?')}
  </div>
</div>""", unsafe_allow_html=True)

# Also show departures table for easy printing
st.markdown("---")
st.markdown("### 🖨️ Printable Departure Board")
import pandas as pd
rows = []
for s in upcoming:
    m = meta.get(s["train"], {})
    rows.append({
        "Time": s["time"] + ("⁺" if s["minutes"]>=1440 else ""),
        "Train No.": s["train"],
        "Direction": s["direction"],
        "Type": s["type"],
        "AC": "AC" if s["ac"]=="AC" else "",
        "From": m.get("from_stn",""),
        "To":   m.get("to_stn",""),
        "Set":  m.get("set_no",""),
        "Cars": m.get("cars",""),
        "Platform": m.get("platform",""),
        "Link": m.get("link",""),
    })
df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, height=400)
c1,c2 = st.columns(2)
c1.download_button("⬇️ Download CSV", df.to_csv(index=False),
                    f"departures_{sel_stn}_{query_time.replace(':','')}.csv", "text/csv")
