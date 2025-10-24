"""
Google Maps Style Door-to-Door Routing
COMPLETE DYNAMIC INPUT SYSTEM
Works with ANY coordinates in Palembang
"""

import json
import sys
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List

from algorithms.ida_star_routing.data_loader import load_network_data
from algorithms.ida_star_routing.dijkstra import DijkstraRouter, haversine_distance_km
from algorithms.ida_star_routing.data_structures import (
    TransportationGraph, Route, RouteSegment, TransportationMode, Stop
)
from algorithms.ida_star_routing.door_to_door import Location


def find_nearest_stops_extended(graph: TransportationGraph, 
                                lat: float, lon: float, 
                                max_distance_km: float = 2.0,
                                top_k: int = 10) -> List[Tuple[Stop, float]]:
    """Find nearest stops with extended range"""
    distances = []
    
    for stop in graph.stops.values():
        dist = haversine_distance_km(lat, lon, stop.lat, stop.lon)
        if dist <= max_distance_km:
            distances.append((stop, dist))
    
    distances.sort(key=lambda x: x[1])
    return distances[:top_k]


def create_walking_segment(seq: int, from_loc: Location, to_loc: Location,
                          departure_time: datetime) -> RouteSegment:
    """Create walking segment"""
    dist_km = haversine_distance_km(from_loc.lat, from_loc.lon, to_loc.lat, to_loc.lon)
    duration_min = (dist_km / 5.0) * 60  # 5 km/h walking speed
    
    from_stop = Stop(-1, f"walk_{seq}", from_loc.name, from_loc.lat, from_loc.lon, 
                     "Walking", TransportationMode.WALK)
    to_stop = Stop(-2, f"walk_{seq}", to_loc.name, to_loc.lat, to_loc.lon,
                   "Walking", TransportationMode.WALK)
    
    return RouteSegment(
        sequence=seq,
        mode=TransportationMode.WALK,
        route_name="Walking",
        from_stop=from_stop,
        to_stop=to_stop,
        departure_time=departure_time,
        arrival_time=departure_time + timedelta(minutes=duration_min),
        duration_minutes=duration_min,
        cost=0,
        distance_km=dist_km
    )


