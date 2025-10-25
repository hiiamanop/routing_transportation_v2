"""
Data Structures for IDA* Multi-Modal Route Planning System
Palembang Public Transportation Network
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Tuple
import json


import math


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometers"""
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


class TransportationMode(Enum):
    """Transportation modes available in Palembang"""
    LRT = "LRT"
    TEMAN_BUS = "TEMAN_BUS"
    FEEDER_ANGKOT = "FEEDER_ANGKOT"
    TRANSFER = "TRANSFER"
    WALK = "WALK"


class TrafficCondition(Enum):
    """Traffic conditions affecting travel time"""
    LIGHT = "Light"
    MODERATE = "Moderate"
    HEAVY = "Heavy"
    SEVERE = "Severe"


@dataclass
class Location:
    """Represents a geographical location"""
    name: str
    lat: float
    lon: float
    
    def __str__(self):
        return f"{self.name} ({self.lat:.6f}, {self.lon:.6f})"


@dataclass
class Stop:
    """Represents a bus stop or station"""
    id: int
    stop_id: str
    name: str
    lat: float
    lon: float
    route: str
    mode: TransportationMode
    
    def __hash__(self):
        return hash(self.stop_id)
    
    def __eq__(self, other):
        if isinstance(other, Stop):
            return self.stop_id == other.stop_id
        return False
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'stop_id': self.stop_id,
            'name': self.name,
            'lat': self.lat,
            'lon': self.lon,
            'route': self.route,
            'mode': self.mode.value
        }


@dataclass
class Edge:
    """Represents a connection between two stops"""
    from_stop: Stop
    to_stop: Stop
    route: str
    mode: TransportationMode
    distance_meters: float
    base_time_minutes: float
    cost: int = 0  # In Rupiah
    
    def to_dict(self) -> dict:
        return {
            'from': self.from_stop.name,
            'to': self.to_stop.name,
            'route': self.route,
            'mode': self.mode.value,
            'distance_km': round(self.distance_meters / 1000, 2),
            'time_minutes': round(self.base_time_minutes, 2),
            'cost': self.cost
        }


@dataclass
class RouteSegment:
    """Represents one segment of a journey on a single mode"""
    sequence: int
    mode: TransportationMode
    route_name: str
    from_stop: Stop
    to_stop: Stop
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: float
    cost: int
    distance_km: float
    traffic_condition: Optional[TrafficCondition] = None
    
    def to_dict(self) -> dict:
        return {
            'sequence': self.sequence,
            'mode': self.mode.value,
            'route_name': self.route_name,
            'from_stop': self.from_stop.name,
            'to_stop': self.to_stop.name,
            'departure_time': self.departure_time.isoformat() if self.departure_time else None,
            'arrival_time': self.arrival_time.isoformat() if self.arrival_time else None,
            'duration_minutes': round(self.duration_minutes, 2),
            'cost': self.cost,
            'distance_km': round(self.distance_km, 2),
            'traffic_condition': self.traffic_condition.value if self.traffic_condition else None
        }


