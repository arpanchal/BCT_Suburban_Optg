import streamlit as st
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _utils import _stops_mtime, _meta_mtime, load_stops, load_meta, STATIONS, CARS_OPTIONS, cars_filter_label
from collections import defaultdict
import pandas as pd

# st.set_page_config(page_title="Station Timetable Cards", layout="wide")
st.title("📋 Station Timetable Cards")
st.caption("Printable per-station timetables — one card per station for platform staff")

stops = load_stops(_mtime=_stops_mtime())
meta  = load_meta(_mtime=_meta_mtime())
train_cars_cat_stn = {tr: cars_filter_label(m.get("ac",""), m.get("cars","")) for tr, m in meta.items()}

st.sidebar.title("📋 Timetable Cards")
sel_stns   = st.sidebar.multiselect("Stations", STATIONS, default=["BA","ADH","CCG"])
direction  = st.sidebar.radio("Direction", ["Both","DOWN","UP"])
train_type = st.sidebar.multiselect("Train Type", ["SLOW","FAST"], default=["SLOW","FAST"])
cars_filter = st.sidebar.multiselect("Cars", CARS_OPTIONS, default=CARS_OPTIONS)
t_start    = st.sidebar.number_input("Start hour", 0, 24, 0, 1)
t_end      = st.sidebar.number_input("End hour",   1, 26, 24, 1)
t_min, t_max = int(t_start)*60, int(t_end)*60

if not sel_stns:
    st.warning("Select at least one station from the sidebar.")
    st.stop()

# Print stylesheet injected once
st.markdown("""
<style>
  @media print {
    [data-testid="stSidebar"], [data-testid="stToolbar"],
    header, footer, .stButton { display: none !important; }
    .station-card { page-break-after: always; }
  }
  .station-card {
    background: #fff;
    color: #111;
    border: 2px solid #333;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 14px 0;
    font-family: Arial, sans-serif;
  }
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 2px solid #333;
    padding-bottom: 8px;
    margin-bottom: 10px;
  }
  .card-title   { font-size: 22px; font-weight: 900; color: #1a1a1a; }
  .card-sub     { font-size: 11px; color: #555; margin-top: 2px; }
  .card-counts  { text-align: right; font-size: 12px; color: #555; }
  table.tt      { width: 100%; border-collapse: collapse; font-size: 11px; }
  table.tt th   { background: #333; color: #fff; padding: 5px 7px; text-align: center; }
  table.tt td   { padding: 4px 6px; border-bottom: 1px solid #ddd; text-align: center; }
  tr.row-dn     { background: #e8f5e9; }
  tr.row-up     { background: #fce4ec; }
  tr.row-other  { background: #f5f5f5; }
</style>
""", unsafe_allow_html=True)

for stn in sel_stns:
    stn_stops = [s for s in stops if s["station"] == stn
                 and train_cars_cat_stn.get(s["train"],"12 CAR") in cars_filter
                 and t_min <= s["minutes"] <= t_max]
    if direction != "Both":
        stn_stops = [s for s in stn_stops if s["direction"] == direction]
    stn_stops = [s for s in stn_stops
                 if not s["type"] or s["type"] in train_type]
    stn_stops.sort(key=lambda x: x["minutes"])

    if not stn_stops:
        st.info(f"No data for **{stn}** with current filters.")
        continue

    dn_ct = sum(1 for s in stn_stops if s["direction"] == "DOWN")
    up_ct = sum(1 for s in stn_stops if s["direction"] == "UP")

    # Build rows as plain dicts — no pandas styling involved
    rows = []
    for s in stn_stops:
        m   = meta.get(s["train"], {})
        nd  = "⁺" if s["minutes"] >= 1440 else ""
        arr = (s.get("arr_time","") + nd) if s.get("stop_type") == "dwell" else ""
        dep = (s.get("dep_time","") + nd) if s.get("stop_type") in ("dwell","dep") else ""
        rows.append({
            "dir_class": "row-dn" if s["direction"]=="DOWN" else "row-up" if s["direction"]=="UP" else "row-other",
            "Time":      s["time"] + nd,
            "ARR":       arr,
            "DEP":       dep,
            "Train":     s["train"],
            "Dir":       s["direction"],
            "Type":      s["type"],
            "AC":        "AC" if s["ac"] == "AC" else "",
            "From":      m.get("from_stn",""),
            "To":        m.get("to_stn",""),
            "Set":       m.get("set_no",""),
            "Cars":      m.get("cars",""),
            "Platform":  m.get("platform",""),
            "Link":      m.get("link",""),
            "Rev As":    m.get("rev_as",""),
        })

    # Build HTML table rows — iterate list of dicts directly, no .values() on Series
    col_keys = ["Time","ARR","DEP","Train","Dir","Type","AC","From","To",
                "Set","Cars","Platform","Link","Rev As"]
    header_html = "".join(f"<th>{c}</th>" for c in col_keys)
    body_html   = ""
    for r in rows:
        cells = "".join(f"<td>{r[c]}</td>" for c in col_keys)
        body_html += f'<tr class="{r["dir_class"]}">{cells}</tr>'

    card_html = f"""
<div class="station-card">
  <div class="card-header">
    <div>
      <div class="card-title">🚉 {stn}</div>
      <div class="card-sub">Mumbai Suburban Railway · 26 March
        · {direction} · {', '.join(train_type)}
        · {t_start:02d}:00 – {t_end if t_end < 24 else str(t_end-24)+':00⁺'}
      </div>
    </div>
    <div class="card-counts">
      ▼ DOWN: {dn_ct} trains<br>
      ▲ UP:   {up_ct} trains<br>
      Total:  {len(stn_stops)} services
    </div>
  </div>
  <table class="tt">
    <thead><tr>{header_html}</tr></thead>
    <tbody>{body_html}</tbody>
  </table>
</div>"""

    st.markdown(card_html, unsafe_allow_html=True)

    # CSV download per station
    df_dl = pd.DataFrame([{k: r[k] for k in col_keys} for r in rows])
    st.download_button(
        f"⬇️ {stn} — Download CSV",
        df_dl.to_csv(index=False),
        f"timetable_{stn}.csv",
        "text/csv",
        key=f"dl_{stn}",
    )

st.markdown("---")
st.markdown("**🖨️ To print:** Use **Ctrl+P** in your browser. Each station card prints on a separate page with white background.")
