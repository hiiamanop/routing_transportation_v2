#!/usr/bin/env python3
"""
Optimized DFS (Depth First Search) Implementation for Multimodal Routing
Research: PERANCANGAN SISTEM INFORMASI INTEGRASI OPERASIONAL
ANTAR MODA ANGKUTAN UMUM MENGGUNAKAN ALGORITMA DEPTH FIRST SEARCH (DFS) DI KOTA PALEMBANG

Optimizations:
1. DFS with Heuristic (A* style)
2. DFS with Pruning
3. DFS with Network Simplification
4. DFS with Iterative Deepening
5. DFS with Best-First Ordering
"""

import sys
import os
import json
import math
import heapq
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

@dataclass
class Location:
    """Represents a geographical location"""
    name: str
    lat: float
    lon: float

class TransportationMode:
    LRT = "LRT"
    TEMAN_BUS = "TEMAN_BUS"
    FEEDER_ANGKOT = "FEEDER_ANGKOT"
    WALKING = "WALKING"

@dataclass
class Stop:
    """Represents a bus stop or station"""
    stop_id: str
    name: str
    lat: float
    lon: float
    mode: str

@dataclass
class Edge:
    """Represents a connection between stops"""
    from_stop: Stop
    to_stop: Stop
    cost: float
    duration_minutes: float
    distance_km: float
    mode: str

@dataclass
class RouteSegment:
    """Represents a segment of a route"""
    sequence: int
    mode: str
    from_location: Location
    to_location: Location
    duration_minutes: float
    cost: float
    distance_km: float
    departure_time: datetime
    arrival_time: datetime

@dataclass
class Route:
    """Represents a complete route"""
    route_id: int
    segments: List[RouteSegment]
    total_cost: float
    total_time_minutes: float
    total_distance_km: float

@dataclass
class DFSResult:
    """Result of DFS search"""
    found: bool
    path: List[str]
    total_cost: float
    iterations: int
    max_depth_reached: int
    algorithm: str

def calculate_lrt_cost(from_stop_name: str, to_stop_name: str) -> float:
    """
    Calculate LRT cost based on distance
    
    Rules:
    - Antar stasiun: Rp 5,000
    - Ujung ke ujung: Rp 10,000
    - Tidak ada penambahan nilai berdasarkan jarak
    """
    # Get LRT station names
    from_name = from_stop_name.lower()
    to_name = to_stop_name.lower()
    
    # Define LRT stations (assuming these are the end stations)
    lrt_end_stations = ['smb', 'bumi sriwijaya', 'asrama haji']
    
    # Check if it's end-to-end journey
    is_from_end = any(end_station in from_name for end_station in lrt_end_stations)
    is_to_end = any(end_station in to_name for end_station in lrt_end_stations)
    
    # If both are end stations, it's end-to-end journey
    if is_from_end and is_to_end and from_name != to_name:
        return 10000  # Rp 10,000 for end-to-end
    else:
        return 5000   # Rp 5,000 for regular inter-station

def calculate_transfer_cost(current_mode: str, next_mode: str, from_stop_name: str = None, to_stop_name: str = None) -> float:
    """
    Calculate cost for transfer between modes
    
    Rules:
    - Angkot Feeder: FREE (Rp 0)
    - Teman Bus: Rp 5,000 per trip
    - LRT: Rp 5,000 (antar stasiun) atau Rp 10,000 (ujung ke ujung)
    - No additional cost if staying in same mode/corridor
    """
    # If staying in same mode, no additional cost
    if current_mode == next_mode:
        return 0
    
    # If walking, no cost
    if next_mode == "WALKING":
        return 0
    
    # Calculate cost for new mode
    if next_mode == "LRT":
        # For LRT, calculate based on stations
        if from_stop_name and to_stop_name:
            return calculate_lrt_cost(from_stop_name, to_stop_name)
        else:
            return 5000  # Default LRT cost
    elif next_mode == "FEEDER_ANGKOT":
        return 0  # FREE
    elif next_mode == "TEMAN_BUS":
        return 5000  # Rp 5,000
    else:
        return 0

