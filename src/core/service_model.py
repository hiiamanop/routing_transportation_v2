"""
Service Model - waktu tempuh nyata, waktu tunggu, dan jam operasional.

Menggantikan traffic_aware.py, yang mencari file traffic_stats_aggregated.json
yang tidak pernah ada di repo ini sehingga selalu jatuh ke tebakan 12/20 km/h.
Modul ini membaca langsung dari data survei yang memang ada di dataset/.

Sumber data:
- dataset/traffic_30days/*.csv : survei 30 hari, waktu tempuh nyata per ruas
                                 per jam (8 Feeder + 2 Teman Bus)
- dataset/lrt/jadwal.csv       : jadwal resmi LRT (trip pertama & terakhir)

ASUMSI YANG DIDEKLARASIKAN (tidak berasal dari data penelitian ini):
headway armada TIDAK ADA di dataset manapun. Angka di HEADWAY_MINUTES berasal
dari sumber sekunder (internet) dan BELUM DISITASI - lengkapi rujukannya
sebelum dipakai di naskah. Survei 30 hari mencatat waktu TEMPUH, bukan
FREKUENSI kendaraan: ke-480 keberangkatan di CSV semuanya tepat pada detik :00
di awal jam, yang berarti itu jadwal surveyor, bukan jadwal armada.
"""

import csv
import glob
import math
import os
from collections import defaultdict
from datetime import datetime, time
from pathlib import Path
from typing import Dict, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent.parent
TRAFFIC_GLOB = str(_ROOT / "dataset" / "traffic_30days" / "*.csv")
LRT_JADWAL = str(_ROOT / "dataset" / "lrt" / "jadwal.csv")

# --- Asumsi headway (menit antar kendaraan di rute yang sama) --------------
# SUMBER: sekunder (internet), bukan survei primer penelitian ini. TODO: sitasi.
# Ubah di sini kalau nanti ada data headway hasil survei sendiri.
HEADWAY_MINUTES = {
    "FEEDER_ANGKOT": 30.0,
    "TEMAN_BUS": 30.0,
    "LRT": 17.0,
}

# Model tunggu: "full" = headway penuh (skenario terburuk, pilihan pemilik
# penelitian), "half" = headway/2 (kedatangan penumpang acak, lazim di literatur).
WAIT_MODEL = "full"

# --- Jam operasional ------------------------------------------------------
# Feeder & Teman Bus: rentang keberangkatan yang tercakup survei (06:00-21:00).
# LRT: dari jadwal.csv - trip paling awal 05:06 (DJKA), paling akhir tiba 20:43.
SERVICE_HOURS = {
    "FEEDER_ANGKOT": (time(6, 0), time(21, 0)),
    "TEMAN_BUS": (time(6, 0), time(21, 0)),
    "LRT": (time(5, 6), time(20, 43)),
}

# --- Kendaraan pribadi ----------------------------------------------------
# Jarak garis lurus dikali faktor ini untuk memperkirakan jarak jalan nyata.
ROAD_DETOUR_FACTOR = 1.3
# Kecepatan survei sudah termasuk waktu berhenti menaik-turunkan penumpang;
# kendaraan pribadi tidak berhenti, jadi diberi faktor pengali. Knob kalibrasi:
# naikkan kalau estimasi mobil terasa terlalu lambat dibanding kenyataan.
PRIVATE_VEHICLE_SPEED_FACTOR = 1.4
# Dipakai kalau data survei tidak tersedia sama sekali.
FALLBACK_ROAD_SPEED_KMH = 25.0

LRT_NAME_TO_LOCAL = {
    'Bandara': '5', 'Asrama Haji': '6', 'Punti Kayu': '1', 'RSUD': '2',
    'Garuda Dempo': '3', 'Demang': '4', 'Bumi Sriwijaya': '7', 'Dishub': '8',
    'Cinde': '9', 'Ampera': '10', 'Polresta': '11', 'Jakabaring': '12', 'DJKA': '13',
}

DEFAULT_SPEEDS_KMH = {
    "LRT": 40.0, "TEMAN_BUS": 25.0, "FEEDER_ANGKOT": 20.0, "WALK": 5.0,
}


