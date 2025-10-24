"""
Dynamic Door-to-Door Routing System (Google Maps Style)
Accepts dynamic coordinate inputs and compares IDA* vs Dijkstra
"""

import json
import sys
from datetime import datetime
from typing import Optional, Tuple

from ida_star_routing.data_loader import load_network_data
from ida_star_routing.door_to_door import Location, DoorToDoorRouter, print_door_to_door_route
from ida_star_routing.dijkstra import DijkstraRouter
from ida_star_routing.data_structures import TransportationGraph, Route, RouteSegment, TransportationMode
from ida_star_routing.main import export_route_to_json


def parse_coordinates(coord_str: str) -> Tuple[float, float]:
    """
    Parse coordinates from various formats:
    - "lat, lon"
    - "lat,lon"
    - "(lat, lon)"
    - "lat lon"
    """
    # Remove parentheses and extra spaces
    coord_str = coord_str.strip().replace('(', '').replace(')', '')
    
    # Try comma separator
    if ',' in coord_str:
        parts = coord_str.split(',')
    else:
        # Try space separator
        parts = coord_str.split()
    
    if len(parts) != 2:
        raise ValueError("Coordinates must be in format: latitude, longitude")
    
    lat = float(parts[0].strip())
    lon = float(parts[1].strip())
    
    return (lat, lon)


