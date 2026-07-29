"""
Task 1: Perumnas OPI Jakabaring -> Universitas Sriwijaya case study.
Matches each segment of the paper's documented 22-segment / 56-minute route
against real ground truth (survey/schedule), and reports a data-anchored
total time vs. the system's own estimate. No rounding/smoothing of results.

NOTE ON ROUTE SOURCE: this is the exact 22-segment route produced by the
*unpatched* gmaps_style_route_balanced_ida_star() for this origin/destination
(captured before the ida_star_balanced.py fallback-rate fix in this same
session) -- i.e. the same route documented in the paper's Section 3.2 case
study (total_time_minutes=56.86650973326238, matching the paper's "56 menit").
The now-patched algorithm returns a different (26-segment) route for the same
query, since relaxing the search's pruning changes which path it settles on.
The 22-segment list below is hardcoded from that captured run so this script
validates the actual route the paper describes, not a different one.
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

from backend.experiments.ground_truth import build_traffic_lookup, build_lrt_lookup

SYSTEM_TOTAL_TIME_MINUTES = 56.86650973326238

# (sequence, mode, route_name, from_local, to_local, formula_duration_minutes)
# mode in {WALK, TRANSFER, FEEDER_ANGKOT, LRT}; WALK/TRANSFER have no local stop numbers.
ROUTE_SEGMENTS = [
    (1, "WALK", "Walking", None, None, 5.8677739182350654),
    (2, "FEEDER_ANGKOT", "Feeder Koridor 4", "6", "7", 2.7837594080814134),
    (3, "FEEDER_ANGKOT", "Feeder Koridor 4", "7", "8", 4.059233001789014),
    (4, "FEEDER_ANGKOT", "Feeder Koridor 4", "8", "9", 5.826123460028396),
    (5, "TRANSFER", "Transfer (Walking)", None, None, 5.542007296673028),
    (6, "LRT", "LRT Sumsel", "11", "10", 3.232141343461449),
    (7, "LRT", "LRT Sumsel", "10", "9", 1.655865054581967),
    (8, "LRT", "LRT Sumsel", "9", "8", 1.2042087832886736),
    (9, "LRT", "LRT Sumsel", "8", "7", 0.7513900181824896),
    (10, "TRANSFER", "Transfer (Walking)", None, None, 5.615067274950327),
    (11, "FEEDER_ANGKOT", "Feeder Koridor 7", "8", "9", 0.944687172950147),
    (12, "FEEDER_ANGKOT", "Feeder Koridor 7", "9", "10", 1.1237053894854492),
    (13, "FEEDER_ANGKOT", "Feeder Koridor 7", "10", "11", 1.3332428944428165),
    (14, "FEEDER_ANGKOT", "Feeder Koridor 7", "11", "12", 0.463682844107832),
    (15, "FEEDER_ANGKOT", "Feeder Koridor 7", "12", "13", 1.5181184550576525),
    (16, "FEEDER_ANGKOT", "Feeder Koridor 7", "13", "14", 0.5904450604826647),
    (17, "FEEDER_ANGKOT", "Feeder Koridor 7", "14", "15", 0.48369793090381635),
    (18, "FEEDER_ANGKOT", "Feeder Koridor 7", "15", "16", 0.5704299736865477),
    (19, "FEEDER_ANGKOT", "Feeder Koridor 7", "16", "17", 0.35693571452898376),
    (20, "FEEDER_ANGKOT", "Feeder Koridor 7", "17", "18", 1.0025939174769183),
    (21, "TRANSFER", "Transfer (Walking)", None, None, 6.9777461516994395),
    (22, "WALK", "Walking", None, None, 4.963654669168289),
]


def segment_ground_truth(mode, route_name, from_local, to_local, traffic_lookup, lrt_lookup):
    """Real ground-truth minutes for one route segment, or None if not covered."""
    if mode in ("WALK", "TRANSFER"):
        return None, None  # formula-by-definition, not surveyed
    if mode == "LRT":
        key = (from_local, to_local)
        if key in lrt_lookup:
            return lrt_lookup[key], 'lrt_schedule'
        return None, None
    key = (route_name, from_local, to_local)
    if key in traffic_lookup:
        return traffic_lookup[key], 'survey_30day'
    return None, None


def main():
    traffic_lookup, _, _ = build_traffic_lookup()
    lrt_lookup, _ = build_lrt_lookup()

    system_total = SYSTEM_TOTAL_TIME_MINUTES
    print(f"Route: {len(ROUTE_SEGMENTS)} segments")
    print(f"System estimated total time: {system_total} minutes")
    print()

    n_covered = 0
    n_total = len(ROUTE_SEGMENTS)
    real_time_sum = 0.0
    formula_time_sum = 0.0

    print(f"{'#':>2} {'mode':13s} {'route':22s} {'from':>6s}->{'to':<6s} {'formula_min':>12s} {'real_min':>12s} {'source':12s}")
    for seq, mode, route_name, from_local, to_local, duration_minutes in ROUTE_SEGMENTS:
        real_min, source = segment_ground_truth(mode, route_name, from_local, to_local, traffic_lookup, lrt_lookup)

        if real_min is not None:
            n_covered += 1
            real_time_sum += real_min
        else:
            formula_time_sum += duration_minutes

        fl = from_local if from_local is not None else "-"
        tl = to_local if to_local is not None else "-"
        print(f"{seq:>2} {mode:13s} {route_name:22s} {fl:>6}->{tl:<6} "
              f"{duration_minutes:12.6f} {(real_min if real_min is not None else float('nan')):12.6f} {source or 'formula':12s}")

    data_anchored_total = real_time_sum + formula_time_sum

    print()
    print(f"Total segments: {n_total}")
    print(f"Segments with real ground truth: {n_covered}")
    print(f"Segments without (formula-only): {n_total - n_covered}")
    print(f"Ground-truth coverage for this route: {n_covered/n_total*100:.6f}%")
    print()
    print(f"Sum of REAL ground-truth minutes (covered segments): {real_time_sum:.6f}")
    print(f"Sum of FORMULA-estimated minutes (uncovered segments): {formula_time_sum:.6f}")
    print(f"Data-anchored total time: {data_anchored_total:.6f} minutes")
    print(f"System's own estimated total time: {system_total:.6f} minutes")
    abs_diff = abs(data_anchored_total - system_total)
    pct_error = abs_diff / system_total * 100
    print(f"Absolute difference: {abs_diff:.6f} minutes")
    print(f"Percentage error (system vs data-anchored): {pct_error:.6f}%")


if __name__ == '__main__':
    main()