def gmaps_style_route(
    graph: TransportationGraph,
    origin_name: str,
    origin_coords: Tuple[float, float],
    dest_name: str,
    dest_coords: Tuple[float, float],
    optimization_mode: str = "time",
    departure_time: Optional[datetime] = None,
    max_walking_km: float = 2.0
) -> Optional[Route]:
    """
    Complete Google Maps style routing
    
    Args:
        graph: Transportation network
        origin_name: Origin name
        origin_coords: (lat, lon)
        dest_name: Destination name
        dest_coords: (lat, lon)
        optimization_mode: Optimization criteria
        departure_time: When to depart
        max_walking_km: Maximum walking distance
    
    Returns:
        Complete route with walking + transit
    """
    if departure_time is None:
        departure_time = datetime.now()
    
    print(f"\n{'='*90}")
    print(f"{'🗺️  GOOGLE MAPS STYLE ROUTING':^90}")
    print(f"{'='*90}")
    
    print(f"\n📍 FROM: {origin_name}")
    print(f"   📌 {origin_coords[0]:.5f}, {origin_coords[1]:.5f}")
    
    print(f"\n📍 TO:   {dest_name}")
    print(f"   📌 {dest_coords[0]:.5f}, {dest_coords[1]:.5f}")
    
    print(f"\n⚙️  Settings:")
    print(f"   🕐 Departure: {departure_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"   🎯 Optimize:  {optimization_mode.upper()}")
    print(f"   🚶 Max walk:  {max_walking_km} km")
    
    # Find nearest stops
    print(f"\n{'─'*90}")
    print(f"STEP 1: Finding nearest transit stops")
    print(f"{'─'*90}")
    
    origin_stops = find_nearest_stops_extended(graph, origin_coords[0], origin_coords[1], max_walking_km)
    dest_stops = find_nearest_stops_extended(graph, dest_coords[0], dest_coords[1], max_walking_km)
    
    if not origin_stops:
        print(f"❌ No stops within {max_walking_km}km of origin")
        return None
    
    if not dest_stops:
        print(f"❌ No stops within {max_walking_km}km of destination")
        return None
    
    print(f"✅ Found {len(origin_stops)} origin stops, {len(dest_stops)} destination stops")
    print(f"\n   Nearest to origin:")
    for i, (stop, dist) in enumerate(origin_stops[:3], 1):
        print(f"      {i}. {stop.name} ({stop.mode.value}) - {dist*1000:.0f}m")
    
    print(f"\n   Nearest to destination:")
    for i, (stop, dist) in enumerate(dest_stops[:3], 1):
        print(f"      {i}. {stop.name} ({stop.mode.value}) - {dist*1000:.0f}m")
    
    # Find best route using Dijkstra
    print(f"\n{'─'*90}")
    print(f"STEP 2: Finding optimal transit route (Dijkstra algorithm)")
    print(f"{'─'*90}")
    
    router = DijkstraRouter(graph, optimization_mode)
    
    best_route = None
    best_score = float('inf')
    
    # Try combinations
    combinations_tried = 0
    max_combinations = min(5, len(origin_stops)) * min(5, len(dest_stops))
    
    print(f"🔍 Trying up to {max_combinations} route combinations...")
    
    for origin_stop, origin_dist in origin_stops[:5]:
        for dest_stop, dest_dist in dest_stops[:5]:
            combinations_tried += 1
            
            # Find transit route
            transit_route = router.search(origin_stop, dest_stop, departure_time)
            
            if transit_route:
                # Calculate total score including walking
                origin_walk_time = (origin_dist / 5.0) * 60  # 5 km/h
                dest_walk_time = (dest_dist / 5.0) * 60
                total_time = origin_walk_time + transit_route.total_time_minutes + dest_walk_time
                
                if optimization_mode == "time":
                    score = total_time
                elif optimization_mode == "cost":
                    score = transit_route.total_cost  # Walking is free
                else:
                    score = total_time + transit_route.total_cost / 1000
                
                if score < best_score:
                    best_score = score
                    best_route = {
                        'origin_stop': origin_stop,
                        'origin_dist': origin_dist,
                        'dest_stop': dest_stop,
                        'dest_dist': dest_dist,
                        'transit_route': transit_route,
                        'total_time': total_time
                    }
                    print(f"   ✓ Found route: {total_time:.1f} min, Rp {transit_route.total_cost:,}")
    
    print(f"\n   Checked {combinations_tried} combinations")
    
    if not best_route:
        print(f"❌ No viable route found")
        return None
    
    # Construct complete route
    print(f"\n{'─'*90}")
    print(f"STEP 3: Building complete door-to-door route")
    print(f"{'─'*90}")
    
    segments = []
    current_time = departure_time
    
    # Walking to first stop
    origin_loc = Location(origin_name, origin_coords[0], origin_coords[1])
    origin_stop_loc = Location(
        best_route['origin_stop'].name,
        best_route['origin_stop'].lat,
        best_route['origin_stop'].lon
    )
    
    walk1 = create_walking_segment(1, origin_loc, origin_stop_loc, current_time)
    segments.append(walk1)
    current_time = walk1.arrival_time
    
    print(f"✅ Segment 1: Walk to {best_route['origin_stop'].name} ({best_route['origin_dist']*1000:.0f}m)")
    
    # Transit segments
    for transit_seg in best_route['transit_route'].segments:
        transit_seg.sequence = len(segments) + 1
        transit_seg.departure_time = current_time
        transit_seg.arrival_time = current_time + timedelta(minutes=transit_seg.duration_minutes)
        segments.append(transit_seg)
        current_time = transit_seg.arrival_time
    
    print(f"✅ Segments 2-{len(segments)}: Transit ({len(best_route['transit_route'].segments)} segments)")
    
    # Walking from last stop
    dest_stop_loc = Location(
        best_route['dest_stop'].name,
        best_route['dest_stop'].lat,
        best_route['dest_stop'].lon
    )
    dest_loc = Location(dest_name, dest_coords[0], dest_coords[1])
    
    walk2 = create_walking_segment(len(segments) + 1, dest_stop_loc, dest_loc, current_time)
    segments.append(walk2)
    
    print(f"✅ Segment {len(segments)}: Walk to destination ({best_route['dest_dist']*1000:.0f}m)")
    
    # Create final route
    complete_route = Route(route_id=1, segments=segments)
    complete_route.calculate_metrics()
    complete_route.optimization_score = best_score
    
    return complete_route


def print_gmaps_route(route: Route, origin_name: str, dest_name: str):
    """Print route in Google Maps style"""
    
    print(f"\n{'='*90}")
    print(f"{'✅ ROUTE FOUND - GOOGLE MAPS STYLE':^90}")
    print(f"{'='*90}")
    
    # Header
    print(f"\n🗺️  {origin_name} → {dest_name}")
    print(f"{'─'*90}")
    
    # Summary
    walking_segs = [s for s in route.segments if s.mode == TransportationMode.WALK]
    transit_segs = [s for s in route.segments if s.mode != TransportationMode.WALK]
    
    total_walk_km = sum(s.distance_km for s in walking_segs)
    total_transit_km = sum(s.distance_km for s in transit_segs)
    
    print(f"\n📊 JOURNEY SUMMARY")
    print(f"   ⏱️  Total time:     {route.total_time_minutes:.0f} min ({route.total_time_minutes/60:.1f} hours)")
    print(f"   💰 Total cost:     Rp {route.total_cost:,}")
    print(f"   📏 Total distance: {route.total_distance_km:.2f} km")
    print(f"   🔄 Transfers:      {route.num_transfers}")
    print(f"")
    print(f"   🚶 Walking:   {total_walk_km:.2f} km ({len(walking_segs)} segments)")
    print(f"   🚌 Transit:   {total_transit_km:.2f} km ({len(transit_segs)} segments)")
    print(f"")
    print(f"   🕐 Depart:    {route.departure_time.strftime('%H:%M')}")
    print(f"   🕐 Arrive:    {route.arrival_time.strftime('%H:%M')}")
    
    # Detailed directions
    print(f"\n{'─'*90}")
    print(f"📍 TURN-BY-TURN DIRECTIONS")
    print(f"{'─'*90}")
    
    for i, seg in enumerate(route.segments, 1):
        # Icon
        if seg.mode == TransportationMode.WALK:
            icon = "🚶"
            action = "Walk"
        elif seg.mode == TransportationMode.LRT:
            icon = "🚄"
            action = "Take LRT"
        elif seg.mode == TransportationMode.TEMAN_BUS:
            icon = "🚌"
            action = "Take Teman Bus"
        elif seg.mode == TransportationMode.FEEDER_ANGKOT:
            icon = "🚐"
            action = "Take Angkot Feeder"
        elif seg.mode == TransportationMode.TRANSFER:
            icon = "🚶"
            action = "Transfer (walk)"
        else:
            icon = "🚗"
            action = "Travel"
        
        print(f"\n{i}. {icon} {action}")
        
        if seg.mode == TransportationMode.WALK:
            print(f"   Walk {seg.distance_km*1000:.0f} meters ({seg.duration_minutes:.0f} min)")
        else:
            print(f"   Route: {seg.route_name}")
            print(f"   Duration: {seg.duration_minutes:.1f} min | Cost: Rp {seg.cost:,} | Distance: {seg.distance_km:.2f} km")
        
        print(f"   From: {seg.from_stop.name}")
        print(f"   To:   {seg.to_stop.name}")
        
        if seg.departure_time:
            print(f"   ⏰ {seg.departure_time.strftime('%H:%M')} → {seg.arrival_time.strftime('%H:%M')}")
    
    print(f"\n{'='*90}")
    print(f"{'✅ HAVE A SAFE JOURNEY!':^90}")
    print(f"{'='*90}")


def interactive_routing():
    """Interactive routing interface"""
    
    print(f"\n{'='*90}")
    print(f"{'🚀 GOOGLE MAPS STYLE ROUTING - PALEMBANG':^90}")
    print(f"{'='*90}")
    print(f"{'Enter ANY coordinates in Palembang':^90}")
    print(f"{'System will find the best public transport route!':^90}")
    print(f"{'='*90}")
    
    # Load network
    print(f"\n📂 Loading Palembang transportation network...")
    graph = load_network_data("dataset/network_data_complete.json")
    
    while True:
        try:
            print(f"\n{'─'*90}")
            
            # Origin
            origin_name = input(f"\n📍 ORIGIN name: ").strip()
            if not origin_name:
                print(f"Using example: SMA Negeri 10 Palembang")
                origin_name = "SMA Negeri 10 Palembang"
                origin_coords = (-2.99361, 104.72556)
            else:
                lat_str = input(f"   Latitude:  ").strip()
                lon_str = input(f"   Longitude: ").strip()
                origin_coords = (float(lat_str), float(lon_str))
            
            # Destination
            dest_name = input(f"\n📍 DESTINATION name: ").strip()
            if not dest_name:
                print(f"Using example: Pasar Modern Plaju")
                dest_name = "Pasar Modern Plaju"
                dest_coords = (-3.01495, 104.807771)
            else:
                lat_str = input(f"   Latitude:  ").strip()
                lon_str = input(f"   Longitude: ").strip()
                dest_coords = (float(lat_str), float(lon_str))
            
            # Options
            print(f"\n⚙️  OPTIMIZATION:")
            print(f"   1. Time (fastest)")
            print(f"   2. Cost (cheapest)")
            print(f"   3. Balanced")
            
            opt_choice = input(f"\nSelect (1-3) [1]: ").strip() or "1"
            opt_map = {'1': 'time', '2': 'cost', '3': 'balanced'}
            optimization = opt_map.get(opt_choice, 'time')
            
            # Route
            route = gmaps_style_route(
                graph=graph,
                origin_name=origin_name,
                origin_coords=origin_coords,
                dest_name=dest_name,
                dest_coords=dest_coords,
                optimization_mode=optimization
            )
            
            if route:
                print_gmaps_route(route, origin_name, dest_name)
                
                # Export
                export_choice = input(f"\n💾 Export to JSON? (y/n): ").strip().lower()
                if export_choice == 'y':
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"gmaps_route_{timestamp}.json"
                    
                    route_dict = route.to_dict()
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(route_dict, f, indent=2, ensure_ascii=False)
                    
                    print(f"✅ Saved to: {filename}")
            
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


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test with user's example
        print(f"🧪 Testing with: SMA 10 → Pasar Modern Plaju")
        
        graph = load_network_data("dataset/network_data_complete.json")
        
        route = gmaps_style_route(
            graph=graph,
            origin_name="SMA Negeri 10 Palembang",
            origin_coords=(-2.99361, 104.72556),
            dest_name="Pasar Modern Plaju",
            dest_coords=(-3.01495, 104.807771),
            optimization_mode="time"
        )
        
        if route:
            print_gmaps_route(route, "SMA Negeri 10 Palembang", "Pasar Modern Plaju")
    else:
        interactive_routing()

