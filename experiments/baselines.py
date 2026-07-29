"""
Standard DFS and Conventional Routing baselines, implemented exactly per the
paper's own Section 2.4 definitions, reusing the same graph, neighbor
options (direct edges + 0.6km transfer radius) and data structures as the
Enhanced DFS-IDA* implementation (ida_star_balanced.py) -- the only
difference is the search strategy itself.

Standard DFS: same movement options as Enhanced DFS, but NO heuristic h(n)
and NO iterative-deepening/threshold pruning -- plain backtracking DFS up to
max depth 15, exploring neighbors in a fixed (non-heuristic) order, capped by
a node budget so a dead network region can't hang the run. Returns the FIRST
complete path found (this *is* the "no optimization" baseline -- an
IDA*-guided search finds a good path deliberately, this one takes what it
stumbles on).

Conventional Routing: greedy nearest-neighbor by straight-line (haversine)
distance to the destination, no cost/time weighting, no backtracking, no
lookahead. Fails as soon as it reaches a stop with no unvisited neighbor that
gets closer to the goal.
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

from typing import List, Optional, Set, Tuple
from datetime import datetime, timedelta

from algorithms.ida_star_routing.data_structures import (
    Stop, Edge, Route, RouteSegment, TransportationGraph, TransportationMode,
)
from algorithms.ida_star_routing.dijkstra import haversine_distance_km
from algorithms.ida_star_routing.door_to_door import Location
from core.gmaps_style_routing import find_nearest_stops_extended, create_walking_segment

WALKING_SPEED_KMH = 5.0
MAX_TRANSFER_WALK_KM = 0.6  # same radius as Enhanced DFS (paper 2.4)
TRANSFER_TIME_PENALTY = 5.0
MODE_SWITCH_PENALTY = 10.0
STANDARD_DFS_MAX_DEPTH = 15  # paper 2.4
STANDARD_DFS_NODE_BUDGET = 200_000  # runtime safety cap, not in the paper


def _build_transfer_map(graph: TransportationGraph):
    """Same construction as BalancedIDAStarRouter._build_balanced_transfer_map:
    identical movement options, so the two searches are only compared on
    search strategy, not on what moves are available."""
    transfer_map = {}
    stops_list = list(graph.stops.values())
    for stop in stops_list:
        nearby = []
        for other in stops_list:
            if stop.stop_id == other.stop_id or stop.route == other.route:
                continue
            dist_km = haversine_distance_km(stop.lat, stop.lon, other.lat, other.lon)
            if dist_km <= MAX_TRANSFER_WALK_KM:
                nearby.append((other, dist_km))
        nearby.sort(key=lambda x: x[1])
        if nearby:
            transfer_map[stop.stop_id] = nearby[:8]
    return transfer_map


def _edge_cost(edge: Edge, current_mode, optimization_mode: str) -> float:
    if optimization_mode == "time":
        cost = edge.base_time_minutes
    elif optimization_mode == "cost":
        cost = float(edge.cost)
    else:
        cost = edge.base_time_minutes + edge.cost / 1000
    if edge.mode != current_mode and current_mode != TransportationMode.TRANSFER:
        cost += MODE_SWITCH_PENALTY
    return cost


def _get_neighbors(graph: TransportationGraph, transfer_map, current: Stop, visited: Set[str]):
    """Same move set as Enhanced DFS's _get_balanced_neighbors, MINUS the
    distance-to-goal filtering -- Standard DFS has no heuristic guidance at all."""
    neighbors = []
    for edge in graph.get_neighbors(current):
        if edge.to_stop.stop_id in visited:
            continue
        neighbors.append((edge.to_stop, edge, False))

    if current.stop_id in transfer_map:
        for nearby_stop, walk_dist in transfer_map[current.stop_id]:
            if nearby_stop.stop_id in visited or nearby_stop.route == current.route:
                continue
            walk_time = (walk_dist / WALKING_SPEED_KMH) * 60 + TRANSFER_TIME_PENALTY
            virtual_edge = Edge(
                from_stop=current, to_stop=nearby_stop, route="Transfer (Walking)",
                mode=TransportationMode.TRANSFER, distance_meters=walk_dist * 1000,
                base_time_minutes=walk_time, cost=0,
            )
            neighbors.append((nearby_stop, virtual_edge, True))
    return neighbors


class _NodeBudgetExceeded(Exception):
    pass


def _standard_dfs_recursive(graph, transfer_map, current, goal, visited, current_time,
                             current_mode, path, segments, depth, optimization_mode, budget):
    budget[0] -= 1
    if budget[0] <= 0:
        raise _NodeBudgetExceeded()

    if current.stop_id == goal.stop_id:
        route = Route(route_id=1, segments=list(segments))
        route.calculate_metrics()
        return route

    if depth >= STANDARD_DFS_MAX_DEPTH:
        return None

    for neighbor, edge, is_transfer in _get_neighbors(graph, transfer_map, current, visited):
        edge_cost = _edge_cost(edge, current_mode, optimization_mode)
        arrival_time = current_time + timedelta(minutes=edge.base_time_minutes)
        segment = RouteSegment(
            sequence=len(segments) + 1, mode=edge.mode, route_name=edge.route,
            from_stop=current, to_stop=neighbor, departure_time=current_time,
            arrival_time=arrival_time, duration_minutes=edge.base_time_minutes,
            cost=edge.cost, distance_km=edge.distance_meters / 1000,
        )
        visited.add(neighbor.stop_id)
        segments.append(segment)

        result = _standard_dfs_recursive(
            graph, transfer_map, neighbor, goal, visited, arrival_time,
            edge.mode, path, segments, depth + 1, optimization_mode, budget,
        )
        if result is not None:
            return result

        segments.pop()
        visited.remove(neighbor.stop_id)

    return None


def standard_dfs_route(graph: TransportationGraph, origin_name: str, origin_coords: Tuple[float, float],
                        dest_name: str, dest_coords: Tuple[float, float],
                        optimization_mode: str = "time", departure_time: Optional[datetime] = None,
                        max_walking_km: float = 2.0) -> Optional[Route]:
    if departure_time is None:
        departure_time = datetime.now()

    origin_stops = find_nearest_stops_extended(graph, origin_coords[0], origin_coords[1], max_walking_km)
    dest_stops = find_nearest_stops_extended(graph, dest_coords[0], dest_coords[1], max_walking_km)
    if not origin_stops or not dest_stops:
        return None

    transfer_map = _build_transfer_map(graph)
    budget = [STANDARD_DFS_NODE_BUDGET]

    best_route = None
    for origin_stop, origin_dist in origin_stops[:3]:
        for dest_stop, dest_dist in dest_stops[:3]:
            try:
                transit_route = _standard_dfs_recursive(
                    graph, transfer_map, origin_stop, dest_stop, {origin_stop.stop_id},
                    departure_time, origin_stop.mode, [origin_stop], [], 0, optimization_mode, budget,
                )
            except _NodeBudgetExceeded:
                transit_route = None

            if transit_route:
                best_route = (origin_stop, origin_dist, dest_stop, dest_dist, transit_route)
                break  # first complete path found -- no optimization, per paper 2.4
        if best_route:
            break

    if not best_route:
        return None

    origin_stop, origin_dist, dest_stop, dest_dist, transit_route = best_route
    segments = []
    current_time = departure_time

    origin_loc = Location(origin_name, origin_coords[0], origin_coords[1])
    origin_stop_loc = Location(origin_stop.name, origin_stop.lat, origin_stop.lon)
    walk1 = create_walking_segment(1, origin_loc, origin_stop_loc, current_time)
    segments.append(walk1)
    current_time = walk1.arrival_time

    for seg in transit_route.segments:
        seg.sequence = len(segments) + 1
        seg.departure_time = current_time
        seg.arrival_time = current_time + timedelta(minutes=seg.duration_minutes)
        segments.append(seg)
        current_time = seg.arrival_time

    dest_stop_loc = Location(dest_stop.name, dest_stop.lat, dest_stop.lon)
    dest_loc = Location(dest_name, dest_coords[0], dest_coords[1])
    walk2 = create_walking_segment(len(segments) + 1, dest_stop_loc, dest_loc, current_time)
    segments.append(walk2)

    complete_route = Route(route_id=1, segments=segments)
    complete_route.calculate_metrics()
    return complete_route


CONVENTIONAL_MAX_STEPS = 200


def conventional_route(graph: TransportationGraph, origin_name: str, origin_coords: Tuple[float, float],
                        dest_name: str, dest_coords: Tuple[float, float],
                        optimization_mode: str = "time", departure_time: Optional[datetime] = None,
                        max_walking_km: float = 2.0) -> Optional[Route]:
    if departure_time is None:
        departure_time = datetime.now()

    origin_stops = find_nearest_stops_extended(graph, origin_coords[0], origin_coords[1], max_walking_km)
    dest_stops = find_nearest_stops_extended(graph, dest_coords[0], dest_coords[1], max_walking_km)
    if not origin_stops or not dest_stops:
        return None

    transfer_map = _build_transfer_map(graph)
    origin_stop, origin_dist = origin_stops[0]
    goal_stop, dest_dist = dest_stops[0]

    visited = {origin_stop.stop_id}
    current = origin_stop
    current_mode = origin_stop.mode
    current_time = departure_time
    segments = []

    for _ in range(CONVENTIONAL_MAX_STEPS):
        if current.stop_id == goal_stop.stop_id:
            break

        neighbors = _get_neighbors(graph, transfer_map, current, visited)
        if not neighbors:
            return None  # dead end -- no backtracking allowed, per paper 2.4

        # pure greedy: nearest to goal by straight-line distance, no cost/time weighting
        best = min(neighbors, key=lambda item: haversine_distance_km(
            item[0].lat, item[0].lon, goal_stop.lat, goal_stop.lon))
        neighbor, edge, is_transfer = best

        arrival_time = current_time + timedelta(minutes=edge.base_time_minutes)
        segments.append(RouteSegment(
            sequence=len(segments) + 1, mode=edge.mode, route_name=edge.route,
            from_stop=current, to_stop=neighbor, departure_time=current_time,
            arrival_time=arrival_time, duration_minutes=edge.base_time_minutes,
            cost=edge.cost, distance_km=edge.distance_meters / 1000,
        ))
        visited.add(neighbor.stop_id)
        current = neighbor
        current_mode = edge.mode
        current_time = arrival_time
    else:
        return None  # step budget exceeded without reaching goal

    if current.stop_id != goal_stop.stop_id:
        return None

    final_segments = []
    t = departure_time
    origin_loc = Location(origin_name, origin_coords[0], origin_coords[1])
    origin_stop_loc = Location(origin_stop.name, origin_stop.lat, origin_stop.lon)
    walk1 = create_walking_segment(1, origin_loc, origin_stop_loc, t)
    final_segments.append(walk1)
    t = walk1.arrival_time

    for seg in segments:
        seg.sequence = len(final_segments) + 1
        seg.departure_time = t
        seg.arrival_time = t + timedelta(minutes=seg.duration_minutes)
        final_segments.append(seg)
        t = seg.arrival_time

    dest_stop_loc = Location(goal_stop.name, goal_stop.lat, goal_stop.lon)
    dest_loc = Location(dest_name, dest_coords[0], dest_coords[1])
    walk2 = create_walking_segment(len(final_segments) + 1, dest_stop_loc, dest_loc, t)
    final_segments.append(walk2)

    complete_route = Route(route_id=1, segments=final_segments)
    complete_route.calculate_metrics()
    return complete_route