@dataclass
class Route:
    """Complete journey from origin to destination"""
    route_id: int
    segments: List[RouteSegment] = field(default_factory=list)
    total_time_minutes: float = 0.0
    total_cost: int = 0
    total_distance_km: float = 0.0
    num_transfers: int = 0
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    optimization_score: float = 0.0  # For ranking routes
    
    def add_segment(self, segment: RouteSegment):
        """Add a segment to the route"""
        self.segments.append(segment)
        self.calculate_metrics()
    
    def calculate_lrt_cost(self, from_stop: Stop, to_stop: Stop) -> int:
        """
        Calculate LRT cost based on distance
        
        Rules:
        - Antar stasiun: Rp 5,000
        - Ujung ke ujung: Rp 10,000
        - Tidak ada penambahan nilai berdasarkan jarak
        """
        # Get LRT station names
        from_name = from_stop.name.lower()
        to_name = to_stop.name.lower()
        
        # Define LRT stations (assuming these are the end stations)
        lrt_end_stations = ['smb', 'bumi sriwijaya', 'asrama haji']
        
        # Check if it's end-to-end journey
        is_from_end = any(end_station in from_name for end_station in lrt_end_stations)
        is_to_end = any(end_station in to_name for end_station in lrt_end_stations)
        
        # If both are end stations, it's end-to-end journey
        if is_from_end and is_to_end and from_name != to_name:
            return 10000  # Rp 10,000 for end-to-end
        else:
            return 5000   # Rp 5,000 for regular inter-station
    
    def calculate_transfer_cost(self, current_mode: TransportationMode, 
                               next_mode: TransportationMode,
                               from_stop: Stop = None,
                               to_stop: Stop = None) -> int:
        """
        Calculate cost for transfer between modes
        
        Rules:
        - Angkot Feeder: FREE (Rp 0)
        - Teman Bus: Rp 5,000 per trip
        - LRT: Rp 5,000 (antar stasiun) atau Rp 10,000 (ujung ke ujung)
        - No additional cost if staying in same mode/corridor
        """
        # If staying in same mode, no additional cost
        if current_mode == next_mode:
            return 0
        
        # If walking or transfer, no cost
        if next_mode in [TransportationMode.WALK, TransportationMode.TRANSFER]:
            return 0
        
        # Calculate cost for new mode
        if next_mode == TransportationMode.LRT:
            # For LRT, we need to calculate based on stations
            if from_stop and to_stop:
                return self.calculate_lrt_cost(from_stop, to_stop)
            else:
                return 5000  # Default LRT cost
        else:
            return DEFAULT_COSTS.get(next_mode, 0)
    
    def calculate_route_cost(self, segments: List[RouteSegment]) -> int:
        """
        Calculate total cost for a route with proper transfer logic
        
        Rules:
        - Only charge when entering a new mode/corridor
        - Angkot Feeder: FREE
        - Teman Bus: Rp 5,000 per trip
        - LRT: Rp 5,000 (antar stasiun) atau Rp 10,000 (ujung ke ujung)
        """
        if not segments:
            return 0
        
        total_cost = 0
        current_mode = None
        
        for segment in segments:
            # Skip walking and transfer segments
            if segment.mode in [TransportationMode.WALK, TransportationMode.TRANSFER]:
                continue
            
            # If mode changed, add cost for new mode
            if current_mode != segment.mode:
                if segment.mode == TransportationMode.LRT:
                    # For LRT, calculate based on stations
                    if hasattr(segment, 'from_stop') and hasattr(segment, 'to_stop'):
                        total_cost += self.calculate_lrt_cost(segment.from_stop, segment.to_stop)
                    else:
                        total_cost += 5000  # Default LRT cost
                else:
                    total_cost += DEFAULT_COSTS.get(segment.mode, 0)
                current_mode = segment.mode
        
        return total_cost
    
    def calculate_metrics(self):
        """Calculate total time, cost, distance, and transfers"""
        if not self.segments:
            return
        
        self.total_time_minutes = sum(s.duration_minutes for s in self.segments)
        # Use proper transfer cost calculation instead of sum of segment costs
        self.total_cost = self.calculate_route_cost(self.segments)
        self.total_distance_km = sum(s.distance_km for s in self.segments)
        
        # Count transfers (mode changes)
        self.num_transfers = sum(
            1 for i in range(1, len(self.segments))
            if self.segments[i].mode != self.segments[i-1].mode
            and self.segments[i].mode != TransportationMode.TRANSFER
        )
        
        # Set departure and arrival times
        self.departure_time = self.segments[0].departure_time if self.segments else None
        self.arrival_time = self.segments[-1].arrival_time if self.segments else None
    
    def calculate_optimization_score(self, mode: str = "time", 
                                     weights: Dict[str, float] = None) -> float:
        """
        Calculate optimization score based on mode
        
        Args:
            mode: "time", "cost", "transfers", or "balanced"
            weights: Custom weights for balanced mode
        
        Returns:
            Optimization score (lower is better)
        """
        if mode == "time":
            return self.total_time_minutes
        elif mode == "cost":
            return self.total_cost
        elif mode == "transfers":
            return self.num_transfers * 15 + self.total_time_minutes  # Penalize transfers
        elif mode == "balanced":
            w = weights or {'time': 0.4, 'cost': 0.3, 'transfers': 0.3}
            # Normalize values
            time_norm = self.total_time_minutes / 60  # Normalize to hours
            cost_norm = self.total_cost / 10000  # Normalize to 10k IDR
            transfer_norm = self.num_transfers
            
            return (w['time'] * time_norm + 
                   w['cost'] * cost_norm + 
                   w['transfers'] * transfer_norm)
        else:
            return self.total_time_minutes
    
    def to_dict(self) -> dict:
        """Convert route to dictionary for JSON serialization"""
        return {
            'route_id': self.route_id,
            'summary': {
                'total_time_minutes': round(self.total_time_minutes, 2),
                'total_cost': self.total_cost,
                'total_distance_km': round(self.total_distance_km, 2),
                'num_transfers': self.num_transfers,
                'departure_time': self.departure_time.isoformat() if self.departure_time else None,
                'arrival_time': self.arrival_time.isoformat() if self.arrival_time else None,
                'optimization_score': round(self.optimization_score, 2)
            },
            'segments': [seg.to_dict() for seg in self.segments]
        }
    
    def __lt__(self, other):
        """For sorting routes by optimization score"""
        return self.optimization_score < other.optimization_score


