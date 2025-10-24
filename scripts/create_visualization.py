#!/usr/bin/env python3
"""
Create comprehensive interactive HTML visualization for public transport network
"""

import json
from pathlib import Path

BASE_DIR = Path("/Users/ahmadnaufalmuzakki/Documents/KERJAAN/Meetsin.Id/2025/DFS/DFS_final")
DATASET_DIR = BASE_DIR / "dataset"

# Load network data
with open(DATASET_DIR / "network_data_complete.json", 'r', encoding='utf-8') as f:
    network_data = json.load(f)

# Define route colors
ROUTE_COLORS = {
    "Feeder Koridor 1": "#FF6B6B",
    "Feeder Koridor 2": "#4ECDC4",
    "Feeder Koridor 3": "#45B7D1",
    "Feeder Koridor 4": "#96CEB4",
    "Feeder Koridor 5": "#FFEAA7",
    "Feeder Koridor 6": "#DFE6E9",
    "Feeder Koridor 7": "#74B9FF",
    "Feeder Koridor 8": "#A29BFE",
    "Teman Bus Koridor 2": "#FD79A8",
    "Teman Bus Koridor 5": "#FDCB6E",
    "LRT Sumsel": "#00B894"
}

def create_html_visualization():
    """Create comprehensive HTML visualization"""
    
    # Group nodes by route
    routes_data = {}
    for node in network_data['nodes']:
        route = node['route']
        if route not in routes_data:
            routes_data[route] = []
        routes_data[route].append(node)
    
    # Group edges by route
    edges_by_route = {}
    for edge in network_data['edges']:
        route = edge['route']
        if route not in edges_by_route:
            edges_by_route[route] = []
        edges_by_route[route].append(edge)
    
    # Calculate center point (average of all stops)
    avg_lat = sum(node['lat'] for node in network_data['nodes']) / len(network_data['nodes'])
    avg_lon = sum(node['lon'] for node in network_data['nodes']) / len(network_data['nodes'])
    
    html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Palembang Public Transport Network - Feeder, Teman Bus & LRT</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 5px;
        }}
        
        .header p {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .container {{
            display: flex;
            height: calc(100vh - 100px);
        }}
        
        .sidebar {{
            width: 300px;
            background: white;
            padding: 20px;
            overflow-y: auto;
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
        }}
        
        .sidebar h2 {{
            font-size: 18px;
            margin-bottom: 15px;
            color: #333;
        }}
        
        .route-item {{
            padding: 12px;
            margin-bottom: 8px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid transparent;
        }}
        
        .route-item:hover {{
            transform: translateX(5px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .route-item.active {{
            border-color: #667eea;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
        }}
        
        .route-name {{
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 4px;
        }}
        
        .route-info {{
            font-size: 12px;
            opacity: 0.7;
        }}
        
        .route-color {{
            width: 30px;
            height: 30px;
            border-radius: 50%;
            float: right;
            margin-top: -5px;
        }}
        
        .map-container {{
            flex: 1;
            position: relative;
        }}
        
        #map {{
            width: 100%;
            height: 100%;
        }}
        
        .stats {{
            background: white;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        
        .stats-item {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            padding: 5px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        .stats-label {{
            font-size: 13px;
            color: #666;
        }}
        
        .stats-value {{
            font-weight: 600;
            color: #667eea;
        }}
        
        .legend {{
            position: absolute;
            bottom: 30px;
            right: 10px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
            max-height: 300px;
            overflow-y: auto;
        }}
        
        .legend h3 {{
            font-size: 14px;
            margin-bottom: 10px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 8px;
            font-size: 12px;
        }}
        
        .legend-color {{
            width: 20px;
            height: 3px;
            margin-right: 8px;
        }}
        
        .controls {{
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
        }}
        
        .control-btn {{
            background: white;
            border: none;
            padding: 10px 15px;
            margin-bottom: 5px;
            border-radius: 5px;
            cursor: pointer;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            font-size: 12px;
            display: block;
            width: 120px;
        }}
        
        .control-btn:hover {{
            background: #f0f0f0;
        }}
        
        .leaflet-popup-content {{
            font-size: 13px;
        }}
        
        .leaflet-popup-content h3 {{
            margin: 0 0 8px 0;
            color: #667eea;
            font-size: 14px;
        }}
        
        .leaflet-popup-content p {{
            margin: 4px 0;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚌 Jaringan Transportasi Umum Palembang</h1>
        <p>Angkot Feeder • Teman Bus • LRT Sumsel</p>
    </div>
    
    <div class="container">
        <div class="sidebar">
            <div class="stats">
                <h2>📊 Statistik Jaringan</h2>
                <div class="stats-item">
                    <span class="stats-label">Total Halte</span>
                    <span class="stats-value">{len(network_data['nodes'])}</span>
                </div>
                <div class="stats-item">
                    <span class="stats-label">Total Rute</span>
                    <span class="stats-value">{len(network_data['routes'])}</span>
                </div>
                <div class="stats-item">
                    <span class="stats-label">Total Koneksi</span>
                    <span class="stats-value">{len(network_data['edges'])}</span>
                </div>
            </div>
            
            <h2>🚏 Daftar Koridor</h2>
            <div id="routeList">
"""
    
    # Add route items
    for route in sorted(network_data['routes']):
        color = ROUTE_COLORS.get(route, '#999')
        stops_count = len(routes_data[route])
        
        html_content += f"""
                <div class="route-item" data-route="{route}" style="background-color: {color}22;">
                    <div class="route-color" style="background-color: {color};"></div>
                    <div class="route-name">{route}</div>
                    <div class="route-info">{stops_count} halte</div>
                </div>
"""
    
    html_content += """
            </div>
        </div>
        
        <div class="map-container">
            <div id="map"></div>
            
            <div class="controls">
                <button class="control-btn" onclick="showAllRoutes()">📍 Semua Rute</button>
                <button class="control-btn" onclick="resetView()">🔄 Reset View</button>
            </div>
            
            <div class="legend">
                <h3>🎨 Legenda Rute</h3>
"""
    
    # Add legend items
    for route in sorted(network_data['routes']):
        color = ROUTE_COLORS.get(route, '#999')
        html_content += f"""
                <div class="legend-item">
                    <div class="legend-color" style="background-color: {color};"></div>
                    <span>{route}</span>
                </div>
"""
    
    html_content += f"""
            </div>
        </div>
    </div>
    
    <script>
        // Initialize map
        const map = L.map('map').setView([{avg_lat}, {avg_lon}], 12);
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors',
            maxZoom: 18
        }}).addTo(map);
        
        // Store all layers
        const routeLayers = {{}};
        const routeData = {json.dumps(routes_data)};
        const edgesData = {json.dumps(edges_by_route)};
        const allNodes = {json.dumps(network_data['nodes'])};
        const routeColors = {json.dumps(ROUTE_COLORS)};
        
        // Create layers for each route
        Object.keys(routeData).forEach(route => {{
            const color = routeColors[route] || '#999';
            const layerGroup = L.layerGroup();
            
            // Add stops
            routeData[route].forEach(stop => {{
                const marker = L.circleMarker([stop.lat, stop.lon], {{
                    radius: 6,
                    fillColor: color,
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                }});
                
                marker.bindPopup(`
                    <h3>${{stop.name}}</h3>
                    <p><strong>Koridor:</strong> ${{stop.route}}</p>
                    <p><strong>Koordinat:</strong> ${{stop.lat.toFixed(6)}}, ${{stop.lon.toFixed(6)}}</p>
                `);
                
                marker.addTo(layerGroup);
            }});
            
            // Add route lines
            if (edgesData[route]) {{
                edgesData[route].forEach(edge => {{
                    const fromNode = allNodes.find(n => n.id === edge.from);
                    const toNode = allNodes.find(n => n.id === edge.to);
                    
                    if (fromNode && toNode) {{
                        const line = L.polyline([
                            [fromNode.lat, fromNode.lon],
                            [toNode.lat, toNode.lon]
                        ], {{
                            color: color,
                            weight: 3,
                            opacity: 0.7
                        }});
                        
                        line.addTo(layerGroup);
                    }}
                }});
            }}
            
            layerGroup.addTo(map);
            routeLayers[route] = layerGroup;
        }});
        
        // Route item click handler
        document.querySelectorAll('.route-item').forEach(item => {{
            item.addEventListener('click', function() {{
                const route = this.getAttribute('data-route');
                
                // Remove active class from all
                document.querySelectorAll('.route-item').forEach(i => i.classList.remove('active'));
                
                // Add active class
                this.classList.add('active');
                
                // Hide all routes
                Object.values(routeLayers).forEach(layer => map.removeLayer(layer));
                
                // Show selected route
                if (routeLayers[route]) {{
                    routeLayers[route].addTo(map);
                    
                    // Fit bounds to route
                    const routeStops = routeData[route];
                    if (routeStops.length > 0) {{
                        const bounds = L.latLngBounds(
                            routeStops.map(s => [s.lat, s.lon])
                        );
                        map.fitBounds(bounds, {{ padding: [50, 50] }});
                    }}
                }}
            }});
        }});
        
        // Show all routes
        function showAllRoutes() {{
            document.querySelectorAll('.route-item').forEach(i => i.classList.remove('active'));
            Object.values(routeLayers).forEach(layer => layer.addTo(map));
            map.setView([{avg_lat}, {avg_lon}], 12);
        }}
        
        // Reset view
        function resetView() {{
            showAllRoutes();
        }}
    </script>
</body>
</html>
"""
    
    return html_content

# Generate and save HTML
print("Generating comprehensive HTML visualization...")
html_content = create_html_visualization()

output_file = DATASET_DIR / "public_transport_network_complete.html"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ Visualization created: {output_file}")
print(f"\nOpen the file in your browser to view the interactive map!")

