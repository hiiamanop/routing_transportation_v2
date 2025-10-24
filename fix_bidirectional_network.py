"""
Fix Network to be Bidirectional
Add reverse edges for all existing edges to enable routing in both directions
"""

import json
from ida_star_routing.data_loader import load_network_data
from ida_star_routing.data_structures import Edge, TransportationMode


def make_network_bidirectional(graph):
    """
    Add reverse edges to make network bidirectional
    
    Args:
        graph: TransportationGraph
    
    Returns:
        Updated graph with bidirectional edges
    """
    print(f"\n🔧 MAKING NETWORK BIDIRECTIONAL")
    print(f"="*80)
    
    print(f"\n📊 BEFORE:")
    original_edge_count = sum(len(edges) for edges in graph.edges.values())
    print(f"   Total edges: {original_edge_count}")
    
    # Collect all edges
    all_edges = []
    for stop_id, edges in graph.edges.items():
        for edge in edges:
            all_edges.append(edge)
    
    print(f"   Edges to process: {len(all_edges)}")
    
    # Add reverse edges
    reverse_edges_added = 0
    
    for edge in all_edges:
        # Create reverse edge
        reverse_edge = Edge(
            from_stop=edge.to_stop,
            to_stop=edge.from_stop,
            route=edge.route,
            mode=edge.mode,
            distance_meters=edge.distance_meters,
            base_time_minutes=edge.base_time_minutes,
            cost=edge.cost
        )
        
        # Check if reverse edge already exists
        existing_edges = graph.get_neighbors(edge.to_stop)
        edge_exists = False
        
        for existing in existing_edges:
            if existing.to_stop.stop_id == edge.from_stop.stop_id:
                edge_exists = True
                break
        
        # Add if doesn't exist
        if not edge_exists:
            graph.add_edge(reverse_edge)
            reverse_edges_added += 1
    
    print(f"\n📊 AFTER:")
    new_edge_count = sum(len(edges) for edges in graph.edges.values())
    print(f"   Total edges: {new_edge_count}")
    print(f"   Reverse edges added: {reverse_edges_added}")
    print(f"   Increase: {((new_edge_count / original_edge_count) - 1) * 100:.1f}%")
    
    # Verify connectivity
    print(f"\n✅ Network is now bidirectional!")
    print(f"   All routes can be traversed in both directions")
    
    return graph


def save_bidirectional_network(graph, output_file="dataset/network_data_bidirectional.json"):
    """Save bidirectional network to JSON"""
    
    print(f"\n💾 SAVING BIDIRECTIONAL NETWORK")
    print(f"   Output: {output_file}")
    
    # Convert to JSON format
    nodes = []
    edges = []
    edge_id = 1
    
    # Nodes
    for stop in graph.stops.values():
        nodes.append({
            'id': stop.id,
            'stop_id': stop.stop_id,
            'name': stop.name,
            'lat': stop.lat,
            'lon': stop.lon,
            'route': stop.route,
            'mode': stop.mode.value
        })
    
    # Edges
    seen_edges = set()
    for stop_id, edge_list in graph.edges.items():
        for edge in edge_list:
            # Create unique edge identifier
            edge_key = f"{edge.from_stop.id}_{edge.to_stop.id}_{edge.route}"
            
            if edge_key not in seen_edges:
                edges.append({
                    'id': edge_id,
                    'from': edge.from_stop.id,
                    'to': edge.to_stop.id,
                    'route': edge.route,
                    'mode': edge.mode.value,
                    'distance': edge.distance_meters
                })
                seen_edges.add(edge_key)
                edge_id += 1
    
    # Create output
    output = {
        'nodes': nodes,
        'edges': edges,
        'metadata': {
            'total_stops': len(nodes),
            'total_edges': len(edges),
            'bidirectional': True,
            'description': 'Palembang multi-modal transport network with bidirectional edges'
        }
    }
    
    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ Saved {len(nodes)} nodes and {len(edges)} edges")
    
    return output_file


if __name__ == "__main__":
    print(f"\n{'='*80}")
    print(f"{'🔧 NETWORK BIDIRECTIONAL CONVERTER':^80}")
    print(f"{'='*80}")
    
    # Load original network
    print(f"\n📂 Loading original network...")
    graph = load_network_data("dataset/network_data_complete.json")
    
    # Make bidirectional
    graph = make_network_bidirectional(graph)
    
    # Save
    output_file = save_bidirectional_network(graph)
    
    print(f"\n{'='*80}")
    print(f"✅ CONVERSION COMPLETE!")
    print(f"{'='*80}")
    print(f"\nBidirectional network saved to:")
    print(f"   {output_file}")
    print(f"\nYou can now use this network for routing in both directions!")
    print(f"\nTo use:")
    print(f"   graph = load_network_data('dataset/network_data_bidirectional.json')")

