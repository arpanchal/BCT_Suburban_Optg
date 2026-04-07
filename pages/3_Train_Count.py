import streamlit as st
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _utils import _stops_mtime, _meta_mtime, load_stops, load_meta, STATIONS, LINES_DEF, CAT_COLORS, CARS_OPTIONS, cars_filter_label
from collections import defaultdict
import pandas as pd

st.set_page_config(page_title="Train Count by Hour", layout="wide")
st.title("📈 Train Count by Hour")

stops = load_stops(_mtime=_stops_mtime())
meta  = load_meta(_mtime=_meta_mtime())

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("📈 Train Count")
sel_stn    = st.sidebar.selectbox("Station (ALL = full network)", ["ALL"] + STATIONS)
split_mode = st.sidebar.radio("Split by", ["Direction","Category","Type","Line","Combined"])

st.sidebar.markdown("**Filters**")
train_types  = st.sidebar.multiselect("Train Type",  ["SLOW","FAST","M/E"], default=["SLOW","FAST","M/E"])
train_cats   = st.sidebar.multiselect("Category",    list(CAT_COLORS.keys()),
                                       default=["LOCAL","AC_LOCAL","DRD","MAIL","EXPRESS"])
cars_filter  = st.sidebar.multiselect("Cars",        CARS_OPTIONS, default=CARS_OPTIONS)
line_opts    = sorted(LINES_DEF.keys())
line_filter  = st.sidebar.multiselect("Line (blank = all)", line_opts, default=[],
                                       format_func=lambda c: f"{c} — {LINES_DEF[c]['label']}")
direction_f  = st.sidebar.radio("Direction", ["Both","DOWN","UP"])

# ── Filter & count ────────────────────────────────────────────────────────────
train_cars_cat = {tr: cars_filter_label(m.get("ac",""), m.get("cars","")) for tr, m in meta.items()}
line_set = set(line_filter) if line_filter else None

hour_counts = defaultdict(lambda: defaultdict(int))
seen = set()

for s in stops:
    if sel_stn != "ALL" and s["station"] != sel_stn: continue
    if s["type"] and s["type"] not in train_types: continue
    if s.get("train_cat","LOCAL") not in train_cats: continue
    if train_cars_cat.get(s["train"],"12 CAR") not in cars_filter: continue
    if line_set and s.get("line","") not in line_set: continue
    if direction_f != "Both" and s["direction"] != direction_f: continue

    hr  = (s["minutes"] % 1440) // 60
    key = (s["train"], hr)
    if key in seen: continue
    seen.add(key)

    if split_mode == "Direction":
        cat = s["direction"] or "Unknown"
    elif split_mode == "Category":
        cat = CAT_COLORS.get(s.get("train_cat","LOCAL"),{}).get("label", s.get("train_cat","LOCAL"))
    elif split_mode == "Type":
        cat = s["type"] or "Unknown"
    elif split_mode == "Line":
        cat = s.get("line","") or "Unknown"
    else:
        cat = "All Trains"

    hour_counts[hr][cat] += 1

categories = sorted(set(cat for hd in hour_counts.values() for cat in hd))
hours = list(range(24))
data_by_cat = {cat: [hour_counts[h].get(cat, 0) for h in hours] for cat in categories}

if not categories:
    st.warning("No data for this selection.")
    st.stop()

# Active filter summary
active = []
if line_filter: active.append(f"Line: {', '.join(line_filter)}")
if set(train_types) != {"SLOW","FAST","M/E"}: active.append(f"Type: {', '.join(train_types)}")
if set(train_cats) != set(CAT_COLORS.keys()): active.append(f"Category: {', '.join(train_cats)}")
if cars_filter != CARS_OPTIONS: active.append(f"Cars: {', '.join(cars_filter)}")
if active: st.info("🔍 Active filters: " + " · ".join(active))

# ── Top-level Suburban vs Mail-Express summary ────────────────────────────────────────
all_trains_in_stops = set(s["train"] for s in stops)
total_uniq   = len(all_trains_in_stops)

