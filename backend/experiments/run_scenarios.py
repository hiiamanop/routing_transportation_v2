"""
Task 2: error analysis + normality/significance testing across a real sample
of simple and complex routes, for Enhanced DFS-IDA*, Standard DFS, and
Conventional Routing.

Route categories (straight-line origin-destination distance, since the paper
gives no other quantitative definition):
  simple  : 1.5 km <= distance < 5 km
  complex : 8 km <= distance < 16 km

O-D pairs are real stops sampled from the actual network graph (seeded for
reproducibility), not synthetic points. Ground truth for each algorithm's
predicted route is computed the same way as Task 1 (run_case_study.py):
sum of real survey/schedule minutes for covered edges + the algorithm's own
formula estimate for uncovered edges, evaluated on the SPECIFIC path that
algorithm proposed (paper's own stated methodology, Section 2.3).
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

import io
import contextlib
import random
from datetime import datetime, timezone, timedelta

from scipy import stats

from algorithms.ida_star_routing.data_loader import load_network_data
from algorithms.ida_star_routing.ida_star_balanced import gmaps_style_route_balanced_ida_star
from algorithms.ida_star_routing.data_structures import TransportationMode
from algorithms.ida_star_routing.dijkstra import haversine_distance_km

from backend.experiments.baselines import standard_dfs_route, conventional_route
from backend.experiments.ground_truth import build_traffic_lookup, build_lrt_lookup, stop_id_to_local

WIB = timezone(timedelta(hours=7))
ROUTE_MODES = {TransportationMode.FEEDER_ANGKOT, TransportationMode.LRT, TransportationMode.TEMAN_BUS}

SIMPLE_MIN_KM, SIMPLE_MAX_KM = 1.5, 5.0
COMPLEX_MIN_KM, COMPLEX_MAX_KM = 8.0, 16.0
N_PER_CATEGORY = 10
RANDOM_SEED = 7

ALGORITHMS = ["enhanced_dfs_ida", "standard_dfs", "conventional"]


def route_ground_truth_total(route, traffic_lookup, lrt_lookup):
    """Data-anchored total time for a route: real GT for covered segments,
    formula duration for uncovered -- same rule as Task 1."""
    total = 0.0
    n_covered = 0
    for seg in route.segments:
        real_min = None
        if seg.mode in ROUTE_MODES:
            from_local = stop_id_to_local(seg.from_stop.stop_id)
            to_local = stop_id_to_local(seg.to_stop.stop_id)
            if seg.mode == TransportationMode.LRT:
                real_min = lrt_lookup.get((from_local, to_local))
            else:
                real_min = traffic_lookup.get((seg.route_name, from_local, to_local))
        if real_min is not None:
            total += real_min
            n_covered += 1
        else:
            total += seg.duration_minutes
    return total, n_covered, len(route.segments)


def sample_pairs(graph, category_min_km, category_max_km, n, rng):
    stops = list(graph.stops.values())
    pairs = []
    attempts = 0
    while len(pairs) < n and attempts < 20000:
        attempts += 1
        o = rng.choice(stops)
        d = rng.choice(stops)
        if o.stop_id == d.stop_id:
            continue
        dist = haversine_distance_km(o.lat, o.lon, d.lat, d.lon)
        if category_min_km <= dist < category_max_km:
            pairs.append((o, d, dist))
    return pairs


def run_algorithm(name, graph, o, d):
    # No artificial wall-clock cap here: enhanced_dfs_ida's own internal
    # timeout (15s x up to 9 stop combinations) already bounds worst case,
    # and adding a tighter external cap would unfairly handicap it relative
    # to standard_dfs/conventional, which aren't wall-clock-limited at all.
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        if name == "enhanced_dfs_ida":
            return gmaps_style_route_balanced_ida_star(
                graph=graph, origin_name=o.name, origin_coords=(o.lat, o.lon),
                dest_name=d.name, dest_coords=(d.lat, d.lon),
                optimization_mode="time", departure_time=datetime.now(WIB),
            )
        elif name == "standard_dfs":
            return standard_dfs_route(
                graph=graph, origin_name=o.name, origin_coords=(o.lat, o.lon),
                dest_name=d.name, dest_coords=(d.lat, d.lon),
                optimization_mode="time", departure_time=datetime.now(WIB),
            )
        elif name == "conventional":
            return conventional_route(
                graph=graph, origin_name=o.name, origin_coords=(o.lat, o.lon),
                dest_name=d.name, dest_coords=(d.lat, d.lon),
                optimization_mode="time", departure_time=datetime.now(WIB),
            )


def main():
    graph = load_network_data('dataset/network_data_correct_bidirectional.json')
    traffic_lookup, _, _ = build_traffic_lookup()
    lrt_lookup, _ = build_lrt_lookup()
    rng = random.Random(RANDOM_SEED)

    scenarios = []
    simple_pairs = sample_pairs(graph, SIMPLE_MIN_KM, SIMPLE_MAX_KM, N_PER_CATEGORY, rng)
    complex_pairs = sample_pairs(graph, COMPLEX_MIN_KM, COMPLEX_MAX_KM, N_PER_CATEGORY, rng)
    for o, d, dist in simple_pairs:
        scenarios.append(("simple", o, d, dist))
    for o, d, dist in complex_pairs:
        scenarios.append(("complex", o, d, dist))

    print(f"n simple scenarios sampled: {len(simple_pairs)}")
    print(f"n complex scenarios sampled: {len(complex_pairs)}")
    print(f"n total scenarios: {len(scenarios)}")
    print()

    errors = {alg: [] for alg in ALGORITHMS}  # list of (category, scenario_index, abs_error)
    success_count = {alg: 0 for alg in ALGORITHMS}

    print(f"{'idx':>3} {'cat':8s} {'dist_km':>8s} {'alg':16s} {'success':7s} {'predicted_min':>14s} {'gt_min':>10s} {'abs_error':>10s}")
    for idx, (category, o, d, dist) in enumerate(scenarios):
        for alg in ALGORITHMS:
            route = run_algorithm(alg, graph, o, d)
            if route is None:
                print(f"{idx:>3} {category:8s} {dist:8.3f} {alg:16s} {'NO':7s} {'-':>14s} {'-':>10s} {'-':>10s}")
                continue
            gt_total, n_cov, n_seg = route_ground_truth_total(route, traffic_lookup, lrt_lookup)
            abs_error = abs(route.total_time_minutes - gt_total)
            errors[alg].append((category, idx, abs_error))
            success_count[alg] += 1
            print(f"{idx:>3} {category:8s} {dist:8.3f} {alg:16s} {'YES':7s} {route.total_time_minutes:14.6f} {gt_total:10.6f} {abs_error:10.6f}")

    print()
    print("=== Success counts (out of", len(scenarios), "scenarios) ===")
    for alg in ALGORITHMS:
        print(f"  {alg}: {success_count[alg]}")

    print()
    print("=== Per-algorithm error distribution + normality (Shapiro-Wilk) ===")
    for alg in ALGORITHMS:
        vals = [e for _, _, e in errors[alg]]
        n = len(vals)
        print(f"\n{alg}: n={n}")
        if n < 3:
            print("  n < 3, Shapiro-Wilk not applicable")
            continue
        stat, p = stats.shapiro(vals)
        print(f"  mean_abs_error={sum(vals)/n:.6f}  Shapiro-Wilk W={stat:.6f}  p={p:.6f}  {'NORMAL' if p > 0.05 else 'NOT NORMAL'} (alpha=0.05)")

    print()
    print("=== Paired comparisons (only scenarios where BOTH algorithms succeeded) ===")

    def paired_errors(alg_a, alg_b):
        idx_to_err_a = {idx: e for _, idx, e in errors[alg_a]}
        idx_to_err_b = {idx: e for _, idx, e in errors[alg_b]}
        common = sorted(set(idx_to_err_a) & set(idx_to_err_b))
        a_vals = [idx_to_err_a[i] for i in common]
        b_vals = [idx_to_err_b[i] for i in common]
        return a_vals, b_vals, common

    for other in ["standard_dfs", "conventional"]:
        a_vals, b_vals, common = paired_errors("enhanced_dfs_ida", other)
        n = len(common)
        print(f"\nenhanced_dfs_ida vs {other}: n_pairs={n}")
        if n < 3:
            print("  n_pairs < 3, cannot run a meaningful paired test")
            continue

        _, p_a = stats.shapiro(a_vals)
        _, p_b = stats.shapiro(b_vals)
        both_normal = p_a > 0.05 and p_b > 0.05
        print(f"  Shapiro-Wilk: enhanced p={p_a:.6f}, {other} p={p_b:.6f} -> {'use paired t-test' if both_normal else 'use Wilcoxon signed-rank'}")

        if both_normal:
            t_stat, p_val = stats.ttest_rel(a_vals, b_vals)
            df = n - 1
            print(f"  paired t-test: t={t_stat:.6f}  df={df}  p={p_val:.6f}")
        else:
            try:
                w_stat, p_val = stats.wilcoxon(a_vals, b_vals)
                print(f"  Wilcoxon signed-rank: W={w_stat:.6f}  p={p_val:.6f}  (n_pairs={n}, no df for this test)")
            except ValueError as e:
                print(f"  Wilcoxon signed-rank failed: {e}")


if __name__ == '__main__':
    main()