def mode_of_route(route: str) -> str:
    """'Feeder Koridor 1' -> 'FEEDER_ANGKOT'. Cocok dgn field route di graf."""
    if route == "LRT Sumsel" or route.startswith("LRT"):
        return "LRT"
    if route.startswith("Teman Bus"):
        return "TEMAN_BUS"
    if "Feeder" in route:
        return "FEEDER_ANGKOT"
    return "WALK"


def local_of_stop_id(stop_id: str) -> str:
    """'Feeder_Koridor_4_6' -> '6'."""
    return stop_id.rsplit("_", 1)[-1]


class _ServiceData:
    """Lookup waktu tempuh nyata. Dibaca sekali, di-cache di level modul."""

    def __init__(self):
        # (route, from_local, to_local, hour) -> mean menit
        self.by_hour: Dict[Tuple[str, str, str, int], float] = {}
        # (route, from_local, to_local) -> mean menit (semua jam)
        self.by_edge: Dict[Tuple[str, str, str], float] = {}
        # hour -> mean effective_speed_kmh se-kota (untuk kendaraan pribadi)
        self.road_speed_by_hour: Dict[int, float] = {}
        self.loaded = False
        self.n_rows = 0

    def load(self):
        if self.loaded:
            return self
        hour_sums, hour_counts = defaultdict(float), defaultdict(int)
        edge_sums, edge_counts = defaultdict(float), defaultdict(int)
        spd_sums, spd_counts = defaultdict(float), defaultdict(int)

        for path in glob.glob(TRAFFIC_GLOB):
            with open(path, newline="") as f:
                for row in csv.DictReader(f):
                    # CSV pakai "Angkot Feeder Koridor N", graf pakai
                    # "Feeder Koridor N" - normalkan supaya join-nya cocok.
                    route = row["corridor"].replace("Angkot ", "", 1)
                    frm, to = row["from_stop"], row["to_stop"]
                    try:
                        minutes = float(row["travel_time_min"])
                        hour = int(row["departure_time"][:2])
                        speed = float(row["effective_speed_kmh"])
                    except (ValueError, KeyError):
                        continue
                    self.n_rows += 1
                    hour_sums[(route, frm, to, hour)] += minutes
                    hour_counts[(route, frm, to, hour)] += 1
                    edge_sums[(route, frm, to)] += minutes
                    edge_counts[(route, frm, to)] += 1
                    spd_sums[hour] += speed
                    spd_counts[hour] += 1

        self.by_hour = {k: hour_sums[k] / hour_counts[k] for k in hour_sums}
        self.by_edge = {k: edge_sums[k] / edge_counts[k] for k in edge_sums}
        self.road_speed_by_hour = {h: spd_sums[h] / spd_counts[h] for h in spd_sums}

        for (a, b), minutes in _load_lrt_times().items():
            self.by_edge[("LRT Sumsel", a, b)] = minutes

        self.loaded = True
        return self


def _parse_wib(t: str) -> int:
    t = t.replace(" WIB", "").strip()
    h, m = t.split(".")
    return int(h) * 60 + int(m)


def _load_lrt_times() -> Dict[Tuple[str, str], float]:
    """(from_local, to_local) -> menit antar stasiun, dari jadwal resmi."""
    if not os.path.exists(LRT_JADWAL):
        return {}
    rows = list(csv.reader(open(LRT_JADWAL)))
    directions, current = [], []
    for r in rows:
        if not any(r) or (r and r[0] and "Perjalanan" in r[0]):
            if current:
                directions.append(current)
                current = []
            continue
        if len(r) == 3 and r[1] and r[2]:
            current.append(r)
    if current:
        directions.append(current)

    pair_times = defaultdict(list)
    for direction in directions:
        for i in range(len(direction) - 1):
            name_a, t1a, t1b = direction[i]
            name_b, t2a, t2b = direction[i + 1]
            a = LRT_NAME_TO_LOCAL.get(name_a.strip())
            b = LRT_NAME_TO_LOCAL.get(name_b.strip())
            if not a or not b:
                continue
            for ta, tb in ((t1a, t2a), (t1b, t2b)):
                diff = _parse_wib(tb) - _parse_wib(ta)
                if diff < 0:
                    diff += 24 * 60
                pair_times[(a, b)].append(diff)
    return {k: sum(v) / len(v) for k, v in pair_times.items()}


_data: Optional[_ServiceData] = None


def get_data() -> _ServiceData:
    global _data
    if _data is None:
        _data = _ServiceData().load()
    return _data


