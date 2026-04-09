import streamlit as st
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))

from _utils import load_stops, load_meta, STATIONS, LINES_DEF, CAT_COLORS
from _path_finder_ import (LINES_META, LINE_ENDPOINT_RULES, CROSSOVERS,
                           find_paths, load_occupancy, find_multi_line_paths, check_departure)
from collections import defaultdict
import pandas as pd

# st.set_page_config(page_title="Path Finder", layout="wide")
st.title("🔍 Path Finder — Available Slots for New Trains")
st.caption(
    "Scan existing timetable to find time windows where a new train can be "
    "introduced without conflicting with existing services. "
    "Minimum headway is checked at every station along the route."
)

stops = load_stops()
meta  = load_meta()

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Inputs
# ══════════════════════════════════════════════════════════════════════════════
st.sidebar.title("🔍 Path Finder")

search_mode = st.sidebar.radio("Search Mode", ["Single Line", "Multi-Line (Routing)"])

st.sidebar.markdown("### New Train Parameters")
direction  = st.sidebar.radio("Direction", ["DOWN", "UP"])
train_type = st.sidebar.radio("Train Type", ["SLOW", "FAST", "M/E"])

sel_line = None
if search_mode == "Single Line":
    # Line options based on direction
    if direction == "DOWN":
        line_choices = ["DNLL — Down Local Line", "DNTL — Down Through Line",
                        "DNHB — Down Harbour Branch"]
    else:
        line_choices = ["UPLL — Up Local Line", "UPTL — Up Through Line",
                        "UPHB — Up Harbour Branch"]
    
    sel_line_display = st.sidebar.selectbox("Line", line_choices)
    sel_line = sel_line_display.split(" — ")[0]
    line_meta  = LINES_META.get(sel_line, {})
    line_route = line_meta.get("route", [])
    
    if line_route:
        from_stn = st.sidebar.selectbox("From Station", line_route, index=0)
        to_stns  = [s for s in line_route if line_route.index(s) > line_route.index(from_stn)]
        if to_stns:
            to_stn = st.sidebar.selectbox("To Station", to_stns, index=len(to_stns)-1)
        else:
            st.sidebar.warning("Select a different From station.")
            st.stop()
    else:
        st.sidebar.error("Line route not configured.")
        st.stop()
else:
    # Multi-Line Mode
    valid_stns = []
    # Identify stations that exist on ANY line for this direction
    for k, v in LINES_META.items():
        if v.get('direction') == direction:
            valid_stns.extend(v.get('route', []))
    valid_stns = sorted(list(set(valid_stns)), key=lambda s: STATIONS.index(s))
    
    # Restrict ordering geographically
    if direction == "UP":
        valid_stns = valid_stns[::-1]
        
    from_stn = st.sidebar.selectbox("From Station (Any Line)", valid_stns, index=0)
    to_stns = [s for s in valid_stns if valid_stns.index(s) > valid_stns.index(from_stn)]
    if to_stns:
        to_stn = st.sidebar.selectbox("To Station", to_stns, index=len(to_stns)-1)
    else:
        st.sidebar.warning("Select a different From station.")
        st.stop()
        
st.sidebar.markdown("### Search Parameters")
min_headway = st.sidebar.slider(
    "Minimum headway (min each side)", 2, 15, 5,
    help="Gap required between new train and existing trains at every station"
)

t_start = st.sidebar.number_input("Search from hour", 0, 23, 0, 1)
t_end   = st.sidebar.number_input("Search to hour",   1, 24, 24, 1)
if t_end <= t_start: t_end = t_start + 1

show_chart  = st.sidebar.checkbox("Show Marey chart for selected window", True)
show_all_db = st.sidebar.checkbox("Show full path database for this line", False) if search_mode == "Single Line" else False