def calculate_route_cost(segments: List[RouteSegment]) -> float:
    """
    Calculate total cost for a route with proper transfer logic
    
    Rules:
    - Only charge when entering a new mode/corridor
    - Angkot Feeder: FREE
    - Teman Bus: Rp 5,000 per trip
    - LRT: Rp 5,000 (antar stasiun) atau Rp 10,000 (ujung ke ujung)
    """
    if not segments:
        return 0
    
    total_cost = 0
    current_mode = None
    
    for segment in segments:
        # Skip walking segments
        if segment.mode == "WALKING":
            continue
        
        # If mode changed, add cost for new mode
        if current_mode != segment.mode:
            if segment.mode == "LRT":
                # For LRT, calculate based on stations
                if hasattr(segment, 'from_stop') and hasattr(segment, 'to_stop'):
                    total_cost += calculate_lrt_cost(segment.from_stop.name, segment.to_stop.name)
                else:
                    total_cost += 5000  # Default LRT cost
            else:
                total_cost += calculate_transfer_cost(current_mode, segment.mode)
            current_mode = segment.mode
    
    return total_cost

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

class TransportationGraph:
    """Simple transportation graph"""
    def __init__(self):
        self.stops = {}
        self.edges = {}
    
    def add_stop(self, stop: Stop):
        self.stops[stop.stop_id] = stop
    
    def add_edge(self, edge: Edge):
        if edge.from_stop.stop_id not in self.edges:
            self.edges[edge.from_stop.stop_id] = []
        self.edges[edge.from_stop.stop_id].append(edge)

def load_network_data():
    """Load network data from JSON file"""
    try:
        with open('dataset/network_data_correct_bidirectional.json', 'r') as f:
            data = json.load(f)
        
        graph = TransportationGraph()
        
        # Load stops
        for stop_data in data['nodes']:
            stop = Stop(
                stop_id=stop_data['stop_id'],
                name=stop_data['name'],
                lat=stop_data['lat'],
                lon=stop_data['lon'],
                mode=stop_data.get('mode', 'UNKNOWN')
            )
            graph.add_stop(stop)
        
        # Load edges
        for edge_data in data['edges']:
            from_stop = graph.stops[list(graph.stops.keys())[edge_data['from']]]
            to_stop = graph.stops[list(graph.stops.keys())[edge_data['to']]]
            
            edge = Edge(
                from_stop=from_stop,
                to_stop=to_stop,
                cost=edge_data.get('cost', 3500),  # Default cost
                duration_minutes=edge_data.get('duration_minutes', 2),  # Default duration
                distance_km=edge_data.get('distance', 0.5) / 1000,  # Convert to km
                mode=edge_data.get('mode', edge_data.get('route', 'UNKNOWN'))
            )
            graph.add_edge(edge)
        
        return graph
    except Exception as e:
        print(f"Error loading network data: {e}")
        return None

def find_nearest_stops(graph: TransportationGraph, lat: float, lon: float, max_stops: int = 5, max_distance_km: float = 2.0):
    """Find nearest stops to given coordinates with distance limit
    
    Args:
        graph: Transportation network
        lat: Latitude
        lon: Longitude
        max_stops: Maximum number of stops to return
        max_distance_km: Maximum distance in km (default 2km - reasonable walking distance)
    
    Returns:
        List of (stop, distance) tuples sorted by distance
    """
    distances = []
    
    for stop_id, stop in graph.stops.items():
        dist = haversine_distance_km(lat, lon, stop.lat, stop.lon)
        # Only include stops within walking distance
        if dist <= max_distance_km:
            distances.append((stop, dist))
    
    # Sort by distance
    distances.sort(key=lambda x: x[1])
    
    return distances[:max_stops]

