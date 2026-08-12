"""
Logika inti penggantian data halte satu koridor (dipakai endpoint tagging
GPS di api/app.py). Modul murni -- tidak baca/tulis file sendiri, supaya
gampang diuji tanpa I/O nyata dan dipakai ulang dari mana saja.

Konteks kenapa ada 2 struktur data (complete_data & bidir_data): API live
(`api/app.py`) memuat graf routing dari network_data_correct_bidirectional.json,
BUKAN network_data_complete.json. File itu turunan dari network_data_complete.json,
tapi juga punya key route_waypoints/route_stop_anchors yg TIDAK ada di file
asal. Makanya replace_corridor_stops() harus dipanggil utk KEDUA dict, dan
tidak boleh membangun ulang bidir_data dari nol (akan menghapus 2 key itu).

Semua koridor di file bidir live SUDAH dua-arah (diverifikasi langsung thd
data produksi: 747/748 edge di network_data_correct_bidirectional.json
punya pasangan balik) -- BUKAN cuma 2 koridor "linear" seperti asumsi awal
scripts/create_correct_bidirectional.py (skrip itu ternyata tidak
mencerminkan cara file live ini sebenarnya dibuat). Makanya
replace_corridor_stops() SELALU menambah edge balik utk bidir_data, utk
koridor mana pun yg ditag ulang -- supaya konsisten dgn koridor lain yg
tidak disentuh.
"""

from math import radians, sin, cos, sqrt, atan2


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

    max_id = max(
        max((n["id"] for n in complete_data["nodes"]), default=-1),
        max((n["id"] for n in bidir_data["nodes"]), default=-1),
    )
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
                        add_reverse=True)

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

    fk1_bidir_edges = [e for e in bidir["edges"] if e["route"] == "Feeder Koridor 1"]
    assert len(fk1_bidir_edges) == 4, "3 halte -> 2 edge forward + 2 edge reverse di bidir_data (semua koridor sekarang dua-arah)"
    assert sum(1 for e in fk1_bidir_edges if e.get("is_reverse")) == 2, "semua koridor (bukan cuma yg dulu di LINEAR_ROUTES) harus dpt edge balik di bidir_data"

    # bidir_data: route_waypoints/route_stop_anchors TIDAK boleh hilang
    assert "route_waypoints" in bidir and bidir["route_waypoints"]
    assert "route_stop_anchors" in bidir and bidir["route_stop_anchors"]

    # Koridor kedua (LRT Sumsel) -- tag ulang juga harus MENGHASILKAN edge
    # balik di bidir_data, sama seperti semua koridor lain sekarang
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