if st.sidebar.button("🔍 Find Available Paths", type="primary", use_container_width=True):
    with st.spinner(f"Scanning for available paths..."):
        if search_mode == "Single Line":
            windows = find_paths(
                stops, sel_line, from_stn, to_stn,
                min_headway=min_headway,
                time_start=t_start * 60,
                time_end=t_end * 60,
            )
        else:
            windows = find_multi_line_paths(
                stops, direction, from_stn, to_stn,
                min_headway=min_headway,
                start_time=t_start * 60,
                end_time=t_end * 60,
            )
            
        st.session_state['pf_results'] = {
            'windows': windows,
            'search_mode': search_mode,
            'sel_line': sel_line,
            'from_stn': from_stn,
            'to_stn': to_stn,
            't_end': t_end,
            't_start': t_start,
            'min_headway': min_headway
        }

# ══════════════════════════════════════════════════════════════════════════════
# MAIN — Display Results
# ══════════════════════════════════════════════════════════════════════════════
res = st.session_state.get('pf_results')

if res:
    windows = res['windows']
    sel_line = res['sel_line']
    from_stn = res['from_stn']
    to_stn = res['to_stn']
    search_mode = res['search_mode']
    t_end = res['t_end']
    t_start = res['t_start']
    min_headway = res['min_headway']

    # ── Summary metrics ──────────────────────────────────────────────────────
    total_mins = (t_end - t_start) * 60
    feasible_mins = sum(w["window_mins"] for w in windows)
    wide   = [w for w in windows if w["classification"] == "WIDE"]
    medium = [w for w in windows if w["classification"] == "MEDIUM"]
    tight  = [w for w in windows if w["classification"] == "TIGHT"]

    if search_mode == "Single Line":
        st.markdown(f"### Results — {sel_line}: {from_stn} → {to_stn}")
    else:
        st.markdown(f"### Results — Multi-Line: {from_stn} → {to_stn}")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Windows found",      len(windows))
    c2.metric("Feasible minutes",   f"{feasible_mins} / {total_mins}")
    c3.metric("🟢 Wide (≥10 min)",  len(wide))
    c4.metric("🟡 Medium (6–9 min)",len(medium))
    c5.metric("🔴 Tight (<6 min)",  len(tight))

    if not windows:
        st.error(
            f"❌ No available paths found between {from_stn} and {to_stn} "
            f"with {min_headway}-minute headway in the selected time window. "
            "Try reducing the minimum headway or expanding the time window."
        )
    else:
        # ── Path windows table ───────────────────────────────────────────────
        st.markdown("#### Available Path Windows")
        st.caption("Each row = a continuous window where a new train can depart from the origin station.")

        rows = []
        key_stns = list(windows[0]["key_times"].keys()) if windows else []
        for w in windows:
            row = {
                "Status":      ("🟢 WIDE" if w["classification"]=="WIDE"
                                else "🟡 MEDIUM" if w["classification"]=="MEDIUM"
                                else "🔴 TIGHT"),
                "Route": w.get('virtual_line', {}).get('label', sel_line) if "Multi-Line" in search_mode else sel_line,
                "Dep Window":  f"{w['dep_start_str']} – {w['dep_end_str']}",
                "Window (min)":w["window_mins"],
                "Min Gap (min)": w["min_gap"],
            }
            for stn in key_stns:
                row[f"@ {stn}"] = w["key_times"].get(stn, "—")
            rows.append(row)

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, height=min(400, 50 + 35 * len(windows)))

        st.download_button(
            "⬇️ Download Path Windows CSV",
            df.to_csv(index=False),
            f"paths_{from_stn}_{to_stn}.csv",
            "text/csv",
        )

        # ── Marey chart for selected window ──────────────────────────────────
        if show_chart and windows:
            st.markdown("#### 📊 Marey Visualisation")
            st.caption("Select a path window to overlay the proposed new train on the existing timetable.")

            sel_w_idx = st.selectbox(
                "Show proposed train for window:",
                range(len(windows)),
                format_func=lambda i: (
                    f"{windows[i].get('virtual_line', {}).get('label', sel_line) if 'Multi-Line' in search_mode else sel_line} | "
                    f"{windows[i]['dep_start_str']}–{windows[i]['dep_end_str']}  "
                    f"({windows[i]['classification']}, gap≥{windows[i]['min_gap']}min)"
                ),
            )
            sel_w = windows[sel_w_idx]
            proposed_dep = (sel_w["dep_start"] + sel_w["dep_end"]) // 2

            # Route and offsets
            route = sel_w["route"]
            if "Multi-Line" in search_mode:
                vline = sel_w["virtual_line"]
                offsets = vline["offsets"]
                local_off = offsets
                direction = vline["direction"]
                LINE_COL = "#ffffff"
            else:
                line_meta = LINES_META[sel_line]
                offsets = {s: v for s, v in line_meta["offsets"].items() if s in route}
                base = offsets.get(from_stn, 0)
                local_off = {s: offsets[s] - base for s in route if s in offsets}
                direction = line_meta["direction"]
                LINE_COL = line_meta.get("color", "#aaa")

            # Geography aware stn mapping (CCG at top)
            geo_route = sorted(route, key=lambda s: STATIONS.index(s))
            stn_idx_map = {s: i for i, s in enumerate(geo_route)}

            # Build chart data
            existing_lines = []
            
            if search_mode == "Single Line":
                # Single line
                by_train = defaultdict(list)
                for s in stops:
                    if s.get("line") != sel_line: continue
                    if s.get("direction") != direction: continue
                    if s["station"] not in stn_idx_map: continue
                    by_train[s["train"]].append(s)
            else:
                # Multi-Line: Add trains running on any segment line during that segment
                by_train = defaultdict(list)
                for seg in vline['segments']:
                    seg_meta = LINES_META[seg['line']]
                    rt = seg_meta['route']
                    i1, i2 = rt.index(seg['from']), rt.index(seg['to'])
                    seg_stns = set(rt[i1:i2+1])
                    for s in stops:
                        if s.get("line") != seg['line']: continue
                        if s.get("direction") != direction: continue
                        if s["station"] not in stn_idx_map or s["station"] not in seg_stns: continue
                        by_train[s["train"]].append(s)

            for tr, pts in by_train.items():
                pts.sort(key=lambda x: x["minutes"])
                coords = []
                for p in pts:
                    if p["station"] not in stn_idx_map: continue
                    m = p["minutes"] % 1440
                    coords.append([m, stn_idx_map[p["station"]], p["time"]])
                if coords:
                    m0 = pts[0]
                    existing_lines.append([
                        tr, m0.get("direction",""), m0.get("type",""),
                        m0.get("train_cat","LOCAL"), m0.get("ac",""),
                        m0.get("from_stn",""), m0.get("to_stn",""), coords
                    ])

            # Proposed new train path
            proposed_coords = []
            for stn in route:
                off = local_off.get(stn)
                if off is None: continue
                t = (proposed_dep + off) % 1440
                proposed_coords.append([t, stn_idx_map[stn], f"{t//60:02d}:{t%60:02d}"])
                
            proposed_line = [
                f"NEW ({from_stn}→{to_stn})", direction, train_type,
                "MAIL" if train_type == "M/E" else "LOCAL",
                "", from_stn, to_stn, proposed_coords
            ]

            chart_tmin = max(0, proposed_dep - 60)
            # Estimate max offset
            max_off = max(local_off.values()) if local_off else 0
            chart_tmax = min(1440, proposed_dep + max_off + 60)

            CAT_COL_JS = json.dumps({c: {"slow": v["slow"], "fast": v["fast"]} for c, v in CAT_COLORS.items()})
            
            def hl(h): return f"{h:02d}:00" if h < 24 else f"{h-24:02d}:00⁺"
            hticks = json.dumps([{"m": h*60, "l": hl(h)} for h in range(chart_tmin//60, chart_tmax//60+2)])

            PROP_LINE_JSON = json.dumps(proposed_line)
            EXISTING_JSON  = json.dumps(existing_lines)
            STNS_JSON      = json.dumps(geo_route)

            html = f'''<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;overflow:hidden;width:100%;height:100%;}}
#app{{display:flex;flex-direction:column;height:100vh;}}
#tb{{flex-shrink:0;padding:4px 8px;background:#141824;border-bottom:1px solid #252840;
  font-size:11px;color:#99aabb;display:flex;gap:8px;align-items:center;}}
#tb b{{color:#fff;}}
#area{{flex:1;display:grid;grid-template-columns:80px 1fr;grid-template-rows:28px 1fr;overflow:hidden;}}
#c-tl{{background:#0f1117;border-right:2px solid #252840;border-bottom:2px solid #252840;}}
#c-xa{{overflow:hidden;border-bottom:2px solid #252840;background:#0f1117;}}
#c-ya{{overflow:hidden;border-right:2px solid #252840;background:#0f1117;}}
#c-bd{{overflow:auto;}}
.tip{{position:fixed;background:rgba(10,12,24,0.97);border:1px solid #445;border-radius:6px;
  padding:7px 11px;font-size:11px;color:#eee;pointer-events:none;display:none;z-index:999;line-height:1.7;}}
</style></head><body>
<div id="app">
  <div id="tb">
    <span>Route: <b>{from_stn} → {to_stn}</b></span>
    <span>Proposed dep: <b style="color:#fff">{proposed_dep//60:02d}:{proposed_dep%60:02d}</b></span>
    <span style="margin-left:12px">
      <span style="display:inline-block;width:14px;height:3px;background:{LINE_COL};vertical-align:middle"></span> Existing
      <span style="display:inline-block;width:14px;height:3px;background:#FFFFFF;vertical-align:middle;margin-left:8px"></span> Proposed new train
    </span>
  </div>
  <div id="area">
    <div id="c-tl"></div>
    <div id="c-xa"><canvas id="cx"></canvas></div>
    <div id="c-ya"><canvas id="cy"></canvas></div>
    <div id="c-bd"><canvas id="cm"></canvas></div>
  </div>
</div>
<div class="tip" id="tip"></div>
<script>
const EXISTING  = {EXISTING_JSON};
const PROPOSED  = {PROP_LINE_JSON};
const STNS      = {STNS_JSON};
const HTICKS    = {hticks};
const CAT_COL   = {CAT_COL_JS};
const LINE_COL  = "{LINE_COL}";
const NEW_COL   = "#FFFFFF";
const T_MIN={chart_tmin}, T_MAX={chart_tmax};
const CH=22, CW=2;

const bd=document.getElementById("c-bd"),xa=document.getElementById("c-xa"),
      ya=document.getElementById("c-ya"),tip=document.getElementById("tip");
bd.addEventListener("scroll",()=>{{xa.scrollLeft=bd.scrollLeft;ya.scrollTop=bd.scrollTop;}});

function setC(c,w,h){{
  const d=window.devicePixelRatio||1;
  c.width=w*d;c.height=h*d;c.style.width=w+"px";c.style.height=h+"px";
  const ctx=c.getContext("2d");ctx.scale(d,d);return ctx;
}}
const xPx=m=>(m-T_MIN)*CW, yPx=i=>i*CH;
function lCol(cat,typ){{
  const c=CAT_COL[cat]||CAT_COL['LOCAL'];
  return typ==="FAST"?c.fast:c.slow;
}}

function drawX(){{
  const W=(T_MAX-T_MIN)*CW,H=28,ctx=setC(document.getElementById("cx"),W,H);
  ctx.fillStyle="#0f1117";ctx.fillRect(0,0,W,H);
  HTICKS.forEach(t=>{{
    const xp=xPx(t.m);
    ctx.strokeStyle="#252840";ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(xp,0);ctx.lineTo(xp,H);ctx.stroke();
    ctx.fillStyle="#5566aa";ctx.font="9px Arial";ctx.textAlign="center";
    ctx.fillText(t.l,xp,H-4);
  }});
}}

function drawY(){{
  const W=80,H=STNS.length*CH,ctx=setC(document.getElementById("cy"),W,H);
  STNS.forEach((stn,i)=>{{
    ctx.fillStyle=i%2===0?"#12161e":"#0d1117";
    ctx.fillRect(0,yPx(i),W,CH);
    ctx.fillStyle="#ccddee";ctx.font="9px Arial";ctx.textAlign="right";
    ctx.textBaseline="middle";ctx.fillText(stn,W-4,yPx(i)+CH/2);
  }});
}}

function drawMain(){{
  const W=(T_MAX-T_MIN)*CW,H=STNS.length*CH;
  const ctx=setC(document.getElementById("cm"),W,H);
  ctx.clearRect(0,0,W,H);

  STNS.forEach((_,i)=>{{
    ctx.fillStyle=i%2===0?"#12161e":"#0d1117";
    ctx.fillRect(0,yPx(i),W,CH);
  }});
  HTICKS.forEach(t=>{{
    ctx.strokeStyle="#252840";ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(xPx(t.m),0);ctx.lineTo(xPx(t.m),H);ctx.stroke();
  }});
  STNS.forEach((_,i)=>{{
    ctx.strokeStyle="#1a1e28";ctx.lineWidth=0.4;
    ctx.beginPath();ctx.moveTo(0,yPx(i+1));ctx.lineTo(W,yPx(i+1));ctx.stroke();
  }});

  // Min headway bands
  const propPts=PROPOSED[7];
  if(propPts&&propPts.length>1){{
    const hw={min_headway};
    ctx.fillStyle="rgba(255,255,100,0.06)";
    ctx.beginPath();
    ctx.moveTo(xPx((propPts[0][0]-hw+1440)%1440),yPx(propPts[0][1])+CH/2);
    for(let i=1;i<propPts.length;i++) ctx.lineTo(xPx((propPts[i][0]-hw+1440)%1440),yPx(propPts[i][1])+CH/2);
    for(let i=propPts.length-1;i>=0;i--) ctx.lineTo(xPx((propPts[i][0]+hw)%1440),yPx(propPts[i][1])+CH/2);
    ctx.closePath();ctx.fill();
  }}

  EXISTING.forEach(l=>{{
    const [tr,dir,typ,cat,ac,fr,to,pts]=l;
    if(!pts||pts.length<2) return;
    const col=lCol(cat,typ);
    ctx.strokeStyle=col;ctx.lineWidth=1.2;ctx.globalAlpha=0.55;
    ctx.beginPath();
    ctx.moveTo(xPx(pts[0][0]),yPx(pts[0][1])+CH/2);
    for(let i=1;i<pts.length;i++) ctx.lineTo(xPx(pts[i][0]),yPx(pts[i][1])+CH/2);
    ctx.stroke();ctx.globalAlpha=1;
  }});

  if(propPts&&propPts.length>1){{
    ctx.strokeStyle=NEW_COL;ctx.lineWidth=2.8;ctx.globalAlpha=1;
    ctx.beginPath();
    ctx.moveTo(xPx(propPts[0][0]),yPx(propPts[0][1])+CH/2);
    for(let i=1;i<propPts.length;i++) ctx.lineTo(xPx(propPts[i][0]),yPx(propPts[i][1])+CH/2);
    ctx.stroke();
    propPts.forEach(p=>{{
      ctx.fillStyle=NEW_COL;
      ctx.beginPath();ctx.arc(xPx(p[0]),yPx(p[1])+CH/2,3,0,Math.PI*2);ctx.fill();
    }});
    ctx.fillStyle=NEW_COL;ctx.font="bold 9px Arial";ctx.textAlign="left";
    ctx.textBaseline="bottom";
    if(propPts.length>0) ctx.fillText("NEW →",xPx(propPts[0][0])+2,yPx(propPts[0][1])+CH/2-1);
  }}
}}

drawX();drawY();drawMain();

const cm=document.getElementById("cm");
const hitBoxes=[];
EXISTING.forEach(l=>{{
  const [tr,dir,typ,cat,ac,fr,to,pts]=l;
  pts.forEach(p=>{{
    if(p[0]<T_MIN||p[0]>T_MAX) return;
    hitBoxes.push({{x:xPx(p[0])-6,y:yPx(p[1])+CH/2-6,w:12,h:12,
      html:`<b>${{p[2]}}</b> @ <b>${{tr}}</b><br>${{dir}}·${{typ}}·${{cat}}<br>${{fr}}→${{to}}`}});
  }});
}});
PROPOSED[7].forEach(p=>{{
  hitBoxes.push({{x:xPx(p[0])-7,y:yPx(p[1])+CH/2-7,w:14,h:14,
    html:`<b style="color:#fff">PROPOSED NEW TRAIN</b><br>${{from_stn}}→${{to_stn}}<br>@ ${{p[2]}}`}});
}});
cm.addEventListener("mousemove",e=>{{
  const r=cm.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
  const b=hitBoxes.find(b=>mx>=b.x&&mx<=b.x+b.w&&my>=b.y&&my<=b.y+b.h);
  if(b){{tip.style.display="block";tip.innerHTML=b.html;
         tip.style.left=(e.clientX+14)+"px";tip.style.top=(e.clientY-10)+"px";}}
  else tip.style.display="none";
}});
cm.addEventListener("mouseleave",()=>tip.style.display="none");
</script></body></html>'''
            st.components.v1.html(html, height=500, scrolling=False)

        # ── Bottleneck analysis ──────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📍 Station-by-Station Gap Analysis")
        st.caption("For the selected window's midpoint departure, shows the actual gap to adjacent trains.")

        if windows:
            w = sel_w
            mid_dep = (w["dep_start"] + w["dep_end"]) // 2
            route_stns = w["route"]

            if "Multi-Line" in search_mode:
                vline = w["virtual_line"]
                offsets = vline["offsets"]
                from _path_finder import generate_occupancy_for_virtual
                occupancy = generate_occupancy_for_virtual(stops, vline)
            else:
                base_off = LINES_META[sel_line]["offsets"].get(from_stn, 0)
                offsets = {s: LINES_META[sel_line]["offsets"][s] - base_off for s in route_stns if s in LINES_META[sel_line]["offsets"]}
                occupancy = load_occupancy(stops, sel_line)

            gap_rows = []
            for stn in route_stns:
                off = offsets.get(stn)
                if off is None: continue
                arr = (mid_dep + off) % 1440
                occ = occupancy.get(stn, [])
                if not occ:
                    gap_rows.append({"Station": stn, "New train": f"{arr//60:02d}:{arr%60:02d}", "Prev train": "—", "Gap before": "—", "Next train": "—", "Gap after": "—", "Status": "No data"})
                    continue
                from bisect import bisect_left
                pos = bisect_left(occ, arr)
                prev_t = occ[pos-1] if pos > 0 else occ[-1]-1440
                next_t = occ[pos] if pos < len(occ) else occ[0]+1440
                gb = arr - prev_t; ga = next_t - arr
                status = ("✅ OK" if min(gb,ga) >= min_headway else "⚠️ Tight" if min(gb,ga) >= min_headway-2 else "🔴 Conflict")
                gap_rows.append({
                    "Station": stn, "New train": f"{arr//60:02d}:{arr%60:02d}",
                    "Prev train": f"{prev_t%1440//60:02d}:{prev_t%1440%60:02d}", "Gap before": f"{gb} min",
                    "Next train": f"{next_t%1440//60:02d}:{next_t%1440%60:02d}", "Gap after": f"{ga} min", "Status": status,
                })

            df_gap = pd.DataFrame(gap_rows)
            st.dataframe(df_gap, use_container_width=True, height=400)
            st.download_button("⬇️ Gap Analysis CSV", df_gap.to_csv(index=False), f"gap_analysis.csv", "text/csv")
