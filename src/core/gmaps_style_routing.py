"""
Google Maps Style Door-to-Door Routing
COMPLETE DYNAMIC INPUT SYSTEM
Works with ANY coordinates in Palembang
"""

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List

from algorithms.routing.data_loader import load_network_data
from algorithms.routing.dijkstra import DijkstraRouter, haversine_distance_km
from algorithms.routing.data_structures import (
    TransportationGraph, Route, RouteSegment, TransportationMode, Stop
)
from core import service_model


@dataclass
class Location:
    """Titik mana pun di peta -- belum tentu sebuah halte (mis. titik asal
    dan tujuan yang diketik pengguna)."""
    name: str
    lat: float
    lon: float

WALKING_SPEED_KMH = 5.0
# Di atas jarak ini, first/last-mile jalan kaki diganti "kendaraan pribadi"
# (ojek/motor) drpd gagal total "no route found" atau memaksa jalan kaki
# sangat jauh -- lihat create_first_last_mile_segment().
WALK_MAX_KM = 0.5
# Radius pencarian halte kandidat first/last-mile -- lebih lebar drpd
# WALK_MAX_KM krn halte yg agak jauh utk jalan kaki masih relevan kalau
# dijangkau naik motor.
FIRST_LAST_MILE_SEARCH_KM = 5.0


def find_nearest_stops_extended(graph: TransportationGraph,
                                lat: float, lon: float,
                                max_distance_km: float = FIRST_LAST_MILE_SEARCH_KM,
                                top_k: int = 10) -> List[Tuple[Stop, float]]:
    """Find nearest stops with extended range"""
    distances = []

    for stop in graph.stops.values():
        dist = haversine_distance_km(lat, lon, stop.lat, stop.lon)
        if dist <= max_distance_km:
            distances.append((stop, dist))

    distances.sort(key=lambda x: x[1])
    return distances[:top_k]


def _first_last_mile_minutes(dist_km: float) -> float:
    """
    Estimasi waktu first/last-mile buat SKORING kombinasi. Kecepatan SAMA
    persis dgn jalan kaki (5km/jam) baik itu WALK maupun PRIVATE_VEHICLE --
    beda >500m cuma soal PENAMAAN (orang biasanya sudah enggan jalan kaki
    lebih dari itu), bukan klaim kendaraan lebih cepat -- lihat
    create_first_last_mile_segment().
    """
    return (dist_km / WALKING_SPEED_KMH) * 60


def create_first_last_mile_segment(seq: int, from_loc: Location, to_loc: Location,
                                   departure_time: datetime) -> RouteSegment:
    """
    Segmen first/last-mile. Waktu SELALU dihitung dari jarak-garis-lurus/
    5km/jam (sama persis WALK & PRIVATE_VEHICLE) -- cuma label/mode yg beda
    di atas WALK_MAX_KM ("Kendaraan Pribadi" drpd "Jalan kaki"), krn orang
    biasanya sudah enggan jalan kaki lebih dari itu. TIDAK ada klaim
    kendaraan lebih cepat (tidak ada data tunggu ojek/lalu lintas utk ruas
    sependek ini).
    """
    dist_km = haversine_distance_km(from_loc.lat, from_loc.lon, to_loc.lat, to_loc.lon)
    duration_min = _first_last_mile_minutes(dist_km)

    from_stop = Stop(-1, f"leg_{seq}", from_loc.name, from_loc.lat, from_loc.lon,
                     "Walking", TransportationMode.WALK)
    to_stop = Stop(-2, f"leg_{seq}", to_loc.name, to_loc.lat, to_loc.lon,
                   "Walking", TransportationMode.WALK)

    is_walk = dist_km <= WALK_MAX_KM
    path = service_model.walking_path(from_loc.lat, from_loc.lon, to_loc.lat, to_loc.lon) if is_walk else None

    return RouteSegment(
        sequence=seq,
        mode=TransportationMode.WALK if is_walk else TransportationMode.PRIVATE_VEHICLE,
        route_name="Walking" if is_walk else "Kendaraan Pribadi",
        from_stop=from_stop,
        to_stop=to_stop,
        departure_time=departure_time,
        arrival_time=departure_time + timedelta(minutes=duration_min),
        duration_minutes=duration_min,
        cost=0,
        distance_km=dist_km,
        path=path
    )