def travel_minutes(route: str, from_stop_id: str, to_stop_id: str,
                   distance_km: float, when: Optional[datetime] = None) -> float:
    """
    Waktu tempuh satu ruas. Prioritas:
      1. data survei nyata untuk jam tersebut
      2. data survei nyata rata-rata semua jam
      3. rumus jarak/kecepatan (ruas tanpa cakupan survei)
    """
    data = get_data()
    frm, to = local_of_stop_id(from_stop_id), local_of_stop_id(to_stop_id)

    if when is not None:
        hit = data.by_hour.get((route, frm, to, when.hour))
        if hit is not None:
            return hit

    hit = data.by_edge.get((route, frm, to))
    if hit is not None:
        return hit

    speed = DEFAULT_SPEEDS_KMH.get(mode_of_route(route), 20.0)
    return distance_km / speed * 60


def wait_minutes(route: str) -> float:
    """Waktu tunggu saat naik kendaraan ini. Nol untuk jalan kaki."""
    mode = mode_of_route(route)
    headway = HEADWAY_MINUTES.get(mode)
    if headway is None:
        return 0.0
    return headway if WAIT_MODEL == "full" else headway / 2.0


def is_in_service(route: str, when: datetime) -> bool:
    window = SERVICE_HOURS.get(mode_of_route(route))
    if window is None:
        return True
    start, end = window
    return start <= when.time() <= end


def any_service_available(when: datetime) -> bool:
    """True kalau ADA moda yang beroperasi pada jam tsb."""
    return any(start <= when.time() <= end for start, end in SERVICE_HOURS.values())


def service_window_text() -> str:
    parts = []
    for mode, (start, end) in SERVICE_HOURS.items():
        parts.append(f"{mode.replace('_', ' ').title()} "
                     f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}")
    return "; ".join(parts)


import json as _json
import ssl as _ssl
import urllib.request as _req

OSRM_BASE = "https://router.project-osrm.org/route/v1"
WALKING_PATH_TIMEOUT_SECONDS = 3.0
# ponytail: OSRM demo publik, bukan server sendiri -- tidak ada SLA. Kalau
# ini jadi sumber error/lambat di produksi, ganti ke OSRM self-hosted atau
# naikkan timeout. Gagal/timeout SELALU fallback diam-diam ke garis lurus,
# jadi tidak pernah membuat pencarian rute gagal total.
_walking_path_disabled = False  # dimatikan otomatis setelah kegagalan pertama
_cached_ssl_context: Optional[_ssl.SSLContext] = None


def _ssl_context() -> Optional[_ssl.SSLContext]:
    """
    Pakai bundel sertifikat certifi kalau ada -- banyak instalasi Python
    (terutama python.org di macOS) tidak otomatis memakai trust store sistem,
    jadi urlopen() polos gagal dgn CERTIFICATE_VERIFY_FAILED walau curl normal.
    None (default urlopen) kalau certifi tidak terpasang.
    """
    global _cached_ssl_context
    if _cached_ssl_context is None:
        try:
            import certifi
            _cached_ssl_context = _ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            _cached_ssl_context = False  # sudah dicoba, tidak ada certifi
    return _cached_ssl_context or None


