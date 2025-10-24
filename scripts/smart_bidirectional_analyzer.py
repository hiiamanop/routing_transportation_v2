#!/usr/bin/env python3
"""
Analyze Routes to Identify Circuit vs Linear Routes
Only make linear routes bidirectional, keep circuit routes as one-way
"""

import json
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

def haversine_distance_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers"""
    R = 6371000  # Radius of Earth in meters
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c  # Distance in meters

def load_network_data(file_path: str) -> dict:
    """Load network data from JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_routes(network_data: dict) -> dict:
    """
    Analyze each route to determine if it's circuit or linear
    
    Returns:
        Dictionary with route analysis results
    """
    print("🔍 ANALYZING ROUTES FOR CIRCUIT vs LINEAR")
    print("="*60)
    
    # Group edges by route
    routes = {}
    for edge in network_data['edges']:
        route_name = edge['route']
        if route_name not in routes:
            routes[route_name] = []
        routes[route_name].append(edge)
    
    # Create node lookup
    nodes = {node['id']: node for node in network_data['nodes']}
    
    route_analysis = {}
    
    for route_name, edges in routes.items():
        print(f"\n📍 Analyzing: {route_name}")
        
        # Get all unique stops in this route
        stop_ids = set()
        for edge in edges:
            stop_ids.add(edge['from'])
            stop_ids.add(edge['to'])
        
        # Convert to list and get coordinates
        stop_list = []
        for stop_id in stop_ids:
            node = nodes[stop_id]
            stop_list.append({
                'id': stop_id,
                'name': node['name'],
                'lat': node['lat'],
                'lon': node['lon']
            })
        
        print(f"   📊 Stops: {len(stop_list)}")
        
        if len(stop_list) < 2:
            print(f"   ⚠️  Skipping: Less than 2 stops")
            continue
        
        # Calculate distance between first and last stop
        first_stop = stop_list[0]
        last_stop = stop_list[-1]
        
        distance_km = haversine_distance_km(
            first_stop['lat'], first_stop['lon'],
            last_stop['lat'], last_stop['lon']
        )
        
        print(f"   📏 First stop: {first_stop['name']}")
        print(f"   📏 Last stop: {last_stop['name']}")
        print(f"   📏 Distance: {distance_km:.2f} km")
        
        # Determine if circuit or linear
        # Circuit: first and last stops are close (< 1km)
        # Linear: first and last stops are far apart (> 1km)
        is_circuit = distance_km < 1.0
        
        route_type = "CIRCUIT" if is_circuit else "LINEAR"
        print(f"   🎯 Type: {route_type}")
        
        route_analysis[route_name] = {
            'type': route_type,
            'is_circuit': is_circuit,
            'stops': stop_list,
            'first_stop': first_stop,
            'last_stop': last_stop,
            'distance_km': distance_km,
            'edges': edges
        }
    
    return route_analysis

def create_smart_bidirectional_network(network_data: dict, route_analysis: dict) -> dict:
    """
    Create bidirectional network only for linear routes
    Keep circuit routes as one-way
    """
    print("\n🔧 CREATING SMART BIDIRECTIONAL NETWORK")
    print("="*60)
    
    # Separate circuit and linear routes
    circuit_routes = []
    linear_routes = []
    
    for route_name, analysis in route_analysis.items():
        if analysis['is_circuit']:
            circuit_routes.append(route_name)
        else:
            linear_routes.append(route_name)
    
    print(f"📊 Circuit routes: {len(circuit_routes)}")
    for route in circuit_routes:
        print(f"   🔄 {route}")
    
    print(f"\n📊 Linear routes: {len(linear_routes)}")
    for route in linear_routes:
        print(f"   ➡️  {route}")
    
    # Create new edges list
    new_edges = []
    
    # Keep all original edges
    for edge in network_data['edges']:
        new_edges.append(edge)
    
    # Add reverse edges only for linear routes
    reverse_count = 0
    for edge in network_data['edges']:
        route_name = edge['route']
        
        # Skip if this is a circuit route
        if route_name in circuit_routes:
            print(f"   🔒 Keeping circuit route one-way: {route_name}")
            continue
        
        # Skip walking connections and existing reverse edges
        if edge.get('is_reverse_connection', False) or edge.get('is_reverse', False):
            continue
        
        # Create reverse edge for linear routes
        reverse_edge = {
            "from": edge['to'],
            "to": edge['from'],
            "route": edge["route"],
            "distance": edge["distance"],
            "is_reverse": True
        }
        new_edges.append(reverse_edge)
        reverse_count += 1
        print(f"   🔄 Adding reverse for linear route: {route_name}")
    
    print(f"\n📊 Summary:")
    print(f"   🔒 Circuit routes (one-way): {len(circuit_routes)}")
    print(f"   🔄 Linear routes (bidirectional): {len(linear_routes)}")
    print(f"   ➕ Reverse edges added: {reverse_count}")
    
    # Update network
    network_data['edges'] = new_edges
    
    return network_data

def main():
    print("="*80)
    print("🔍 SMART BIDIRECTIONAL NETWORK CREATOR")
    print("   Circuit routes = One-way (memutar)")
    print("   Linear routes = Bidirectional (tidak memutar)")
    print("="*80)
    
    # Load original network
    input_file = "dataset/network_data_complete.json"
    output_file = "dataset/network_data_smart_bidirectional.json"
    
    print(f"📂 Loading original network from: {input_file}")
    network_data = load_network_data(input_file)
    
    print(f"   Nodes: {len(network_data['nodes'])}")
    print(f"   Edges: {len(network_data['edges'])}")
    
    # Analyze routes
    route_analysis = analyze_routes(network_data)
    
    # Create smart bidirectional network
    network_data = create_smart_bidirectional_network(network_data, route_analysis)
    
    # Save result
    print(f"\n💾 Saving smart bidirectional network to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(network_data, f, indent=2, ensure_ascii=False)
    
    print("\n✅ CONVERSION COMPLETE!")
    print(f"   Final nodes: {len(network_data['nodes'])}")
    print(f"   Final edges: {len(network_data['edges'])}")
    
    print("\n📋 STRATEGY:")
    print("   1. ✅ Circuit routes remain one-way (memutar)")
    print("   2. ✅ Linear routes become bidirectional")
    print("   3. ✅ Respects real-world route characteristics")
    print("   4. ✅ Optimizes network connectivity")
    
    print(f"\n🎯 RESULT: Smart bidirectional network")
    print(f"   File: {output_file}")

if __name__ == "__main__":
    main()
