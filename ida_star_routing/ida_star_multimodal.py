"""
IDA* (Iterative Deepening A*) with Multi-Modal Support
Enhanced version that supports transfer detection and walking edges
"""

from typing import List, Optional, Set, Dict, Tuple
from datetime import datetime, timedelta
import time as time_module

from .data_structures import (
    Stop,
    Edge,
    Route,
    RouteSegment,
    TransportationGraph,
    TransportationMode
)
from .heuristics import get_heuristic_function
from .dijkstra import haversine_distance_km


# Constants
WALKING_SPEED_KMH = 5.0
MAX_TRANSFER_WALK_KM = 0.5  # 500m
TRANSFER_TIME_PENALTY = 5.0


class IDAStarMultiModalRouter:
    """
    Enhanced IDA* with multi-modal support
    Includes automatic transfer detection like Dijkstra
    """
    
    def __init__(self, graph: TransportationGraph, optimization_mode: str = "time"):
        """
        Initialize IDA* Multi-Modal Router
        
        Args:
            graph: Transportation network (preferably bidirectional)
            optimization_mode: Optimization criteria
        """
        self.graph = graph
        self.optimization_mode = optimization_mode
        self.heuristic = get_heuristic_function(optimization_mode)
        
        # Build transfer map
        self.transfer_map = self._build_transfer_map()
        
        # Statistics
        self.nodes_explored = 0
        self.max_depth_reached = 0
        self.iterations = 0
        
        print(f"\n🔧 IDA* Multi-Modal Router initialized")
        print(f"   Optimization: {optimization_mode}")
        print(f"   Transfer points: {len(self.transfer_map)}")
    
    def _build_transfer_map(self) -> Dict[str, List[Tuple[Stop, float]]]:
        """Build transfer map for nearby stops"""
        print(f"   Building transfer map...")
        
        transfer_map = {}
        stops_list = list(self.graph.stops.values())
        
        for stop in stops_list:
            nearby_stops = []
            
            for other_stop in stops_list:
                if stop.stop_id == other_stop.stop_id:
                    continue
                
                dist_km = haversine_distance_km(
                    stop.lat, stop.lon,
                    other_stop.lat, other_stop.lon
                )
                
                if dist_km <= MAX_TRANSFER_WALK_KM:
                    nearby_stops.append((other_stop, dist_km))
            
            if nearby_stops:
                transfer_map[stop.stop_id] = nearby_stops
        
        return transfer_map
    
    def search(self, 
               start: Stop, 
               goal: Stop,
               departure_time: Optional[datetime] = None,
               max_iterations: int = 1000,
               timeout_seconds: float = 120.0) -> Optional[Route]:
        """
        Find optimal route using IDA* with multi-modal support
        
        Args:
            start: Starting stop
            goal: Destination stop
            departure_time: When to start
            max_iterations: Maximum iterations
            timeout_seconds: Timeout
        
        Returns:
            Route if found, None otherwise
        """
        if departure_time is None:
            departure_time = datetime.now()
        
        print(f"\n🔍 IDA* Multi-Modal Search")
        print(f"   From: {start.name} ({start.mode.value})")
        print(f"   To:   {goal.name} ({goal.mode.value})")
        print(f"   Mode: {self.optimization_mode}")
        
        # Reset stats
        self.nodes_explored = 0
        self.max_depth_reached = 0
        self.iterations = 0
        
        start_time = time_module.time()
        
        # Initial bound
        bound = self.heuristic(start, goal, self.graph)
        
        print(f"\n📊 Initial bound: {bound:.2f}")
        
        while self.iterations < max_iterations:
            self.iterations += 1
            
            # Check timeout
            if time_module.time() - start_time > timeout_seconds:
                print(f"\n⏱️  Timeout reached")
                return None
            
            print(f"\n🔄 Iteration {self.iterations}, Bound: {bound:.2f}")
            
            # DFS with current bound
            result = self._search_recursive(
                current=start,
                goal=goal,
                g_cost=0.0,
                bound=bound,
                visited=set([start.stop_id]),
                current_time=departure_time,
                current_mode=start.mode,
                path=[start],
                segments=[]
            )
            
            if isinstance(result, Route):
                # Solution found! Stop immediately
                elapsed = time_module.time() - start_time
                print(f"\n✅ Solution found!")
                print(f"   Iterations: {self.iterations}")
                print(f"   Nodes explored: {self.nodes_explored}")
                print(f"   Max depth: {self.max_depth_reached}")
                print(f"   Time: {elapsed:.4f}s")
                print(f"   Bound: {bound:.2f}")
                return result
            
            if result == float('inf'):
                print(f"\n❌ No solution exists")
                return None
            
            # Update bound
            bound = result
        
        print(f"\n⚠️  Max iterations reached")
        return None
    
    def _search_recursive(self,
                         current: Stop,
                         goal: Stop,
                         g_cost: float,
                         bound: float,
                         visited: Set[str],
                         current_time: datetime,
                         current_mode: TransportationMode,
                         path: List[Stop],
                         segments: List[RouteSegment]) -> any:
        """
        Recursive IDA* search with transfer support
        
        Returns:
            - Route if goal reached
            - float('inf') if no solution
            - float (new bound) if exceeded current bound
        """
        self.nodes_explored += 1
        
        if len(path) > self.max_depth_reached:
            self.max_depth_reached = len(path)
        
        # Calculate f-cost
        h_cost = self.heuristic(current, goal, self.graph)
        f_cost = g_cost + h_cost
        
        # Exceeded bound
        if f_cost > bound:
            return f_cost
        
        # Goal reached!
        if current.stop_id == goal.stop_id:
            route = Route(route_id=1, segments=segments)
            route.calculate_metrics()
            route.optimization_score = g_cost
            return route
        
        min_exceeded = float('inf')
        
        # Get all possible moves (regular edges + transfers)
        neighbors = []
        
        # 1. Regular edges (same route)
        for edge in self.graph.get_neighbors(current):
            neighbors.append((edge.to_stop, edge, False))  # (stop, edge, is_transfer)
        
        # 2. Transfer edges (walking to nearby stops on different routes)
        if current.stop_id in self.transfer_map:
            for nearby_stop, walk_dist in self.transfer_map[current.stop_id]:
                # Skip if same route
                if nearby_stop.route == current.route:
                    continue
                
                # Skip if already visited
                if nearby_stop.stop_id in visited:
                    continue
                
                # Create virtual walking edge
                walk_time = (walk_dist / WALKING_SPEED_KMH) * 60 + TRANSFER_TIME_PENALTY
                
                virtual_edge = Edge(
                    from_stop=current,
                    to_stop=nearby_stop,
                    route="Transfer (Walking)",
                    mode=TransportationMode.TRANSFER,
                    distance_meters=walk_dist * 1000,
                    base_time_minutes=walk_time,
                    cost=0
                )
                
                neighbors.append((nearby_stop, virtual_edge, True))
        
        # Explore neighbors
        for neighbor, edge, is_transfer in neighbors:
            # Skip if visited
            if neighbor.stop_id in visited:
                continue
            
            # Calculate cost
            edge_cost = self._calculate_edge_cost(edge, current_mode)
            new_g_cost = g_cost + edge_cost
            
            # Create segment
            arrival_time = current_time + timedelta(minutes=edge.base_time_minutes)
            
            segment = RouteSegment(
                sequence=len(segments) + 1,
                mode=edge.mode,
                route_name=edge.route,
                from_stop=current,
                to_stop=neighbor,
                departure_time=current_time,
                arrival_time=arrival_time,
                duration_minutes=edge.base_time_minutes,
                cost=edge.cost,
                distance_km=edge.distance_meters / 1000
            )
            
            # Add to path
            path.append(neighbor)
            visited.add(neighbor.stop_id)
            new_segments = segments + [segment]
            
            # Recursive search
            result = self._search_recursive(
                current=neighbor,
                goal=goal,
                g_cost=new_g_cost,
                bound=bound,
                visited=visited,
                current_time=arrival_time,
                current_mode=edge.mode,
                path=path,
                segments=new_segments
            )
            
            # Check result
            if isinstance(result, Route):
                return result  # Solution found!
            
            if result < min_exceeded:
                min_exceeded = result
            
            # Backtrack
            path.pop()
            visited.remove(neighbor.stop_id)
        
        return min_exceeded
    
    def _calculate_edge_cost(self, edge: Edge, current_mode: TransportationMode) -> float:
        """Calculate cost based on optimization mode"""
        if self.optimization_mode == "time":
            return edge.base_time_minutes
        elif self.optimization_mode == "cost":
            return float(edge.cost)
        elif self.optimization_mode == "transfers":
            transfer_penalty = 15.0 if edge.mode != current_mode else 0.0
            return edge.base_time_minutes + transfer_penalty
        else:  # balanced
            time_norm = edge.base_time_minutes / 60
            cost_norm = edge.cost / 10000
            transfer_penalty = 1.0 if edge.mode != current_mode else 0.0
            return time_norm + cost_norm + transfer_penalty


