#!/usr/bin/env python3
"""
Comparison between Pure DFS and Dijkstra for Multimodal Routing
Research: PERANCANGAN SISTEM INFORMASI INTEGRASI OPERASIONAL
ANTAR MODA ANGKUTAN UMUM MENGGUNAKAN ALGORITMA DEPTH FIRST SEARCH (DFS) DI KOTA PALEMBANG
"""

import sys
import os
from datetime import datetime
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.algorithms.dfs_routing.dfs_multimodal import gmaps_style_route_dfs
from src.algorithms.ida_star_routing.ida_star_multimodal import gmaps_style_route_dijkstra

def compare_algorithms(origin_lat, origin_lon, dest_lat, dest_lon):
    """
    Compare Pure DFS vs Dijkstra algorithms
    """
    print("🔬 ALGORITHM COMPARISON STUDY")
    print("=" * 60)
    print(f"Origin: ({origin_lat:.6f}, {origin_lon:.6f})")
    print(f"Destination: ({dest_lat:.6f}, {dest_lon:.6f})")
    print("=" * 60)
    
    # Test Dijkstra
    print("\n🚀 Testing DIJKSTRA Algorithm")
    print("-" * 40)
    start_time = time.time()
    
    dijkstra_result = gmaps_style_route_dijkstra(
        origin_lat, origin_lon, dest_lat, dest_lon
    )
    
    dijkstra_time = time.time() - start_time
    
    # Test Pure DFS
    print("\n🚀 Testing PURE DFS Algorithm")
    print("-" * 40)
    start_time = time.time()
    
    dfs_result = gmaps_style_route_dfs(
        origin_lat, origin_lon, dest_lat, dest_lon
    )
    
    dfs_time = time.time() - start_time
    
    # Comparison Results
    print("\n📊 COMPARISON RESULTS")
    print("=" * 60)
    
    if dijkstra_result and dfs_result:
        print("✅ Both algorithms found routes!")
        
        # Dijkstra results
        print(f"\n🔵 DIJKSTRA:")
        print(f"   Execution time: {dijkstra_time:.2f} seconds")
        print(f"   Total cost: Rp {dijkstra_result['route'].total_cost:,.0f}")
        print(f"   Total time: {dijkstra_result['route'].total_time_minutes:.1f} minutes")
        print(f"   Walking distance: {dijkstra_result['total_walking_distance']*1000:.0f}m")
        print(f"   Segments: {len(dijkstra_result['route'].segments)}")
        
        # DFS results
        print(f"\n🔴 PURE DFS:")
        print(f"   Execution time: {dfs_time:.2f} seconds")
        print(f"   Total cost: Rp {dfs_result['route'].total_cost:,.0f}")
        print(f"   Total time: {dfs_result['route'].total_time_minutes:.1f} minutes")
        print(f"   Walking distance: {dfs_result['total_walking_distance']*1000:.0f}m")
        print(f"   Segments: {len(dfs_result['route'].segments)}")
        print(f"   Iterations: {dfs_result['iterations']}")
        print(f"   Max depth: {dfs_result['max_depth']}")
        
        # Analysis
        print(f"\n📈 ANALYSIS:")
        cost_diff = abs(dijkstra_result['route'].total_cost - dfs_result['route'].total_cost)
        cost_ratio = cost_diff / dijkstra_result['route'].total_cost * 100
        
        time_diff = abs(dijkstra_result['route'].total_time_minutes - dfs_result['route'].total_time_minutes)
        time_ratio = time_diff / dijkstra_result['route'].total_time_minutes * 100
        
        walk_diff = abs(dijkstra_result['total_walking_distance'] - dfs_result['total_walking_distance'])
        walk_ratio = walk_diff / dijkstra_result['total_walking_distance'] * 100
        
        print(f"   Cost difference: Rp {cost_diff:,.0f} ({cost_ratio:.1f}%)")
        print(f"   Time difference: {time_diff:.1f} min ({time_ratio:.1f}%)")
        print(f"   Walking difference: {walk_diff*1000:.0f}m ({walk_ratio:.1f}%)")
        print(f"   Speed ratio: {dijkstra_time/dfs_time:.2f}x")
        
        # Conclusion
        print(f"\n🎯 CONCLUSION:")
        if cost_ratio < 5 and time_ratio < 5 and walk_ratio < 10:
            print("   ✅ DFS achieved similar results to Dijkstra!")
            print("   📝 Suitable for research comparison")
        else:
            print("   ⚠️  DFS results differ significantly from Dijkstra")
            print("   📝 Needs further optimization")
            
    elif dijkstra_result and not dfs_result:
        print("❌ Dijkstra found route, but DFS failed")
        print("📝 DFS needs improvement")
        
    elif not dijkstra_result and dfs_result:
        print("❌ DFS found route, but Dijkstra failed")
        print("📝 Unexpected result - check Dijkstra implementation")
        
    else:
        print("❌ Both algorithms failed to find routes")
        print("📝 Check network connectivity")

if __name__ == "__main__":
    # Test case: UNSRI to PTC
    origin_lat = -2.985256
    origin_lon = 104.732880
    dest_lat = -2.95115
    dest_lon = 104.76090
    
    compare_algorithms(origin_lat, origin_lon, dest_lat, dest_lon)
