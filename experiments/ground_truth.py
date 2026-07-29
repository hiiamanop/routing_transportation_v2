"""
Rebuilds real (non-formula) per-edge travel times from the actual collected data:
- dataset/traffic_30days/*.csv: 30-day GPS survey logs, 8 Feeder + 2 Teman Bus corridors
- dataset/lrt/jadwal.csv + titik.csv: official LRT Sumsel timetable

Reports ground-truth coverage against the 423-edge network graph
(dataset/network_data_correct_bidirectional.json), and exposes lookups other
scripts can use to compute a "data-anchored" travel time for any given route.
"""
import csv
import glob
import json
from collections import defaultdict

NETWORK_PATH = "dataset/network_data_correct_bidirectional.json"
TRAFFIC_GLOB = "dataset/traffic_30days/*.csv"
LRT_JADWAL = "dataset/lrt/jadwal.csv"

# LRT station name (jadwal.csv) -> network local stop number (titik.csv "Bus Stop" id).
# Determined by matching titik.csv coordinates against jadwal.csv's physical (south-to-north)
# station sequence -- NOT the stop_id's local number, which is an arbitrary data-entry order.
# "Ampera" in jadwal.csv has no direct name match in the network/titik data; by coordinate
# adjacency (Jembatan Ampera sits beside Pasar 16 Ilir) it corresponds to local stop 10.
LRT_NAME_TO_LOCAL = {
    'Bandara': '5', 'Asrama Haji': '6', 'Punti Kayu': '1', 'RSUD': '2',
    'Garuda Dempo': '3', 'Demang': '4', 'Bumi Sriwijaya': '7', 'Dishub': '8',
    'Cinde': '9', 'Ampera': '10', 'Polresta': '11', 'Jakabaring': '12', 'DJKA': '13',
}


def load_network():
    d = json.load(open(NETWORK_PATH))
    id_to_stop_id = {n['id']: n['stop_id'] for n in d['nodes']}
    return d, id_to_stop_id


def stop_id_to_local(stop_id):
    """'Feeder_Koridor_4_6' -> local stop number '6'."""
    return stop_id.rsplit('_', 1)[-1]


def build_traffic_lookup():
    """(corridor, from_local, to_local) -> mean travel_time_min across all 30-day survey rows."""
    sums = defaultdict(float)
    counts = defaultdict(int)
    files = glob.glob(TRAFFIC_GLOB)
    for path in files:
        with open(path) as f:
            for row in csv.DictReader(f):
                # CSV corridor names use "Angkot Feeder Koridor N"; the graph's edge
                # 'route' field uses "Feeder Koridor N" (no "Angkot " prefix) -- normalize
                # so the join actually matches instead of silently missing every Feeder row.
                corridor = row['corridor'].replace('Angkot ', '', 1)
                key = (corridor, row['from_stop'], row['to_stop'])
                sums[key] += float(row['travel_time_min'])
                counts[key] += 1
    return {k: sums[k] / counts[k] for k in sums}, counts, files


def _parse_wib(t):
    t = t.replace(' WIB', '').strip()
    h, m = t.split('.')
    return int(h) * 60 + int(m)


def build_lrt_lookup():
    """(from_local, to_local) -> mean inter-station minutes, from both-direction timetables."""
    rows = list(csv.reader(open(LRT_JADWAL)))
    directions, current = [], []
    for r in rows:
        if not any(r) or (r[0] and 'Perjalanan' in r[0]):
            if current:
                directions.append(current)
                current = []
            continue
        if len(r) == 3 and r[1] and r[2]:
            current.append(r)
    if current:
        directions.append(current)

    pair_times = defaultdict(list)
    unmatched_names = set()
    for direction in directions:
        for i in range(len(direction) - 1):
            name_a, t1a, t1b = direction[i]
            name_b, t2a, t2b = direction[i + 1]
            local_a = LRT_NAME_TO_LOCAL.get(name_a.strip())
            local_b = LRT_NAME_TO_LOCAL.get(name_b.strip())
            if not local_a:
                unmatched_names.add(name_a.strip())
            if not local_b:
                unmatched_names.add(name_b.strip())
            if not local_a or not local_b:
                continue
            for ta, tb in [(t1a, t2a), (t1b, t2b)]:
                diff = _parse_wib(tb) - _parse_wib(ta)
                if diff < 0:
                    diff += 24 * 60
                pair_times[(local_a, local_b)].append(diff)
    return {k: sum(v) / len(v) for k, v in pair_times.items()}, unmatched_names


def edge_ground_truth(edge, id_to_stop_id, traffic_lookup, lrt_lookup):
    """Returns (real_minutes, source) if edge has real ground truth, else (None, None)."""
    route = edge['route']
    from_local = stop_id_to_local(id_to_stop_id[edge['from']])
    to_local = stop_id_to_local(id_to_stop_id[edge['to']])
    if route == 'LRT Sumsel':
        key = (from_local, to_local)
        if key in lrt_lookup:
            return lrt_lookup[key], 'lrt_schedule'
        return None, None
    key = (route, from_local, to_local)
    if key in traffic_lookup:
        return traffic_lookup[key], 'survey_30day'
    return None, None


def compute_full_coverage():
    d, id_to_stop_id = load_network()
    traffic_lookup, traffic_counts, files = build_traffic_lookup()
    lrt_lookup, unmatched_lrt_names = build_lrt_lookup()

    covered, uncovered = [], []
    for e in d['edges']:
        real_min, source = edge_ground_truth(e, id_to_stop_id, traffic_lookup, lrt_lookup)
        if real_min is not None:
            covered.append((e, real_min, source))
        else:
            uncovered.append(e)
    return covered, uncovered, unmatched_lrt_names, len(files)


if __name__ == '__main__':
    covered, uncovered, unmatched_lrt_names, n_files = compute_full_coverage()
    total = len(covered) + len(uncovered)
    print(f"Traffic CSV files loaded: {n_files}")
    print(f"Unmatched LRT station names in jadwal.csv: {unmatched_lrt_names}")
    print(f"Total edges: {total}")
    print(f"Covered by real ground truth: {len(covered)}")
    print(f"Uncovered (formula-only): {len(uncovered)}")
    print(f"Coverage: {len(covered)/total*100:.4f}%")

    by_source = defaultdict(int)
    for _, _, src in covered:
        by_source[src] += 1
    print(f"Breakdown by source: {dict(by_source)}")

    by_route_uncovered = defaultdict(int)
    for e in uncovered:
        by_route_uncovered[e['route']] += 1
    print(f"Uncovered edges by route: {dict(by_route_uncovered)}")