# Integration with door-to-door system
def gmaps_style_route_ida_star(
    graph: TransportationGraph,
    origin_name: str,
    origin_coords: Tuple[float, float],
    dest_name: str,
    dest_coords: Tuple[float, float],
    optimization_mode: str = "time",
    departure_time: Optional[datetime] = None,
    max_walking_km: float = 2.0
) -> Optional[Route]:
    """
    Google Maps style routing using IDA*
    
    Same interface as Dijkstra version
    """
    if departure_time is None:
        departure_time = datetime.now()
    
    from .door_to_door import Location, DoorToDoorRouter
    # Import from gmaps_style_routing
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from gmaps_style_routing import find_nearest_stops_extended, create_walking_segment
    
    print(f"\n{'='*90}")
    print(f"{'🗺️  GOOGLE MAPS STYLE ROUTING (IDA* Algorithm)':^90}")
    print(f"{'='*90}")
    
    print(f"\n📍 FROM: {origin_name}")
    print(f"   📌 {origin_coords[0]:.5f}, {origin_coords[1]:.5f}")
    
    print(f"\n📍 TO:   {dest_name}")
    print(f"   📌 {dest_coords[0]:.5f}, {dest_coords[1]:.5f}")
    
    # Find nearest stops
    print(f"\n{'─'*90}")
    print(f"STEP 1: Finding nearest transit stops")
    print(f"{'─'*90}")
    
    origin_stops = find_nearest_stops_extended(graph, origin_coords[0], origin_coords[1], max_walking_km)
    dest_stops = find_nearest_stops_extended(graph, dest_coords[0], dest_coords[1], max_walking_km)
    
    if not origin_stops or not dest_stops:
        print(f"❌ No stops found within {max_walking_km}km")
        return None
    
    print(f"✅ Found {len(origin_stops)} origin stops, {len(dest_stops)} destination stops")
    
    # Find best route using IDA*
    print(f"\n{'─'*90}")
    print(f"STEP 2: Finding optimal transit route (IDA* algorithm)")
    print(f"{'─'*90}")
    
    router = IDAStarMultiModalRouter(graph, optimization_mode)
    
    best_route = None
    best_score = float('inf')
    
    print(f"🔍 Trying route combinations...")
    
    for origin_stop, origin_dist in origin_stops[:5]:
        for dest_stop, dest_dist in dest_stops[:5]:
            # Find transit route with IDA*
            # Network size: 402 stops - optimized for 1000 iterations
            # User requested: timeout at 1000 iterations
            transit_route = router.search(origin_stop, dest_stop, departure_time, max_iterations=1000, timeout_seconds=120.0)
            
            if transit_route:
                # Calculate total score
                origin_walk_time = (origin_dist / 5.0) * 60
                dest_walk_time = (dest_dist / 5.0) * 60
                total_time = origin_walk_time + transit_route.total_time_minutes + dest_walk_time
                
                if optimization_mode == "time":
                    score = total_time
                elif optimization_mode == "cost":
                    score = transit_route.total_cost
                else:
                    score = total_time + transit_route.total_cost / 1000
                
                if score < best_score:
                    best_score = score
                    best_route = {
                        'origin_stop': origin_stop,
                        'origin_dist': origin_dist,
                        'dest_stop': dest_stop,
                        'dest_dist': dest_dist,
                        'transit_route': transit_route,
                        'total_time': total_time
                    }
                    print(f"   ✓ Found route: {total_time:.1f} min, Rp {transit_route.total_cost:,}")
    
    if not best_route:
        print(f"❌ No viable route found")
        return None
    
    # Construct complete route
    print(f"\n{'─'*90}")
    print(f"STEP 3: Building complete door-to-door route")
    print(f"{'─'*90}")
    
    segments = []
    current_time = departure_time
    
    # Walking to first stop
    origin_loc = Location(origin_name, origin_coords[0], origin_coords[1])
    origin_stop_loc = Location(
        best_route['origin_stop'].name,
        best_route['origin_stop'].lat,
        best_route['origin_stop'].lon
    )
    
    walk1 = create_walking_segment(1, origin_loc, origin_stop_loc, current_time)
    segments.append(walk1)
    current_time = walk1.arrival_time
    
    # Transit segments
    for transit_seg in best_route['transit_route'].segments:
        transit_seg.sequence = len(segments) + 1
        transit_seg.departure_time = current_time
        transit_seg.arrival_time = current_time + timedelta(minutes=transit_seg.duration_minutes)
        segments.append(transit_seg)
        current_time = transit_seg.arrival_time
    
    # Walking from last stop
    dest_stop_loc = Location(
        best_route['dest_stop'].name,
        best_route['dest_stop'].lat,
        best_route['dest_stop'].lon
    )
    dest_loc = Location(dest_name, dest_coords[0], dest_coords[1])
    
    walk2 = create_walking_segment(len(segments) + 1, dest_stop_loc, dest_loc, current_time)
    segments.append(walk2)
    
    # Create final route
    complete_route = Route(route_id=1, segments=segments)
    complete_route.calculate_metrics()
    complete_route.optimization_score = best_score
    
    return complete_route

