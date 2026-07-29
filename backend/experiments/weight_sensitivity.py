"""
Task 3.2: weight sensitivity check.

IMPORTANT FINDING (see report): no w1-w4 weighted-sum multi-objective
function exists anywhere in the codebase. `calculate_optimization_score()`
in data_structures.py is the only related code, uses a DIFFERENT 3-criteria
formula (time/cost/transfers, weights 0.4/0.3/0.3, no distance term), is only
called from the unused ida_star.py variant (not ida_star_balanced.py, which
is what api/app.py actually serves), and every routing call in this
codebase passes optimization_mode="time" -- meaning production routing
never runs any weighted-sum scoring at all.

This script is a from-scratch reconstruction of the paper's *described*
formula (Section 2.3.2 text: normalized time/cost/distance/transfers,
w=[0.40,0.30,0.15,0.15]) applied to real candidate routes -- it is NOT the
original methodology's code, because that code does not exist. Candidates
per O-D pair are the real routes returned by the three implemented
algorithms (Enhanced DFS-IDA*, Standard DFS, Conventional Routing), which
are genuinely different real paths with different time/cost/distance/
transfer profiles -- not synthetic data.
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

import io
import contextlib
from datetime import datetime, timezone, timedelta

from algorithms.ida_star_routing.data_loader import load_network_data
from algorithms.ida_star_routing.ida_star_balanced import gmaps_style_route_balanced_ida_star
from backend.experiments.baselines import standard_dfs_route, conventional_route

WIB = timezone(timedelta(hours=7))

BASE_WEIGHTS = {"time": 0.40, "cost": 0.30, "distance": 0.15, "transfers": 0.15}

TEST_PAIRS = [
    ("Perumnas OPI Jakabaring", (-3.0438, 104.7861), "Universitas Sriwijaya", (-2.98525, 104.732880)),
    # shorter real pairs, picked to give Standard DFS (depth<=15) a realistic chance to also succeed
    ("Talang Kelapa area", (-2.94493176, 104.6871163), "Griya Palm Tl. Kelapa area", (-2.93895688, 104.68877294)),
    ("Punti Kayu LRT area", (-2.940535, 104.723820), "Demang LRT area", (-2.964308, 104.736048)),
]


def get_candidates(graph, origin_name, origin_coords, dest_name, dest_coords):
    candidates = []
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        for name, fn in [
            ("enhanced_dfs_ida", gmaps_style_route_balanced_ida_star),
            ("standard_dfs", standard_dfs_route),
            ("conventional", conventional_route),
        ]:
            route = fn(graph=graph, origin_name=origin_name, origin_coords=origin_coords,
                       dest_name=dest_name, dest_coords=dest_coords,
                       optimization_mode="time", departure_time=datetime.now(WIB))
            if route is not None:
                candidates.append((name, route))
    return candidates


def normalize(values):
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def weighted_scores(candidates, weights):
    times = [r.total_time_minutes for _, r in candidates]
    costs = [r.total_cost for _, r in candidates]
    dists = [r.total_distance_km for _, r in candidates]
    transfers = [r.num_transfers for _, r in candidates]

    t_n, c_n, d_n, x_n = normalize(times), normalize(costs), normalize(dists), normalize(transfers)

    scores = []
    for i in range(len(candidates)):
        s = (weights["time"] * t_n[i] + weights["cost"] * c_n[i] +
             weights["distance"] * d_n[i] + weights["transfers"] * x_n[i])
        scores.append(s)
    return scores


def shifted_weights(base, key, delta):
    """Shift weights[key] by delta, rescale the rest to keep their
    relative proportions but sum to 1 -- matches the paper's own wording
    ('menjaga proporsi bobot parameter lainnya tetap konsisten')."""
    new = dict(base)
    new[key] = base[key] + delta
    remaining_keys = [k for k in base if k != key]
    remaining_total_old = sum(base[k] for k in remaining_keys)
    remaining_total_new = 1.0 - new[key]
    for k in remaining_keys:
        new[k] = base[k] / remaining_total_old * remaining_total_new
    return new


def main():
    graph = load_network_data('dataset/network_data_correct_bidirectional.json')

    for origin_name, origin_coords, dest_name, dest_coords in TEST_PAIRS:
        print(f"\n=== {origin_name} -> {dest_name} ===")
        candidates = get_candidates(graph, origin_name, origin_coords, dest_name, dest_coords)
        print(f"Candidates found: {[name for name, _ in candidates]} (n={len(candidates)})")
        for name, r in candidates:
            print(f"  {name}: time={r.total_time_minutes:.4f}min cost={r.total_cost} "
                  f"dist={r.total_distance_km:.4f}km transfers={r.num_transfers}")

        if len(candidates) < 2:
            print("  fewer than 2 candidates -- cannot rank / cannot test sensitivity")
            continue

        base_scores = weighted_scores(candidates, BASE_WEIGHTS)
        base_ranking = sorted(range(len(candidates)), key=lambda i: base_scores[i])
        base_best = candidates[base_ranking[0]][0]
        print(f"  BASE weights {BASE_WEIGHTS}: scores={[f'{s:.6f}' for s in base_scores]}  best={base_best}")

        for delta in (-0.10, 0.10):
            shifted = shifted_weights(BASE_WEIGHTS, "time", delta)
            new_scores = weighted_scores(candidates, shifted)
            new_ranking = sorted(range(len(candidates)), key=lambda i: new_scores[i])
            new_best = candidates[new_ranking[0]][0]

            pct_shifts = []
            for i in range(len(candidates)):
                if base_scores[i] == 0:
                    continue
                pct_shifts.append(abs(new_scores[i] - base_scores[i]) / abs(base_scores[i]) * 100)
            max_pct_shift = max(pct_shifts) if pct_shifts else float('nan')

            print(f"  w1={shifted['time']:.4f} (delta={delta:+.2f}) weights={ {k: round(v,4) for k,v in shifted.items()} }")
            print(f"    scores={[f'{s:.6f}' for s in new_scores]}  best={new_best}  "
                  f"ranking_changed={new_best != base_best}  max_score_shift_pct={max_pct_shift:.6f}%")


if __name__ == '__main__':
    main()
