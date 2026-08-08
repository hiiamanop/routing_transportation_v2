"""
Service Model - waktu tempuh nyata, waktu tunggu, dan jam operasional.

Menggantikan traffic_aware.py, yang mencari file traffic_stats_aggregated.json
yang tidak pernah ada di repo ini sehingga selalu jatuh ke tebakan 12/20 km/h.
Modul ini membaca langsung dari data survei yang memang ada di dataset/.

Sumber data:
- dataset/traffic_30days/*.csv        : survei 30 hari, dipakai utk kecepatan
                                        rata-rata kendaraan pribadi per jam
- dataset/lrt/jadwal_lrt_palembang_*.csv : jadwal resmi LRT lengkap (~47
                                        perjalanan/arah, 1 Januari 2026)

ASUMSI YANG DIDEKLARASIKAN (tidak berasal dari data penelitian ini):
headway armada TIDAK ADA di dataset manapun. Angka di HEADWAY_MINUTES berasal
dari sumber sekunder (internet) dan BELUM DISITASI - lengkapi rujukannya
sebelum dipakai di naskah. Survei 30 hari mencatat waktu TEMPUH, bukan
FREKUENSI kendaraan: ke-480 keberangkatan di CSV semuanya tepat pada detik :00
di awal jam, yang berarti itu jadwal surveyor, bukan jadwal armada.
"""

import bisect
import csv
import glob
import math
import os
from collections import defaultdict
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent.parent
TRAFFIC_GLOB = str(_ROOT / "dataset" / "traffic_30days" / "*.csv")
# Jadwal resmi lengkap (semua ~47 perjalanan/arah, 1 Januari 2026) -- lebih
# representatif drpd jadwal.csv lama yg cuma catat trip pertama & terakhir.
# Key = label arah, dipakai jg utk cari jadwal keberangkatan per stasiun.
LRT_DIRECTION_FILES = {
    "BANDARA_DJKA": str(_ROOT / "dataset" / "lrt" / "jadwal_lrt_palembang_bandara_djka.csv"),
    "DJKA_BANDARA": str(_ROOT / "dataset" / "lrt" / "jadwal_lrt_palembang_djka_bandara.csv"),
}

# --- Asumsi headway (menit antar kendaraan di rute yang sama) --------------
# SUMBER: sekunder (update dari pemilik penelitian: Feeder 12 menit, Teman Bus
# 15 menit), bukan survei primer penelitian ini. TODO: sitasi kalau ada data
# headway hasil survei sendiri.
# LRT TIDAK pakai ini lagi utk perhitungan nyata -- sekarang kita punya jadwal
# resmi lengkap (~47 trip/arah), jadi waktu tunggu LRT dihitung dari selisih
# ke keberangkatan terdekat sesudah waktu tiba penumpang (lihat
# _lrt_schedule_wait). Angka 17 di sini cuma fallback kalau lookup jadwal
# gagal (mis. data hilang).
HEADWAY_MINUTES = {
    "FEEDER_ANGKOT": 12.0,
    "TEMAN_BUS": 15.0,
    "LRT": 17.0,
}

