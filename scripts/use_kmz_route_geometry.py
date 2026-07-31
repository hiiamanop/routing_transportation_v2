#!/usr/bin/env python3
"""
Ganti waypoints tebakan OSRM dengan geometri rute ASLI dari KMZ, untuk koridor
yang KMZ-nya benar-benar berisi LineString (bukan cuma titik halte).

Ditemukan (2026-07-29): generate_road_waypoints.py sebelumnya memakai OSRM
untuk SEMUA koridor Feeder/Teman Bus, padahal ternyata 6 dari 8 KMZ Feeder +
1 dari 2 KMZ Teman Bus SUDAH berisi LineString hasil trace manual rute
sesungguhnya -- lebih akurat dari tebakan "jalan tercepat" OSRM, karena rute
angkot/bus riil belum tentu lewat jalan yang menurut OSRM paling optimal.
Bounding box LineString ini sudah dicek cocok persis dgn lokasi halte
masing-masing koridor.

Koridor 8 KMZ-nya rusak/terpecah jadi 5 LineString terpisah (kemungkinan
digambar ulang beberapa kali) -- skrip ini menyambungnya otomatis berdasar
titik ujung yang berdekatan (chaining bidireksional).

Koridor TANPA LineString di KMZ-nya (Feeder 1, Feeder 2, Teman Bus 2) TETAP
pakai hasil OSRM dari generate_road_waypoints.py -- tidak disentuh di sini.

Cara pakai: python3 scripts/use_kmz_route_geometry.py
"""
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from math import radians, sin, cos, sqrt, atan2

ROOT = Path(__file__).resolve().parent.parent
NETWORK_PATH = ROOT / "dataset" / "network_data_correct_bidirectional.json"
KMZ_DIR = ROOT / "dataset" / "kmz_file"

# route (sesuai field 'route' di graf) -> file KMZ yang punya LineString asli.
ROUTE_TO_KMZ = {
    "Feeder Koridor 3": KMZ_DIR / "Peta Angkot Feeder" / "Koridor 3 Feeder (Asrama Haji - Talang Betutu).kmz",
    "Feeder Koridor 4": KMZ_DIR / "Peta Angkot Feeder" / "Koridor 4 Feeder (Sta Polresta - Perum OPI).kmz",
    "Feeder Koridor 5": KMZ_DIR / "Peta Angkot Feeder" / "Koridor 5 Feeder (DJKA -Terminal Plaju).kmz",
    "Feeder Koridor 6": KMZ_DIR / "Peta Angkot Feeder" / "Koridor 6 Feeder (RSUD - Sukawitan).kmz",
    "Feeder Koridor 7": KMZ_DIR / "Peta Angkot Feeder" / "Koridor 7 Feeder (Stadion Kamboja - Bukit Siguntang).kmz",
    "Feeder Koridor 8": KMZ_DIR / "Peta Angkot Feeder" / "Koridor 8 (Asrama Haji - Talang Jambe) (1).kmz",
    "Teman Bus Koridor 5": KMZ_DIR / "Peta Teman Bus" / "Koridor 5.kmz",
}

CHAIN_THRESHOLD_KM = 0.15  # 150m -- ujung segmen dianggap "nyambung" kalau sedekat ini


def haversine_km(a, b):
    r = 6371.0
    lat1, lon1 = radians(a[0]), radians(a[1])
    lat2, lon2 = radians(b[0]), radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return r * 2 * atan2(sqrt(h), sqrt(1 - h))


def extract_linestrings(kmz_path: Path) -> list:
    """Semua LineString di file KMZ, sbg list of [(lat, lon), ...]."""
    with zipfile.ZipFile(kmz_path) as z:
        kml_name = [n for n in z.namelist() if n.endswith(".kml")][0]
        kml = z.read(kml_name).decode("utf-8", errors="replace")
    root = ET.fromstring(kml)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    segments = []
    for placemark in root.findall(".//kml:Placemark", ns):
        ls = placemark.find(".//kml:LineString/kml:coordinates", ns)
        if ls is None:
            continue
        coords = []
        for c in ls.text.strip().split():
            lon, lat, *_ = c.split(",")
            coords.append((float(lat), float(lon)))
        if coords:
            segments.append(coords)
    return segments


