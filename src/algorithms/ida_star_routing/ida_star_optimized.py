"""
ULTRA-OPTIMIZED IDA* (Iterative Deepening A*) with Multi-Modal Support
Tuned to match Dijkstra performance without fallback

Key Optimizations:
1. AGGRESSIVE bound initialization (start with realistic bound)
2. SMART bound increment (exponential growth)
3. ULTRA-FAST heuristic (direct distance + mode penalties)
4. AGGRESSIVE pruning (visited states, dominated paths)
5. EARLY termination (good enough solutions)
"""

from typing import List, Optional, Set, Dict, Tuple
from datetime import datetime, timedelta
import time as time_module
import math

from .data_structures import (
    Stop,
    Edge,
    Route,
    RouteSegment,
    TransportationGraph,
    TransportationMode
)
from .dijkstra import haversine_distance_km


# ULTRA-OPTIMIZED Constants
WALKING_SPEED_KMH = 5.0
MAX_TRANSFER_WALK_KM = 0.8  # Increased for better connectivity
TRANSFER_TIME_PENALTY = 3.0  # Reduced penalty
MODE_SWITCH_PENALTY = 8.0  # Penalty for switching transport modes


class UltraOptimizedIDAStarRouter:
    """
    ULTRA-OPTIMIZED IDA* Router designed to match Dijkstra performance
    """
    
    def __init__(self, graph: TransportationGraph, optimization_mode: str = "time"):
        self.graph = graph
        self.optimization_mode = optimization_mode
        
        # Build ULTRA-FAST transfer map
        self.transfer_map = self._build_ultra_fast_transfer_map()
        
        # Statistics
        self.nodes_explored = 0
        self.max_depth_reached = 0
        self.iterations = 0
        
        print(f"\n🚀 ULTRA-OPTIMIZED IDA* Router initialized")
        print(f"   Optimization: {optimization_mode}")
        print(f"   Transfer points: {len(self.transfer_map)}")
    
    def _build_ultra_fast_transfer_map(self) -> Dict[str, List[Tuple[Stop, float]]]:
        """Build ULTRA-FAST transfer map with aggressive filtering"""
        transfer_map = {}
        stops_list = list(self.graph.stops.values())
        
        # AGGRESSIVE filtering: Only consider high-priority stops for transfers
        priority_stops = [s for s in stops_list if s.mode in [TransportationMode.LRT, TransportationMode.TEMAN_BUS]]
        
        for stop in stops_list:
            nearby_stops = []
            
            # Check against priority stops first
            for other_stop in priority_stops:
                if stop.stop_id == other_stop.stop_id or stop.route == other_stop.route:
                    continue
                
                dist_km = haversine_distance_km(stop.lat, stop.lon, other_stop.lat, other_stop.lon)
                
                if dist_km <= MAX_TRANSFER_WALK_KM:
                    nearby_stops.append((other_stop, dist_km))
            
            # Then check regular stops but with stricter distance
            for other_stop in stops_list:
                if (stop.stop_id == other_stop.stop_id or 
                    stop.route == other_stop.route or
                    other_stop in [s for s, _ in nearby_stops]):
                    continue
                
                dist_km = haversine_distance_km(stop.lat, stop.lon, other_stop.lat, other_stop.lon)
                
                if dist_km <= MAX_TRANSFER_WALK_KM * 0.6:  # Stricter for regular stops
                    nearby_stops.append((other_stop, dist_km))
            
            # Sort by distance and keep only top 5
            nearby_stops.sort(key=lambda x: x[1])
            if nearby_stops:
                transfer_map[stop.stop_id] = nearby_stops[:5]
        
        return transfer_map
    
    def _ultra_fast_heuristic(self, current: Stop, goal: Stop) -> float:
        """
        ULTRA-FAST heuristic that closely approximates actual cost
        """
        # Direct distance
        dist_km = haversine_distance_km(current.lat, current.lon, goal.lat, goal.lon)
        
        if self.optimization_mode == "time":
            # Estimate time: assume optimal transport speed
            if dist_km < 2.0:
                # Short distance: walking + one bus
                return (dist_km / WALKING_SPEED_KMH) * 60 + 15  # 15 min bus ride
            elif dist_km < 10.0:
                # Medium distance: walking + bus + transfer
                return (dist_km / 25.0) * 60 + 20  # 25 km/h average speed + 20 min overhead
            else:
                # Long distance: walking + LRT + bus
                return (dist_km / 35.0) * 60 + 25  # 35 km/h average speed + 25 min overhead
        
        elif self.optimization_mode == "cost":
            # Estimate cost based on distance
            if dist_km < 5.0:
                return 5000  # One bus fare
            elif dist_km < 15.0:
                return 8000  # Bus + transfer
            else:
                return 12000  # Multiple transfers
        
        else:  # balanced
            time_est = self._ultra_fast_heuristic(current, goal) if self.optimization_mode != "time" else (dist_km / 25.0) * 60 + 20
            cost_est = 8000 if dist_km > 5.0 else 5000
            return time_est + cost_est / 1000
    
    def search(self, 
               start: Stop, 
               goal: Stop,
               departure_time: Optional[datetime] = None,
               max_iterations: int = 50,  # DRASTICALLY reduced
               timeout_seconds: float = 60.0) -> Optional[Route]:  # Reduced timeout
        """
        ULTRA-OPTIMIZED IDA* search with aggressive bounds and pruning
        """
        if departure_time is None:
            departure_time = datetime.now()
        
        print(f"\n🚀 ULTRA-OPTIMIZED IDA* Search")
        print(f"   From: {start.name} ({start.mode.value})")
        print(f"   To:   {goal.name} ({goal.mode.value})")
        
        # Reset stats
        self.nodes_explored = 0
        self.max_depth_reached = 0
        self.iterations = 0
        
        start_time = time_module.time()
        
        # AGGRESSIVE initial bound (much higher than conservative heuristic)
        heuristic_bound = self._ultra_fast_heuristic(start, goal)
        bound = heuristic_bound * 1.5  # Start with 1.5x heuristic (aggressive)
        
        print(f"📊 Heuristic: {heuristic_bound:.2f}, Initial bound: {bound:.2f}")
        
        # ULTRA-AGGRESSIVE bound sequence
        bound_multipliers = [1.5, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0]  # Exponential growth
        
        for multiplier in bound_multipliers:
            if self.iterations >= max_iterations:
                break
                
            self.iterations += 1
            current_bound = heuristic_bound * multiplier
            
            # Check timeout
            if time_module.time() - start_time > timeout_seconds:
                print(f"⏱️  Timeout reached")
                break
            
            print(f"🔄 Iteration {self.iterations}, Bound: {current_bound:.2f}")
            
            # DFS with current bound
            result = self._search_recursive(
                current=start,
                goal=goal,
                g_cost=0.0,
                bound=current_bound,
                visited=set([start.stop_id]),
                current_time=departure_time,
                current_mode=start.mode,
                path=[start],
                segments=[],
                depth=0
            )
            
            if isinstance(result, Route):
                elapsed = time_module.time() - start_time
                print(f"✅ Solution found!")
                print(f"   Iterations: {self.iterations}")
                print(f"   Nodes explored: {self.nodes_explored}")
                print(f"   Max depth: {self.max_depth_reached}")
                print(f"   Time: {elapsed:.4f}s")
                print(f"   Final bound: {current_bound:.2f}")
                return result
            
            if result == float('inf'):
                print(f"❌ No solution exists")
                break
        
        print(f"⚠️  Search completed without solution")
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
                         segments: List[RouteSegment],
                         depth: int) -> any:
        """
        ULTRA-OPTIMIZED recursive search with aggressive pruning
        """
        self.nodes_explored += 1
        
        if depth > self.max_depth_reached:
            self.max_depth_reached = depth
        
        # AGGRESSIVE depth limit
        if depth > 15:  # Much stricter depth limit
            return float('inf')
        
        # Calculate f-cost with ULTRA-FAST heuristic
        h_cost = self._ultra_fast_heuristic(current, goal)
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
        
        # Get neighbors with ULTRA-AGGRESSIVE filtering
        neighbors = self._get_ultra_filtered_neighbors(current, visited, goal)
        
        # Sort neighbors by heuristic (best-first within IDA*)
        neighbors.sort(key=lambda x: self._ultra_fast_heuristic(x[0], goal))
        
        # Explore only TOP neighbors (aggressive pruning)
        max_neighbors = min(8, len(neighbors))  # Only explore top 8 neighbors
        
        for neighbor, edge, is_transfer in neighbors[:max_neighbors]:
            # Skip if visited
            if neighbor.stop_id in visited:
                continue
            
            # Calculate cost with mode switching penalty
            edge_cost = self._calculate_optimized_edge_cost(edge, current_mode)
            new_g_cost = g_cost + edge_cost
            
            # AGGRESSIVE pruning: skip if cost is already too high
            if new_g_cost > bound * 0.8:  # Skip if already 80% of bound
                continue
            
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
                segments=new_segments,
                depth=depth + 1
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
    
    def _get_ultra_filtered_neighbors(self, current: Stop, visited: Set[str], goal: Stop) -> List[Tuple[Stop, Edge, bool]]:
        """Get neighbors with ULTRA-AGGRESSIVE filtering"""
        neighbors = []
        goal_dist = haversine_distance_km(current.lat, current.lon, goal.lat, goal.lon)
        
        # 1. Regular edges (same route) - with distance filtering
        for edge in self.graph.get_neighbors(current):
            if edge.to_stop.stop_id in visited:
                continue
            
            # AGGRESSIVE filtering: only consider edges that move towards goal
            to_goal_dist = haversine_distance_km(edge.to_stop.lat, edge.to_stop.lon, goal.lat, goal.lon)
            
            # Only add if it moves us closer to goal (or very slightly further for necessary connections)
            if to_goal_dist <= goal_dist * 1.1:  # Allow 10% detour
                neighbors.append((edge.to_stop, edge, False))
        
        # 2. Transfer edges - ULTRA-SELECTIVE
        if current.stop_id in self.transfer_map:
            for nearby_stop, walk_dist in self.transfer_map[current.stop_id][:3]:  # Only top 3 transfers
                if nearby_stop.stop_id in visited or nearby_stop.route == current.route:
                    continue
                
                # Only consider transfers that significantly move towards goal
                to_goal_dist = haversine_distance_km(nearby_stop.lat, nearby_stop.lon, goal.lat, goal.lon)
                
                if to_goal_dist < goal_dist * 0.9:  # Must move significantly closer (10% improvement)
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
        
        return neighbors
    
    def _calculate_optimized_edge_cost(self, edge: Edge, current_mode: TransportationMode) -> float:
        """Calculate cost with optimized penalties"""
        base_cost = 0.0
        
        if self.optimization_mode == "time":
            base_cost = edge.base_time_minutes
        elif self.optimization_mode == "cost":
            base_cost = float(edge.cost)
        else:  # balanced
            base_cost = edge.base_time_minutes + edge.cost / 1000
        
        # Mode switching penalty
        if edge.mode != current_mode and current_mode != TransportationMode.TRANSFER:
            base_cost += MODE_SWITCH_PENALTY
        
        return base_cost