def walking_path(from_lat: float, from_lon: float,
                 to_lat: float, to_lon: float) -> Optional[list]:
    """
    Polyline jalan kaki asli dari OSRM (profil foot), sbg list [lat, lon]
    (format yang sama dengan route_waypoints koridor transit). None kalau
    OSRM gagal/timeout -- pemanggil harus fallback ke garis lurus [from, to].
    """
    global _walking_path_disabled
    if _walking_path_disabled:
        return None
    url = (f"{OSRM_BASE}/foot/{from_lon},{from_lat};{to_lon},{to_lat}"
          f"?overview=full&geometries=geojson")
    try:
        with _req.urlopen(url, timeout=WALKING_PATH_TIMEOUT_SECONDS, context=_ssl_context()) as resp:
            data = _json.loads(resp.read())
        if data.get("code") != "Ok":
            return None
        return [[c[1], c[0]] for c in data["routes"][0]["geometry"]["coordinates"]]
    except Exception:
        # Satu kegagalan (mis. timeout/offline) cukup untuk mematikan sisa
        # request di proses ini -- jangan bikin SETIAP jalan kaki di rute yang
        # sama menunggu timeout satu-satu kalau OSRM sedang tidak bisa dihubungi.
        _walking_path_disabled = True
        return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def driving_estimate(origin: Tuple[float, float], dest: Tuple[float, float],
                     when: Optional[datetime] = None) -> dict:
    """
    Estimasi kendaraan pribadi, dipakai saat di luar jam operasional angkutan umum.

    CATATAN KETERBATASAN: repo ini tidak punya jaringan jalan raya (graf hanya
    berisi 402 halte di koridor angkutan umum), jadi ini estimasi jarak & waktu,
    BUKAN rute belok-per-belok. Butuh data OSM untuk rute jalan sebenarnya.
    """
    data = get_data()
    straight_km = haversine_km(origin[0], origin[1], dest[0], dest[1])
    road_km = straight_km * ROAD_DETOUR_FACTOR

    speed = None
    if when is not None:
        speed = data.road_speed_by_hour.get(when.hour)
    if speed is None and data.road_speed_by_hour:
        speed = sum(data.road_speed_by_hour.values()) / len(data.road_speed_by_hour)
    if not speed:
        speed = FALLBACK_ROAD_SPEED_KMH
    speed *= PRIVATE_VEHICLE_SPEED_FACTOR

    return {
        "mode": "PRIVATE_VEHICLE",
        "distance_km": round(road_km, 2),
        "straight_line_km": round(straight_km, 2),
        "duration_minutes": round(road_km / speed * 60, 1),
        "assumed_speed_kmh": round(speed, 1),
        "is_estimate": True,
        "note": ("Estimasi jarak & waktu berdasarkan kecepatan jalan hasil survei "
                 "30 hari. Bukan rute belok-per-belok - sistem ini tidak memuat "
                 "jaringan jalan raya."),
    }


def demo():
    """Self-check: jalankan `python src/core/service_model.py`."""
    data = get_data()
    assert data.n_rows > 0, "tidak ada baris survei yang terbaca"
    assert data.by_hour, "lookup per-jam kosong"

    # Waktu tempuh nyata harus berbeda antar jam (pola jam sibuk).
    k1 = ("Feeder Koridor 1", "1", "2", 7)
    k2 = ("Feeder Koridor 1", "1", "2", 13)
    assert k1 in data.by_hour and k2 in data.by_hour, "ruas contoh tidak ada"
    assert data.by_hour[k1] > data.by_hour[k2], "jam sibuk harusnya lebih lambat"

    # Ruas tanpa cakupan survei tetap dapat angka (fallback rumus).
    t = travel_minutes("Feeder Koridor 1", "Feeder_Koridor_1_999",
                       "Feeder_Koridor_1_998", 2.0, datetime(2026, 1, 1, 8))
    assert t > 0, "fallback rumus gagal"

    # Waktu tunggu = headway penuh sesuai WAIT_MODEL.
    assert wait_minutes("Feeder Koridor 1") == 30.0
    assert wait_minutes("LRT Sumsel") == 17.0
    assert wait_minutes("Walking") == 0.0

    # Jam operasional.
    assert is_in_service("Feeder Koridor 1", datetime(2026, 1, 1, 8, 0))
    assert not is_in_service("Feeder Koridor 1", datetime(2026, 1, 1, 3, 0))
    assert not any_service_available(datetime(2026, 1, 1, 3, 0))
    assert any_service_available(datetime(2026, 1, 1, 8, 0))

    # Estimasi kendaraan pribadi.
    est = driving_estimate((-2.9852, 104.7328), (-2.9511, 104.7609),
                           datetime(2026, 1, 1, 3, 0))
    assert est["duration_minutes"] > 0 and est["distance_km"] > 0

    print(f"OK - {data.n_rows:,} baris survei, "
          f"{len(data.by_hour):,} lookup per-jam, "
          f"{len(data.by_edge):,} ruas")
    print(f"   jam 07 vs 13 pada Feeder K1 ruas 1->2: "
          f"{data.by_hour[k1]:.2f} vs {data.by_hour[k2]:.2f} menit")
    print(f"   estimasi kendaraan pribadi: {est['distance_km']} km, "
          f"{est['duration_minutes']} menit @ {est['assumed_speed_kmh']} km/h")


if __name__ == "__main__":
    demo()
