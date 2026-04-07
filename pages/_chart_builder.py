"""
Shared canvas chart builder for Marey/Line Capacity charts.
Returns an HTML string with full frozen-axis canvas chart.
"""
import json
from collections import defaultdict

# ── Colour constants passed in from caller ────────────────────────────────────
def build_chart_html(
    *,
    lines_json: str,
    dwells_json: str,
    conflicts_json: str = "[]",
    stns_json: str,
    halt_json: str,
    hticks_json: str,
    cat_col_json: str,
    cat_label_json: str,
    t_min: int,
    t_max: int,
    cell_h: int,
    cell_w: int,
    show_labels: bool,
    label_min_gap: int,
    print_mode: bool,
    conflict_gap: int = 6,
    chart_title: str = "",
    chart_id: str = "chart",
    show_minute_markers: bool = True,
    car15_json: str = "[]",
    highlight_train: str = "",
) -> str:

    midnight = 24 * 60

    if print_mode:
        BG="#fff"; ROW_E="#f8f8f8"; ROW_O="#fff"; ROW_HALT="#fffaee"
        HOUR_MAJ="#bbbbcc"; HOUR_MIN="#e5e5e5"; HOUR_LBL="#444"
        STN_LBL="#111"; STN_HALT="#7B5800"
        MID_LINE="#7777bb"; MID_LBL="#5555aa"; MID_BAND="#eeeeff"
        TIP_BG="rgba(240,240,250,0.98)"; TIP_BD="#aaa"; TIP_FG="#111"
        TICK_10="#888888"; TICK_5="#bbbbbb"; TICK_1="#dddddd"
    else:
        BG="#0f1117"; ROW_E="#12161e"; ROW_O="#0d1117"; ROW_HALT="#1a1a10"
        HOUR_MAJ="#252840"; HOUR_MIN="#181b28"; HOUR_LBL="#5566aa"
        STN_LBL="#ccddee"; STN_HALT="#FFD700"
        MID_LINE="#4455aa"; MID_LBL="#8899cc"; MID_BAND="#1a1830"
        TIP_BG="rgba(12,14,26,0.97)"; TIP_BD="#445566"; TIP_FG="#eee"
        TICK_10="#445566"; TICK_5="#2a3040"; TICK_1="#1a1e28"

    SHOW_LABELS_JS = "true" if show_labels else "false"
    SHOW_MARKERS_JS = "true" if show_minute_markers else "false"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  html,body{{width:100%;height:100%;background:{BG};font-family:'Segoe UI',Arial,sans-serif;overflow:hidden;}}
  #app-{chart_id}{{display:flex;flex-direction:column;width:100%;height:100vh;}}
  #toolbar-{chart_id}{{
    flex-shrink:0;display:flex;align-items:center;gap:7px;flex-wrap:wrap;
    padding:4px 10px;
    background:{'#f0f0f0' if print_mode else '#141824'};
    border-bottom:1px solid {'#ccc' if print_mode else '#252840'};
    font-size:11px;color:{'#333' if print_mode else '#99aabb'};
  }}
  #toolbar-{chart_id} button{{
    background:{'#ddd' if print_mode else '#252840'};
    color:{'#111' if print_mode else '#ccc'};
    border:1px solid {'#bbb' if print_mode else '#3a3f60'};
    border-radius:4px;padding:3px 9px;font-size:11px;cursor:pointer;
  }}
  #toolbar-{chart_id} button:hover{{background:{'#bbb' if print_mode else '#3a4a70'};}}
  #zoom-val-{chart_id}{{min-width:38px;text-align:center;font-weight:600;color:{'#333' if print_mode else '#ddd'};}}
  #chart-area-{chart_id}{{
    flex:1;display:grid;
    grid-template-columns:92px 1fr 72px;
    grid-template-rows:auto 34px 1fr auto;
    overflow:hidden;
  }}
  #corner-{chart_id}{{background:{BG};border-right:2px solid {'#ccc' if print_mode else '#252840'};border-bottom:2px solid {'#ccc' if print_mode else '#252840'};grid-row:2;grid-column:1;}}
  #x-axis-{chart_id}{{overflow:hidden;border-bottom:2px solid {'#ccc' if print_mode else '#252840'};background:{BG};grid-row:2;grid-column:2;}}
  #y-axis-{chart_id}{{overflow:hidden;border-right:2px solid {'#ccc' if print_mode else '#252840'};background:{BG};grid-row:3;grid-column:1;}}
  #body-{chart_id}{{overflow:auto;grid-row:3;grid-column:2;}}
  #y-axis-right-{chart_id}{{overflow:hidden;border-left:2px solid {'#ccc' if print_mode else '#252840'};background:{BG};grid-row:3;grid-column:3;}}
  #corner-right-{chart_id}{{background:{BG};border-left:2px solid {'#ccc' if print_mode else '#252840'};grid-row:2;grid-column:3;}}
  /* Top strip: DOWN train labels (vertically oriented, above X-axis) */
  #top-labels-{chart_id}{{
    overflow:hidden;grid-row:1;grid-column:2;
    background:{BG};
    border-bottom:1px solid {'#ddd' if print_mode else '#1a1e2e'};
  }}
  /* Bottom strip: UP train labels (vertically oriented, below chart body) */
  #bot-corner-{chart_id}{{background:{BG};grid-row:4;grid-column:1;}}
  #bot-labels-{chart_id}{{
    overflow:hidden;grid-row:4;grid-column:2;
    background:{BG};
    border-top:1px solid {'#ddd' if print_mode else '#1a1e2e'};
  }}
  #body-{chart_id}::-webkit-scrollbar{{width:8px;height:8px;}}
  #body-{chart_id}::-webkit-scrollbar-track{{background:{'#eee' if print_mode else '#1a1a2e'};}}
  #body-{chart_id}::-webkit-scrollbar-thumb{{background:{'#bbb' if print_mode else '#3a3f60'};border-radius:4px;}}
  .tip-{chart_id}{{
    position:fixed;background:{TIP_BG};border:1px solid {TIP_BD};border-radius:7px;
    padding:8px 12px;font-size:11px;color:{TIP_FG};pointer-events:none;display:none;
    z-index:9999;line-height:1.75;min-width:190px;max-width:280px;
    box-shadow:0 4px 18px rgba(0,0,0,.35);
  }}
  @media print{{
    #toolbar-{chart_id}{{display:none!important;}}
    html,body{{overflow:visible!important;height:auto!important;}}
    #app-{chart_id}{{height:auto!important;}}
    #chart-area-{chart_id}{{display:block!important;overflow:visible!important;}}
    #corner-{chart_id},#x-axis-{chart_id},#y-axis-{chart_id}{{display:none!important;}}
    #body-{chart_id}{{overflow:visible!important;}}
  }}
