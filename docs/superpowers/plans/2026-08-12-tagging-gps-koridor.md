# Tagging GPS Koridor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambahkan mode "Tagging GPS" ke tab Jaringan, supaya pemilik proyek bisa naik tiap transum, menandai posisi GPS aktual tiap kali berhenti di halte, lalu menyimpan hasilnya sebagai pengganti data koordinat halte koridor tersebut.

**Architecture:** Backend: satu modul Python murni (`src/core/network_edit.py`) yang menghitung penggantian `nodes`/`edges` untuk satu koridor di kedua file network JSON, dipanggil dari satu endpoint Flask baru (`PUT /api/network/corridor/<route_name>/stops`) yang menangani I/O file (baca, backup, tulis) dan reload graf routing in-memory. Frontend: satu hook (`useTaggingSession`) mengelola state sesi GPS + persistensi `localStorage`, dipakai oleh komponen peta baru (`TaggingMapComponent`) dan panel UI yang ditambahkan ke `frontend/src/app/jaringan/page.tsx`.

**Tech Stack:** Flask (Python, tanpa dependency baru), Next.js/React + `react-leaflet` (sudah terpasang), Geolocation Web API browser bawaan (tanpa library baru).

## Global Constraints

- Tidak ada auth/login ditambahkan (keputusan eksplisit user — fitur ini publik, sama seperti seluruh app).
- Akurasi GPS 2,5m: kalau lebih buruk saat titik ditag, tetap masuk daftar dengan peringatan visual, TIDAK memblokir tombol Tag.
- Penamaan titik: auto "Halte N" saat ditag, nama asli diisi/diubah belakangan di layar review (atau kapan saja, lihat Task 5).
- Simpan = replace penuh seluruh halte koridor itu (bukan cocokkan satu-satu ke data lama).
- Endpoint backend HARUS memperbarui `dataset/network_data_complete.json` DAN `dataset/network_data_correct_bidirectional.json` (API live memuat graf dari file kedua) — lihat catatan koreksi di `docs/superpowers/specs/2026-08-12-tagging-gps-koridor-design.md`.
- Backup kedua file network JSON (`<nama>.backup-<YYYYMMDDHHMMSS><ext>`) sebelum menulis, setiap kali endpoint dipanggil.
- `route_waypoints`/`route_stop_anchors` di `network_data_correct_bidirectional.json` TIDAK boleh disentuh/dihapus oleh endpoint ini.
- Reverse edge (`is_reverse: true`) hanya ditambahkan untuk koridor di `LINEAR_ROUTES = {"Feeder Koridor 5", "LRT Sumsel"}`, konsisten dengan `scripts/create_correct_bidirectional.py`.
- Tidak ada dependency npm/pip baru — pakai `react-leaflet`/Geolocation API/`crypto.randomUUID()` yang sudah tersedia.
- Ikuti konvensi self-check codebase ini: modul Python inti punya `demo()` dengan `assert`, dijalankan via `python <path_file>.py` (lihat `src/core/service_model.py`), bukan pytest (repo ini tidak pakai pytest).
- Tidak ada framework test frontend di repo ini (tidak ada jest/vitest terpasang) — verifikasi frontend dilakukan manual di browser dev server, sesuai konvensi fitur-fitur sebelumnya di app ini.

---

## File Structure

**Backend (baru):**
- `src/core/network_edit.py` — logika murni penggantian nodes/edges satu koridor di kedua struktur data network. Tidak baca/tulis file sendiri (mudah diuji tanpa I/O).

**Backend (diubah):**
- `api/app.py` — tambah endpoint `PUT /api/network/corridor/<route_name>/stops`: baca kedua file JSON, backup, panggil `network_edit.replace_corridor_stops()`, tulis hasil, reload `network_graph` global.

**Frontend (baru):**
- `frontend/src/app/components/useTaggingSession.ts` — hook: state sesi tagging (titik-titik, posisi GPS live, status idle/session/review), persistensi `localStorage`, fungsi tag/hapus/ubah nama/reorder/tambah manual/simpan ke server.
- `frontend/src/app/components/TaggingMapComponent.tsx` — peta Leaflet: marker posisi GPS live + lingkaran akurasi, marker tiap titik tertag (bernomor), garis penghubung berurutan, klik peta untuk tambah titik manual.

**Frontend (diubah):**
- `frontend/src/app/jaringan/page.tsx` — tambah tombol "Mode Edit" saat koridor dipilih, render panel sesi tagging (pakai `useTaggingSession` + `TaggingMapComponent`) menggantikan tampilan read-only saat mode edit aktif.

---

### Task 1: Modul inti `network_edit.py` (penggantian nodes/edges koridor)

**Files:**
- Create: `src/core/network_edit.py`

**Interfaces:**
- Produces: `LINEAR_ROUTES: set[str]`, `haversine_distance(lat1, lon1, lat2, lon2) -> float` (meter), `replace_corridor_stops(complete_data: dict, bidir_data: dict, route_name: str, stops: list[dict]) -> dict` dengan `stops` = `[{"name": str, "lat": float, "lon": float}, ...]` dan return `{"complete_data": dict, "bidir_data": dict, "old_count": int, "new_count": int}`. Melempar `ValueError` kalau `len(stops) < 2`.

- [ ] **Step 1: Tulis modul dengan `demo()` self-check di dalamnya (bukan file test terpisah — ikuti konvensi `src/core/service_model.py`)**