# Count unique trains by type from meta (ground truth)
suburban_tr  = sum(1 for tr, m in meta.items() if m.get("type") in ("SLOW","FAST") and not tr.startswith("ETY"))
me_tr        = sum(1 for tr, m in meta.items() if m.get("type") == "M/E")
suburban_slow= sum(1 for tr, m in meta.items() if m.get("type") == "SLOW" and not tr.startswith("ETY"))
suburban_fast= sum(1 for tr, m in meta.items() if m.get("type") == "FAST" and not tr.startswith("ETY"))

st.markdown("#### Train Composition Summary")
sa, sb, sc, sd, se = st.columns(5)
sa.metric("🚆 Total Trains",     f"{len(meta):,}",     help="All trains in train_meta.json (from Excel Train Summary sheet)")
sb.metric("🚇 Suburban",         f"{suburban_tr:,}",   delta=f"SLOW: {suburban_slow:,}  |  FAST: {suburban_fast:,}",
          help="Suburban trains (SLOW + FAST) from Train Summary")
sc.metric("🚂 Mail / Express",   f"{me_tr:,}",         help="M/E trains from Train Summary")

# Filtered stops stats
total_trains = sum(sum(v.values()) for v in hour_counts.values())
peak_hr = max(hours, key=lambda h: sum(hour_counts[h].values())) if hour_counts else 0
sd.metric("Train-hours counted", f"{total_trains:,}")
se.metric("Peak hour", f"{peak_hr:02d}:00–{peak_hr+1:02d}:00",
          f"{sum(hour_counts[peak_hr].values())} trains")

st.markdown("---")
c1, c2, c3 = st.columns(3)
c1.metric("Total train-hours counted", f"{total_trains:,}")
c2.metric("Peak hour", f"{peak_hr:02d}:00–{peak_hr+1:02d}:00",
           f"{sum(hour_counts[peak_hr].values())} trains")
c3.metric("Categories shown", len(categories))

# Colour map
cat_colors_js = {
    "DOWN": "#4CAF50", "UP": "#FF7043",
    "SLOW": "#90CAF9", "FAST": "#FFD54F", "M/E": "#E65100",
    "Local": "#4CAF50", "AC Local": "#29B6F6", "DRD Branch": "#FF7043",
    "Mail/Express (M/E)": "#E65100", "Express": "#FF4081", "Empty": "#78909C",
    "UPLL": "#BF360C", "DNLL": "#2E7D32", "UPTL": "#AD1457", "DNTL": "#1565C0",
    "UPHB": "#6A1B9A", "DNHB": "#F57F17", "5L": "#00695C", "6L": "#4527A0",
    "All Trains": "#7C83FD", "Unknown": "#aaa",
}

