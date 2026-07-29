#!/usr/bin/env python3
"""
Generate road-following waypoints for every corridor route.

Kenapa: frontend (MapComponent.tsx) & endpoint /api/route/waypoints/<route>
sudah bisa menggambar polyline detail per koridor lewat key "route_waypoints"
di network_data_correct_bidirectional.json -- tapi cuma 2 dari 11 koridor
(Feeder 5 & 7) yang datanya ada, sisanya jatuh ke garis lurus antar halte.
Skrip ini melengkapi 9 koridor yang tersisa.

Sumber geometri:
- Feeder & Teman Bus: OSRM demo server (profil "driving"), disambung per
  pasangan halte berurutan -- ini kendaraan roda yang lewat jalan raya.
- LRT: LineString asli dari dataset/kmz_file/Peta LRT/Rute LRT.kmz (rel
  kereta, BUKAN jalan raya -- OSRM driving akan salah nebak lewat jalan).

ponytail: pakai OSRM demo publik (router.project-osrm.org), bukan server
sendiri -- cukup untuk precompute SEKALI ini, tapi tidak ada SLA. Kalau
data ini perlu di-refresh rutin, pertimbangkan self-host OSRM.

Cara pakai: python3 scripts/generate_road_waypoints.py
"""
import json
import ssl
import sys
import time
import urllib.request
import urllib.error
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
NETWORK_PATH = ROOT / "dataset" / "network_data_correct_bidirectional.json"
LRT_KMZ = ROOT / "dataset" / "kmz_file" / "Peta LRT" / "Rute LRT.kmz"

OSRM_BASE = "https://router.project-osrm.org/route/v1"

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    # Tanpa certifi: urlopen pakai default (bisa gagal CERTIFICATE_VERIFY_FAILED
    # di beberapa instalasi Python macOS) -- kalau itu terjadi: pip install certifi.
    SSL_CONTEXT = None
REQUEST_DELAY_SECONDS = 0.3  # sopan ke server demo publik
REQUEST_TIMEOUT_SECONDS = 10


def local_seq(stop_id: str) -> int:
    """'Feeder_Koridor_1_23' -> 23, dipakai untuk urut halte sepanjang koridor."""
    return int(stop_id.rsplit("_", 1)[-1])


def osrm_road_segment(lon1, lat1, lon2, lat2, profile="driving"):
    """
    Polyline jalan asli antara dua titik, sbg list [lat, lon] (format yang
    SAMA dgn 2 entri route_waypoints yang sudah ada -- frontend membaca
    wp[0]/wp[1] sbg array, bukan dict). None kalau gagal (fallback ke garis lurus).
    """
    url = (f"{OSRM_BASE}/{profile}/{lon1},{lat1};{lon2},{lat2}"
          f"?overview=full&geometries=geojson")
    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS, context=SSL_CONTEXT) as resp:
            data = json.loads(resp.read())
        if data.get("code") != "Ok":
            return None
        return [[c[1], c[0]] for c in data["routes"][0]["geometry"]["coordinates"]]
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
        return None


def build_corridor_waypoints(stops: list) -> list:
    """Sambungkan polyline OSRM antar halte berurutan jadi satu rute utuh."""
    full_path = [[stops[0]["lat"], stops[0]["lon"]]]
    n_ok, n_fallback = 0, 0
    for i in range(len(stops) - 1):
        a, b = stops[i], stops[i + 1]
        seg = osrm_road_segment(a["lon"], a["lat"], b["lon"], b["lat"])
        time.sleep(REQUEST_DELAY_SECONDS)
        if seg:
            full_path.extend(seg[1:])  # buang titik pertama, sudah ada
            n_ok += 1
        else:
            full_path.append([b["lat"], b["lon"]])  # fallback lurus
            n_fallback += 1
    return full_path, n_ok, n_fallback


def extract_lrt_linestring() -> list:
    """LineString rel kereta dari KMZ resmi -- lebih akurat dari OSRM driving."""
    with zipfile.ZipFile(LRT_KMZ) as z:
        kml = z.read("doc.kml").decode("utf-8", errors="replace")
    root = ET.fromstring(kml)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    linestring = root.find(".//kml:LineString/kml:coordinates", ns)
    points = []
    for coord in linestring.text.strip().split():
        lon, lat, *_ = coord.split(",")
        points.append([float(lat), float(lon)])
    return points


def main():
    network = json.loads(NETWORK_PATH.read_text(encoding="utf-8"))
    route_waypoints = network.setdefault("route_waypoints", {})

    all_routes = sorted(set(n["route"] for n in network["nodes"]))
    todo = [r for r in all_routes if r not in route_waypoints]
    print(f"Koridor yang sudah ada waypoints: {len(all_routes) - len(todo)}/{len(all_routes)}")
    print(f"Koridor yang akan diproses: {todo}\n")

    for route in todo:
        if route == "LRT Sumsel":
            print(f"[{route}] pakai LineString rel kereta asli dari KMZ...")
            points = extract_lrt_linestring()
            route_waypoints[route] = points
            print(f"  -> {len(points)} titik (dari file resmi, bukan OSRM)\n")
            continue

        stops = sorted(
            [n for n in network["nodes"] if n["route"] == route],
            key=lambda n: local_seq(n["stop_id"]),
        )
        print(f"[{route}] {len(stops)} halte, memanggil OSRM per pasangan berurutan...")
        points, n_ok, n_fallback = build_corridor_waypoints(stops)
        route_waypoints[route] = points
        print(f"  -> {len(points)} titik total ({n_ok} ruas dari OSRM, "
             f"{n_fallback} jatuh ke garis lurus)\n")

        # Simpan SETELAH tiap koridor (bukan cuma di akhir) -- ~350 panggilan
        # OSRM makan waktu beberapa menit, jangan sampai progres hilang kalau
        # proses terputus di tengah jalan.
        NETWORK_PATH.write_text(
            json.dumps(network, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Tersimpan ke {NETWORK_PATH}")
    print(f"Total koridor dgn waypoints sekarang: {len(route_waypoints)}/{len(all_routes)}")


if __name__ == "__main__":
    main()