```python
"""
Logika inti penggantian data halte satu koridor (dipakai endpoint tagging
GPS di api/app.py). Modul murni -- tidak baca/tulis file sendiri, supaya
gampang diuji tanpa I/O nyata dan dipakai ulang dari mana saja.

Konteks kenapa ada 2 struktur data (complete_data & bidir_data): API live
(`api/app.py`) memuat graf routing dari network_data_correct_bidirectional.json,
BUKAN network_data_complete.json. File itu turunan: scripts/create_correct_bidirectional.py
membaca network_data_complete.json, menambah edge balik HANYA utk koridor
linear (LINEAR_ROUTES di bawah), lalu simpan sbg file terpisah yg juga
punya key route_waypoints/route_stop_anchors yg TIDAK ada di file asal.
Makanya replace_corridor_stops() harus dipanggil utk KEDUA dict, dan tidak
boleh membangun ulang bidir_data dari nol (akan menghapus 2 key itu).
"""

from math import radians, sin, cos, sqrt, atan2

# Sinkron dengan scripts/create_correct_bidirectional.py -- HANYA 2 koridor
# ini yg diberi edge balik (linear/point-to-point), sisanya koridor
# memutar (circuit) jadi tetap satu arah.
LINEAR_ROUTES = {"Feeder Koridor 5", "LRT Sumsel"}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Jarak dua titik lat/lon dalam meter (sama persis dgn data_loader.py)."""
    R = 6371000
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def _slugify_route(route_name: str) -> str:
    return route_name.replace(" ", "_")


def _build_nodes_and_edges(route_name: str, stops: list) -> tuple:
    slug = _slugify_route(route_name)
    nodes = []
    for i, stop in enumerate(stops):
        nodes.append({
            "id": None,  # diisi caller (butuh tahu max id lintas file dulu)
            "stop_id": f"{slug}_{i + 1}",
            "name": stop["name"],
            "lat": stop["lat"],
            "lon": stop["lon"],
            "route": route_name,
        })
    edges = []
    for i in range(len(nodes) - 1):
        a, b = nodes[i], nodes[i + 1]
        edges.append({
            "route": route_name,
            "distance": haversine_distance(a["lat"], a["lon"], b["lat"], b["lon"]),
            "_from_idx": i,
            "_to_idx": i + 1,
        })
    return nodes, edges


def _apply_replacement(data: dict, route_name: str, new_nodes: list, new_edges: list,
                        add_reverse: bool) -> None:
    """Ubah data['nodes']/data['edges'] IN PLACE: buang milik route_name lama,
    pasang yg baru. new_edges masih berisi '_from_idx'/'_to_idx' (indeks ke
    new_nodes) -- dikonversi ke id node asli di sini."""
    data["nodes"] = [n for n in data["nodes"] if n["route"] != route_name] + new_nodes

    resolved_edges = []
    for e in new_edges:
        from_id = new_nodes[e["_from_idx"]]["id"]
        to_id = new_nodes[e["_to_idx"]]["id"]
        resolved_edges.append({"from": from_id, "to": to_id, "route": route_name, "distance": e["distance"]})
        if add_reverse:
            resolved_edges.append({"from": to_id, "to": from_id, "route": route_name,
                                    "distance": e["distance"], "is_reverse": True})

    data["edges"] = [e for e in data["edges"] if e.get("route") != route_name] + resolved_edges


def replace_corridor_stops(complete_data: dict, bidir_data: dict, route_name: str, stops: list) -> dict:
    """Ganti seluruh halte satu koridor di kedua struktur data sekaligus.

    stops: [{"name": str, "lat": float, "lon": float}, ...] terurut sesuai
    urutan fisik di lapangan. Return dict berisi complete_data/bidir_data
    yg sudah diubah (in place, juga dikembalikan utk kenyamanan caller) +
    jumlah halte lama/baru utk pelaporan.
    """
    if len(stops) < 2:
        raise ValueError("stops harus berisi minimal 2 titik")

    old_count = sum(1 for n in complete_data["nodes"] if n["route"] == route_name)

    max_id = max((n["id"] for n in complete_data["nodes"]), default=-1)
    new_nodes, new_edges = _build_nodes_and_edges(route_name, stops)
    for i, node in enumerate(new_nodes):
        node["id"] = max_id + 1 + i

    _apply_replacement(complete_data, route_name, new_nodes, new_edges, add_reverse=False)
    # new_nodes dipakai lagi utk bidir_data -- id harus SAMA persis antar
    # kedua file, jadi bukan bangun node baru lagi, cukup deep-copy dict-nya
    # (edge builder butuh objek node baru krn _apply_replacement pertama
    # sudah "memakai" list yg sama sbg referensi data["nodes"]).
    bidir_new_nodes = [dict(n) for n in new_nodes]
    _apply_replacement(bidir_data, route_name, bidir_new_nodes, new_edges,
                        add_reverse=route_name in LINEAR_ROUTES)

    return {
        "complete_data": complete_data,
        "bidir_data": bidir_data,
        "old_count": old_count,
        "new_count": len(new_nodes),
    }


def demo():
    """Self-check: jalankan `python src/core/network_edit.py`."""
    complete = {
        "nodes": [
            {"id": 0, "stop_id": "Feeder_Koridor_1_1", "name": "A", "lat": -2.90, "lon": 104.70, "route": "Feeder Koridor 1"},
            {"id": 1, "stop_id": "Feeder_Koridor_1_2", "name": "B", "lat": -2.91, "lon": 104.71, "route": "Feeder Koridor 1"},
            {"id": 2, "stop_id": "LRT_Sumsel_1", "name": "C", "lat": -3.00, "lon": 104.80, "route": "LRT Sumsel"},
        ],
        "edges": [
            {"from": 0, "to": 1, "route": "Feeder Koridor 1", "distance": 1500.0},
        ],
        "routes": ["Feeder Koridor 1", "LRT Sumsel"],
    }
    bidir = {
        "nodes": [dict(n) for n in complete["nodes"]],
        "edges": [dict(e) for e in complete["edges"]],
        "routes": list(complete["routes"]),
        "route_waypoints": {"Feeder Koridor 1": [[-2.90, 104.70], [-2.91, 104.71]]},
        "route_stop_anchors": {"Feeder Koridor 1": [[-2.90, 104.70, 0]]},
    }

    new_stops = [
        {"name": "Halte 1", "lat": -2.905, "lon": 104.705},
        {"name": "Halte 2", "lat": -2.915, "lon": 104.715},
        {"name": "Halte 3", "lat": -2.925, "lon": 104.725},
    ]
    result = replace_corridor_stops(complete, bidir, "Feeder Koridor 1", new_stops)

    assert result["old_count"] == 2, "harus menghitung 2 halte lama Feeder Koridor 1"
    assert result["new_count"] == 3

    fk1_nodes = [n for n in complete["nodes"] if n["route"] == "Feeder Koridor 1"]
    assert len(fk1_nodes) == 3, "node lama harus diganti, bukan ditambah"
    assert all(n["id"] >= 3 for n in fk1_nodes), "id baru harus lanjut dari max id lama (2)"

    lrt_nodes = [n for n in complete["nodes"] if n["route"] == "LRT Sumsel"]
    assert len(lrt_nodes) == 1, "koridor lain (LRT Sumsel) tidak boleh ikut terhapus/berubah"

    fk1_edges = [e for e in complete["edges"] if e["route"] == "Feeder Koridor 1"]
    assert len(fk1_edges) == 2, "3 halte -> 2 edge berurutan"
    assert all(not e.get("is_reverse") for e in fk1_edges), "Feeder Koridor 1 bukan linear, tidak boleh ada edge balik"

    expected_dist = haversine_distance(-2.905, 104.705, -2.915, 104.715)
    assert abs(fk1_edges[0]["distance"] - expected_dist) < 0.01

    # bidir_data: route_waypoints/route_stop_anchors TIDAK boleh hilang
    assert "route_waypoints" in bidir and bidir["route_waypoints"]
    assert "route_stop_anchors" in bidir and bidir["route_stop_anchors"]

    # Koridor linear (LRT Sumsel): tag ulang harus MENGHASILKAN edge balik di bidir_data
    lrt_stops = [
        {"name": "Stasiun 1", "lat": -3.00, "lon": 104.80},
        {"name": "Stasiun 2", "lat": -3.01, "lon": 104.81},
    ]
    replace_corridor_stops(complete, bidir, "LRT Sumsel", lrt_stops)
    lrt_bidir_edges = [e for e in bidir["edges"] if e["route"] == "LRT Sumsel"]
    assert len(lrt_bidir_edges) == 2, "1 forward + 1 reverse utk koridor linear"
    assert sum(1 for e in lrt_bidir_edges if e.get("is_reverse")) == 1
    lrt_complete_edges = [e for e in complete["edges"] if e["route"] == "LRT Sumsel"]
    assert len(lrt_complete_edges) == 1, "complete_data TIDAK pernah dapat edge balik (satu arah semua)"

    print("OK - semua self-check network_edit.py lolos")


if __name__ == "__main__":
    demo()
```

