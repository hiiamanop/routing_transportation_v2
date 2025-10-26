"""
Flask API for Public Transport Routing System
Provides endpoints for Dijkstra and Optimized DFS routing algorithms
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
from datetime import datetime
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from algorithms.ida_star_routing.data_loader import load_network_data
from core.gmaps_style_routing import gmaps_style_route
from optimized_dfs_test import gmaps_style_route_optimized_dfs

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variable to store loaded network
network_graph = None

def load_network():
    """Load network data once at startup"""
    global network_graph
    if network_graph is None:
        print("Loading network data...")
        network_graph = load_network_data("dataset/network_data_correct_bidirectional.json")
        print(f"Network loaded: {len(network_graph.stops)} stops, {len(network_graph.edges)} edges")
    return network_graph

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "Public Transport Routing API is running",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/network/info', methods=['GET'])
def network_info():
    """Get network information"""
    graph = load_network()
    
    # Count stops by mode
    mode_counts = {}
    for stop in graph.stops.values():
        mode = stop.mode.value
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
    
    return jsonify({
        "total_stops": len(graph.stops),
        "total_edges": len(graph.edges),
        "stops_by_mode": mode_counts,
        "modes": list(mode_counts.keys())
    })

@app.route('/api/route', methods=['POST'])
def route_request():
    """
    Main routing endpoint
    Expected JSON payload:
    {
        "origin": {
            "name": "Origin Name",
            "lat": -2.985256,
            "lon": 104.732880
        },
        "destination": {
            "name": "Destination Name", 
            "lat": -2.95115,
            "lon": 104.76090
        },
        "algorithm": "dijkstra" | "dfs" | "both",
        "departure_time": "2025-01-01T10:00:00" (optional)
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['origin', 'destination', 'algorithm']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "error": f"Missing required field: {field}"
                }), 400
        
        origin = data['origin']
        destination = data['destination']
        algorithm = data['algorithm'].lower()
        
        # Validate coordinates
        if not all(key in origin for key in ['lat', 'lon']):
            return jsonify({"error": "Origin must have lat and lon"}), 400
        if not all(key in destination for key in ['lat', 'lon']):
            return jsonify({"error": "Destination must have lat and lon"}), 400
        
        # Parse departure time
        departure_time = datetime.now()
        if 'departure_time' in data and data['departure_time']:
            try:
                departure_time = datetime.fromisoformat(data['departure_time'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid departure_time format"}), 400
        
        # Load network
        graph = load_network()
        
        results = {}
        
        # Run Dijkstra
        if algorithm in ['dijkstra', 'both']:
            try:
                dijkstra_route = gmaps_style_route(
                    graph=graph,
                    origin_name=origin['name'],
                    origin_coords=(origin['lat'], origin['lon']),
                    dest_name=destination['name'],
                    dest_coords=(destination['lat'], destination['lon']),
                    optimization_mode="time",
                    departure_time=departure_time
                )
                
                if dijkstra_route:
                    results['dijkstra'] = {
                        "success": True,
                        "route": serialize_route(dijkstra_route, origin['name'], destination['name'], (origin['lat'], origin['lon']), (destination['lat'], destination['lon']))
                    }
                else:
                    results['dijkstra'] = {
                        "success": False,
                        "error": "No route found"
                    }
            except Exception as e:
                results['dijkstra'] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Run Optimized DFS
        if algorithm in ['dfs', 'both']:
            try:
                dfs_result = gmaps_style_route_optimized_dfs(
                    origin_lat=origin['lat'],
                    origin_lon=origin['lon'],
                    dest_lat=destination['lat'],
                    dest_lon=destination['lon'],
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
                            if hasattr(seg, 'from_location') and seg.from_location:
                                seg.from_stop = type('Location', (), {'name': seg.from_location.name})()
                            else:
                                seg.from_stop = type('Location', (), {'name': 'Unknown'})()
                        if not hasattr(seg, 'to_stop'):
                            if hasattr(seg, 'to_location') and seg.to_location:
                                seg.to_stop = type('Location', (), {'name': seg.to_location.name})()
                            else:
                                seg.to_stop = type('Location', (), {'name': 'Unknown'})()
                    
                    results['dfs'] = {
                        "success": True,
                        "route": serialize_route(dfs_route, origin['name'], destination['name'], (origin['lat'], origin['lon']), (destination['lat'], destination['lon'])),
                        "algorithm_info": {
                            "algorithm": dfs_result['algorithm'],
                            "iterations": dfs_result['iterations'],
                            "max_depth": dfs_result['max_depth'],
                            "pruned_paths": dfs_result.get('pruned_paths', 0)
                        }
                    }
                else:
                    results['dfs'] = {
                        "success": False,
                        "error": "No route found"
                    }
            except Exception as e:
                results['dfs'] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Add comparison if both algorithms were run
        if algorithm == 'both' and 'dijkstra' in results and 'dfs' in results:
            if results['dijkstra']['success'] and results['dfs']['success']:
                dijkstra_route = results['dijkstra']['route']
                dfs_route = results['dfs']['route']
                
                results['comparison'] = {
                    "dijkstra_time": dijkstra_route['summary']['total_time_minutes'],
                    "dfs_time": dfs_route['summary']['total_time_minutes'],
                    "dijkstra_cost": dijkstra_route['summary']['total_cost'],
                    "dfs_cost": dfs_route['summary']['total_cost'],
                    "dijkstra_segments": len(dijkstra_route['segments']),
                    "dfs_segments": len(dfs_route['segments']),
                    "fastest": "dijkstra" if dijkstra_route['summary']['total_time_minutes'] < dfs_route['summary']['total_time_minutes'] else "dfs",
                    "cheapest": "dijkstra" if dijkstra_route['summary']['total_cost'] < dfs_route['summary']['total_cost'] else "dfs"
                }
        
        return jsonify({
            "success": True,
            "results": results,
            "request_info": {
                "origin": origin,
                "destination": destination,
                "algorithm": algorithm,
                "departure_time": departure_time.isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

def serialize_route(route, origin_name, destination_name, origin_coords=None, dest_coords=None):
    """Convert route object to JSON-serializable format"""
    # Load stops data to get coordinates
    graph = load_network()
    stops_dict = {stop.name: stop for stop in graph.stops.values()}
    
    return {
        "route_id": route.route_id,
        "origin": origin_name,
        "destination": destination_name,
        "summary": {
            "total_time_minutes": route.total_time_minutes,
            "total_cost": route.total_cost,
            "total_distance_km": route.total_distance_km,
            "num_transfers": route.num_transfers,
            "departure_time": route.segments[0].departure_time.isoformat(),
            "arrival_time": route.segments[-1].arrival_time.isoformat(),
        },
        "segments": [
            {
                "sequence": seg.sequence,
                "mode": seg.mode.value if hasattr(seg.mode, 'value') else str(seg.mode),
                "route_name": getattr(seg, 'route_name', 'Unknown'),
                "from_stop": seg.from_stop.name if hasattr(seg, 'from_stop') else 'Unknown',
                "to_stop": seg.to_stop.name if hasattr(seg, 'to_stop') else 'Unknown',
                "duration_minutes": seg.duration_minutes,
                "cost": seg.cost,
                "distance_km": seg.distance_km,
                "departure_time": seg.departure_time.isoformat(),
                "arrival_time": seg.arrival_time.isoformat(),
                # Add coordinates for map visualization
                "from_coords": {
                    "lat": (
                        origin_coords[0] if seg.sequence == 1 and origin_coords else
                        stops_dict.get(seg.from_stop.name if hasattr(seg, 'from_stop') else 'Unknown', {}).lat if stops_dict.get(seg.from_stop.name if hasattr(seg, 'from_stop') else 'Unknown') else
                        seg.from_location.lat if hasattr(seg, 'from_location') and seg.from_location and hasattr(seg.from_location, 'lat') else None
                    ),
                    "lon": (
                        origin_coords[1] if seg.sequence == 1 and origin_coords else
                        stops_dict.get(seg.from_stop.name if hasattr(seg, 'from_stop') else 'Unknown', {}).lon if stops_dict.get(seg.from_stop.name if hasattr(seg, 'from_stop') else 'Unknown') else
                        seg.from_location.lon if hasattr(seg, 'from_location') and seg.from_location and hasattr(seg.from_location, 'lon') else None
                    )
                },
                "to_coords": {
                    "lat": (
                        dest_coords[0] if seg.sequence == len(route.segments) and dest_coords else
                        stops_dict.get(seg.to_stop.name if hasattr(seg, 'to_stop') else 'Unknown', {}).lat if stops_dict.get(seg.to_stop.name if hasattr(seg, 'to_stop') else 'Unknown') else
                        seg.to_location.lat if hasattr(seg, 'to_location') and seg.to_location and hasattr(seg.to_location, 'lat') else None
                    ),
                    "lon": (
                        dest_coords[1] if seg.sequence == len(route.segments) and dest_coords else
                        stops_dict.get(seg.to_stop.name if hasattr(seg, 'to_stop') else 'Unknown', {}).lon if stops_dict.get(seg.to_stop.name if hasattr(seg, 'to_stop') else 'Unknown') else
                        seg.to_location.lon if hasattr(seg, 'to_location') and seg.to_location and hasattr(seg.to_location, 'lon') else None
                    )
                }
            }
            for seg in route.segments
        ]
    }

@app.route('/api/stops', methods=['GET'])
def get_stops():
    """Get all stops for map visualization"""
    try:
        graph = load_network()
        
        stops = []
        for stop in graph.stops.values():
            stops.append({
                "id": stop.stop_id,
                "name": stop.name,
                "lat": stop.lat,
                "lon": stop.lon,
                "mode": stop.mode.value if hasattr(stop.mode, 'value') else str(stop.mode),
                "route": stop.route
            })
        
        return jsonify({
            "success": True,
            "stops": stops,
            "total": len(stops)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # Load network at startup
    load_network()
    
    print("="*60)
    print("🚀 Starting Public Transport Routing API")
    print("="*60)
    print("📡 Available endpoints:")
    print("   GET  /api/health - Health check")
    print("   GET  /api/network/info - Network information")
    print("   POST /api/route - Route planning")
    print("   GET  /api/stops - Get all stops")
    print("="*60)
    
    app.run(debug=True, host='0.0.0.0', port=5001)
