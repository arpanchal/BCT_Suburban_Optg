import streamlit as st
import json
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _utils import _stops_mtime, _meta_mtime, load_stops, load_meta, STATIONS
from collections import defaultdict
import pandas as pd

# st.set_page_config(page_title="Set Working", layout="wide")
st.title("🔧 Set Working Sheet")
st.caption("Full day working for any set number — shows all trains operated by a set in sequence")

stops     = load_stops(_mtime=_stops_mtime())
meta      = load_meta(_mtime=_meta_mtime())

# Build set → trains mapping
set_trains = defaultdict(list)
for tr, m in meta.items():
    sn = m.get("set_no", "")
    if sn and sn not in ("", "nan", "None"):
        set_trains[sn].append(tr)

all_sets = sorted(set_trains.keys(), key=lambda x: x.zfill(10))

if not all_sets:
    st.warning("No set numbers found in data.")
    st.stop()

st.sidebar.title("🔧 Set Working")
sel_set = st.sidebar.selectbox("Set Number", all_sets)

trains_for_set = sorted(set_trains[sel_set])

# Per-train stop lookup
train_stops = defaultdict(list)
for s in stops:
    train_stops[s["train"]].append(s)

st.markdown(f"### Set **{sel_set}** — {len(trains_for_set)} train working(s)")

all_rows = []

for tr in trains_for_set:
    m   = meta.get(tr, {})
    pts = sorted(train_stops.get(tr, []), key=lambda x: x["minutes"])
    first = pts[0]  if pts else None
    last  = pts[-1] if pts else None

    direction = m.get("direction", "")
    typ       = m.get("type", "")
    ac        = m.get("ac", "")
    from_s    = m.get("from_stn", "—")
    to_s      = m.get("to_stn", "—")
    cars      = m.get("cars", "—")
    platform  = m.get("platform", "—")
    link_v    = m.get("link", "—")
    rev_as    = m.get("rev_as", "—")
    rev_set   = m.get("rev_set_no", "—")

    dir_col   = "#4CAF50" if direction == "DOWN" else "#FF7043" if direction == "UP" else "#90CAF9"
    type_col  = "#00E676" if typ == "FAST" else "#999999"
    border_col= dir_col
    ac_badge  = '<span style="background:#88ccff;color:#000;padding:2px 7px;border-radius:3px;font-size:11px;font-weight:700;margin-left:4px">AC</span>' if ac == "AC" else ""
    nd_first  = "⁺" if first and first["minutes"] >= 1440 else ""
    nd_last   = "⁺" if last  and last["minutes"]  >= 1440 else ""
    dep_info  = f'{first["time"]}{nd_first} ({first["station"]})' if first else "—"
    arr_info  = f'{last["time"]}{nd_last} ({last["station"]})'    if last  else "—"

    # Render each card via st.components.v1.html so HTML is never escaped
    card_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  body{{margin:0;padding:0;font-family:'Segoe UI',Arial,sans-serif;background:transparent;}}
  .card{{background:#1a1f2e;border-left:5px solid {border_col};border-radius:7px;
    padding:11px 16px;margin:2px 0;}}
  .row1{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:6px;}}
  .trno{{font-size:18px;font-weight:800;color:{dir_col};}}
  .badge{{padding:2px 8px;border-radius:3px;font-size:11px;font-weight:700;color:#000;}}
  .row2{{font-size:12px;color:#ccc;line-height:1.8;}}
  .row2 b{{color:#eee;}}
</style></head><body>
<div class="card">
  <div class="row1">
    <span class="trno">Train {tr}</span>
    <span class="badge" style="background:{dir_col}">{direction}</span>
    <span class="badge" style="background:{type_col}">{typ}</span>
    {ac_badge}
    <span style="color:#ddd;font-size:13px;font-weight:600">{from_s} &rarr; {to_s}</span>
    <span style="color:#999;font-size:11px">Cars: {cars} &nbsp;&middot;&nbsp; Plat: {platform} &nbsp;&middot;&nbsp; Link: {link_v}</span>
  </div>
  <div class="row2">
    <b>Dep:</b> {dep_info} &nbsp;&rarr;&nbsp; <b>Arr:</b> {arr_info}
    &nbsp;&nbsp;&nbsp; <b>Rev as:</b> {rev_as} &nbsp;&middot;&nbsp; <b>Rev set:</b> {rev_set}
  </div>
</div>
</body></html>"""

    st.components.v1.html(card_html, height=90, scrolling=False)

    for p in pts:
        all_rows.append({
            "Set":       sel_set,
            "Train":     tr,
            "Direction": direction,
            "Type":      typ,
            "AC":        ac,
            "Station":   p["station"],
            "Time":      p["time"] + ("⁺" if p["minutes"] >= 1440 else ""),
            "Stop Type": p.get("stop_type", "stop"),
            "From":      from_s,
            "To":        to_s,
            "Cars":      cars,
            "Platform":  platform,
            "Link":      link_v,
            "Rev As":    rev_as,
        })

st.markdown("---")
st.markdown("### Full Working — Printable Table")
if all_rows:
    df = pd.DataFrame(all_rows)
    st.dataframe(df, use_container_width=True, height=420)
    st.download_button(
        "⬇️ Download Set Working CSV",
        df.to_csv(index=False),
        f"set_working_{sel_set}.csv",
        "text/csv",
    )