html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  body{{margin:0;background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;}}
  .tooltip{{position:fixed;background:rgba(12,14,26,0.97);border:1px solid #445;
    border-radius:6px;padding:8px 12px;font-size:11px;color:#eee;pointer-events:none;display:none;z-index:999;line-height:1.7;}}
</style></head><body>
<svg id="chart"></svg>
<div class="tooltip" id="tip"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script>
const HOURS = {json.dumps(hours)};
const DATA  = {json.dumps(data_by_cat)};
const CATS  = {json.dumps(categories)};
const COLORS= {json.dumps(cat_colors_js)};
const PALETTE= ["#4CAF50","#29B6F6","#FF7043","#E65100","#FF4081","#FFD54F","#7C83FD","#78909C","#00BCD4","#AB47BC"];
const M     = {{top:30,right:140,bottom:55,left:55}};
const W     = 1100 - M.left - M.right;
const H     = 360  - M.top  - M.bottom;

const svg = d3.select("#chart").attr("width",W+M.left+M.right).attr("height",H+M.top+M.bottom);
const g   = svg.append("g").attr("transform",`translate(${{M.left}},${{M.top}})`);
svg.insert("rect","g").attr("width","100%").attr("height","100%").attr("fill","#0f1117");

const maxVal = Math.max(d3.max(CATS.flatMap(c=>DATA[c]||[])), 10);
const xSc = d3.scaleBand().domain(HOURS).range([0,W]).padding(0.18);
const ySc = d3.scaleLinear().domain([0,maxVal]).range([H,0]);

[10,20,30,40,50,60,80,100,120,150].filter(v=>v<=maxVal).forEach(v=>{{
  g.append("line").attr("x1",0).attr("x2",W).attr("y1",ySc(v)).attr("y2",ySc(v))
   .attr("stroke","#222840").attr("stroke-width",1).attr("stroke-dasharray","3,3");
  g.append("text").attr("x",-4).attr("y",ySc(v)+3).attr("text-anchor","end")
   .attr("fill","#667").attr("font-size",9).text(v);
}});

const tip = d3.select("#tip");
const bw  = xSc.bandwidth() / CATS.length;

CATS.forEach((cat,ci) => {{
  const col = COLORS[cat] || PALETTE[ci % PALETTE.length];
  const vals = DATA[cat]||[];
  HOURS.forEach((hr,hi) => {{
    const v=vals[hi]||0;
    if(v===0) return;
    const bx = xSc(hr) + ci*bw;
    g.append("rect").attr("x",bx).attr("y",ySc(v)).attr("width",bw*0.92)
     .attr("height",H-ySc(v)).attr("fill",col).attr("rx",1.5).attr("opacity",0.85)
     .on("mouseover",function(e){{
       d3.select(this).attr("opacity",1);
       tip.style("display","block")
          .html(`<b>${{String(hr).padStart(2,"0")}}:00–${{String(hr+1).padStart(2,"0")}}:00</b><br>${{cat}}: <b>${{v}} trains</b>`)
          .style("left",(e.clientX+14)+"px").style("top",(e.clientY-10)+"px");
     }})
     .on("mousemove",e=>tip.style("left",(e.clientX+14)+"px").style("top",(e.clientY-10)+"px"))
     .on("mouseout",function(){{d3.select(this).attr("opacity",0.85);tip.style("display","none");}});
  }});
}});

// X axis
g.append("g").attr("transform",`translate(0,${{H}})`)
 .call(d3.axisBottom(xSc).tickFormat(h=>`${{String(h).padStart(2,"0")}}:00`))
 .selectAll("text").attr("fill","#778").attr("font-size",9)
 .attr("transform","rotate(-45)").attr("text-anchor","end");
g.selectAll(".domain,.tick line").attr("stroke","#333");

g.append("text").attr("transform","rotate(-90)").attr("x",-H/2).attr("y",-42)
 .attr("text-anchor","middle").attr("fill","#778").attr("font-size",11).text("Train count");

// Legend
CATS.forEach((cat,i)=>{{
  const col=COLORS[cat]||PALETTE[i%PALETTE.length];
  const lx=W+15, ly=i*20;
  g.append("rect").attr("x",lx).attr("y",ly).attr("width",14).attr("height",10).attr("fill",col).attr("rx",2);
  g.append("text").attr("x",lx+18).attr("y",ly+9).attr("fill","#ccc").attr("font-size",10).text(cat);
}});

// Peak hour marker
const peakHr = HOURS.reduce((a,h)=>{{
  const s=CATS.reduce((t,c)=>(DATA[c]||[])[HOURS.indexOf(h)]+t,0);
  const sa=CATS.reduce((t,c)=>(DATA[c]||[])[HOURS.indexOf(a)]+t,0);
  return s>sa?h:a;
}}, HOURS[0]);
g.append("line").attr("x1",xSc(peakHr)+xSc.bandwidth()/2).attr("x2",xSc(peakHr)+xSc.bandwidth()/2)
 .attr("y1",0).attr("y2",H).attr("stroke","#FFD700").attr("stroke-width",1.5)
 .attr("stroke-dasharray","5,3").attr("opacity",0.6);
g.append("text").attr("x",xSc(peakHr)+xSc.bandwidth()/2).attr("y",-12)
 .attr("text-anchor","middle").attr("fill","#FFD700").attr("font-size",9)
 .text(`Peak ${{String(peakHr).padStart(2,"0")}}:00`);
</script></body></html>"""

st.components.v1.html(html, height=430)

# Summary table
st.markdown("### Hourly Summary")
rows = [{"Hour": f"{h:02d}:00", **{cat: data_by_cat[cat][h] for cat in categories}} for h in hours]
df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, height=300)
st.download_button("⬇️ Download CSV", df.to_csv(index=False), "train_count_by_hour.csv", "text/csv")
