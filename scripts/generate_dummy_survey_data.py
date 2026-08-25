#!/usr/bin/env python3
"""
Data SINTETIS -- HANYA untuk menguji pipa data (export_long_format.py +
skrip estimasi S-4 nanti), BUKAN pengganti survei nyata. Setiap baris
ditandai "synthetic": true, dan ditulis ke file *.dummy.jsonl terpisah dari
data survei asli (choices.jsonl / respondents.jsonl) supaya tidak pernah
bisa tercampur atau tidak sengaja dipakai sbg dasar estimasi utk naskah.

Yang REAL: koordinat asal-tujuan (dari halte sungguhan di dataset jaringan)
dan atribut tiap alternatif (dihitung oleh find_route_alternatives() --
mesin routing yg sama persis dgn yg dipakai aplikasi).

Yang DIKARANG: karakteristik responden dan alternatif mana yang "dipilih"
-- disimulasikan dgn model utilitas acak sederhana, bukan perilaku manusia
sungguhan. JANGAN dipakai sbg dasar kesimpulan penelitian.

Usage:
    python scripts/generate_dummy_survey_data.py --n-respondents 40 --trips-per-respondent 5
"""

import argparse
import json
import math
import random
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from algorithms.routing.data_loader import load_network_data  # noqa: E402
from core.gmaps_style_routing import (  # noqa: E402
    find_route_alternatives, route_attributes, PREFERENCE_CRITERIA,
)

WIB_TZ = timezone(timedelta(hours=7))

# Sama persis dgn true_beta di scripts/estimate_mnl.py:demo() (BASE_ATTRIBUTES
# order: time_minutes, cost_rupiah, transfers, access_km, comfort, reliability)
# + interaksi waktu/biaya x preferensi -- dipakai sbg SATU sumber kebenaran
# spy hasil `estimate_mnl.py --interactions` bisa dicek: apakah beta yg
# dipulihkan mendekati angka ini. Ini bukan klaim ttg perilaku Palembang
# sungguhan, cuma parameter model yg dipakai buat menguji pipa estimasi.
TRUE_BETA = {
    "time_minutes": -0.05, "cost_rupiah": -0.0004, "transfers": -0.3,
    "access_km": -0.5, "comfort": 0.4, "reliability": 0.4,
}
TRUE_GAMMA = {"time_minutes": -0.01, "cost_rupiah": -0.00006}  # x pref_time / pref_cost

AGE_OPTIONS = ["<18", "18-25", "26-35", "36-50", ">50"]
GENDER_OPTIONS = ["Laki-laki", "Perempuan"]
OCCUPATION_OPTIONS = ["Pelajar/Mahasiswa", "Karyawan", "Wiraswasta", "PNS/TNI/Polri", "Lainnya"]
INCOME_OPTIONS = ["<1 juta", "1-3 juta", "3-5 juta", "5-10 juta", ">10 juta"]
VEHICLE_OPTIONS = ["Tidak punya", "Motor", "Mobil", "Motor dan mobil"]
TRIP_PURPOSE_OPTIONS = ["Kerja", "Sekolah/Kuliah", "Belanja/Rekreasi", "Lainnya"]
FREQUENCY_OPTIONS = ["Setiap hari", "Beberapa kali seminggu", "Beberapa kali sebulan", "Jarang/tidak pernah"]


def make_synthetic_respondent(rng: random.Random) -> dict:
    return {
        "synthetic": True,
        "timestamp": datetime.now(WIB_TZ).isoformat(),
        "respondent_id": f"dummy-{rng.randrange(10**9):09d}",
        "age": rng.choice(AGE_OPTIONS),
        "gender": rng.choice(GENDER_OPTIONS),
        "occupation": rng.choice(OCCUPATION_OPTIONS),
        "income": rng.choice(INCOME_OPTIONS),
        "vehicle_ownership": rng.choice(VEHICLE_OPTIONS),
        "trip_purpose": rng.choice(TRIP_PURPOSE_OPTIONS),
        "transit_frequency": rng.choice(FREQUENCY_OPTIONS),
    }


