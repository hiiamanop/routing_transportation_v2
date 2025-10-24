#!/usr/bin/env python3
"""
Script to extract all KMZ files, match with CSV data, and create public transport network
"""

import os
import zipfile
import pandas as pd
import numpy as np
from xml.etree import ElementTree as ET
from pathlib import Path
import json
from math import radians, sin, cos, sqrt, atan2

# Define paths
BASE_DIR = Path("/Users/ahmadnaufalmuzakki/Documents/KERJAAN/Meetsin.Id/2025/DFS/DFS_final")
DATASET_DIR = BASE_DIR / "dataset"
KMZ_DIR = DATASET_DIR / "kmz_file"

# Define all KMZ files to process
KMZ_FILES = {
    "feeder": [
        "Peta Angkot Feeder/Koridor 1 Bus Stop TK - TTB.kmz",
        "Peta Angkot Feeder/Koridor 2 Bus Stop AH - SB.kmz",
        "Peta Angkot Feeder/Koridor 3 Feeder (Asrama Haji - Talang Betutu).kmz",
        "Peta Angkot Feeder/Koridor 4 Feeder (Sta Polresta - Perum OPI).kmz",
        "Peta Angkot Feeder/Koridor 5 Feeder (DJKA -Terminal Plaju).kmz",
        "Peta Angkot Feeder/Koridor 6 Feeder (RSUD - Sukawitan).kmz",
        "Peta Angkot Feeder/Koridor 7 Feeder (Stadion Kamboja - Bukit Siguntang).kmz",
        "Peta Angkot Feeder/Koridor 8 (Asrama Haji - Talang Jambe) (1).kmz",
    ],
    "teman_bus": [
        "Peta Teman Bus/Koridor 2.kmz",
        "Peta Teman Bus/Koridor 5.kmz",
    ],
    "lrt": [
        "Peta LRT/Rute LRT.kmz",
    ]
}