def gmaps_style_route(
    graph: TransportationGraph,
    origin_name: str,
    origin_coords: Tuple[float, float],
    dest_name: str,
    dest_coords: Tuple[float, float],
    optimization_mode: str = "time",
    departure_time: Optional[datetime] = None,
    max_walking_km: float = FIRST_LAST_MILE_SEARCH_KM,
    avoid_routes: Optional[set] = None
) -> Optional[Route]:
    """
    Complete Google Maps style routing

    Args:
        graph: Transportation network
        origin_name: Origin name
        origin_coords: (lat, lon)
        dest_name: Destination name
        dest_coords: (lat, lon)
        optimization_mode: Optimization criteria
        departure_time: When to depart
        max_walking_km: Radius pencarian halte kandidat first/last-mile
            (BUKAN cuma jalan kaki -- di atas WALK_MAX_KM otomatis jadi
            "kendaraan pribadi", lihat create_first_last_mile_segment())

    Returns:
        Complete route with walking + transit
    """
    if departure_time is None:
        departure_time = datetime.now()

    print(f"\n{'='*90}")
    print(f"{'🗺️  GOOGLE MAPS STYLE ROUTING':^90}")
    print(f"{'='*90}")

    print(f"\n📍 FROM: {origin_name}")
    print(f"   📌 {origin_coords[0]:.5f}, {origin_coords[1]:.5f}")

    print(f"\n📍 TO:   {dest_name}")
    print(f"   📌 {dest_coords[0]:.5f}, {dest_coords[1]:.5f}")

    print(f"\n⚙️  Settings:")
    print(f"   🕐 Departure: {departure_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"   🎯 Optimize:  {optimization_mode.upper()}")
    print(f"   🚶 Radius kandidat halte: {max_walking_km} km (jalan kaki <= {WALK_MAX_KM}km, sisanya motor)")

    # Find nearest stops
    print(f"\n{'─'*90}")
    print(f"STEP 1: Finding nearest transit stops")
    print(f"{'─'*90}")

    origin_stops = find_nearest_stops_extended(graph, origin_coords[0], origin_coords[1], max_walking_km)
    dest_stops = find_nearest_stops_extended(graph, dest_coords[0], dest_coords[1], max_walking_km)

    if not origin_stops:
        print(f"❌ No stops within {max_walking_km}km of origin")
        return None

    if not dest_stops:
        print(f"❌ No stops within {max_walking_km}km of destination")
        return None
    
    print(f"✅ Found {len(origin_stops)} origin stops, {len(dest_stops)} destination stops")
    print(f"\n   Nearest to origin:")
    for i, (stop, dist) in enumerate(origin_stops[:3], 1):
        print(f"      {i}. {stop.name} ({stop.mode.value}) - {dist*1000:.0f}m")
    
    print(f"\n   Nearest to destination:")
    for i, (stop, dist) in enumerate(dest_stops[:3], 1):
        print(f"      {i}. {stop.name} ({stop.mode.value}) - {dist*1000:.0f}m")
    
    # Find best route using Dijkstra
    print(f"\n{'─'*90}")
    print(f"STEP 2: Finding optimal transit route (Dijkstra algorithm)")
    print(f"{'─'*90}")
    
    router = DijkstraRouter(graph, optimization_mode, avoid_routes=avoid_routes)
    
    best_route = None
    best_score = float('inf')
    
    # Try combinations
    combinations_tried = 0
    max_combinations = min(5, len(origin_stops)) * min(5, len(dest_stops))
    
    print(f"🔍 Trying up to {max_combinations} route combinations...")
    
    for origin_stop, origin_dist in origin_stops[:5]:
        for dest_stop, dest_dist in dest_stops[:5]:
            combinations_tried += 1
            
            # Find transit route
            transit_route = router.search(origin_stop, dest_stop, departure_time)
            
            if transit_route:
                # Calculate total score including first/last-mile (jalan
                # kaki atau kendaraan pribadi, kecepatan sama -- lihat WALK_MAX_KM)
                origin_leg_time = _first_last_mile_minutes(origin_dist)
                dest_leg_time = _first_last_mile_minutes(dest_dist)
                total_time = origin_leg_time + transit_route.total_time_minutes + dest_leg_time

                if optimization_mode == "time":
                    # Pemilihan halte naik/turun pertama dari alamat asal/
                    # tujuan TETAP murni waktu tercepat -- prioritas mutlak
                    # minimalkan jalan kaki hanya berlaku utk TRANSFER di
                    # tengah perjalanan (ganti moda/koridor), sudah ditangani
                    # di DijkstraRouter._calculate_walking_cost(). Kalau
                    # dipakai di sini juga, pencarian bisa memaksa naik
                    # kendaraan yang jauh lebih lama demi transfer 0 meter,
                    # padahal yang diinginkan cuma transfer-nya yg dihemat.
                    score = total_time
                elif optimization_mode == "cost":
                    # Ongkos dulu, TAPI di antara yang ongkosnya sama pilih yang
                    # tercepat. Tarif di jaringan ini sangat kasar (Feeder GRATIS,
                    # Teman Bus & LRT tarif rata Rp5.000), jadi SANGAT banyak rute
                    # berbeda punya ongkos PERSIS SAMA. Dulu skor di sini cuma
                    # total_cost, sehingga di antara yang seri terpilih rute mana
                    # saja -- akibatnya tab "Termurah" menyajikan rute yang
                    # ongkosnya sama persis dgn "Tercepat" tapi 2-3x lebih lama
                    # (terukur: Rp5.000/38 menit vs Rp5.000/93 menit).
                    #
                    # 0.01 per menit: rute terlama sekalipun (~300 menit) cuma
                    # menambah 3, jauh di bawah satuan rupiah terkecil (Rp5.000),
                    # jadi TIDAK PERNAH bisa mengalahkan selisih ongkos yang
                    # nyata -- murni pemecah seri.
                    score = transit_route.total_cost + 0.01 * total_time
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
                        'total_time': total_time
                    }
                    print(f"   ✓ Found route: {total_time:.1f} min, Rp {transit_route.total_cost:,}")
    
    print(f"\n   Checked {combinations_tried} combinations")
    
    if not best_route:
        print(f"❌ No viable route found")
        return None
    
    # Construct complete route
    print(f"\n{'─'*90}")
    print(f"STEP 3: Building complete door-to-door route")
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
    
    walk1 = create_first_last_mile_segment(1, origin_loc, origin_stop_loc, current_time)
    segments.append(walk1)
    current_time = walk1.arrival_time

    print(f"✅ Segment 1: {walk1.mode.value} to {best_route['origin_stop'].name} ({best_route['origin_dist']*1000:.0f}m)")
    
    # Segmen transit: duration_minutes & wait_minutes SUDAH dihitung dengan
    # benar (waktu nyata per-jam + waktu tunggu) di dalam DijkstraRouter itu
    # sendiri. Dulu di sini ada lapisan "traffic-aware" tambahan yang menimpa
    # angka itu dengan tebakan 12/20 km/h dari traffic_aware.py -- dihapus
    # karena menimpa angka yang sudah benar dengan yang lebih kasar (dan
    # kebetulan menganggap jam 08:00 & 13:00 sama-sama "peak", menutupi variasi
    # per-jam yang seharusnya terlihat).
    for transit_seg in best_route['transit_route'].segments:
        transit_seg.sequence = len(segments) + 1
        transit_seg.departure_time = current_time
        transit_seg.arrival_time = current_time + timedelta(minutes=transit_seg.duration_minutes)
        segments.append(transit_seg)
        current_time = transit_seg.arrival_time
    
    print(f"✅ Segments 2-{len(segments)}: Transit ({len(best_route['transit_route'].segments)} segments)")
    
    # Walking from last stop
    dest_stop_loc = Location(
        best_route['dest_stop'].name,
        best_route['dest_stop'].lat,
        best_route['dest_stop'].lon
    )
    dest_loc = Location(dest_name, dest_coords[0], dest_coords[1])
    
    walk2 = create_first_last_mile_segment(len(segments) + 1, dest_stop_loc, dest_loc, current_time)
    segments.append(walk2)

    print(f"✅ Segment {len(segments)}: {walk2.mode.value} to destination ({best_route['dest_dist']*1000:.0f}m)")
    
    # Create final route
    complete_route = Route(route_id=1, segments=segments)
    complete_route.calculate_metrics()
    complete_route.optimization_score = best_score
    
    return complete_route


