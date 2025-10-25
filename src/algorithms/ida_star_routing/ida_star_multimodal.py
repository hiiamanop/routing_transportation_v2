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
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from core.gmaps_style_routing import find_nearest_stops_extended, create_walking_segment
    
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
    print(f"   📍 Origin stops: {[s.name for s, d in origin_stops[:5]]}")
    print(f"   📍 Dest stops: {[s.name for s, d in dest_stops[:5]]}")
    
    # OPTIMIZATION: Network Simplification (like DFS-IDA* UMI)
    print(f"\n🔧 Applying Network Simplification...")
    simplified_graph = create_simplified_network(graph, origin_stops[:5], dest_stops[:5])
    print(f"   📉 Network simplified: {len(graph.stops)} → {len(simplified_graph.stops)} stops")
    
    # Use simplified network for IDA* search
    router_simplified = IDAStarMultiModalRouter(simplified_graph, optimization_mode)
    
    # Try ONLY TOP 2 combinations first (2x2 = 4 combinations) for ULTRA-FAST optimal solution
    combinations_tried = 0
    
    for origin_stop, origin_dist in origin_stops[:2]:  # Only top 2 origin stops (most promising)
        for dest_stop, dest_dist in dest_stops[:2]:  # Only top 2 dest stops (most promising)
            combinations_tried += 1
            # Find transit route with IDA* using simplified network
            print(f"   🔍 Trying: {origin_stop.name} → {dest_stop.name}")
            
            # ULTRA-INCREASED iterations for top combinations to find optimal solution
            max_iterations = 3000 if combinations_tried <= 2 else 1500  # Even more iterations for first 2 combinations
            timeout_seconds = 240.0 if combinations_tried <= 2 else 150.0  # Even more time for first 2 combinations
            
            transit_route = router_simplified.search(origin_stop, dest_stop, departure_time, max_iterations=max_iterations, timeout_seconds=timeout_seconds)
            
            if transit_route:
                # Calculate total score - SAME AS DIJKSTRA
                origin_walk_time = (origin_dist / 5.0) * 60  # 5 km/h walking speed
                dest_walk_time = (dest_dist / 5.0) * 60
                total_walking_distance = origin_dist + dest_dist  # Total walking distance in km
                total_time = origin_walk_time + transit_route.total_time_minutes + dest_walk_time
                
                # USE SAME SCORING AS DIJKSTRA
                if optimization_mode == "time":
                    score = total_time  # Same as Dijkstra: just total time
                elif optimization_mode == "cost":
                    score = transit_route.total_cost  # Same as Dijkstra: walking is free
                else:
                    score = total_time + transit_route.total_cost / 1000  # Same as Dijkstra: balanced
                
                if score < best_score:
                    best_score = score
                    best_route = {
                        'origin_stop': origin_stop,
                        'origin_dist': origin_dist,
                        'dest_stop': dest_stop,
                        'dest_dist': dest_dist,
                        'transit_route': transit_route,
                        'total_time': total_time,
                        'total_walking_distance': total_walking_distance
                    }
                    print(f"   ✓ Found route: {total_time:.1f} min, Rp {transit_route.total_cost:,}")
                    print(f"      Origin: {origin_stop.name} ({origin_dist*1000:.0f}m)")
                    print(f"      Dest: {dest_stop.name} ({dest_dist*1000:.0f}m)")
                    print(f"      Walking: {total_walking_distance*1000:.0f}m, Score: {score:.1f}")
                    
                # ULTRA-AGGRESSIVE EARLY TERMINATION: If walking distance is very small (< 300m), this is likely optimal
                if total_walking_distance < 0.3:  # Less than 300m walking
                    print(f"   🎯 ULTRA-EARLY TERMINATION: Very low walking distance ({total_walking_distance*1000:.0f}m) - likely optimal!")
                    # Break both inner and outer loops
                    break
                
                # Continue searching for better routes, but with early termination for very good solutions
            else:
                print(f"   ❌ No route found: {origin_stop.name} → {dest_stop.name}")
        
        # Break outer loop if we found a very good solution
        if best_route and best_route.get('total_walking_distance', float('inf')) < 0.2:
            break
    
    # If no route found, try more combinations (fallback to top 5x5)
    if not best_route:
        print(f"   📊 Checked {combinations_tried} combinations, trying more...")
        
        # Fallback: Try more combinations if no route found
        for origin_stop, origin_dist in origin_stops[2:5]:  # Try next 3 origin stops
            for dest_stop, dest_dist in dest_stops[2:5]:  # Try next 3 dest stops
                combinations_tried += 1
                print(f"   🔍 Trying: {origin_stop.name} → {dest_stop.name}")
                
                # Standard iterations for fallback combinations
                max_iterations = 1000
                timeout_seconds = 120.0
                
                transit_route = router_simplified.search(origin_stop, dest_stop, departure_time, max_iterations=max_iterations, timeout_seconds=timeout_seconds)
                
                if transit_route:
                    # Calculate total score - SAME AS DIJKSTRA
                    total_walking_distance = origin_dist + dest_dist
                    total_time = transit_route.total_time_minutes + (total_walking_distance * 10)  # 10 min/km walking
                    
                    if optimization_mode == "time":
                        score = total_time  # Same as Dijkstra: just total time
                    elif optimization_mode == "cost":
                        score = transit_route.total_cost  # Same as Dijkstra: walking is free
                    else:
                        score = total_time + transit_route.total_cost / 1000  # Same as Dijkstra: balanced
                    
                    if score < best_score:
                        best_score = score
                        best_route = transit_route
                        best_origin_stop = origin_stop
                        best_dest_stop = dest_stop
                        best_origin_dist = origin_dist
                        best_dest_dist = dest_dist
                        
                        print(f"   ✓ Found route: {total_time:.1f} min, Rp {transit_route.total_cost:,}")
                        print(f"      Origin: {origin_stop.name} ({origin_dist*1000:.0f}m)")
                        print(f"      Dest: {dest_stop.name} ({dest_dist*1000:.0f}m)")
                        print(f"      Walking: {total_walking_distance*1000:.0f}m, Score: {score:.1f}")
                        
                        # Early termination for fallback too
                        if total_walking_distance < 0.5:  # Less than 500m walking
                            print(f"   🎯 EARLY TERMINATION: Low walking distance ({total_walking_distance*1000:.0f}m) - likely optimal!")
                            break
                else:
                    print(f"   ❌ No route found: {origin_stop.name} → {dest_stop.name}")
            
            if best_route:
                break
    
    print(f"\n   📊 Checked {combinations_tried} combinations")
    
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
        best_origin_stop.name,
        best_origin_stop.lat,
        best_origin_stop.lon
    )
    
    walk1 = create_walking_segment(1, origin_loc, origin_stop_loc, current_time)
    segments.append(walk1)
    current_time = walk1.arrival_time
    
    # Transit segments
    for transit_seg in best_route.segments:
        transit_seg.sequence = len(segments) + 1
        transit_seg.departure_time = current_time
        transit_seg.arrival_time = current_time + timedelta(minutes=transit_seg.duration_minutes)
        segments.append(transit_seg)
        current_time = transit_seg.arrival_time
    
    # Walking from last stop
    dest_stop_loc = Location(
        best_dest_stop.name,
        best_dest_stop.lat,
        best_dest_stop.lon
    )
    dest_loc = Location(dest_name, dest_coords[0], dest_coords[1])
    
    walk2 = create_walking_segment(len(segments) + 1, dest_stop_loc, dest_loc, current_time)
    segments.append(walk2)
    
    # Create final route
    complete_route = Route(route_id=1, segments=segments)
    complete_route.calculate_metrics()
    complete_route.optimization_score = best_score
    
    return complete_route