- [ ] **Step 2: Jalankan self-check**

Run: `cd /home/naufa/workspace/routing_transportation_v2 && python3 src/core/network_edit.py`
Expected: `OK - semua self-check network_edit.py lolos` tercetak, exit code 0 (tidak ada `AssertionError`/traceback).

- [ ] **Step 3: Commit**

```bash
git add src/core/network_edit.py
git commit -m "feat: add core logic for replacing a corridor's stops (GPS tagging)"
```

---

### Task 2: Endpoint backend `PUT /api/network/corridor/<route_name>/stops`

**Files:**
- Modify: `api/app.py`

**Interfaces:**
- Consumes: `network_edit.replace_corridor_stops(complete_data, bidir_data, route_name, stops) -> {"complete_data", "bidir_data", "old_count", "new_count"}` (dari Task 1; `LINEAR_ROUTES` dipakai internal oleh fungsi ini, endpoint tidak perlu mengimpornya langsung).
- Produces: endpoint HTTP `PUT /api/network/corridor/<route_name>/stops`, body `{"stops": [{"name","lat","lon"}, ...]}`, response sukses `{"success": true, "route": str, "old_stop_count": int, "new_stop_count": int, "backups": [str, str]}` (200), response gagal `{"success": false, "error": str}` (400/404/500).

- [ ] **Step 1: Tambah import & konstanta path file, di dekat `CHOICE_LOG_PATH` yang sudah ada**

Tambahkan di `api/app.py` setelah baris `from core.survey_export import build_long_format_rows, rows_to_csv` (baris 25):

```python
import shutil
from core.network_edit import replace_corridor_stops
```

Tambahkan setelah blok `CHOICE_LOG_PATH`/`RESPONDENT_LOG_PATH` (dekat baris 320-322 & 442-444), sebelum endpoint baru ditambahkan:

```python
NETWORK_COMPLETE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'dataset', 'network_data_complete.json'
)
NETWORK_BIDIR_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'dataset', 'network_data_correct_bidirectional.json'
)
```

- [ ] **Step 2: Tambah fungsi validasi payload + endpoint, taruh persis sebelum `if __name__ == '__main__':` di akhir file**