def _route_signature(route: Route) -> tuple:
    """Sidik jari rute berdasarkan urutan halte transit - dipakai untuk
    membuang alternatif yang sebetulnya rute yang sama persis."""
    return tuple(
        (s.from_stop.stop_id, s.to_stop.stop_id, s.route_name)
        for s in route.segments
        if s.mode not in (TransportationMode.WALK, TransportationMode.PRIVATE_VEHICLE)
    )


def find_route_alternatives(
    graph: TransportationGraph,
    origin_name: str,
    origin_coords: Tuple[float, float],
    dest_name: str,
    dest_coords: Tuple[float, float],
    departure_time: Optional[datetime] = None,
    max_walking_km: float = FIRST_LAST_MILE_SEARCH_KM
) -> List[Dict]:
    """
    Beberapa opsi rute seperti Google Maps: tercepat, termurah, paling sedikit
    transfer. Dijalankan dengan tiga tujuan optimasi berbeda di atas Dijkstra
    yang sama (bukan k-shortest-path formal) -- cukup untuk jaringan sekecil
    ini (402 halte) dan sudah menghasilkan opsi yang benar-benar berbeda
    karena tarif & jumlah transfer nyata berbeda antar rute.
    """
    candidates = [
        ("Tercepat", "time"),
        ("Termurah", "cost"),
        ("Paling sedikit transfer", "transfers"),
    ]

    seen_signatures = set()
    alternatives = []
    for label, mode in candidates:
        route = gmaps_style_route(
            graph, origin_name, origin_coords, dest_name, dest_coords,
            optimization_mode=mode, departure_time=departure_time,
            max_walking_km=max_walking_km,
        )
        if route is None:
            continue
        sig = _route_signature(route)
        if sig in seen_signatures:
            continue  # sama persis dengan alternatif yang sudah ada, skip
        seen_signatures.add(sig)
        alternatives.append({"label": label, "optimized_for": mode, "route": route})

    # Rute lewat KORIDOR LAIN.
    #
    # Ketiga pencarian di atas sering bermuara ke rute yang sama persis lalu
    # digabung penyaring duplikat -- terukur: 9 dari 14 pencarian cuma
    # menyisakan SATU alternatif. Akibatnya tab "Sesuai Preferensi Saya"
    # tidak punya apa pun untuk dipilih dan selalu sama dgn "Tercepat".
    #
    # Jadi dicari sekali lagi dgn koridor yang dipakai rute terbaik DIHUKUM,
    # meniru cara Google Maps menyodorkan jalan lain. Hasilnya pilihan yang
    # benar-benar berbeda (mis. naik Feeder gratis alih-alih LRT berbayar),
    # bukan variasi tipis. Hukumannya lunak: kalau memang tidak ada jalan
    # lain, koridor yang sama tetap dipakai dan hasilnya tersaring sbg
    # duplikat -- tidak pernah bikin pencarian gagal.
    if alternatives:
        used = {
            s.route_name
            for s in alternatives[0]["route"].segments
            if s.mode not in (TransportationMode.WALK,
                              TransportationMode.PRIVATE_VEHICLE,
                              TransportationMode.TRANSFER)
        }
        if used:
            other = gmaps_style_route(
                graph, origin_name, origin_coords, dest_name, dest_coords,
                optimization_mode="time", departure_time=departure_time,
                max_walking_km=max_walking_km, avoid_routes=used,
            )
            if other is not None and _route_signature(other) not in seen_signatures:
                alternatives.append({
                    "label": "Lewat rute lain",
                    "optimized_for": "alternative",
                    "route": other,
                })

    return alternatives