</style></head><body>
<div id="app-{chart_id}">
  <div id="toolbar-{chart_id}">
    {"<span style='font-weight:700;font-size:12px;color:"+(MID_LBL)+"'>"+chart_title+"</span>" if chart_title else ""}
    <div style="margin-left:auto;display:flex;align-items:center;gap:6px;">
      Zoom:
      <button id="btn-zout-{chart_id}">－</button>
      <span id="zoom-val-{chart_id}">100%</span>
      <button id="btn-zin-{chart_id}">＋</button>
      <button id="btn-reset-{chart_id}">Reset</button>
      <button id="btn-fs-{chart_id}" style="margin-left:3px">Fullscreen</button>
      <button onclick="window.print()" style="margin-left:6px">🖨️ Print</button>
      <button id="btn-png-{chart_id}">PNG</button>
      <button id="btn-svg-{chart_id}">SVG</button>
    </div>
  </div>
  <div id="chart-area-{chart_id}">
    <div id="top-labels-{chart_id}"><canvas id="ctop-{chart_id}"></canvas></div>
    <div id="corner-{chart_id}"></div>
    <div id="x-axis-{chart_id}"><canvas id="cx-{chart_id}"></canvas></div>
    <div id="y-axis-{chart_id}"><canvas id="cy-{chart_id}"></canvas></div>
    <div id="body-{chart_id}" style="position:relative;"><canvas id="cm-{chart_id}"></canvas><canvas id="cov-{chart_id}" style="position:absolute;top:0;left:0;pointer-events:none;"></canvas></div>
    <div id="corner-right-{chart_id}"></div>
    <div id="y-axis-right-{chart_id}"><canvas id="cyr-{chart_id}"></canvas></div>
    <div id="corner-right-{chart_id}"></div>
    <div id="y-axis-right-{chart_id}"><canvas id="cyr-{chart_id}"></canvas></div>
    <div id="bot-corner-{chart_id}"></div>
    <div id="bot-labels-{chart_id}"><canvas id="cbot-{chart_id}"></canvas></div>
  </div>
</div>
<div class="tip-{chart_id}" id="tip-{chart_id}"></div>