def dynamic_door_to_door_routing(
    graph: TransportationGraph,
    origin_name: str,
    origin_coords: Tuple[float, float],
    dest_name: str,
    dest_coords: Tuple[float, float],
    algorithm: str = "both",  # "ida", "dijkstra", or "both"
    optimization_mode: str = "time",
    departure_time: Optional[datetime] = None
):
    """
    Dynamic door-to-door routing with algorithm comparison
    
    Args:
        graph: Transportation network
        origin_name: Name of origin
        origin_coords: (lat, lon) of origin
        dest_name: Name of destination
        dest_coords: (lat, lon) of destination
        algorithm: Which algorithm to use
        optimization_mode: Optimization criteria
        departure_time: When to depart
    """
    if departure_time is None:
        departure_time = datetime.now()
    
    print(f"\n{'='*90}")
    print(f"{'🗺️  DYNAMIC DOOR-TO-DOOR ROUTING (GOOGLE MAPS STYLE)':^90}")
    print(f"{'='*90}")
    
    print(f"\n📍 JOURNEY DETAILS:")
    print(f"   Origin:      {origin_name}")
    print(f"   Coordinates: {origin_coords[0]:.5f}, {origin_coords[1]:.5f}")
    print(f"\n   Destination: {dest_name}")
    print(f"   Coordinates: {dest_coords[0]:.5f}, {dest_coords[1]:.5f}")
    print(f"\n   Departure:   {departure_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Optimize by: {optimization_mode.upper()}")
    
    origin = Location(origin_name, origin_coords[0], origin_coords[1])
    destination = Location(dest_name, dest_coords[0], dest_coords[1])
    
    results = {}
    
    # Try IDA*
    if algorithm in ["ida", "both"]:
        print(f"\n{'='*90}")
        print(f"{'🔬 ALGORITHM 1: IDA* (Iterative Deepening A*)':^90}")
        print(f"{'='*90}")
        print(f"   Memory: O(d) - Very efficient")
        print(f"   Strategy: DFS with iterative deepening")
        print(f"   Best for: Single-mode routes, memory-constrained devices")
        
        try:
            from ida_star_routing.ida_star import IDAStarRouter
            ida_router = DoorToDoorRouter(graph, optimization_mode)
            ida_router.ida_router = IDAStarRouter(graph, optimization_mode)
            
            import time
            start_time = time.time()
            ida_route = ida_router.route(origin, destination, departure_time, max_walking_km=1.0)
            ida_time = time.time() - start_time
            
            if ida_route:
                print(f"\n✅ IDA* Route Found!")
                print(f"   Computation time: {ida_time:.4f} seconds")
                results['ida'] = {'route': ida_route, 'time': ida_time, 'success': True}
                print_door_to_door_route(ida_route)
            else:
                print(f"\n❌ IDA* could not find a route")
                results['ida'] = {'route': None, 'time': ida_time, 'success': False}
        
        except Exception as e:
            print(f"\n❌ IDA* Error: {e}")
            results['ida'] = {'route': None, 'time': 0, 'success': False, 'error': str(e)}
    
    # Try Dijkstra
    if algorithm in ["dijkstra", "both"]:
        print(f"\n{'='*90}")
        print(f"{'🔬 ALGORITHM 2: DIJKSTRA (With Multi-Modal Transfer)':^90}")
        print(f"{'='*90}")
        print(f"   Memory: O(V) - Moderate")
        print(f"   Strategy: Best-first search with all paths explored")
        print(f"   Best for: Multi-modal routes, guaranteed optimal solution")
        
        try:
            dijkstra_router = DijkstraRouter(graph, optimization_mode)
            
            # Find nearest stops
            print(f"\n🔍 Finding nearest stops to origin...")
            origin_stops = []
            for stop in graph.stops.values():
                from ida_star_routing.dijkstra import haversine_distance_km
                dist = haversine_distance_km(origin.lat, origin.lon, stop.lat, stop.lon)
                if dist <= 1.0:  # Within 1km
                    origin_stops.append((stop, dist))
            
            origin_stops.sort(key=lambda x: x[1])
            
            print(f"\n🔍 Finding nearest stops to destination...")
            dest_stops = []
            for stop in graph.stops.values():
                from ida_star_routing.dijkstra import haversine_distance_km
                dist = haversine_distance_km(destination.lat, destination.lon, stop.lat, stop.lon)
                if dist <= 1.0:  # Within 1km
                    dest_stops.append((stop, dist))
            
            dest_stops.sort(key=lambda x: x[1])
            
            if not origin_stops:
                print(f"❌ No stops within 1km of origin")
                results['dijkstra'] = {'route': None, 'time': 0, 'success': False}
            elif not dest_stops:
                print(f"❌ No stops within 1km of destination")
                results['dijkstra'] = {'route': None, 'time': 0, 'success': False}
            else:
                print(f"   Found {len(origin_stops)} origin stops, {len(dest_stops)} destination stops")
                
                import time
                start_time = time.time()
                
                # Try best combination
                best_route = None
                best_score = float('inf')
                
                for origin_stop, origin_dist in origin_stops[:3]:
                    for dest_stop, dest_dist in dest_stops[:3]:
                        route = dijkstra_router.search(origin_stop, dest_stop, departure_time)
                        
                        if route:
                            # Add walking segments
                            from ida_star_routing.door_to_door import DoorToDoorRouter as DTDRouter
                            dummy_router = DTDRouter(graph, optimization_mode)
                            
                            # Create complete route with walking
                            segments = []
                            current_time = departure_time
                            
                            # Walking to first stop
                            walk1 = dummy_router.create_walking_segment(
                                1, origin, 
                                Location(origin_stop.name, origin_stop.lat, origin_stop.lon),
                                current_time
                            )
                            segments.append(walk1)
                            current_time = walk1.arrival_time
                            
                            # Transit segments
                            for seg in route.segments:
                                seg.sequence = len(segments) + 1
                                seg.departure_time = current_time
                                seg.arrival_time = current_time + datetime.timedelta(minutes=seg.duration_minutes)
                                segments.append(seg)
                                current_time = seg.arrival_time
                            
                            # Walking from last stop
                            walk2 = dummy_router.create_walking_segment(
                                len(segments) + 1,
                                Location(dest_stop.name, dest_stop.lat, dest_stop.lon),
                                destination,
                                current_time
                            )
                            segments.append(walk2)
                            
                            # Create complete route
                            from ida_star_routing.data_structures import Route
                            complete_route = Route(route_id=1, segments=segments)
                            complete_route.calculate_metrics()
                            
                            if complete_route.optimization_score < best_score:
                                best_score = complete_route.optimization_score
                                best_route = complete_route
                
                dijkstra_time = time.time() - start_time
                
                if best_route:
                    print(f"\n✅ Dijkstra Route Found!")
                    print(f"   Computation time: {dijkstra_time:.4f} seconds")
                    results['dijkstra'] = {'route': best_route, 'time': dijkstra_time, 'success': True}
                    print_door_to_door_route(best_route)
                else:
                    print(f"\n❌ Dijkstra could not find a route")
                    results['dijkstra'] = {'route': None, 'time': dijkstra_time, 'success': False}
        
        except Exception as e:
            print(f"\n❌ Dijkstra Error: {e}")
            import traceback
            traceback.print_exc()
            results['dijkstra'] = {'route': None, 'time': 0, 'success': False, 'error': str(e)}
    
    # Comparison
    if algorithm == "both" and len(results) == 2:
        print(f"\n{'='*90}")
        print(f"{'📊 ALGORITHM COMPARISON':^90}")
        print(f"{'='*90}")
        
        print(f"\n{'Metric':<25} {'IDA*':<30} {'Dijkstra':<30}")
        print(f"{'-'*90}")
        
        # Success
        ida_success = "✅ Found" if results.get('ida', {}).get('success') else "❌ Not found"
        dijk_success = "✅ Found" if results.get('dijkstra', {}).get('success') else "❌ Not found"
        print(f"{'Route Found':<25} {ida_success:<30} {dijk_success:<30}")
        
        # Computation time
        ida_time = results.get('ida', {}).get('time', 0)
        dijk_time = results.get('dijkstra', {}).get('time', 0)
        print(f"{'Computation Time':<25} {f'{ida_time:.4f}s':<30} {f'{dijk_time:.4f}s':<30}")
        
        # If both found routes
        if results.get('ida', {}).get('success') and results.get('dijkstra', {}).get('success'):
            ida_route = results['ida']['route']
            dijk_route = results['dijkstra']['route']
            
            print(f"{'Total Time (min)':<25} {f'{ida_route.total_time_minutes:.1f}':<30} {f'{dijk_route.total_time_minutes:.1f}':<30}")
            print(f"{'Total Cost (Rp)':<25} {f'{ida_route.total_cost:,}':<30} {f'{dijk_route.total_cost:,}':<30}")
            print(f"{'Total Distance (km)':<25} {f'{ida_route.total_distance_km:.2f}':<30} {f'{dijk_route.total_distance_km:.2f}':<30}")
            print(f"{'Transfers':<25} {f'{ida_route.num_transfers}':<30} {f'{dijk_route.num_transfers}':<30}")
            print(f"{'Segments':<25} {f'{len(ida_route.segments)}':<30} {f'{len(dijk_route.segments)}':<30}")
            
            # Winner
            print(f"\n🏆 WINNER:")
            if dijk_route.total_time_minutes < ida_route.total_time_minutes:
                print(f"   Dijkstra found a faster route!")
                print(f"   Time saved: {ida_route.total_time_minutes - dijk_route.total_time_minutes:.1f} minutes")
            elif ida_route.total_time_minutes < dijk_route.total_time_minutes:
                print(f"   IDA* found a faster route!")
                print(f"   Time saved: {dijk_route.total_time_minutes - ida_route.total_time_minutes:.1f} minutes")
            else:
                print(f"   Both algorithms found equally optimal routes!")
    
    return results