def describe_no_route_reason(
    graph: TransportationGraph,
    origin_coords: Tuple[float, float],
    dest_coords: Tuple[float, float],
    max_walking_km: float = FIRST_LAST_MILE_SEARCH_KM,
) -> str:
    """
    Alasan spesifik kalau find_route_alternatives() balik kosong -- dicek
    ULANG di sini (bukan reuse hasil yg sudah None) supaya pesan errornya
    bisa membedakan "halte tidak ditemukan di sekitar titik ini" (kasus
    paling umum, mis. titik terlalu jauh dari jaringan) dari "halte ada di
    kedua titik tapi tidak ada rute yg menghubungkan keduanya".
    """
    origin_stops = find_nearest_stops_extended(graph, origin_coords[0], origin_coords[1], max_walking_km)
    dest_stops = find_nearest_stops_extended(graph, dest_coords[0], dest_coords[1], max_walking_km)
    radius = f"{max_walking_km:.0f} km"

    if not origin_stops and not dest_stops:
        return (
            f"Tidak ditemukan halte transportasi umum dalam radius {radius} "
            f"dari titik asal maupun titik tujuan."
        )
    if not origin_stops:
        return f"Tidak ditemukan halte transportasi umum dalam radius {radius} dari titik asal."
    if not dest_stops:
        return f"Tidak ditemukan halte transportasi umum dalam radius {radius} dari titik tujuan."
    return "Halte ditemukan di titik asal dan tujuan, tapi tidak ada rute yang menghubungkan keduanya di jaringan kami."


