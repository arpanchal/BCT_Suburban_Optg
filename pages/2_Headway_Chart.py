import streamlit as st
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _utils import _stops_mtime, _meta_mtime, load_stops, load_meta, STATIONS, LINES_DEF, CAT_COLORS, CARS_OPTIONS, cars_filter_label
from collections import defaultdict
import pandas as pd

st.set_page_config(page_title="Headway Chart", layout="wide")
st.title("📏 Headway Chart — Gap Between Consecutive Trains")

stops = load_stops(_mtime=_stops_mtime())
meta  = load_meta(_mtime=_meta_mtime())

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("📏 Headway Controls")
sel_stn   = st.sidebar.selectbox("Station", STATIONS, index=STATIONS.index("BA"))
direction = st.sidebar.radio("Direction", ["Both", "DOWN", "UP"])

st.sidebar.markdown("**Filters**")
train_types  = st.sidebar.multiselect("Train Type", ["SLOW","FAST","M/E"], default=["SLOW","FAST","M/E"])
train_cats   = st.sidebar.multiselect("Category",   list(CAT_COLORS.keys()),
                                       default=["LOCAL","AC_LOCAL","DRD","MAIL","EXPRESS"])
cars_filter  = st.sidebar.multiselect("Cars",        CARS_OPTIONS, default=CARS_OPTIONS)
line_opts    = sorted(LINES_DEF.keys())
line_filter  = st.sidebar.multiselect("Line (blank = all)", line_opts, default=[],
                                       format_func=lambda c: f"{c} — {LINES_DEF[c]['label']}")

st.sidebar.markdown("**Time Window**")
t_start = st.sidebar.number_input("Start hour", 0, 24, 4, 1)
t_end   = st.sidebar.number_input("End hour",   1, 26, 24, 1)
t_min, t_max = int(t_start)*60, int(t_end)*60

# ── Filter ────────────────────────────────────────────────────────────────────
train_cars_cat = {tr: cars_filter_label(m.get("ac",""), m.get("cars","")) for tr, m in meta.items()}
line_set = set(line_filter) if line_filter else None

stn_stops = []
for s in stops:
    if s["station"] != sel_stn: continue
    if not (t_min <= s["minutes"] <= t_max): continue
    if s["type"] and s["type"] not in train_types: continue
    if s.get("train_cat","LOCAL") not in train_cats: continue
    if train_cars_cat.get(s["train"],"12 CAR") not in cars_filter: continue
    if line_set and s.get("line","") not in line_set: continue
    if direction != "Both" and s["direction"] != direction: continue
    stn_stops.append(s)

stn_stops.sort(key=lambda x: x["minutes"])

headways = []
for i in range(1, len(stn_stops)):
    gap = stn_stops[i]["minutes"] - stn_stops[i-1]["minutes"]
    headways.append({
        "from_train": stn_stops[i-1]["train"],
        "to_train":   stn_stops[i]["train"],
        "from_time":  stn_stops[i-1]["time"],
        "to_time":    stn_stops[i]["time"],
        "gap_min":    gap,
        "direction":  stn_stops[i]["direction"],
        "type":       stn_stops[i]["type"],
        "category":   stn_stops[i].get("train_cat","LOCAL"),
        "line":       stn_stops[i].get("line",""),
    })

if not headways:
    st.warning("No data for this selection.")
    st.stop()

avg_gap = sum(h["gap_min"] for h in headways) / len(headways)
max_hw  = max(headways, key=lambda x: x["gap_min"])
min_hw  = min(headways, key=lambda x: x["gap_min"])

# Active filter summary
active = []
if line_filter: active.append(f"Line: {', '.join(line_filter)}")
if set(train_types) != {"SLOW","FAST","M/E"}: active.append(f"Type: {', '.join(train_types)}")
if cars_filter != CARS_OPTIONS: active.append(f"Cars: {', '.join(cars_filter)}")
if active:
    st.info("🔍 Active filters: " + " · ".join(active))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Trains at station", len(stn_stops))
c2.metric("Avg headway",       f"{avg_gap:.1f} min")
c3.metric("Max gap",           f"{max_hw['gap_min']} min", f"{max_hw['from_time']}–{max_hw['to_time']}")
c4.metric("Min gap",           f"{min_hw['gap_min']} min", f"{min_hw['from_time']}–{min_hw['to_time']}")

