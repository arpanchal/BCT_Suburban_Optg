import streamlit as st
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _utils import _stops_mtime, _meta_mtime, load_stops, load_meta, CAT_COLORS
from collections import defaultdict

# st.set_page_config(page_title="Rake Link Utilisation", layout="wide", initial_sidebar_state="collapsed")

stops = load_stops(_mtime=_stops_mtime())
meta  = load_meta(_mtime=_meta_mtime())

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🚃 Rake Link")

all_links = sorted(set(m.get('link', '') for m in meta.values() if m.get('link')))
train_types_f = st.sidebar.multiselect("Train Type", ["SLOW", "FAST", "M/E"], default=["SLOW", "FAST", "M/E"])
link_search   = st.sidebar.text_input("Filter links (e.g. A, BU)", "").upper().strip()
t_start = st.sidebar.number_input("Start hour", 0, 24, 0, 1)
t_end   = st.sidebar.number_input("End hour (>24 = next day)", 1, 26, 26, 1)
cell_h  = st.sidebar.slider("Row height (px)", 14, 40, 22, 2)
show_labels = st.sidebar.checkbox("Show train numbers", True)

t_min = int(t_start) * 60
t_max = int(t_end)   * 60

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🚃 Rake Link Utilisation Chart")
st.caption("Each row = one rake link. Each bar = one train trip. Hover for details. "
           "Utilisation % = active running time ÷ day span × 100.")

# ── Build timing from stops ───────────────────────────────────────────────────
tr_timing = defaultdict(lambda: [9999, -1])
for s in stops:
    tr  = s['train']
    mn  = s['minutes']
    if mn < tr_timing[tr][0]: tr_timing[tr][0] = mn
    if mn > tr_timing[tr][1]: tr_timing[tr][1] = mn

# ── Group trains by link ──────────────────────────────────────────────────────
link_trains = defaultdict(list)
for tr, m in meta.items():
    lk = m.get('link', '')
    if not lk: continue
    if m.get('type', 'SLOW') not in train_types_f: continue
    timing = tr_timing.get(tr)
    if not timing or timing[0] == 9999: continue
    link_trains[lk].append({
        'train':  tr,
        'dep':    timing[0],
        'arr':    timing[1],
        'dir':    m.get('direction', ''),
        'typ':    m.get('type', 'SLOW'),
        'cat':    m.get('train_cat', 'LOCAL'),
        'from':   m.get('from_stn', ''),
        'to':     m.get('to_stn', ''),
        'cars':   m.get('cars', ''),
        'ac':     m.get('ac', ''),
    })

# 1. Sort A→Z then AA→AZ, BA→BZ … (length-first, then alpha)
def link_sort_key(lk): return (len(lk), lk)

# 2. Exclude GN-based links
filtered_links = sorted(
    (lk for lk in link_trains if not lk.upper().startswith('GN')),
    key=link_sort_key
)
if link_search:
    terms = [t.strip() for t in link_search.replace(',', ' ').split()]
    filtered_links = [lk for lk in filtered_links if any(lk == t or lk.startswith(t) for t in terms)]

if not filtered_links:
    st.warning("No rake links match the current filters.")
    st.stop()

# ── Compute utilisation for each link ────────────────────────────────────────
def utilisation(trips, t_min, t_max):
    """Total running minutes within window ÷ window length × 100."""
    window = t_max - t_min
    if window <= 0: return 0.0
    active = 0
    for tr in trips:
        lo = max(tr['dep'], t_min)
        hi = min(tr['arr'], t_max)
        if hi > lo:
            active += hi - lo
    return min(100.0, active / window * 100)

# ── Summary metrics ───────────────────────────────────────────────────────────
total_links = len(filtered_links)
total_trains_shown = sum(len(link_trains[lk]) for lk in filtered_links)
avg_util = sum(utilisation(link_trains[lk], t_min, t_max) for lk in filtered_links) / max(1, total_links)