# CSV file mappings
CSV_FILES = {
    "feeder": [
        "Angkot Feeder/Koridor 1 - Talang Kelapa - Talang Buruk.csv",
        "Angkot Feeder/Koridor 2 - Asrama Haji - Sematang Borang_.csv",
        "Angkot Feeder/Koridor 3 - Asrama Haji - Talang Betutu_updated.csv",
        "Angkot Feeder/Koridor 4 - Polresta - Perum OPI_updated.csv",
        "Angkot Feeder/Koridor 5 - DJKA - Terminal Plaju_.csv",
        "Angkot Feeder/Koridor 6 - RSUD - Sukawinatan.csv",
        "Angkot Feeder/Koridor 7 - Kamboja - Bukit Siguntang.csv",
        "Angkot Feeder/Koridor 8 - ASRAMA HAJI - TALANG JAMBE.csv",
    ],
    "teman_bus": [
        "Bis Teman Bus/koridor 2.csv",
        "Bis Teman Bus/Koridor 5.csv",
    ],
    "lrt": [
        "lrt/titik.csv",
    ]
}


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on the earth (in meters)"""
    R = 6371000  # Radius of the Earth in meters
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance


def extract_kmz(kmz_path):
    """Extract placemarks (stops) from KMZ file"""
    stops = []
    
    try:
        with zipfile.ZipFile(kmz_path, 'r') as kmz:
            # KMZ files contain a doc.kml file
            kml_file = None
            for name in kmz.namelist():
                if name.endswith('.kml'):
                    kml_file = name
                    break
            
            if kml_file:
                kml_data = kmz.read(kml_file)
                
                # Parse KML
                root = ET.fromstring(kml_data)
                
                # KML namespace
                ns = {'kml': 'http://www.opengis.net/kml/2.2'}
                
                # Find all Placemarks
                for placemark in root.findall('.//kml:Placemark', ns):
                    name_elem = placemark.find('kml:name', ns)
                    point = placemark.find('.//kml:Point/kml:coordinates', ns)
                    
                    if name_elem is not None and point is not None:
                        name = name_elem.text
                        coords = point.text.strip().split(',')
                        
                        if len(coords) >= 2:
                            lon = float(coords[0])
                            lat = float(coords[1])
                            stops.append({
                                'name': name,
                                'lon': lon,
                                'lat': lat
                            })
    
    except Exception as e:
        print(f"Error extracting {kmz_path}: {e}")
    
    return stops


def find_nearest_stop(lat, lon, kmz_stops, max_distance=500):
    """Find the nearest stop from KMZ data"""
    min_distance = float('inf')
    nearest_stop = None
    
    for stop in kmz_stops:
        distance = haversine_distance(lat, lon, stop['lat'], stop['lon'])
        if distance < min_distance:
            min_distance = distance
            nearest_stop = stop
    
    if min_distance <= max_distance:
        return nearest_stop['name'], min_distance
    
    return None, min_distance


def process_all_kmz_files():
    """Extract all KMZ files and return organized data"""
    all_kmz_data = {}
    
    print("\n=== EXTRACTING ALL KMZ FILES ===\n")
    
    for transport_type, kmz_list in KMZ_FILES.items():
        print(f"\nProcessing {transport_type.upper()}:")
        all_kmz_data[transport_type] = {}
        
        for kmz_file in kmz_list:
            kmz_path = KMZ_DIR / kmz_file
            if kmz_path.exists():
                print(f"  - Extracting: {kmz_file}")
                stops = extract_kmz(kmz_path)
                print(f"    Found {len(stops)} stops")
                all_kmz_data[transport_type][kmz_file] = stops
            else:
                print(f"  - WARNING: File not found: {kmz_file}")
    
    return all_kmz_data


def match_csv_with_kmz(csv_path, kmz_stops, koridor_name):
    """Match CSV stops with KMZ data"""
    print(f"\n  Processing: {csv_path.name}")
    
    try:
        # Read CSV
        df = pd.read_csv(csv_path)
        
        # Check columns
        if 'Ordinat_X' not in df.columns or 'Ordinat_Y' not in df.columns:
            print(f"    WARNING: Missing coordinate columns in {csv_path.name}")
            return None
        
        # Create matched data
        matched_stops = []
        
        for idx, row in df.iterrows():
            lon = row['Ordinat_X']
            lat = row['Ordinat_Y']
            
            # Get existing name if available
            existing_name = None
            if 'Deskripsi (Nama Halte dan Alamat)' in df.columns:
                existing_name = row['Deskripsi (Nama Halte dan Alamat)']
            
            # Check if name is valid (not generic like "Stop X")
            if pd.isna(existing_name) or existing_name == '' or existing_name.startswith('Stop '):
                # Find nearest from KMZ
                kmz_name, distance = find_nearest_stop(lat, lon, kmz_stops)
                if kmz_name:
                    final_name = kmz_name
                    print(f"    Matched: CSV point {idx+1} -> {kmz_name} (distance: {distance:.1f}m)")
                else:
                    final_name = f"{koridor_name} - Stop {idx+1}"
                    print(f"    No match: Creating name '{final_name}' (nearest: {distance:.1f}m)")
            else:
                final_name = existing_name
            
            matched_stops.append({
                'stop_id': f"{koridor_name.replace(' ', '_')}_{idx+1}",
                'stop_name': final_name,
                'lat': lat,
                'lon': lon,
                'route': koridor_name
            })
        
        print(f"    Matched {len(matched_stops)} stops")
        return matched_stops
    
    except Exception as e:
        print(f"    ERROR: {e}")
        return None


def build_network_data(all_stops):
    """Build network data structure for visualization"""
    nodes = []
    edges = []
    routes = {}
    
    # Group stops by route
    for stop in all_stops:
        route_name = stop['route']
        if route_name not in routes:
            routes[route_name] = []
        routes[route_name].append(stop)
    
    # Create nodes
    stop_id_map = {}
    node_id = 0
    
    for stop in all_stops:
        stop_id_map[stop['stop_id']] = node_id
        nodes.append({
            'id': node_id,
            'stop_id': stop['stop_id'],
            'name': stop['stop_name'],
            'lat': stop['lat'],
            'lon': stop['lon'],
            'route': stop['route']
        })
        node_id += 1
    
    # Create edges (connect consecutive stops on same route)
    for route_name, stops in routes.items():
        for i in range(len(stops) - 1):
            stop1 = stops[i]
            stop2 = stops[i + 1]
            
            node1_id = stop_id_map[stop1['stop_id']]
            node2_id = stop_id_map[stop2['stop_id']]
            
            # Calculate distance
            distance = haversine_distance(
                stop1['lat'], stop1['lon'],
                stop2['lat'], stop2['lon']
            )
            
            edges.append({
                'from': node1_id,
                'to': node2_id,
                'route': route_name,
                'distance': distance
            })
    
    return {
        'nodes': nodes,
        'edges': edges,
        'routes': list(routes.keys())
    }


def main():
    print("=" * 80)
    print("PUBLIC TRANSPORT NETWORK BUILDER")
    print("Palembang - Feeder, Teman Bus, LRT")
    print("=" * 80)
    
    # Step 1: Extract all KMZ files
    print("\n[STEP 1] Extracting all KMZ files...")
    all_kmz_data = process_all_kmz_files()
    
    # Step 2: Match CSV with KMZ
    print("\n[STEP 2] Matching CSV files with KMZ data...")
    all_matched_stops = []
    
    # Process Feeder
    print("\n--- FEEDER ANGKOT ---")
    for i, csv_file in enumerate(CSV_FILES['feeder']):
        csv_path = DATASET_DIR / csv_file
        koridor_name = f"Feeder Koridor {i+1}"
        
        # Get corresponding KMZ data
        kmz_file = KMZ_FILES['feeder'][i]
        if kmz_file in all_kmz_data['feeder']:
            kmz_stops = all_kmz_data['feeder'][kmz_file]
            matched = match_csv_with_kmz(csv_path, kmz_stops, koridor_name)
            if matched:
                all_matched_stops.extend(matched)
    
    # Process Teman Bus
    print("\n--- TEMAN BUS ---")
    for i, csv_file in enumerate(CSV_FILES['teman_bus']):
        csv_path = DATASET_DIR / csv_file
        koridor_num = 2 if i == 0 else 5
        koridor_name = f"Teman Bus Koridor {koridor_num}"
        
        # Get corresponding KMZ data
        kmz_file = KMZ_FILES['teman_bus'][i]
        if kmz_file in all_kmz_data['teman_bus']:
            kmz_stops = all_kmz_data['teman_bus'][kmz_file]
            matched = match_csv_with_kmz(csv_path, kmz_stops, koridor_name)
            if matched:
                all_matched_stops.extend(matched)
    
    # Process LRT
    print("\n--- LRT ---")
    csv_path = DATASET_DIR / CSV_FILES['lrt'][0]
    kmz_file = KMZ_FILES['lrt'][0]
    if kmz_file in all_kmz_data['lrt']:
        kmz_stops = all_kmz_data['lrt'][kmz_file]
        matched = match_csv_with_kmz(csv_path, kmz_stops, "LRT Sumsel")
        if matched:
            all_matched_stops.extend(matched)
    
    # Step 3: Build network
    print("\n[STEP 3] Building network data structure...")
    network_data = build_network_data(all_matched_stops)
    
    print(f"\n  Total nodes: {len(network_data['nodes'])}")
    print(f"  Total edges: {len(network_data['edges'])}")
    print(f"  Total routes: {len(network_data['routes'])}")
    print(f"\n  Routes:")
    for route in network_data['routes']:
        print(f"    - {route}")
    
    # Save network data
    output_file = DATASET_DIR / "network_data_complete.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(network_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SUCCESS] Network data saved to: {output_file}")
    
    # Save matched stops to CSV
    stops_df = pd.DataFrame(all_matched_stops)
    stops_csv = DATASET_DIR / "all_stops_matched.csv"
    stops_df.to_csv(stops_csv, index=False)
    print(f"[SUCCESS] Matched stops saved to: {stops_csv}")
    
    return network_data


if __name__ == "__main__":
    network_data = main()
    print("\n" + "=" * 80)
    print("COMPLETED!")
    print("=" * 80)