<script>
(function(){{
const CID="{chart_id}";
const RAW_LINES  = {lines_json};
const RAW_DWELLS = {dwells_json};
const CONFLICTS  = {conflicts_json};
const CAR15_TRAINS = {car15_json};
const STNS       = {stns_json};
const HALTS      = new Set({halt_json});
const HTICKS     = {hticks_json};
const CAT_COL    = {cat_col_json};
const CAT_LABEL  = {cat_label_json};
const T_MIN={t_min}, T_MAX={t_max}, MIDNIGHT={midnight};
const BASE_CH={cell_h}, BASE_CW={cell_w};
const SHOW_LABELS={SHOW_LABELS_JS};
const LABEL_MIN_GAP={label_min_gap};
const SHOW_MARKERS={SHOW_MARKERS_JS};
const CONFLICT_GAP={conflict_gap};
const HIGHLIGHT_TR="{highlight_train}";

// Colours
const ROW_E="{ROW_E}",ROW_O="{ROW_O}",ROW_HALT="{ROW_HALT}";
const HOUR_MAJ="{HOUR_MAJ}",HOUR_MIN="{HOUR_MIN}",HOUR_LBL="{HOUR_LBL}";
const STN_LBL="{STN_LBL}",STN_HALT="{STN_HALT}";
const MID_LINE="{MID_LINE}",MID_LBL="{MID_LBL}",MID_BAND="{MID_BAND}";
const BG="{BG}";
const TICK_10="{TICK_10}",TICK_5="{TICK_5}",TICK_1="{TICK_1}";
const PRINT={'true' if print_mode else 'false'};

let scale=1.0;
const cH=()=>BASE_CH*scale, cW=()=>BASE_CW*scale;
const dR=()=>Math.max(1.4, BASE_CH*0.075*scale);
const dwH_=()=>Math.max(3, BASE_CH*0.30*scale);
const xPx=m=>(m-T_MIN)*cW(), yPx=i=>i*cH();
const COLOR_15CAR = "{'#FFD700' if not print_mode else '#AA7700'}";   // gold for 15-car
// CAR15_SET: set of train numbers that are 15-car (populated below)
const CAR15_SET = new Set(CAR15_TRAINS);

function lCol(cat,typ,tr){{
  if(CAR15_SET.has(tr)) return COLOR_15CAR;
  const c=CAT_COL[cat]||CAT_COL['LOCAL'];
  return typ==="FAST"?c.fast:c.slow;
}}
function lW(typ,tr){{
  const base = CAR15_SET.has(tr) ? 2.6 : (typ==="FAST"?2.2:1.4);
  return base*scale;
}}

const bodyDiv=document.getElementById("body-"+CID);
const xDiv=document.getElementById("x-axis-"+CID);
const yDiv=document.getElementById("y-axis-"+CID);
const topDiv=document.getElementById("top-labels-"+CID);
const botDiv=document.getElementById("bot-labels-"+CID);
const cm=document.getElementById("cm-"+CID);
const cx=document.getElementById("cx-"+CID);
const cy=document.getElementById("cy-"+CID);
const cyr=document.getElementById("cyr-"+CID);
const cov=document.getElementById("cov-"+CID);
const yrDiv=document.getElementById("y-axis-right-"+CID);
const ctop=document.getElementById("ctop-"+CID);
const cbot=document.getElementById("cbot-"+CID);
const tip=document.getElementById("tip-"+CID);
const zoomLbl=document.getElementById("zoom-val-"+CID);

bodyDiv.addEventListener("scroll",()=>{{
  xDiv.scrollLeft   = bodyDiv.scrollLeft;
  yDiv.scrollTop    = bodyDiv.scrollTop;
  yrDiv.scrollTop   = bodyDiv.scrollTop;
  topDiv.scrollLeft = bodyDiv.scrollLeft;
  botDiv.scrollLeft = bodyDiv.scrollLeft;
}});

function setC(c,w,h){{
  const d=window.devicePixelRatio||1;
  c.width=w*d; c.height=h*d;
  c.style.width=w+"px"; c.style.height=h+"px";
  const ctx=c.getContext("2d");
  ctx.scale(d,d);
  return ctx;
}}

// ── Draw X axis (time ruler) ──────────────────────────────────────────────────
function drawX(){{
  const W=(T_MAX-T_MIN)*cW(), H=34;
  const ctx=setC(cx,W,H);
  ctx.fillStyle=BG; ctx.fillRect(0,0,W,H);

  // ── Minute tick marks on top of x-axis ──
  if(SHOW_MARKERS && cW()>=1){{
    for(let m=T_MIN;m<=T_MAX;m++){{
      const xp=xPx(m);
      const mod10=m%10===0, mod5=m%5===0;
      if(mod10){{
        // 10-min mark: bigger, distinct colour
        ctx.strokeStyle=TICK_10; ctx.lineWidth=1.5;
        ctx.beginPath(); ctx.moveTo(xp,0); ctx.lineTo(xp,10); ctx.stroke();
        // dot on top
        ctx.fillStyle=TICK_10;
        ctx.beginPath(); ctx.arc(xp,2.5,PRINT?2:2.5,0,Math.PI*2); ctx.fill();
      }} else if(mod5){{
        // 5-min mark: medium
        ctx.strokeStyle=TICK_5; ctx.lineWidth=1;
        ctx.beginPath(); ctx.moveTo(xp,0); ctx.lineTo(xp,7); ctx.stroke();
        ctx.fillStyle=TICK_5;
        ctx.beginPath(); ctx.arc(xp,2,1.5,0,Math.PI*2); ctx.fill();
      }} else if(cW()>=2){{
        // 1-min mark: subtle tick only
        ctx.strokeStyle=TICK_1; ctx.lineWidth=0.5;
        ctx.beginPath(); ctx.moveTo(xp,0); ctx.lineTo(xp,4); ctx.stroke();
      }}
    }}
  }}

  // Hour grid labels
  HTICKS.forEach(t=>{{
    const xp=xPx(t.m);
    ctx.strokeStyle=HOUR_MAJ; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(xp,10); ctx.lineTo(xp,H); ctx.stroke();
    ctx.fillStyle=HOUR_LBL; ctx.font="9px Arial"; ctx.textAlign="center";
    ctx.fillText(t.l, xp, H-5);
  }});

  // Midnight marker
  if(MIDNIGHT>T_MIN && MIDNIGHT<T_MAX){{
    const xm=xPx(MIDNIGHT);
    ctx.strokeStyle=MID_LINE; ctx.lineWidth=2.5;
    ctx.setLineDash([7,4]);
    ctx.beginPath(); ctx.moveTo(xm,0); ctx.lineTo(xm,H); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle=MID_LBL; ctx.font="bold 9px Arial"; ctx.textAlign="center";
    ctx.fillText("◀ MIDNIGHT ▶", xm, H-5);
  }}
}}

// ── Draw Y axis (station ruler) ───────────────────────────────────────────────
function drawY(){{
  const W=92, H=STNS.length*cH();
  const ctx=setC(cy,W,H);
  STNS.forEach((stn,i)=>{{
    const isH=HALTS.has(stn), y=yPx(i);
    ctx.fillStyle=isH?ROW_HALT:(i%2===0?ROW_E:ROW_O);
    ctx.fillRect(0,y,W,cH());
    ctx.strokeStyle=HOUR_MAJ; ctx.lineWidth=0.5;
    ctx.beginPath(); ctx.moveTo(0,y+cH()); ctx.lineTo(W,y+cH()); ctx.stroke();
    const fs=Math.max(7,Math.min(11,cH()*0.52));
    ctx.fillStyle=isH?STN_HALT:STN_LBL;
    ctx.font=`${{isH?"bold ":""}}${{fs}}px Arial`;
    ctx.textAlign="right"; ctx.textBaseline="middle";
    ctx.fillText(isH?"★ "+stn:stn, W-5, y+cH()/2);
  }});
}}


// ── Draw right Y axis (mirrored station labels) ───────────────────────────────
function drawYR(){{
  const W=72, H=STNS.length*cH();
  const ctx=setC(cyr,W,H);
  STNS.forEach((stn,i)=>{{
    const isH=HALTS.has(stn), y=yPx(i);
    ctx.fillStyle=isH?ROW_HALT:(i%2===0?ROW_E:ROW_O);
    ctx.fillRect(0,y,W,cH());
    ctx.strokeStyle=HOUR_MAJ; ctx.lineWidth=0.5;
    ctx.beginPath(); ctx.moveTo(0,y+cH()); ctx.lineTo(W,y+cH()); ctx.stroke();
    const fs=Math.max(7,Math.min(11,cH()*0.52));
    ctx.fillStyle=isH?STN_HALT:STN_LBL;
    ctx.font=`${{isH?"bold ":""}}${{fs}}px Arial`;
    ctx.textAlign="left"; ctx.textBaseline="middle";
    ctx.fillText(isH?"* "+stn:stn, 5, y+cH()/2);
  }});
}}

// ── Draw main chart canvas ────────────────────────────────────────────────────
function drawMain(){{
  const W=(T_MAX-T_MIN)*cW(), H=STNS.length*cH();
  const ctx=setC(cm,W,H);
  ctx.clearRect(0,0,W,H);

  // Row backgrounds
  STNS.forEach((_,i)=>{{
    ctx.fillStyle=HALTS.has(STNS[i])?ROW_HALT:(i%2===0?ROW_E:ROW_O);
    ctx.fillRect(0,yPx(i),W,cH());
  }});

  // ── Vertical minute tick marks (1-min, 5-min, 10-min) ──
  if(SHOW_MARKERS){{
    for(let m=T_MIN;m<=T_MAX;m++){{
      const xp=xPx(m);
      const mod10=m%10===0, mod5=m%5===0;
      // Full-height vertical line at each tick mark position
      if(mod10){{
        ctx.strokeStyle=TICK_10; ctx.lineWidth=0.8; ctx.setLineDash([]);
        ctx.beginPath(); ctx.moveTo(xp,0); ctx.lineTo(xp,H); ctx.stroke();
      }} else if(mod5 && cW()>=1.5){{
        ctx.strokeStyle=TICK_5; ctx.lineWidth=0.5; ctx.setLineDash([2,3]);
        ctx.beginPath(); ctx.moveTo(xp,0); ctx.lineTo(xp,H); ctx.stroke();
        ctx.setLineDash([]);
      }}
    }}
  }}

  // 30-min minor grey lines
  for(let m=Math.ceil(T_MIN/30)*30; m<T_MAX; m+=30){{
    if(m%60!==0){{
      ctx.strokeStyle=HOUR_MIN; ctx.lineWidth=0.6; ctx.setLineDash([2,4]);
      ctx.beginPath(); ctx.moveTo(xPx(m),0); ctx.lineTo(xPx(m),H); ctx.stroke();
      ctx.setLineDash([]);
    }}
  }}
  // Hour major lines
  HTICKS.forEach(t=>{{
    ctx.strokeStyle=HOUR_MAJ; ctx.lineWidth=1.1;
    ctx.beginPath(); ctx.moveTo(xPx(t.m),0); ctx.lineTo(xPx(t.m),H); ctx.stroke();
  }});
  // Row separators
  STNS.forEach((_,i)=>{{
    ctx.strokeStyle=HOUR_MAJ; ctx.lineWidth=0.4;
    ctx.beginPath(); ctx.moveTo(0,yPx(i+1)); ctx.lineTo(W,yPx(i+1)); ctx.stroke();
  }});

  // ── Minute reference dots on station rows ──
  // Top, 1/3, 2/3, bottom of each row at every minute
  if(SHOW_MARKERS && cW()>=1.5){{
    const rowFracs=[0.04, 0.34, 0.67, 0.96];  // top, 1/3, 2/3, bottom
    for(let m=T_MIN;m<=T_MAX;m++){{
      const xp=xPx(m);
      const mod10=m%10===0, mod5=m%5===0;
      if(!mod10 && !mod5 && cW()<3) continue; // skip 1-min dots if zoomed out
      const dotR= mod10?2.2:(mod5?1.5:0.8);
      const dotCol= mod10?TICK_10:(mod5?TICK_5:TICK_1);
      ctx.fillStyle=dotCol;
      STNS.forEach((_,i)=>{{
        rowFracs.forEach(frac=>{{
          ctx.beginPath();
          ctx.arc(xp, yPx(i)+cH()*frac, dotR*scale, 0, Math.PI*2);
          ctx.fill();
        }});
      }});
    }}
  }}

  // Midnight band
  if(MIDNIGHT>T_MIN && MIDNIGHT<T_MAX){{
    const xm=xPx(MIDNIGHT);
    ctx.fillStyle=MID_BAND; ctx.globalAlpha=0.5;
    ctx.fillRect(xPx(MIDNIGHT-15),0,30*cW(),H); ctx.globalAlpha=1;
    ctx.strokeStyle=MID_LINE; ctx.lineWidth=2.5; ctx.setLineDash([7,4]);
    ctx.beginPath(); ctx.moveTo(xm,0); ctx.lineTo(xm,H); ctx.stroke();
    ctx.setLineDash([]);
  }}

  // ── Conflict zones ──
  CONFLICTS.forEach(c=>{{
    if(c.x1<T_MIN || c.x2>T_MAX) return;
    const xi1=xPx(c.x1), xi2=xPx(c.x2);
    const y_=yPx(c.y), h_=cH();
    const sev=c.gap<=CONFLICT_GAP/2;
    const fc=sev?"255,60,60":"255,160,0";
    ctx.fillStyle=`rgba(${{fc}},${{sev?0.40:0.20}})`;
    ctx.fillRect(xi1,y_,Math.max(xi2-xi1,4),h_);
    ctx.strokeStyle=`rgba(${{fc}},0.85)`; ctx.lineWidth=1.5;
    [xi1,xi2].forEach(xp=>{{
      ctx.beginPath(); ctx.moveTo(xp,y_+2); ctx.lineTo(xp,y_+h_-2); ctx.stroke();
    }});
    if(xi2-xi1>14){{
      ctx.fillStyle=`rgba(${{fc}},1)`;
      ctx.font=`bold ${{Math.max(7,Math.min(9,h_*0.44))}}px Arial`;
      ctx.textAlign="center"; ctx.textBaseline="middle";
      ctx.fillText(c.gap+"m",(xi1+xi2)/2,y_+h_/2);
    }}
  }});

  // ── Halt station dots (KLV / PLG / BOR / VGN) ───────────────────────────
  // The horizontal segment (arr→dep) is drawn by the polyline in RAW_LINES
  // because dwell stops are expanded to TWO coords: [arr_min,y] then [dep_min,y].
  // Here we only draw the distinguishing dots and optional time labels.
  //
  // Conventions matching the sketch:
  //   dwell  → filled ● at ARR  +  hollow ○ at DEP  +  labels
  //   dep    → hollow ○ at DEP
  //   arr    → filled ● at ARR
  //   pass   → filled ● (same as normal stop, line passes through)
  RAW_DWELLS.forEach(d=>{{
    const [tr,yi,dir,typ,stp,x1r,x2r,at,dt,cat]=d;
    if(yi===undefined || yi>=STNS.length) return;

    const col   = lCol(cat||'LOCAL', typ);
    const cy_   = yPx(yi) + cH()/2;
    const dotR_ = Math.max(2.8, dR() * 1.6);   // noticeably bigger than normal dots
    const lblSz = Math.max(6, Math.min(8, cH() * 0.38));
    const inWin = m => m !== undefined && m >= T_MIN && m <= T_MAX;

    // ── Helper: draw filled dot ────────────────────────────────────────
    function filledDot(xm, label){{
      if(!inWin(xm)) return;
      const xp = xPx(xm);
      ctx.fillStyle = col; ctx.globalAlpha = 1;
      ctx.beginPath(); ctx.arc(xp, cy_, dotR_, 0, Math.PI*2); ctx.fill();
      ctx.globalAlpha = 1;
      if(label && cH() >= 20){{
        ctx.fillStyle = col; ctx.globalAlpha = 0.92;
        ctx.font = `bold ${{lblSz}}px Arial`;
        ctx.textAlign = "center"; ctx.textBaseline = "bottom";
        ctx.fillText(label, xp, cy_ - dotR_ - 1);
        ctx.globalAlpha = 1;
      }}
    }}

    // ── Helper: draw hollow dot ────────────────────────────────────────
    function hollowDot(xm, label){{
      if(!inWin(xm)) return;
      const xp = xPx(xm);
      // Outer ring
      ctx.strokeStyle = col; ctx.lineWidth = Math.max(1.6, dotR_*0.44);
      ctx.globalAlpha = 1;
      ctx.beginPath(); ctx.arc(xp, cy_, dotR_, 0, Math.PI*2); ctx.stroke();
      // Small filled centre so it's visible
      ctx.fillStyle = col; ctx.globalAlpha = 0.5;
      ctx.beginPath(); ctx.arc(xp, cy_, dotR_*0.35, 0, Math.PI*2); ctx.fill();
      ctx.globalAlpha = 1;
      if(label && cH() >= 20){{
        ctx.fillStyle = col; ctx.globalAlpha = 0.92;
        ctx.font = `bold ${{lblSz}}px Arial`;
        ctx.textAlign = "center"; ctx.textBaseline = "bottom";
        ctx.fillText(label, xp, cy_ - dotR_ - 1);
        ctx.globalAlpha = 1;
      }}
    }}

    // ── Helper: draw time text below dot ──────────────────────────────
    function timeText(xm, txt, align){{
      if(!inWin(xm) || !txt || cH() < 24) return;
      const xp = xPx(xm);
      ctx.fillStyle = col; ctx.globalAlpha = 0.82;
      ctx.font = `${{lblSz}}px Arial`;
      ctx.textAlign = align; ctx.textBaseline = "top";
      const offset = align==="left" ? dotR_+2 : -(dotR_+2);
      ctx.fillText(txt, xp + offset, cy_ + dotR_ + 1);
      ctx.globalAlpha = 1;
    }}

    if(stp === "dwell"){{
      // Filled ● at ARR (train arrives), hollow ○ at DEP (train departs)
      filledDot(x1r, "A");
      hollowDot(x2r, "D");
      timeText(x1r, at, "left");
      timeText(x2r, dt, "right");

    }} else if(stp === "dep"){{
      // Only departure known → hollow ○
      hollowDot(x2r, "D");
      timeText(x2r, dt, "left");

    }} else if(stp === "arr"){{
      // Only arrival known → filled ●
      filledDot(x1r, "A");
      timeText(x1r, at, "left");

    }} else {{
      // Pass-through → plain filled dot (same as regular stop)
      filledDot(x1r, null);
    }}
  }});

  // ── Train lines ──
  const labelSize=Math.max(5,Math.min(9,cH()*0.44));

  RAW_LINES.forEach(l=>{{
    const [tr,dir,typ,cat,ac,fr,to,pts]=l;
    if(!pts||pts.length<1) return;
    const col=lCol(cat,typ,tr);
    const lw_=lW(typ,tr);
    const is15=CAR15_SET.has(tr);
    const opacity=typ==="FAST"?0.90:0.80;

    // ── Draw the full polyline (diagonal + horizontal halt segments) ──
    if(is15) {{ ctx.setLineDash([6,3]); }} else {{ ctx.setLineDash([]); }}
    ctx.strokeStyle=col; ctx.lineWidth=Math.max(0.5,lw_); ctx.globalAlpha=opacity;
    if(pts.length>1){{
      ctx.beginPath();
      ctx.moveTo(xPx(pts[0][0]), yPx(pts[0][1])+cH()/2);
      for(let i=1;i<pts.length;i++)
        ctx.lineTo(xPx(pts[i][0]), yPx(pts[i][1])+cH()/2);
      ctx.stroke();
    }}
    ctx.setLineDash([]);
    ctx.globalAlpha=1;

    // ── Re-draw horizontal halt segments with THICKER line ──
    const haltLW = Math.max(lw_*2.2, 3.0);
    ctx.strokeStyle=col; ctx.lineWidth=haltLW; ctx.globalAlpha=opacity;
    for(let i=1; i<pts.length; i++){{
      if(pts[i][1] === pts[i-1][1]){{
        const x1=xPx(pts[i-1][0]), x2=xPx(pts[i][0]);
        const cy_=yPx(pts[i][1])+cH()/2;
        ctx.beginPath(); ctx.moveTo(x1, cy_); ctx.lineTo(x2, cy_); ctx.stroke();
      }}
    }}
    ctx.globalAlpha=1;

    // ── Stop dots (skip halt-station positions — drawn by RAW_DWELLS) ──
    ctx.fillStyle=col; ctx.globalAlpha=0.90;
    for(let i=0;i<pts.length;i++){{
      const isHaltDep = i>0 && pts[i][1]===pts[i-1][1];
      const isHaltArr = i<pts.length-1 && pts[i][1]===pts[i+1][1];
      if(isHaltDep || isHaltArr) continue;
      ctx.beginPath();
      ctx.arc(xPx(pts[i][0]), yPx(pts[i][1])+cH()/2, dR(), 0, Math.PI*2);
      ctx.fill();
    }}
    ctx.globalAlpha=1;
  }});
}}

// ── Draw train labels in top strip (DOWN) and bottom strip (UP) ───────────
// Labels are vertical (rotated -90°), red, non-overlapping
// DOWN: above top X-axis border, positioned at first visible stop x
// UP:   below bottom chart border, positioned at last visible stop x
function drawLabels(){{
  const W        = (T_MAX-T_MIN)*cW();
  const LABEL_H  = Math.max(120, Math.min(180, scale*130)); // strip height increased for full labels
  const LSIZE    = Math.max(7,  Math.min(11, scale*9));    // font size
  const LABEL_COL= PRINT ? "#cc0000" : "#FF3333";          // red (darker on white)
  const MIN_GAP  = Math.max(LSIZE+3, 14);                  // min px between labels
  const PAD      = 4;                                       // padding from chart border

  function setSC(canvas, w, h){{
    const dpr=window.devicePixelRatio||1;
    canvas.width=w*dpr; canvas.height=h*dpr;
    canvas.style.width=w+"px"; canvas.style.height=h+"px";
    const ctx=canvas.getContext("2d");
    ctx.scale(dpr,dpr);
    return ctx;
  }}

  const ctxTop = setSC(ctop, W, LABEL_H);
  const ctxBot = setSC(cbot, W, LABEL_H);
  const ctxM = cm.getContext("2d");
  topDiv.style.height = LABEL_H + "px";
  botDiv.style.height = LABEL_H + "px";
  ctxTop.clearRect(0,0,W,LABEL_H);
  ctxBot.clearRect(0,0,W,LABEL_H);

  // Collect DOWN and UP label anchors
  const downLabels = [];
  const upLabels   = [];

  RAW_LINES.forEach(l=>{{
    const [tr,dir,typ,cat,ac,fr,to,pts]=l;
    if(!pts||pts.length<1) return;
    const visiblePts = pts.filter(p=>p[0]>=T_MIN && p[0]<=T_MAX);
    if(visiblePts.length===0) return;

    if(dir==="DOWN"){{
      const p = visiblePts[0];
      const col = lCol(cat, typ, tr);
      downLabels.push({{x: xPx(p[0]), y: yPx(p[1])+cH()/2, label: tr, col: col}});
    }} else if(dir==="UP"){{
      const p = visiblePts[0]; // attach to first station stop
      const col = lCol(cat, typ, tr);
      upLabels.push({{x: xPx(p[0]), y: yPx(p[1])+cH()/2, label: tr, col: col}});
    }}
  }});

  downLabels.sort((a,b)=>a.x-b.x);
  upLabels.sort((a,b)=>a.x-b.x);

  function relaxLabels(labels, gap) {{
    let changed = true;
    let iters = 0;
    while(changed && iters < 20) {{
      changed = false;
      for(let i=0; i<labels.length-1; i++) {{
         let diff = labels[i+1].lx - labels[i].lx;
         if(diff < gap) {{
            let overlap = gap - diff;
            labels[i].lx -= overlap / 2.0;    // push left
            labels[i+1].lx += overlap / 2.0;  // push right
            changed = true;
         }}
      }}
      iters++;
    }}
  }}

  downLabels.forEach(item => item.lx = item.x);
  relaxLabels(downLabels, MIN_GAP);

  upLabels.forEach(item => item.lx = item.x);
  relaxLabels(upLabels, MIN_GAP);


  // ── DOWN labels — top strip ───────────────────────────────────────────────
  ctxTop.font      = `bold ${{LSIZE}}px Arial`;
  downLabels.forEach(item=>{{
    const borderY = LABEL_H;
    const textBaseY = borderY - PAD;

    // ── Dotted connector line on MAIN chart: from top (0) to first stop (item.y) ──
    ctxM.save();
    ctxM.strokeStyle = item.col;
    ctxM.lineWidth   = 0.8;
    ctxM.setLineDash([2, 3]);
    ctxM.beginPath();
    ctxM.moveTo(item.lx, 0);
    ctxM.lineTo(item.x, item.y);
    ctxM.stroke();
    ctxM.restore();

    // ── Vertical label (rotated -90°, reads bottom→up) ──
    ctxTop.save();
    ctxTop.translate(item.lx, textBaseY);
    ctxTop.rotate(-Math.PI/2);
    ctxTop.fillStyle     = item.col;
    ctxTop.textAlign     = "left";
    ctxTop.textBaseline  = "middle";
    ctxTop.fillText(item.label, 0, 0);
    ctxTop.restore();
  }});

  // ── UP labels — bottom strip ──────────────────────────────────────────────
  ctxBot.font      = `bold ${{LSIZE}}px Arial`;
  upLabels.forEach(item=>{{
    const borderY  = 0;
    const textTopY = borderY + PAD;

    // ── Dotted connector line on MAIN chart: from bottom (H) to first stop (item.y) ──
    ctxM.save();
    ctxM.strokeStyle = item.col;
    ctxM.lineWidth   = 0.8;
    ctxM.setLineDash([2, 3]);
    ctxM.beginPath();
    let H = STNS.length*cH();
    ctxM.moveTo(item.lx, H);
    ctxM.lineTo(item.x, item.y);
    ctxM.stroke();
    ctxM.restore();

    // ── Vertical label (rotated +90°, reads top→down) ──
    ctxBot.save();
    ctxBot.translate(item.lx, textTopY);
    ctxBot.rotate(Math.PI/2);
    ctxBot.fillStyle     = item.col;
    ctxBot.textAlign     = "left";
    ctxBot.textBaseline  = "middle";
    ctxBot.fillText(item.label, 0, 0);
    ctxBot.restore();
  }});
}}

function renderAll(){{
  drawX(); drawY(); drawYR(); drawMain();
  if(SHOW_LABELS) drawLabels();
  zoomLbl.textContent=Math.round(scale*100)+"%";
  buildHitBoxes();
  drawHighlight(hlVisible);
}}

// ── Train Highlight + Blink ──────────────────────────────────────────────────
let hlVisible=true, hlTimer=null;

function drawHighlight(visible){{
  if(!cov) return;
  const W=(T_MAX-T_MIN)*cW(), H=STNS.length*cH();
  // Size the overlay to match main canvas
  const dpr=window.devicePixelRatio||1;
  cov.width=W*dpr; cov.height=H*dpr;
  cov.style.width=W+"px"; cov.style.height=H+"px";
  const ctx=cov.getContext("2d");
  ctx.scale(dpr,dpr);
  ctx.clearRect(0,0,W,H);
  if(!HIGHLIGHT_TR || !visible) return;

  const line=RAW_LINES.find(l=>l[0]===HIGHLIGHT_TR);
  if(!line) return;
  const [tr,dir,typ,cat,ac,fr,to,pts]=line;
  const visiblePts=pts.filter(p=>p[0]>=T_MIN&&p[0]<=T_MAX);
  if(!visiblePts.length) return;

  const col=lCol(cat,typ,tr);
  // White glow halo
  for(let glow=4;glow>=1;glow--){{
    ctx.strokeStyle="#FFFFFF";
    ctx.lineWidth=(glow*3.5)*scale;
    ctx.globalAlpha=0.06+glow*0.05;
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(xPx(pts[0][0]),yPx(pts[0][1])+cH()/2);
    for(let i=1;i<pts.length;i++) ctx.lineTo(xPx(pts[i][0]),yPx(pts[i][1])+cH()/2);
    ctx.stroke();
  }}
  // Solid highlight line
  ctx.setLineDash([]);
  ctx.strokeStyle=col;
  ctx.lineWidth=3.5*scale;
  ctx.globalAlpha=1.0;
  ctx.beginPath();
  ctx.moveTo(xPx(pts[0][0]),yPx(pts[0][1])+cH()/2);
  for(let i=1;i<pts.length;i++) ctx.lineTo(xPx(pts[i][0]),yPx(pts[i][1])+cH()/2);
  ctx.stroke();
  // Stop dots
  ctx.fillStyle=col;
  visiblePts.forEach(p=>{{
    ctx.beginPath(); ctx.arc(xPx(p[0]),yPx(p[1])+cH()/2,dR()*2,0,Math.PI*2); ctx.fill();
  }});
  // Label badge on first visible point
  const fp=visiblePts[0];
  const lx=xPx(fp[0]), ly=yPx(fp[1])+cH()/2;
  ctx.font=`bold ${{Math.max(10,Math.min(14,cH()*0.6))}}px Arial`;
  const tw=ctx.measureText(tr).width;
  ctx.fillStyle="rgba(0,0,0,0.8)";
  ctx.fillRect(lx+6,ly-12,tw+10,18);
  ctx.strokeStyle=col; ctx.lineWidth=1.5;
  ctx.strokeRect(lx+6,ly-12,tw+10,18);
  ctx.fillStyle="#FFFFFF";
  ctx.textAlign="left"; ctx.textBaseline="middle";
  ctx.fillText(tr,lx+11,ly-3);
  ctx.globalAlpha=1;
}}

if(HIGHLIGHT_TR){{
  if(hlTimer) clearInterval(hlTimer);
  hlTimer=setInterval(()=>{{ hlVisible=!hlVisible; drawHighlight(hlVisible); }}, 550);
  // Stop blinking after 15 seconds, leave highlight statically visible
  setTimeout(()=>{{
    clearInterval(hlTimer); hlTimer=null;
    hlVisible=true; drawHighlight(true);
  }}, 10000);
}}

const fsBtn=document.getElementById("btn-fs-"+CID);
if(fsBtn){{
  fsBtn.onclick=()=>{{
    const el=document.documentElement;
    if(!document.fullscreenElement){{
      (el.requestFullscreen||el.webkitRequestFullscreen||el.mozRequestFullScreen||el.msRequestFullscreen).call(el);
      fsBtn.textContent="Exit Fullscreen";
    }} else {{
      (document.exitFullscreen||document.webkitExitFullscreen||document.mozCancelFullScreen||document.msExitFullscreen).call(document);
      fsBtn.textContent="Fullscreen";
    }}
  }};
  document.addEventListener("fullscreenchange",()=>{{
    if(!document.fullscreenElement) fsBtn.textContent="Fullscreen";
  }});
}}

document.getElementById("btn-zin-"+CID).onclick   =()=>{{scale=Math.min(8,scale*1.3);renderAll();}};
document.getElementById("btn-zout-"+CID).onclick  =()=>{{scale=Math.max(0.15,scale/1.3);renderAll();}};
document.getElementById("btn-reset-"+CID).onclick =()=>{{scale=1.0;renderAll();}};
bodyDiv.addEventListener("wheel",e=>{{
  if(!e.ctrlKey&&!e.metaKey) return;
  e.preventDefault();
  scale=e.deltaY<0?Math.min(8,scale*1.15):Math.max(0.15,scale/1.15);
  renderAll();
}},{{passive:false}});

// ── Hit-test for tooltips ─────────────────────────────────────────────────────
let hitBoxes=[];
function buildHitBoxes(){{
  hitBoxes=[];
  RAW_LINES.forEach(l=>{{
    const [tr,dir,typ,cat,ac,fr,to,pts]=l;
    const catLbl=CAT_LABEL[cat]||cat;
    const col=lCol(cat,typ,tr);
    pts.forEach(p=>{{
      if(p[0]<T_MIN||p[0]>T_MAX) return;
      const nd=p[0]>=1440;
      hitBoxes.push({{
        x:xPx(p[0])-7, y:yPx(p[1])+cH()/2-7, w:14, h:14,
        html:`<b>${{p[2]}}</b>${{nd?' <span style="color:#99aadd">⁺</span>':''}} &nbsp;<span style="color:#aaccee;font-weight:600">@${{STNS[p[1]]}}</span>&nbsp; Train <b>${{tr}}</b><br>
              ${{dir}} · ${{typ}} · <b style="color:${{col}}">${{catLbl}}</b>
              ${{ac==="AC"?' · <b style="color:#88ccff">AC</b>':''}}<br>
              ${{fr}} → ${{to}}`
      }});
    }});
  }});
  RAW_DWELLS.forEach(d=>{{
    const [tr,yi,dir,typ,stp,x1r,x2r,at,dt,cat]=d;
    if(yi===undefined||yi>=STNS.length) return;
    const col=lCol(cat||'LOCAL',typ);
    const cy_=yPx(yi)+cH()/2;
    const dotR_=Math.max(2.5,dR()*1.5);

    // Build tooltip HTML
    const stnName=STNS[yi];
    const catLbl=CAT_LABEL[cat]||cat;
    let html=`<b>${{stnName}}</b> <span style="color:#aaccee">@${{stnName}}</span> &nbsp; Train <b>${{tr}}</b><br>
              ${{dir}} · ${{typ}} · <b style="color:${{col}}">${{catLbl}}</b><br>`;
    if(stp==="dwell"){{
      html+=`<b style="color:#88ccff">ARR: ${{at}}</b> (●) &nbsp;→&nbsp; (○) <b style="color:#88ccff">DEP: ${{dt}}</b><br>
             Halt: <b style="color:${{col}}">${{x2r-x1r}} min</b>`;
    }} else if(stp==="dep"){{
      html+=`<b style="color:#88ccff">DEP: ${{dt}}</b> &nbsp; (departure only)`;
    }} else if(stp==="arr"){{
      html+=`<b style="color:#88ccff">ARR: ${{at}}</b> &nbsp; (arrival only)`;
    }} else {{
      html+=`Pass through @ ${{at||dt||"—"}}`;
    }}

    // Hit box around the rendered element
    if(stp==="dwell" && x2r>x1r){{
      // Cover the full ARR-to-DEP span
      const x1c=Math.max(x1r,T_MIN), x2c=Math.min(x2r,T_MAX);
      if(x2c<T_MIN||x1c>T_MAX) return;
      hitBoxes.push({{
        x:xPx(x1c)-dotR_-2, y:yPx(yi),
        w:Math.max(xPx(x2c)-xPx(x1c)+dotR_*2+4, 12), h:cH(),
        html
      }});
    }} else {{
      // Single dot hit area
      const xpos=(stp==="dep")?x2r:x1r;
      if(xpos<T_MIN||xpos>T_MAX) return;
      hitBoxes.push({{
        x:xPx(xpos)-dotR_-2, y:yPx(yi),
        w:dotR_*2+4, h:cH(),
        html
      }});
    }}
  }});
  CONFLICTS.forEach(c=>{{
    const sev=c.gap<=CONFLICT_GAP/2?"🔴 CONFLICT":"⚠️ Tight";
    hitBoxes.unshift({{
      x:xPx(c.x1), y:yPx(c.y), w:Math.max(xPx(c.x2)-xPx(c.x1),10), h:cH(),
      html:`<b>${{sev}}</b> at <b>${{STNS[c.y]}}</b><br>
            Train ${{c.tr1}} @ ${{c.time1}}<br>
            Train ${{c.tr2}} @ ${{c.time2}}<br>
            Gap: <b style="color:#f44">${{c.gap}} min</b>`
    }});
  }});
}}

cm.addEventListener("mousemove",e=>{{
  const r=cm.getBoundingClientRect(), mx=e.clientX-r.left, my=e.clientY-r.top;
  let found=null;
  for(let i=0;i<hitBoxes.length;i++){{
    const b=hitBoxes[i];
    if(mx>=b.x&&mx<=b.x+b.w&&my>=b.y&&my<=b.y+b.h){{found=b;break;}}
  }}
  if(!found){{
    for(let i=hitBoxes.length-1;i>=0;i--){{
      const b=hitBoxes[i];
      if(mx>=b.x&&mx<=b.x+b.w&&my>=b.y&&my<=b.y+b.h){{found=b;break;}}
    }}
  }}
  if(found){{
    tip.style.display="block"; tip.innerHTML=found.html;
    tip.style.left=(e.clientX+14)+"px"; tip.style.top=(e.clientY-10)+"px";
    cm.style.cursor="pointer";
  }} else {{ tip.style.display="none"; cm.style.cursor="default"; }}
}});
cm.addEventListener("mouseleave",()=>tip.style.display="none");

// ── Downloads ─────────────────────────────────────────────────────────────────
document.getElementById("btn-png-"+CID).onclick=()=>{{
  const a=document.createElement("a");
  a.href=cm.toDataURL("image/png");
  a.download="marey_chart.png"; a.click();
}};

document.getElementById("btn-svg-"+CID).onclick=()=>{{
  const svgNS="http://www.w3.org/2000/svg";
  const root=document.createElementNS(svgNS,"svg");
  const W2=(T_MAX-T_MIN)*cW(), H2=STNS.length*cH(), ML=92, MT=34;
  const topH=ctop.clientHeight||0, botH=cbot.clientHeight||0;
  root.setAttribute("xmlns",svgNS);
  root.setAttribute("width",  W2+ML+20);
  root.setAttribute("height", topH+MT+H2+botH+20);
  const bg=document.createElementNS(svgNS,"rect");
  bg.setAttribute("width","100%"); bg.setAttribute("height","100%");
  bg.setAttribute("fill",BG); root.appendChild(bg);
  function addPanel(canvas,x,y){{
    if(!canvas||!canvas.width) return;
    const img=document.createElementNS(svgNS,"image");
    img.setAttribute("href",  canvas.toDataURL("image/png"));
    img.setAttribute("x",     x);
    img.setAttribute("y",     y);
    img.setAttribute("width", canvas.style.width  || canvas.width);
    img.setAttribute("height",canvas.style.height || canvas.height);
    root.appendChild(img);
  }}
  addPanel(ctop, ML, 0);               // DOWN labels strip
  addPanel(cx,   ML, topH);            // X-axis
  addPanel(cy,   0,  topH+MT);         // Y-axis
  addPanel(cm,   ML, topH+MT);         // Main chart
  addPanel(cbot, ML, topH+MT+H2);      // UP labels strip
  const serial=new XMLSerializer().serializeToString(root);
  const blob=new Blob([serial],{{type:"image/svg+xml;charset=utf-8"}});
  const a=document.createElement("a");
  a.href=URL.createObjectURL(blob);
  a.download="marey_chart.svg"; a.click();
}};

renderAll();

// ── Auto-scroll to highlighted train ─────────────────────────────────────────
function scrollToHighlight(){{
  if(!HIGHLIGHT_TR) return;
  const line=RAW_LINES.find(l=>l[0]===HIGHLIGHT_TR);
  if(!line) return;
  const [tr,dir,typ,cat,ac,fr,to,pts]=line;
  const visiblePts=pts.filter(p=>p[0]>=T_MIN&&p[0]<=T_MAX);
  // If train not in current time window, scroll to its first stop regardless
  const anchorPts=visiblePts.length?visiblePts:pts;
  if(!anchorPts.length) return;
  const fp=anchorPts[0];
  const xCenter=xPx(fp[0]);
  const yCenter=yPx(fp[1])+cH()/2;
  const bW=bodyDiv.clientWidth||600;
  const bH=bodyDiv.clientHeight||400;
  bodyDiv.scrollTo({{
    left:Math.max(0,xCenter-bW/2),
    top:Math.max(0,yCenter-bH/2),
    behavior:"smooth"
  }});
}}

// Delay slightly so layout is settled, then scroll
if(HIGHLIGHT_TR) setTimeout(scrollToHighlight, 120);
}})();
</script></body></html>"""