mc1, mc2, mc3, mc4 = st.columns(4)
mc1.metric("🔗 Links shown",     total_links)
mc2.metric("🚆 Train trips",     total_trains_shown)
mc3.metric("📊 Avg Utilisation", f"{avg_util:.1f}%")
mc4.metric("⏱️ Time window",     f"{t_start:02.0f}:00 – {t_end:02.0f}:00")

# ── Build JSON for chart ──────────────────────────────────────────────────────
CAT_PALETTE = {
    'LOCAL':    {'slow': '#4CAF50', 'fast': '#00E676'},
    'AC_LOCAL': {'slow': '#29B6F6', 'fast': '#00B0FF'},
    'DRD':      {'slow': '#FF7043', 'fast': '#FF5722'},
    'MAIL':     {'slow': '#E65100', 'fast': '#BF360C'},
    'EXPRESS':  {'slow': '#FF4081', 'fast': '#F50057'},
    'EMPTY':    {'slow': '#78909C', 'fast': '#607D8B'},
}

# 4. Color logic: 15-car-AC > 15-car > AC > FAST > category
COL_15AC  = '#00E5FF'   # 15-car AC  — bright cyan
COL_15    = '#FFD700'   # 15-car non-AC — gold
COL_AC    = '#29B6F6'   # AC 12-car  — sky blue

def is_15car(t):
    cars = str(t.get('cars', '')).strip()
    return '15' in cars

def trip_color(trip):
    car15 = is_15car(trip)
    ac    = trip.get('ac', '') == 'AC'
    if car15 and ac:   return COL_15AC
    if car15:          return COL_15
    if ac:             return COL_AC
    c = CAT_PALETTE.get(trip['cat'], CAT_PALETTE['LOCAL'])
    return c['fast'] if trip['typ'] == 'FAST' else c['slow']

def trip_badge(trip):
    """Short badge icons for overlay on bar."""
    badges = []
    if is_15car(trip): badges.append('15C')
    if trip.get('ac') == 'AC': badges.append('AC')
    return '+'.join(badges)

chart_rows = []
for lk in filtered_links:
    trips = sorted(link_trains[lk], key=lambda t: t['dep'])
    util  = utilisation(trips, t_min, t_max)
    chart_rows.append({
        'link':  lk,
        'util':  round(util, 1),
        'trips': [{
            'tr':    t['train'],
            'dep':   t['dep'],
            'arr':   t['arr'],
            'dir':   t['dir'],
            'typ':   t['typ'],
            'cat':   t['cat'],
            'from':  t['from'],
            'to':    t['to'],
            'cars':  t.get('cars', ''),
            'ac':    t.get('ac', ''),
            'col':   trip_color(t),
            'badge': trip_badge(t),
            'dur':   t['arr'] - t['dep'],
        } for t in trips]
    })

rows_json = json.dumps(chart_rows)

def hlabel(m):
    h = m // 60
    mn = m % 60
    if h < 24: return f"{h:02d}:{mn:02d}"
    return f"{h-24:02d}:{mn:02d}⁺"

htick_step = 60  # every hour
hticks = [{'m': m, 'l': hlabel(m)} for m in range(t_min, t_max + 1, htick_step)]
hticks_json = json.dumps(hticks)

# ── HTML + Canvas chart ───────────────────────────────────────────────────────
BG     = "#0f1117"
ROW_E  = "#12161e"
ROW_O  = "#0d1117"
HDR_BG = "#141824"
GRID   = "#1e2235"
GRID_H = "#252840"
LBL    = "#99aabb"
UTIL_G = "#4CAF50"
UTIL_A = "#FF7043"
MID    = "#4455aa"

CHART_H_EST = min(1400, len(filtered_links) * cell_h + 100)