# --- Fitur "preferensi pengguna": pilih di antara alternatif yang SUDAH ---
# --- ada (Tercepat/Termurah/Transfer paling sedikit), bukan pencarian baru.

PREFERENCE_CRITERIA = ("time", "cost", "comfort", "accessibility", "reliability")


def _route_comfort_score(route: Route) -> float:
    """Rata-rata skor kenyamanan per moda (COMFORT_SCORE), tertimbang durasi
    tiap segmen, dikurangi penalti per transfer. Lihat komentar
    COMFORT_SCORE di service_model.py -- ini skor editorial, bukan hasil ukur."""
    total_duration = sum(s.duration_minutes for s in route.segments)
    if total_duration <= 0:
        return 0.0
    weighted = sum(
        service_model.COMFORT_SCORE.get(s.mode.value, 2.5) * s.duration_minutes
        for s in route.segments
    )
    score = weighted / total_duration - service_model.TRANSFER_COMFORT_PENALTY * route.num_transfers
    return max(0.0, min(5.0, score))


def _route_reliability_score(route: Route) -> float:
    """Rata-rata skor keandalan per moda (RELIABILITY_SCORE), tertimbang
    durasi tiap segmen."""
    total_duration = sum(s.duration_minutes for s in route.segments)
    if total_duration <= 0:
        return 0.0
    weighted = sum(
        service_model.RELIABILITY_SCORE.get(s.mode.value, 2.5) * s.duration_minutes
        for s in route.segments
    )
    return weighted / total_duration


def _route_accessibility_km(route: Route) -> float:
    """Total jarak first/last-mile (jalan kaki + kendaraan pribadi) -- makin
    pendek makin mudah diakses."""
    return sum(
        s.distance_km for s in route.segments
        if s.mode in (TransportationMode.WALK, TransportationMode.PRIVATE_VEHICLE)
    )


def route_attributes(route: Route) -> Dict[str, float]:
    """
    Atribut X_ij satu alternatif rute, dalam SATUAN ASLI (menit, rupiah, km,
    skor 0-5) -- bukan hasil normalisasi.

    Dipakai dua hal: ditampilkan bersama tiap alternatif, dan direkam sbg
    variabel bebas saat pengguna memilih rute (lihat POST /api/choice).
    Satuan asli dipertahankan karena estimasi parameter model pemilihan
    (MNL) butuh nilai apa adanya -- normalisasi min-max hanya relevan utk
    perbandingan antar kandidat dalam SATU query, dan koefisiennya tidak
    akan bisa ditafsirkan (mis. "per menit") kalau skalanya berubah-ubah
    tiap perjalanan.
    """
    return {
        "time_minutes": float(route.total_time_minutes),
        "cost_rupiah": float(route.total_cost),
        "transfers": float(route.num_transfers),
        "access_km": _route_accessibility_km(route),
        "comfort": _route_comfort_score(route),
        "reliability": _route_reliability_score(route),
    }


def score_route_by_preference(route: Route, weights: Dict[str, float],
                              bounds: Dict[str, Tuple[float, float]]) -> float:
    """
    Gabungkan 5 kriteria jadi satu skor (lebih tinggi = lebih cocok dgn
    preferensi). `bounds` = {criterion: (lo, hi)} dari MIN-MAX di antara
    kandidat yang sedang dibandingkan (bukan angka acuan tetap -- perjalanan
    2km vs 25km punya skala waktu/biaya yg beda jauh, jadi normalisasi harus
    relatif ke kandidat yg ada, bukan konstanta yg dikarang).
    """
    def goodness(value: float, criterion: str, higher_is_better: bool) -> float:
        lo, hi = bounds[criterion]
        if hi == lo:
            return 1.0
        return (value - lo) / (hi - lo) if higher_is_better else (hi - value) / (hi - lo)

    time_g = goodness(route.total_time_minutes, "time", higher_is_better=False)
    cost_g = goodness(route.total_cost, "cost", higher_is_better=False)
    comfort_g = goodness(_route_comfort_score(route), "comfort", higher_is_better=True)
    access_g = goodness(_route_accessibility_km(route), "accessibility", higher_is_better=False)
    reliability_g = goodness(_route_reliability_score(route), "reliability", higher_is_better=True)

    return (
        weights["time"] * time_g + weights["cost"] * cost_g +
        weights["comfort"] * comfort_g + weights["accessibility"] * access_g +
        weights["reliability"] * reliability_g
    )


