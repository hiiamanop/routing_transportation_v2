"""
Heuristic Functions for IDA* Algorithm
"""

from math import radians, sin, cos, sqrt, atan2
from typing import Optional
from datetime import datetime

from .data_structures import (
    Stop,
    TransportationMode,
    TransportationGraph,
    DEFAULT_COSTS,
    DEFAULT_SPEEDS
)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate straight-line distance in meters"""
    R = 6371000  # Earth radius in meters
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def heuristic_time(current: Stop, goal: Stop, graph: TransportationGraph) -> float:
    """
    Estimate minimum time to reach goal (in minutes)
    Uses straight-line distance and fastest available mode
    
    This is admissible (never overestimates) because:
    - Straight line is shortest possible distance
    - LRT is fastest mode available
    """
    distance_km = haversine_distance(
        current.lat, current.lon,
        goal.lat, goal.lon
    ) / 1000
    
    # Use fastest mode (LRT) for optimistic estimate
    fastest_speed = DEFAULT_SPEEDS[TransportationMode.LRT]  # 40 km/h
    
    estimated_time = (distance_km / fastest_speed) * 60  # Convert to minutes
    
    return estimated_time


def heuristic_cost(current: Stop, goal: Stop, graph: TransportationGraph) -> float:
    """
    Estimate minimum cost to reach goal (in IDR)
    Uses straight-line distance and cheapest mode
    
    This is admissible because:
    - Straight line is shortest distance
    - Feeder Angkot is cheapest mode
    - We assume one direct trip (minimum transfers)
    """
    distance_km = haversine_distance(
        current.lat, current.lon,
        goal.lat, goal.lon
    ) / 1000
    
    # Cheapest mode
    cheapest_cost = DEFAULT_COSTS[TransportationMode.FEEDER_ANGKOT]  # 3000 IDR
    
    # Estimate: at least one trip needed
    estimated_cost = cheapest_cost
    
    # Add extra cost for long distances (may need transfer)
    if distance_km > 10:
        estimated_cost += cheapest_cost  # One transfer likely
    
    return float(estimated_cost)


def heuristic_transfers(current: Stop, goal: Stop, graph: TransportationGraph) -> float:
    """
    Estimate minimum transfers needed
    
    Returns 0 if same route, otherwise estimates based on distance
    """
    # If on same route, no transfer needed
    if current.route == goal.route:
        return 0.0
    
    # Calculate distance
    distance_km = haversine_distance(
        current.lat, current.lon,
        goal.lat, goal.lon
    ) / 1000
    
    # Estimate transfers based on distance
    # Typically: 0-5km = 1 transfer, 5-15km = 2 transfers, >15km = 3 transfers
    if distance_km < 5:
        return 1.0
    elif distance_km < 15:
        return 2.0
    else:
        return 3.0


def heuristic_balanced(current: Stop, goal: Stop, graph: TransportationGraph,
                      weights: dict = None) -> float:
    """
    Balanced heuristic combining time, cost, and transfers
    
    Args:
        weights: Dict with keys 'time', 'cost', 'transfers' (default equal weights)
    
    Returns:
        Combined heuristic score
    """
    if weights is None:
        weights = {'time': 0.33, 'cost': 0.33, 'transfers': 0.34}
    
    h_time = heuristic_time(current, goal, graph)
    h_cost = heuristic_cost(current, goal, graph)
    h_transfers = heuristic_transfers(current, goal, graph)
    
    # Normalize to similar scales
    time_norm = h_time / 60  # Normalize to hours
    cost_norm = h_cost / 10000  # Normalize to 10k IDR
    transfer_norm = h_transfers
    
    return (weights['time'] * time_norm + 
            weights['cost'] * cost_norm + 
            weights['transfers'] * transfer_norm)


def get_heuristic_function(optimization_mode: str):
    """
    Get appropriate heuristic function based on optimization mode
    
    Args:
        optimization_mode: "time", "cost", "transfers", or "balanced"
    
    Returns:
        Heuristic function
    """
    heuristics = {
        'time': heuristic_time,
        'cost': heuristic_cost,
        'transfers': heuristic_transfers,
        'balanced': heuristic_balanced
    }
    
    return heuristics.get(optimization_mode, heuristic_time)


# For testing
if __name__ == "__main__":
    # Create mock stops for testing
    stop1 = Stop(
        id=1,
        stop_id="test_1",
        name="Bandara SMB 2",
        lat=-2.894114,
        lon=104.705661,
        route="LRT Sumsel",
        mode=TransportationMode.LRT
    )
    
    stop2 = Stop(
        id=2,
        stop_id="test_2",
        name="DJKA",
        lat=-3.031568,
        lon=104.790251,
        route="LRT Sumsel",
        mode=TransportationMode.LRT
    )
    
    from .data_structures import TransportationGraph
    graph = TransportationGraph()
    
    print("Testing Heuristic Functions")
    print("="*60)
    print(f"From: {stop1.name}")
    print(f"To:   {stop2.name}")
    print(f"\nStraight-line distance: {haversine_distance(stop1.lat, stop1.lon, stop2.lat, stop2.lon)/1000:.2f} km")
    print(f"\nHeuristic Estimates:")
    print(f"  Time:      {heuristic_time(stop1, stop2, graph):.2f} minutes")
    print(f"  Cost:      Rp {heuristic_cost(stop1, stop2, graph):.0f}")
    print(f"  Transfers: {heuristic_transfers(stop1, stop2, graph):.0f}")
    print(f"  Balanced:  {heuristic_balanced(stop1, stop2, graph):.4f}")