# --- Skor kenyamanan & keandalan per moda (fitur "preferensi pengguna") ----
# SUMBER: editorial, BUKAN data survei/pengukuran -- tidak ada data kenyamanan
# atau keandalan primer di dataset manapun. Skala 1-5, sama dgn skala Likert
# yg diisi pengguna di halaman preferensi. LRT dinilai paling andal krn
# satu-satunya moda dgn jadwal resmi nyata (_lrt_schedule_wait di bawah);
# Feeder Angkot dinilai paling rendah keandalannya krn angkutan informal tanpa
# data headway riil (sama spt disclaimer HEADWAY_MINUTES di atas). TODO:
# ganti dgn data survei kepuasan penumpang kalau tersedia.
COMFORT_SCORE = {
    "LRT": 5.0, "TEMAN_BUS": 3.5, "FEEDER_ANGKOT": 2.0,
    "WALK": 2.5, "PRIVATE_VEHICLE": 4.0,
}
RELIABILITY_SCORE = {
    "LRT": 5.0, "TEMAN_BUS": 3.5, "FEEDER_ANGKOT": 2.0,
    "WALK": 4.5, "PRIVATE_VEHICLE": 3.0,
}
TRANSFER_COMFORT_PENALTY = 0.3  # poin dikurangi dari skor kenyamanan per transfer

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
# Fallback KALAU OSRM gagal/timeout: jarak garis lurus dikali faktor ini
# utk memperkirakan jarak jalan. Kalau OSRM berhasil, jarak JALAN NYATA
# dari OSRM dipakai langsung (biasanya lebih jauh & lebih akurat dari ini).
ROAD_DETOUR_FACTOR = 1.3
# Kecepatan motor efektif di lalu lintas kota (BUKAN kecepatan jalan bebas
# hambatan) -- dipakai utk menghitung waktu tempuh dari JARAK JALAN (dari
# OSRM atau fallback di atas). Sengaja TIDAK memakai durasi bawaan OSRM:
# profil "driving" OSRM demo mengasumsikan jalan lengang sesuai batas
# kecepatan (~50+ km/jam utk jalan kota), jauh lebih optimis dari kondisi
# macet nyata. Knob kalibrasi: turunkan kalau estimasi masih terasa
# terlalu cepat dibanding kenyataan lapangan.
PRIVATE_VEHICLE_PEAK_KMH = 20.0
PRIVATE_VEHICLE_OFFPEAK_KMH = 28.0
# Biaya bahan bakar motor: ~40 km/liter, harga BBM ~Rp10.000/liter -> Rp250/km.
# Motor dipilih sbg acuan (bukan mobil) krn itu kendaraan pribadi dominan di
# konteks penelitian ini -- lihat RENCANA_SISTEM.md soal kepemilikan kendaraan.
# Knob kalibrasi: sesuaikan kalau harga BBM/konsumsi berubah.
MOTORBIKE_FUEL_COST_PER_KM = 250

# --- Kecepatan tetap Feeder & Teman Bus, per jam sibuk/normal --------------
# Survei per-jam ternyata berlubang (banyak ruas cuma punya data 1 arah/1 jam),
# sehingga waktu tempuh jam sibuk vs normal sering keluar identik. Ketetapan
# pemilik penelitian (2026-07-30): patok langsung kecepatannya, jangan lagi
# bergantung pada data per-jam. LRT TIDAK memakai ini -- rel sendiri, tidak
# kena macet, tetap statis dari jadwal resmi (headway 17 menit yang menandai
# jam sibuk, bukan kecepatannya).
PEAK_WINDOWS = [
    (time(7, 0), time(9, 0)),    # berangkat kerja/sekolah
    (time(12, 0), time(14, 0)),  # 
    (time(16, 0), time(19, 0)),  # pulang kerja
]
PEAK_SPEED_KMH = 25.0
OFFPEAK_SPEED_KMH = 32.5


def is_peak_hour(when: datetime) -> bool:
    t = when.time()
    return any(start <= t <= end for start, end in PEAK_WINDOWS)

LRT_NAME_TO_LOCAL = {
    'Bandara': '5', 'Asrama Haji': '6', 'Punti Kayu': '1', 'RSUD': '2',
    'Garuda Dempo': '3', 'Demang': '4', 'Bumi Sriwijaya': '7', 'Dishub': '8',
    'Cinde': '9', 'Ampera': '10', 'Polresta': '11', 'Jakabaring': '12', 'DJKA': '13',
}