def select_preferred_route(alternatives: List[Dict], preferences: Dict[str, float]) -> Optional[Dict]:
    """
    Pilih alternatif (dari `find_route_alternatives()`) yang paling cocok dgn
    preferensi 1-5 pengguna utk 5 kriteria. Tidak menjalankan pencarian rute
    baru -- murni menilai ulang kandidat yang sudah ada.
    """
    if not alternatives:
        return None

    total_rating = sum(preferences.values())
    if total_rating <= 0:
        weights = {c: 1.0 / len(PREFERENCE_CRITERIA) for c in PREFERENCE_CRITERIA}
    else:
        weights = {c: preferences[c] / total_rating for c in PREFERENCE_CRITERIA}

    routes = [alt["route"] for alt in alternatives]
    raw = {
        "time": [r.total_time_minutes for r in routes],
        "cost": [r.total_cost for r in routes],
        "comfort": [_route_comfort_score(r) for r in routes],
        "accessibility": [_route_accessibility_km(r) for r in routes],
        "reliability": [_route_reliability_score(r) for r in routes],
    }
    bounds = {c: (min(values), max(values)) for c, values in raw.items()}

    best_alt = max(alternatives, key=lambda alt: score_route_by_preference(alt["route"], weights, bounds))
    return {"label": "Sesuai Preferensi Saya", "optimized_for": "preference", "route": best_alt["route"]}


def print_gmaps_route(route: Route, origin_name: str, dest_name: str):
    """Print route in Google Maps style"""
    
    print(f"\n{'='*90}")
    print(f"{'✅ ROUTE FOUND - GOOGLE MAPS STYLE':^90}")
    print(f"{'='*90}")
    
    # Header
    print(f"\n🗺️  {origin_name} → {dest_name}")
    print(f"{'─'*90}")
    
    # Summary
    walking_segs = [s for s in route.segments if s.mode == TransportationMode.WALK]
    transit_segs = [s for s in route.segments if s.mode != TransportationMode.WALK]
    
    total_walk_km = sum(s.distance_km for s in walking_segs)
    total_transit_km = sum(s.distance_km for s in transit_segs)
    
    print(f"\n📊 JOURNEY SUMMARY")
    print(f"   ⏱️  Total time:     {route.total_time_minutes:.0f} min ({route.total_time_minutes/60:.1f} hours)")
    print(f"   💰 Total cost:     Rp {route.total_cost:,}")
    print(f"   📏 Total distance: {route.total_distance_km:.2f} km")
    print(f"   🔄 Transfers:      {route.num_transfers}")
    print(f"")
    print(f"   🚶 Walking:   {total_walk_km:.2f} km ({len(walking_segs)} segments)")
    print(f"   🚌 Transit:   {total_transit_km:.2f} km ({len(transit_segs)} segments)")
    print(f"")
    print(f"   🕐 Depart:    {route.departure_time.strftime('%H:%M')}")
    print(f"   🕐 Arrive:    {route.arrival_time.strftime('%H:%M')}")
    
    # Detailed directions
    print(f"\n{'─'*90}")
    print(f"📍 TURN-BY-TURN DIRECTIONS")
    print(f"{'─'*90}")
    
    for i, seg in enumerate(route.segments, 1):
        # Icon
        if seg.mode == TransportationMode.WALK:
            icon = "🚶"
            action = "Walk"
        elif seg.mode == TransportationMode.LRT:
            icon = "🚄"
            action = "Take LRT"
        elif seg.mode == TransportationMode.TEMAN_BUS:
            icon = "🚌"
            action = "Take Teman Bus"
        elif seg.mode == TransportationMode.FEEDER_ANGKOT:
            icon = "🚐"
            action = "Take Angkot Feeder"
        elif seg.mode == TransportationMode.TRANSFER:
            icon = "🚶"
            action = "Transfer (walk)"
        else:
            icon = "🚗"
            action = "Travel"
        
        print(f"\n{i}. {icon} {action}")
        
        if seg.mode == TransportationMode.WALK:
            print(f"   Walk {seg.distance_km*1000:.0f} meters ({seg.duration_minutes:.0f} min)")
        else:
            print(f"   Route: {seg.route_name}")
            print(f"   Duration: {seg.duration_minutes:.1f} min | Cost: Rp {seg.cost:,} | Distance: {seg.distance_km:.2f} km")
        
        print(f"   From: {seg.from_stop.name}")
        print(f"   To:   {seg.to_stop.name}")
        
        if seg.departure_time:
            print(f"   ⏰ {seg.departure_time.strftime('%H:%M')} → {seg.arrival_time.strftime('%H:%M')}")
    
    print(f"\n{'='*90}")
    print(f"{'✅ HAVE A SAFE JOURNEY!':^90}")
    print(f"{'='*90}")