html = f"""<!DOCTYPE html><html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  html,body{{background:{BG};font-family:'Segoe UI',Arial,sans-serif;overflow:hidden;height:100%;width:100%;}}
  #app{{display:flex;flex-direction:column;height:100vh;width:100%;}}
  #hdr{{flex-shrink:0;display:flex;align-items:center;gap:8px;padding:4px 10px;
        background:{HDR_BG};border-bottom:1px solid {GRID_H};font-size:11px;color:{LBL};flex-wrap:wrap;}}
  #hdr button{{background:{GRID_H};color:#ccc;border:1px solid #3a3f60;border-radius:4px;
               padding:3px 9px;font-size:11px;cursor:pointer;}}
  #hdr button:hover{{background:#3a4a70;}}
  #grid{{flex:1;display:grid;grid-template-columns:90px 1fr 72px;grid-template-rows:36px 1fr;overflow:hidden;}}
  #corner{{background:{BG};border-right:2px solid {GRID_H};border-bottom:2px solid {GRID_H};}}
  #xcanvas{{overflow:hidden;border-bottom:2px solid {GRID_H};background:{BG};}}
  #ycanvas{{overflow:hidden;border-right:2px solid {GRID_H};background:{BG};}}
  #body{{overflow:auto;position:relative;}}
  #yr{{overflow:hidden;border-left:2px solid {GRID_H};background:{BG};}}
  #yrc{{overflow:hidden;border-left:2px solid {GRID_H};background:{BG};}}
  #body::-webkit-scrollbar{{width:8px;height:8px;}}
  #body::-webkit-scrollbar-track{{background:#1a1a2e;}}
  #body::-webkit-scrollbar-thumb{{background:#3a3f60;border-radius:4px;}}
  .tip{{position:fixed;background:rgba(10,12,24,0.97);border:1px solid #445566;border-radius:7px;
        padding:8px 12px;font-size:11px;color:#eee;pointer-events:none;display:none;
        z-index:9999;line-height:1.75;min-width:190px;max-width:270px;box-shadow:0 4px 18px rgba(0,0,0,.4);}}
  @media(max-width:640px){{
    #grid{{grid-template-columns:60px 1fr;}}
    #yr,#yrc{{display:none;}}
  }}
</style>
</head><body>
<div id="app">
<div id="hdr">
  <span style="font-weight:700;color:#8899cc">🚃 Rake Link Chart</span>
  <span style="margin-left:auto">Links: <b style="color:#ddd">{total_links}</b>
  &nbsp;|&nbsp; Trips: <b style="color:#ddd">{total_trains_shown}</b>
  &nbsp;|&nbsp; Avg util: <b style="color:{UTIL_G}">{avg_util:.1f}%</b></span>
  <button id="btn-zin">＋</button>
  <span id="zval" style="min-width:38px;text-align:center;font-weight:600;color:#ddd">100%</span>
  <button id="btn-zout">－</button>
  <button id="btn-reset">Reset</button>
</div>
<div id="grid">
  <div id="corner"></div>
  <div id="xcanvas"><canvas id="cx"></canvas></div>
  <div id="corner2" style="background:{BG};border-left:2px solid {GRID_H};border-bottom:2px solid {GRID_H};"></div>
  <div id="ycanvas"><canvas id="cy"></canvas></div>
  <div id="body"><canvas id="cm"></canvas></div>
  <div id="yr"><canvas id="cyr"></canvas></div>
</div>
</div>
<div class="tip" id="tip"></div>

<script>
const ROWS    = {rows_json};
const HTICKS  = {hticks_json};
const T_MIN   = {t_min};
const T_MAX   = {t_max};
const BASE_CH = {cell_h};
const SHOW_LBL= {'true' if show_labels else 'false'};

const BG="{BG}",ROW_E="{ROW_E}",ROW_O="{ROW_O}",GRID="{GRID}",GRID_H="{GRID_H}",LBL="{LBL}";
const UTIL_G="{UTIL_G}",UTIL_A="{UTIL_A}",MID="{MID}";
const MIDNIGHT=1440;

let scale=1.0;
const cH=()=>BASE_CH*scale;
const cW=()=>Math.max(1.5, 2.0*scale);  // px per minute

const xPx=m=>(m-T_MIN)*cW();
const yPx=i=>i*cH();
const W=()=>(T_MAX-T_MIN)*cW();

const bodyDiv=document.getElementById("body");
const xDiv=document.getElementById("xcanvas");
const yDiv=document.getElementById("ycanvas");
const yrDiv=document.getElementById("yr");
const cx=document.getElementById("cx");
const cy=document.getElementById("cy");
const cm=document.getElementById("cm");
const cyr=document.getElementById("cyr");
const tip=document.getElementById("tip");
const zval=document.getElementById("zval");

bodyDiv.addEventListener("scroll",()=>{{
  xDiv.scrollLeft=bodyDiv.scrollLeft;
  yDiv.scrollTop=bodyDiv.scrollTop;
  yrDiv.scrollTop=bodyDiv.scrollTop;
}});

function dpr(){{return window.devicePixelRatio||1;}}
function setC(c,w,h){{
  const r=dpr();
  c.width=w*r; c.height=h*r;
  c.style.width=w+"px"; c.style.height=h+"px";
  const ctx=c.getContext("2d"); ctx.scale(r,r); return ctx;
}}

// ── X axis ──────────────────────────────────────────────────────────────────
function drawX(){{
  const w=W(), h=36;
  const ctx=setC(cx,w,h);
  ctx.fillStyle=BG; ctx.fillRect(0,0,w,h);
  HTICKS.forEach(t=>{{
    const xp=xPx(t.m);
    ctx.strokeStyle=GRID_H; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(xp,12); ctx.lineTo(xp,h); ctx.stroke();
    ctx.fillStyle=LBL; ctx.font="9px Arial"; ctx.textAlign="center";
    ctx.fillText(t.l, xp, h-4);
  }});
  if(MIDNIGHT>T_MIN&&MIDNIGHT<T_MAX){{
    const xm=xPx(MIDNIGHT);
    ctx.strokeStyle=MID; ctx.lineWidth=2; ctx.setLineDash([6,4]);
    ctx.beginPath(); ctx.moveTo(xm,0); ctx.lineTo(xm,h); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle=MID; ctx.font="bold 8px Arial"; ctx.textAlign="center";
    ctx.fillText("◀ 00:00 ▶",xm,h-4);
  }}
}}

// ── Y axis (link names + util bar) ──────────────────────────────────────────
function drawY(){{
  const W2=90, H=ROWS.length*cH();
  const ctx=setC(cy,W2,H);
  ctx.fillStyle=BG; ctx.fillRect(0,0,W2,H);
  ROWS.forEach((row,i)=>{{
    const y=yPx(i), h=cH();
    ctx.fillStyle=i%2===0?ROW_E:ROW_O;
    ctx.fillRect(0,y,W2,h);
    ctx.strokeStyle=GRID; ctx.lineWidth=0.4;
    ctx.beginPath(); ctx.moveTo(0,y+h); ctx.lineTo(W2,y+h); ctx.stroke();
    // Link name
    const fs=Math.max(7,Math.min(11,h*0.52));
    ctx.fillStyle="#ccddee"; ctx.font=`bold ${{fs}}px Arial`;
    ctx.textAlign="right"; ctx.textBaseline="middle";
    ctx.fillText(row.link, W2-5, y+h/2);
  }});
}}

// ── Right Y axis (utilisation % bar + label) ─────────────────────────────────
function drawYR(){{
  const W2=72, H=ROWS.length*cH();
  const ctx=setC(cyr,W2,H);
  ctx.fillStyle=BG; ctx.fillRect(0,0,W2,H);
  ROWS.forEach((row,i)=>{{
    const y=yPx(i), h=cH();
    ctx.fillStyle=i%2===0?ROW_E:ROW_O;
    ctx.fillRect(0,y,W2,h);
    ctx.strokeStyle=GRID; ctx.lineWidth=0.4;
    ctx.beginPath(); ctx.moveTo(0,y+h); ctx.lineTo(W2,y+h); ctx.stroke();
    // Util bar background
    const barW=38, barH=Math.max(4,h*0.55);
    const bx=2, by=y+(h-barH)/2;
    ctx.fillStyle="#1a2030";
    ctx.fillRect(bx,by,barW,barH);
    // Util filled portion
    const u=Math.min(row.util/100,1);
    const col=u>=0.8?UTIL_G:(u>=0.5?"#FFD700":UTIL_A);
    ctx.fillStyle=col;
    ctx.fillRect(bx,by,barW*u,barH);
    // % label
    const fs=Math.max(6,Math.min(9,h*0.45));
    ctx.fillStyle="#ddd"; ctx.font=`${{fs}}px Arial`;
    ctx.textAlign="left"; ctx.textBaseline="middle";
    ctx.fillText(`${{row.util}}%`, bx+barW+3, y+h/2);
  }});
}}

// ── Main chart ───────────────────────────────────────────────────────────────
function drawMain(){{
  const w=W(), H=ROWS.length*cH();
  const ctx=setC(cm,w,H);
  ctx.clearRect(0,0,w,H);

  // Row backgrounds
  ROWS.forEach((_,i)=>{{
    ctx.fillStyle=i%2===0?ROW_E:ROW_O;
    ctx.fillRect(0,yPx(i),w,cH());
  }});

  // Hour grid lines
  HTICKS.forEach(t=>{{
    ctx.strokeStyle=GRID_H; ctx.lineWidth=t.m%60===0?1:0.5;
    ctx.beginPath(); ctx.moveTo(xPx(t.m),0); ctx.lineTo(xPx(t.m),H); ctx.stroke();
  }});
  // Row separators
  ROWS.forEach((_,i)=>{{
    ctx.strokeStyle=GRID; ctx.lineWidth=0.4;
    ctx.beginPath(); ctx.moveTo(0,yPx(i+1)); ctx.lineTo(w,yPx(i+1)); ctx.stroke();
  }});

  // Midnight band
  if(MIDNIGHT>T_MIN&&MIDNIGHT<T_MAX){{
    const xm=xPx(MIDNIGHT);
    ctx.fillStyle="rgba(68,85,170,0.08)";
    ctx.fillRect(xPx(MIDNIGHT-15),0,30*cW(),H);
    ctx.strokeStyle=MID; ctx.lineWidth=2; ctx.setLineDash([6,4]);
    ctx.beginPath(); ctx.moveTo(xm,0); ctx.lineTo(xm,H); ctx.stroke();
    ctx.setLineDash([]);
  }}

  // Train trip bars
  const barPad = Math.max(1, cH()*0.18);
  ROWS.forEach((row,i)=>{{
    const y=yPx(i)+barPad;
    const bh=cH()-barPad*2;
    row.trips.forEach(tr=>{{
      const x1=xPx(Math.max(tr.dep,T_MIN));
      const x2=xPx(Math.min(tr.arr,T_MAX));
      if(x2<=x1) return;
      const bw=Math.max(x2-x1,2);
      // DOWN = full colour, UP = lighter (intensity differentiation)
      const isDN = tr.dir === "DOWN";
      const r=Math.min(3,bh/3);
      // Draw bar fill
      ctx.fillStyle=tr.col;
      ctx.globalAlpha= isDN ? 0.92 : 0.50;
      ctx.beginPath();
      ctx.moveTo(x1+r,y); ctx.lineTo(x1+bw-r,y);
      ctx.quadraticCurveTo(x1+bw,y,x1+bw,y+r);
      ctx.lineTo(x1+bw,y+bh-r);
      ctx.quadraticCurveTo(x1+bw,y+bh,x1+bw-r,y+bh);
      ctx.lineTo(x1+r,y+bh);
      ctx.quadraticCurveTo(x1,y+bh,x1,y+bh-r);
      ctx.lineTo(x1,y+r);
      ctx.quadraticCurveTo(x1,y,x1+r,y);
      ctx.closePath();
      ctx.fill();
      // UP trains: add diagonal stripe overlay to further distinguish
      if(!isDN){{
        ctx.save();
        ctx.clip();
        ctx.strokeStyle="rgba(255,255,255,0.18)";
        ctx.lineWidth=3;
        for(let sx=x1-bh;sx<x1+bw+bh;sx+=7){{
          ctx.beginPath();ctx.moveTo(sx,y+bh);ctx.lineTo(sx+bh,y);ctx.stroke();
        }}
        ctx.restore();
      }}
      // Solid border for UP trains to compensate for lighter fill
      ctx.strokeStyle=tr.col;
      ctx.lineWidth= isDN ? 0 : 1.2;
      ctx.globalAlpha= isDN ? 0 : 0.85;
      if(!isDN){{
        ctx.beginPath();
        ctx.moveTo(x1+r,y); ctx.lineTo(x1+bw-r,y);
        ctx.quadraticCurveTo(x1+bw,y,x1+bw,y+r);
        ctx.lineTo(x1+bw,y+bh-r);
        ctx.quadraticCurveTo(x1+bw,y+bh,x1+bw-r,y+bh);
        ctx.lineTo(x1+r,y+bh);
        ctx.quadraticCurveTo(x1,y+bh,x1,y+bh-r);
        ctx.lineTo(x1,y+r);
        ctx.quadraticCurveTo(x1,y,x1+r,y);
        ctx.closePath();
        ctx.stroke();
      }}
      ctx.globalAlpha=1;
      // Direction arrow / label + badge
      if(SHOW_LBL && bw>18){{
        const fs=Math.max(6,Math.min(9,bh*0.58));
        ctx.font=`bold ${{fs}}px Arial`;
        ctx.textAlign="center"; ctx.textBaseline="middle";
        ctx.globalAlpha=0.92;
        const arrow=tr.dir==="DOWN"?"▶":"◀";
        let lbl;
        if(bw>70) lbl=`${{tr.badge?"["+tr.badge+"] ":""}}${{tr.tr}} ${{arrow}}`;
        else if(bw>40) lbl=`${{tr.tr}} ${{arrow}}`;
        else if(bw>22) lbl=arrow;
        else lbl="";
        if(lbl){{
          ctx.fillStyle="#fff";
          ctx.fillText(lbl, x1+bw/2, y+bh/2);
        }}
        ctx.globalAlpha=1;
      }}
    }});
  }});
}}

// ── Hit-test (tooltip) ───────────────────────────────────────────────────────
let hitBoxes=[];
function buildHits(){{
  hitBoxes=[];
  const barPad=Math.max(1,cH()*0.18);
  ROWS.forEach((row,i)=>{{
    const y=yPx(i)+barPad;
    const bh=cH()-barPad*2;
    row.trips.forEach(tr=>{{
      const x1=xPx(Math.max(tr.dep,T_MIN));
      const x2=xPx(Math.min(tr.arr,T_MAX));
      if(x2<=x1) return;
      const fmt=m=>{{const h=Math.floor(m/60),mn=m%60;return h>=24?String(h-24).padStart(2,'0')+':'+String(mn).padStart(2,'0')+'\u207a':String(h).padStart(2,'0')+':'+String(mn).padStart(2,'0');}}

      const acTag=tr.ac==="AC"?' <b style="color:#29B6F6">[AC]</b>':'';

      const carTag=tr.cars?' <span style="color:#FFD700">'+tr.cars+'</span>':'';

      const dirCol=tr.dir==="DOWN"?'#88ee88':'#ee9966';

      hitBoxes.push({{

        x:x1, y, w:Math.max(x2-x1,6), h:bh,

        html:'<span style="font-size:13px;font-weight:700;color:'+tr.col+'">'+tr.tr+'</span>'+acTag+carTag

             +' <span style="color:'+dirCol+';margin-left:5px">'+tr.dir+'</span><br>'

             +'<span style="color:#88ccff">↓ DEP: <b>'+fmt(tr.dep)+'</b></span>'

             +'&nbsp;&nbsp;<span style="color:#88ccff">↑ ARR: <b>'+fmt(tr.arr)+'</b></span><br>'

             +'Duration: <b style="color:#ffdd99">'+tr.dur+' min ('+Math.round(tr.dur/60*10)/10+' hrs)</b><br>'

             +'Route: <b>'+tr.from+'</b> → <b>'+tr.to+'</b><br>'

             +'Type: <span style="color:#aaa">'+tr.typ+'</span>'

             +'&nbsp;|&nbsp;Cat: <span style="color:'+tr.col+'">'+tr.cat+'</span>'

      }});


    }});
  }});
}}

// Mouse events on body canvas
cm.addEventListener("mousemove",e=>{{
  const rect=cm.getBoundingClientRect();
  // getBoundingClientRect() already includes scroll offset — do NOT add scrollLeft/Top again
  const mx=e.clientX-rect.left;
  const my=e.clientY-rect.top;
  const hit=hitBoxes.find(b=>mx>=b.x&&mx<=b.x+b.w&&my>=b.y&&my<=b.y+b.h);
  if(hit){{
    tip.style.display="block";
    tip.innerHTML=hit.html;
    tip.style.left=(e.clientX+14)+"px";
    tip.style.top=(e.clientY-10)+"px";
  }} else {{
    tip.style.display="none";
  }}
}});
cm.addEventListener("mouseleave",()=>tip.style.display="none");

// ── Zoom ─────────────────────────────────────────────────────────────────────
document.getElementById("btn-zin").onclick=()=>{{scale=Math.min(8,scale*1.3);renderAll();}};
document.getElementById("btn-zout").onclick=()=>{{scale=Math.max(0.2,scale/1.3);renderAll();}};
document.getElementById("btn-reset").onclick=()=>{{scale=1.0;renderAll();}};
bodyDiv.addEventListener("wheel",e=>{{
  if(!e.ctrlKey&&!e.metaKey) return;
  e.preventDefault();
  scale=e.deltaY<0?Math.min(8,scale*1.15):Math.max(0.2,scale/1.15);
  renderAll();
}},{{passive:false}});

function renderAll(){{
  zval.textContent=Math.round(scale*100)+"%";
  drawX(); drawY(); drawYR(); drawMain(); buildHits();
}}
renderAll();
</script>
</body></html>"""