def dedupe_segments(segments: list) -> list:
    """
    Buang segmen yang cuma trace ULANG dari fisik jalan yang sama (kedua
    ujungnya berdekatan dengan segmen lain, tanpa peduli arah) -- ditemukan di
    Koridor 8 KMZ-nya, 5 segmen ternyata cuma 2 ruas fisik digambar berkali-kali.
    Kalau tidak dibuang, chaining akan menyambung banyak segmen ke titik ujung
    yang SAMA dan menghasilkan garis zigzag/bolak-balik di titik itu.
    Yang disimpan per kelompok duplikat: yang paling panjang (paling detail).
    """
    kept: list = []
    for seg in sorted(segments, key=len, reverse=True):
        is_dup = False
        for k in kept:
            same_dir = (haversine_km(seg[0], k[0]) <= CHAIN_THRESHOLD_KM and
                       haversine_km(seg[-1], k[-1]) <= CHAIN_THRESHOLD_KM)
            reversed_dir = (haversine_km(seg[0], k[-1]) <= CHAIN_THRESHOLD_KM and
                           haversine_km(seg[-1], k[0]) <= CHAIN_THRESHOLD_KM)
            if same_dir or reversed_dir:
                is_dup = True
                break
        if not is_dup:
            kept.append(seg)
    return kept


def chain_segments(segments: list) -> list:
    """
    Sambung beberapa LineString jadi satu rute utuh, berdasar titik ujung yang
    berdekatan (bidireksional -- bisa nyambung di depan ATAU belakang chain).
    Segmen yang tidak ketemu sambungannya (duplikat trace) dibuang.
    """
    segments = dedupe_segments(segments)
    if len(segments) == 1:
        return segments[0]

    remaining = sorted(segments, key=len, reverse=True)
    chain = list(remaining.pop(0))

    changed = True
    while changed and remaining:
        changed = False
        chain_start, chain_end = chain[0], chain[-1]
        best = None  # (idx, distance, attach_at, reverse)
        for i, seg in enumerate(remaining):
            candidates = [
                (haversine_km(chain_end, seg[0]), "end", False),
                (haversine_km(chain_end, seg[-1]), "end", True),
                (haversine_km(chain_start, seg[0]), "start", True),
                (haversine_km(chain_start, seg[-1]), "start", False),
            ]
            for dist, attach_at, reverse in candidates:
                if dist <= CHAIN_THRESHOLD_KM and (best is None or dist < best[1]):
                    best = (i, dist, attach_at, reverse)
        if best:
            i, _, attach_at, reverse = best
            seg = remaining.pop(i)
            if reverse:
                seg = list(reversed(seg))
            if attach_at == "end":
                chain.extend(seg[1:])
            else:
                chain = seg[:-1] + chain
            changed = True

    if remaining:
        print(f"    (peringatan: {len(remaining)} segmen tidak nyambung, "
             f"kemungkinan trace duplikat -- diabaikan)")
    return chain


def main():
    network = json.loads(NETWORK_PATH.read_text(encoding="utf-8"))
    route_waypoints = network.setdefault("route_waypoints", {})

    for route, kmz_path in ROUTE_TO_KMZ.items():
        if not kmz_path.exists():
            print(f"[{route}] SKIP: file KMZ tidak ada ({kmz_path.name})")
            continue
        segments = extract_linestrings(kmz_path)
        if not segments:
            print(f"[{route}] SKIP: tidak ada LineString di KMZ")
            continue

        before = len(route_waypoints.get(route, []))
        chained = chain_segments(segments)
        route_waypoints[route] = [[lat, lon] for lat, lon in chained]
        print(f"[{route}] {len(segments)} segmen KMZ -> {len(chained)} titik "
             f"(sebelumnya {before} titik dari OSRM)")

    NETWORK_PATH.write_text(
        json.dumps(network, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nTersimpan ke {NETWORK_PATH}")


if __name__ == "__main__":
    main()
