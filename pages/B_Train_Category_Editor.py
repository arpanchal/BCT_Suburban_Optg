import streamlit as st
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _utils import _stops_mtime, _meta_mtime, load_meta, STATIONS, CAT_COLORS, LINES_DEF
import pandas as pd

# st.set_page_config(page_title="Train Category Editor", layout="wide")
st.title("🏷️ Train Category & Line Editor")
st.caption("Tag Mail/Express trains, assign line types, and set mid-route line switches. "
           "Changes are saved to train_meta.json and take effect immediately on all charts.")

BASE      = os.path.dirname(os.path.dirname(__file__))
META_PATH = os.path.join(BASE, "train_meta.json")

def save_meta(m):
    with open(META_PATH, "w") as f:
        json.dump(m, f)
    st.cache_data.clear()

meta = load_meta(_mtime=_meta_mtime())

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 View & Bulk Edit", "✏️ Edit Single Train", "📥 Import from CSV"])

# ═══════════════════════════════════════════════════════════════
# TAB 1 — View & bulk edit
# ═══════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Current Train Category & Line Assignments")

    col1, col2, col3 = st.columns(3)
    filter_cat  = col1.multiselect("Filter by Category",
                      list(CAT_COLORS.keys()), default=list(CAT_COLORS.keys()))
    filter_line = col2.multiselect("Filter by Line",
                      list(LINES_DEF.keys()), default=list(LINES_DEF.keys()))
    filter_dir  = col3.radio("Direction", ["Both","DOWN","UP"], horizontal=True)

    rows = []
    for tr, m in meta.items():
        if m.get("train_cat","LOCAL") not in filter_cat: continue
        if m.get("line","AUTO") not in filter_line: continue
        if filter_dir != "Both" and m.get("direction","") != filter_dir: continue
        rows.append({
            "Train No.":   tr,
            "Set No.":     m.get("set_no",""),
            "Direction":   m.get("direction",""),
            "Type":        m.get("type",""),
            "Category":    m.get("train_cat","LOCAL"),
            "Line":        m.get("line","AUTO"),
            "Line Switch": json.dumps(m.get("line_switch",{})) if m.get("line_switch") else "",
            "AC":          m.get("ac",""),
            "From":        m.get("from_stn",""),
            "To":          m.get("to_stn",""),
            "Cars":        m.get("cars",""),
        })

    df = pd.DataFrame(rows)
    st.info(f"Showing **{len(df)}** trains")

    # Category colour pills
    from collections import Counter
    cat_cts = Counter(r["Category"] for r in rows)
    pills = " &nbsp; ".join(
        f'<span style="background:{CAT_COLORS[c]["slow"]};color:#000;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">{c}: {n}</span>'
        for c,n in cat_cts.most_common() if c in CAT_COLORS
    )
    st.markdown(pills, unsafe_allow_html=True)

    st.dataframe(df, use_container_width=True, height=400)
    st.download_button("⬇️ Download as CSV", df.to_csv(index=False),
                       "train_categories.csv", "text/csv")

    st.markdown("---")
    st.markdown("#### Bulk Category Change")
    bcol1, bcol2, bcol3 = st.columns(3)
    bulk_from = bcol1.multiselect("Change trains with category", list(CAT_COLORS.keys()))
    bulk_dir  = bcol2.radio("Direction", ["Both","DOWN","UP"], horizontal=True, key="bulk_dir")
    bulk_to   = bcol3.selectbox("To category", list(CAT_COLORS.keys()), index=0, key="bulk_to")
    if st.button("Apply Bulk Category Change", type="primary"):
        changed = 0
        for tr, m in meta.items():
            if m.get("train_cat","LOCAL") in bulk_from:
                if bulk_dir == "Both" or m.get("direction","") == bulk_dir:
                    meta[tr]["train_cat"] = bulk_to
                    changed += 1
        save_meta(meta)
        st.success(f"Updated {changed} trains to category **{bulk_to}**. Reload page to see changes.")

