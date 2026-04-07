path = r"c:\Users\alpes\Downloads\train_app_new2\pages\_chart_builder.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. replace in downLabels and upLabels array setup
idx_start = text.find('if(dir==="DOWN"){')
idx_end = text.find('upLabels.sort((a,b)=>a.x-b.x);')

new_1 = """if(dir==="DOWN"){
      const p = visiblePts[0];
      const col = lCol(cat, typ);
      downLabels.push({x: xPx(p[0]), y: yPx(p[1])+cH()/2, label: tr, col: col});
    } else if(dir==="UP"){
      const p = visiblePts[0]; // attach to first station stop
      const col = lCol(cat, typ);
      upLabels.push({x: xPx(p[0]), y: yPx(p[1])+cH()/2, label: tr, col: col});
    }
  });

  downLabels.sort((a,b)=>a.x-b.x);
  upLabels.sort((a,b)=>a.x-b.x);

  function relaxLabels(labels, gap) {
    let changed = true;
    let iters = 0;
    while(changed && iters < 20) {
      changed = false;
      for(let i=0; i<labels.length-1; i++) {
         let diff = labels[i+1].lx - labels[i].lx;
         if(diff < gap) {
            let overlap = gap - diff;
            labels[i].lx -= overlap / 2.0;    // push left
            labels[i+1].lx += overlap / 2.0;  // push right
            changed = true;
         }
      }
      iters++;
    }
  }

  downLabels.forEach(item => item.lx = item.x);
  relaxLabels(downLabels, MIN_GAP);

  upLabels.forEach(item => item.lx = item.x);
  relaxLabels(upLabels, MIN_GAP);
"""

if idx_start != -1 and idx_end != -1:
    text = text[:idx_start] + new_1 + text[idx_end + len('upLabels.sort((a,b)=>a.x-b.x);'):]
else:
    print("1 not found")

# 2. replace drawLabels DOWN and UP
idx_start_down = text.find('// ── DOWN labels — top strip')
idx_end_down = text.find('// ── UP labels — bottom strip')

new_down = """// ── DOWN labels — top strip ───────────────────────────────────────────────
  ctxTop.font      = `bold ${LSIZE}px Arial`;
  downLabels.forEach(item=>{
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
  });

  """

if idx_start_down != -1 and idx_end_down != -1:
    text = text[:idx_start_down] + new_down + text[idx_end_down:]
else:
    print("2 not found")


# 3. replace UP labels
idx_start_up = text.find('// ── UP labels — bottom strip')
idx_end_up = text.find('function renderAll()')

new_up = """// ── UP labels — bottom strip ──────────────────────────────────────────────
  ctxBot.font      = `bold ${LSIZE}px Arial`;
  upLabels.forEach(item=>{
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
  });
}

"""

if idx_start_up != -1 and idx_end_up != -1:
    text = text[:idx_start_up] + new_up + text[idx_end_up:]
else:
    print("3 not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("applied anchors approach")
