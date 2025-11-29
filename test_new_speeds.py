"""
Test dengan kecepatan baru:
- Peak hour: 12 km/h
- Normal hour: 20 km/h
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
print("🧪 TESTING NEW SPEEDS: Peak 12 km/h, Normal 20 km/h")
print("="*90)

# Load network
graph = load_network_data("dataset/network_data_correct_bidirectional.json")

origin_name = "SMA Negeri 10 Palembang"
origin_coords = (-2.99361, 104.72556)
dest_name = "Pasar Modern Plaju"
dest_coords = (-3.01495, 104.807771)

test_times = [
    ("Peak Pagi 07:00", datetime(2025, 1, 15, 7, 0, tzinfo=WIB_TZ)),
    ("Normal 11:00", datetime(2025, 1, 15, 11, 0, tzinfo=WIB_TZ)),
    ("Peak Siang 13:00", datetime(2025, 1, 15, 13, 0, tzinfo=WIB_TZ)),
]

results = []

for label, departure_time in test_times:
    print(f"\n⏰ {label} (Hour: {departure_time.hour:02d}:00)")
    
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
        results.append({
            'label': label,
            'hour': departure_time.hour,
            'total_time': total_time
        })
        print(f"   Total time: {total_time:.1f} minutes")

# Comparison
if len(results) >= 2:
    print(f"\n{'='*90}")
    print(f"📊 COMPARISON")
    print(f"{'='*90}")
    print(f"\n{'Time':<25} {'Hour':<8} {'Total Time':<15}")
    print(f"{'-'*50}")
    
    for result in results:
        print(f"{result['label']:<25} {result['hour']:02d}:00    {result['total_time']:>6.1f} min")
    
    peak_results = [r for r in results if r['hour'] in [7, 13]]
    normal_results = [r for r in results if r['hour'] == 11]
    
    if peak_results and normal_results:
        avg_peak = sum(r['total_time'] for r in peak_results) / len(peak_results)
        avg_normal = sum(r['total_time'] for r in normal_results) / len(normal_results)
        diff = avg_peak - avg_normal
        
        print(f"\n{'─'*50}")
        print(f"Peak hours (12 km/h):    {avg_peak:.1f} minutes")
        print(f"Normal hours (20 km/h):  {avg_normal:.1f} minutes")
        print(f"Difference:              {diff:+.1f} minutes")
        
        # Calculate expected difference (20 km/h vs 12 km/h = 1.67x slower)
        if diff > 0:
            slowdown_factor = avg_peak / avg_normal
            print(f"Slowdown factor:         {slowdown_factor:.2f}x")
            print(f"\n✅ Perbedaan jelas terlihat!")
        else:
            print(f"\n⚠️  Masih ada masalah!")

