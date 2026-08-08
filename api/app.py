"""
Flask API sistem informasi integrasi antar moda Kota Palembang.

Menyediakan pencarian rute (Dijkstra), alternatif rute beserta atributnya,
dan perekaman pilihan pengguna sebagai data survei pemilihan moda.
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import sys
import os
from datetime import datetime, timezone, timedelta
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from algorithms.routing.data_loader import load_network_data
from core.gmaps_style_routing import (
    gmaps_style_route, find_route_alternatives, select_preferred_route, PREFERENCE_CRITERIA,
    describe_no_route_reason, route_attributes
)
from core import service_model
from core.survey_export import build_long_format_rows, rows_to_csv

app = Flask(__name__)
# Enable CORS for all routes with explicit configuration
CORS(app, 
     origins="*",
     methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
     allow_headers=["Content-Type", "Authorization"
     "", "X-Requested-With"],
     supports_credentials=False,
     max_age=3600)

@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS,PUT,DELETE')
    return response

# Global variable to store loaded network
network_graph = None

# GMT+7 timezone (WIB - Waktu Indonesia Barat)
WIB_TZ = timezone(timedelta(hours=7))

def parse_departure_time(time_str: str) -> datetime:
    """
    Parse departure time string to datetime with GMT+7 timezone
    
    Args:
        time_str: ISO format datetime string (e.g., "2025-01-01T10:00" or "2025-01-01T10:00:00")
    
    Returns:
        datetime object with GMT+7 timezone
    """
    if not time_str:
        return datetime.now(WIB_TZ)
    
    try:
        # Handle different formats
        if 'T' in time_str:
            # Remove 'Z' if present and add GMT+7
            if time_str.endswith('Z'):
                time_str = time_str[:-1] + '+07:00'
            elif '+' not in time_str[-6:] and '-' not in time_str[-6:]:
                # No timezone, assume GMT+7
                if len(time_str) == 16:  # YYYY-MM-DDTHH:mm
                    time_str = time_str + ':00+07:00'
                elif len(time_str) == 19:  # YYYY-MM-DDTHH:mm:ss
                    time_str = time_str + '+07:00'
                else:
                    time_str = time_str + '+07:00'
            
            dt = datetime.fromisoformat(time_str)
            # Ensure timezone is GMT+7
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=WIB_TZ)
            else:
                # Convert to GMT+7
                dt = dt.astimezone(WIB_TZ)
            return dt
        else:
            raise ValueError("Invalid format: missing 'T' separator")
    except ValueError as e:
        raise ValueError(f"Invalid departure_time format: {str(e)}")

def load_network():
    """Load network data once at startup"""
    global network_graph
    if network_graph is None:
        print("Loading network data...")
        network_graph = load_network_data("dataset/network_data_correct_bidirectional.json")
        print(f"Network loaded: {len(network_graph.stops)} stops, {len(network_graph.edges)} edges")
    return network_graph

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "Public Transport Routing API is running",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/network/info', methods=['GET'])
def network_info():
    """Get network information"""
    graph = load_network()
    
    # Count stops by mode
    mode_counts = {}
    for stop in graph.stops.values():
        mode = stop.mode.value
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
    
    return jsonify({
        "total_stops": len(graph.stops),
        "total_edges": len(graph.edges),
        "stops_by_mode": mode_counts,
        "modes": list(mode_counts.keys())
    })

def serialize_route(route, origin_name, destination_name, origin_coords=None, dest_coords=None):
    """Convert route object to JSON-serializable format"""
    return {
        "route_id": route.route_id,
        "origin": origin_name,
        "destination": destination_name,
        "summary": {
            "total_time_minutes": route.total_time_minutes,
            "total_cost": route.total_cost,
            "total_distance_km": route.total_distance_km,
            "num_transfers": route.num_transfers,
            "departure_time": route.segments[0].departure_time.isoformat(),
            "arrival_time": route.segments[-1].arrival_time.isoformat(),
        },
        "segments": [
            {
                "sequence": seg.sequence,
                "mode": seg.mode.value if hasattr(seg.mode, 'value') else str(seg.mode),
                "route_name": getattr(seg, 'route_name', 'Unknown'),
                "from_stop": seg.from_stop.name if hasattr(seg, 'from_stop') else 'Unknown',
                "to_stop": seg.to_stop.name if hasattr(seg, 'to_stop') else 'Unknown',
                "duration_minutes": seg.duration_minutes,
                "wait_minutes": getattr(seg, 'wait_minutes', 0.0),
                "travel_minutes": seg.duration_minutes - getattr(seg, 'wait_minutes', 0.0),
                "path": getattr(seg, 'path', None),
                "via_stops": getattr(seg, 'via_stops', []),
                "cost": seg.cost,
                "distance_km": seg.distance_km,
                "departure_time": seg.departure_time.isoformat(),
                "arrival_time": seg.arrival_time.isoformat(),
                # Koordinat langsung dari objek Stop milik segmen ini (bukan
                # dicari ulang lewat dict ber-kunci nama halte) -- beberapa
                # halte berbagi nama yang sama di koridor berbeda (mis. "BS
                # SPBU 24 ada" ada di Feeder Koridor 5 DAN 6, lokasi beda ~13km),
                # jadi lookup by-name dulu diam-diam bisa memberi koordinat
                # halte koridor lain yang salah.
                "from_coords": {
                    "lat": origin_coords[0] if seg.sequence == 1 and origin_coords else seg.from_stop.lat,
                    "lon": origin_coords[1] if seg.sequence == 1 and origin_coords else seg.from_stop.lon,
                },
                "to_coords": {
                    "lat": dest_coords[0] if seg.sequence == len(route.segments) and dest_coords else seg.to_stop.lat,
                    "lon": dest_coords[1] if seg.sequence == len(route.segments) and dest_coords else seg.to_stop.lon,
                }
            }
            for seg in route.segments
        ]
    }


@app.route('/api/route/alternatives', methods=['POST'])
def route_alternatives():
    """
    Beberapa opsi rute seperti Google Maps: tercepat, termurah, paling
    sedikit transfer. Memakai Dijkstra (mesin utama, hasil optimal terjamin)
    sebagai satu-satunya algoritma pencarian.

    Expected JSON payload sama seperti POST /api/route (tanpa field
    "algorithm" -- endpoint ini selalu memberi beberapa opsi sekaligus).
    """
    try:
        data = request.get_json()
        if not data or 'origin' not in data or 'destination' not in data:
            return jsonify({"error": "origin and destination are required"}), 400

        origin = data['origin']
        destination = data['destination']

        if not all(key in origin for key in ['lat', 'lon']):
            return jsonify({"error": "Origin must have lat and lon"}), 400
        if not all(key in destination for key in ['lat', 'lon']):
            return jsonify({"error": "Destination must have lat and lon"}), 400

        departure_time = datetime.now(WIB_TZ)
        if 'departure_time' in data and data['departure_time']:
            try:
                departure_time = parse_departure_time(data['departure_time'])
            except ValueError as e:
                return jsonify({"error": str(e)}), 400

        # Preferensi pengguna (opsional) -- skala 1-5 per kriteria, dipakai
        # utk menilai ulang alternatif yang sudah dihitung (bukan pencarian
        # baru). Divalidasi ketat krn ini input dari luar (trust boundary).
        preferences = None
        if 'preferences' in data and data['preferences'] is not None:
            raw_prefs = data['preferences']
            if not isinstance(raw_prefs, dict) or set(raw_prefs.keys()) != set(PREFERENCE_CRITERIA):
                return jsonify({
                    "error": f"preferences must have exactly these keys: {list(PREFERENCE_CRITERIA)}"
                }), 400
            try:
                preferences = {k: float(raw_prefs[k]) for k in PREFERENCE_CRITERIA}
            except (TypeError, ValueError):
                return jsonify({"error": "preferences values must be numbers"}), 400
            if any(v < 1 or v > 5 for v in preferences.values()):
                return jsonify({"error": "preferences values must be between 1 and 5"}), 400

        if not service_model.any_service_available(departure_time):
            estimate = service_model.driving_estimate(
                (origin['lat'], origin['lon']),
                (destination['lat'], destination['lon']),
                departure_time,
            )
            return jsonify({
                "success": True,
                "public_transport_available": False,
                "reason": (
                    f"Di luar jam operasional angkutan umum "
                    f"({departure_time.strftime('%H:%M')} WIB). "
                    f"Jam layanan: {service_model.service_window_text()}."
                ),
                "suggested_mode": "PRIVATE_VEHICLE",
                "private_vehicle": estimate,
                "origin": origin,
                "destination": destination,
                "departure_time": departure_time.isoformat(),
            }), 200

        graph = load_network()
        alternatives = find_route_alternatives(
            graph=graph,
            origin_name=origin.get('name', 'Origin'),
            origin_coords=(origin['lat'], origin['lon']),
            dest_name=destination.get('name', 'Destination'),
            dest_coords=(destination['lat'], destination['lon']),
            departure_time=departure_time,
        )

        if not alternatives:
            # Halte ada di kedua titik tapi jaringan transit tidak
            # menghubungkannya (atau titik terlalu jauh dari halte manapun) --
            # drpd berhenti di "no route found", tawarkan estimasi kendaraan
            # pribadi (sama persis pola & fungsi yg dipakai utk kasus di luar
            # jam operasional di atas) supaya user tetap dapat jawaban yang
            # bisa ditindaklanjuti, bukan jalan buntu.
            reason = describe_no_route_reason(
                graph, (origin['lat'], origin['lon']), (destination['lat'], destination['lon'])
            )
            estimate = service_model.driving_estimate(
                (origin['lat'], origin['lon']),
                (destination['lat'], destination['lon']),
                departure_time,
            )
            return jsonify({
                "success": True,
                "public_transport_available": False,
                "reason": reason,
                "suggested_mode": "PRIVATE_VEHICLE",
                "private_vehicle": estimate,
                "origin": origin,
                "destination": destination,
                "departure_time": departure_time.isoformat(),
            }), 200

        if preferences is not None:
            preferred = select_preferred_route(alternatives, preferences)
            if preferred is not None:
                alternatives.append(preferred)

        return jsonify({
            "success": True,
            "origin": origin,
            "destination": destination,
            "departure_time": departure_time.isoformat(),
            "alternatives": [
                {
                    "label": alt["label"],
                    "optimized_for": alt["optimized_for"],
                    # Atribut X_ij dalam satuan asli, ikut dikirim supaya
                    # himpunan pilihan bisa direkam apa adanya saat pengguna
                    # memilih salah satu (POST /api/choice).
                    "attributes": route_attributes(alt["route"]),
                    "route": serialize_route(
                        alt["route"], origin.get('name', 'Origin'),
                        destination.get('name', 'Destination'),
                        (origin['lat'], origin['lon']),
                        (destination['lat'], destination['lon']),
                    ),
                }
                for alt in alternatives
            ],
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# Satu observasi = satu baris JSON. Formatnya sengaja "tabel panjang" (satu
# baris memuat SELURUH himpunan pilihan + mana yang dipilih), krn itu bentuk
# yang dibutuhkan estimasi model pemilihan diskret -- bukan satu baris per
# rute yang ditampilkan.
CHOICE_LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'dataset', 'survey', 'choices.jsonl'
)

ATTRIBUTE_KEYS = ("time_minutes", "cost_rupiah", "transfers", "access_km", "comfort", "reliability")

MAX_CHOICE_SET = 10


def _validate_choice_payload(data):
    """
    Kembalikan (observasi, None) kalau valid, atau (None, pesan_error).

    Divalidasi ketat: isinya datang dari browser (trust boundary), dan file
    ini adalah DATA PENELITIAN -- satu baris rusak yang lolos bisa membiaskan
    estimasi parameter tanpa ketahuan.
    """
    if not isinstance(data, dict):
        return None, "payload must be a JSON object"

    choice_set = data.get('choice_set')
    if not isinstance(choice_set, list) or not 1 <= len(choice_set) <= MAX_CHOICE_SET:
        return None, f"choice_set must be a list of 1..{MAX_CHOICE_SET} alternatives"

    chosen_index = data.get('chosen_index')
    if not isinstance(chosen_index, int) or isinstance(chosen_index, bool):
        return None, "chosen_index must be an integer"
    if not 0 <= chosen_index < len(choice_set):
        return None, "chosen_index is out of range for choice_set"

    clean_set = []
    for alt in choice_set:
        if not isinstance(alt, dict):
            return None, "each alternative must be an object"
        attrs = alt.get('attributes')
        if not isinstance(attrs, dict) or set(attrs.keys()) != set(ATTRIBUTE_KEYS):
            return None, f"each alternative needs attributes with exactly: {list(ATTRIBUTE_KEYS)}"
        try:
            numeric = {k: float(attrs[k]) for k in ATTRIBUTE_KEYS}
        except (TypeError, ValueError):
            return None, "attribute values must be numbers"
        # Nilai negatif/tak-hingga tidak punya arti fisik utk menit, rupiah,
        # jumlah transfer, maupun jarak akses -- tolak drpd mencemari data.
        if any(v != v or v in (float('inf'), float('-inf')) or v < 0 for v in numeric.values()):
            return None, "attribute values must be finite and non-negative"
        clean_set.append({
            "label": str(alt.get('label', ''))[:80],
            "optimized_for": str(alt.get('optimized_for', ''))[:40],
            "attributes": numeric,
        })

    prefs = data.get('preferences')
    clean_prefs = None
    if prefs is not None:
        if not isinstance(prefs, dict) or set(prefs.keys()) != set(PREFERENCE_CRITERIA):
            return None, f"preferences must have exactly these keys: {list(PREFERENCE_CRITERIA)}"
        try:
            clean_prefs = {k: float(prefs[k]) for k in PREFERENCE_CRITERIA}
        except (TypeError, ValueError):
            return None, "preferences values must be numbers"
        if any(not 1 <= v <= 5 for v in clean_prefs.values()):
            return None, "preferences values must be between 1 and 5"

    def clean_place(raw):
        if not isinstance(raw, dict):
            return None
        try:
            return {
                "name": str(raw.get('name', ''))[:200],
                "lat": float(raw['lat']),
                "lon": float(raw['lon']),
            }
        except (KeyError, TypeError, ValueError):
            return None

    return {
        "timestamp": datetime.now(WIB_TZ).isoformat(),
        "respondent_id": str(data.get('respondent_id', ''))[:64],
        "preferences": clean_prefs,
        "origin": clean_place(data.get('origin')),
        "destination": clean_place(data.get('destination')),
        "departure_time": str(data.get('departure_time', ''))[:40],
        "choice_set": clean_set,
        "chosen_index": chosen_index,
    }, None


@app.route('/api/choice', methods=['POST'])
def record_choice():
    """
    Rekam satu observasi pemilihan rute: himpunan alternatif yang ditawarkan
    beserta atributnya, penilaian preferensi responden, dan alternatif mana
    yang dipilih.

    Inilah bagian "pilihan moda aktual" pada input survei -- penilaian
    atribut saja (skala 1-5 di halaman /preferensi) tidak cukup untuk
    mengestimasi parameter model pemilihan; yang dibutuhkan adalah pasangan
    (himpunan pilihan -> yang dipilih).
    """
    try:
        observation, error = _validate_choice_payload(request.get_json())
        if error:
            return jsonify({"success": False, "error": error}), 400

        os.makedirs(os.path.dirname(CHOICE_LOG_PATH), exist_ok=True)
        # ponytail: append baris tunggal ke JSONL, tanpa basis data & tanpa
        # kunci file. Satu baris << 4KB sehingga append O_APPEND praktis atomik
        # di POSIX. Kalau nanti dipakai banyak responden serentak di banyak
        # proses, barulah pindah ke SQLite.
        with open(CHOICE_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(observation, ensure_ascii=False) + "\n")

        return jsonify({"success": True}), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# Data karakteristik responden (S-1), terpisah dari choices.jsonl krn
# ini satu baris per ORANG (sekali isi), bukan per observasi pilihan.
# Dihubungkan lewat respondent_id yang sama dgn /api/choice.
RESPONDENT_LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'dataset', 'survey', 'respondents.jsonl'
)

RESPONDENT_FIELDS = (
    "age", "gender", "occupation", "income", "vehicle_ownership",
    "trip_purpose", "transit_frequency",
)


def _validate_respondent_payload(data):
    """Kembalikan (record, None) kalau valid, atau (None, pesan_error)."""
    if not isinstance(data, dict):
        return None, "payload must be a JSON object"

    respondent_id = str(data.get('respondent_id', ''))[:64]
    if not respondent_id:
        return None, "respondent_id is required"

    clean = {}
    for field in RESPONDENT_FIELDS:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            return None, f"field '{field}' is required"
        clean[field] = value.strip()[:80]

    return {
        "timestamp": datetime.now(WIB_TZ).isoformat(),
        "respondent_id": respondent_id,
        **clean,
    }, None


@app.route('/api/respondent', methods=['POST'])
def record_respondent():
    """Rekam karakteristik responden (sekali per orang, anonim -- tidak ada
    autentikasi, respondent_id cukup UUID yang dibuat & disimpan di browser)."""
    try:
        record, error = _validate_respondent_payload(request.get_json())
        if error:
            return jsonify({"success": False, "error": error}), 400

        os.makedirs(os.path.dirname(RESPONDENT_LOG_PATH), exist_ok=True)
        # ponytail: sama seperti choices.jsonl -- append JSONL polos, cukup
        # utk skala survei tunggal ini. Pindah ke SQLite kalau nanti butuh
        # query/dedup di sisi server.
        with open(RESPONDENT_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return jsonify({"success": True}), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/survey/export', methods=['GET'])
def export_survey_data():
    """
    Unduh seluruh observasi pilihan (S-3, long-format) sbg CSV -- gabungan
    choices.jsonl + respondents.jsonl, format sama persis dgn
    scripts/export_long_format.py (satu sumber logika, lihat
    core/survey_export.py). TIDAK menerima path dari request -- selalu file
    survei baku, supaya tidak bisa dipakai baca file sembarang di server.
    """
    try:
        if not os.path.exists(CHOICE_LOG_PATH):
            return jsonify({"success": False, "error": "Belum ada data observasi."}), 404

        rows = build_long_format_rows(CHOICE_LOG_PATH, RESPONDENT_LOG_PATH)
        csv_text = rows_to_csv(rows)

        timestamp = datetime.now(WIB_TZ).strftime('%Y%m%d_%H%M%S')
        return Response(
            csv_text,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="choices_long_{timestamp}.csv"'
            },
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/route/waypoints/<route_name>', methods=['GET'])
def get_route_waypoints(route_name):
    """Get route waypoints from KMZ for accurate visualization"""
    try:
        import json
        json_path = "dataset/network_data_correct_bidirectional.json"
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        route_waypoints = data.get('route_waypoints', {})
        route_stop_anchors = data.get('route_stop_anchors', {})

        if route_name in route_waypoints:
            return jsonify({
                "success": True,
                "route": route_name,
                "waypoints": route_waypoints[route_name],
                "count": len(route_waypoints[route_name]),
                # [lat, lon, waypoint_index] per halte asli -- dicatat PERSIS
                # saat polyline dibuat (bukan ditebak lewat nearest-search),
                # supaya frontend tidak perlu cari "titik terdekat" di seluruh
                # polyline (rawan salah utk rute berbentuk loop yg bisa lewat
                # berdekatan dgn dirinya sendiri di titik yg beda).
                "stop_anchors": route_stop_anchors.get(route_name, [])
            })
        else:
            return jsonify({
                "success": False,
                "error": f"No waypoints found for route: {route_name}"
            }), 404
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/stops', methods=['GET'])
def get_stops():
    """Get all stops for map visualization"""
    try:
        graph = load_network()
        
        stops = []
        for stop in graph.stops.values():
            stops.append({
                "id": stop.stop_id,
                "name": stop.name,
                "lat": stop.lat,
                "lon": stop.lon,
                "mode": stop.mode.value if hasattr(stop.mode, 'value') else str(stop.mode),
                "route": stop.route
            })
        
        return jsonify({
            "success": True,
            "stops": stops,
            "total": len(stops)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # Load network at startup
    load_network()
    
    print("="*60)
    print("🚀 Sistem Informasi Integrasi Antar Moda - Kota Palembang")
    print("="*60)
    print("📡 Endpoint tersedia:")
    print("   GET  /api/health - Cek status layanan")
    print("   GET  /api/network/info - Informasi jaringan")
    print("   POST /api/route/alternatives - Alternatif rute + atributnya")
    print("   POST /api/choice - Rekam pilihan rute (data survei)")
    print("   GET  /api/route/waypoints/<route_name> - Jalur koridor")
    print("   GET  /api/stops - Daftar halte")
    print("="*60)
    
    app.run(debug=True, host='0.0.0.0', port=5001)
