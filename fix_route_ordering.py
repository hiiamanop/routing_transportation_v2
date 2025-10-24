#!/usr/bin/env python3
"""
Fix route ordering - ensure stops are connected in proper sequential order
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

BASE_DIR = Path("/Users/ahmadnaufalmuzakki/Documents/KERJAAN/Meetsin.Id/2025/DFS/DFS_final")
DATASET_DIR = BASE_DIR / "dataset"

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points"""
    R = 6371000  # Earth radius in meters
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def order_stops_sequentially(stops):
    """
    Order stops to form a sequential path (nearest neighbor algorithm)
    """
    if len(stops) <= 1:
        return stops
    
    ordered = [stops[0]]
    remaining = stops[1:].copy()
    
    while remaining:
        current = ordered[-1]
        # Find nearest stop to current
        min_dist = float('inf')
        nearest_idx = 0
        
        for i, stop in enumerate(remaining):
            dist = haversine_distance(
                current['lat'], current['lon'],
                stop['lat'], stop['lon']
            )
            if dist < min_dist:
                min_dist = dist
                nearest_idx = i
        
        ordered.append(remaining.pop(nearest_idx))
    
    return ordered

def fix_lrt_order(stops):
    """
    Fix LRT order based on known station sequence
    Bandara → Asrama Haji → Punti Kayu → RSUD → Garuda → Demang → 
    Bumi Sriwijaya → Dishub → Cinde → 16 Ilir → Polresta → Jakabaring → DJKA
    """
    correct_order = [
        "Bandara SMB 2",
        "Asrama Haji",
        "Punti Kayu",
        "RSDU Prov Sumsel",
        "Garuda Dempo",
        "Demang",
        "Bumi Sriwijaya",
        "Dishub",
        "Pasar Cinde",
        "Pasar 16 Ilir",
        "Polresta",
        "Jakabaring",
        "DJKA"
    ]
    
    ordered_stops = []
    for station_name in correct_order:
        for stop in stops:
            if station_name.lower() in stop['stop_name'].lower():
                ordered_stops.append(stop)
                break
    
    # Add any missing stops at the end
    for stop in stops:
        if stop not in ordered_stops:
            ordered_stops.append(stop)
    
    return ordered_stops

def rebuild_network_with_proper_order():
    """Rebuild network with properly ordered routes"""
    
    print("🔧 Fixing route ordering...")
    print("=" * 80)
    
    # Load existing stops
    stops_df = pd.read_csv(DATASET_DIR / 'all_stops_matched.csv')
    
    # Group by route
    routes = {}
    for route_name in stops_df['route'].unique():
        route_stops = stops_df[stops_df['route'] == route_name].to_dict('records')
        routes[route_name] = route_stops
    
    print(f"\nFound {len(routes)} routes\n")
    
    # Fix ordering for each route
    fixed_routes = {}
    for route_name, stops in routes.items():
        print(f"Processing: {route_name} ({len(stops)} stops)")
        
        # Special handling for LRT
        if "LRT" in route_name:
            ordered_stops = fix_lrt_order(stops)
            print(f"  → LRT: Using predefined order")
        else:
            # For other routes, use nearest neighbor
            ordered_stops = order_stops_sequentially(stops)
            print(f"  → Ordered using nearest neighbor algorithm")
        
        fixed_routes[route_name] = ordered_stops
    
    # Build new network
    print("\n" + "=" * 80)
    print("Building new network with fixed ordering...")
    
    all_stops = []
    node_id = 0
    
    # Create ordered nodes
    for route_name in sorted(fixed_routes.keys()):
        for i, stop in enumerate(fixed_routes[route_name]):
            stop['stop_id'] = f"{route_name.replace(' ', '_')}_{i+1}"
            stop['node_id'] = node_id
            all_stops.append(stop)
            node_id += 1
    
    # Create nodes list
    nodes = []
    for stop in all_stops:
        nodes.append({
            'id': stop['node_id'],
            'stop_id': stop['stop_id'],
            'name': stop['stop_name'],
            'lat': stop['lat'],
            'lon': stop['lon'],
            'route': stop['route']
        })
    
    # Create edges - connect consecutive stops on same route
    edges = []
    for route_name, stops in fixed_routes.items():
        for i in range(len(stops) - 1):
            stop1 = stops[i]
            stop2 = stops[i + 1]
            
            distance = haversine_distance(
                stop1['lat'], stop1['lon'],
                stop2['lat'], stop2['lon']
            )
            
            edges.append({
                'from': stop1['node_id'],
                'to': stop2['node_id'],
                'route': route_name,
                'distance': distance
            })
    
    network_data = {
        'nodes': nodes,
        'edges': edges,
        'routes': sorted(list(fixed_routes.keys()))
    }
    
    print(f"\n✅ Network rebuilt:")
    print(f"   - Nodes: {len(nodes)}")
    print(f"   - Edges: {len(edges)}")
    print(f"   - Routes: {len(network_data['routes'])}")
    
    # Show route details
    print("\n📍 Route Details:")
    for route_name in sorted(fixed_routes.keys()):
        stops = fixed_routes[route_name]
        print(f"\n{route_name}:")
        print(f"  {stops[0]['stop_name']} → ... → {stops[-1]['stop_name']}")
        print(f"  Total: {len(stops)} stops")
        
        # Show first 3 and last 3 for verification
        if len(stops) > 6:
            print(f"  Order: {stops[0]['stop_name']}")
            print(f"         {stops[1]['stop_name']}")
            print(f"         {stops[2]['stop_name']}")
            print(f"         ...")
            print(f"         {stops[-3]['stop_name']}")
            print(f"         {stops[-2]['stop_name']}")
            print(f"         {stops[-1]['stop_name']}")
    
    # Save network data
    output_file = DATASET_DIR / "network_data_complete.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(network_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Network saved to: {output_file}")
    
    # Save updated stops CSV
    stops_csv = pd.DataFrame(all_stops)
    stops_csv = stops_csv[['stop_id', 'stop_name', 'lat', 'lon', 'route']]
    stops_csv.to_csv(DATASET_DIR / 'all_stops_matched.csv', index=False)
    
    print(f"✅ Stops CSV updated")
    
    return network_data

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("FIXING ROUTE ORDER - Sequential Connections")
    print("=" * 80 + "\n")
    
    network_data = rebuild_network_with_proper_order()
    
    print("\n" + "=" * 80)
    print("✅ DONE! Routes now connect sequentially")
    print("=" * 80)

