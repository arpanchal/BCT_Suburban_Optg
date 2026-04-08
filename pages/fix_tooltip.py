"""
Fix the tooltip JS block in D_Rake_Link.py:
- Line 446: fmt arrow function needs {{ }} braces to stay as JS inside Python f-string
- Lines 447-462: hitBoxes.push( and template literals need {{ }} escaping
"""
path = r'c:\Users\alpes\Downloads\train_app_new2\pages\D_Rake_Link.py'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# The broken block (single braces, no Python f-string escaping)
OLD = r"""      const fmt=m=>{const h=Math.floor(m/60),mn=m%60;return h>=24?`${String(h-24).padStart(2,'0')}:${String(mn).padStart(2,'0')}\u207a`:`${String(h).padStart(2,'0')}:${String(mn).padStart(2,'0')}`;};
      const acBadge=tr.ac===\"AC\"?` <b style=\"color:#29B6F6\">[AC]</b>`:\"\";
      const carBadge=tr.cars?` <span style=\"color:#FFD700\">${tr.cars}</span>`:\"\";
      hitBoxes.push({
        x:x1, y, w:Math.max(x2-x1,6), h:bh,
        html:`<span style=\"font-size:13px;font-weight:700;color:${tr.col}\">${tr.tr}</span>${acBadge}${carBadge}
              <span style=\"color:#aaccee;margin-left:6px\">${tr.dir}</span><br>
              <span style=\"color:#88ccff\">↓ DEP: <b>${fmt(tr.dep)}</b></span>
              &nbsp;&nbsp;<span style=\"color:#88ccff\">↑ ARR: <b>${fmt(tr.arr)}</b></span><br>
              Duration: <b style=\"color:#ffdd99\">${tr.dur} min (${Math.round(tr.dur/60*10)/10} hrs)</b><br>
              Route: <b>${tr.from}</b> → <b>${tr.to}</b><br>
              Type: <span style=\"color:#aaa\">${tr.typ}</span>
              &nbsp;|&nbsp; Cat: <span style=\"color:${tr.col}\">${tr.cat}</span>`
      });"""

NEW = r"""      const fmt=m=>{{const h=Math.floor(m/60),mn=m%60;return h>=24?`${{String(h-24).padStart(2,'0')}}:${{String(mn).padStart(2,'0')}}\u207a`:`${{String(h).padStart(2,'0')}}:${{String(mn).padStart(2,'0')}}`;}}
      const acBadge=tr.ac===\"AC\"?` <b style=\"color:#29B6F6\">[AC]</b>`:\"\";
      const carBadge=tr.cars?` <span style=\"color:#FFD700\">${{tr.cars}}</span>`:\"\";
      hitBoxes.push({{
        x:x1, y, w:Math.max(x2-x1,6), h:bh,
        html:`<span style=\"font-size:13px;font-weight:700;color:${{tr.col}}\">${{tr.tr}}</span>${{acBadge}}${{carBadge}}
              <span style=\"color:#aaccee;margin-left:6px\">${{tr.dir}}</span><br>
              <span style=\"color:#88ccff\">\u2193 DEP: <b>${{fmt(tr.dep)}}</b></span>
              &nbsp;&nbsp;<span style=\"color:#88ccff\">\u2191 ARR: <b>${{fmt(tr.arr)}}</b></span><br>
              Duration: <b style=\"color:#ffdd99\">${{tr.dur}} min (${{Math.round(tr.dur/60*10)/10}} hrs)</b><br>
              Route: <b>${{tr.from}}</b> \u2192 <b>${{tr.to}}</b><br>
              Type: <span style=\"color:#aaa\">${{tr.typ}}</span>
              &nbsp;|&nbsp; Cat: <span style=\"color:${{tr.col}}\">${{tr.cat}}</span>`
      }});"""

if OLD in src:
    src = src.replace(OLD, NEW)
    print("Fixed tooltip block")
else:
    print("OLD pattern not found, showing context around fmt=m=")
    idx = src.find('const fmt=m=>')
    if idx >= 0:
        print(repr(src[idx:idx+200]))

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)