```python
def _validate_stops_payload(data):
    """Kembalikan (list_titik_bersih, None) kalau valid, atau (None, pesan_error)."""
    if not isinstance(data, dict):
        return None, "payload must be a JSON object"

    stops = data.get('stops')
    if not isinstance(stops, list) or len(stops) < 2:
        return None, "stops must be a list of at least 2 points"

    clean = []
    for stop in stops:
        if not isinstance(stop, dict):
            return None, "each stop must be an object"
        name = str(stop.get('name', '')).strip()[:120]
        if not name:
            return None, "each stop needs a non-empty name"
        try:
            lat = float(stop['lat'])
            lon = float(stop['lon'])
        except (KeyError, TypeError, ValueError):
            return None, "each stop needs numeric lat/lon"
        # Rentang longgar wilayah Indonesia -- cukup utk menolak salah input
        # kasar (mis. lat/lon tertukar), bukan validasi presisi lokasi.
        if not (-11 <= lat <= 6) or not (95 <= lon <= 141):
            return None, "lat/lon out of range for Indonesia"
        clean.append({"name": name, "lat": lat, "lon": lon})

    return clean, None


@app.route('/api/network/corridor/<route_name>/stops', methods=['PUT'])
def update_corridor_stops(route_name):
    """
    Ganti seluruh data halte satu koridor (hasil sesi tagging GPS lapangan).
    Menulis KEDUA file network JSON (lihat network_edit.py utk alasannya),
    backup dulu sebelum overwrite, lalu reload graf routing in-memory
    supaya pencarian rute langsung pakai data baru tanpa restart container.
    """
    try:
        stops, error = _validate_stops_payload(request.get_json())
        if error:
            return jsonify({"success": False, "error": error}), 400

        with open(NETWORK_COMPLETE_PATH, 'r', encoding='utf-8') as f:
            complete_data = json.load(f)
        with open(NETWORK_BIDIR_PATH, 'r', encoding='utf-8') as f:
            bidir_data = json.load(f)

        existing_routes = {n['route'] for n in complete_data['nodes']}
        if route_name not in existing_routes:
            return jsonify({"success": False, "error": f"Koridor '{route_name}' tidak dikenal"}), 404

        timestamp = datetime.now(WIB_TZ).strftime('%Y%m%d%H%M%S')

        def _backup(path):
            base, ext = os.path.splitext(path)
            backup_path = f"{base}.backup-{timestamp}{ext}"
            shutil.copy2(path, backup_path)
            return backup_path

        complete_backup = _backup(NETWORK_COMPLETE_PATH)
        bidir_backup = _backup(NETWORK_BIDIR_PATH)

        result = replace_corridor_stops(complete_data, bidir_data, route_name, stops)

        with open(NETWORK_COMPLETE_PATH, 'w', encoding='utf-8') as f:
            json.dump(result["complete_data"], f, ensure_ascii=False, indent=2)
        with open(NETWORK_BIDIR_PATH, 'w', encoding='utf-8') as f:
            json.dump(result["bidir_data"], f, ensure_ascii=False, indent=2)

        global network_graph
        network_graph = None
        load_network()

        return jsonify({
            "success": True,
            "route": route_name,
            "old_stop_count": result["old_count"],
            "new_stop_count": result["new_count"],
            "backups": [complete_backup, bidir_backup],
        }), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
```

- [ ] **Step 3: Verifikasi manual dengan Flask dev server + curl**

Run (terminal 1):
```bash
cd /home/naufa/workspace/routing_transportation_v2
python3 api/app.py
```

Run (terminal 2, ganti `<route>` dengan nama koridor kecil yang aman dicoba, mis. cek dulu daftar via `curl -s http://localhost:5001/api/network/info`):
```bash
curl -s -X PUT http://localhost:5001/api/network/corridor/Feeder%20Koridor%201/stops \
  -H "Content-Type: application/json" \
  -d '{"stops":[{"name":"Test A","lat":-2.90,"lon":104.70},{"name":"Test B","lat":-2.91,"lon":104.71}]}' | python3 -m json.tool
```

Expected: JSON `{"success": true, "route": "Feeder Koridor 1", "old_stop_count": <angka lama>, "new_stop_count": 2, "backups": [...]}`. Cek juga:
```bash
ls dataset/*.backup-*.json
curl -s "http://localhost:5001/api/route/waypoints/Feeder%20Koridor%201" | python3 -m json.tool | head -20
```
Pastikan `route_waypoints` untuk koridor lain (misal `LRT Sumsel`) di respons `/api/route/waypoints/LRT%20Sumsel` masih ada/tidak berubah.

**Setelah verifikasi, kembalikan data ke semula** (jangan biarkan `Feeder Koridor 1` tertimpa data uji coba):
```bash
LATEST_COMPLETE=$(ls -t dataset/network_data_complete.backup-*.json | head -1)
LATEST_BIDIR=$(ls -t dataset/network_data_correct_bidirectional.backup-*.json | head -1)
cp "$LATEST_COMPLETE" dataset/network_data_complete.json
cp "$LATEST_BIDIR" dataset/network_data_correct_bidirectional.json
rm dataset/*.backup-*.json
```
Restart `python3 api/app.py` setelah restore supaya graf in-memory ikut kembali normal.

- [ ] **Step 4: Commit**

```bash
git add api/app.py
git commit -m "feat: add PUT /api/network/corridor/<route>/stops endpoint for GPS tagging"
```

---

### Task 3: Hook frontend `useTaggingSession`

**Files:**
- Create: `frontend/src/app/components/useTaggingSession.ts`

**Interfaces:**
- Consumes: tidak ada dari task lain (hook mandiri, hanya pakai Geolocation Web API bawaan browser + `localStorage` + `crypto.randomUUID()`).
- Produces (dipakai Task 5 di `jaringan/page.tsx`):
  - `export interface TaggedPoint { id: string; name: string; lat: number; lon: number; accuracy: number }`
  - `export function useTaggingSession(routeName: string | null)` mengembalikan:
    - `status: "idle" | "session" | "review"`
    - `points: TaggedPoint[]`
    - `currentPosition: { lat: number; lon: number; accuracy: number } | null`
    - `geoError: string | null`
    - `hasSavedSession: boolean`
    - `saving: boolean`
    - `saveError: string | null`
    - `startSession(): void`
    - `resumeSession(): void`
    - `discardSession(): void`
    - `tagCurrentPosition(): void`
    - `addManualPoint(lat: number, lon: number): void`
    - `removePoint(id: string): void`
    - `renamePoint(id: string, name: string): void`
    - `movePoint(id: string, direction: "up" | "down"): void`
    - `finishSession(): void`
    - `backToSession(): void`
    - `save(): Promise<boolean>`

