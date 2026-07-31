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
    DEFAULT_SPEEDS,
    merge_consecutive_segments
)
from core import service_model


# Constants
WALKING_SPEED_KMH = 5.0
MAX_TRANSFER_WALK_KM = 0.5  # Maximum walking distance for transfers (500m)
TRANSFER_TIME_PENALTY = 5.0  # Extra 5 minutes for transfer overhead

# Preferensi jalan kaki lebih pendek saat TRANSFER, dipakai HANYA sbg
# tie-breaker mikro (menit) -- BUKAN pengali cost spt sebelumnya.
#
# Riwayat: pernah dicoba pengali 100.000x lalu 5x pada (walking_time +
# TRANSFER_TIME_PENALTY). Keduanya ternyata BISA mengalahkan selisih waktu
# NYATA berskala menit, krn cost gabungan (transfer yg dikalikan + tunggu/
# tempuh kendaraan yg TIDAK dikalikan) tidak lagi sebanding dgn total waktu
# sungguhan -- ditemukan lewat kasus nyata (2026-07-31): transfer 26m vs 302m
# (real time beda cuma ~3 menit) sampai mengalahkan pilihan yg REAL TIME-nya
# 12-13 menit lebih cepat, krn cost 5x menutupi selisih tunggu LRT berbasis
# jadwal. Cost yg dipakai utk ranking pqueue HARUS = waktu nyata total,
# supaya optimization_mode="time" selalu menemukan rute tercepat SUNGGUHAN.
# Nudge ini cuma menambah pecahan menit kecil (dibatasi/di-cap), jadi tidak
# pernah bisa membalik pilihan yg bedanya sampai hitungan menit -- cuma
# menang saat dua opsi memang sudah hampir sama waktu nyatanya.
TRANSFER_TIEBREAK_PER_KM = 0.05  # menit per km jarak transfer
TRANSFER_TIEBREAK_CAP_KM = 2.0   # jarak transfer di atas ini tidak menambah nudge lagi


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

    def _boarding_wait_minutes(self, edge: Edge, current_route: Optional[str],
                               when: Optional[datetime] = None) -> float:
        """
        Waktu tunggu kendaraan baru (nol kalau masih di rute yang sama).
        Utk LRT, `when` dipakai cari keberangkatan terdekat di jadwal resmi
        (lihat service_model.wait_minutes) -- bukan headway tetap lagi.
        """
        if edge.mode in (TransportationMode.WALK, TransportationMode.TRANSFER):
            return 0.0
        if edge.route == current_route:
            return 0.0
        return service_model.wait_minutes(
            edge.route, edge.from_stop.stop_id, edge.to_stop.stop_id, when)

    def _calculate_edge_cost(self, edge: Edge, current_mode: Optional[TransportationMode],
                             current_route: Optional[str] = None,
                             when: Optional[datetime] = None) -> float:
        """Biaya ruas: waktu tempuh nyata + waktu tunggu kendaraan."""
        wait = self._boarding_wait_minutes(edge, current_route, when)

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
            # Cost = waktu nyata + nudge mikro dibatasi (lihat komentar
            # TRANSFER_TIEBREAK_PER_KM) -- transfer lebih pendek cuma menang
            # kalau dua opsi memang sudah dekat waktu nyatanya.
            real_time = walking_time + TRANSFER_TIME_PENALTY
            tiebreak = min(distance_km, TRANSFER_TIEBREAK_CAP_KM) * TRANSFER_TIEBREAK_PER_KM
            return real_time + tiebreak
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
        
        # State = (stop_id, current_route) -- BUKAN cuma stop_id. Kalau state
        # cuma stop_id, dua cara berbeda mencapai halte yang sama (jalan kaki
        # vs masih naik kendaraan yang sama) dianggap satu hal, padahal biaya
        # LANJUTANNYA beda: yang baru jalan kaki harus bayar tunggu penuh saat
        # naik kendaraan berikutnya, yang masih di kendaraan tidak. Kalau opsi
        # "cost lebih murah utk sampai di halte ini" ternyata jalan kaki
        # (tanpa tunggu ke depan lebih baik), padahal versi "sedikit lebih
        # mahal tapi sudah naik kendaraan" (tak perlu tunggu lagi) sebenarnya
        # lebih baik utk PERJALANAN SELANJUTNYA, versi yang salah menang dan
        # yang benar tidak pernah dieksplorasi krn halte itu sudah "dikunjungi".
        # Contoh nyata: transfer H. PI->Dishub (jalan langsung) vs H. PI->Bumi
        # Sriwijaya lalu terus naik LRT lewat Dishub (tak bayar tunggu lagi).
        pq = []
        start_state = (start.stop_id, None)
        heapq.heappush(pq, DijkstraNode(cost=0.0, stop=start))

        # Best cost utk tiap STATE (halte, rute yang sedang dinaiki)
        best_cost: Dict[Tuple[str, Optional[str]], float] = {start_state: 0.0}

        visited: Set[Tuple[str, Optional[str]]] = set()
        nodes_explored = 0

        while pq:
            current_node = heapq.heappop(pq)
            current_stop = current_node.stop
            current_cost = current_node.cost
            current_route = current_node.edge_used.route if current_node.edge_used else None
            state = (current_stop.stop_id, current_route)

            # Skip if already visited
            if state in visited:
                continue

            visited.add(state)
            nodes_explored += 1

            # Goal reached! (state pertama yg stop_id-nya goal PASTI yang
            # termurah, krn heap selalu mengeluarkan cost terkecil dulu --
            # tidak peduli lewat rute apa sampainya)
            if current_stop.stop_id == goal.stop_id:
                print(f"\n✅ Route found!")
                print(f"   Nodes explored: {nodes_explored}")
                print(f"   Cost: {current_cost:.2f}")

                # Reconstruct path
                return self._reconstruct_path(current_node, departure_time)

            # Get current mode (from parent if available)
            current_mode = current_node.edge_used.mode if current_node.edge_used else current_stop.mode
            came_from_stop = current_node.edge_used.from_stop if current_node.edge_used else None
            when = departure_time + timedelta(minutes=current_node.time_accumulated)

            # Explore regular edges (same route)
            for edge in self.graph.get_neighbors(current_stop):
                neighbor = edge.to_stop
                neighbor_state = (neighbor.stop_id, edge.route)

                if neighbor_state in visited:
                    continue

                # Larang U-turn: balik ke halte yg baru saja ditinggalkan,
                # masih di rute yg sama. Sekadar mengenakan tunggu baru (bukan
                # gratis) TIDAK cukup -- dua jadwal arah berlawanan bisa
                # kebetulan selisih beberapa detik, jadi U-turn kadang masih
                # menang tipis walau tunggu baru sudah dihitung. Di dunia
                # nyata tidak ada penumpang/algoritma navigasi yg naik kereta
                # ke arah salah demi selisih hitungan detik -- larang total.
                if (edge.route == current_route and came_from_stop is not None
                        and edge.to_stop.stop_id == came_from_stop.stop_id):
                    continue

                edge_cost = self._calculate_edge_cost(edge, current_mode, current_route, when)
                new_cost = current_cost + edge_cost

                # Update if better path found
                if neighbor_state not in best_cost or new_cost < best_cost[neighbor_state]:
                    best_cost[neighbor_state] = new_cost

                    # Jam terus berjalan dgn waktu NYATA (tempuh+tunggu), bukan
                    # skor optimasi -- penting saat optimization_mode="cost",
                    # di mana edge_cost adalah Rupiah, bukan menit.
                    duration = (self._edge_travel_minutes(edge, when) +
                               self._boarding_wait_minutes(edge, current_route, when))
                    new_node = DijkstraNode(
                        cost=new_cost,
                        stop=neighbor,
                        parent=current_node,
                        edge_used=edge,
                        time_accumulated=current_node.time_accumulated + duration,
                        is_walking=False
                    )

                    heapq.heappush(pq, new_node)

            # Explore transfer options (walking to nearby stops) -- dilarang
            # dua transfer jalan kaki berturut-turut (current_node.is_walking
            # berarti kita baru saja tiba di sini lewat jalan kaki lintas
            # rute). Tanpa batas ini, pencarian bisa zigzag jalan kaki
            # lompat-lompat antar halte dari BEBERAPA rute berbeda sebelum
            # naik kendaraan apapun -- tampak seperti "sengaja jalan kaki jauh"
            # padahal cuma efek transfer_map yang menghubungkan sembarang dua
            # halte berdekatan tanpa peduli rutenya.
            if not current_node.is_walking and current_stop.stop_id in self.transfer_map:
                for nearby_stop, walk_dist_km in self.transfer_map[current_stop.stop_id]:
                    nearby_state = (nearby_stop.stop_id, "Transfer (Walking)")
                    if nearby_state in visited:
                        continue

                    # Skip if same route (already handled by regular edges)
                    if nearby_stop.route == current_stop.route:
                        continue

                    walking_cost = self._calculate_walking_cost(walk_dist_km)
                    new_cost = current_cost + walking_cost

                    # Update if better path found
                    if nearby_state not in best_cost or new_cost < best_cost[nearby_state]:
                        best_cost[nearby_state] = new_cost

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
            wait = self._boarding_wait_minutes(edge, current_route, current_time)
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

        # Gabungkan segmen berturut-turut satu kendaraan (mode+rute sama) jadi
        # satu baris tampilan -- lihat merge_consecutive_segments().
        segments = merge_consecutive_segments(segments)

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