# Dipakai kalau ruas LRT tidak ada di jadwal resmi sama sekali.
LRT_FALLBACK_SPEED_KMH = 40.0


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
        # (route, from_local, to_local) -> mean menit. Cuma diisi utk LRT
        # (dari jadwal resmi) -- Feeder & Teman Bus pakai PEAK_SPEED_KMH /
        # OFFPEAK_SPEED_KMH langsung, bukan lagi data survei per-ruas.
        self.by_edge: Dict[Tuple[str, str, str], float] = {}
        # hour -> mean effective_speed_kmh se-kota (untuk kendaraan pribadi)
        self.road_speed_by_hour: Dict[int, float] = {}
        # (from_local, to_local) -> label arah ("BANDARA_DJKA"/"DJKA_BANDARA"),
        # dipakai wait_minutes utk tau jadwal keberangkatan mana yg relevan.
        self.lrt_direction: Dict[Tuple[str, str], str] = {}
        # (label arah, station_local) -> menit-sejak-tengah-malam tiap
        # keberangkatan LRT dari stasiun itu, terurut menaik.
        self.lrt_departures: Dict[Tuple[str, str], List[int]] = {}
        self.loaded = False
        self.n_rows = 0

    def load(self):
        if self.loaded:
            return self
        spd_sums, spd_counts = defaultdict(float), defaultdict(int)

        for path in glob.glob(TRAFFIC_GLOB):
            with open(path, newline="") as f:
                for row in csv.DictReader(f):
                    try:
                        hour = int(row["departure_time"][:2])
                        speed = float(row["effective_speed_kmh"])
                    except (ValueError, KeyError):
                        continue
                    self.n_rows += 1
                    spd_sums[hour] += speed
                    spd_counts[hour] += 1

        self.road_speed_by_hour = {h: spd_sums[h] / spd_counts[h] for h in spd_sums}

        pair_times, direction, departures = _load_lrt_schedule()
        for (a, b), minutes in pair_times.items():
            self.by_edge[("LRT Sumsel", a, b)] = minutes
        self.lrt_direction = direction
        self.lrt_departures = departures

        self.loaded = True
        return self


# Header CSV jadwal lengkap tidak selalu eja nama stasiun sama persis dgn
# LRT_NAME_TO_LOCAL (mis. "B. SRIWIJAYA" vs "BUMI SRIWIJAYA") -- normalkan.
_LRT_HEADER_ALIAS = {
    "BANDARA": "Bandara", "ASRAMA HAJI": "Asrama Haji", "PUNTI KAYU": "Punti Kayu",
    "RSUD": "RSUD", "GARUDA DEMPO": "Garuda Dempo", "DEMANG": "Demang",
    "B. SRIWIJAYA": "Bumi Sriwijaya", "BUMI SRIWIJAYA": "Bumi Sriwijaya",
    "DISHUB": "Dishub", "CINDE": "Cinde", "AMPERA": "Ampera",
    "POLRESTA": "Polresta", "JAKABARING": "Jakabaring", "DJKA": "DJKA",
}


def _parse_hhmm(t: str) -> int:
    h, m = t.strip().split(":")
    return int(h) * 60 + int(m)


def _load_lrt_schedule() -> Tuple[Dict[Tuple[str, str], float],
                                  Dict[Tuple[str, str], str],
                                  Dict[Tuple[str, str], List[int]]]:
    """
    Baca kedua file jadwal resmi lengkap (~47 trip/arah, 1 Januari 2026).
    Return 3 hal sekaligus (satu pembacaan file, bukan reuse dua kali):

    - pair_times: (from_local, to_local) -> rata-rata menit antar stasiun
      bersebelahan, dari SELURUH trip (bukan cuma pertama & terakhir spt
      jadwal.csv lama) -- dipakai travel_minutes LRT.
    - direction:  (from_local, to_local) -> label arah file asalnya --
      dipakai wait_minutes utk tau jadwal keberangkatan mana yg relevan.
    - departures: (label arah, station_local) -> daftar menit-sejak-tengah-
      malam tiap keberangkatan dari stasiun itu, terurut menaik -- dipakai
      wait_minutes utk cari keberangkatan terdekat sesudah waktu tiba
      penumpang (bukan lagi asumsi headway tetap).
    """
    pair_time_samples = defaultdict(list)
    direction: Dict[Tuple[str, str], str] = {}
    departures = defaultdict(list)

    for label, path in LRT_DIRECTION_FILES.items():
        if not os.path.exists(path):
            continue
        with open(path, newline="") as f:
            rows = list(csv.reader(f))
        locals_ = [LRT_NAME_TO_LOCAL[_LRT_HEADER_ALIAS[h.strip().upper()]]
                  for h in rows[0][1:]]
        for row in rows[1:]:
            if not row or not row[0].strip():
                continue
            minutes_row = [_parse_hhmm(t) if t.strip() else None for t in row[1:]]

            for local, minute in zip(locals_, minutes_row):
                if minute is not None:
                    departures[(label, local)].append(minute)

            for i in range(len(locals_) - 1):
                m1, m2 = minutes_row[i], minutes_row[i + 1]
                if m1 is None or m2 is None:
                    continue
                diff = m2 - m1
                if diff <= 0:
                    continue  # data janggal (salah ketik di jadwal sumber), abaikan
                pair_time_samples[(locals_[i], locals_[i + 1])].append(diff)
                direction[(locals_[i], locals_[i + 1])] = label

    pair_times = {k: sum(v) / len(v) for k, v in pair_time_samples.items()}
    for key in departures:
        departures[key].sort()
    return pair_times, direction, dict(departures)


