#!/usr/bin/env python3
"""
Debug script to compare IDA* vs Dijkstra combinations
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from algorithms.ida_star_routing.data_loader import load_network_data
from core.gmaps_style_routing import find_nearest_stops_extended
from algorithms.ida_star_routing.dijkstra import DijkstraRouter
from algorithms.ida_star_routing.ida_star_multimodal import IDAStarMultiModalRouter
from datetime import datetime

def debug_combinations():
    """Debug IDA* vs Dijkstra combinations"""
    
    print("="*90)
    print("🔍 DEBUG: IDA* vs Dijkstra Combinations")
    print("="*90)
    
    # Load network
    print("📂 Loading network...")
    graph = load_network_data("dataset/network_data_correct_bidirectional.json")
    
    # Test coordinates
    origin_coords = (-2.985256, 104.732880)  # UNSRI
    dest_coords = (-2.95115, 104.76090)      # PTC
    
    print(f"\n📍 Route: UNSRI → PTC")
    print(f"   Origin: {origin_coords}")
    print(f"   Dest: {dest_coords}")
    
    # Find nearest stops
    print(f"\n🔍 Finding nearest stops...")
    origin_stops = find_nearest_stops_extended(graph, origin_coords[0], origin_coords[1])
    dest_stops = find_nearest_stops_extended(graph, dest_coords[0], dest_coords[1])
    
    print(f"\n📍 Origin stops (top 5):")
    for i, (stop, dist) in enumerate(origin_stops[:5]):
        print(f"   {i+1}. {stop.name} ({dist*1000:.0f}m)")
    
    print(f"\n📍 Dest stops (top 5):")
    for i, (stop, dist) in enumerate(dest_stops[:5]):
        print(f"   {i+1}. {stop.name} ({dist*1000:.0f}m)")
    
    # Test Dijkstra
    print(f"\n{'='*50}")
    print("🚀 DIJKSTRA RESULTS")
    print(f"{'='*50}")
    
    dijkstra_router = DijkstraRouter(graph, "time")
    dijkstra_results = []
    
    for i, (origin_stop, origin_dist) in enumerate(origin_stops[:5]):
        for j, (dest_stop, dest_dist) in enumerate(dest_stops[:5]):
            print(f"\n🔍 Dijkstra {i+1},{j+1}: {origin_stop.name} → {dest_stop.name}")
            
            transit_route = dijkstra_router.search(origin_stop, dest_stop, datetime.now())
            
            if transit_route:
                origin_walk_time = (origin_dist / 5.0) * 60
                dest_walk_time = (dest_dist / 5.0) * 60
                total_time = origin_walk_time + transit_route.total_time_minutes + dest_walk_time
                total_walking_distance = origin_dist + dest_dist
                
                score = total_time  # Same as Dijkstra scoring
                
                result = {
                    'origin_stop': origin_stop,
                    'origin_dist': origin_dist,
                    'dest_stop': dest_stop,
                    'dest_dist': dest_dist,
                    'transit_route': transit_route,
                    'total_time': total_time,
                    'total_walking_distance': total_walking_distance,
                    'score': score
                }
                
                dijkstra_results.append(result)
                
                print(f"   ✅ Found: {total_time:.1f} min, Rp {transit_route.total_cost:,}")
                print(f"      Walking: {total_walking_distance*1000:.0f}m, Score: {score:.1f}")
            else:
                print(f"   ❌ No route found")
    
    # Sort Dijkstra results by score
    dijkstra_results.sort(key=lambda x: x['score'])
    
    print(f"\n🏆 DIJKSTRA BEST RESULTS:")
    for i, result in enumerate(dijkstra_results[:3]):
        print(f"   {i+1}. Score: {result['score']:.1f}")
        print(f"      Origin: {result['origin_stop'].name} ({result['origin_dist']*1000:.0f}m)")
        print(f"      Dest: {result['dest_stop'].name} ({result['dest_dist']*1000:.0f}m)")
        print(f"      Walking: {result['total_walking_distance']*1000:.0f}m")
        print(f"      Transit: {result['transit_route'].total_time_minutes:.1f} min")
    
    # Test IDA*
    print(f"\n{'='*50}")
    print("🚀 IDA* RESULTS")
    print(f"{'='*50}")
    
    ida_router = IDAStarMultiModalRouter(graph, "time")
    ida_results = []
    
    for i, (origin_stop, origin_dist) in enumerate(origin_stops[:5]):
        for j, (dest_stop, dest_dist) in enumerate(dest_stops[:5]):
            print(f"\n🔍 IDA* {i+1},{j+1}: {origin_stop.name} → {dest_stop.name}")
            
            transit_route = ida_router.search(origin_stop, dest_stop, datetime.now(), max_iterations=1000, timeout_seconds=120.0)
            
            if transit_route:
                origin_walk_time = (origin_dist / 5.0) * 60
                dest_walk_time = (dest_dist / 5.0) * 60
                total_time = origin_walk_time + transit_route.total_time_minutes + dest_walk_time
                total_walking_distance = origin_dist + dest_dist
                
                score = total_time  # Same as Dijkstra scoring
                
                result = {
                    'origin_stop': origin_stop,
                    'origin_dist': origin_dist,
                    'dest_stop': dest_stop,
                    'dest_dist': dest_dist,
                    'transit_route': transit_route,
                    'total_time': total_time,
                    'total_walking_distance': total_walking_distance,
                    'score': score
                }
                
                ida_results.append(result)
                
                print(f"   ✅ Found: {total_time:.1f} min, Rp {transit_route.total_cost:,}")
                print(f"      Walking: {total_walking_distance*1000:.0f}m, Score: {score:.1f}")
            else:
                print(f"   ❌ No route found")
    
    # Sort IDA* results by score
    ida_results.sort(key=lambda x: x['score'])
    
    print(f"\n🏆 IDA* BEST RESULTS:")
    for i, result in enumerate(ida_results[:3]):
        print(f"   {i+1}. Score: {result['score']:.1f}")
        print(f"      Origin: {result['origin_stop'].name} ({result['origin_dist']*1000:.0f}m)")
        print(f"      Dest: {result['dest_stop'].name} ({result['dest_dist']*1000:.0f}m)")
        print(f"      Walking: {result['total_walking_distance']*1000:.0f}m")
        print(f"      Transit: {result['transit_route'].total_time_minutes:.1f} min")
    
    # Compare results
    print(f"\n{'='*50}")
    print("📊 COMPARISON")
    print(f"{'='*50}")
    
    if dijkstra_results and ida_results:
        dijkstra_best = dijkstra_results[0]
        ida_best = ida_results[0]
        
        print(f"🏆 Dijkstra Best:")
        print(f"   Origin: {dijkstra_best['origin_stop'].name} ({dijkstra_best['origin_dist']*1000:.0f}m)")
        print(f"   Dest: {dijkstra_best['dest_stop'].name} ({dijkstra_best['dest_dist']*1000:.0f}m)")
        print(f"   Walking: {dijkstra_best['total_walking_distance']*1000:.0f}m")
        print(f"   Score: {dijkstra_best['score']:.1f}")
        
        print(f"\n🏆 IDA* Best:")
        print(f"   Origin: {ida_best['origin_stop'].name} ({ida_best['origin_dist']*1000:.0f}m)")
        print(f"   Dest: {ida_best['dest_stop'].name} ({ida_best['dest_dist']*1000:.0f}m)")
        print(f"   Walking: {ida_best['total_walking_distance']*1000:.0f}m")
        print(f"   Score: {ida_best['score']:.1f}")
        
        if dijkstra_best['dest_stop'].name == ida_best['dest_stop'].name:
            print(f"\n✅ SAME DESTINATION STOP!")
        else:
            print(f"\n❌ DIFFERENT DESTINATION STOPS!")
            print(f"   Dijkstra uses: {dijkstra_best['dest_stop'].name}")
            print(f"   IDA* uses: {ida_best['dest_stop'].name}")

if __name__ == "__main__":
    debug_combinations()
