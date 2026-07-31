"""
Flask API for Public Transport Routing System
Provides endpoints for Dijkstra and Optimized DFS routing algorithms
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
from datetime import datetime, timezone, timedelta
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from algorithms.ida_star_routing.data_loader import load_network_data
from core.gmaps_style_routing import gmaps_style_route, find_route_alternatives
from algorithms.dfs_routing.optimized_dfs_test import gmaps_style_route_optimized_dfs
from algorithms.ida_star_routing.ida_star_balanced import gmaps_style_route_balanced_ida_star
from algorithms.ida_star_routing.ida_star_with_fallback import gmaps_style_route_ida_star_with_fallback
from core import service_model

app = Flask(__name__)
# Enable CORS for all routes with explicit configuration
CORS(app, 
     origins="*",
     methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
     allow_headers=["Content-Type", "Authorization"
     "", "X-Requested-With"],
     supports_credentials=False,
     max_age=3600)

@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS,PUT,DELETE')
    return response

# Global variable to store loaded network
network_graph = None

# GMT+7 timezone (WIB - Waktu Indonesia Barat)
WIB_TZ = timezone(timedelta(hours=7))

def parse_departure_time(time_str: str) -> datetime:
    """
    Parse departure time string to datetime with GMT+7 timezone
    
    Args:
        time_str: ISO format datetime string (e.g., "2025-01-01T10:00" or "2025-01-01T10:00:00")
    
    Returns:
        datetime object with GMT+7 timezone
    """
    if not time_str:
        return datetime.now(WIB_TZ)
    
    try:
        # Handle different formats
        if 'T' in time_str:
            # Remove 'Z' if present and add GMT+7
            if time_str.endswith('Z'):
                time_str = time_str[:-1] + '+07:00'
            elif '+' not in time_str[-6:] and '-' not in time_str[-6:]:
                # No timezone, assume GMT+7
                if len(time_str) == 16:  # YYYY-MM-DDTHH:mm
                    time_str = time_str + ':00+07:00'
                elif len(time_str) == 19:  # YYYY-MM-DDTHH:mm:ss
                    time_str = time_str + '+07:00'
                else:
                    time_str = time_str + '+07:00'
            
            dt = datetime.fromisoformat(time_str)
            # Ensure timezone is GMT+7
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=WIB_TZ)
            else:
                # Convert to GMT+7
                dt = dt.astimezone(WIB_TZ)
            return dt
        else:
            raise ValueError("Invalid format: missing 'T' separator")
    except ValueError as e:
        raise ValueError(f"Invalid departure_time format: {str(e)}")

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
        
        # Parse departure time (GMT+7)
        departure_time = datetime.now(WIB_TZ)
        if 'departure_time' in data and data['departure_time']:
            try:
                departure_time = parse_departure_time(data['departure_time'])
            except ValueError as e:
                return jsonify({"error": str(e)}), 400

        # Di luar jam operasional angkutan umum: tidak ada rute yang bisa
        # dijalani, jadi berikan estimasi kendaraan pribadi + alasannya
        # (seperti Google Maps yang beralih ke moda menyetir).
        if not service_model.any_service_available(departure_time):
            estimate = service_model.driving_estimate(
                (origin['lat'], origin['lon']),
                (destination['lat'], destination['lon']),
                departure_time,
            )
            return jsonify({
                "success": True,
                "public_transport_available": False,
                "reason": (
                    f"Di luar jam operasional angkutan umum "
                    f"({departure_time.strftime('%H:%M')} WIB). "
                    f"Jam layanan: {service_model.service_window_text()}."
                ),
                "suggested_mode": "PRIVATE_VEHICLE",
                "private_vehicle": estimate,
                "origin": origin,
                "destination": destination,
                "departure_time": departure_time.isoformat(),
            }), 200

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
        
        # Run DFS using IDA* (Iterative Deepening A*)
        # IDA* is a DFS-based algorithm that explores paths using depth-first manner
        if algorithm in ['dfs', 'both']:
            try:
                # Use BALANCED IDA* which is truly a DFS-based algorithm
                dfs_route = gmaps_style_route_balanced_ida_star(
                    graph=graph,
                    origin_name=origin['name'],
                    origin_coords=(origin['lat'], origin['lon']),
                    dest_name=destination['name'],
                    dest_coords=(destination['lat'], destination['lon']),
                    optimization_mode="time",
                    departure_time=departure_time
                )
                
                if dfs_route:
                    results['dfs'] = {
                        "success": True,
                        "route": serialize_route(dfs_route, origin['name'], destination['name'], (origin['lat'], origin['lon']), (destination['lat'], destination['lon'])),
                        "algorithm_info": {
                            "algorithm": "BALANCED IDA* (Iterative Deepening A*) - DFS-Based Search",
                            "description": "Balanced IDA* uses reasonable bounds, efficient heuristics, and smart pruning for reliable DFS-based optimal routing",
                            "iterations": dfs_route.get('iterations', 0) if hasattr(dfs_route, 'get') else 0,
                            "max_depth": dfs_route.get('max_depth', 0) if hasattr(dfs_route, 'get') else 0
                        }
                    }
                else:
                    results['dfs'] = {
                        "success": False,
                        "error": "No route found using IDA* (DFS-based search)"
                    }
            except Exception as e:
                print(f"Error in DFS (IDA*): {e}")
                import traceback
                traceback.print_exc()
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
                "wait_minutes": getattr(seg, 'wait_minutes', 0.0),
                "travel_minutes": seg.duration_minutes - getattr(seg, 'wait_minutes', 0.0),
                "path": getattr(seg, 'path', None),
                "via_stops": getattr(seg, 'via_stops', []),
                "cost": seg.cost,
                "distance_km": seg.distance_km,
                "departure_time": seg.departure_time.isoformat(),
                "arrival_time": seg.arrival_time.isoformat(),
                # Koordinat langsung dari objek Stop milik segmen ini (bukan
                # dicari ulang lewat dict ber-kunci nama halte) -- beberapa
                # halte berbagi nama yang sama di koridor berbeda (mis. "BS
                # SPBU 24 ada" ada di Feeder Koridor 5 DAN 6, lokasi beda ~13km),
                # jadi lookup by-name dulu diam-diam bisa memberi koordinat
                # halte koridor lain yang salah.
                "from_coords": {
                    "lat": origin_coords[0] if seg.sequence == 1 and origin_coords else seg.from_stop.lat,
                    "lon": origin_coords[1] if seg.sequence == 1 and origin_coords else seg.from_stop.lon,
                },
                "to_coords": {
                    "lat": dest_coords[0] if seg.sequence == len(route.segments) and dest_coords else seg.to_stop.lat,
                    "lon": dest_coords[1] if seg.sequence == len(route.segments) and dest_coords else seg.to_stop.lon,
                }
            }
            for seg in route.segments
        ]
    }


@app.route('/api/route/alternatives', methods=['POST'])
def route_alternatives():
    """
    Beberapa opsi rute seperti Google Maps: tercepat, termurah, paling
    sedikit transfer. Memakai Dijkstra (mesin utama, hasil optimal terjamin)
    sebagai satu-satunya algoritma pencarian.

    Expected JSON payload sama seperti POST /api/route (tanpa field
    "algorithm" -- endpoint ini selalu memberi beberapa opsi sekaligus).
    """
    try:
        data = request.get_json()
        if not data or 'origin' not in data or 'destination' not in data:
            return jsonify({"error": "origin and destination are required"}), 400

        origin = data['origin']
        destination = data['destination']

        if not all(key in origin for key in ['lat', 'lon']):
            return jsonify({"error": "Origin must have lat and lon"}), 400
        if not all(key in destination for key in ['lat', 'lon']):
            return jsonify({"error": "Destination must have lat and lon"}), 400

        departure_time = datetime.now(WIB_TZ)
        if 'departure_time' in data and data['departure_time']:
            try:
                departure_time = parse_departure_time(data['departure_time'])
            except ValueError as e:
                return jsonify({"error": str(e)}), 400

        if not service_model.any_service_available(departure_time):
            estimate = service_model.driving_estimate(
                (origin['lat'], origin['lon']),
                (destination['lat'], destination['lon']),
                departure_time,
            )
            return jsonify({
                "success": True,
                "public_transport_available": False,
                "reason": (
                    f"Di luar jam operasional angkutan umum "
                    f"({departure_time.strftime('%H:%M')} WIB). "
                    f"Jam layanan: {service_model.service_window_text()}."
                ),
                "suggested_mode": "PRIVATE_VEHICLE",
                "private_vehicle": estimate,
                "origin": origin,
                "destination": destination,
                "departure_time": departure_time.isoformat(),
            }), 200

        graph = load_network()
        alternatives = find_route_alternatives(
            graph=graph,
            origin_name=origin.get('name', 'Origin'),
            origin_coords=(origin['lat'], origin['lon']),
            dest_name=destination.get('name', 'Destination'),
            dest_coords=(destination['lat'], destination['lon']),
            departure_time=departure_time,
        )

        if not alternatives:
            return jsonify({"success": False, "error": "No route found"}), 200

        return jsonify({
            "success": True,
            "origin": origin,
            "destination": destination,
            "departure_time": departure_time.isoformat(),
            "alternatives": [
                {
                    "label": alt["label"],
                    "optimized_for": alt["optimized_for"],
                    "route": serialize_route(
                        alt["route"], origin.get('name', 'Origin'),
                        destination.get('name', 'Destination'),
                        (origin['lat'], origin['lon']),
                        (destination['lat'], destination['lon']),
                    ),
                }
                for alt in alternatives
            ],
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/route/presentation', methods=['POST'])
def route_request_presentation():
    """
    Presentation routing endpoint with Dijkstra fallback
    If DFS-IDA* takes more than 1 minute, it automatically falls back to Dijkstra.
    
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
        "algorithm": "dfs" | "both",
        "departure_time": "2025-01-01T10:00:00" (optional),
        "timeout_seconds": 60.0 (optional, default 60 seconds)
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
        timeout_seconds = data.get('timeout_seconds', 60.0)
        
        # Validate coordinates
        if not all(key in origin for key in ['lat', 'lon']):
            return jsonify({"error": "Origin must have lat and lon"}), 400
        if not all(key in destination for key in ['lat', 'lon']):
            return jsonify({"error": "Destination must have lat and lon"}), 400
        
        # Parse departure time (GMT+7)
        departure_time = datetime.now(WIB_TZ)
        if 'departure_time' in data and data['departure_time']:
            try:
                departure_time = parse_departure_time(data['departure_time'])
            except ValueError as e:
                return jsonify({"error": str(e)}), 400

        # Di luar jam operasional angkutan umum: tidak ada rute yang bisa
        # dijalani, jadi berikan estimasi kendaraan pribadi + alasannya
        # (seperti Google Maps yang beralih ke moda menyetir).
        if not service_model.any_service_available(departure_time):
            estimate = service_model.driving_estimate(
                (origin['lat'], origin['lon']),
                (destination['lat'], destination['lon']),
                departure_time,
            )
            return jsonify({
                "success": True,
                "public_transport_available": False,
                "reason": (
                    f"Di luar jam operasional angkutan umum "
                    f"({departure_time.strftime('%H:%M')} WIB). "
                    f"Jam layanan: {service_model.service_window_text()}."
                ),
                "suggested_mode": "PRIVATE_VEHICLE",
                "private_vehicle": estimate,
                "origin": origin,
                "destination": destination,
                "departure_time": departure_time.isoformat(),
            }), 200

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
        
        # Run DFS using IDA* with Dijkstra fallback
        if algorithm in ['dfs', 'both']:
            try:
                dfs_route, metadata = gmaps_style_route_ida_star_with_fallback(
                    graph=graph,
                    origin_name=origin['name'],
                    origin_coords=(origin['lat'], origin['lon']),
                    dest_name=destination['name'],
                    dest_coords=(destination['lat'], destination['lon']),
                    optimization_mode="time",
                    departure_time=departure_time,
                    timeout_seconds=timeout_seconds
                )
                
                if dfs_route:
                    results['dfs'] = {
                        "success": True,
                        "route": serialize_route(dfs_route, origin['name'], destination['name'], (origin['lat'], origin['lon']), (destination['lat'], destination['lon'])),
                        "algorithm_info": {
                            "algorithm": metadata['algorithm_used'].upper(),
                            "description": f"DFS-IDA* with Dijkstra fallback (fallback used: {metadata['fallback_used']})",
                            "search_time_seconds": metadata['search_time_seconds'],
                            "timeout_reached": metadata['timeout_reached'],
                            "fallback_used": metadata['fallback_used']
                        }
                    }
                else:
                    results['dfs'] = {
                        "success": False,
                        "error": "No route found using IDA* or Dijkstra fallback"
                    }
            except Exception as e:
                print(f"Error in DFS (IDA* with fallback): {e}")
                import traceback
                traceback.print_exc()
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
                "departure_time": departure_time.isoformat(),
                "presentation_mode": True,
                "timeout_seconds": timeout_seconds
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@app.route('/api/route/waypoints/<route_name>', methods=['GET'])
def get_route_waypoints(route_name):
    """Get route waypoints from KMZ for accurate visualization"""
    try:
        import json
        json_path = "dataset/network_data_correct_bidirectional.json"
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        route_waypoints = data.get('route_waypoints', {})
        
        if route_name in route_waypoints:
            return jsonify({
                "success": True,
                "route": route_name,
                "waypoints": route_waypoints[route_name],
                "count": len(route_waypoints[route_name])
            })
        else:
            return jsonify({
                "success": False,
                "error": f"No waypoints found for route: {route_name}"
            }), 404
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

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
    print("   POST /api/route - Route planning (pure DFS, no fallback)")
    print("   POST /api/route/presentation - Route planning with fallback (for presentation)")
    print("   GET  /api/route/waypoints/<route_name> - Get route waypoints from KMZ")
    print("   GET  /api/stops - Get all stops")
    print("="*60)
    print("📝 Note: /api/route uses pure DFS-IDA*")
    print("📝 Note: /api/route/presentation uses DFS-IDA* with Dijkstra fallback (60s timeout)")
    print("="*60)
    
    app.run(debug=True, host='0.0.0.0', port=5001)