# ═══════════════════════════════════════════════════════════════
# TAB 2 — Edit single train
# ═══════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Edit a Single Train")
    all_trains = sorted(meta.keys())
    sel_tr = st.selectbox("Select Train", all_trains)
    m = meta[sel_tr]

    col1, col2, col3, col4 = st.columns(4)
    new_cat  = col1.selectbox("Category", list(CAT_COLORS.keys()),
                               index=list(CAT_COLORS.keys()).index(m.get("train_cat","LOCAL")))
    new_line = col2.selectbox("Line Assignment", list(LINES_DEF.keys()),
                               index=list(LINES_DEF.keys()).index(m.get("line","AUTO")) if m.get("line") in LINES_DEF else 0)
    new_type = col3.selectbox("Train Type", ["SLOW", "FAST", "M/E", ""],
                               index=(["SLOW","FAST","M/E",""].index(m.get("type","SLOW"))
                                      if m.get("type","SLOW") in ["SLOW","FAST","M/E",""] else 0))
    new_ac   = col4.selectbox("AC", ["","AC"],
                               index=1 if m.get("ac")=="AC" else 0)

    st.markdown("**Line Switch** — specify station where train switches line mid-route")
    st.caption('Example: train runs on Down Through (DT) from CCG to BA, then switches to Down Local (DL). '
               'Enter station code and new line code.')
    sw_stn  = st.selectbox("Switch at station (optional)", ["(none)"] + STATIONS)
    sw_line = st.selectbox("Switch to line", list(LINES_DEF.keys()), key="sw_line")

    # Show current switch
    current_sw = m.get("line_switch",{})
    if current_sw:
        st.info(f"Current switch: {current_sw}")
        if st.button("Clear existing line switch"):
            meta[sel_tr]["line_switch"] = {}
            save_meta(meta)
            st.success("Line switch cleared.")

    st.markdown("**Current values:**")
    curr = pd.DataFrame([{
        "Train": sel_tr, "Direction": m.get("direction",""), "Type": m.get("type",""),
        "Category": m.get("train_cat",""), "Line": m.get("line",""),
        "Line Switch": str(current_sw), "From": m.get("from_stn",""),
        "To": m.get("to_stn",""), "Set": m.get("set_no",""),
    }])
    st.dataframe(curr, use_container_width=True)

    if st.button(f"💾 Save changes for Train {sel_tr}", type="primary"):
        meta[sel_tr]["train_cat"] = new_cat
        meta[sel_tr]["line"]      = new_line
        meta[sel_tr]["type"]      = new_type
        meta[sel_tr]["ac"]        = new_ac
        if sw_stn != "(none)":
            if "line_switch" not in meta[sel_tr]:
                meta[sel_tr]["line_switch"] = {}
            meta[sel_tr]["line_switch"][sw_stn] = sw_line
        save_meta(meta)
        st.success(f"✅ Train {sel_tr} updated. Cache cleared — changes visible immediately.")
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# TAB 3 — Import from CSV
# ═══════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Import Category/Line from CSV")
    st.markdown("""
Upload a CSV with columns: **Train No.**, **Category**, **Line** (optional), **Line Switch** (optional, JSON format).

Valid categories: `LOCAL`, `AC_LOCAL`, `DRD`, `MAIL`, `EXPRESS`, `EMPTY`

Valid lines: `DT`, `DL`, `UT`, `UL`, `MAIN`, `AUTO`

**Example CSV:**
```
Train No.,Category,Line,Line Switch
90001,LOCAL,DL,
90021,LOCAL,DT,
12953,MAIL,DT,
19023,EXPRESS,DT,"{""BA"": ""DL""}"
```
""")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded:
        try:
            df_up = pd.read_csv(uploaded, dtype=str).fillna("")
            st.dataframe(df_up.head(20), use_container_width=True)
            st.info(f"Found **{len(df_up)}** rows")
            if st.button("🚀 Apply CSV Changes", type="primary"):
                updated, skipped = 0, 0
                for _, row in df_up.iterrows():
                    tr = str(row.get("Train No.","")).strip()
                    if not tr or tr not in meta:
                        skipped += 1; continue
                    cat = str(row.get("Category","")).strip()
                    if cat in CAT_COLORS:
                        meta[tr]["train_cat"] = cat
                    ln  = str(row.get("Line","")).strip()
                    if ln in LINES_DEF:
                        meta[tr]["line"] = ln
                    sw_raw = str(row.get("Line Switch","")).strip()
                    if sw_raw:
                        try:
                            meta[tr]["line_switch"] = json.loads(sw_raw)
                        except Exception:
                            pass
                    updated += 1
                save_meta(meta)
                st.success(f"✅ Updated {updated} trains, skipped {skipped}. Cache cleared.")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")

# ── Summary at bottom ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Line Assignment Summary")
from collections import Counter
line_cats = Counter((m.get("line","AUTO"), m.get("train_cat","LOCAL")) for m in meta.values())
sum_rows = [{"Line": LINES_DEF.get(l,{}).get("label",l), "Category": CAT_COLORS.get(c,{}).get("label",c), "Trains": n}
            for (l,c), n in sorted(line_cats.items())]
st.dataframe(pd.DataFrame(sum_rows), use_container_width=True, height=300)