- [ ] **Step 1: Tulis hook**

```typescript
"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface TaggedPoint {
  id: string;
  name: string;
  lat: number;
  lon: number;
  accuracy: number;
}

interface StoredSession {
  points: TaggedPoint[];
  status: "session" | "review";
}

type Status = "idle" | "session" | "review";

const ACCURACY_WARNING_METERS = 2.5;

function storageKey(routeName: string) {
  return `tagging_session_v1_${routeName}`;
}

// Hook mandiri: mengelola satu sesi tagging GPS utk SATU koridor (routeName).
// Dipanggil ulang dgn routeName berbeda saat user ganti koridor di halaman
// Jaringan -- state di-reset otomatis krn key localStorage beda per koridor.
export function useTaggingSession(routeName: string | null) {
  const [status, setStatus] = useState<Status>("idle");
  const [points, setPoints] = useState<TaggedPoint[]>([]);
  const [currentPosition, setCurrentPosition] = useState<
    { lat: number; lon: number; accuracy: number } | null
  >(null);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [hasSavedSession, setHasSavedSession] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const watchIdRef = useRef<number | null>(null);

  // Cek localStorage tiap kali koridor berganti -- tawarkan resume kalau ada
  // sesi tersimpan sebelumnya utk koridor itu.
  useEffect(() => {
    setStatus("idle");
    setPoints([]);
    setCurrentPosition(null);
    setGeoError(null);
    setSaveError(null);
    if (!routeName) {
      setHasSavedSession(false);
      return;
    }
    const raw = localStorage.getItem(storageKey(routeName));
    setHasSavedSession(!!raw);
  }, [routeName]);

  // Simpan progres ke localStorage tiap kali daftar titik berubah, SELAMA
  // sesi berjalan/direview -- supaya refresh/HP terkunci di tengah
  // perjalanan tidak menghilangkan hasil keliling.
  useEffect(() => {
    if (!routeName || status === "idle") return;
    const payload: StoredSession = { points, status };
    localStorage.setItem(storageKey(routeName), JSON.stringify(payload));
  }, [routeName, points, status]);

  const stopWatch = useCallback(() => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
  }, []);

  useEffect(() => stopWatch, [stopWatch]);

  const beginWatch = useCallback(() => {
    if (!("geolocation" in navigator)) {
      setGeoError("Browser ini tidak mendukung geolocation.");
      return;
    }
    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        setGeoError(null);
        setCurrentPosition({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
      },
      (err) => setGeoError(`Gagal mengakses lokasi: ${err.message}`),
      { enableHighAccuracy: true, maximumAge: 0, timeout: 15000 }
    );
  }, []);

  const startSession = useCallback(() => {
    setPoints([]);
    setStatus("session");
    beginWatch();
  }, [beginWatch]);

  const resumeSession = useCallback(() => {
    if (!routeName) return;
    const raw = localStorage.getItem(storageKey(routeName));
    if (!raw) return;
    const stored: StoredSession = JSON.parse(raw);
    setPoints(stored.points);
    setStatus(stored.status);
    if (stored.status === "session") beginWatch();
  }, [routeName, beginWatch]);

  const discardSession = useCallback(() => {
    if (routeName) localStorage.removeItem(storageKey(routeName));
    setHasSavedSession(false);
    setPoints([]);
    setStatus("idle");
    stopWatch();
  }, [routeName, stopWatch]);

  const tagCurrentPosition = useCallback(() => {
    if (!currentPosition) return;
    setPoints((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        name: `Halte ${prev.length + 1}`,
        lat: currentPosition.lat,
        lon: currentPosition.lon,
        accuracy: currentPosition.accuracy,
      },
    ]);
  }, [currentPosition]);

  const addManualPoint = useCallback((lat: number, lon: number) => {
    setPoints((prev) => [
      ...prev,
      { id: crypto.randomUUID(), name: `Halte ${prev.length + 1}`, lat, lon, accuracy: 0 },
    ]);
  }, []);

  const removePoint = useCallback((id: string) => {
    setPoints((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const renamePoint = useCallback((id: string, name: string) => {
    setPoints((prev) => prev.map((p) => (p.id === id ? { ...p, name } : p)));
  }, []);

  const movePoint = useCallback((id: string, direction: "up" | "down") => {
    setPoints((prev) => {
      const index = prev.findIndex((p) => p.id === id);
      const swapWith = direction === "up" ? index - 1 : index + 1;
      if (index === -1 || swapWith < 0 || swapWith >= prev.length) return prev;
      const next = [...prev];
      [next[index], next[swapWith]] = [next[swapWith], next[index]];
      return next;
    });
  }, []);

  const finishSession = useCallback(() => {
    setStatus("review");
    stopWatch();
  }, [stopWatch]);

  const backToSession = useCallback(() => {
    setStatus("session");
    beginWatch();
  }, [beginWatch]);

  const save = useCallback(async (): Promise<boolean> => {
    if (!routeName || points.length < 2) {
      setSaveError("Minimal 2 titik dibutuhkan sebelum menyimpan.");
      return false;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const res = await fetch(
        `/api/network/corridor/${encodeURIComponent(routeName)}/stops`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            stops: points.map((p) => ({ name: p.name, lat: p.lat, lon: p.lon })),
          }),
        }
      );
      const data = await res.json();
      if (!res.ok || !data.success) {
        setSaveError(data.error || "Gagal menyimpan ke server.");
        return false;
      }
      localStorage.removeItem(storageKey(routeName));
      setHasSavedSession(false);
      setPoints([]);
      setStatus("idle");
      return true;
    } catch {
      setSaveError("Gagal menghubungi server.");
      return false;
    } finally {
      setSaving(false);
    }
  }, [routeName, points]);

  return {
    status,
    points,
    currentPosition,
    geoError,
    hasSavedSession,
    saving,
    saveError,
    startSession,
    resumeSession,
    discardSession,
    tagCurrentPosition,
    addManualPoint,
    removePoint,
    renamePoint,
    movePoint,
    finishSession,
    backToSession,
    save,
    accuracyWarningMeters: ACCURACY_WARNING_METERS,
  };
}
```

