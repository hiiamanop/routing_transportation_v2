"""
Main Interface for IDA* Route Planning System
Run routing queries and export results
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .data_loader import load_network_data, find_stops_by_name
from .ida_star import IDAStarRouter, find_route
from .data_structures import Route, Stop, TransportationGraph


def print_route_summary(route: Route):
    """Print route summary in readable format"""
    print(f"\n" + "="*70)
    print(f"📋 ROUTE SUMMARY")
    print(f"="*70)
    print(f"Total Time:      {route.total_time_minutes:.1f} minutes ({route.total_time_minutes/60:.1f} hours)")
    print(f"Total Cost:      Rp {route.total_cost:,}")
    print(f"Total Distance:  {route.total_distance_km:.2f} km")
    print(f"Transfers:       {route.num_transfers}")
    print(f"Departure:       {route.departure_time.strftime('%H:%M:%S') if route.departure_time else 'N/A'}")
    print(f"Arrival:         {route.arrival_time.strftime('%H:%M:%S') if route.arrival_time else 'N/A'}")
    print(f"Score:           {route.optimization_score:.4f}")
    print(f"\n📍 ROUTE DETAILS ({len(route.segments)} segments):")
    print(f"-"*70)
    
    for seg in route.segments:
        mode_icon = {
            'LRT': '🚄',
            'TEMAN_BUS': '🚌',
            'FEEDER_ANGKOT': '🚐',
            'TRANSFER': '🚶',
            'WALK': '🚶'
        }.get(seg.mode.value, '🚗')
        
        print(f"\n{seg.sequence}. {mode_icon} {seg.mode.value} - {seg.route_name}")
        print(f"   From: {seg.from_stop.name}")
        print(f"   To:   {seg.to_stop.name}")
        print(f"   Time: {seg.duration_minutes:.1f} min | Cost: Rp {seg.cost:,} | Distance: {seg.distance_km:.2f} km")
        if seg.departure_time:
            print(f"   Depart: {seg.departure_time.strftime('%H:%M')} → Arrive: {seg.arrival_time.strftime('%H:%M')}")
    
    print(f"\n" + "="*70)


def export_route_to_json(route: Route, filename: str):
    """Export route to JSON file"""
    route_dict = route.to_dict()
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(route_dict, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Route exported to: {filename}")


def interactive_search(graph: TransportationGraph):
    """Interactive route search interface"""
    print(f"\n" + "="*70)
    print(f"🚌 PALEMBANG MULTI-MODAL ROUTE PLANNER")
    print(f"="*70)
    print(f"\nAvailable modes:")
    for mode, routes in graph.routes_by_mode.items():
        stops_count = sum(1 for s in graph.stops.values() if s.mode == mode)
        print(f"  - {mode.value}: {len(routes)} routes, {stops_count} stops")
    
    print(f"\n" + "-"*70)
    
    # Get origin
    print(f"\n📍 Enter ORIGIN (stop name or partial name):")
    origin_input = input(f"   >> ").strip()
    
    origin_matches = find_stops_by_name(graph, origin_input)
    
    if not origin_matches:
        print(f"❌ No stops found matching: {origin_input}")
        return None
    
    if len(origin_matches) > 1:
        print(f"\n🔍 Found {len(origin_matches)} matches:")
        for i, stop in enumerate(origin_matches[:10], 1):
            print(f"   {i}. {stop.name} ({stop.mode.value} - {stop.route})")
        
        choice = input(f"\nSelect stop (1-{min(10, len(origin_matches))}): ")
        try:
            origin = origin_matches[int(choice) - 1]
        except (ValueError, IndexError):
            print(f"❌ Invalid choice")
            return None
    else:
        origin = origin_matches[0]
    
    print(f"✅ Origin: {origin.name}")
    
    # Get destination
    print(f"\n📍 Enter DESTINATION (stop name or partial name):")
    dest_input = input(f"   >> ").strip()
    
    dest_matches = find_stops_by_name(graph, dest_input)
    
    if not dest_matches:
        print(f"❌ No stops found matching: {dest_input}")
        return None
    
    if len(dest_matches) > 1:
        print(f"\n🔍 Found {len(dest_matches)} matches:")
        for i, stop in enumerate(dest_matches[:10], 1):
            print(f"   {i}. {stop.name} ({stop.mode.value} - {stop.route})")
        
        choice = input(f"\nSelect stop (1-{min(10, len(dest_matches))}): ")
        try:
            destination = dest_matches[int(choice) - 1]
        except (ValueError, IndexError):
            print(f"❌ Invalid choice")
            return None
    else:
        destination = dest_matches[0]
    
    print(f"✅ Destination: {destination.name}")
    
    # Get optimization mode
    print(f"\n⚙️  Select OPTIMIZATION MODE:")
    print(f"   1. Time (fastest route)")
    print(f"   2. Cost (cheapest route)")
    print(f"   3. Transfers (minimum transfers)")
    print(f"   4. Balanced (all factors)")
    
    mode_choice = input(f"\nSelect mode (1-4) [default: 1]: ").strip() or "1"
    
    mode_map = {
        '1': 'time',
        '2': 'cost',
        '3': 'transfers',
        '4': 'balanced'
    }
    
    optimization_mode = mode_map.get(mode_choice, 'time')
    
    # Run search
    print(f"\n🔍 Searching for route...")
    print(f"   Optimization: {optimization_mode}")
    
    router = IDAStarRouter(graph, optimization_mode)
    route = router.search(origin, destination)
    
    if route:
        print_route_summary(route)
        
        # Ask to export
        export_choice = input(f"\n💾 Export route to JSON? (y/n): ").strip().lower()
        if export_choice == 'y':
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"route_{optimization_mode}_{timestamp}.json"
            export_route_to_json(route, filename)
        
        return route
    else:
        print(f"\n❌ No route found!")
        return None


def run_example_queries(graph: TransportationGraph):
    """Run example routing queries for testing"""
    print(f"\n" + "="*70)
    print(f"🧪 RUNNING EXAMPLE QUERIES")
    print(f"="*70)
    
    # Example 1: LRT route
    print(f"\n📝 Example 1: LRT Route (Bandara → DJKA)")
    route1 = find_route(graph, "Bandara", "DJKA", "time")
    if route1:
        print_route_summary(route1)
        export_route_to_json(route1, "example_lrt_route.json")
    
    # Example 2: Multi-modal if available
    print(f"\n📝 Example 2: Optimized by Cost")
    route2 = find_route(graph, "Bandara", "DJKA", "cost")
    if route2:
        print_route_summary(route2)
    
    # Example 3: Feeder route
    print(f"\n📝 Example 3: Feeder Route")
    feeder_stops = [s for s in graph.stops.values() if 'Feeder' in s.route]
    if len(feeder_stops) >= 2:
        start = feeder_stops[0]
        goal = feeder_stops[-1]
        route3 = find_route(graph, start.name, goal.name, "time")
        if route3:
            print_route_summary(route3)


def main():
    """Main entry point"""
    base_dir = Path(__file__).parent.parent
    json_path = base_dir / "dataset" / "network_data_complete.json"
    
    if not json_path.exists():
        print(f"❌ Network data not found: {json_path}")
        sys.exit(1)
    
    # Load network
    print(f"\n🚀 INITIALIZING IDA* ROUTING SYSTEM...")
    graph = load_network_data(str(json_path))
    
    print(f"\n✅ System ready!")
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "examples":
            run_example_queries(graph)
        elif command == "test":
            # Quick test
            print(f"\n🧪 Quick Test...")
            route = find_route(graph, "Bandara", "DJKA", "time")
            if route:
                print_route_summary(route)
        else:
            print(f"Unknown command: {command}")
            print(f"Usage: python -m ida_star_routing.main [examples|test]")
    else:
        # Interactive mode
        while True:
            try:
                route = interactive_search(graph)
                
                cont = input(f"\n🔄 Search another route? (y/n): ").strip().lower()
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
    main()