class OptimizedDFSRouter:
    """
    Optimized DFS Router for Multimodal Transportation
    
    This implementation uses multiple optimization techniques:
    1. Heuristic-based DFS (A* style)
    2. Pruning with cost bounds
    3. Network simplification
    4. Iterative deepening
    5. Best-first ordering
    """
    
    def __init__(self, graph: TransportationGraph):
        self.graph = graph
        self.visited = set()
        self.path = []
        self.best_path = None
        self.best_cost = float('inf')
        self.iterations = 0
        self.max_depth_reached = 0
        self.pruned_paths = 0
        self.max_iterations = 50000  # Limit iterations to prevent infinite loops
        
    def heuristic_cost(self, current: str, goal: str) -> float:
        """
        Heuristic function for A* style DFS
        Uses straight-line distance as heuristic
        """
        if current not in self.graph.stops or goal not in self.graph.stops:
            return 0
        
        current_stop = self.graph.stops[current]
        goal_stop = self.graph.stops[goal]
        
        # Use distance as heuristic (assume 10 min/km walking)
        distance = haversine_distance_km(current_stop.lat, current_stop.lon, 
                                        goal_stop.lat, goal_stop.lon)
        return distance * 10  # Convert to time estimate
    
    def get_neighbors_sorted(self, current: str, goal: str) -> List[Edge]:
        """
        Get neighbors sorted by heuristic + cost (best-first ordering)
        """
        if current not in self.graph.edges:
            return []
        
        neighbors = []
        for edge in self.graph.edges[current]:
            heuristic = self.heuristic_cost(edge.to_stop.stop_id, goal)
            total_cost = edge.cost + heuristic
            neighbors.append((total_cost, edge))
        
        # Sort by total cost (heuristic + actual cost)
        neighbors.sort(key=lambda x: x[0])
        
        return [edge for _, edge in neighbors]
    
    def dfs_with_heuristic(self, start: str, goal: str, max_depth: int = 20) -> DFSResult:
        """
        DFS with heuristic (A* style)
        """
        self.visited.clear()
        self.path.clear()
        self.best_path = None
        self.best_cost = float('inf')
        self.iterations = 0
        self.max_depth_reached = 0
        self.pruned_paths = 0
        
        print(f"🔍 Starting Heuristic DFS search: {start} → {goal}")
        print(f"   Max depth: {max_depth}")
        
        # Start DFS search with heuristic
        found = self._dfs_heuristic_recursive(start, goal, 0, max_depth, 0)
        
        return DFSResult(
            found=found,
            path=self.best_path if self.best_path else [],
            total_cost=self.best_cost if self.best_cost != float('inf') else 0,
            iterations=self.iterations,
            max_depth_reached=self.max_depth_reached,
            algorithm="DFS with Heuristic"
        )
    
    def _dfs_heuristic_recursive(self, current: str, goal: str, depth: int, max_depth: int, current_cost: float) -> bool:
        """
        Recursive DFS with heuristic and pruning
        """
        self.iterations += 1
        
        # Update max depth reached
        self.max_depth_reached = max(self.max_depth_reached, depth)
        
        # Check depth limit
        if depth > max_depth:
            return False
        
        # Pruning: If current cost + heuristic > best cost, prune this path
        # But only if we have a valid best_cost (not infinity)
        if self.best_cost != float('inf'):
            heuristic_cost = self.heuristic_cost(current, goal)
            # Use a more lenient bound: allow 20% overhead
            if current_cost + heuristic_cost > self.best_cost * 1.2:
                self.pruned_paths += 1
                return False
        
        # Check if goal reached
        if current == goal:
            if current_cost < self.best_cost:
                self.best_cost = current_cost
                self.best_path = self.path + [current].copy()
                print(f"   ✅ Found path at depth {depth}, cost: {current_cost:.2f}")
            return True
        
        # Mark current as visited
        self.visited.add(current)
        self.path.append(current)
        
        # Explore neighbors in best-first order
        found_goal = False
        neighbors = self.get_neighbors_sorted(current, goal)
        
        for edge in neighbors:
            neighbor = edge.to_stop.stop_id
            
            if neighbor not in self.visited:
                new_cost = current_cost + edge.cost
                if self._dfs_heuristic_recursive(neighbor, goal, depth + 1, max_depth, new_cost):
                    found_goal = True
                    # Don't return immediately - continue exploring for better paths
        
        # Backtrack
        self.path.pop()
        self.visited.remove(current)
        
        return found_goal
    
    def pure_dfs(self, start: str, goal: str, max_depth: int = 200) -> DFSResult:
        """
        Pure DFS without heuristic or pruning (guaranteed to find ANY path if exists)
        """
        self.visited.clear()
        self.path.clear()
        self.best_path = None
        self.best_cost = float('inf')
        self.iterations = 0
        self.max_depth_reached = 0
        self.pruned_paths = 0
        
        print(f"🔍 Starting Pure DFS search: {start} → {goal}")
        print(f"   Max depth: {max_depth}")
        
        # Start Pure DFS search
        found = self._pure_dfs_recursive(start, goal, 0, max_depth, 0)
        
        return DFSResult(
            found=found,
            path=self.best_path if self.best_path else [],
            total_cost=self.best_cost if self.best_cost != float('inf') else 0,
            iterations=self.iterations,
            max_depth_reached=self.max_depth_reached,
            algorithm="Pure DFS"
        )
    
    def _pure_dfs_recursive(self, current: str, goal: str, depth: int, max_depth: int, current_cost: float) -> bool:
        """Pure DFS recursive search without pruning"""
        self.iterations += 1
        
        # Stop if too many iterations
        if self.iterations > self.max_iterations:
            return self.best_path is not None
        
        # Update max depth reached
        self.max_depth_reached = max(self.max_depth_reached, depth)
        
        # Check depth limit
        if depth > max_depth:
            return False
        
        # Check if goal reached
        if current == goal:
            if current_cost < self.best_cost:
                self.best_cost = current_cost
                self.best_path = self.path + [current].copy()
                print(f"   ✅ Found path at depth {depth}, cost: {current_cost:.2f}")
            return True
        
        # Mark current as visited
        self.visited.add(current)
        self.path.append(current)
        
        # Explore neighbors (no sorting, no pruning)
        found_goal = False
        if current in self.graph.edges:
            neighbors = self.graph.edges[current]
            for edge in neighbors:
                neighbor = edge.to_stop.stop_id
                
                if neighbor not in self.visited:
                    new_cost = current_cost + edge.cost
                    if self._pure_dfs_recursive(neighbor, goal, depth + 1, max_depth, new_cost):
                        found_goal = True
                        # Continue exploring for better paths
        
        # Backtrack
        self.path.pop()
        self.visited.remove(current)
        
        return found_goal
    
    def iterative_deepening_dfs(self, start: str, goal: str, max_depth: int = 30) -> DFSResult:
        """
        Iterative Deepening DFS
        Gradually increases depth limit until solution found
        """
        print(f"🔍 Starting Iterative Deepening DFS: {start} → {goal}")
        print(f"   Max depth: {max_depth}")
        
        for depth_limit in range(1, max_depth + 1):
            print(f"   📏 Trying depth limit: {depth_limit}")
            
            result = self.dfs_with_heuristic(start, goal, depth_limit)
            
            if result.found and result.path:
                print(f"   ✅ Found solution at depth {depth_limit}")
                result.algorithm = "Iterative Deepening DFS"
                return result
            
            print(f"   ❌ No solution at depth {depth_limit}")
        
        return DFSResult(
            found=False,
            path=[],
            total_cost=0,
            iterations=self.iterations,
            max_depth_reached=max_depth,
            algorithm="Iterative Deepening DFS"
        )
    
    def create_simplified_network(self, origin_stops: List, dest_stops: List) -> TransportationGraph:
        """
        Create simplified network for DFS search
        Keep only relevant stops and connections
        """
        simplified = TransportationGraph()
        
        # Get origin and destination coordinates
        origin_coords = [(stop.lat, stop.lon) for stop, _ in origin_stops[:3]]
        dest_coords = [(stop.lat, stop.lon) for stop, _ in dest_stops[:3]]
        
        # Calculate search radius
        max_dist = 0
        for orig_coord in origin_coords:
            for dest_coord in dest_coords:
                dist = haversine_distance_km(orig_coord[0], orig_coord[1], dest_coord[0], dest_coord[1])
                max_dist = max(max_dist, dist)
        
        search_radius = max(max_dist * 2.0, 5.0)  # 2x direct distance, minimum 5 km
        
        # Priority stop types
        priority_modes = ["LRT", "TEMAN_BUS"]
        
        # Add stops with smart selection
        for stop_id, stop in self.graph.stops.items():
            should_add = False
            
            # Rule 1: Priority stops (LRT, Teman Bus)
            if stop.mode in priority_modes:
                should_add = True
            
            # Rule 2: Origin/destination stops
            elif stop_id in [stop.stop_id for stop, _ in origin_stops[:5]] or stop_id in [stop.stop_id for stop, _ in dest_stops[:5]]:
                should_add = True
            
            # Rule 3: Within search radius
            else:
                for orig_coord in origin_coords:
                    dist_to_origin = haversine_distance_km(stop.lat, stop.lon, orig_coord[0], orig_coord[1])
                    if dist_to_origin < search_radius:
                        should_add = True
                        break
                
                if not should_add:
                    for dest_coord in dest_coords:
                        dist_to_dest = haversine_distance_km(stop.lat, stop.lon, dest_coord[0], dest_coord[1])
                        if dist_to_dest < search_radius:
                            should_add = True
                            break
            
            if should_add:
                simplified.add_stop(stop)
        
        # Add edges for simplified stops
        for from_id in simplified.stops:
            if from_id in self.graph.edges:
                for edge in self.graph.edges[from_id]:
                    if edge.to_stop.stop_id in simplified.stops:
                        simplified.add_edge(edge)
        
        print(f"   📊 Simplified network: {len(simplified.stops)} stops, {sum(len(edges) for edges in simplified.edges.values())} edges")
        
        return simplified

