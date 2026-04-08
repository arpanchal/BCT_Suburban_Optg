"""Fix the tooltip JS block lines 446-459 in D_Rake_Link.py"""
path = r'c:\Users\alpes\Downloads\train_app_new2\pages\D_Rake_Link.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The lines 446-459 (0-indexed: 445-458) contain unescaped JS braces
# We replace the whole block with correctly escaped version
FIXED_BLOCK = [
    "      const fmt=m=>{{const h=Math.floor(m/60),mn=m%60;return h>=24?`${{String(h-24).padStart(2,'0')}}:${{String(mn).padStart(2,'0')}}\\u207a`:`${{String(h).padStart(2,'0')}}:${{String(mn).padStart(2,'0')}}`;}};\r\n",
    "      const acBadge=tr.ac===\"AC\"?` <b style=\"color:#29B6F6\">[AC]</b>`:\"\";\r\n",
    "      const carBadge=tr.cars?` <span style=\"color:#FFD700\">${{tr.cars}}</span>`:\"\";\r\n",
    "      hitBoxes.push({{\r\n",
    "        x:x1, y, w:Math.max(x2-x1,6), h:bh,\r\n",
    "        html:`<span style=\"font-size:13px;font-weight:700;color:${{tr.col}}\">${{tr.tr}}</span>${{acBadge}}${{carBadge}}\r\n",
    "              <span style=\"color:#aaccee;margin-left:6px\">${{tr.dir}}</span><br>\r\n",
    "              <span style=\"color:#88ccff\">\u2193 DEP: <b>${{fmt(tr.dep)}}</b></span>\r\n",
    "              &nbsp;&nbsp;<span style=\"color:#88ccff\">\u2191 ARR: <b>${{fmt(tr.arr)}}</b></span><br>\r\n",
    "              Duration: <b style=\"color:#ffdd99\">${{tr.dur}} min (${{Math.round(tr.dur/60*10)/10}} hrs)</b><br>\r\n",
    "              Route: <b>${{tr.from}}</b> \u2192 <b>${{tr.to}}</b><br>\r\n",
    "              Type: <span style=\"color:#aaa\">${{tr.typ}}</span>\r\n",
    "              &nbsp;|&nbsp; Cat: <span style=\"color:${{tr.col}}\">${{tr.cat}}</span>`\r\n",
    "      }});\r\n",
]

# Lines 446-459 are 0-indexed 445-458
start = 445
end = 459
print(f"Replacing lines {start+1} to {end} ({end-start} lines) with {len(FIXED_BLOCK)} lines")
print("Before line 446:", repr(lines[445][:80]))
lines[start:end] = FIXED_BLOCK
print("After line 446:", repr(lines[445][:80]))

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("Syntax OK!")
except py_compile.PyCompileError as e:
    print(f"Syntax error: {e}")