- [ ] **Step 2: Verifikasi manual di browser (tidak ada test framework di repo ini)**

Run:
```bash
cd /home/naufa/workspace/routing_transportation_v2/frontend
npm run lint
```
Expected: tidak ada error TypeScript/ESLint baru dari file ini (boleh ada warning pre-existing yang tidak terkait).

Verifikasi fungsional hook baru dilakukan sekaligus dengan Task 5 (butuh UI utk dipakai) — bukan diulang di sini.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/components/useTaggingSession.ts
git commit -m "feat: add useTaggingSession hook for GPS stop-tagging state"
```

---

### Task 4: Komponen peta `TaggingMapComponent`

**Files:**
- Create: `frontend/src/app/components/TaggingMapComponent.tsx`

**Interfaces:**
- Consumes: `TaggedPoint` (dari Task 3, `./useTaggingSession`), `modeColor` (dari `./icons`, sudah ada).
- Produces: `export default function TaggingMapComponent(props: { points: TaggedPoint[]; currentPosition: { lat: number; lon: number; accuracy: number } | null; onMapClick: (lat: number, lon: number) => void })` — dirender via `next/dynamic` dgn `ssr: false` (pola sama seperti `NetworkMapComponent`, Leaflet butuh `window`).

- [ ] **Step 1: Tulis komponen**

```typescript
"use client";

