#!/usr/bin/env python3
"""
Create Smart Bidirectional Network
Only Koridor 5 Feeder and LRT are bidirectional (linear)
All other routes remain one-way (circuit)
"""

import json
from pathlib import Path

def load_network_data(file_path: str) -> dict:
    """Load network data from JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_network_data(data: dict, file_path: str):
    """Save network data to JSON file"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def create_correct_bidirectional_network(network_data: dict) -> dict:
    """
    Create bidirectional network only for linear routes:
    - Koridor 5 Feeder (linear)
    - LRT Sumsel (linear)
    
    Keep all other routes as one-way (circuit)
    """
    print("🔧 CREATING CORRECT BIDIRECTIONAL NETWORK")
    print("="*60)
    
    # Define which routes are LINEAR (bidirectional)
    linear_routes = {
        "Feeder Koridor 5",  # Linear route
        "LRT Sumsel"         # Linear route
    }
    
    # All other routes are CIRCUIT (one-way)
    circuit_routes = {
        "Feeder Koridor 1",
        "Feeder Koridor 2", 
        "Feeder Koridor 3",
        "Feeder Koridor 4",
        "Feeder Koridor 6",
        "Feeder Koridor 7",
        "Feeder Koridor 8",
        "Teman Bus Koridor 2",
        "Teman Bus Koridor 5"
    }
    
    print(f"📊 Linear routes (bidirectional): {len(linear_routes)}")
    for route in linear_routes:
        print(f"   ➡️  {route}")
    
    print(f"\n📊 Circuit routes (one-way): {len(circuit_routes)}")
    for route in circuit_routes:
        print(f"   🔄 {route}")
    
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
        
        # Create reverse edge only for linear routes
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
    print("🔧 CORRECT SMART BIDIRECTIONAL NETWORK CREATOR")
    print("   Circuit routes = One-way (memutar)")
    print("   Linear routes = Bidirectional (tidak memutar)")
    print("   Only Koridor 5 Feeder and LRT are linear!")
    print("="*80)
    
    # Load original network
    input_file = "dataset/network_data_complete.json"
    output_file = "dataset/network_data_correct_bidirectional.json"
    
    print(f"📂 Loading original network from: {input_file}")
    network_data = load_network_data(input_file)
    
    print(f"   Nodes: {len(network_data['nodes'])}")
    print(f"   Edges: {len(network_data['edges'])}")
    
    # Create correct bidirectional network
    network_data = create_correct_bidirectional_network(network_data)
    
    # Save result
    print(f"\n💾 Saving correct bidirectional network to: {output_file}")
    save_network_data(network_data, output_file)
    
    print("\n✅ CONVERSION COMPLETE!")
    print(f"   Final nodes: {len(network_data['nodes'])}")
    print(f"   Final edges: {len(network_data['edges'])}")
    
    print("\n📋 STRATEGY:")
    print("   1. ✅ Circuit routes remain one-way (memutar)")
    print("   2. ✅ Only Koridor 5 Feeder & LRT become bidirectional")
    print("   3. ✅ Respects real-world route characteristics")
    print("   4. ✅ Optimizes network connectivity correctly")
    
    print(f"\n🎯 RESULT: Correct smart bidirectional network")
    print(f"   File: {output_file}")

if __name__ == "__main__":
    main()