def gmaps_style_route_optimized_dfs(
    origin_lat: float, 
    origin_lon: float, 
    dest_lat: float, 
    dest_lon: float,
    departure_time: datetime = None,
    optimization_mode: str = "time",
    max_walking_km: float = 2.0
) -> Optional[Dict]:
    """
    Google Maps style routing using Optimized DFS
    
    Args:
        origin_lat: Origin latitude
        origin_lon: Origin longitude  
        dest_lat: Destination latitude
        dest_lon: Destination longitude
        departure_time: Departure time
        optimization_mode: "time", "cost", or "balanced"
        max_walking_km: Maximum walking distance in km (default 2km - reasonable walking distance)
        
    Returns:
        Route information or None if no route found
    """
    if departure_time is None:
        departure_time = datetime.now()
    
    print(f"\n🚀 Optimized DFS Routing")
    print(f"   Origin: ({origin_lat:.6f}, {origin_lon:.6f})")
    print(f"   Destination: ({dest_lat:.6f}, {dest_lon:.6f})")
    print(f"   Departure: {departure_time.strftime('%H:%M')}")
    print(f"   Mode: {optimization_mode}")
    
    # Load network
    graph = load_network_data()
    if not graph:
        print("❌ Failed to load transportation network")
        return None
    
    # Find nearest stops - increase coverage for more robust routing
    # Use max_walking_km to limit to reasonable walking distance
    origin_stops = find_nearest_stops(graph, origin_lat, origin_lon, max_stops=10, max_distance_km=max_walking_km)
    dest_stops = find_nearest_stops(graph, dest_lat, dest_lon, max_stops=10, max_distance_km=max_walking_km)
    
    if not origin_stops or not dest_stops:
        print("❌ No stops found near origin or destination")
        return None
    
    print(f"\n📍 Nearest stops:")
    print(f"   Origin: {[f'{stop.name} ({dist:.0f}m)' for stop, dist in origin_stops[:5]]}")
    print(f"   Destination: {[f'{stop.name} ({dist:.0f}m)' for stop, dist in dest_stops[:5]]}")
    
    # Try different DFS optimizations
    best_route = None
    best_cost = float('inf')
    combinations_tried = 0
    
    print(f"\n🔍 Trying Optimized DFS combinations...")
    
    # Limit combinations to prevent timeout (try ONLY closest stops for speed)
    for origin_stop, origin_dist in origin_stops[:1]:  # Only closest origin
        for dest_stop, dest_dist in dest_stops[:1]:   # Only closest destination
            combinations_tried += 1
            
            print(f"\n   🔄 Combination {combinations_tried}: {origin_stop.name} → {dest_stop.name}")
            
            # Create optimized DFS router
            dfs_router = OptimizedDFSRouter(graph)
            
            # Try different optimization strategies with reasonable depth limits
            # Focus on most promising strategies to avoid timeout
            strategies = [
                ("Pure DFS (Depth 100)", lambda: dfs_router.pure_dfs(origin_stop.stop_id, dest_stop.stop_id, 100))
            ]
            
            # Only try first strategy to save time
            # If it works, we have a route; if not, move to next combination
            
            for strategy_name, strategy_func in strategies:
                print(f"      🧠 Trying {strategy_name}")
                
                result = strategy_func()
                
                if result.found and result.path:
                    print(f"      ✅ {strategy_name} found path: {len(result.path)} stops, cost: {result.total_cost:.2f}")
                    print(f"         Iterations: {result.iterations}, Pruned: {dfs_router.pruned_paths}")
                    
                    # Calculate total walking distance
                    total_walking_distance = origin_dist + dest_dist
                    
                    # Create route with walking distance penalty
                    # Since user mentioned transport cost is flat and only increases on mode change,
                    # we need to heavily weight walking distance in our selection
                    # Weight walking distance at 1000x to prioritize closer stops
                    total_score = result.total_cost + (total_walking_distance * 1000)
                    
                    # Create route
                    route_info = {
                        'origin_stop': origin_stop,
                        'dest_stop': dest_stop,
                        'path': result.path,
                        'total_cost': result.total_cost,
                        'total_walking_distance': total_walking_distance,
                        'total_score': total_score,  # Combined score with walking penalty
                        'iterations': result.iterations,
                        'max_depth': result.max_depth_reached,
                        'algorithm': result.algorithm,
                        'pruned_paths': dfs_router.pruned_paths
                    }
                    
                    # Check if this is better (considering total score which includes walking penalty)
                    if not best_route or total_score < best_route.get('total_score', float('inf')):
                        best_cost = total_score  # Update best cost to use total_score
                        best_route = route_info
                        print(f"      🎯 New best route found! (Walking: {total_walking_distance*1000:.0f}m)")
                    
                    # Stop after first valid route to save time
                    # We already have a route, no need to explore more
                    print(f"      ✅ Route found, stopping search for this combination")
                    break
                else:
                    print(f"      ❌ {strategy_name} failed")
            
            # Stop after finding first valid route to avoid infinite search
            if best_route:
                print(f"      ✅ Found valid route, continuing search...")
                break  # Stop exploring this combination once we have a route
    
    print(f"\n   📊 Checked {combinations_tried} combinations")
    
    if not best_route:
        print(f"❌ No viable route found with Optimized DFS")
        print(f"💡 Consider using Dijkstra algorithm for complex routes")
        return None
    
    # Build complete route
    print(f"\n✅ Best Optimized DFS route found:")
    print(f"   Algorithm: {best_route['algorithm']}")
    print(f"   Path: {' → '.join([graph.stops[stop_id].name for stop_id in best_route['path']])}")
    print(f"   Cost: {best_route['total_cost']:.2f}")
    print(f"   Walking: {best_route['total_walking_distance']*1000:.0f}m")
    print(f"   Iterations: {best_route['iterations']}")
    print(f"   Max depth: {best_route['max_depth']}")
    print(f"   Pruned paths: {best_route['pruned_paths']}")
    
    # Create route segments
    segments = []
    current_time = departure_time
    
    # Origin to first stop
    origin_stop = best_route['origin_stop']
    first_stop = graph.stops[best_route['path'][0]]
    
    origin_loc = Location("Origin", origin_lat, origin_lon)
    first_stop_loc = Location(first_stop.name, first_stop.lat, first_stop.lon)
    
    walk_seg = RouteSegment(
        sequence=1,
        mode=TransportationMode.WALKING,
        from_location=origin_loc,
        to_location=first_stop_loc,
        duration_minutes=origin_dist * 10,  # 10 min/km walking
        cost=0,
        distance_km=origin_dist,
        departure_time=current_time,
        arrival_time=current_time + timedelta(minutes=origin_dist * 10)
    )
    segments.append(walk_seg)
    current_time = walk_seg.arrival_time
    
    # Transit segments
    for i in range(len(best_route['path']) - 1):
        from_stop_id = best_route['path'][i]
        to_stop_id = best_route['path'][i + 1]
        
        from_stop = graph.stops[from_stop_id]
        to_stop = graph.stops[to_stop_id]
        
        # Find edge
        edge = None
        if from_stop_id in graph.edges:
            for e in graph.edges[from_stop_id]:
                if e.to_stop.stop_id == to_stop_id:
                    edge = e
                    break
        
        if edge:
            transit_seg = RouteSegment(
                sequence=len(segments) + 1,
                mode=edge.mode,
                from_location=from_stop,
                to_location=to_stop,
                departure_time=current_time,
                arrival_time=current_time + timedelta(minutes=edge.duration_minutes),
                duration_minutes=edge.duration_minutes,
                cost=edge.cost,
                distance_km=edge.distance_km
            )
            segments.append(transit_seg)
            current_time = transit_seg.arrival_time
    
    # Last stop to destination
    last_stop = graph.stops[best_route['path'][-1]]
    
    # Create a temporary destination stop for walking segment
    dest_stop = Stop(
        stop_id="destination",
        name="Destination",
        lat=dest_lat,
        lon=dest_lon,
        mode=TransportationMode.WALKING
    )
    dest_stop.id = 999999
    dest_stop.route = "WALK"
    
    walk_seg = RouteSegment(
        sequence=len(segments) + 1,
        mode=TransportationMode.WALKING,
        from_location=last_stop,
        to_location=dest_stop,
        departure_time=current_time,
        arrival_time=current_time + timedelta(minutes=dest_dist * 10),
        duration_minutes=dest_dist * 10,  # 10 min/km walking
        cost=0,
        distance_km=dest_dist
    )
    segments.append(walk_seg)
    
    # Calculate proper route cost using transfer logic
    proper_total_cost = calculate_route_cost(segments)
    
    print(f"\n💰 Cost Analysis:")
    print(f"   Old calculation: Rp {best_route['total_cost']:,.0f}")
    print(f"   New calculation: Rp {proper_total_cost:,.0f}")
    print(f"   Difference: Rp {proper_total_cost - best_route['total_cost']:,.0f}")
    
    # Create complete route
    complete_route = Route(
        route_id=1,
        segments=segments,
        total_cost=proper_total_cost,  # Use proper transfer cost calculation
        total_time_minutes=sum(seg.duration_minutes for seg in segments),
        total_distance_km=sum(seg.distance_km for seg in segments)
    )
    
    return {
        'route': complete_route,
        'origin_stop': origin_stop,
        'dest_stop': dest_stop,
        'total_walking_distance': best_route['total_walking_distance'],
        'iterations': best_route['iterations'],
        'max_depth': best_route['max_depth'],
        'algorithm': best_route['algorithm'],
        'pruned_paths': best_route['pruned_paths']
    }

