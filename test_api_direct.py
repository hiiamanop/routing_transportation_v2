"""
Test API langsung untuk melihat apakah backend mengembalikan hasil berbeda
"""

import requests
import json
from datetime import datetime, timezone, timedelta

WIB_TZ = timezone(timedelta(hours=7))

# Test dengan waktu berbeda
test_cases = [
    ("Peak Pagi 07:00", datetime(2025, 1, 15, 7, 0, tzinfo=WIB_TZ)),
    ("Normal 11:00", datetime(2025, 1, 15, 11, 0, tzinfo=WIB_TZ)),
    ("Peak Siang 13:00", datetime(2025, 1, 15, 13, 0, tzinfo=WIB_TZ)),
    ("Peak Sore 17:00", datetime(2025, 1, 15, 17, 0, tzinfo=WIB_TZ)),
]

# Test coordinates
origin = {
    "name": "SMA Negeri 10 Palembang",
    "lat": -2.99361,
    "lon": 104.72556
}

destination = {
    "name": "Pasar Modern Plaju",
    "lat": -3.01495,
    "lon": 104.807771
}

print("="*90)
print("🧪 TESTING API DIRECTLY")
print("="*90)

results = []

for label, departure_time in test_cases:
    print(f"\n{'─'*90}")
    print(f"⏰ {label}")
    print(f"   Time: {departure_time.strftime('%Y-%m-%dT%H:%M:%S%z')}")
    print(f"{'─'*90}")
    
    # Format untuk API
    departure_str = departure_time.strftime('%Y-%m-%dT%H:%M:%S+07:00')
    
    payload = {
        "origin": origin,
        "destination": destination,
        "algorithm": "dijkstra",
        "departure_time": departure_str
    }
    
    try:
        # Test dengan localhost:5001
        response = requests.post(
            "http://localhost:5001/api/route",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('results', {}).get('dijkstra', {}).get('success'):
                route = data['results']['dijkstra']['route']
                total_time = route['summary']['total_time_minutes']
                num_segments = len(route['segments'])
                
                results.append({
                    'label': label,
                    'hour': departure_time.hour,
                    'total_time': total_time,
                    'num_segments': num_segments
                })
                
                print(f"✅ Success!")
                print(f"   Total time: {total_time:.1f} minutes")
                print(f"   Segments: {num_segments}")
            else:
                error = data.get('error', 'Unknown error')
                print(f"❌ API Error: {error}")
        else:
            print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error: API tidak dapat diakses di localhost:5001")
        print(f"   Pastikan Flask API berjalan")
        break
    except Exception as e:
        print(f"❌ Error: {e}")

# Comparison
if len(results) >= 2:
    print(f"\n{'='*90}")
    print(f"📊 COMPARISON")
    print(f"{'='*90}")
    print(f"\n{'Time':<25} {'Hour':<8} {'Total Time':<15}")
    print(f"{'-'*50}")
    
    for result in results:
        print(f"{result['label']:<25} {result['hour']:02d}:00    {result['total_time']:>6.1f} min")
    
    peak_results = [r for r in results if r['hour'] in [6, 7, 8, 9, 12, 13, 14, 17, 18, 19]]
    normal_results = [r for r in results if r['hour'] not in [6, 7, 8, 9, 12, 13, 14, 17, 18, 19]]
    
    if peak_results and normal_results:
        avg_peak = sum(r['total_time'] for r in peak_results) / len(peak_results)
        avg_normal = sum(r['total_time'] for r in normal_results) / len(normal_results)
        
        print(f"\n{'─'*50}")
        print(f"Peak hours:    {avg_peak:.1f} minutes")
        print(f"Normal hours:  {avg_normal:.1f} minutes")
        print(f"Difference:    {avg_peak - avg_normal:+.1f} minutes")
        
        if abs(avg_peak - avg_normal) < 1.0:
            print(f"\n⚠️  WARNING: Perbedaan sangat kecil!")
            print(f"   Traffic-aware mungkin tidak bekerja dengan baik")
        else:
            print(f"\n✅ Traffic-aware bekerja dengan baik!")

