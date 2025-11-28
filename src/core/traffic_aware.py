"""
Traffic-Aware Routing Helper
Loads traffic statistics and provides dynamic travel time calculation
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional, Tuple
from pathlib import Path


class TrafficAwareHelper:
    """
    Helper class to load and use traffic statistics for dynamic routing
    """
    
    def __init__(self, traffic_stats_path: Optional[str] = None):
        """
        Initialize traffic-aware helper
        
        Args:
            traffic_stats_path: Path to traffic_stats_aggregated.json
        """
        self.traffic_stats: Dict[str, Dict] = {}
        self.corridor_speeds: Dict[Tuple[str, int], float] = {}  # (corridor, hour) -> speed
        self.loaded = False
        
        if traffic_stats_path:
            self.load_traffic_stats(traffic_stats_path)
        else:
            # Try to find traffic stats in common locations
            # Get current file directory
            current_dir = Path(__file__).parent.parent.parent
            possible_paths = [
                str(current_dir / "Penelitian_umi" / "data" / "traffic_stats_aggregated.json"),
                str(current_dir / "dataset" / "traffic_stats_aggregated.json"),
                "Penelitian_umi/data/traffic_stats_aggregated.json",
                "dataset/traffic_stats_aggregated.json",
                "../Penelitian_umi/data/traffic_stats_aggregated.json",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    self.load_traffic_stats(path)
                    break
    
    def load_traffic_stats(self, stats_path: str):
        """Load traffic statistics from JSON file"""
        if not os.path.exists(stats_path):
            print(f"⚠️  Traffic stats file not found: {stats_path}")
            print("   Using static travel times (no traffic awareness)")
            return
        
        try:
            print(f"📈 Loading traffic statistics from: {stats_path}")
            with open(stats_path, 'r', encoding='utf-8') as f:
                traffic_json = json.load(f)
            
            # Parse traffic stats
            for key_str, stats in traffic_json.items():
                self.traffic_stats[key_str] = stats
                
                # Extract corridor and hour for speed lookup
                parts = key_str.split('|')
                if len(parts) >= 4:
                    corridor = parts[0]
                    hour = int(parts[3])
                    key = (corridor, hour)
                    
                    if key not in self.corridor_speeds:
                        self.corridor_speeds[key] = []
                    
                    # Collect speeds for averaging
                    if 'mean_speed' in stats:
                        self.corridor_speeds[key].append(stats['mean_speed'])
            
            # Calculate average speeds per corridor-hour
            import statistics
            for key in self.corridor_speeds:
                speeds = self.corridor_speeds[key]
                if speeds:
                    self.corridor_speeds[key] = statistics.mean(speeds)
            
            self.loaded = True
            print(f"   ✅ Loaded {len(self.traffic_stats):,} traffic statistics")
            print(f"   ✅ Pre-calculated speeds for {len(self.corridor_speeds)} corridor-hour combinations")
        except Exception as e:
            print(f"⚠️  Error loading traffic stats: {e}")
            print("   Using static travel times (no traffic awareness)")
    
    def get_travel_time(self, route_name: str, distance_km: float, 
                       current_time: datetime) -> float:
        """
        Get dynamic travel time based on route, distance, and current time
        
        Args:
            route_name: Route name (e.g., "Angkot Feeder Koridor 1")
            distance_km: Distance in kilometers
            current_time: Current datetime (for hour lookup)
        
        Returns:
            Travel time in minutes
        """
        if not self.loaded:
            # Fallback: use default speed
            default_speed_kmh = 30.0  # Average speed
            return (distance_km / default_speed_kmh) * 60
        
        hour = current_time.hour
        
        # Try to find matching corridor
        # Match route name to corridor
        corridor_name = None
        route_lower = route_name.lower()
        
        # Map route names to corridor patterns
        if 'koridor 1' in route_lower or 'koridor_1' in route_lower:
            if 'angkot' in route_lower or 'feeder' in route_lower:
                corridor_name = "Angkot Feeder Koridor 1"
            elif 'teman bus' in route_lower or 'teman_bus' in route_lower:
                corridor_name = "Teman Bus Koridor 2"  # Check actual mapping
        elif 'koridor 2' in route_lower or 'koridor_2' in route_lower:
            if 'angkot' in route_lower or 'feeder' in route_lower:
                corridor_name = "Angkot Feeder Koridor 2"
            elif 'teman bus' in route_lower or 'teman_bus' in route_lower:
                corridor_name = "Teman Bus Koridor 2"
        elif 'koridor 3' in route_lower or 'koridor_3' in route_lower:
            corridor_name = "Angkot Feeder Koridor 3"
        elif 'koridor 4' in route_lower or 'koridor_4' in route_lower:
            corridor_name = "Angkot Feeder Koridor 4"
        elif 'koridor 5' in route_lower or 'koridor_5' in route_lower:
            if 'angkot' in route_lower or 'feeder' in route_lower:
                corridor_name = "Angkot Feeder Koridor 5"
            elif 'teman bus' in route_lower or 'teman_bus' in route_lower:
                corridor_name = "Teman Bus Koridor 5"
        elif 'koridor 6' in route_lower or 'koridor_6' in route_lower:
            corridor_name = "Angkot Feeder Koridor 6"
        elif 'koridor 7' in route_lower or 'koridor_7' in route_lower:
            corridor_name = "Angkot Feeder Koridor 7"
        elif 'koridor 8' in route_lower or 'koridor_8' in route_lower:
            corridor_name = "Angkot Feeder Koridor 8"
        
        # If corridor found, use traffic data
        if corridor_name:
            key = (corridor_name, hour)
            if key in self.corridor_speeds:
                avg_speed = self.corridor_speeds[key]
                time_hours = distance_km / avg_speed
                time_minutes = time_hours * 60
                return round(time_minutes, 2)
        
        # Fallback: use default speed with peak hour adjustment
        # Peak hours: 6-9 AM and 4-7 PM (slower)
        # Normal hours: other times (faster)
        if (6 <= hour <= 9) or (16 <= hour <= 19):
            # Peak hour: slower
            default_speed_kmh = 20.0
        else:
            # Normal hour: faster
            default_speed_kmh = 32.0
        
        return (distance_km / default_speed_kmh) * 60


# Global instance
_traffic_helper: Optional[TrafficAwareHelper] = None

def get_traffic_helper() -> TrafficAwareHelper:
    """Get or create global traffic helper instance"""
    global _traffic_helper
    if _traffic_helper is None:
        _traffic_helper = TrafficAwareHelper()
    return _traffic_helper

