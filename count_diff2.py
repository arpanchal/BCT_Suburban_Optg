import json
import os

BASE = r'c:\Users\alpes\Downloads\train_app_new2'
meta_path = os.path.join(BASE, 'train_meta.json')
stops_path = os.path.join(BASE, 'stops_data.json')

with open(meta_path, 'r', encoding='utf-8') as f:
    train_info = json.load(f)

with open(stops_path, 'r', encoding='utf-8') as f:
    stops_data = json.load(f)

trains_in_meta = set(train_info.keys())
trains_in_stops = set(s['train'] for s in stops_data['stops'])

missing_in_meta = trains_in_stops - trains_in_meta

with open('missing.txt', 'w') as f:
    f.write(f"Count: {len(missing_in_meta)}\n")
    f.write(", ".join(sorted(missing_in_meta)))
