"""
BALANCED IDA* (Iterative Deepening A*) with Multi-Modal Support
Tuned to match Dijkstra performance with balanced approach

Key Optimizations:
1. REALISTIC bound initialization (start with reasonable bound)
2. BALANCED bound increment (moderate growth)
3. EFFICIENT heuristic (accurate distance + mode penalties)
4. SMART pruning (visited states, reasonable filtering)
5. BALANCED termination (good solutions without being too strict)
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
from core import service_model


# BALANCED Constants
WALKING_SPEED_KMH = 5.0
MAX_TRANSFER_WALK_KM = 0.6  # Reasonable transfer distance
TRANSFER_TIME_PENALTY = 5.0  # Reasonable penalty
# MODE_SWITCH_PENALTY dihapus: dulu 10 menit tebakan untuk "ongkos repot pindah
# moda". Sekarang digantikan waktu tunggu nyata dari service_model.wait_minutes(),
# yang juga menangkap kasus yang dulu terlewat -- pindah antar KORIDOR pada moda
# yang sama (mis. Feeder K1 -> Feeder K4) dulu dianggap gratis, padahal
# penumpang tetap harus menunggu kendaraan yang berbeda.


class BalancedIDAStarRouter:
    """
    BALANCED IDA* Router designed to match Dijkstra performance with reasonable approach
    """
    
    def __init__(self, graph: TransportationGraph, optimization_mode: str = "time"):
        self.graph = graph
        self.optimization_mode = optimization_mode
        
        # Build BALANCED transfer map
        self.transfer_map = self._build_balanced_transfer_map()
        
        # Statistics
        self.nodes_explored = 0
        self.max_depth_reached = 0
        self.iterations = 0
        
        print(f"\n🎯 BALANCED IDA* Router initialized")
        print(f"   Optimization: {optimization_mode}")
        print(f"   Transfer points: {len(self.transfer_map)}")
    
    def _build_balanced_transfer_map(self) -> Dict[str, List[Tuple[Stop, float]]]:
        """Build BALANCED transfer map with reasonable filtering"""
        transfer_map = {}
        stops_list = list(self.graph.stops.values())
        
        for stop in stops_list:
            nearby_stops = []
            
            for other_stop in stops_list:
                if stop.stop_id == other_stop.stop_id or stop.route == other_stop.route:
                    continue
                
                dist_km = haversine_distance_km(stop.lat, stop.lon, other_stop.lat, other_stop.lon)
                
                if dist_km <= MAX_TRANSFER_WALK_KM:
                    nearby_stops.append((other_stop, dist_km))
            
            # Sort by distance and keep reasonable number (top 8)
            nearby_stops.sort(key=lambda x: x[1])
            if nearby_stops:
                transfer_map[stop.stop_id] = nearby_stops[:8]
        
        return transfer_map
    
    def _balanced_heuristic(self, current: Stop, goal: Stop) -> float:
        """
        BALANCED heuristic that reasonably approximates actual cost
        """
        # Direct distance
        dist_km = haversine_distance_km(current.lat, current.lon, goal.lat, goal.lon)
        
        if self.optimization_mode == "time":
            # Estimate time: reasonable transport speed assumptions
            if dist_km < 1.0:
                # Very short distance: mostly walking
                return (dist_km / WALKING_SPEED_KMH) * 60 + 5  # 5 min overhead
            elif dist_km < 5.0:
                # Short distance: walking + one transport
                return (dist_km / 20.0) * 60 + 10  # 20 km/h average + 10 min overhead
            elif dist_km < 15.0:
                # Medium distance: walking + transport + possible transfer
                return (dist_km / 25.0) * 60 + 15  # 25 km/h average + 15 min overhead
            else:
                # Long distance: multiple transports
                return (dist_km / 30.0) * 60 + 20  # 30 km/h average + 20 min overhead
        
        elif self.optimization_mode == "cost":
            # Estimate cost based on distance and transfers
            if dist_km < 3.0:
                return 5000  # One fare
            elif dist_km < 10.0:
                return 8000  # One transfer
            else:
                return 12000  # Multiple transfers
        
        else:  # balanced
            time_est = self._balanced_heuristic(current, goal) if self.optimization_mode != "time" else (dist_km / 25.0) * 60 + 15
            cost_est = 8000 if dist_km > 3.0 else 5000
            return time_est + cost_est / 1000
    
    def search(self, 
               start: Stop, 
               goal: Stop,
               departure_time: Optional[datetime] = None,
               max_iterations: int = 100,  # Reasonable iteration limit
               timeout_seconds: float = 120.0) -> Optional[Route]:  # Reasonable timeout
        """
        BALANCED IDA* search with reasonable bounds and pruning
        """
        if departure_time is None:
            departure_time = datetime.now()
        
        print(f"\n🎯 BALANCED IDA* Search")
        print(f"   From: {start.name} ({start.mode.value})")
        print(f"   To:   {goal.name} ({goal.mode.value})")
        
        # Reset stats
        self.nodes_explored = 0
        self.max_depth_reached = 0
        self.iterations = 0
        
        start_time = time_module.time()
        self.search_start_time = start_time  # Store for recursive timeout checking
        self.timeout_seconds = timeout_seconds  # Store timeout
        
        # BALANCED initial bound (reasonable starting point)
        heuristic_bound = self._balanced_heuristic(start, goal)
        bound = heuristic_bound * 1.2  # Start with 1.2x heuristic (reasonable)
        
        print(f"📊 Heuristic: {heuristic_bound:.2f}, Initial bound: {bound:.2f}")
        
        # BALANCED bound sequence
        bound_multipliers = [1.2, 1.5, 2.0, 2.5, 3.5, 5.0, 7.0]  # one extra headroom step for multi-transfer routes
        
        for multiplier in bound_multipliers:
            if self.iterations >= max_iterations:
                break
                
            self.iterations += 1
            current_bound = heuristic_bound * multiplier
            
            # Check timeout BEFORE starting iteration
            elapsed = time_module.time() - start_time
            if elapsed > timeout_seconds:
                print(f"⏱️  Timeout reached ({elapsed:.2f}s)")
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
            
            # Check timeout after iteration
            elapsed = time_module.time() - start_time
            if elapsed > timeout_seconds:
                print(f"⏱️  Timeout reached after iteration ({elapsed:.2f}s)")
                break
            
            # No solution yet: continue to next bound (don't break!)
            print(f"   No solution with bound {current_bound:.2f}, trying higher bound...")
        
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
                         depth: int,
                         current_route: Optional[str] = None) -> any:
        """
        BALANCED recursive search with reasonable pruning and timeout checking
        """
        # Check timeout at the start of recursive call
        if hasattr(self, 'search_start_time') and hasattr(self, 'timeout_seconds'):
            elapsed = time_module.time() - self.search_start_time
            if elapsed > self.timeout_seconds:
                return float('inf')  # Timeout - return infinity to stop search
        
        self.nodes_explored += 1
        
        if depth > self.max_depth_reached:
            self.max_depth_reached = depth
        
        # Depth limit - loose enough to not cut off valid multi-hop transit routes
        # (the paper's own case study reaches depth 21; 20 was clipping real routes)
        if depth > 35:
            return float('inf')
        
        # Calculate f-cost with BALANCED heuristic
        h_cost = self._balanced_heuristic(current, goal)
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
        
        # Get neighbors with BALANCED filtering
        neighbors = self._get_balanced_neighbors(current, visited, goal)
        
        # Sort neighbors by estimated total cost (g + h) to prioritize direct paths
        def sort_key(item):
            neighbor_stop, edge, is_transfer = item
            estimated_cost_to_neighbor = self._calculate_balanced_edge_cost(
                edge, current_mode, current_route, current_time)
            heuristic_from_neighbor = self._balanced_heuristic(neighbor_stop, goal)

            # Penalti transfer untuk URUTAN eksplorasi saja (bukan skor akhir):
            # dorong jalur langsung dicoba lebih dulu. Biaya transfer yang
            # sebenarnya sekarang sudah masuk lewat waktu tunggu di edge cost.
            transfer_penalty = 50.0 if is_transfer else 0.0

            return estimated_cost_to_neighbor + heuristic_from_neighbor + transfer_penalty
        
        neighbors.sort(key=sort_key)  # Best total cost first, penalize transfers lightly
        
        # Explore reasonable number of neighbors
        max_neighbors = min(12, len(neighbors))  # Explore top 12 neighbors
        
        for neighbor, edge, is_transfer in neighbors[:max_neighbors]:
            # Skip if visited
            if neighbor.stop_id in visited:
                continue
            
            # Biaya = waktu tempuh nyata + waktu tunggu kendaraan
            edge_cost = self._calculate_balanced_edge_cost(
                edge, current_mode, current_route, current_time)
            new_g_cost = g_cost + edge_cost
            new_h_cost = self._balanced_heuristic(neighbor, goal)
            new_f_cost = new_g_cost + new_h_cost

            # Standard IDA* pruning: skip if f-cost exceeds bound
            if new_f_cost > bound:
                continue

            # Segmen memakai angka yang SAMA dengan yang dipakai mencari, supaya
            # waktu yang ditampilkan = waktu yang dioptimasi (dulu tidak sama).
            wait = self._boarding_wait_minutes(edge, current_route)
            travel = self._edge_travel_minutes(edge, current_time)
            duration = travel + wait
            arrival_time = current_time + timedelta(minutes=duration)

            segment = RouteSegment(
                sequence=len(segments) + 1,
                mode=edge.mode,
                route_name=edge.route,
                from_stop=current,
                to_stop=neighbor,
                departure_time=current_time,
                arrival_time=arrival_time,
                duration_minutes=duration,
                cost=edge.cost,
                distance_km=edge.distance_meters / 1000,
                wait_minutes=wait
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
                depth=depth + 1,
                current_route=edge.route
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
    
    def _get_balanced_neighbors(self, current: Stop, visited: Set[str], goal: Stop) -> List[Tuple[Stop, Edge, bool]]:
        """Get neighbors with BALANCED filtering"""
        neighbors = []
        goal_dist = haversine_distance_km(current.lat, current.lon, goal.lat, goal.lon)
        
        # 1. Regular edges (same route) - prioritize direct paths
        for edge in self.graph.get_neighbors(current):
            if edge.to_stop.stop_id in visited:
                continue
            
            # Check if this edge gets us closer to goal
            to_goal_dist = haversine_distance_km(edge.to_stop.lat, edge.to_stop.lon, goal.lat, goal.lon)
            
            # Allow generous detour: transit corridors curve, so straight-line distance
            # to goal is a poor proxy for "wrong direction" and was pruning valid paths
            if to_goal_dist <= goal_dist * 2.0 or goal_dist < 1.0:
                neighbors.append((edge.to_stop, edge, False))
        
        # 2. Transfer edges - BALANCED selection
        if current.stop_id in self.transfer_map:
            for nearby_stop, walk_dist in self.transfer_map[current.stop_id][:5]:  # Top 5 transfers
                if nearby_stop.stop_id in visited or nearby_stop.route == current.route:
                    continue
                
                # Consider transfers that reasonably move towards goal
                to_goal_dist = haversine_distance_km(nearby_stop.lat, nearby_stop.lon, goal.lat, goal.lon)

                if to_goal_dist < goal_dist * 1.3 or goal_dist < 1.0:  # was 1.1x, too strict for curved corridors
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
    
    def _edge_travel_minutes(self, edge: Edge, when: Optional[datetime] = None) -> float:
        """
        Waktu tempuh nyata ruas ini, dari survei 30 hari kalau tersedia.
        Menggantikan edge.base_time_minutes yang cuma jarak/kecepatan-tetap.
        """
        if edge.mode in (TransportationMode.WALK, TransportationMode.TRANSFER):
            return edge.base_time_minutes
        return service_model.travel_minutes(
            edge.route,
            edge.from_stop.stop_id,
            edge.to_stop.stop_id,
            edge.distance_meters / 1000,
            when,
        )

    def _boarding_wait_minutes(self, edge: Edge, current_route: Optional[str]) -> float:
        """
        Waktu tunggu kendaraan. Dikenakan saat naik kendaraan BARU -- termasuk
        naik pertama kali (current_route None) dan pindah koridor pada moda sama.
        """
        if edge.mode in (TransportationMode.WALK, TransportationMode.TRANSFER):
            return 0.0
        if edge.route == current_route:
            return 0.0  # masih di kendaraan yang sama, tidak menunggu lagi
        return service_model.wait_minutes(edge.route)

    def _calculate_balanced_edge_cost(self, edge: Edge,
                                      current_mode: TransportationMode,
                                      current_route: Optional[str] = None,
                                      when: Optional[datetime] = None) -> float:
        """Biaya ruas: waktu tempuh nyata + waktu tunggu kendaraan."""
        wait = self._boarding_wait_minutes(edge, current_route)

        if self.optimization_mode == "cost":
            return float(edge.cost)

        travel = self._edge_travel_minutes(edge, when)
        if self.optimization_mode == "time":
            return travel + wait
        # balanced: waktu (termasuk tunggu) + ongkos yang diskalakan
        return travel + wait + edge.cost / 1000


# Integration function (same interface as original)
def gmaps_style_route_balanced_ida_star(
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
    BALANCED Google Maps style routing using IDA*
    Designed to match Dijkstra performance with reasonable approach
    """
    if departure_time is None:
        departure_time = datetime.now()
    
    from .door_to_door import Location
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from core.gmaps_style_routing import find_nearest_stops_extended, create_walking_segment
    
    print(f"\n{'='*90}")
    print(f"{'🎯 BALANCED IDA* ROUTING':^90}")
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
    
    # BALANCED route finding
    print(f"\n{'─'*90}")
    print(f"STEP 2: BALANCED IDA* search")
    print(f"{'─'*90}")
    
    router = BalancedIDAStarRouter(graph, optimization_mode)
    
    best_route = None
    best_score = float('inf')
    
    # SMART combination evaluation: Start with BEST 2x2, expand if needed
    combinations_tried = 0
    
    for origin_stop, origin_dist in origin_stops[:3]:  # Top 3 origin stops
        for dest_stop, dest_dist in dest_stops[:3]:  # Top 3 dest stops
            combinations_tried += 1
            print(f"   🎯 Trying: {origin_stop.name} → {dest_stop.name}")
            
            # FAST search with tight limits
            transit_route = router.search(
                origin_stop, 
                dest_stop, 
                departure_time, 
                max_iterations=30,  # Very aggressive limit
                timeout_seconds=15.0  # Aggressive timeout (15 seconds)
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
                    
                    # Don't early stop: need to evaluate all to find the best
            else:
                print(f"   ❌ No route found")
        
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