hw_json  = json.dumps(headways)
avg_json = round(avg_gap, 2)

html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body{{margin:0;background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;}}
  #toolbar{{padding:5px 10px;display:flex;gap:8px;align-items:center;}}
  #toolbar button{{background:#252840;color:#ccc;border:1px solid #3a3f60;
    border-radius:4px;padding:3px 9px;font-size:11px;cursor:pointer;}}
  #toolbar button:hover{{background:#3a4a70;}}
  .tooltip{{position:fixed;background:rgba(12,14,26,0.97);border:1px solid #445;
    border-radius:6px;padding:8px 12px;font-size:11px;color:#eee;
    pointer-events:none;display:none;z-index:999;line-height:1.7;}}
  @media print{{body{{background:#fff;}}#toolbar{{display:none;}}}}
</style>
</head><body>
<div id="toolbar">
  <span style="color:#aaa;font-size:11px">Headway at <b style="color:#eee">{sel_stn}</b> — {direction}</span>
  <button id="btn-svg">⬇️ SVG</button>
  <button id="btn-png">⬇️ PNG</button>
</div>
<svg id="chart"></svg>
<div class="tooltip" id="tip"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script>
const DATA    = {hw_json};
const AVG_GAP = {avg_json};
const M       = {{top:30, right:70, bottom:70, left:55}};
const W       = Math.min(window.innerWidth - 20, 1100) - M.left - M.right;
const H       = 300 - M.top - M.bottom;

const CAT_COL = {{
  'LOCAL':'#4CAF50','AC_LOCAL':'#29B6F6','DRD':'#FF7043',
  'MAIL':'#E65100','EXPRESS':'#FF4081','EMPTY':'#78909C'
}};

const svg = d3.select("#chart")
  .attr("width",  W + M.left + M.right)
  .attr("height", H + M.top  + M.bottom)
  .attr("xmlns", "http://www.w3.org/2000/svg");
const g = svg.append("g").attr("transform", `translate(${{M.left}},${{M.top}})`);
svg.insert("rect","g").attr("width","100%").attr("height","100%").attr("fill","#0f1117");

const xSc = d3.scaleBand().domain(DATA.map((_,i)=>i)).range([0,W]).padding(0.1);
const yMax = Math.max(d3.max(DATA, d=>d.gap_min)||30, 30);
const ySc  = d3.scaleLinear().domain([0, yMax]).range([H, 0]);

[3,5,10,15,20,30,45,60].filter(v=>v<=yMax).forEach(v=>{{
  g.append("line").attr("x1",0).attr("x2",W).attr("y1",ySc(v)).attr("y2",ySc(v))
   .attr("stroke", v===6?"#FF5722":"#222840")
   .attr("stroke-width", v===6?1.5:1)
   .attr("stroke-dasharray", v===6?"5,3":"3,3").attr("opacity",0.8);
  g.append("text").attr("x",-4).attr("y",ySc(v)+3).attr("text-anchor","end")
   .attr("fill", v===6?"#FF5722":"#667").attr("font-size",9).attr("font-family","Arial")
   .text(v+"m"+(v===6?" ⚠":""));
}});

// Avg line
g.append("line").attr("x1",0).attr("x2",W).attr("y1",ySc(AVG_GAP)).attr("y2",ySc(AVG_GAP))
 .attr("stroke","#FFD700").attr("stroke-width",1.5).attr("stroke-dasharray","6,3");
g.append("text").attr("x",W+4).attr("y",ySc(AVG_GAP)+4).attr("fill","#FFD700")
 .attr("font-size",9).attr("font-family","Arial").text("Avg "+AVG_GAP.toFixed(1)+"m");

const tip = d3.select("#tip");
g.selectAll("rect.bar").data(DATA).join("rect").attr("class","bar")
  .attr("x",      (_,i) => xSc(i))
  .attr("y",       d    => ySc(d.gap_min))
  .attr("width",   xSc.bandwidth())
  .attr("height",  d    => H - ySc(d.gap_min))
  .attr("fill",    d    => {{
    const base = CAT_COL[d.category] || "#4CAF50";
    if(d.gap_min < 4)  return "#E53935";
    if(d.gap_min > 20) return "#FF5722";
    return base;
  }})
  .attr("rx", 2).attr("opacity", 0.85)
  .on("mouseover", function(e, d) {{
    d3.select(this).attr("opacity", 1);
    tip.style("display","block")
       .html(`<b>Gap: ${{d.gap_min}} min</b><br>
              ${{d.from_time}} Train <b>${{d.from_train}}</b><br>
              → ${{d.to_time}} Train <b>${{d.to_train}}</b><br>
              ${{d.direction}} · ${{d.type}} · ${{d.category}}<br>
              Line: ${{d.line||"—"}}`)
       .style("left",(e.clientX+14)+"px").style("top",(e.clientY-10)+"px");
  }})
  .on("mousemove", e=>tip.style("left",(e.clientX+14)+"px").style("top",(e.clientY-10)+"px"))
  .on("mouseout",  function(){{d3.select(this).attr("opacity",0.85);tip.style("display","none");}});

g.selectAll("text.val").data(DATA).join("text").attr("class","val")
  .attr("x", (_,i)=>xSc(i)+xSc.bandwidth()/2).attr("y",d=>ySc(d.gap_min)-3)
  .attr("text-anchor","middle").attr("fill","#ccc")
  .attr("font-size",Math.max(6,Math.min(9,xSc.bandwidth()*0.6))).attr("font-family","Arial")
  .text(d=>xSc.bandwidth()>14?d.gap_min:"");

const nth = Math.max(1, Math.floor(DATA.length/18));
g.selectAll("text.xlbl").data(DATA.filter((_,i)=>i%nth===0)).join("text").attr("class","xlbl")
  .attr("x",(_,i)=>xSc(i*nth)+xSc.bandwidth()/2).attr("y",H+14)
  .attr("text-anchor","end").attr("fill","#778").attr("font-size",8).attr("font-family","Arial")
  .attr("transform",(_,i)=>`rotate(-45,${{xSc(i*nth)+xSc.bandwidth()/2}},${{H+14}})`)
  .text(d=>d.from_time);

g.append("text").attr("x",W/2).attr("y",H+58).attr("text-anchor","middle")
 .attr("fill","#778").attr("font-size",11).attr("font-family","Arial").text("Departure time →");
g.append("text").attr("transform","rotate(-90)").attr("x",-H/2).attr("y",-42)
 .attr("text-anchor","middle").attr("fill","#778").attr("font-size",11).attr("font-family","Arial")
 .text("Headway gap (minutes)");
g.append("text").attr("x",W/2).attr("y",-10).attr("text-anchor","middle")
 .attr("fill","#ddd").attr("font-size",13).attr("font-weight","bold").attr("font-family","Arial")
 .text("Headway at {sel_stn} — {direction}");

document.getElementById("btn-svg").onclick=()=>{{
  const s=new XMLSerializer().serializeToString(document.getElementById("chart"));
  const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([s],{{type:"image/svg+xml"}}));
  a.download="headway_{sel_stn}.svg";a.click();
}};
document.getElementById("btn-png").onclick=()=>{{
  const svgEl=document.getElementById("chart");
  const s=new XMLSerializer().serializeToString(svgEl);
  const c=document.createElement("canvas");c.width=svgEl.getAttribute("width");c.height=svgEl.getAttribute("height");
  const img=new Image();
  img.onload=()=>{{c.getContext("2d").drawImage(img,0,0);const a=document.createElement("a");
    a.href=c.toDataURL("image/png");a.download="headway_{sel_stn}.png";a.click();}};
  img.src="data:image/svg+xml;base64,"+btoa(unescape(encodeURIComponent(s)));
}};
</script></body></html>"""

st.components.v1.html(html, height=420)

st.markdown("### Headway Details")
table_rows = []
for h in headways:
    table_rows.append({
        "From Train": h["from_train"], "Departs": h["from_time"],
        "To Train":   h["to_train"],   "Arrives": h["to_time"],
        "Gap (min)":  h["gap_min"],    "Dir":     h["direction"],
        "Type":       h["type"],       "Category":h["category"],
        "Line":       h["line"],
        "Alert": ("⚠️ Long gap" if h["gap_min"]>20 else "🔴 Close" if h["gap_min"]<3 else "✅ OK"),
    })

df = pd.DataFrame(table_rows)
st.dataframe(df, use_container_width=True, height=320)
col1, col2 = st.columns(2)
col1.download_button("⬇️ Download CSV", df.to_csv(index=False), f"headway_{sel_stn}.csv", "text/csv")
