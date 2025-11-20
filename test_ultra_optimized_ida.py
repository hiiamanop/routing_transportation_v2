#!/usr/bin/env python3
"""
Test script for Ultra-Optimized IDA* algorithm
"""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from algorithms.ida_star_routing.data_loader import load_network_data
from algorithms.ida_star_routing.ida_star_balanced import gmaps_style_route_balanced_ida_star

def test_balanced_ida():
    """Test the balanced IDA* algorithm"""
    
    print("="*80)
    print("TESTING BALANCED IDA* ALGORITHM")
    print("="*80)
    
    # Load network
    print("\n1. Loading network...")
    try:
        json_path = "dataset/network_data_correct_bidirectional.json"
        graph = load_network_data(json_path)
        print(f"✅ Network loaded: {len(graph.stops)} stops, {len(graph.edges)} edges")
    except Exception as e:
        print(f"❌ Failed to load network: {e}")
        return
    
    # Test case: Palembang Icon to PTC
    print("\n2. Testing route: Palembang Icon → PTC")
    
    origin_name = "Palembang Icon"
    origin_coords = (-2.97930, 104.74510)
    dest_name = "Palembang Trade Center"
    dest_coords = (-2.95115, 104.76090)
    
    try:
        route = gmaps_style_route_balanced_ida_star(
            graph=graph,
            origin_name=origin_name,
            origin_coords=origin_coords,
            dest_name=dest_name,
            dest_coords=dest_coords,
            optimization_mode="time",
            departure_time=datetime.now(),
            max_walking_km=2.0
        )
        
        if route:
            print(f"✅ Route found!")
            print(f"   Total time: {route.total_time_minutes:.1f} minutes")
            print(f"   Total cost: Rp {route.total_cost:,}")
            print(f"   Total distance: {route.total_distance_km:.2f} km")
            print(f"   Segments: {len(route.segments)}")
            print(f"   Transfers: {route.num_transfers}")
            
            print(f"\n   Route details:")
            for i, seg in enumerate(route.segments, 1):
                print(f"   {i}. {seg.mode.value if hasattr(seg.mode, 'value') else seg.mode}: {seg.from_stop.name if hasattr(seg, 'from_stop') else 'Unknown'} → {seg.to_stop.name if hasattr(seg, 'to_stop') else 'Unknown'}")
                print(f"      Duration: {seg.duration_minutes:.1f} min, Cost: Rp {seg.cost:,}")
        else:
            print("❌ No route found")
            
    except Exception as e:
        print(f"❌ Error during routing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_balanced_ida()
