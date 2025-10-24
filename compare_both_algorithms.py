"""
Side-by-side comparison of Dijkstra and IDA* routing results
"""

from datetime import datetime
from ida_star_routing.data_loader import load_network_data
from ida_star_routing.ida_star_multimodal import gmaps_style_route_ida_star
from gmaps_style_routing import gmaps_style_route

print("="*100)
print(" "*30 + "🔬 ALGORITHM COMPARISON TEST")
print("="*100)

# Load network
print("\n📂 Loading network...")
graph = load_network_data("dataset/network_data_bidirectional.json")

# Test parameters
origin_name = "SMA Negeri 10 Palembang"
origin_coords = (-2.99361, 104.72556)
dest_name = "Pasar Modern Plaju"
dest_coords = (-3.01495, 104.807771)
departure_time = datetime(2025, 6, 15, 7, 30)

print(f"\n📍 Route: {origin_name} → {dest_name}")
print(f"   Origin: {origin_coords}")
print(f"   Destination: {dest_coords}")
print(f"   Departure: {departure_time}")

# Run Dijkstra
print("\n" + "="*100)
print(" "*35 + "🚀 DIJKSTRA ALGORITHM")
print("="*100)

dijkstra_route = gmaps_style_route(
    graph=graph,
    origin_name=origin_name,
    origin_coords=origin_coords,
    dest_name=dest_name,
    dest_coords=dest_coords,
    optimization_mode="time",
    departure_time=departure_time
)

if dijkstra_route:
    print(f"\n✅ DIJKSTRA SUCCESS!")
    print(f"   Total Duration: {dijkstra_route.total_time_minutes:.1f} minutes")
    print(f"   Total Cost: Rp {dijkstra_route.total_cost:,}")
    print(f"   Total Distance: {dijkstra_route.total_distance_km:.2f} km")
    print(f"   Segments: {len(dijkstra_route.segments)}")
    print(f"   Transfers: {dijkstra_route.num_transfers}")
else:
    print("\n❌ DIJKSTRA FAILED")

# Run IDA*
print("\n" + "="*100)
print(" "*35 + "🧠 IDA* ALGORITHM")
print("="*100)

ida_route = gmaps_style_route_ida_star(
    graph=graph,
    origin_name=origin_name,
    origin_coords=origin_coords,
    dest_name=dest_name,
    dest_coords=dest_coords,
    optimization_mode="time",
    departure_time=departure_time
)

if ida_route:
    print(f"\n✅ IDA* SUCCESS!")
    print(f"   Total Duration: {ida_route.total_time_minutes:.1f} minutes")
    print(f"   Total Cost: Rp {ida_route.total_cost:,}")
    print(f"   Total Distance: {ida_route.total_distance_km:.2f} km")
    print(f"   Segments: {len(ida_route.segments)}")
    print(f"   Transfers: {ida_route.num_transfers}")
else:
    print("\n❌ IDA* FAILED")

# Compare
print("\n" + "="*100)
print(" "*35 + "📊 COMPARISON RESULTS")
print("="*100)

if dijkstra_route and ida_route:
    print(f"\n{'Metric':<25} {'Dijkstra':>20} {'IDA*':>20} {'Match?':>15}")
    print("-" * 85)
    
    duration_match = "✅" if abs(dijkstra_route.total_time_minutes - ida_route.total_time_minutes) < 0.1 else "❌"
    print(f"{'Duration':<25} {dijkstra_route.total_time_minutes:>18.1f} min {ida_route.total_time_minutes:>18.1f} min {duration_match:>12}")
    
    cost_match = "✅" if dijkstra_route.total_cost == ida_route.total_cost else "❌"
    print(f"{'Cost':<25} {'Rp ' + f'{dijkstra_route.total_cost:,}':>20} {'Rp ' + f'{ida_route.total_cost:,}':>20} {cost_match:>12}")
    
    distance_match = "✅" if abs(dijkstra_route.total_distance_km - ida_route.total_distance_km) < 0.01 else "❌"
    print(f"{'Distance':<25} {dijkstra_route.total_distance_km:>18.2f} km {ida_route.total_distance_km:>18.2f} km {distance_match:>12}")
    
    segments_match = "✅" if len(dijkstra_route.segments) == len(ida_route.segments) else "❌"
    print(f"{'Segments':<25} {len(dijkstra_route.segments):>20} {len(ida_route.segments):>20} {segments_match:>12}")
    
    transfers_match = "✅" if dijkstra_route.num_transfers == ida_route.num_transfers else "❌"
    print(f"{'Transfers':<25} {dijkstra_route.num_transfers:>20} {ida_route.num_transfers:>20} {transfers_match:>12}")
    
    # Check if routes are identical
    print(f"\n{'='*85}")
    all_match = (duration_match == "✅" and cost_match == "✅" and 
                 segments_match == "✅" and transfers_match == "✅")
    
    if all_match:
        print("🎉 ROUTES ARE IDENTICAL! Both algorithms found the same optimal path.")
    else:
        print("⚠️  Routes differ. Investigating differences...")
        
    # Show detailed route comparison
    print(f"\n{'='*100}")
    print(" "*30 + "🗺️  DETAILED ROUTE COMPARISON")
    print(f"{'='*100}")
    
    print(f"\n{'Step':<5} {'Dijkstra Route':<45} {'IDA* Route':<45}")
    print("-" * 100)
    
    max_segments = max(len(dijkstra_route.segments), len(ida_route.segments))
    for i in range(max_segments):
        dijkstra_desc = ""
        ida_desc = ""
        
        if i < len(dijkstra_route.segments):
            seg = dijkstra_route.segments[i]
            dijkstra_desc = f"{seg.mode.value[:4]} {seg.from_stop.name[:20]} → {seg.to_stop.name[:15]}"
        
        if i < len(ida_route.segments):
            seg = ida_route.segments[i]
            ida_desc = f"{seg.mode.value[:4]} {seg.from_stop.name[:20]} → {seg.to_stop.name[:15]}"
        
        match = "✅" if dijkstra_desc == ida_desc else "⚠️"
        print(f"{i+1:<5} {dijkstra_desc:<45} {ida_desc:<45} {match}")
        
else:
    print("\n⚠️  Cannot compare - one or both algorithms failed")

print("\n" + "="*100)
print(" "*35 + "✅ COMPARISON COMPLETE")
print("="*100)