def _lrt_schedule_wait(from_stop_id: str, to_stop_id: str, when: datetime) -> Optional[float]:
    """
    Menit tunggu = selisih ke keberangkatan LRT terdekat sesudah `when` di
    stasiun asal, dari jadwal resmi lengkap. None kalau arah/stasiun tidak
    dikenal atau sudah lewat trip terakhir hari itu -- pemanggil fallback ke
    HEADWAY_MINUTES.
    """
    data = get_data()
    frm, to = local_of_stop_id(from_stop_id), local_of_stop_id(to_stop_id)
    label = data.lrt_direction.get((frm, to))
    if label is None:
        return None
    departures = data.lrt_departures.get((label, frm))
    if not departures:
        return None
    now_min = when.hour * 60 + when.minute
    idx = bisect.bisect_left(departures, now_min)
    if idx >= len(departures):
        return None
    return float(departures[idx] - now_min)


_data: Optional[_ServiceData] = None


def get_data() -> _ServiceData:
    global _data
    if _data is None:
        _data = _ServiceData().load()
    return _data


def travel_minutes(route: str, from_stop_id: str, to_stop_id: str,
                   distance_km: float, when: Optional[datetime] = None) -> float:
    """
    Waktu tempuh satu ruas.

    LRT: statis dari jadwal resmi (rel sendiri, tidak kena macet) -- lihat
    _load_lrt_times(). Jarak antar-stasiun nyata cuma 2-8 menit; headway
    (17 menit) adalah waktu TUNGGU sekali naik, bukan ditambahkan per stasiun.

    Feeder & Teman Bus: kecepatan tetap sesuai jam (lihat PEAK_WINDOWS) --
    data survei per-jam ditinggalkan krn cakupannya berlubang (banyak ruas
    cuma py data 1 arah/1 jam), sehingga waktu tempuh jam sibuk vs normal
    sering keluar identik.
    """
    if mode_of_route(route) == "LRT":
        data = get_data()
        frm, to = local_of_stop_id(from_stop_id), local_of_stop_id(to_stop_id)
        hit = data.by_edge.get((route, frm, to))
        if hit is not None:
            return hit
        hit = data.by_edge.get((route, to, frm))
        if hit is not None:
            return hit
        return distance_km / LRT_FALLBACK_SPEED_KMH * 60

    speed = PEAK_SPEED_KMH if (when is not None and is_peak_hour(when)) else OFFPEAK_SPEED_KMH
    return distance_km / speed * 60


