#!/usr/bin/env python3
"""
Pure DFS (Depth First Search) Implementation for Multimodal Routing
Research: PERANCANGAN SISTEM INFORMASI INTEGRASI OPERASIONAL
ANTAR MODA ANGKUTAN UMUM MENGGUNAKAN ALGORITMA DEPTH FIRST SEARCH (DFS) DI KOTA PALEMBANG
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.algorithms.ida_star_routing.data_structures import (
    TransportationGraph, Stop, Edge, Route, RouteSegment, 
    TransportationMode, Location, haversine_distance_km
)
from src.algorithms.ida_star_routing.ida_star_multimodal import (
    load_transportation_network, find_nearest_stops
)

@dataclass
class DFSResult:
    """Result of DFS search"""
    found: bool
    path: List[str]
    total_cost: float
    total_time: float
    total_distance: float
    iterations: int
    max_depth_reached: int

class PureDFSRouter:
    """
    Pure DFS Router for Multimodal Transportation
    
    This implementation uses basic Depth First Search without any heuristics
    or optimizations, making it suitable for research comparison.
    """
    
    def __init__(self, graph: TransportationGraph):
        self.graph = graph
        self.visited = set()
        self.path = []
        self.best_path = None
        self.best_cost = float('inf')
        self.iterations = 0
        self.max_depth_reached = 0
        
    def dfs_search(self, start: str, goal: str, max_depth: int = 15) -> DFSResult:
        """
        Pure DFS search from start to goal
        
        Args:
            start: Starting stop ID
            goal: Goal stop ID
            max_depth: Maximum search depth to prevent infinite loops
            
        Returns:
            DFSResult with search outcome
        """
        self.visited.clear()
        self.path.clear()
        self.best_path = None
        self.best_cost = float('inf')
        self.iterations = 0
        self.max_depth_reached = 0
        
        print(f"🔍 Starting Pure DFS search: {start} → {goal}")
        print(f"   Max depth: {max_depth}")
        
        # Start DFS search
        found = self._dfs_recursive(start, goal, 0, max_depth)
        
        return DFSResult(
            found=found,
            path=self.best_path if self.best_path else [],
            total_cost=self.best_cost if self.best_cost != float('inf') else 0,
            total_time=0,  # Will be calculated separately
            total_distance=0,  # Will be calculated separately
            iterations=self.iterations,
            max_depth_reached=self.max_depth_reached
        )
    
    def _dfs_recursive(self, current: str, goal: str, depth: int, max_depth: int) -> bool:
        """
        Recursive DFS implementation
        
        Args:
            current: Current stop ID
            goal: Goal stop ID
            depth: Current search depth
            max_depth: Maximum allowed depth
            
        Returns:
            True if goal found, False otherwise
        """
        self.iterations += 1
        
        # Update max depth reached
        self.max_depth_reached = max(self.max_depth_reached, depth)
        
        # Check depth limit
        if depth > max_depth:
            return False
        
        # Check if goal reached
        if current == goal:
            # Calculate path cost
            path_cost = self._calculate_path_cost(self.path + [current])
            if path_cost < self.best_cost:
                self.best_cost = path_cost
                self.best_path = self.path + [current].copy()
                print(f"   ✅ Found path at depth {depth}, cost: {path_cost:.2f}")
            return True
        
        # Mark current as visited
        self.visited.add(current)
        self.path.append(current)
        
        # Explore neighbors
        found_goal = False
        if current in self.graph.edges:
            for edge in self.graph.edges[current]:
                neighbor = edge.to_stop.stop_id
                
                if neighbor not in self.visited:
                    if self._dfs_recursive(neighbor, goal, depth + 1, max_depth):
                        found_goal = True
                        # Don't return immediately - continue exploring for better paths
        
        # Backtrack
        self.path.pop()
        self.visited.remove(current)
        
        return found_goal
    
    def _calculate_path_cost(self, path: List[str]) -> float:
        """
        Calculate total cost of a path
        
        Args:
            path: List of stop IDs
            
        Returns:
            Total cost of the path
        """
        if len(path) < 2:
            return 0
        
        total_cost = 0
        for i in range(len(path) - 1):
            from_stop = path[i]
            to_stop = path[i + 1]
            
            if from_stop in self.graph.edges:
                for edge in self.graph.edges[from_stop]:
                    if edge.to_stop.stop_id == to_stop:
                        total_cost += edge.cost
                        break
        
        return total_cost

def gmaps_style_route_dfs(
    origin_lat: float, 
    origin_lon: float, 
    dest_lat: float, 
    dest_lon: float,
    departure_time: datetime = None,
    optimization_mode: str = "time"
) -> Optional[Dict]:
    """
    Google Maps style routing using Pure DFS
    
    Args:
        origin_lat: Origin latitude
        origin_lon: Origin longitude  
        dest_lat: Destination latitude
        dest_lon: Destination longitude
        departure_time: Departure time
        optimization_mode: "time", "cost", or "balanced"
        
    Returns:
        Route information or None if no route found
    """
    if departure_time is None:
        departure_time = datetime.now()
    
    print(f"\n🚀 Pure DFS Routing")
    print(f"   Origin: ({origin_lat:.6f}, {origin_lon:.6f})")
    print(f"   Destination: ({dest_lat:.6f}, {dest_lon:.6f})")
    print(f"   Departure: {departure_time.strftime('%H:%M')}")
    print(f"   Mode: {optimization_mode}")
    
    # Load network
    graph = load_transportation_network()
    if not graph:
        print("❌ Failed to load transportation network")
        return None
    
    # Find nearest stops
    origin_stops = find_nearest_stops(graph, origin_lat, origin_lon, max_stops=5)
    dest_stops = find_nearest_stops(graph, dest_lat, dest_lon, max_stops=5)
    
    if not origin_stops or not dest_stops:
        print("❌ No stops found near origin or destination")
        return None
    
    print(f"\n📍 Nearest stops:")
    print(f"   Origin: {[f'{stop.name} ({dist:.0f}m)' for stop, dist in origin_stops[:3]]}")
    print(f"   Destination: {[f'{stop.name} ({dist:.0f}m)' for stop, dist in dest_stops[:3]]}")
    
    # Try DFS search for each origin-destination combination
    best_route = None
    best_cost = float('inf')
    combinations_tried = 0
    
    print(f"\n🔍 Trying DFS combinations...")
    
    for origin_stop, origin_dist in origin_stops[:3]:  # Try top 3 origin stops
        for dest_stop, dest_dist in dest_stops[:3]:  # Try top 3 dest stops
            combinations_tried += 1
            
            print(f"\n   🔄 Combination {combinations_tried}: {origin_stop.name} → {dest_stop.name}")
            
            # Create DFS router
            dfs_router = PureDFSRouter(graph)
            
            # Try DFS search with different max depths
            for max_depth in [10, 15, 20]:  # Try different depth limits
                print(f"      📏 Trying max depth: {max_depth}")
                
                result = dfs_router.dfs_search(
                    origin_stop.stop_id, 
                    dest_stop.stop_id, 
                    max_depth=max_depth
                )
                
                if result.found and result.path:
                    print(f"      ✅ DFS found path: {len(result.path)} stops, cost: {result.total_cost:.2f}")
                    
                    # Calculate total walking distance
                    total_walking_distance = origin_dist + dest_dist
                    
                    # Create route
                    route_info = {
                        'origin_stop': origin_stop,
                        'dest_stop': dest_stop,
                        'path': result.path,
                        'total_cost': result.total_cost,
                        'total_walking_distance': total_walking_distance,
                        'iterations': result.iterations,
                        'max_depth': result.max_depth_reached
                    }
                    
                    # Check if this is better
                    if result.total_cost < best_cost:
                        best_cost = result.total_cost
                        best_route = route_info
                        print(f"      🎯 New best route found!")
                    
                    # Early termination if we found a good route
                    if result.total_cost < 1000:  # Very low cost
                        print(f"      🎯 Early termination: Very low cost route found!")
                        break
                else:
                    print(f"      ❌ DFS failed at depth {max_depth}")
            
            # Early termination if we found a very good route
            if best_route and best_route['total_cost'] < 1000:
                break
        
        # Early termination if we found a very good route
        if best_route and best_route['total_cost'] < 1000:
            break
    
    print(f"\n   📊 Checked {combinations_tried} combinations")
    
    if not best_route:
        print(f"❌ No viable route found with Pure DFS")
        return None
    
    # Build complete route
    print(f"\n✅ Best DFS route found:")
    print(f"   Path: {' → '.join([graph.stops[stop_id].name for stop_id in best_route['path']])}")
    print(f"   Cost: {best_route['total_cost']:.2f}")
    print(f"   Walking: {best_route['total_walking_distance']*1000:.0f}m")
    print(f"   Iterations: {best_route['iterations']}")
    print(f"   Max depth: {best_route['max_depth']}")
    
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
            from_loc = Location(from_stop.name, from_stop.lat, from_stop.lon)
            to_loc = Location(to_stop.name, to_stop.lat, to_stop.lon)
            
            transit_seg = RouteSegment(
                sequence=len(segments) + 1,
                mode=edge.mode,
                from_location=from_loc,
                to_location=to_loc,
                duration_minutes=edge.duration_minutes,
                cost=edge.cost,
                distance_km=edge.distance_km,
                departure_time=current_time,
                arrival_time=current_time + timedelta(minutes=edge.duration_minutes)
            )
            segments.append(transit_seg)
            current_time = transit_seg.arrival_time
    
    # Last stop to destination
    last_stop = graph.stops[best_route['path'][-1]]
    dest_stop = best_route['dest_stop']
    
    last_stop_loc = Location(last_stop.name, last_stop.lat, last_stop.lon)
    dest_loc = Location("Destination", dest_lat, dest_lon)
    
    walk_seg = RouteSegment(
        sequence=len(segments) + 1,
        mode=TransportationMode.WALKING,
        from_location=last_stop_loc,
        to_location=dest_loc,
        duration_minutes=dest_dist * 10,  # 10 min/km walking
        cost=0,
        distance_km=dest_dist,
        departure_time=current_time,
        arrival_time=current_time + timedelta(minutes=dest_dist * 10)
    )
    segments.append(walk_seg)
    
    # Create complete route
    complete_route = Route(
        segments=segments,
        total_cost=best_route['total_cost'],
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
        'algorithm': 'Pure DFS'
    }

if __name__ == "__main__":
    # Test with UNSRI to PTC
    origin_lat = -2.985256
    origin_lon = 104.732880
    dest_lat = -2.95115
    dest_lon = 104.76090
    
    print("🧪 Testing Pure DFS Routing")
    print("=" * 50)
    
    result = gmaps_style_route_dfs(origin_lat, origin_lon, dest_lat, dest_lon)
    
    if result:
        print(f"\n✅ DFS Route found!")
        print(f"   Algorithm: {result['algorithm']}")
        print(f"   Iterations: {result['iterations']}")
        print(f"   Max depth: {result['max_depth']}")
        print(f"   Walking distance: {result['total_walking_distance']*1000:.0f}m")
        
        print(f"\n📋 Route details:")
        for i, seg in enumerate(result['route'].segments, 1):
            print(f"{i}. {seg.mode.value}")
            print(f"   {seg.from_location.name} → {seg.to_location.name}")
            print(f"   Duration: {seg.duration_minutes:.1f} min | Cost: Rp {seg.cost:,.0f}")
            print(f"   Time: {seg.departure_time.strftime('%H:%M')} → {seg.arrival_time.strftime('%H:%M')}")
            print()
    else:
        print("❌ No route found with Pure DFS")