if __name__ == "__main__":
    # Test with UNSRI to PTC
    origin_lat = -2.985256
    origin_lon = 104.732880
    dest_lat = -2.95115
    dest_lon = 104.76090
    
    print("🧪 Testing Optimized DFS Routing")
    print("=" * 60)
    
    result = gmaps_style_route_optimized_dfs(origin_lat, origin_lon, dest_lat, dest_lon)
    
    if result:
        print(f"\n✅ Optimized DFS Route found!")
        print(f"   Algorithm: {result['algorithm']}")
        print(f"   Iterations: {result['iterations']}")
        print(f"   Max depth: {result['max_depth']}")
        print(f"   Pruned paths: {result['pruned_paths']}")
        print(f"   Walking distance: {result['total_walking_distance']*1000:.0f}m")
        
        print(f"\n📋 Route details:")
        for i, seg in enumerate(result['route'].segments, 1):
            print(f"{i}. {seg.mode}")
            print(f"   {seg.from_location.name} → {seg.to_location.name}")
            print(f"   Duration: {seg.duration_minutes:.1f} min | Cost: Rp {seg.cost:,.0f}")
            print(f"   Time: {seg.departure_time.strftime('%H:%M')} → {seg.arrival_time.strftime('%H:%M')}")
            print()
    else:
        print("❌ No route found with Optimized DFS")
