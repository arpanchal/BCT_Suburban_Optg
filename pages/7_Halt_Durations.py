import streamlit as st
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _utils import _stops_mtime, _meta_mtime, load_stops, load_meta, HALT_STNS
import pandas as pd

# st.set_page_config(page_title="Halt Durations", layout="wide")
st.title("⏸️ Halt Durations — KLV / PLG / BOR / VGN")
st.caption("Dwell time at intermediate halt stations for crew planning and scheduling")

stops = load_stops(_mtime=_stops_mtime())
meta  = load_meta(_mtime=_meta_mtime())

sel_stn = st.sidebar.selectbox("Halt Station", sorted(HALT_STNS))
direction = st.sidebar.radio("Direction", ["Both","DOWN","UP"])
sort_by   = st.sidebar.radio("Sort by", ["Halt Duration","Arrival Time"])

dwell_stops = [s for s in stops
               if s["station"]==sel_stn and s.get("stop_type")=="dwell"]
if direction != "Both":
    dwell_stops = [s for s in dwell_stops if s["direction"]==direction]

rows = []
for s in dwell_stops:
    halt = s.get("dep_minutes",0) - s.get("arr_minutes",0)
    m    = meta.get(s["train"],{})
    rows.append({
        "Train No.":   s["train"],
        "Direction":   s["direction"],
        "Type":        s["type"],
        "AC":          "AC" if s["ac"]=="AC" else "",
        "ARR Time":    s.get("arr_time",""),
        "DEP Time":    s.get("dep_time",""),
        "Halt (min)":  halt,
        "From":        m.get("from_stn",""),
        "To":          m.get("to_stn",""),
        "Set No.":     m.get("set_no",""),
        "Rev As":      m.get("rev_as",""),
    })

if not rows:
    st.warning(f"No dwell data for {sel_stn} with current filters.")
    st.stop()

df = pd.DataFrame(rows)
if sort_by == "Halt Duration":
    df = df.sort_values("Halt (min)", ascending=False)
else:
    df = df.sort_values("ARR Time")

avg_halt = df["Halt (min)"].mean()
max_halt = df["Halt (min)"].max()
min_halt = df["Halt (min)"].min()

c1,c2,c3,c4 = st.columns(4)
c1.metric("Trains with dwell",  len(df))
c2.metric("Avg halt",  f"{avg_halt:.1f} min")
c3.metric("Max halt",  f"{max_halt} min")
c4.metric("Min halt",  f"{min_halt} min")

# Colour-coded table
def highlight_halt(val):
    if isinstance(val, (int,float)):
        if val >= 15: return "background:#7B1A00;color:white"
        if val >= 10: return "background:#BF360C;color:white"
        if val >= 5:  return "background:#4a3000;color:white"
    return ""

st.dataframe(df.style.applymap(highlight_halt, subset=["Halt (min)"]),
             use_container_width=True, height=500)

st.download_button("⬇️ Download CSV", df.to_csv(index=False),
                    f"halt_durations_{sel_stn}.csv", "text/csv")

# Bar chart
import json
halts_json = json.dumps([{"train":r["Train No."],"halt":r["Halt (min)"],"arr":r["ARR Time"]} for _,r in df.iterrows()])
html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{margin:0;background:#0f1117;font-family:'Segoe UI',Arial;}}</style></head><body>
<svg id="c"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const DATA={halts_json};
const M={{top:20,right:20,bottom:50,left:50}};
const W=900-M.left-M.right, H=220-M.top-M.bottom;
const svg=d3.select("#c").attr("width",W+M.left+M.right).attr("height",H+M.top+M.bottom);
const g=svg.append("g").attr("transform",`translate(${{M.left}},${{M.top}})`);
const xSc=d3.scaleBand().domain(DATA.map((_,i)=>i)).range([0,W]).padding(0.1);
const ySc=d3.scaleLinear().domain([0,d3.max(DATA,d=>d.halt)||10]).range([H,0]);
g.selectAll("rect").data(DATA).join("rect")
 .attr("x",(_,i)=>xSc(i)).attr("y",d=>ySc(d.halt)).attr("width",xSc.bandwidth())
 .attr("height",d=>H-ySc(d.halt))
 .attr("fill",d=>d.halt>=15?"#FF1744":d.halt>=10?"#FF7043":d.halt>=5?"#FFD54F":"#4CAF50")
 .attr("rx",2).attr("opacity",0.9);
g.append("g").attr("transform",`translate(0,${{H}})`).call(d3.axisBottom(xSc).tickFormat((_,i)=>DATA[i].arr||""))
 .selectAll("text").attr("fill","#778").attr("font-size",8).attr("transform","rotate(-45)").attr("text-anchor","end");
g.append("g").call(d3.axisLeft(ySc).ticks(4)).selectAll("text").attr("fill","#778").attr("font-size",9);
</script></body></html>"""
st.components.v1.html(html, height=250)