def simulate_choice(rng: random.Random, alternatives: list, has_vehicle: bool,
                     preferences: dict) -> int:
    """
    Model utilitas acak (RUM) konsisten dgn MNL: U = sum(TRUE_BETA * atribut)
    + sum(TRUE_GAMMA * atribut * preferensi terkait), lalu pilihan digambar
    dari distribusi softmax(U) -- proses generatif yg SAMA persis dgn yg
    diasumsikan scripts/estimate_mnl.py, spy beta hasil estimasi pd data ini
    bisa dicek terhadap TRUE_BETA/TRUE_GAMMA. Responden tanpa kendaraan
    pribadi tidak akan pernah "memilih" alternatif Kendaraan Pribadi --
    constraint realistis minimal (tidak bisa naik kendaraan yang tak dimiliki).
    """
    utilities = []
    blocked = []
    for alt in alternatives:
        is_private = alt["optimized_for"] == "private_vehicle"
        blocked.append(not has_vehicle and is_private)
        attrs = route_attributes(alt["route"])
        u = sum(TRUE_BETA[k] * attrs[k] for k in TRUE_BETA)
        u += TRUE_GAMMA["time_minutes"] * attrs["time_minutes"] * preferences["time"]
        u += TRUE_GAMMA["cost_rupiah"] * attrs["cost_rupiah"] * preferences["cost"]
        utilities.append(u)

    if all(blocked):
        return 0  # semua diblokir (tidak realistis, tapi jaga2)

    max_u = max(u for u, b in zip(utilities, blocked) if not b)
    weights = [0.0 if b else math.exp(u - max_u) for u, b in zip(utilities, blocked)]
    return rng.choices(range(len(alternatives)), weights=weights, k=1)[0]


def generate(n_respondents: int, trips_per_respondent: int, seed: int,
             network_path: str, out_dir: Path):
    rng = random.Random(seed)
    graph = load_network_data(network_path)
    stops = list(graph.stops.values())

    respondents = []
    choices = []

    for _ in range(n_respondents):
        respondent = make_synthetic_respondent(rng)
        respondents.append(respondent)
        has_vehicle = respondent["vehicle_ownership"] != "Tidak punya"

        preferences = {c: rng.randint(1, 5) for c in PREFERENCE_CRITERIA}

        made_trips = 0
        attempts = 0
        while made_trips < trips_per_respondent and attempts < trips_per_respondent * 4:
            attempts += 1
            origin, dest = rng.sample(stops, 2)
            departure_time = datetime.now(WIB_TZ).replace(
                hour=rng.randint(6, 20), minute=rng.randint(0, 59))

            alternatives = find_route_alternatives(
                graph=graph,
                origin_name=origin.name, origin_coords=(origin.lat, origin.lon),
                dest_name=dest.name, dest_coords=(dest.lat, dest.lon),
                departure_time=departure_time,
            )
            if len(alternatives) < 2:
                continue  # sama seperti UI nyata -- himpunan pilihan perlu >=2 opsi

            chosen_index = simulate_choice(rng, alternatives, has_vehicle, preferences)

            choices.append({
                "synthetic": True,
                "timestamp": datetime.now(WIB_TZ).isoformat(),
                "respondent_id": respondent["respondent_id"],
                "preferences": preferences,
                "origin": {"name": origin.name, "lat": origin.lat, "lon": origin.lon},
                "destination": {"name": dest.name, "lat": dest.lat, "lon": dest.lon},
                "departure_time": departure_time.isoformat(),
                "choice_set": [
                    {
                        "label": alt["label"],
                        "optimized_for": alt["optimized_for"],
                        "attributes": route_attributes(alt["route"]),
                    }
                    for alt in alternatives
                ],
                "chosen_index": chosen_index,
            })
            made_trips += 1

    out_dir.mkdir(parents=True, exist_ok=True)
    respondents_path = out_dir / "respondents.dummy.jsonl"
    choices_path = out_dir / "choices.dummy.jsonl"

    with open(respondents_path, "w", encoding="utf-8") as f:
        for r in respondents:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(choices_path, "w", encoding="utf-8") as f:
        for c in choices:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    return respondents_path, choices_path, len(respondents), len(choices)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-respondents", type=int, default=40)
    parser.add_argument("--trips-per-respondent", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--network", default="dataset/network_data_correct_bidirectional.json")
    parser.add_argument("--out-dir", default="dataset/survey")
    args = parser.parse_args()

    print("=" * 70)
    print("  DATA SINTETIS -- BUKAN DATA SURVEI NYATA")
    print("  Jangan dipakai sbg dasar kesimpulan penelitian.")
    print(f"  TRUE_BETA (base)  = {TRUE_BETA}")
    print(f"  TRUE_GAMMA (x pref) = {TRUE_GAMMA}")
    print("  Bandingkan dgn output 'scripts/estimate_mnl.py --interactions'")
    print("  buat cek apakah estimator memulihkan angka2 ini.")
    print("=" * 70)

    resp_path, choice_path, n_resp, n_choice = generate(
        args.n_respondents, args.trips_per_respondent, args.seed,
        args.network, Path(args.out_dir),
    )

    print(f"\nOK - {n_resp} responden sintetis -> {resp_path}")
    print(f"OK - {n_choice} observasi pilihan sintetis -> {choice_path}")


if __name__ == "__main__":
    main()
