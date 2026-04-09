import streamlit as st
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))

from _utils import load_stops, load_meta, STATIONS, LINES_DEF, CAT_COLORS
from _path_finder import (LINES_META, LINE_ENDPOINT_RULES, CROSSOVERS,
                           find_paths, load_occupancy)
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

st.sidebar.markdown("### New Train Parameters")
direction  = st.sidebar.radio("Direction", ["DOWN", "UP"])
train_type = st.sidebar.radio("Train Type", ["SLOW", "FAST", "M/E"])

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

# From / To on this line
if line_route:
    from_stn = st.sidebar.selectbox("From Station", line_route,
                                     index=0)
    to_stns  = [s for s in line_route if line_route.index(s) > line_route.index(from_stn)]
    if to_stns:
        to_stn = st.sidebar.selectbox("To Station", to_stns,
                                       index=len(to_stns)-1)
    else:
        st.sidebar.warning("Select a different From station.")
        st.stop()
else:
    st.sidebar.error("Line route not configured.")
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
show_all_db = st.sidebar.checkbox("Show full path database for this line", False)

run = st.sidebar.button("🔍 Find Available Paths", type="primary", use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# INFO PANEL — Line rules reference
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("📋 Line Rules & Crossover Points", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
**Line Sections:**
| Line | Direction | Section |
|---|---|---|
| DNLL | DOWN | CCG → VR |
| UPLL | UP | VR → CCG |
| DNTL | DOWN | CCG → DRD |
| UPTL | UP | DRD → CCG |
| DNHB | DOWN | BA → GMN |
| UPHB | UP | GMN → BA |
""")
    with col2:
        st.markdown("""
**Crossover Points:**
| From → To | Cross at |
|---|---|
| DNLL → DNHB | BA or ADH |
| DNHB → DNLL | ADH |
| UPHB → UPLL | ADH |

**Train type guidance:**
- SLOW trains → Local Line (DNLL/UPLL)
- FAST trains → Through Line (DNTL/UPTL)
- M/E trains → Usually Through Line
""")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN — Run path-finding
# ══════════════════════════════════════════════════════════════════════════════
if run:
    with st.spinner(f"Scanning {sel_line} {from_stn}→{to_stn} for available paths..."):
        windows = find_paths(
            stops, sel_line, from_stn, to_stn,
            min_headway=min_headway,
            time_start=t_start * 60,
            time_end=t_end * 60,
        )

    # ── Summary metrics ──────────────────────────────────────────────────────
    total_mins = (t_end - t_start) * 60
    feasible_mins = sum(w["window_mins"] for w in windows)
    wide   = [w for w in windows if w["classification"] == "WIDE"]
    medium = [w for w in windows if w["classification"] == "MEDIUM"]
    tight  = [w for w in windows if w["classification"] == "TIGHT"]

    st.markdown(f"### Results — {sel_line}: {from_stn} → {to_stn}")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Windows found",      len(windows))
    c2.metric("Feasible minutes",   f"{feasible_mins} / {total_mins}")
    c3.metric("🟢 Wide (≥10 min)",  len(wide))
    c4.metric("🟡 Medium (6–9 min)",len(medium))
    c5.metric("🔴 Tight (<6 min)",  len(tight))

    if not windows:
        st.error(
            f"❌ No available paths found on {sel_line} between {from_stn} and {to_stn} "
            f"with {min_headway}-minute headway in the selected time window. "
            "Try reducing the minimum headway or expanding the time window."
        )
    else:
        # ── Path windows table ───────────────────────────────────────────────
        st.markdown("#### Available Path Windows")
        st.caption("Each row = a continuous window where a new train can depart from the origin station. "
                   "Middle departure time shown for key station times.")

        # Build display table
        rows = []
        key_stns = list(windows[0]["key_times"].keys()) if windows else []
        for w in windows:
            row = {
                "Status":      ("🟢 WIDE" if w["classification"]=="WIDE"
                                else "🟡 MEDIUM" if w["classification"]=="MEDIUM"
                                else "🔴 TIGHT"),
                "Dep Window":  f"{w['dep_start_str']} – {w['dep_end_str']}",
                "Window (min)":w["window_mins"],
                "Min Gap (min)": w["min_gap"],
            }
            for stn in key_stns:
                row[f"@ {stn}"] = w["key_times"].get(stn, "—")
            rows.append(row)

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, height=min(400, 50 + 35 * len(windows)))

        # Download
        st.download_button(
            "⬇️ Download Path Windows CSV",
            df.to_csv(index=False),
            f"paths_{sel_line}_{from_stn}_{to_stn}.csv",
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
                    f"{windows[i]['dep_start_str']}–{windows[i]['dep_end_str']}  "
                    f"({windows[i]['classification']}, gap≥{windows[i]['min_gap']}min)"
                ),
            )
            sel_w = windows[sel_w_idx]
            # Use the middle of the window as the proposed departure
            proposed_dep = (sel_w["dep_start"] + sel_w["dep_end"]) // 2

            # Get route and offsets
            offsets = {s: v for s, v in line_meta["offsets"].items()
                       if s in sel_w["route"]}
            base = offsets.get(from_stn, 0)
            local_off = {s: offsets[s] - base for s in sel_w["route"] if s in offsets}

            # Build chart data
            route   = sel_w["route"]
            stn_idx_map = {s: i for i, s in enumerate(route)}

            # Existing trains on this line/route section
            existing_lines = []
            by_train = defaultdict(list)
            for s in stops:
                if s.get("line") != sel_line: continue
                if s.get("direction") != line_meta.get("direction"): continue
                if s["station"] not in stn_idx_map: continue
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
                proposed_coords.append([t, stn_idx_map[stn],
                                         f"{t//60:02d}:{t%60:02d}"])
            proposed_line = [
                f"NEW ({from_stn}→{to_stn})", line_meta.get("direction",""), train_type,
                "MAIL" if train_type == "M/E" else ("LOCAL" if train_type=="SLOW" else "LOCAL"),
                "", from_stn, to_stn, proposed_coords
            ]

            # Time window for chart: ±2 hours around proposed window
            chart_tmin = max(0, proposed_dep - 60)
            chart_tmax = min(1440, proposed_dep + line_meta["offsets"].get(to_stn, 0) + 60)

            # Category colours
            CAT_COL_JS = json.dumps({
                c: {"slow": v["slow"], "fast": v["fast"]}
                for c, v in CAT_COLORS.items()
            })
            CAT_LABEL_JS = json.dumps({k: v["label"] for k, v in CAT_COLORS.items()})

            def hl(h):
                return f"{h:02d}:00" if h < 24 else f"{h-24:02d}:00⁺"
            hticks = json.dumps([{"m": h*60, "l": hl(h)}
                                  for h in range(chart_tmin//60, chart_tmax//60+2)])

            # NEW train colour = bright white
            NEW_COL = "#FFFFFF"
            PROP_LINE_JSON = json.dumps(proposed_line)
            EXISTING_JSON  = json.dumps(existing_lines)
            STNS_JSON      = json.dumps(route)
            TMIN, TMAX     = chart_tmin, chart_tmax
            LINE_COL       = line_meta.get("color", "#aaa")

            html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
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
    <span>Line: <b style="color:{LINE_COL}">{sel_line} — {line_meta.get('label','')}</b></span>
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
const NEW_COL   = "{NEW_COL}";
const T_MIN={TMIN}, T_MAX={TMAX};
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

  // Background
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

  // Minimum headway bands around proposed path
  const propPts=PROPOSED[7];
  if(propPts&&propPts.length>1){{
    const hw={min_headway};
    ctx.fillStyle="rgba(255,255,100,0.06)";
    // Draw band hw minutes before and after proposed path
    ctx.beginPath();
    ctx.moveTo(xPx((propPts[0][0]-hw+1440)%1440),yPx(propPts[0][1])+CH/2);
    for(let i=1;i<propPts.length;i++)
      ctx.lineTo(xPx((propPts[i][0]-hw+1440)%1440),yPx(propPts[i][1])+CH/2);
    for(let i=propPts.length-1;i>=0;i--)
      ctx.lineTo(xPx((propPts[i][0]+hw)%1440),yPx(propPts[i][1])+CH/2);
    ctx.closePath();ctx.fill();
  }}

  // Existing trains — dimmed
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

  // Proposed new train — bright white, thick
  const [tr,dir,typ,cat,ac,fr,to,pts]=PROPOSED;
  if(pts&&pts.length>1){{
    ctx.strokeStyle=NEW_COL;ctx.lineWidth=2.8;ctx.globalAlpha=1;
    ctx.beginPath();
    ctx.moveTo(xPx(pts[0][0]),yPx(pts[0][1])+CH/2);
    for(let i=1;i<pts.length;i++) ctx.lineTo(xPx(pts[i][0]),yPx(pts[i][1])+CH/2);
    ctx.stroke();
    // Dots at each stop
    pts.forEach(p=>{{
      ctx.fillStyle=NEW_COL;
      ctx.beginPath();ctx.arc(xPx(p[0]),yPx(p[1])+CH/2,3,0,Math.PI*2);ctx.fill();
    }});
    // Label
    ctx.fillStyle=NEW_COL;ctx.font="bold 9px Arial";ctx.textAlign="left";
    ctx.textBaseline="bottom";
    if(pts.length>0) ctx.fillText("NEW →",xPx(pts[0][0])+2,yPx(pts[0][1])+CH/2-1);
  }}
}}

drawX();drawY();drawMain();

// Hover tooltip on main canvas
const cm=document.getElementById("cm");
const hitBoxes=[];
EXISTING.forEach(l=>{{
  const [tr,dir,typ,cat,ac,fr,to,pts]=l;
  const col=lCol(cat,typ);
  pts.forEach(p=>{{
    if(p[0]<T_MIN||p[0]>T_MAX) return;
    hitBoxes.push({{x:xPx(p[0])-6,y:yPx(p[1])+CH/2-6,w:12,h:12,
      html:`<b>${{p[2]}}</b> @ <b>${{tr}}</b><br>${{dir}}·${{typ}}·${{cat}}<br>${{fr}}→${{to}}`}});
  }});
}});
PROPOSED[7].forEach(p=>{{
  hitBoxes.push({{x:xPx(p[0])-7,y:yPx(p[1])+CH/2-7,w:14,h:14,
    html:`<b style="color:#fff">PROPOSED NEW TRAIN</b><br>${{tr}} ${{from_stn}}→${{to_stn}}<br>@ ${{p[2]}}`}});
}});
cm.addEventListener("mousemove",e=>{{
  const r=cm.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
  const b=hitBoxes.find(b=>mx>=b.x&&mx<=b.x+b.w&&my>=b.y&&my<=b.y+b.h);
  if(b){{tip.style.display="block";tip.innerHTML=b.html;
         tip.style.left=(e.clientX+14)+"px";tip.style.top=(e.clientY-10)+"px";}}
  else tip.style.display="none";
}});
cm.addEventListener("mouseleave",()=>tip.style.display="none");
</script></body></html>"""
            st.components.v1.html(html, height=500, scrolling=False)

        # ── Bottleneck analysis ──────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📍 Station-by-Station Gap Analysis")
        st.caption("For the selected window's midpoint departure, shows the actual gap "
                   "to adjacent trains at every station.")

        if windows:
            sel_w2 = windows[0] if not show_chart else windows[
                st.session_state.get("sel_w_idx2", 0) if "sel_w_idx2" in st.session_state
                else 0
            ]
            # Use first window for analysis
            w = windows[0]
            mid_dep = (w["dep_start"] + w["dep_end"]) // 2

            offsets_full = line_meta.get("offsets", {})
            base_off     = offsets_full.get(from_stn, 0)
            route_stns   = w["route"]

            occupancy = load_occupancy(stops, sel_line)

            gap_rows = []
            for stn in route_stns:
                off = offsets_full.get(stn)
                if off is None: continue
                local = off - base_off
                arr   = (mid_dep + local) % 1440
                occ   = occupancy.get(stn, [])
                if not occ:
                    gap_rows.append({"Station": stn, "New train": f"{arr//60:02d}:{arr%60:02d}",
                                     "Prev train": "—", "Gap before": "—",
                                     "Next train": "—", "Gap after": "—", "Status": "No data"})
                    continue
                from bisect import bisect_left
                pos = bisect_left(occ, arr)
                prev_t = occ[pos-1] if pos > 0 else occ[-1]-1440
                next_t = occ[pos] if pos < len(occ) else occ[0]+1440
                gb = arr - prev_t; ga = next_t - arr
                status = ("✅ OK" if min(gb,ga) >= min_headway
                          else "⚠️ Tight" if min(gb,ga) >= min_headway-2
                          else "🔴 Conflict")
                gap_rows.append({
                    "Station":      stn,
                    "New train":    f"{arr//60:02d}:{arr%60:02d}",
                    "Prev train":   f"{prev_t%1440//60:02d}:{prev_t%1440%60:02d}",
                    "Gap before":   f"{gb} min",
                    "Next train":   f"{next_t%1440//60:02d}:{next_t%1440%60:02d}",
                    "Gap after":    f"{ga} min",
                    "Status":       status,
                })

            df_gap = pd.DataFrame(gap_rows)
            st.dataframe(df_gap, use_container_width=True, height=400)
            st.download_button("⬇️ Gap Analysis CSV", df_gap.to_csv(index=False),
                               f"gap_analysis_{sel_line}.csv", "text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# PATH DATABASE — All windows for this line (pre-scanned)
# ══════════════════════════════════════════════════════════════════════════════
if show_all_db:
    st.markdown("---")
    st.markdown(f"### 📚 Full Path Database — {sel_line}")
    st.caption(f"All available path windows across the full day for {sel_line} "
               f"({line_meta.get('desc','')}). "
               f"Minimum headway: {min_headway} min. Sorted by time.")

    with st.spinner("Scanning full day..."):
        all_routes = LINES_META[sel_line]["route"]
        db_windows = find_paths(
            stops, sel_line,
            from_stn=all_routes[0],
            to_stn=all_routes[-1],
            min_headway=min_headway,
        )

    if db_windows:
        db_rows = []
        for w in db_windows:
            key_stns = list(w["key_times"].keys())
            row = {
                "Status":        ("🟢 WIDE" if w["classification"]=="WIDE"
                                  else "🟡 MEDIUM" if w["classification"]=="MEDIUM"
                                  else "🔴 TIGHT"),
                "Dep Window":    f"{w['dep_start_str']} – {w['dep_end_str']}",
                "Width (min)":   w["window_mins"],
                "Min Gap (min)": w["min_gap"],
            }
            for stn in key_stns:
                row[f"@ {stn}"] = w["key_times"].get(stn,"—")
            db_rows.append(row)

        df_db = pd.DataFrame(db_rows)
        wide_ct   = sum(1 for w in db_windows if w["classification"]=="WIDE")
        med_ct    = sum(1 for w in db_windows if w["classification"]=="MEDIUM")
        tight_ct  = sum(1 for w in db_windows if w["classification"]=="TIGHT")

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total windows", len(db_windows))
        c2.metric("🟢 Wide",   wide_ct)
        c3.metric("🟡 Medium", med_ct)
        c4.metric("🔴 Tight",  tight_ct)

        st.dataframe(df_db, use_container_width=True,
                     height=min(600, 50 + 35 * len(db_windows)))
        st.download_button(
            f"⬇️ Download {sel_line} Path Database CSV",
            df_db.to_csv(index=False),
            f"path_database_{sel_line}_hw{min_headway}.csv",
            "text/csv",
        )
    else:
        st.warning(f"No available paths found on {sel_line} full route with {min_headway}-min headway.")
