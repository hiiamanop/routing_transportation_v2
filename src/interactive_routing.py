"""
Interactive Dynamic Route Planning System
Input koordinat origin & destination secara dinamis
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime
from algorithms.ida_star_routing.data_loader import load_network_data
from core.gmaps_style_routing import gmaps_style_route, print_gmaps_route
from optimized_dfs_test import gmaps_style_route_optimized_dfs
import json

def get_float_input(prompt):
    """Get float input with validation"""
    while True:
        try:
            value = float(input(prompt))
            return value
        except ValueError:
            print("❌ Invalid input. Please enter a number.")

def main():
    print("="*100)
    print(" "*30 + "🗺️  INTERACTIVE ROUTE PLANNING")
    print(" "*25 + "Dynamic Multi-Modal Public Transport Routing")
    print("="*100)
    
    # Load network once
    print("\n📂 Loading network...")
    graph = load_network_data("../dataset/network_data_correct_bidirectional.json")
    print("✅ Network loaded successfully!")
    print(f"   📊 Complete Network: {len(graph.stops)} stops, {len(graph.edges)} edges")
    print(f"   🚌 Routes: 8 Feeder + 2 Teman Bus + 1 LRT = 11 routes")
    print(f"   🔄 Smart Bidirectional: Circuit routes one-way, Linear routes bidirectional")
    
    while True:
        print("\n" + "="*100)
        print("📍 ENTER ROUTE DETAILS")
        print("="*100)
        
        # Get origin
        print("\n🔵 ORIGIN (Asal):")
        origin_name = input("   Name: ").strip()
        if not origin_name:
            print("❌ Origin name cannot be empty!")
            continue
            
        print("   Coordinates:")
        origin_lat = get_float_input("      Latitude: ")
        origin_lon = get_float_input("      Longitude: ")
        
        # Get destination
        print("\n🔴 DESTINATION (Tujuan):")
        dest_name = input("   Name: ").strip()
        if not dest_name:
            print("❌ Destination name cannot be empty!")
            continue
            
        print("   Coordinates:")
        dest_lat = get_float_input("      Latitude: ")
        dest_lon = get_float_input("      Longitude: ")
        
        # Get departure time (optional)
        print("\n🕐 DEPARTURE TIME (default: now):")
        use_default = input("   Use current time? (Y/n): ").strip().lower()
        
        if use_default in ['n', 'no']:
            year = int(input("      Year (2025): ") or "2025")
            month = int(input("      Month (1-12): "))
            day = int(input("      Day (1-31): "))
            hour = int(input("      Hour (0-23): "))
            minute = int(input("      Minute (0-59): ") or "0")
            departure_time = datetime(year, month, day, hour, minute)
        else:
            departure_time = datetime.now()
        
        # Choose algorithm
        print("\n🔧 ALGORITHM:")
        print("   1. Dijkstra (Recommended - Fast & Reliable)")
        print("   2. Optimized DFS (Research - Heuristic + Iterative Deepening)")
        print("   3. Both (Compare Dijkstra vs Optimized DFS)")
        
        algo_choice = input("   Choose (1/2/3, default=1): ").strip() or "1"
        
        # Summary
        print("\n" + "="*100)
        print("📋 ROUTE SUMMARY")
        print("="*100)
        print(f"   🔵 From: {origin_name}")
        print(f"      📌 Lat: {origin_lat}, Lon: {origin_lon}")
        print(f"   🔴 To: {dest_name}")
        print(f"      📌 Lat: {dest_lat}, Lon: {dest_lon}")
        print(f"   🕐 Departure: {departure_time}")
        print(f"   🔧 Algorithm: {['Dijkstra', 'Optimized DFS', 'Both'][int(algo_choice)-1]}")
        
        confirm = input("\n   Proceed? (Y/n): ").strip().lower()
        if confirm in ['n', 'no']:
            print("   ❌ Cancelled.")
            continue
        
        # Run routing
        origin_coords = (origin_lat, origin_lon)
        dest_coords = (dest_lat, dest_lon)
        
        dijkstra_route = None
        dfs_route = None
        
        # Run Dijkstra
        if algo_choice in ['1', '3']:
            print("\n" + "="*100)
            print(" "*40 + "🚀 DIJKSTRA ALGORITHM")
            print("="*100)
            
            try:
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
                    print_gmaps_route(dijkstra_route, origin_name, dest_name)
                    print(f"\n✅ DIJKSTRA SUCCESS!")
                    print(f"   ⏱️  Total time: {dijkstra_route.total_time_minutes:.1f} min")
                    print(f"   💰 Total cost: Rp {dijkstra_route.total_cost:,}")
                    print(f"   🚶 Walking segments: {len([s for s in dijkstra_route.segments if s.mode == 'WALK'])}")
                    print(f"   🚌 Transit segments: {len([s for s in dijkstra_route.segments if s.mode != 'WALK'])}")
                else:
                    print("\n❌ DIJKSTRA: No route found")
            except Exception as e:
                print(f"\n❌ DIJKSTRA ERROR: {e}")
        
        # Run Optimized DFS
        if algo_choice in ['2', '3']:
            print("\n" + "="*100)
            print(" "*35 + "🔍 OPTIMIZED DFS ALGORITHM")
            print("="*100)
            print("   🧠 DFS with Heuristic (A* style)")
            print("   🔄 Iterative Deepening DFS")
            print("   ✂️  Best-First Ordering")
            print("   ✂️  Cost-based Pruning")
            print("   📚 Research: PERANCANGAN SISTEM INFORMASI INTEGRASI OPERASIONAL")
            print("   📚 ANTAR MODA ANGKUTAN UMUM MENGGUNAKAN ALGORITMA DFS")
            
            try:
                dfs_result = gmaps_style_route_optimized_dfs(
                    origin_lat=origin_lat,
                    origin_lon=origin_lon,
                    dest_lat=dest_lat,
                    dest_lon=dest_lon,
                    departure_time=departure_time,
                    optimization_mode="time"
                )
                
                if dfs_result:
                    dfs_route = dfs_result['route']
                    # Add missing attributes for compatibility
                    dfs_route.num_transfers = len([s for s in dfs_route.segments if s.mode != 'WALKING']) - 1
                    dfs_route.departure_time = dfs_route.segments[0].departure_time
                    dfs_route.arrival_time = dfs_route.segments[-1].arrival_time
                    
                    # Add missing attributes for compatibility
                    for seg in dfs_route.segments:
                        if not hasattr(seg, 'route_name'):
                            seg.route_name = getattr(seg, 'mode', 'Unknown')
                        if not hasattr(seg, 'from_stop'):
                            # Try to get from from_location
                            if hasattr(seg, 'from_location') and seg.from_location:
                                seg.from_stop = type('Location', (), {'name': seg.from_location.name})()
                            else:
                                seg.from_stop = type('Location', (), {'name': 'Unknown'})()
                        if not hasattr(seg, 'to_stop'):
                            # Try to get from to_location
                            if hasattr(seg, 'to_location') and seg.to_location:
                                seg.to_stop = type('Location', (), {'name': seg.to_location.name})()
                            else:
                                seg.to_stop = type('Location', (), {'name': 'Unknown'})()
                    
                    print_gmaps_route(dfs_route, origin_name, dest_name)
                    print(f"\n✅ OPTIMIZED DFS SUCCESS!")
                    print(f"   ⏱️  Total time: {dfs_route.total_time_minutes:.1f} min")
                    print(f"   💰 Total cost: Rp {dfs_route.total_cost:,}")
                    print(f"   🚶 Walking segments: {len([s for s in dfs_route.segments if s.mode == 'WALKING'])}")
                    print(f"   🚌 Transit segments: {len([s for s in dfs_route.segments if s.mode != 'WALKING'])}")
                    print(f"   🔍 Algorithm: {dfs_result['algorithm']}")
                    print(f"   🔄 Iterations: {dfs_result['iterations']}")
                    print(f"   📏 Max depth: {dfs_result['max_depth']}")
                    if 'pruned_paths' in dfs_result:
                        print(f"   ✂️  Pruned paths: {dfs_result['pruned_paths']}")
                else:
                    print("\n❌ OPTIMIZED DFS: No route found")
            except Exception as e:
                print(f"\n❌ OPTIMIZED DFS ERROR: {e}")
        
        # Compare if both algorithms
        successful_routes = []
        if dijkstra_route:
            successful_routes.append(("Dijkstra", dijkstra_route))
        if dfs_route:
            successful_routes.append(("Optimized DFS", dfs_route))
        
        if len(successful_routes) > 1:
            print("\n" + "="*80)
            print("📊 ALGORITHM COMPARISON SUMMARY")
            print("="*80)
            
            print(f"✅ {len(successful_routes)} algorithms found routes!")
            print()
            
            # Create comparison table
            print(f"{'Algorithm':<15} {'Time (min)':<12} {'Cost (Rp)':<15} {'Segments':<10}")
            print("-" * 60)
            
            for name, route in successful_routes:
                segments = len(route.segments)
                print(f"{name:<15} {route.total_time_minutes:<12.1f} {route.total_cost:<15,.0f} {segments:<10}")
            
            # Find best route
            best_time = min(successful_routes, key=lambda x: x[1].total_time_minutes)
            best_cost = min(successful_routes, key=lambda x: x[1].total_cost)
            
            print()
            print(f"🏆 Fastest: {best_time[0]} ({best_time[1].total_time_minutes:.1f} min)")
            print(f"💰 Cheapest: {best_cost[0]} (Rp {best_cost[1].total_cost:,.0f})")
            
            # Check if results are similar
            times = [route.total_time_minutes for _, route in successful_routes]
            costs = [route.total_cost for _, route in successful_routes]
            
            time_range = max(times) - min(times)
            cost_range = max(costs) - min(costs)
            
            if time_range < 1.0 and cost_range < 1000:
                print(f"   🎯 All results are nearly identical!")
            elif time_range < 5.0 and cost_range < 5000:
                print(f"   ✅ Results are reasonably similar")
            else:
                print(f"   ⚠️  Results differ significantly")
        
        # Save option
        if successful_routes:
            save = input("\n💾 Save route to JSON? (y/N): ").strip().lower()
            if save in ['y', 'yes']:
                # If multiple routes, let user choose which one to save
                if len(successful_routes) > 1:
                    print("\nWhich route to save?")
                    for i, (name, _) in enumerate(successful_routes, 1):
                        print(f"   {i}. {name}")
                    
                    choice = input("Choose (1-{}): ".format(len(successful_routes))).strip()
                    try:
                        route_idx = int(choice) - 1
                        if 0 <= route_idx < len(successful_routes):
                            selected_route = successful_routes[route_idx]
                        else:
                            selected_route = successful_routes[0]  # Default to first
                    except ValueError:
                        selected_route = successful_routes[0]  # Default to first
                else:
                    selected_route = successful_routes[0]
                
                route_to_save = selected_route[1]
                algo_name = selected_route[0].lower().replace(' ', '_').replace('*', 'star')
                
                filename = f"route_{origin_name.replace(' ', '_').lower()}_{dest_name.replace(' ', '_').lower()}_{algo_name}.json"
                
                # Convert to dict
                route_dict = {
                    "route_id": route_to_save.route_id,
                    "origin": origin_name,
                    "destination": dest_name,
                    "summary": {
                        "total_time_minutes": route_to_save.total_time_minutes,
                        "total_cost": route_to_save.total_cost,
                        "total_distance_km": route_to_save.total_distance_km,
                        "num_transfers": route_to_save.num_transfers,
                        "departure_time": str(route_to_save.segments[0].departure_time),
                        "arrival_time": str(route_to_save.segments[-1].arrival_time),
                    },
                    "segments": []
                }
                
                for seg in route_to_save.segments:
                    route_dict["segments"].append({
                        "sequence": seg.sequence,
                        "mode": seg.mode.value,
                        "route_name": seg.route_name,
                        "from_stop": seg.from_stop.name,
                        "to_stop": seg.to_stop.name,
                        "duration_minutes": seg.duration_minutes,
                        "cost": seg.cost,
                        "distance_km": seg.distance_km,
                    })
                
                with open(filename, 'w') as f:
                    json.dump(route_dict, f, indent=2)
                
                print(f"   ✅ Saved to: {filename}")
        
        # Continue or exit
        print("\n" + "="*100)
        cont = input("🔄 Plan another route? (Y/n): ").strip().lower()
        if cont in ['n', 'no']:
            print("\n✅ Thank you for using Interactive Route Planning!")
            print("="*100)
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