def create_simplified_network(graph, origin_stops, dest_stops):
    """
    Create ULTRA-SIMPLIFIED network for IDA* search (based on DFS-IDA* UMI research)
    
    Strategy:
    1. Keep ONLY origin/destination stops and their immediate neighbors
    2. Keep ONLY LRT stations (highest priority)
    3. Keep ONLY stops within VERY small radius (1.2x direct distance)
    4. Remove ALL intermediate stops to minimize search space
    """
    simplified = TransportationGraph()
    
    # Get origin and destination coordinates
    origin_coords = [(stop.lat, stop.lon) for stop, _ in origin_stops[:2]]  # Only top 2
    dest_coords = [(stop.lat, stop.lon) for stop, _ in dest_stops[:2]]  # Only top 2
    
    # Calculate ULTRA-SMALL search radius (1.2x direct distance for maximum filtering)
    max_dist = 0
    for orig_coord in origin_coords:
        for dest_coord in dest_coords:
            dist = haversine_distance_km(orig_coord[0], orig_coord[1], dest_coord[0], dest_coord[1])
            max_dist = max(max_dist, dist)
    
    search_radius = max(max_dist * 1.2, 2.0)  # Ultra-small radius, minimum 2 km
    
    # ULTRA-AGGRESSIVE filtering
    for stop_id, stop in graph.stops.items():
        should_add = False
        
        # Rule 1: ONLY LRT stations (highest priority)
        if stop.mode == TransportationMode.LRT:
            should_add = True
        
        # Rule 2: Origin/destination stops (only top 2)
        elif stop_id in [stop.stop_id for stop, _ in origin_stops[:2]] or stop_id in [stop.stop_id for stop, _ in dest_stops[:2]]:
            should_add = True
        
        # Rule 3: Within ULTRA-SMALL search radius
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
        if from_id in graph.edges:
            for edge in graph.edges[from_id]:
                if edge.to_stop.stop_id in simplified.stops:
                    simplified.add_edge(edge)
    
    return simplified