# Integration function (same interface as original)
def gmaps_style_route_ultra_optimized_ida_star(
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
    ULTRA-OPTIMIZED Google Maps style routing using IDA*
    Designed to match Dijkstra performance
    """
    if departure_time is None:
        departure_time = datetime.now()
    
    from .door_to_door import Location
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from core.gmaps_style_routing import find_nearest_stops_extended, create_walking_segment
    
    print(f"\n{'='*90}")
    print(f"{'🚀 ULTRA-OPTIMIZED IDA* ROUTING':^90}")
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
    
    # ULTRA-OPTIMIZED route finding
    print(f"\n{'─'*90}")
    print(f"STEP 2: ULTRA-OPTIMIZED IDA* search")
    print(f"{'─'*90}")
    
    router = UltraOptimizedIDAStarRouter(graph, optimization_mode)
    
    best_route = None
    best_score = float('inf')
    
    # ULTRA-AGGRESSIVE: Only try TOP 2x2 combinations (4 total)
    combinations_tried = 0
    
    for origin_stop, origin_dist in origin_stops[:2]:  # Only top 2
        for dest_stop, dest_dist in dest_stops[:2]:  # Only top 2
            combinations_tried += 1
            print(f"   🚀 Trying: {origin_stop.name} → {dest_stop.name}")
            
            # ULTRA-FAST search with tight limits
            transit_route = router.search(
                origin_stop, 
                dest_stop, 
                departure_time, 
                max_iterations=20,  # Very low iteration limit
                timeout_seconds=30.0  # Very tight timeout
            )
            
            if transit_route:
                # Calculate score EXACTLY like Dijkstra
                origin_walk_time = (origin_dist / 5.0) * 60
                dest_walk_time = (dest_dist / 5.0) * 60
                total_walking_distance = origin_dist + dest_dist
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
                        'total_time': total_time,
                        'total_walking_distance': total_walking_distance
                    }
                    print(f"   ✅ Found route: {total_time:.1f} min, Rp {transit_route.total_cost:,}")
                    
                    # ULTRA-EARLY termination for very good solutions
                    if total_walking_distance < 0.4:  # Less than 400m walking
                        print(f"   🎯 ULTRA-EARLY TERMINATION: Excellent solution!")
                        break
            else:
                print(f"   ❌ No route found")
        
        # Break outer loop if excellent solution found
        if best_route and best_route.get('total_walking_distance', float('inf')) < 0.4:
            break
    
    print(f"\n   📊 Checked {combinations_tried} combinations")
    
    if not best_route:
        print(f"❌ No viable route found")
        return None
    
    # Construct complete route
    print(f"\n{'─'*90}")
    print(f"STEP 3: Building complete route")
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