def interactive_mode():
    """Interactive command-line interface for dynamic routing"""
    
    print(f"\n{'='*90}")
    print(f"{'🚀 DYNAMIC DOOR-TO-DOOR ROUTING SYSTEM':^90}")
    print(f"{'='*90}")
    print(f"{'Enter any coordinates in Palembang - system will find the best route!':^90}")
    print(f"{'='*90}")
    
    # Load network
    print(f"\n📂 Loading transportation network...")
    graph = load_network_data("dataset/network_data_complete.json")
    
    while True:
        try:
            print(f"\n{'─'*90}")
            print(f"📍 ORIGIN LOCATION")
            print(f"{'─'*90}")
            
            origin_name = input(f"Name: ").strip()
            if not origin_name:
                print(f"Using default: SMA Negeri 10 Palembang")
                origin_name = "SMA Negeri 10 Palembang"
                origin_coords = (-2.99361, 104.72556)
            else:
                coord_str = input(f"Coordinates (lat, lon): ").strip()
                origin_coords = parse_coordinates(coord_str)
            
            print(f"{'─'*90}")
            print(f"📍 DESTINATION LOCATION")
            print(f"{'─'*90}")
            
            dest_name = input(f"Name: ").strip()
            if not dest_name:
                print(f"Using default: Pasar Modern Plaju")
                dest_name = "Pasar Modern Plaju"
                dest_coords = (-3.01495, 104.807771)
            else:
                coord_str = input(f"Coordinates (lat, lon): ").strip()
                dest_coords = parse_coordinates(coord_str)
            
            print(f"\n⚙️  ROUTING OPTIONS")
            print(f"{'─'*90}")
            print(f"Algorithm:")
            print(f"  1. IDA* only (memory efficient)")
            print(f"  2. Dijkstra only (better for transfers)")
            print(f"  3. Both (compare)")
            
            algo_choice = input(f"\nSelect (1-3) [3]: ").strip() or "3"
            algo_map = {'1': 'ida', '2': 'dijkstra', '3': 'both'}
            algorithm = algo_map.get(algo_choice, 'both')
            
            print(f"\nOptimization:")
            print(f"  1. Time (fastest)")
            print(f"  2. Cost (cheapest)")
            print(f"  3. Transfers (minimum)")
            print(f"  4. Balanced")
            
            opt_choice = input(f"\nSelect (1-4) [1]: ").strip() or "1"
            opt_map = {'1': 'time', '2': 'cost', '3': 'transfers', '4': 'balanced'}
            optimization = opt_map.get(opt_choice, 'time')
            
            # Run routing
            results = dynamic_door_to_door_routing(
                graph=graph,
                origin_name=origin_name,
                origin_coords=origin_coords,
                dest_name=dest_name,
                dest_coords=dest_coords,
                algorithm=algorithm,
                optimization_mode=optimization
            )
            
            # Export
            export_choice = input(f"\n💾 Export results to JSON? (y/n): ").strip().lower()
            if export_choice == 'y':
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                for algo_name, data in results.items():
                    if data.get('success') and data.get('route'):
                        filename = f"route_{algo_name}_{timestamp}.json"
                        export_route_to_json(data['route'], filename)
            
            # Continue?
            cont = input(f"\n🔄 Plan another route? (y/n): ").strip().lower()
            if cont != 'y':
                break
        
        except KeyboardInterrupt:
            print(f"\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
            cont = input(f"\nTry again? (y/n): ").strip().lower()
            if cont != 'y':
                break


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test with user's example
        print(f"🧪 Testing with user's example: SMA 10 → Pasar Modern Plaju")
        
        graph = load_network_data("dataset/network_data_complete.json")
        
        results = dynamic_door_to_door_routing(
            graph=graph,
            origin_name="SMA Negeri 10 Palembang",
            origin_coords=(-2.99361, 104.72556),
            dest_name="Pasar Modern Plaju",
            dest_coords=(-3.01495, 104.807771),
            algorithm="both",
            optimization_mode="time"
        )
    else:
        # Interactive mode
        interactive_mode()

