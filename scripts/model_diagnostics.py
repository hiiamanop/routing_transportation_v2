#!/usr/bin/env python3
"""Diagnostik sampel dan perbandingan MNL dasar vs ASC kendaraan pribadi."""

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

try:
    from scripts.clean_survey_data import ATTRIBUTE_KEYS, read_csv_rows
    from scripts.estimate_mnl import build_report, cluster_robust_se, fit_mnl, load_long_format
except ModuleNotFoundError:  # eksekusi langsung: python scripts/model_diagnostics.py
    from clean_survey_data import ATTRIBUTE_KEYS, read_csv_rows
    from estimate_mnl import build_report, cluster_robust_se, fit_mnl, load_long_format


def alternative_group(row):
    optimized_for = row.get("optimized_for")
    if optimized_for == "private_vehicle":
        return "private_vehicle"
    if optimized_for == "ride_hailing":
        return "ride_hailing"
    return "transit"


def _correlations(rows):
    matrix = np.array([[float(row[key]) for key in ATTRIBUTE_KEYS] for row in rows])
    result = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.corrcoef(matrix, rowvar=False)
    for i, left in enumerate(ATTRIBUTE_KEYS):
        result[left] = {}
        for j, right in enumerate(ATTRIBUTE_KEYS):
            value = corr[i, j]
            result[left][right] = None if not np.isfinite(value) else float(value)
    return result


def build_diagnostics(rows):
    observations = defaultdict(list)
    for row in rows:
        observations[row["observation_id"]].append(row)

    respondent_counts = Counter(choice_set[0].get("respondent_id", "")
                                for choice_set in observations.values())
    choices = Counter()
    for choice_set in observations.values():
        chosen = next(row for row in choice_set if float(row["chosen"]) == 1)
        choices[alternative_group(chosen)] += 1

    variation = {}
    for attribute in ATTRIBUTE_KEYS:
        varying = sum(
            len({float(row[attribute]) for row in choice_set}) > 1
            for choice_set in observations.values()
        )
        variation[attribute] = {
            "varying_observations": varying,
            "constant_observations": len(observations) - varying,
            "varying_percentage": round(100 * varying / len(observations), 1),
        }

    return {
        "sample": {
            "rows": len(rows),
            "observations": len(observations),
            "respondents": len(respondent_counts),
            "respondents_with_multiple_observations": sum(count > 1 for count in respondent_counts.values()),
            "max_observations_per_respondent": max(respondent_counts.values(), default=0),
            "observations_with_preferences": sum(
                bool(choice_set[0].get("pref_time", "")) for choice_set in observations.values()
            ),
        },
        "choices": {"by_group": dict(choices)},
        "within_choice_set_variation": variation,
        "correlations": _correlations(rows),
    }


def estimate_model(path, use_asc=False):
    X_list, chosen, features, _, respondents = load_long_format(
        path, use_private_vehicle_asc=use_asc, return_respondent_ids=True
    )
    fit = fit_mnl(X_list, chosen)
    clustered = cluster_robust_se(fit["beta"], fit["cov"], X_list, chosen, respondents)
    report = build_report(fit, X_list, features, clustered_se=clustered)
    parameter_count = len(features)
    report["aic"] = float(2 * parameter_count - 2 * report["log_likelihood"])
    report["bic"] = float(math.log(len(X_list)) * parameter_count - 2 * report["log_likelihood"])
    report["respondent_clusters"] = len(set(respondents))
    report["primary_standard_error"] = (
        "ordinary" if len(set(respondents)) == len(respondents) else "clustered"
    )
    return report


def write_markdown(path, report):
    sample = report["sample"]
    choices = report["choices"]["by_group"]
    variation = report["within_choice_set_variation"]
    basic = report["models"]["basic"]
    asc = report["models"]["private_vehicle_asc"]

    lines = [
        "# Diagnostik Model Pemilihan Moda", "",
        "## Sampel", "",
        f"- Observasi valid: **{sample['observations']}**",
        f"- Responden unik: **{sample['respondents']}**",
        f"- Responden dengan observasi berulang: **{sample['respondents_with_multiple_observations']}**",
        f"- Observasi dengan preferensi: **{sample['observations_with_preferences']}**", "",
        "## Pilihan menurut kelompok", "",
        "| Kelompok | Pilihan |", "|---|---:|",
    ]
    for group in ("transit", "private_vehicle", "ride_hailing"):
        lines.append(f"| {group} | {choices.get(group, 0)} |")

    lines += ["", "## Variasi atribut di dalam choice set", "",
              "| Atribut | Observasi bervariasi | Persentase |", "|---|---:|---:|"]
    for attribute, values in variation.items():
        lines.append(
            f"| {attribute} | {values['varying_observations']} | {values['varying_percentage']:.1f}% |"
        )

    lines += ["", "## Perbandingan model", "",
              "| Model | LL | McFadden rho² | AIC | BIC |", "|---|---:|---:|---:|---:|",
              f"| Dasar | {basic['log_likelihood']:.3f} | {basic['rho_squared_mcfadden']:.4f} | {basic['aic']:.2f} | {basic['bic']:.2f} |",
              f"| ASC kendaraan pribadi | {asc['log_likelihood']:.3f} | {asc['rho_squared_mcfadden']:.4f} | {asc['aic']:.2f} | {asc['bic']:.2f} |",
              "", "## Koefisien model ASC kendaraan pribadi", "",
              "| Fitur | Beta | SE naïf | SE cluster | t cluster | Signifikan 5% |",
              "|---|---:|---:|---:|---:|---|",]
    for feature, coefficient in asc["coefficients"].items():
        lines.append(
            f"| {feature} | {coefficient['beta']:.6g} | {coefficient['se']:.6g} | "
            f"{coefficient['clustered_se']:.6g} | {coefficient['clustered_t_stat']:.2f} | "
            f"{'Ya' if coefficient['clustered_significant_at_5pct'] else 'Tidak'} |"
        )
    lines += ["", "> ASC memakai angkutan umum sebagai kategori acuan; ride-hailing tidak diklasifikasikan sebagai kendaraan pribadi.", ""]

    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--json", required=True)
    parser.add_argument("--markdown", required=True)
    parser.add_argument("--history", required=True)
    args = parser.parse_args()

    rows, _ = read_csv_rows(args.input)
    report = build_diagnostics(rows)
    report["models"] = {
        "basic": estimate_model(Path(args.input)),
        "private_vehicle_asc": estimate_model(Path(args.input), use_asc=True),
    }

    json_path = Path(args.json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(args.markdown, report)

    history_path = Path(args.history)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report["models"]["private_vehicle_asc"], ensure_ascii=False) + "\n")

    print(json.dumps(report["sample"], indent=2, ensure_ascii=False))
    print(f"Laporan: {json_path} dan {args.markdown}")


if __name__ == "__main__":
    main()
