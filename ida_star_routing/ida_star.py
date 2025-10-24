"""
IDA* (Iterative Deepening A*) Algorithm Implementation
For Multi-Modal Public Transportation Route Planning
"""

from typing import List, Optional, Tuple, Set
from datetime import datetime, timedelta
import time as time_module

from .data_structures import (
    Stop,
    Edge,
    Route,
    RouteSegment,
    SearchNode,
    TransportationGraph,
    TransportationMode,
    TrafficCondition
)
from .heuristics import get_heuristic_function


class IDAStarRouter:
    """IDA* Algorithm for finding optimal routes"""
    
    def __init__(self, graph: TransportationGraph, optimization_mode: str = "time"):
        """
        Initialize IDA* Router
        
        Args:
            graph: Transportation network graph
            optimization_mode: "time", "cost", "transfers", or "balanced"
        """
        self.graph = graph
        self.optimization_mode = optimization_mode
        self.heuristic = get_heuristic_function(optimization_mode)
        
        # Statistics
        self.nodes_explored = 0
        self.max_depth_reached = 0
        self.iterations = 0
        
    def search(self,
               start: Stop,
               goal: Stop,
               departure_time: Optional[datetime] = None,
               max_iterations: int = 100,
               timeout_seconds: float = 30.0) -> Optional[Route]:
        """
        Find optimal route using IDA* algorithm
        
        Args:
            start: Starting stop
            goal: Destination stop
            departure_time: When to start journey (default: now)
            max_iterations: Maximum iterations to prevent infinite loops
            timeout_seconds: Maximum time to search
        
        Returns:
            Route object if found, None otherwise
        """
        if departure_time is None:
            departure_time = datetime.now()
        
        print(f"\n🔍 IDA* Search: {start.name} → {goal.name}")
        print(f"   Mode: {self.optimization_mode}")
        print(f"   Departure: {departure_time.strftime('%H:%M')}")
        
        # Reset statistics
        self.nodes_explored = 0
        self.max_depth_reached = 0
        self.iterations = 0
        
        start_time = time_module.time()
        
        # Initial bound is heuristic from start to goal
        bound = self.heuristic(start, goal, self.graph)
        path = [start]
        
        print(f"\n📊 Initial bound: {bound:.2f}")
        
        while self.iterations < max_iterations:
            self.iterations += 1
            
            # Check timeout
            if time_module.time() - start_time > timeout_seconds:
                print(f"\n⏱️  Timeout reached ({timeout_seconds}s)")
                return None
            
            print(f"\n🔄 Iteration {self.iterations}, Bound: {bound:.2f}")
            
            # Perform DFS with current bound
            result = self._search_recursive(
                path=path,
                g_cost=0.0,
                bound=bound,
                goal=goal,
                visited=set([start]),
                current_time=departure_time,
                current_mode=start.mode,
                segments=[]
            )
            
            if isinstance(result, Route):
                # Solution found!
                elapsed = time_module.time() - start_time
                print(f"\n✅ Solution found!")
                print(f"   Iterations: {self.iterations}")
                print(f"   Nodes explored: {self.nodes_explored}")
                print(f"   Max depth: {self.max_depth_reached}")
                print(f"   Time: {elapsed:.2f}s")
                return result
            
            if result == float('inf'):
                # No solution exists
                print(f"\n❌ No solution exists")
                return None
            
            # Update bound for next iteration
            bound = result
        
        print(f"\n⚠️  Max iterations reached ({max_iterations})")
        return None
    
    def _search_recursive(self,
                         path: List[Stop],
                         g_cost: float,
                         bound: float,
                         goal: Stop,
                         visited: Set[Stop],
                         current_time: datetime,
                         current_mode: TransportationMode,
                         segments: List[RouteSegment]) -> any:
        """
        Recursive DFS search with cost limit (IDA* core)
        
        Returns:
            - Route object if goal reached
            - float('inf') if no solution possible
            - float (new bound) if exceeded current bound
        """
        current = path[-1]
        self.nodes_explored += 1
        
        # Update max depth
        if len(path) > self.max_depth_reached:
            self.max_depth_reached = len(path)
        
        # Calculate f-cost = g-cost + heuristic
        h_cost = self.heuristic(current, goal, self.graph)
        f_cost = g_cost + h_cost
        
        # If f-cost exceeds bound, return minimum exceeded value
        if f_cost > bound:
            return f_cost
        
        # Goal reached!
        if current.id == goal.id:
            # Construct route from segments
            route = Route(route_id=1, segments=segments)
            route.calculate_metrics()
            route.optimization_score = route.calculate_optimization_score(self.optimization_mode)
            return route
        
        min_exceeded = float('inf')
        
        # Explore neighbors (DFS style)
        neighbors = self.graph.get_neighbors(current)
        
        for edge in neighbors:
            neighbor = edge.to_stop
            
            # Avoid cycles (don't revisit stops)
            if neighbor in visited:
                continue
            
            # Calculate segment cost and time
            segment_cost = self._calculate_segment_cost(
                edge, current_mode, current_time
            )
            
            # Create route segment
            segment_duration = edge.base_time_minutes
            segment_arrival = current_time + timedelta(minutes=segment_duration)
            
            segment = RouteSegment(
                sequence=len(segments) + 1,
                mode=edge.mode,
                route_name=edge.route,
                from_stop=current,
                to_stop=neighbor,
                departure_time=current_time,
                arrival_time=segment_arrival,
                duration_minutes=segment_duration,
                cost=edge.cost,
                distance_km=edge.distance_meters / 1000
            )
            
            # Add to path
            path.append(neighbor)
            visited.add(neighbor)
            new_segments = segments + [segment]
            
            # Recursive search
            result = self._search_recursive(
                path=path,
                g_cost=g_cost + segment_cost,
                bound=bound,
                goal=goal,
                visited=visited,
                current_time=segment_arrival,
                current_mode=edge.mode,
                segments=new_segments
            )
            
            # Check result
            if isinstance(result, Route):
                return result  # Solution found, propagate up
            
            if result < min_exceeded:
                min_exceeded = result
            
            # Backtrack
            path.pop()
            visited.remove(neighbor)
        
        return min_exceeded
    
    def _calculate_segment_cost(self,
                                edge: Edge,
                                current_mode: TransportationMode,
                                current_time: datetime) -> float:
        """
        Calculate cost for taking this edge
        Cost depends on optimization mode
        """
        if self.optimization_mode == "time":
            return edge.base_time_minutes
        elif self.optimization_mode == "cost":
            return float(edge.cost)
        elif self.optimization_mode == "transfers":
            # Penalize mode changes
            transfer_penalty = 15.0 if edge.mode != current_mode else 0.0
            return edge.base_time_minutes + transfer_penalty
        else:  # balanced
            time_norm = edge.base_time_minutes / 60
            cost_norm = edge.cost / 10000
            transfer_penalty = 1.0 if edge.mode != current_mode else 0.0
            return time_norm + cost_norm + transfer_penalty
    
    def find_multiple_routes(self,
                            start: Stop,
                            goal: Stop,
                            departure_time: Optional[datetime] = None,
                            num_routes: int = 3,
                            timeout_seconds: float = 60.0) -> List[Route]:
        """
        Find multiple alternative routes
        
        This is a simplified approach - finds one route,
        then blocks it and finds another (k-shortest paths approach)
        
        Args:
            start: Starting stop
            goal: Destination stop
            departure_time: When to start
            num_routes: Number of routes to find
            timeout_seconds: Total timeout for all searches
        
        Returns:
            List of Route objects
        """
        if departure_time is None:
            departure_time = datetime.now()
        
        routes = []
        blocked_edges = set()
        
        start_time = time_module.time()
        
        for i in range(num_routes):
            # Check timeout
            elapsed = time_module.time() - start_time
            if elapsed > timeout_seconds:
                print(f"\n⏱️  Timeout for finding {num_routes} routes")
                break
            
            print(f"\n🔍 Finding route {i+1}/{num_routes}...")
            
            # Find route (with blocked edges)
            route = self.search(
                start=start,
                goal=goal,
                departure_time=departure_time,
                timeout_seconds=timeout_seconds - elapsed
            )
            
            if route is None:
                print(f"   No more routes found")
                break
            
            routes.append(route)
            
            # Block this route's edges for next search
            # (In practice, you'd temporarily remove edges from graph)
            # For now, we just return what we found
            
        return routes


