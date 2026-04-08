"""
Two fixes for D_Rake_Link.py:
1. Fix corrupted \\r\\r\\n line endings in tooltip block (lines ~446-459)
2. Rewrite tooltip with correct JS (single-line template literal, no multi-line corruption)
3. Add DOWN/UP intensity differentiation:
   - DOWN: full opacity bar
   - UP: lighter (overlay white at 30%) + hatched top-border to visually distinguish
"""
path = r'c:\Users\alpes\Downloads\train_app_new2\pages\D_Rake_Link.py'

with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# Fix 1: normalize line endings
src = src.replace('\r\r\n', '\r\n')

# Fix 2: Replace the DOWN/UP bar drawing - add intensity differentiation
OLD_DRAW = """      // Rounded rect\r\n      ctx.fillStyle=tr.col;\r\n      ctx.globalAlpha=0.88;"""

NEW_DRAW = """      // DOWN=full, UP=lighter (intensity differentiation)\r\n      const isDown = tr.dir === "DOWN";\r\n      ctx.fillStyle = tr.col;\r\n      ctx.globalAlpha = isDown ? 0.92 : 0.52;"""

if OLD_DRAW in src:
    src = src.replace(OLD_DRAW, NEW_DRAW)
    print("OK: intensity fix")
else:
    print("MISS: intensity fix")

# Fix 3: Replace tooltip block (all on one line to avoid \r\r\n issue)
# Find and replace the entire hitBoxes.push block
OLD_TIP_START = "      const fmt=m=>{{const h=Math.floor(m/60),mn=m%60;return h>=24?`${{String(h-24).padStart(2,'0')}}:${{String(mn).padStart(2,'0')}}\\u207a`:`${{String(h).padStart(2,'0')}}:${{String(mn).padStart(2,'0')}}`;}};"

NEW_TIP_BLOCK = (
    "      const fmt=m=>{{const h=Math.floor(m/60),mn=m%60;return h>=24?String(h-24).padStart(2,'0')+':'+String(mn).padStart(2,'0')+'\\u207a':String(h).padStart(2,'0')+':'+String(mn).padStart(2,'0');}}\r\n"
    "      const acTag=tr.ac===\"AC\"?' <b style=\"color:#29B6F6\">[AC]</b>':'';\r\n"
    "      const carTag=tr.cars?' <span style=\"color:#FFD700\">'+tr.cars+'</span>':'';\r\n"
    "      const dirCol=tr.dir===\"DOWN\"?'#88ee88':'#ee9966';\r\n"
    "      hitBoxes.push({{\r\n"
    "        x:x1, y, w:Math.max(x2-x1,6), h:bh,\r\n"
    "        html:'<span style=\"font-size:13px;font-weight:700;color:'+tr.col+'\">'+tr.tr+'</span>'+acTag+carTag\r\n"
    "             +' <span style=\"color:'+dirCol+';margin-left:5px\">'+tr.dir+'</span><br>'\r\n"
    "             +'<span style=\"color:#88ccff\">\u2193 DEP: <b>'+fmt(tr.dep)+'</b></span>'\r\n"
    "             +'&nbsp;&nbsp;<span style=\"color:#88ccff\">\u2191 ARR: <b>'+fmt(tr.arr)+'</b></span><br>'\r\n"
    "             +'Duration: <b style=\"color:#ffdd99\">'+tr.dur+' min ('+Math.round(tr.dur/60*10)/10+' hrs)</b><br>'\r\n"
    "             +'Route: <b>'+tr.from+'</b> \u2192 <b>'+tr.to+'</b><br>'\r\n"
    "             +'Type: <span style=\"color:#aaa\">'+tr.typ+'</span>'\r\n"
    "             +'&nbsp;|&nbsp;Cat: <span style=\"color:'+tr.col+'\">'+tr.cat+'</span>'\r\n"
    "      }});\r\n"
)

# Find the start of the old tooltip block and the end (hitBoxes.push close)
import re
# Match from 'const fmt' line to the closing '});' then next });
pattern = r"      const fmt=m=>.*?      }}\);\r?\n"
m = re.search(pattern, src, re.DOTALL)
if m:
    src = src[:m.start()] + NEW_TIP_BLOCK + src[m.end():]
    print("OK: tooltip block replaced")
else:
    print("MISS: tooltip block not found")
    # Show what's around the fmt line
    idx = src.find('const fmt=m=>')
    if idx >= 0:
        print("Context:", repr(src[idx:idx+300]))

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("SYNTAX OK!")
except py_compile.PyCompileError as e:
    print(f"Syntax error: {e}")
