"""
Debug script untuk melihat apakah traffic-aware bekerja
Test dengan waktu berbeda dan lihat perbedaannya
"""

import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.gmaps_style_routing import gmaps_style_route
from algorithms.ida_star_routing.data_loader import load_network_data

WIB_TZ = timezone(timedelta(hours=7))

print("="*90)
print("🔍 DEBUG: Testing Traffic-Aware Routing")
print("="*90)

# Load network
graph = load_network_data("dataset/network_data_correct_bidirectional.json")

origin_name = "SMA Negeri 10 Palembang"
origin_coords = (-2.99361, 104.72556)
dest_name = "Pasar Modern Plaju"
dest_coords = (-3.01495, 104.807771)

# Test dengan 2 waktu yang berbeda
test_times = [
    ("Peak Pagi 07:00", datetime(2025, 1, 15, 7, 0, tzinfo=WIB_TZ)),
    ("Normal 11:00", datetime(2025, 1, 15, 11, 0, tzinfo=WIB_TZ)),
]

results = []

for label, departure_time in test_times:
    print(f"\n{'─'*90}")
    print(f"⏰ {label} - Hour: {departure_time.hour:02d}:00")
    print(f"{'─'*90}")
    
    route = gmaps_style_route(
        graph=graph,
        origin_name=origin_name,
        origin_coords=origin_coords,
        dest_name=dest_name,
        dest_coords=dest_coords,
        optimization_mode="time",
        departure_time=departure_time
    )
    
    if route:
        total_time = route.total_time_minutes
        transit_segments = [s for s in route.segments if s.mode.value != "WALK"]
        
        print(f"\n📊 Route Summary:")
        print(f"   Total time: {total_time:.1f} minutes")
        print(f"   Transit segments: {len(transit_segments)}")
        
        # Show first few transit segments with their times
        print(f"\n📋 First 5 Transit Segments:")
        for i, seg in enumerate(transit_segments[:5], 1):
            hour_at_segment = seg.departure_time.hour if seg.departure_time else departure_time.hour
            print(f"   {i}. {seg.route_name[:30]:<30} | {seg.duration_minutes:>5.1f} min | Hour: {hour_at_segment:02d}:00")
        
        results.append({
            'label': label,
            'hour': departure_time.hour,
            'total_time': total_time,
            'transit_segments': transit_segments
        })

# Comparison
if len(results) == 2:
    print(f"\n{'='*90}")
    print(f"📊 COMPARISON")
    print(f"{'='*90}")
    
    r1, r2 = results
    time_diff = r1['total_time'] - r2['total_time']
    
    print(f"\n{r1['label']}: {r1['total_time']:.1f} minutes")
    print(f"{r2['label']}: {r2['total_time']:.1f} minutes")
    print(f"Difference: {time_diff:+.1f} minutes")
    
    if abs(time_diff) < 1.0:
        print(f"\n⚠️  WARNING: Perbedaan sangat kecil!")
        print(f"   Traffic-aware mungkin tidak bekerja dengan baik")
        print(f"\n💡 Kemungkinan masalah:")
        print(f"   1. Traffic helper tidak loaded")
        print(f"   2. Route yang sama digunakan (Dijkstra menggunakan base time)")
        print(f"   3. Traffic-aware hanya diterapkan pada beberapa segmen")
    else:
        print(f"\n✅ Traffic-aware bekerja dengan baik!")

