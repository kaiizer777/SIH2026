import pandas as pd
import json
import numpy as np

zf = pd.read_csv('data/zone_features.csv')
sensor = pd.read_csv('data/synthetic_sensors.csv')

sensor['_date'] = pd.to_datetime(sensor['timestamp'], utc=True).dt.normalize().dt.tz_localize(None)
zf['_zf_date'] = pd.to_datetime(zf['date'])
zf = zf.sort_values(['zone_id', '_zf_date']).reset_index(drop=True)

max_staleness = 0
staleness_list = []
for zone_id, zone_sensor in sensor.groupby('zone_id', sort=False):
    zone_zf = zf[zf['zone_id'] == zone_id].copy()
    zone_sensor = zone_sensor.sort_values('_date')
    
    merged = pd.merge_asof(
        zone_sensor,
        zone_zf,
        left_on='_date',
        right_on='_zf_date',
        by='zone_id',
        direction='backward'
    )
    
    staleness = (merged['_date'] - merged['_zf_date']).dt.days
    zone_max = staleness.max()
    staleness_list.extend(staleness.dropna().tolist())
    if pd.notna(zone_max):
        max_staleness = max(max_staleness, int(zone_max))

print(f"Max staleness: {max_staleness}")
print(f"Avg staleness: {np.mean(staleness_list):.2f}")
print(f"Median staleness: {np.median(staleness_list):.2f}")
