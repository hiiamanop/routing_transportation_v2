#!/usr/bin/env python3
"""
Palembang Public Transport Routing API
Backend service for multi-modal route planning
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.routing import RoutePlanner
from core.models import RouteRequest, RouteResponse

app = Flask(__name__)

# Initialize route planner once at startup
route_planner = None

def initialize_planner():
    """Initialize the route planner with network data"""
    global route_planner
    try:
        route_planner = RoutePlanner()
        return True
    except Exception as e:
        print(f"❌ Failed to initialize route planner: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Palembang Public Transport Routing API",
        "version": "1.0.0",
        "network_loaded": route_planner is not None
    })

@app.route('/route', methods=['POST'])
def get_route():
    """
    Main routing endpoint
    
    Expected JSON input:
    {
        "origin": {
            "name": "PTC Mall",
            "latitude": -2.951012,
            "longitude": 104.761363
        },
        "destination": {
            "name": "SMA 10",
            "latitude": -2.99361,
            "longitude": 104.72556
        },
        "algorithm": "dijkstra",  // "dijkstra", "ida_star", or "both"
        "optimization": "time",   // "time", "cost", "transfers", "balanced"
        "departure_time": "2025-01-23T08:00:00",  // Optional, defaults to now
        "max_walking_km": 3.0     // Optional, defaults to 3.0
    }
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['origin', 'destination']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Validate origin and destination
        for location in ['origin', 'destination']:
            loc_data = data[location]
            if not all(key in loc_data for key in ['name', 'latitude', 'longitude']):
                return jsonify({"error": f"{location} must have name, latitude, and longitude"}), 400
        
        # Create route request
        route_request = RouteRequest(
            origin_name=data['origin']['name'],
            origin_coords=(data['origin']['latitude'], data['origin']['longitude']),
            dest_name=data['destination']['name'],
            dest_coords=(data['destination']['latitude'], data['destination']['longitude']),
            algorithm=data.get('algorithm', 'dijkstra'),
            optimization=data.get('optimization', 'time'),
            departure_time=data.get('departure_time'),
            max_walking_km=data.get('max_walking_km', 3.0)
        )
        
        # Get route
        result = route_planner.get_route(route_request)
        
        if result:
            return jsonify(result.to_dict())
        else:
            return jsonify({"error": "No route found"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/network/info', methods=['GET'])
def network_info():
    """Get network information"""
    if not route_planner:
        return jsonify({"error": "Route planner not initialized"}), 500
    
    info = route_planner.get_network_info()
    return jsonify(info)

@app.route('/algorithms', methods=['GET'])
def available_algorithms():
    """Get available algorithms"""
    return jsonify({
        "algorithms": [
            {
                "id": "dijkstra",
                "name": "Dijkstra",
                "description": "Fast and reliable shortest path algorithm",
                "recommended": True
            },
            {
                "id": "ida_star",
                "name": "IDA*",
                "description": "Memory-efficient iterative deepening A* algorithm",
                "recommended": False
            },
            {
                "id": "both",
                "name": "Both",
                "description": "Compare Dijkstra and IDA* results",
                "recommended": False
            }
        ],
        "optimization_modes": [
            {"id": "time", "name": "Time", "description": "Minimize travel time"},
            {"id": "cost", "name": "Cost", "description": "Minimize cost"},
            {"id": "transfers", "name": "Transfers", "description": "Minimize transfers"},
            {"id": "balanced", "name": "Balanced", "description": "Balance time, cost, and transfers"}
        ]
    })

if __name__ == '__main__':
    print("="*80)
    print("🚀 STARTING PALEMBANG PUBLIC TRANSPORT ROUTING API")
    print("="*80)
    
    # Initialize route planner
    if initialize_planner():
        print("✅ Route planner initialized successfully")
        print(f"📊 Network: {route_planner.get_network_info()}")
        print("\n🌐 API Endpoints:")
        print("   GET  /health           - Health check")
        print("   POST /route            - Get route")
        print("   GET  /network/info     - Network information")
        print("   GET  /algorithms       - Available algorithms")
        print("\n🚀 Starting server on http://localhost:5000")
        print("="*80)
        
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("❌ Failed to initialize route planner. Exiting.")
        sys.exit(1)
