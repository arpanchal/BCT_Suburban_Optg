# Mumbai Suburban Railway — Marey Chart (Streamlit + D3.js)

A station × time chart (Marey diagram) for 1,315 Mumbai suburban trains across 44 stations.

## Files
```
train_app/
├── app.py            ← Streamlit application
├── stops_data.json   ← Pre-processed stop data (20,829 entries)
├── requirements.txt  ← Python dependencies
└── README.md
```

## Setup & Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the app
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

## Features

| Feature | Detail |
|---|---|
| Chart type | Marey diagram — station (Y) vs time (X) |
| Time resolution | 1 pixel = 1 minute |
| Train lines | Each line = one train journey |
| Colour coding | DOWN Slow = green · DOWN Fast = bright green · UP Slow = orange · UP Fast = red |
| Chart views | Combined / DOWN only / UP only (separate charts) |
| Filters | Train type (SLOW/FAST), AC only, time window, station subset |
| Interactivity | Hover any line or dot → tooltip shows train no., direction, type, route, stops |
| Scrolling | Horizontal + vertical scroll; chart resizes to filters |

## Sidebar Controls

- **Chart View** — Combined, DOWN only, or UP only
- **Train Type** — SLOW, FAST, or both
- **AC trains only** — toggle
- **Time window** — hour slider (0–24)
- **Stations to display** — multi-select subset
- **Row height / px per minute** — zoom controls