st.components.v1.html(html, height=min(1300, len(filtered_links) * cell_h + 140), scrolling=False)

st.markdown("---")
st.markdown("### Link Summary Table")

rows_tbl = []
for lk in filtered_links:
    trips = sorted(link_trains[lk], key=lambda t: t['dep'])
    util  = utilisation(trips, t_min, t_max)
    n_dn  = sum(1 for t in trips if t['dir'] == 'DOWN')
    n_up  = sum(1 for t in trips if t['dir'] == 'UP')
    types = sorted(set(t['typ'] for t in trips))
    dep0  = trips[0]['dep'] if trips else 0
    arrN  = trips[-1]['arr'] if trips else 0
    rows_tbl.append({
        'Link':        lk,
        'Trains':      len(trips),
        'DOWN':        n_dn,
        'UP':          n_up,
        'Type(s)':     '/'.join(types),
        'First Dep':   f"{dep0//60:02d}:{dep0%60:02d}",
        'Last Arr':    f"{arrN//60 % 24:02d}:{arrN%60:02d}" + ("⁺" if arrN >= 1440 else ""),
        'Util %':      f"{util:.1f}%",
    })

import pandas as pd
df = pd.DataFrame(rows_tbl)
st.dataframe(df, use_container_width=True, height=350)
st.download_button("⬇️ Download CSV", df.to_csv(index=False), "rake_link_summary.csv", "text/csv")