def wait_minutes(route: str, from_stop_id: Optional[str] = None,
                 to_stop_id: Optional[str] = None,
                 when: Optional[datetime] = None) -> float:
    """
    Waktu tunggu saat naik kendaraan ini. Nol untuk jalan kaki.

    LRT: selisih ke keberangkatan terdekat SESUDAH `when` di jadwal resmi
    (0-17 menit tergantung kapan penumpang tiba, bukan selalu headway penuh)
    -- krn kita sekarang punya jadwal lengkap semua trip, tidak perlu lagi
    menebak pakai headway rata-rata. Turun ke HEADWAY_MINUTES kalau
    from_stop_id/to_stop_id/when tidak diberikan atau lookup jadwal gagal.
    """
    mode = mode_of_route(route)
    if mode == "LRT" and from_stop_id and to_stop_id and when is not None:
        sched_wait = _lrt_schedule_wait(from_stop_id, to_stop_id, when)
        if sched_wait is not None:
            return sched_wait

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
import time as _time
import urllib.request as _req

OSRM_BASE = "https://router.project-osrm.org/route/v1"
WALKING_PATH_TIMEOUT_SECONDS = 3.0
# ponytail: OSRM demo publik, bukan server sendiri -- tidak ada SLA. Kalau
# ini jadi sumber error/lambat di produksi, ganti ke OSRM self-hosted atau
# naikkan timeout. Gagal/timeout SELALU fallback diam-diam ke garis lurus,
# jadi tidak pernah membuat pencarian rute gagal total.
#
# Cooldown, BUKAN mati permanen: proses API ini hidup berhari-hari (Flask
# tidak restart tiap request), jadi kalau satu kegagalan/timeout OSRM yang
# transient mematikan flag ini selamanya, SEMUA request sesudahnya di sisa
# umur proses itu kehilangan jalur OSRM tanpa pernah coba lagi -- padahal
# OSRM-nya sendiri sudah pulih detik berikutnya. Ditemukan lewat kejadian
# nyata (2026-08-08): satu blip saat pengujian bertubi-tubi bikin SEMUA
# request sesudahnya (termasuk punya pengguna asli) balik ke garis lurus.
_OSRM_COOLDOWN_SECONDS = 30.0
_osrm_disabled_until: float = 0.0  # monotonic timestamp, 0 = tidak sedang cooldown
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


def _osrm_route(profile: str, from_lat: float, from_lon: float,
                to_lat: float, to_lon: float) -> Optional[dict]:
    """
    Panggil OSRM (dipakai bareng oleh walking_path & driving_route -- profil
    beda, mekanisme sama). Return {"path": [[lat,lon],...], "distance_km":}
    atau None kalau OSRM gagal/timeout -- pemanggil harus fallback sendiri
    (garis lurus [from, to] utk path, haversine utk jarak).
    """
    global _osrm_disabled_until
    if _time.monotonic() < _osrm_disabled_until:
        return None
    url = (f"{OSRM_BASE}/{profile}/{from_lon},{from_lat};{to_lon},{to_lat}"
          f"?overview=full&geometries=geojson")
    try:
        with _req.urlopen(url, timeout=WALKING_PATH_TIMEOUT_SECONDS, context=_ssl_context()) as resp:
            data = _json.loads(resp.read())
        if data.get("code") != "Ok":
            return None
        route = data["routes"][0]
        return {
            "path": [[c[1], c[0]] for c in route["geometry"]["coordinates"]],
            "distance_km": route["distance"] / 1000,
        }
    except Exception:
        # Satu kegagalan (mis. timeout/offline) menunda SEMUA panggilan OSRM
        # (WALK & PRIVATE_VEHICLE berbagi cooldown ini) selama
        # _OSRM_COOLDOWN_SECONDS -- jangan bikin SETIAP request menunggu
        # timeout satu-satu selama OSRM benar2 tidak bisa dihubungi, tapi
        # tetap coba lagi otomatis sesudah cooldown, bukan mati permanen.
        _osrm_disabled_until = _time.monotonic() + _OSRM_COOLDOWN_SECONDS
        return None


def walking_path(from_lat: float, from_lon: float,
                 to_lat: float, to_lon: float) -> Optional[list]:
    """Polyline jalan kaki asli dari OSRM (profil foot), sbg list [lat, lon]
    (format yang sama dengan route_waypoints koridor transit). None kalau
    OSRM gagal/timeout -- pemanggil harus fallback ke garis lurus [from, to]."""
    route = _osrm_route("foot", from_lat, from_lon, to_lat, to_lon)
    return route["path"] if route else None


