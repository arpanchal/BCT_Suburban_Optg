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
missing_in_stops = trains_in_meta - trains_in_stops

print(f"Total in Meta: {len(trains_in_meta)}")
print(f"Total in Stops: {len(trains_in_stops)}")
print(f"Trains in Stops but missing from Meta: {len(missing_in_meta)}")
print("Example missing from Meta:", list(missing_in_meta)[:20])
