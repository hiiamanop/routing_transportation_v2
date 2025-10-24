"""
Door-to-Door Routing System (Google Maps Style)
Handles routing from any point to any point, including walking segments
"""

from typing import Optional, Tuple, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import math

from .data_structures import (
    Stop,
    Route,
    RouteSegment,
    TransportationMode,
    TransportationGraph
)
from .ida_star import IDAStarRouter


# Constants
WALKING_SPEED_KMH = 5.0  # Average walking speed
MAX_WALKING_DISTANCE_KM = 2.0  # Maximum reasonable walking distance
EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates in kilometers using Haversine formula
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
    
    Returns:
        Distance in kilometers
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distance_km = EARTH_RADIUS_KM * c
    return distance_km


@dataclass
class Location:
    """Represents any location (not necessarily a stop)"""
    name: str
    lat: float
    lon: float
    address: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'lat': self.lat,
            'lon': self.lon,
            'address': self.address
        }


class DoorToDoorRouter:
    """
    Door-to-door routing system that handles:
    - Walking to nearest stop
    - Public transport routing
    - Walking from last stop to destination
    """
    
    def __init__(self, graph: TransportationGraph, optimization_mode: str = "time"):
        """
        Initialize door-to-door router
        
        Args:
            graph: Transportation network
            optimization_mode: Optimization criteria (time, cost, transfers, balanced)
        """
        self.graph = graph
        self.optimization_mode = optimization_mode
        self.ida_router = IDAStarRouter(graph, optimization_mode)
        
    def find_nearest_stops(self, lat: float, lon: float, max_distance_km: float = None,
                          top_k: int = 5) -> List[Tuple[Stop, float]]:
        """
        Find nearest stops to a given coordinate
        
        Args:
            lat, lon: Coordinates
            max_distance_km: Maximum distance to consider
            top_k: Number of nearest stops to return
        
        Returns:
            List of (Stop, distance_km) tuples, sorted by distance
        """
        if max_distance_km is None:
            max_distance_km = MAX_WALKING_DISTANCE_KM
        
        distances = []
        
        for stop in self.graph.stops.values():
            distance_km = haversine_distance(lat, lon, stop.lat, stop.lon)
            
            if distance_km <= max_distance_km:
                distances.append((stop, distance_km))
        
        # Sort by distance
        distances.sort(key=lambda x: x[1])
        
        return distances[:top_k]
    
    def create_walking_segment(self, 
                              sequence: int,
                              from_loc: Location,
                              to_loc: Location,
                              departure_time: datetime) -> RouteSegment:
        """
        Create a walking segment between two locations
        
        Args:
            sequence: Segment number
            from_loc: Starting location
            to_loc: Ending location
            departure_time: When to start walking
        
        Returns:
            RouteSegment for walking
        """
        # Calculate distance
        distance_km = haversine_distance(
            from_loc.lat, from_loc.lon,
            to_loc.lat, to_loc.lon
        )
        
        # Calculate walking time
        duration_minutes = (distance_km / WALKING_SPEED_KMH) * 60
        
        # Create dummy stops for walking
        from_stop = Stop(
            id=-1,
            stop_id=f"walk_origin_{sequence}",
            name=from_loc.name,
            lat=from_loc.lat,
            lon=from_loc.lon,
            route="Walking",
            mode=TransportationMode.WALK
        )
        
        to_stop = Stop(
            id=-2,
            stop_id=f"walk_dest_{sequence}",
            name=to_loc.name,
            lat=to_loc.lat,
            lon=to_loc.lon,
            route="Walking",
            mode=TransportationMode.WALK
        )
        
        arrival_time = departure_time + timedelta(minutes=duration_minutes)
        
        segment = RouteSegment(
            sequence=sequence,
            mode=TransportationMode.WALK,
            route_name="Walking",
            from_stop=from_stop,
            to_stop=to_stop,
            departure_time=departure_time,
            arrival_time=arrival_time,
            duration_minutes=duration_minutes,
            cost=0,  # Walking is free
            distance_km=distance_km
        )
        
        return segment
    
    def route(self,
             origin: Location,
             destination: Location,
             departure_time: Optional[datetime] = None,
             max_walking_km: float = MAX_WALKING_DISTANCE_KM) -> Optional[Route]:
        """
        Find complete door-to-door route
        
        Args:
            origin: Starting location (any coordinates)
            destination: Ending location (any coordinates)
            departure_time: When to start journey
            max_walking_km: Maximum walking distance to consider
        
        Returns:
            Complete Route with walking + public transport segments
        """
        if departure_time is None:
            departure_time = datetime.now()
        
        print(f"\n🗺️  DOOR-TO-DOOR ROUTING (Google Maps Style)")
        print(f"="*70)
        print(f"📍 Origin:      {origin.name}")
        print(f"   Coordinates: ({origin.lat:.5f}, {origin.lon:.5f})")
        if origin.address:
            print(f"   Address:     {origin.address}")
        
        print(f"\n📍 Destination: {destination.name}")
        print(f"   Coordinates: ({destination.lat:.5f}, {destination.lon:.5f})")
        if destination.address:
            print(f"   Address:     {destination.address}")
        
        print(f"\n⏰ Departure:   {departure_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"🎯 Optimize by: {self.optimization_mode.upper()}")
        print(f"="*70)
        
        # Step 1: Find nearest stops to origin
        print(f"\n🔍 Finding nearest stops to origin...")
        origin_stops = self.find_nearest_stops(origin.lat, origin.lon, max_walking_km)
        
        if not origin_stops:
            print(f"❌ No stops within {max_walking_km} km of origin")
            return None
        
        print(f"   Found {len(origin_stops)} stops within {max_walking_km} km:")
        for i, (stop, dist) in enumerate(origin_stops[:3], 1):
            print(f"   {i}. {stop.name} - {dist:.2f} km away ({stop.mode.value})")
        
        # Step 2: Find nearest stops to destination
        print(f"\n🔍 Finding nearest stops to destination...")
        dest_stops = self.find_nearest_stops(destination.lat, destination.lon, max_walking_km)
        
        if not dest_stops:
            print(f"❌ No stops within {max_walking_km} km of destination")
            return None
        
        print(f"   Found {len(dest_stops)} stops within {max_walking_km} km:")
        for i, (stop, dist) in enumerate(dest_stops[:3], 1):
            print(f"   {i}. {stop.name} - {dist:.2f} km away ({stop.mode.value})")
        
        # Step 3: Try to find best route combination
        print(f"\n🚌 Finding optimal public transport route...")
        
        best_route = None
        best_score = float('inf')
        
        # Try different combinations of origin/destination stops
        for origin_stop, origin_walk_dist in origin_stops[:3]:  # Try top 3 origin stops
            for dest_stop, dest_walk_dist in dest_stops[:3]:  # Try top 3 dest stops
                
                # Calculate walking time at origin
                origin_walk_time = (origin_walk_dist / WALKING_SPEED_KMH) * 60
                transit_start_time = departure_time + timedelta(minutes=origin_walk_time)
                
                # Find public transport route
                transit_route = self.ida_router.search(
                    origin_stop,
                    dest_stop,
                    departure_time=transit_start_time
                )
                
                if transit_route is None:
                    continue
                
                # Calculate total score including walking
                dest_walk_time = (dest_walk_dist / WALKING_SPEED_KMH) * 60
                total_time = origin_walk_time + transit_route.total_time_minutes + dest_walk_time
                total_distance = origin_walk_dist + transit_route.total_distance_km + dest_walk_dist
                
                # Score based on optimization mode
                if self.optimization_mode == "time":
                    score = total_time
                elif self.optimization_mode == "cost":
                    score = transit_route.total_cost  # Walking is free
                else:
                    score = total_time + transit_route.total_cost / 1000
                
                if score < best_score:
                    best_score = score
                    best_route = {
                        'origin_stop': origin_stop,
                        'origin_walk_dist': origin_walk_dist,
                        'dest_stop': dest_stop,
                        'dest_walk_dist': dest_walk_dist,
                        'transit_route': transit_route,
                        'total_time': total_time,
                        'total_distance': total_distance
                    }
        
        if best_route is None:
            print(f"❌ No viable route found")
            return None
        
        # Step 4: Construct complete door-to-door route
        print(f"\n✅ Route found! Constructing complete journey...")
        
        segments = []
        current_time = departure_time
        segment_num = 1
        
        # Segment 1: Walk to origin stop
        origin_loc = Location(origin.name, origin.lat, origin.lon, origin.address)
        origin_stop_loc = Location(
            best_route['origin_stop'].name,
            best_route['origin_stop'].lat,
            best_route['origin_stop'].lon
        )
        
        walk_to_stop = self.create_walking_segment(
            segment_num,
            origin_loc,
            origin_stop_loc,
            current_time
        )
        segments.append(walk_to_stop)
        current_time = walk_to_stop.arrival_time
        segment_num += 1
        
        # Segments 2-N: Public transport
        for transit_seg in best_route['transit_route'].segments:
            transit_seg.sequence = segment_num
            transit_seg.departure_time = current_time
            transit_seg.arrival_time = current_time + timedelta(minutes=transit_seg.duration_minutes)
            segments.append(transit_seg)
            current_time = transit_seg.arrival_time
            segment_num += 1
        
        # Last segment: Walk from last stop to destination
        dest_stop_loc = Location(
            best_route['dest_stop'].name,
            best_route['dest_stop'].lat,
            best_route['dest_stop'].lon
        )
        dest_loc = Location(destination.name, destination.lat, destination.lon, destination.address)
        
        walk_from_stop = self.create_walking_segment(
            segment_num,
            dest_stop_loc,
            dest_loc,
            current_time
        )
        segments.append(walk_from_stop)
        
        # Create complete route
        complete_route = Route(route_id=1, segments=segments)
        complete_route.calculate_metrics()
        complete_route.optimization_score = best_score
        
        # Add metadata
        complete_route.origin_location = origin
        complete_route.destination_location = destination
        complete_route.origin_stop = best_route['origin_stop']
        complete_route.dest_stop = best_route['dest_stop']
        complete_route.origin_walk_distance = best_route['origin_walk_dist']
        complete_route.dest_walk_distance = best_route['dest_walk_dist']
        
        return complete_route


def print_door_to_door_route(route: Route):
    """Print door-to-door route in Google Maps style"""
    
    print(f"\n" + "="*80)
    print(f"🗺️  COMPLETE DOOR-TO-DOOR ROUTE (GOOGLE MAPS STYLE)")
    print(f"="*80)
    
    # Summary
    print(f"\n📊 JOURNEY SUMMARY:")
    print(f"   Total Time:     {route.total_time_minutes:.0f} minutes ({route.total_time_minutes/60:.1f} hours)")
    print(f"   Total Cost:     Rp {route.total_cost:,}")
    print(f"   Total Distance: {route.total_distance_km:.2f} km")
    print(f"   Transfers:      {route.num_transfers}")
    
    walking_segments = [s for s in route.segments if s.mode == TransportationMode.WALK]
    transit_segments = [s for s in route.segments if s.mode != TransportationMode.WALK]
    
    total_walking_km = sum(s.distance_km for s in walking_segments)
    total_transit_km = sum(s.distance_km for s in transit_segments)
    
    print(f"\n   🚶 Walking:     {total_walking_km:.2f} km ({len(walking_segments)} segments)")
    print(f"   🚌 Transit:     {total_transit_km:.2f} km ({len(transit_segments)} segments)")
    
    # Departure and arrival
    print(f"\n   🕐 Depart:      {route.departure_time.strftime('%H:%M')}")
    print(f"   🕐 Arrive:      {route.arrival_time.strftime('%H:%M')}")
    
    # Detailed steps
    print(f"\n📍 STEP-BY-STEP DIRECTIONS:")
    print(f"="*80)
    
    for i, seg in enumerate(route.segments, 1):
        # Mode icon
        if seg.mode == TransportationMode.WALK:
            icon = "🚶"
            mode_text = "WALK"
        elif seg.mode == TransportationMode.LRT:
            icon = "🚄"
            mode_text = "LRT"
        elif seg.mode == TransportationMode.TEMAN_BUS:
            icon = "🚌"
            mode_text = "BUS"
        elif seg.mode == TransportationMode.FEEDER_ANGKOT:
            icon = "🚐"
            mode_text = "ANGKOT"
        else:
            icon = "🚗"
            mode_text = seg.mode.value
        
        print(f"\n{i}. {icon} {mode_text} - {seg.route_name}")
        print(f"   ├─ From: {seg.from_stop.name}")
        if seg.mode == TransportationMode.WALK:
            print(f"   │  Walk {seg.distance_km*1000:.0f} meters ({seg.duration_minutes:.0f} min)")
        else:
            print(f"   │  Take {seg.route_name}")
            print(f"   │  {seg.duration_minutes:.0f} min, Rp {seg.cost:,}, {seg.distance_km:.2f} km")
        print(f"   └─ To:   {seg.to_stop.name}")
        
        if seg.departure_time:
            print(f"      ⏰ {seg.departure_time.strftime('%H:%M')} → {seg.arrival_time.strftime('%H:%M')}")
    
    print(f"\n" + "="*80)
    print(f"✅ Journey Complete!")
    print(f"="*80)


# Convenience function
def plan_journey(graph: TransportationGraph,
                origin_name: str,
                origin_coords: Tuple[float, float],
                dest_name: str,
                dest_coords: Tuple[float, float],
                origin_address: str = None,
                dest_address: str = None,
                optimization_mode: str = "time",
                departure_time: Optional[datetime] = None) -> Optional[Route]:
    """
    Plan a complete door-to-door journey
    
    Args:
        graph: Transportation network
        origin_name: Name of origin location
        origin_coords: (latitude, longitude) of origin
        dest_name: Name of destination location
        dest_coords: (latitude, longitude) of destination
        origin_address: Full address of origin (optional)
        dest_address: Full address of destination (optional)
        optimization_mode: Optimization criteria
        departure_time: When to depart
    
    Returns:
        Complete Route with walking and transit segments
    """
    origin = Location(
        name=origin_name,
        lat=origin_coords[0],
        lon=origin_coords[1],
        address=origin_address
    )
    
    destination = Location(
        name=dest_name,
        lat=dest_coords[0],
        lon=dest_coords[1],
        address=dest_address
    )
    
    router = DoorToDoorRouter(graph, optimization_mode)
    route = router.route(origin, destination, departure_time)
    
    if route:
        print_door_to_door_route(route)
    
    return route