# Helper function for easy use
def find_route(graph: TransportationGraph,
               start_name: str,
               goal_name: str,
               optimization_mode: str = "time",
               departure_time: Optional[datetime] = None) -> Optional[Route]:
    """
    Convenience function to find route by stop names
    
    Args:
        graph: Transportation network
        start_name: Name of starting stop (partial match ok)
        goal_name: Name of destination stop (partial match ok)
        optimization_mode: "time", "cost", "transfers", or "balanced"
        departure_time: When to depart
    
    Returns:
        Route object if found, None otherwise
    """
    # Find stops by name
    start_matches = [s for s in graph.stops.values() 
                     if start_name.lower() in s.name.lower()]
    goal_matches = [s for s in graph.stops.values() 
                   if goal_name.lower() in s.name.lower()]
    
    if not start_matches:
        print(f"❌ No stop found matching: {start_name}")
        return None
    
    if not goal_matches:
        print(f"❌ No stop found matching: {goal_name}")
        return None
    
    start = start_matches[0]
    goal = goal_matches[0]
    
    print(f"📍 From: {start.name} ({start.mode.value})")
    print(f"📍 To:   {goal.name} ({goal.mode.value})")
    
    # Create router and find route
    router = IDAStarRouter(graph, optimization_mode)
    route = router.search(start, goal, departure_time)
    
    return route