def driving_route(from_lat: float, from_lon: float,
                  to_lat: float, to_lon: float) -> Optional[dict]:
    """
    Jarak & polyline jalan NYATA dari OSRM (profil driving) -- utk kendaraan
    pribadi. SENGAJA tidak memakai durasi bawaan OSRM (lihat komentar
    PRIVATE_VEHICLE_PEAK_KMH), cuma jarak & geometrinya. None kalau OSRM
    gagal/timeout -- pemanggil fallback ke haversine x ROAD_DETOUR_FACTOR.
    """
    return _osrm_route("driving", from_lat, from_lon, to_lat, to_lon)


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
    Estimasi kendaraan pribadi -- dipakai sbg alternatif pembanding di
    find_route_alternatives() DAN saat di luar jam operasional angkutan umum.

    Jarak & polyline: dari OSRM (jalan NYATA), fallback ke garis lurus x
    ROAD_DETOUR_FACTOR kalau OSRM gagal/timeout. Waktu tempuh: dihitung
    sendiri dari kecepatan motor efektif (PEAK/OFFPEAK), BUKAN dari durasi
    bawaan OSRM -- lihat komentar PRIVATE_VEHICLE_PEAK_KMH kenapa.
    """
    straight_km = haversine_km(origin[0], origin[1], dest[0], dest[1])

    route = driving_route(origin[0], origin[1], dest[0], dest[1])
    if route is not None:
        road_km = route["distance_km"]
        path = route["path"]
    else:
        road_km = straight_km * ROAD_DETOUR_FACTOR
        path = None

    speed = (PRIVATE_VEHICLE_PEAK_KMH if (when is not None and is_peak_hour(when))
             else PRIVATE_VEHICLE_OFFPEAK_KMH)
    road_km = round(road_km, 2)  # bulatkan dulu -- duration/cost dihitung dari
                                  # angka yg SAMA persis dgn yg ditampilkan sbg distance_km

    return {
        "mode": "PRIVATE_VEHICLE",
        "distance_km": road_km,
        "straight_line_km": round(straight_km, 2),
        "duration_minutes": round(road_km / speed * 60, 1),
        "cost_rupiah": round(road_km * MOTORBIKE_FUEL_COST_PER_KM),
        "assumed_speed_kmh": round(speed, 1),
        "path": path,
        "is_estimate": True,
        "note": ("Jarak & jalur dari OSRM (kalau tersedia) atau estimasi garis lurus. "
                 "Waktu tempuh pakai asumsi kecepatan motor efektif di lalu lintas "
                 "kota (bukan durasi bawaan OSRM, yg mengasumsikan jalan lengang). "
                 "Biaya = estimasi BBM motor saja, tidak termasuk parkir/penyusutan."),
    }


def demo():
    """Self-check: jalankan `python src/core/service_model.py`."""
    data = get_data()
    assert data.n_rows > 0, "tidak ada baris survei yang terbaca"

    # Feeder/Teman Bus: kecepatan tetap, jam sibuk harus lebih lambat.
    # Jam 22:00 dipakai sbg acuan "normal" krn genuinely di luar SEMUA
    # jendela PEAK_WINDOWS (07-09, 12-14 , 16-19) --
    # dulu dipakai jam 13:00, sekarang itu masuk jendela siang yang baru.
    peak = travel_minutes("Feeder Koridor 1", "Feeder_Koridor_1_1",
                          "Feeder_Koridor_1_2", 5.0, datetime(2026, 1, 1, 8))
    normal = travel_minutes("Feeder Koridor 1", "Feeder_Koridor_1_1",
                            "Feeder_Koridor_1_2", 5.0, datetime(2026, 1, 1, 22))
    siang = travel_minutes("Feeder Koridor 1", "Feeder_Koridor_1_1",
                           "Feeder_Koridor_1_2", 5.0, datetime(2026, 1, 1, 13))
    assert peak > normal, "jam sibuk harusnya lebih lambat"
    assert peak == 5.0 / PEAK_SPEED_KMH * 60
    assert normal == 5.0 / OFFPEAK_SPEED_KMH * 60
    assert siang == peak, "jam 13:00 () harusnya sama lambatnya dgn jam sibuk"

    # LRT statis -- sama jam sibuk atau tidak, pakai jadwal resmi.
    lrt_peak = travel_minutes("LRT Sumsel", "LRT_Sumsel_1", "LRT_Sumsel_2",
                              3.0, datetime(2026, 1, 1, 8))
    lrt_normal = travel_minutes("LRT Sumsel", "LRT_Sumsel_1", "LRT_Sumsel_2",
                                3.0, datetime(2026, 1, 1, 22))
    assert lrt_peak == lrt_normal, "LRT harusnya tidak berubah krn jam sibuk"

    # Feeder/Teman Bus: masih headway penuh sesuai WAIT_MODEL (tidak ada
    # jadwal resmi utk moda ini).
    assert wait_minutes("Feeder Koridor 1") == 12.0
    assert wait_minutes("Walking") == 0.0

    # LRT: tunggu = selisih ke jadwal terdekat SESUDAH waktu tiba (bukan
    # headway tetap lagi). Punti Kayu(1) -> RSUD(2) pakai jadwal arah
    # BANDARA_DJKA.
    punti_kayu_departures = data.lrt_departures[("BANDARA_DJKA", "1")]
    first_dep = punti_kayu_departures[0]
    h, m = divmod(first_dep - 4, 60)
    tiba_4_menit_sblm = datetime(2026, 1, 1, h, m)
    wait = wait_minutes("LRT Sumsel", "LRT_Sumsel_1", "LRT_Sumsel_2", tiba_4_menit_sblm)
    assert wait == 4.0, f"harusnya nunggu 4 menit ke jadwal berikutnya, dpt {wait}"

    # Tanpa konteks jadwal (stop_id/when tak diberikan) -> fallback headway.
    assert wait_minutes("LRT Sumsel") == 17.0

    # Jam operasional.
    assert is_in_service("Feeder Koridor 1", datetime(2026, 1, 1, 8, 0))
    assert not is_in_service("Feeder Koridor 1", datetime(2026, 1, 1, 3, 0))
    assert not any_service_available(datetime(2026, 1, 1, 3, 0))
    assert any_service_available(datetime(2026, 1, 1, 8, 0))

    # Estimasi kendaraan pribadi -- jam 03:00 = offpeak.
    est = driving_estimate((-2.9852, 104.7328), (-2.9511, 104.7609),
                           datetime(2026, 1, 1, 3, 0))
    assert est["duration_minutes"] > 0 and est["distance_km"] > 0
    assert est["cost_rupiah"] == round(est["distance_km"] * MOTORBIKE_FUEL_COST_PER_KM)
    assert est["assumed_speed_kmh"] == PRIVATE_VEHICLE_OFFPEAK_KMH

    est_peak = driving_estimate((-2.9852, 104.7328), (-2.9511, 104.7609),
                                datetime(2026, 1, 1, 8, 0))
    assert est_peak["assumed_speed_kmh"] == PRIVATE_VEHICLE_PEAK_KMH
    assert est_peak["duration_minutes"] > est["duration_minutes"], \
        "jam sibuk harusnya lebih lambat drpd offpeak"

    print(f"OK - {data.n_rows:,} baris survei, {len(data.by_edge):,} ruas LRT")
    print(f"   Feeder K1 5km jam 08 vs 22: {peak:.2f} vs {normal:.2f} menit (jam 13 siang: {siang:.2f}, sama sibuknya)")
    print(f"   LRT Punti Kayu->RSUD jam 08 vs 22: {lrt_peak:.2f} vs {lrt_normal:.2f} menit (statis)")
    print(f"   estimasi kendaraan pribadi: {est['distance_km']} km, "
          f"{est['duration_minutes']} menit @ {est['assumed_speed_kmh']} km/h")


if __name__ == "__main__":
    demo()