import { useEffect } from "react";
import { Circle, MapContainer, Marker, Polyline, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { TaggedPoint } from "./useTaggingSession";

// Marker bernomor sederhana (divIcon) -- tidak butuh file gambar terpisah,
// cukup utk membedakan urutan titik tertag di peta.
function numberedIcon(n: number) {
  return L.divIcon({
    className: "",
    html: `<div style="background:#1a73e8;color:white;border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.4)">${n}</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
}

const currentPositionIcon = L.divIcon({
  className: "",
  html: `<div style="background:#ea4335;border-radius:50%;width:16px;height:16px;border:3px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.5)"></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

function RecenterOnPosition({ position }: { position: { lat: number; lon: number } | null }) {
  const map = useMap();
  useEffect(() => {
    if (position) map.setView([position.lat, position.lon], map.getZoom());
  }, [position, map]);
  return null;
}

function ClickToAdd({ onMapClick }: { onMapClick: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) {
      onMapClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

export default function TaggingMapComponent({
  points,
  currentPosition,
  onMapClick,
}: {
  points: TaggedPoint[];
  currentPosition: { lat: number; lon: number; accuracy: number } | null;
  onMapClick: (lat: number, lon: number) => void;
}) {
  const center: [number, number] = currentPosition
    ? [currentPosition.lat, currentPosition.lon]
    : [-2.9911, 104.7574];

  return (
    <MapContainer center={center} zoom={16} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClickToAdd onMapClick={onMapClick} />
      <RecenterOnPosition position={currentPosition} />

      {currentPosition && (
        <>
          <Marker position={[currentPosition.lat, currentPosition.lon]} icon={currentPositionIcon} />
          <Circle
            center={[currentPosition.lat, currentPosition.lon]}
            radius={currentPosition.accuracy}
            pathOptions={{ color: "#ea4335", fillOpacity: 0.1, weight: 1 }}
          />
        </>
      )}

      {points.length > 1 && (
        <Polyline positions={points.map((p) => [p.lat, p.lon])} color="#1a73e8" weight={4} opacity={0.7} />
      )}

      {points.map((p, i) => (
        <Marker key={p.id} position={[p.lat, p.lon]} icon={numberedIcon(i + 1)} />
      ))}
    </MapContainer>
  );
}
```

- [ ] **Step 2: Verifikasi manual**

Run: `cd frontend && npm run lint`
Expected: tidak ada error TypeScript baru dari file ini (verifikasi visual penuh menyusul di Task 5/6 setelah komponen ini benar-benar dirender).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/components/TaggingMapComponent.tsx
git commit -m "feat: add TaggingMapComponent for GPS tagging map view"
```

---

### Task 5: Wire UI ke `frontend/src/app/jaringan/page.tsx`

**Files:**
- Modify: `frontend/src/app/jaringan/page.tsx`

**Interfaces:**
- Consumes: `useTaggingSession` (Task 3), `TaggingMapComponent` (Task 4, dynamic import `ssr: false` seperti `NetworkMapComponent`).

- [ ] **Step 1: Tambah import di bagian atas file (setelah import `NetworkMapComponent` yang sudah ada, baris 6-19)**

```typescript
import { useTaggingSession } from "../components/useTaggingSession";

const TaggingMapComponent = dynamic(
  () => import("../components/TaggingMapComponent"),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full w-full items-center justify-center bg-[var(--gmaps-surface-hover)] text-sm text-[var(--gmaps-text-secondary)]">
        Memuat peta...
      </div>
    ),
  }
);
```

- [ ] **Step 2: Panggil hook di dalam `JaringanPage`, tepat setelah state `error` yang sudah ada (baris 34)**

```typescript
  const [editMode, setEditMode] = useState(false);
  const tagging = useTaggingSession(editMode ? selectedName : null);
```

- [ ] **Step 3: Tambah tombol "Mode Edit" di header saat koridor terpilih — sisipkan di `<aside>`, tepat setelah blok daftar koridor (`</div>` penutup `gmaps-scroll`, sebelum `</aside>` penutup, sekitar baris 136)**

```typescript
          {selectedRoute && !editMode && (
            <div className="border-t border-[var(--gmaps-border)] px-4 py-3">
              <button
                type="button"
                onClick={() => setEditMode(true)}
                className="w-full rounded-md bg-[var(--gmaps-blue)] px-3 py-2 text-sm font-medium text-white hover:opacity-90"
              >
                Mode Edit: Tagging GPS Halte
              </button>
            </div>
          )}

          {editMode && selectedRoute && (
            <div className="border-t border-[var(--gmaps-border)] px-4 py-3">
              <TaggingPanel routeName={selectedRoute.name} tagging={tagging} onExit={() => setEditMode(false)} />
            </div>
          )}
```

- [ ] **Step 4: Ganti render peta utama supaya pakai `TaggingMapComponent` saat `editMode` aktif — ubah blok `<main>` (baris 139-166) jadi:**

```typescript
      <main className="relative h-[60vh] w-full lg:h-full lg:flex-1">
        {editMode ? (
          <TaggingMapComponent
            points={tagging.points}
            currentPosition={tagging.currentPosition}
            onMapClick={(lat, lon) => {
              if (tagging.status === "session" || tagging.status === "review") {
                tagging.addManualPoint(lat, lon);
              }
            }}
          />
        ) : (
          <NetworkMapComponent selectedRoute={selectedRoute} />
        )}

        {!editMode && !selectedRoute && (
          <div className="pointer-events-none absolute inset-x-0 top-4 z-[1000] flex justify-center px-4">
            <p className="rounded-full bg-white/95 px-4 py-2 text-sm text-[var(--gmaps-text-secondary)] shadow-md">
              Pilih koridor di daftar untuk menampilkan rutenya di peta
            </p>
          </div>
        )}

        {!editMode && selectedRoute && (
          <div className="pointer-events-none absolute inset-x-0 top-4 z-[1000] flex justify-center px-4">
            <p className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 rounded-full bg-white/95 px-4 py-2 text-sm font-medium text-[var(--gmaps-text)] shadow-md">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: modeColor(selectedRoute.mode) }}
              />
              {selectedRoute.name}
              <span className="text-xs font-normal text-[var(--gmaps-text-secondary)]">
                · garis tegas = berangkat, putus-putus = pulang
              </span>
            </p>
          </div>
        )}
      </main>
```

- [ ] **Step 5: Tulis komponen `TaggingPanel` — tambahkan di FILE BARU `frontend/src/app/components/TaggingPanel.tsx` (dipisah dari `page.tsx` supaya file halaman tidak membengkak; ini komponen UI cukup besar: tombol mulai, daftar titik, layar review)**

```typescript
"use client";

import { useState } from "react";
import type { useTaggingSession } from "./useTaggingSession";

type TaggingHook = ReturnType<typeof useTaggingSession>;

export default function TaggingPanel({
  routeName,
  tagging,
  onExit,
}: {
  routeName: string;
  tagging: TaggingHook;
  onExit: () => void;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);

  if (tagging.status === "idle") {
    return (
      <div className="space-y-2">
        <p className="text-xs text-[var(--gmaps-text-secondary)]">
          Koridor: <strong>{routeName}</strong>
        </p>
        {tagging.hasSavedSession && (
          <div className="rounded-md bg-[var(--gmaps-surface-hover)] p-2 text-xs">
            <p className="mb-2">Ada sesi tagging tersimpan untuk koridor ini.</p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={tagging.resumeSession}
                className="flex-1 rounded-md bg-[var(--gmaps-blue)] px-2 py-1.5 font-medium text-white"
              >
                Lanjutkan
              </button>
              <button
                type="button"
                onClick={tagging.discardSession}
                className="flex-1 rounded-md border border-[var(--gmaps-border)] px-2 py-1.5"
              >
                Mulai Ulang
              </button>
            </div>
          </div>
        )}
        {!tagging.hasSavedSession && (
          <button
            type="button"
            onClick={tagging.startSession}
            className="w-full rounded-md bg-[var(--gmaps-blue)] px-3 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Mulai Sesi Tagging
          </button>
        )}
        <button
          type="button"
          onClick={onExit}
          className="w-full rounded-md border border-[var(--gmaps-border)] px-3 py-1.5 text-sm text-[var(--gmaps-text-secondary)]"
        >
          Keluar Mode Edit
        </button>
      </div>
    );
  }

  const isReview = tagging.status === "review";

  return (
    <div className="space-y-3">
      <p className="text-xs text-[var(--gmaps-text-secondary)]">
        Koridor: <strong>{routeName}</strong> · {isReview ? "Review" : "Sesi berjalan"}
      </p>

      {tagging.geoError && (
        <p className="text-xs text-[var(--gmaps-red)]">{tagging.geoError}</p>
      )}

      {!isReview && (
        <>
          <div className="text-xs text-[var(--gmaps-text-secondary)]">
            {tagging.currentPosition
              ? `Akurasi GPS saat ini: ${tagging.currentPosition.accuracy.toFixed(1)}m${
                  tagging.currentPosition.accuracy > tagging.accuracyWarningMeters ? " (kurang presisi)" : ""
                }`
              : "Menunggu sinyal GPS..."}
          </div>
          <button
            type="button"
            onClick={tagging.tagCurrentPosition}
            disabled={!tagging.currentPosition}
            className="w-full rounded-md bg-[var(--gmaps-blue)] px-3 py-3 text-base font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            Tag Halte ({tagging.points.length})
          </button>
        </>
      )}

      <ul className="max-h-64 space-y-1 overflow-y-auto">
        {tagging.points.map((p, i) => (
          <li
            key={p.id}
            className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-xs ${
              p.accuracy > tagging.accuracyWarningMeters ? "bg-yellow-50" : "bg-[var(--gmaps-surface-hover)]"
            }`}
          >
            <span className="w-4 shrink-0 text-center font-semibold">{i + 1}</span>
            {editingId === p.id ? (
              <input
                autoFocus
                defaultValue={p.name}
                onBlur={(e) => {
                  tagging.renamePoint(p.id, e.target.value || p.name);
                  setEditingId(null);
                }}
                className="min-w-0 flex-1 rounded border border-[var(--gmaps-border)] px-1 py-0.5"
              />
            ) : (
              <button
                type="button"
                onClick={() => setEditingId(p.id)}
                className="min-w-0 flex-1 truncate text-left"
                title="Klik untuk ganti nama"
              >
                {p.name}
              </button>
            )}
            <button type="button" onClick={() => tagging.movePoint(p.id, "up")} className="px-1 text-[var(--gmaps-text-secondary)]">
              ↑
            </button>
            <button type="button" onClick={() => tagging.movePoint(p.id, "down")} className="px-1 text-[var(--gmaps-text-secondary)]">
              ↓
            </button>
            <button type="button" onClick={() => tagging.removePoint(p.id)} className="px-1 text-[var(--gmaps-red)]">
              ✕
            </button>
          </li>
        ))}
      </ul>

      {!isReview && (
        <button
          type="button"
          onClick={tagging.finishSession}
          disabled={tagging.points.length < 2}
          className="w-full rounded-md border border-[var(--gmaps-blue)] px-3 py-2 text-sm font-medium text-[var(--gmaps-blue)] disabled:opacity-50"
        >
          Selesai Keliling ({tagging.points.length} titik)
        </button>
      )}

      {isReview && (
        <>
          <p className="text-xs text-[var(--gmaps-text-secondary)]">
            Klik peta untuk tambah titik yang kelewat. Simpan akan MENGGANTI seluruh data halte koridor ini.
          </p>
          {tagging.saveError && <p className="text-xs text-[var(--gmaps-red)]">{tagging.saveError}</p>}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={tagging.backToSession}
              disabled={tagging.saving}
              className="flex-1 rounded-md border border-[var(--gmaps-border)] px-3 py-2 text-sm disabled:opacity-50"
            >
              Kembali
            </button>
            <button
              type="button"
              onClick={async () => {
                const ok = await tagging.save();
                if (ok) onExit();
              }}
              disabled={tagging.saving || tagging.points.length < 2}
              className="flex-1 rounded-md bg-[var(--gmaps-blue)] px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {tagging.saving ? "Menyimpan..." : "Simpan ke Server"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Import `TaggingPanel` di `jaringan/page.tsx`**

Tambahkan di bagian import (dekat import `useTaggingSession` dari Step 1):

```typescript
import TaggingPanel from "../components/TaggingPanel";
```

- [ ] **Step 7: Verifikasi**

Run:
```bash
cd frontend && npm run lint && npm run build
```
Expected: build sukses tanpa error TypeScript (warning pre-existing yang tidak terkait boleh ada).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/app/jaringan/page.tsx frontend/src/app/components/TaggingPanel.tsx
git commit -m "feat: wire GPS tagging UI into Jaringan tab"
```

---

### Task 6: Verifikasi end-to-end manual di browser

Tidak ada file diubah — task ini murni verifikasi fungsional penuh sebelum dianggap selesai, sesuai instruksi "start dev server dan uji di browser" untuk perubahan UI.

- [ ] **Step 1: Jalankan backend & frontend**

```bash
cd /home/naufa/workspace/routing_transportation_v2
python3 api/app.py &
cd frontend && npm run dev
```

- [ ] **Step 2: Buka `http://localhost:3030/jaringan` (atau port dev Next.js yang aktif) di Chrome**

- [ ] **Step 3: Simulasikan GPS lewat DevTools (tidak perlu HP asli untuk verifikasi awal)**

Chrome DevTools → ⋮ → More tools → Sensors → Location → pilih "Custom location..." → isi koordinat sekitar salah satu koridor kecil (mis. sekitar halte pertama Feeder Koridor 1).

- [ ] **Step 4: Jalankan alur penuh**

1. Pilih koridor di daftar kiri → klik "Mode Edit: Tagging GPS Halte".
2. Klik "Mulai Sesi Tagging" → izinkan lokasi saat browser minta.
3. Klik "Tag Halte" 3-4 kali (ubah koordinat di DevTools Sensors sedikit tiap kali sebelum tag, supaya titik tidak numpuk di satu tempat) → pastikan tiap tag menambah marker bernomor di peta dan baris baru di daftar.
4. Refresh halaman (`F5`) di tengah sesi → pastikan setelah pilih koridor yang sama & masuk Mode Edit lagi, muncul opsi "Lanjutkan" dan titik-titik sebelumnya tidak hilang.
5. Klik "Selesai Keliling" → masuk layar review, coba klik di peta untuk tambah titik manual, coba ganti nama salah satu titik, coba tombol ↑/↓ untuk reorder, coba ✕ untuk hapus satu titik.
6. Klik "Simpan ke Server" → pastikan sukses (kembali ke tampilan awal Mode Edit, `hasSavedSession` false), lalu keluar Mode Edit dan pastikan garis koridor di peta read-only (`NetworkMapComponent`) masih tampil normal (waypoint jalan tidak rusak).

- [ ] **Step 5: Verifikasi sisi data**

```bash
git diff --stat dataset/network_data_complete.json dataset/network_data_correct_bidirectional.json
ls dataset/*.backup-*.json
```
Pastikan hanya koridor yang diedit yang berubah (`git diff` tanpa `--stat` untuk lihat detail kalau perlu), dan file backup benar-benar dibuat.

**Setelah selesai verifikasi, restore data uji coba ke semula** (langkah sama seperti Task 2 Step 3) sebelum lanjut ke pekerjaan lain, supaya data koridor asli tidak tertinggal dalam kondisi hasil tes.
