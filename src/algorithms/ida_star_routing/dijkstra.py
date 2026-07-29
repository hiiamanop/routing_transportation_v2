"""
Dijkstra's Algorithm Implementation for Multi-Modal Transportation
With automatic transfer point detection and walking connections
"""

import heapq
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .data_structures import (
    Stop,
    Edge,
    Route,
    RouteSegment,
    TransportationGraph,
    TransportationMode,
    DEFAULT_COSTS,
    DEFAULT_SPEEDS
)
from core import service_model


# Constants
WALKING_SPEED_KMH = 5.0
MAX_TRANSFER_WALK_KM = 0.5  # Maximum walking distance for transfers (500m)
TRANSFER_TIME_PENALTY = 5.0  # Extra 5 minutes for transfer overhead


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometers"""
    import math
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


@dataclass(order=True)
class DijkstraNode:
    """Node for Dijkstra's priority queue"""
    cost: float
    stop: Stop = field(compare=False)
    parent: Optional['DijkstraNode'] = field(default=None, compare=False)
    edge_used: Optional[Edge] = field(default=None, compare=False)
    time_accumulated: float = field(default=0.0, compare=False)
    is_walking: bool = field(default=False, compare=False)


class DijkstraRouter:
    """
    Dijkstra's algorithm with multi-modal support and automatic transfer detection
    """
    
    def __init__(self, graph: TransportationGraph, optimization_mode: str = "time"):
        """
        Initialize Dijkstra router
        
        Args:
            graph: Transportation network
            optimization_mode: "time", "cost", "transfers", or "balanced"
        """
        self.graph = graph
        self.optimization_mode = optimization_mode
        self.transfer_map = self._build_transfer_map()
        
        print(f"\n🔧 Dijkstra Router initialized")
        print(f"   Optimization: {optimization_mode}")
        print(f"   Transfer points detected: {len(self.transfer_map)}")
    
    def _build_transfer_map(self) -> Dict[str, List[Tuple[Stop, float]]]:
        """
        Build map of possible transfers between stops
        Finds stops within walking distance of each other
        
        Returns:
            Dict mapping stop_id to list of (nearby_stop, distance_km) tuples
        """
        print(f"\n🔍 Building transfer map...")
        print(f"   Max transfer walking distance: {MAX_TRANSFER_WALK_KM * 1000}m")
        
        transfer_map = {}
        stops_list = list(self.graph.stops.values())
        
        for i, stop in enumerate(stops_list):
            nearby_stops = []
            
            for other_stop in stops_list:
                if stop.stop_id == other_stop.stop_id:
                    continue
                
                # Calculate distance
                dist_km = haversine_distance_km(
                    stop.lat, stop.lon,
                    other_stop.lat, other_stop.lon
                )
                
                # If within walking distance, add as transfer option
                if dist_km <= MAX_TRANSFER_WALK_KM:
                    nearby_stops.append((other_stop, dist_km))
            
            if nearby_stops:
                transfer_map[stop.stop_id] = nearby_stops
        
        # Statistics
        stops_with_transfers = len(transfer_map)
        total_transfers = sum(len(v) for v in transfer_map.values())
        
        print(f"   ✅ Stops with transfer options: {stops_with_transfers}")
        print(f"   ✅ Total transfer connections: {total_transfers}")
        
        return transfer_map
    
    def _edge_travel_minutes(self, edge: Edge, when: Optional[datetime] = None) -> float:
        """Waktu tempuh nyata dari survei 30 hari, sama dengan yang dipakai IDA*."""
        if edge.mode in (TransportationMode.WALK, TransportationMode.TRANSFER):
            return edge.base_time_minutes
        return service_model.travel_minutes(
            edge.route, edge.from_stop.stop_id, edge.to_stop.stop_id,
            edge.distance_meters / 1000, when)

    def _boarding_wait_minutes(self, edge: Edge, current_route: Optional[str]) -> float:
        """Waktu tunggu kendaraan baru (nol kalau masih di rute yang sama)."""
        if edge.mode in (TransportationMode.WALK, TransportationMode.TRANSFER):
            return 0.0
        if edge.route == current_route:
            return 0.0
        return service_model.wait_minutes(edge.route)

    def _calculate_edge_cost(self, edge: Edge, current_mode: Optional[TransportationMode],
                             current_route: Optional[str] = None,
                             when: Optional[datetime] = None) -> float:
        """Biaya ruas: waktu tempuh nyata + waktu tunggu kendaraan."""
        wait = self._boarding_wait_minutes(edge, current_route)

        if self.optimization_mode == "cost":
            return float(edge.cost)

        travel = self._edge_travel_minutes(edge, when)
        if self.optimization_mode == "time":
            return travel + wait
        elif self.optimization_mode == "transfers":
            # Penalti tambahan untuk pindah moda, di atas waktu tunggu yang
            # sudah nyata menangkap "ongkos" transfer.
            transfer_penalty = 20.0 if (current_mode and edge.mode != current_mode) else 0.0
            return travel + wait + transfer_penalty
        else:  # balanced
            return travel + wait + edge.cost / 1000
    
    def _calculate_walking_cost(self, distance_km: float) -> float:
        """Calculate cost for walking segment"""
        walking_time = (distance_km / WALKING_SPEED_KMH) * 60  # minutes
        
        if self.optimization_mode == "time":
            return walking_time + TRANSFER_TIME_PENALTY
        elif self.optimization_mode == "cost":
            return 0.0  # Walking is free
        elif self.optimization_mode == "transfers":
            return walking_time + TRANSFER_TIME_PENALTY
        else:  # balanced
            return (walking_time + TRANSFER_TIME_PENALTY) / 60  # normalize to hours
    
    def search(self, start: Stop, goal: Stop, 
              departure_time: Optional[datetime] = None) -> Optional[Route]:
        """
        Find optimal route using Dijkstra's algorithm
        
        Args:
            start: Starting stop
            goal: Destination stop
            departure_time: When to start journey
        
        Returns:
            Route object if found, None otherwise
        """
        if departure_time is None:
            departure_time = datetime.now()
        
        print(f"\n🔍 Dijkstra Search")
        print(f"   From: {start.name} ({start.mode.value})")
        print(f"   To:   {goal.name} ({goal.mode.value})")
        print(f"   Mode: {self.optimization_mode}")
        
        # Priority queue: (cost, node)
        pq = []
        heapq.heappush(pq, DijkstraNode(cost=0.0, stop=start))
        
        # Best cost to reach each stop
        best_cost: Dict[str, float] = {start.stop_id: 0.0}
        
        # Best node to reach each stop (for path reconstruction)
        best_node: Dict[str, DijkstraNode] = {
            start.stop_id: DijkstraNode(cost=0.0, stop=start)
        }
        
        visited: Set[str] = set()
        nodes_explored = 0
        
        while pq:
            current_node = heapq.heappop(pq)
            current_stop = current_node.stop
            current_cost = current_node.cost
            
            # Skip if already visited
            if current_stop.stop_id in visited:
                continue
            
            visited.add(current_stop.stop_id)
            nodes_explored += 1
            
            # Goal reached!
            if current_stop.stop_id == goal.stop_id:
                print(f"\n✅ Route found!")
                print(f"   Nodes explored: {nodes_explored}")
                print(f"   Cost: {current_cost:.2f}")
                
                # Reconstruct path
                return self._reconstruct_path(current_node, departure_time)
            
            # Get current mode/route (from parent if available)
            current_mode = current_node.edge_used.mode if current_node.edge_used else current_stop.mode
            current_route = current_node.edge_used.route if current_node.edge_used else None
            when = departure_time + timedelta(minutes=current_node.time_accumulated)

            # Explore regular edges (same route)
            for edge in self.graph.get_neighbors(current_stop):
                neighbor = edge.to_stop

                if neighbor.stop_id in visited:
                    continue

                edge_cost = self._calculate_edge_cost(edge, current_mode, current_route, when)
                new_cost = current_cost + edge_cost

                # Update if better path found
                if neighbor.stop_id not in best_cost or new_cost < best_cost[neighbor.stop_id]:
                    best_cost[neighbor.stop_id] = new_cost

                    # Jam terus berjalan dgn waktu NYATA (tempuh+tunggu), bukan
                    # skor optimasi -- penting saat optimization_mode="cost",
                    # di mana edge_cost adalah Rupiah, bukan menit.
                    duration = (self._edge_travel_minutes(edge, when) +
                               self._boarding_wait_minutes(edge, current_route))
                    new_node = DijkstraNode(
                        cost=new_cost,
                        stop=neighbor,
                        parent=current_node,
                        edge_used=edge,
                        time_accumulated=current_node.time_accumulated + duration,
                        is_walking=False
                    )
                    
                    best_node[neighbor.stop_id] = new_node
                    heapq.heappush(pq, new_node)
            
            # Explore transfer options (walking to nearby stops)
            if current_stop.stop_id in self.transfer_map:
                for nearby_stop, walk_dist_km in self.transfer_map[current_stop.stop_id]:
                    if nearby_stop.stop_id in visited:
                        continue
                    
                    # Skip if same route (already handled by regular edges)
                    if nearby_stop.route == current_stop.route:
                        continue
                    
                    walking_cost = self._calculate_walking_cost(walk_dist_km)
                    new_cost = current_cost + walking_cost
                    
                    # Update if better path found
                    if nearby_stop.stop_id not in best_cost or new_cost < best_cost[nearby_stop.stop_id]:
                        best_cost[nearby_stop.stop_id] = new_cost
                        
                        # Create virtual walking edge
                        virtual_edge = Edge(
                            from_stop=current_stop,
                            to_stop=nearby_stop,
                            route="Transfer (Walking)",
                            mode=TransportationMode.TRANSFER,
                            distance_meters=walk_dist_km * 1000,
                            base_time_minutes=(walk_dist_km / WALKING_SPEED_KMH) * 60 + TRANSFER_TIME_PENALTY,
                            cost=0
                        )
                        
                        new_node = DijkstraNode(
                            cost=new_cost,
                            stop=nearby_stop,
                            parent=current_node,
                            edge_used=virtual_edge,
                            time_accumulated=current_node.time_accumulated + virtual_edge.base_time_minutes,
                            is_walking=True
                        )
                        
                        best_node[nearby_stop.stop_id] = new_node
                        heapq.heappush(pq, new_node)
        
        print(f"\n❌ No route found")
        print(f"   Nodes explored: {nodes_explored}")
        return None
    
    def _reconstruct_path(self, goal_node: DijkstraNode, departure_time: datetime) -> Route:
        """Reconstruct route from goal node back to start"""
        
        # Trace back from goal to start
        path = []
        current = goal_node
        
        while current.parent is not None:
            path.append((current.edge_used, current.is_walking))
            current = current.parent
        
        # Reverse to get start -> goal
        path.reverse()
        
        # Build route segments -- pakai waktu tempuh + tunggu yang SAMA dgn
        # yang dipakai search (bukan base_time_minutes statis), supaya waktu
        # yang ditampilkan = waktu yang dioptimasi.
        segments = []
        current_time = departure_time
        current_route = None

        for seq, (edge, is_walking) in enumerate(path, 1):
            wait = self._boarding_wait_minutes(edge, current_route)
            travel = self._edge_travel_minutes(edge, current_time)
            duration = travel + wait
            arrival_time = current_time + timedelta(minutes=duration)

            segment = RouteSegment(
                sequence=seq,
                mode=edge.mode,
                route_name=edge.route,
                from_stop=edge.from_stop,
                to_stop=edge.to_stop,
                departure_time=current_time,
                arrival_time=arrival_time,
                duration_minutes=duration,
                cost=edge.cost,
                distance_km=edge.distance_meters / 1000,
                wait_minutes=wait
            )

            segments.append(segment)
            current_time = arrival_time
            current_route = edge.route
        
        # Create route
        route = Route(route_id=1, segments=segments)
        route.calculate_metrics()
        route.optimization_score = goal_node.cost
        
        return route


# Convenience function
def find_route_dijkstra(graph: TransportationGraph,
                       start_name: str,
                       goal_name: str,
                       optimization_mode: str = "time",
                       departure_time: Optional[datetime] = None) -> Optional[Route]:
    """
    Find route using Dijkstra's algorithm
    
    Args:
        graph: Transportation network
        start_name: Name of starting stop (partial match ok)
        goal_name: Name of destination stop (partial match ok)
        optimization_mode: Optimization criteria
        departure_time: When to depart
    
    Returns:
        Route if found, None otherwise
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
    router = DijkstraRouter(graph, optimization_mode)
    route = router.search(start, goal, departure_time)
    
    return route