def interactive_routing():
    """Interactive routing interface"""
    
    print(f"\n{'='*90}")
    print(f"{'🚀 GOOGLE MAPS STYLE ROUTING - PALEMBANG':^90}")
    print(f"{'='*90}")
    print(f"{'Enter ANY coordinates in Palembang':^90}")
    print(f"{'System will find the best public transport route!':^90}")
    print(f"{'='*90}")
    
    # Load network
    print(f"\n📂 Loading Palembang transportation network...")
    graph = load_network_data("dataset/network_data_complete.json")
    
    while True:
        try:
            print(f"\n{'─'*90}")
            
            # Origin
            origin_name = input(f"\n📍 ORIGIN name: ").strip()
            if not origin_name:
                print(f"Using example: SMA Negeri 10 Palembang")
                origin_name = "SMA Negeri 10 Palembang"
                origin_coords = (-2.99361, 104.72556)
            else:
                lat_str = input(f"   Latitude:  ").strip()
                lon_str = input(f"   Longitude: ").strip()
                origin_coords = (float(lat_str), float(lon_str))
            
            # Destination
            dest_name = input(f"\n📍 DESTINATION name: ").strip()
            if not dest_name:
                print(f"Using example: Pasar Modern Plaju")
                dest_name = "Pasar Modern Plaju"
                dest_coords = (-3.01495, 104.807771)
            else:
                lat_str = input(f"   Latitude:  ").strip()
                lon_str = input(f"   Longitude: ").strip()
                dest_coords = (float(lat_str), float(lon_str))
            
            # Options
            print(f"\n⚙️  OPTIMIZATION:")
            print(f"   1. Time (fastest)")
            print(f"   2. Cost (cheapest)")
            print(f"   3. Balanced")
            
            opt_choice = input(f"\nSelect (1-3) [1]: ").strip() or "1"
            opt_map = {'1': 'time', '2': 'cost', '3': 'balanced'}
            optimization = opt_map.get(opt_choice, 'time')
            
            # Route
            route = gmaps_style_route(
                graph=graph,
                origin_name=origin_name,
                origin_coords=origin_coords,
                dest_name=dest_name,
                dest_coords=dest_coords,
                optimization_mode=optimization
            )
            
            if route:
                print_gmaps_route(route, origin_name, dest_name)
                
                # Export
                export_choice = input(f"\n💾 Export to JSON? (y/n): ").strip().lower()
                if export_choice == 'y':
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"gmaps_route_{timestamp}.json"
                    
                    route_dict = route.to_dict()
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(route_dict, f, indent=2, ensure_ascii=False)
                    
                    print(f"✅ Saved to: {filename}")
            
            # Continue?
            cont = input(f"\n🔄 Plan another route? (y/n): ").strip().lower()
            if cont != 'y':
                break
        
        except KeyboardInterrupt:
            print(f"\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test with user's example
        print(f"🧪 Testing with: SMA 10 → Pasar Modern Plaju")
        
        graph = load_network_data("dataset/network_data_complete.json")
        
        route = gmaps_style_route(
            graph=graph,
            origin_name="SMA Negeri 10 Palembang",
            origin_coords=(-2.99361, 104.72556),
            dest_name="Pasar Modern Plaju",
            dest_coords=(-3.01495, 104.807771),
            optimization_mode="time"
        )
        
        if route:
            print_gmaps_route(route, "SMA Negeri 10 Palembang", "Pasar Modern Plaju")
    else:
        interactive_routing()

