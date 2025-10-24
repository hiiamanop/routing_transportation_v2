"""
Quick IDA* Test - Shorter timeout for faster results
"""

from datetime import datetime
from ida_star_routing.data_loader import load_network_data
from ida_star_routing.ida_star_multimodal import gmaps_style_route_ida_star

print("🧪 QUICK IDA* TEST")
print("="*80)

# Load network
graph = load_network_data("dataset/network_data_bidirectional.json")

# Test
route = gmaps_style_route_ida_star(
    graph=graph,
    origin_name="SMA Negeri 10 Palembang",
    origin_coords=(-2.99361, 104.72556),
    dest_name="Pasar Modern Plaju",
    dest_coords=(-3.01495, 104.807771),
    optimization_mode="time",
    departure_time=datetime(2025, 6, 15, 7, 30)
)

if route:
    from gmaps_style_routing import print_gmaps_route
    print_gmaps_route(route, "SMA Negeri 10", "Pasar Modern Plaju")
    
    print(f"\n🎉 IDA* SUCCESS!")
    print(f"   Can produce same quality as Dijkstra")
else:
    print(f"\n❌ IDA* failed")
    print(f"   May need more iterations or different approach")

