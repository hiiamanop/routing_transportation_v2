"""
Data Loader - Load Palembang transportation network data
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
from math import radians, sin, cos, sqrt, atan2

from .data_structures import (
    TransportationMode,
    Stop,
    Edge,
    TransferPoint,
    TransportationGraph,
    DEFAULT_COSTS,
    DEFAULT_SPEEDS
)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points in meters using Haversine formula
    """
    R = 6371000  # Earth radius in meters
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def determine_mode(route_name: str) -> TransportationMode:
    """Determine transportation mode from route name"""
    route_lower = route_name.lower()
    
    if 'lrt' in route_lower:
        return TransportationMode.LRT
    elif 'teman bus' in route_lower:
        return TransportationMode.TEMAN_BUS
    elif 'feeder' in route_lower:
        return TransportationMode.FEEDER_ANGKOT
    else:
        return TransportationMode.FEEDER_ANGKOT  # Default


def load_network_data(json_path: str) -> TransportationGraph:
    """
    Load transportation network from JSON file
    
    Args:
        json_path: Path to network_data_complete.json
    
    Returns:
        TransportationGraph with all stops, edges, and transfer points
    """
    print(f"📂 Loading network data from: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    graph = TransportationGraph()
    
    # Skip circuit routes - only process point-to-point
    circuit_routes = set(data.get('circuit_routes', []))
    print(f"⚠️  Skipping {len(circuit_routes)} circuit routes (focus on point-to-point)")
    
    # Load all stops (nodes)
    print(f"\n1️⃣ Loading stops...")
    for node_data in data['nodes']:
        route_name = node_data['route']
        
        # Skip circuit routes
        if route_name in circuit_routes:
            continue
        
        mode = determine_mode(route_name)
        
        stop = Stop(
            id=node_data['id'],
            stop_id=node_data['stop_id'],
            name=node_data['name'],
            lat=node_data['lat'],
            lon=node_data['lon'],
            route=route_name,
            mode=mode
        )
        
        graph.add_stop(stop)
        
        # Group by mode
        if mode not in graph.routes_by_mode:
            graph.routes_by_mode[mode] = []
        if route_name not in graph.routes_by_mode[mode]:
            graph.routes_by_mode[mode].append(route_name)
    
    print(f"   ✅ Loaded {len(graph.stops)} stops")
    for mode, routes in graph.routes_by_mode.items():
        print(f"   - {mode.value}: {len(routes)} routes")
    
    # Load edges (connections between stops)
    print(f"\n2️⃣ Loading edges...")
    edges_loaded = 0
    
    for edge_data in data['edges']:
        route_name = edge_data['route']
        
        # Skip circuit routes
        if route_name in circuit_routes:
            continue
        
        # Skip return connections
        if edge_data.get('is_return', False):
            continue
        
        from_node_id = edge_data['from']
        to_node_id = edge_data['to']
        
        # Find corresponding stops
        from_stop = None
        to_stop = None
        
        for stop in graph.stops.values():
            if stop.id == from_node_id:
                from_stop = stop
            if stop.id == to_node_id:
                to_stop = stop
            if from_stop and to_stop:
                break
        
        if not from_stop or not to_stop:
            continue
        
        mode = determine_mode(route_name)
        distance_meters = edge_data['distance']
        
        # Calculate base time (distance / speed)
        speed_kmh = DEFAULT_SPEEDS[mode]
        base_time_minutes = (distance_meters / 1000) / speed_kmh * 60
        
        # Get cost
        cost = DEFAULT_COSTS[mode]
        
        edge = Edge(
            from_stop=from_stop,
            to_stop=to_stop,
            route=route_name,
            mode=mode,
            distance_meters=distance_meters,
            base_time_minutes=base_time_minutes,
            cost=cost
        )
        
        graph.add_edge(edge)
        edges_loaded += 1
    
    print(f"   ✅ Loaded {edges_loaded} edges")
    
    # Detect transfer points (stops where multiple routes meet)
    print(f"\n3️⃣ Detecting transfer points...")
    
    # Group stops by location (nearby stops)
    location_groups = defaultdict(list)
    
    for stop in graph.stops.values():
        # Round coordinates to group nearby stops
        loc_key = (round(stop.lat, 4), round(stop.lon, 4))
        location_groups[loc_key].append(stop)
    
    transfer_count = 0
    for loc, stops in location_groups.items():
        if len(stops) > 1:
            # Multiple stops at same location = transfer point
            routes = set(s.route for s in stops)
            modes = set(s.mode for s in stops)
            
            if len(modes) > 1:  # Different modes available
                # Use first stop as transfer location
                transfer = TransferPoint(
                    location=stops[0],
                    available_modes=list(modes),
                    transfer_time_minutes=5.0  # Default 5 minutes
                )
                
                # Add transfer point for all stops at this location
                for stop in stops:
                    graph.add_transfer_point(transfer)
                
                transfer_count += 1
    
    print(f"   ✅ Detected {transfer_count} transfer points")
    
    # Print summary
    print(f"\n" + "="*60)
    print(f"📊 NETWORK SUMMARY")
    print(f"="*60)
    print(f"Stops:            {len(graph.stops)}")
    print(f"Edges:            {sum(len(e) for e in graph.edges.values())}")
    print(f"Transfer Points:  {len(graph.transfer_points)}")
    print(f"Routes by Mode:")
    for mode, routes in graph.routes_by_mode.items():
        stops_count = sum(1 for s in graph.stops.values() if s.mode == mode)
        print(f"  - {mode.value}: {len(routes)} routes, {stops_count} stops")
    print(f"="*60)
    
    return graph


def find_stops_by_name(graph: TransportationGraph, search_term: str) -> List[Stop]:
    """
    Find stops matching search term
    
    Args:
        graph: Transportation graph
        search_term: Search string (case-insensitive)
    
    Returns:
        List of matching stops
    """
    search_lower = search_term.lower()
    matches = []
    
    for stop in graph.stops.values():
        if search_lower in stop.name.lower():
            matches.append(stop)
    
    return matches


def get_route_stops(graph: TransportationGraph, route_name: str) -> List[Stop]:
    """Get all stops on a specific route"""
    stops = [s for s in graph.stops.values() if s.route == route_name]
    # Sort by ID to maintain order
    return sorted(stops, key=lambda s: s.id)


def export_graph_summary(graph: TransportationGraph, output_path: str):
    """Export graph summary to JSON file"""
    summary = {
        'statistics': {
            'total_stops': len(graph.stops),
            'total_edges': sum(len(edges) for edges in graph.edges.values()),
            'total_transfer_points': len(graph.transfer_points)
        },
        'modes': {
            mode.value: {
                'routes': routes,
                'stops': sum(1 for s in graph.stops.values() if s.mode == mode)
            }
            for mode, routes in graph.routes_by_mode.items()
        },
        'sample_stops': [
            stop.to_dict() 
            for stop in list(graph.stops.values())[:10]
        ],
        'transfer_points': [
            {
                'location': tp.location.name,
                'modes': [m.value for m in tp.available_modes],
                'transfer_time': tp.transfer_time_minutes
            }
            for tp in list(graph.transfer_points.values())[:10]
        ]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Graph summary exported to: {output_path}")


if __name__ == "__main__":
    # Test loading
    import sys
    from pathlib import Path
    
    base_dir = Path(__file__).parent.parent
    json_path = base_dir / "dataset" / "network_data_complete.json"
    
    if json_path.exists():
        graph = load_network_data(str(json_path))
        
        # Export summary
        output_path = base_dir / "ida_star_routing" / "graph_summary.json"
        export_graph_summary(graph, str(output_path))
        
        # Test search
        print(f"\n🔍 Testing stop search...")
        results = find_stops_by_name(graph, "terminal")
        print(f"Found {len(results)} stops matching 'terminal':")
        for stop in results[:5]:
            print(f"  - {stop.name} ({stop.mode.value})")
    else:
        print(f"❌ Network data file not found: {json_path}")
        sys.exit(1)