@dataclass
class TransferPoint:
    """Transfer point between different modes"""
    location: Stop
    available_modes: List[TransportationMode]
    transfer_time_minutes: float = 5.0  # Default walking time
    
    def to_dict(self) -> dict:
        return {
            'location': self.location.to_dict(),
            'available_modes': [m.value for m in self.available_modes],
            'transfer_time_minutes': self.transfer_time_minutes
        }


@dataclass
class SearchNode:
    """Node for IDA* search"""
    stop: Stop
    parent: Optional['SearchNode'] = None
    g_cost: float = 0.0  # Cost from start
    h_cost: float = 0.0  # Heuristic cost to goal
    f_cost: float = 0.0  # Total cost (g + h)
    depth: int = 0
    current_time: Optional[datetime] = None
    current_mode: Optional[TransportationMode] = None
    route_segments: List[RouteSegment] = field(default_factory=list)
    
    def __post_init__(self):
        self.f_cost = self.g_cost + self.h_cost
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost
    
    def __hash__(self):
        return hash(self.stop.stop_id)
    
    def __eq__(self, other):
        if isinstance(other, SearchNode):
            return self.stop.stop_id == other.stop.stop_id
        return False


class TransportationGraph:
    """Graph representation of transportation network"""
    
    def __init__(self):
        self.stops: Dict[str, Stop] = {}  # stop_id -> Stop
        self.edges: Dict[str, List[Edge]] = {}  # stop_id -> [Edge]
        self.transfer_points: Dict[str, TransferPoint] = {}
        self.routes_by_mode: Dict[TransportationMode, List[str]] = {}
        
    def add_stop(self, stop: Stop):
        """Add a stop to the graph"""
        self.stops[stop.stop_id] = stop
        if stop.stop_id not in self.edges:
            self.edges[stop.stop_id] = []
    
    def add_edge(self, edge: Edge):
        """Add an edge (connection) between two stops"""
        from_id = edge.from_stop.stop_id
        if from_id not in self.edges:
            self.edges[from_id] = []
        self.edges[from_id].append(edge)
    
    def add_transfer_point(self, transfer: TransferPoint):
        """Add a transfer point"""
        self.transfer_points[transfer.location.stop_id] = transfer
    
    def get_neighbors(self, stop: Stop) -> List[Edge]:
        """Get all edges from a stop"""
        return self.edges.get(stop.stop_id, [])
    
    def get_stop_by_name(self, name: str) -> Optional[Stop]:
        """Find stop by name (fuzzy search)"""
        name_lower = name.lower()
        for stop in self.stops.values():
            if name_lower in stop.name.lower():
                return stop
        return None
    
    def is_transfer_point(self, stop: Stop) -> bool:
        """Check if stop is a transfer point"""
        return stop.stop_id in self.transfer_points
    
    def get_transfer_info(self, stop: Stop) -> Optional[TransferPoint]:
        """Get transfer point information"""
        return self.transfer_points.get(stop.stop_id)
    
    def to_dict(self) -> dict:
        """Export graph to dictionary"""
        return {
            'stops': {k: v.to_dict() for k, v in self.stops.items()},
            'edges_count': sum(len(edges) for edges in self.edges.values()),
            'transfer_points': {k: v.to_dict() for k, v in self.transfer_points.items()},
            'stats': {
                'total_stops': len(self.stops),
                'total_edges': sum(len(edges) for edges in self.edges.values()),
                'total_transfers': len(self.transfer_points)
            }
        }


# Constants
DEFAULT_COSTS = {
    TransportationMode.LRT: 5000,  # IDR per trip
    TransportationMode.TEMAN_BUS: 5000,  # IDR per trip (updated)
    TransportationMode.FEEDER_ANGKOT: 0,  # FREE (updated)
    TransportationMode.TRANSFER: 0,
    TransportationMode.WALK: 0
}

DEFAULT_SPEEDS = {
    TransportationMode.LRT: 40.0,  # km/h
    TransportationMode.TEMAN_BUS: 25.0,
    TransportationMode.FEEDER_ANGKOT: 20.0,
    TransportationMode.WALK: 5.0
}

TRAFFIC_MULTIPLIERS = {
    TrafficCondition.LIGHT: 1.0,
    TrafficCondition.MODERATE: 1.3,
    TrafficCondition.HEAVY: 1.7,
    TrafficCondition.SEVERE: 2.2
}

