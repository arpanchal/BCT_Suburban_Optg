import streamlit as st
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _utils import _stops_mtime, _meta_mtime, load_stops, load_meta, STATIONS
from collections import defaultdict
import pandas as pd

# st.set_page_config(page_title="Reversal Summary", layout="wide")
st.title("🔄 Reversal Summary")
st.caption("Which trains reverse where — helps crew plan handovers and platform allocation")

meta = load_meta(_mtime=_meta_mtime())

# Group by reversal station
rev_groups = defaultdict(list)
for tr, m in meta.items():
    rev_as = m.get("rev_as","")
    to_stn = m.get("to_stn","")
    if rev_as and rev_as != "nan":
        rev_groups[to_stn].append({
            "train": tr,
            "rev_as": rev_as,
            "rev_set_no": m.get("rev_set_no",""),
            "direction": m.get("direction",""),
            "type": m.get("type",""),
            "ac": m.get("ac",""),
            "from_stn": m.get("from_stn",""),
            "to_stn": to_stn,
            "dep_time": m.get("dep_time",""),
            "last_arr": m.get("last_arr",""),
            "set_no": m.get("set_no",""),
            "link": m.get("link",""),
            "platform": m.get("platform",""),
        })

sel_stn = st.sidebar.selectbox("Filter by reversal station", ["ALL"] + sorted(rev_groups.keys()))
direction = st.sidebar.radio("Direction", ["Both","DOWN","UP"])

rows = []
targets = rev_groups.keys() if sel_stn=="ALL" else [sel_stn]
for stn in sorted(targets):
    entries = rev_groups[stn]
    if direction != "Both":
        entries = [e for e in entries if e["direction"]==direction]
    entries.sort(key=lambda x: x["last_arr"] or "")
    for e in entries:
        rows.append({
            "Reversal Stn": stn,
            "Train No.": e["train"],
            "Rev As": e["rev_as"],
            "Set No.": e["set_no"],
            "Rev Set": e["rev_set_no"],
            "Direction": e["direction"],
            "Type": e["type"],
            "AC": "AC" if e["ac"]=="AC" else "",
            "From": e["from_stn"],
            "To": e["to_stn"],
            "Arrives": e["last_arr"],
            "Departs": e["dep_time"],
            "Platform": e["platform"],
            "Link": e["link"],
        })

c1,c2,c3 = st.columns(3)
c1.metric("Reversal stations", len(rev_groups))
c2.metric("Total reversals", len(rows))
c3.metric("Shown", len(rows))

if rows:
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, height=500)
    st.download_button("⬇️ Download Reversal CSV", df.to_csv(index=False),
                        "reversal_summary.csv", "text/csv")
