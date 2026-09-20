#!/usr/bin/env python3
"""Bandingkan spesifikasi MNL + ASC dan sensitivitas terhadap atribut/sampel."""

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

try:
    from scripts.clean_survey_data import ATTRIBUTE_KEYS, read_csv_rows
    from scripts.estimate_mnl import build_report, cluster_robust_se, fit_mnl
except ModuleNotFoundError:  # eksekusi langsung
    from clean_survey_data import ATTRIBUTE_KEYS, read_csv_rows
    from estimate_mnl import build_report, cluster_robust_se, fit_mnl

ASC = "asc_private_vehicle"
SPECS = {
    "full_asc": list(ATTRIBUTE_KEYS) + [ASC],
    "without_access": [key for key in ATTRIBUTE_KEYS if key != "access_km"] + [ASC],
    "without_transfers": [key for key in ATTRIBUTE_KEYS if key != "transfers"] + [ASC],
    "without_access_transfers": [
        key for key in ATTRIBUTE_KEYS if key not in ("access_km", "transfers")
    ] + [ASC],
    "without_ride_hailing": list(ATTRIBUTE_KEYS) + [ASC],
}


def prepare_choice_sets(rows, exclude_ride_hailing=False):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["observation_id"]].append(row)

    kept, dropped = [], Counter()
    for choice_set in grouped.values():
        if exclude_ride_hailing:
            chosen = next(row for row in choice_set if float(row["chosen"]) == 1)
            if chosen.get("optimized_for") == "ride_hailing":
                dropped["chosen_ride_hailing"] += 1
                continue
            choice_set = [row for row in choice_set if row.get("optimized_for") != "ride_hailing"]
        if len(choice_set) < 2:
            dropped["fewer_than_two_alternatives"] += 1
            continue
        kept.append(choice_set)
    return kept, dict(dropped)


def _matrix(choice_set, features):
    values = []
    for row in choice_set:
        feature_row = []
        for feature in features:
            if feature == ASC:
                feature_row.append(1.0 if row.get("optimized_for") == "private_vehicle" else 0.0)
            else:
                feature_row.append(float(row[feature]))
        values.append(feature_row)
    return np.array(values)


def estimate_spec(choice_sets, features):
    X_list = [_matrix(choice_set, features) for choice_set in choice_sets]
    chosen = [next(i for i, row in enumerate(choice_set) if float(row["chosen"]) == 1)
              for choice_set in choice_sets]
    respondents = [choice_set[0].get("respondent_id", "") or f"observation:{i}"
                   for i, choice_set in enumerate(choice_sets)]
    fit = fit_mnl(X_list, chosen)
    clustered = cluster_robust_se(fit["beta"], fit["cov"], X_list, chosen, respondents)
    report = build_report(fit, X_list, features, clustered_se=clustered)
    k = len(features)
    report.update({
        "aic": float(2 * k - 2 * report["log_likelihood"]),
        "bic": float(math.log(len(X_list)) * k - 2 * report["log_likelihood"]),
        "parameters": k,
        "respondent_clusters": len(set(respondents)),
        "primary_standard_error": (
            "ordinary" if len(set(respondents)) == len(respondents) else "clustered"
        ),
    })
    return report


def _chi_square_survival(statistic, degrees_of_freedom):
    if degrees_of_freedom == 1:
        return math.erfc(math.sqrt(statistic / 2))
    if degrees_of_freedom == 2:
        return math.exp(-statistic / 2)
    raise ValueError("Only 1 or 2 degrees of freedom are needed by this analysis.")


def likelihood_ratio_test(full_ll, reduced_ll, degrees_of_freedom):
    statistic = max(0.0, 2 * (full_ll - reduced_ll))
    return {
        "statistic": statistic,
        "degrees_of_freedom": degrees_of_freedom,
        "p_value": _chi_square_survival(statistic, degrees_of_freedom),
    }


def run_sensitivity_analysis(rows):
    regular_sets, _ = prepare_choice_sets(rows)
    no_ride_hailing_sets, ride_hailing_dropped = prepare_choice_sets(
        rows, exclude_ride_hailing=True
    )
    models = {}
    for name, features in SPECS.items():
        choice_sets = no_ride_hailing_sets if name == "without_ride_hailing" else regular_sets
        models[name] = estimate_spec(choice_sets, features)

    full = models["full_asc"]
    likelihood_tests = {}
    for name, removed_count in (
        ("without_access", 1),
        ("without_transfers", 1),
        ("without_access_transfers", 2),
    ):
        likelihood_tests[name] = likelihood_ratio_test(
            full["log_likelihood"], models[name]["log_likelihood"], removed_count
        )

    stable_features = ("time_minutes", "cost_rupiah", "comfort", "reliability", ASC)
    stability = {}
    for feature in stable_features:
        estimates = {
            name: model["coefficients"][feature]["beta"]
            for name, model in models.items() if feature in model["coefficients"]
        }
        signs = {0 if value == 0 else (1 if value > 0 else -1) for value in estimates.values()}
        stability[feature] = {
            "estimates": estimates,
            "same_sign_across_models": len(signs) == 1,
            "minimum": min(estimates.values()),
            "maximum": max(estimates.values()),
        }

    return {
        "models": models,
        "likelihood_ratio_tests": likelihood_tests,
        "coefficient_stability": stability,
        "without_ride_hailing_exclusions": ride_hailing_dropped,
    }


def write_markdown(path, report):
    labels = {
        "full_asc": "Penuh + ASC",
        "without_access": "Tanpa akses",
        "without_transfers": "Tanpa transfer",
        "without_access_transfers": "Tanpa akses & transfer",
        "without_ride_hailing": "Tanpa ride-hailing",
    }
    lines = [
        "# Analisis Sensitivitas Model MNL", "",
        "## Perbandingan kecocokan model", "",
        "| Model | N | Parameter | LL | rho² | AIC | BIC |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, model in report["models"].items():
        lines.append(
            f"| {labels[name]} | {model['n_observations']} | {model['parameters']} | "
            f"{model['log_likelihood']:.3f} | {model['rho_squared_mcfadden']:.4f} | "
            f"{model['aic']:.2f} | {model['bic']:.2f} |"
        )

    lines += ["", "## Likelihood-ratio test terhadap model penuh", "",
              "| Model tereduksi | LR | df | p-value |", "|---|---:|---:|---:|"]
    for name, result in report["likelihood_ratio_tests"].items():
        lines.append(
            f"| {labels[name]} | {result['statistic']:.3f} | "
            f"{result['degrees_of_freedom']} | {result['p_value']:.4f} |"
        )

    lines += ["", "## Koefisien dan clustered t-stat", ""]
    for name, model in report["models"].items():
        lines += [f"### {labels[name]}", "",
                  "| Fitur | Beta | t cluster | Signifikan 5% |",
                  "|---|---:|---:|---|"]
        for feature, coefficient in model["coefficients"].items():
            lines.append(
                f"| {feature} | {coefficient['beta']:.6g} | "
                f"{coefficient['clustered_t_stat']:.2f} | "
                f"{'Ya' if coefficient['clustered_significant_at_5pct'] else 'Tidak'} |"
            )
        lines.append("")

    lines += ["## Stabilitas tanda", "",
              "| Fitur | Tanda sama di semua model | Rentang beta |",
              "|---|---|---:|"]
    for feature, values in report["coefficient_stability"].items():
        lines.append(
            f"| {feature} | {'Ya' if values['same_sign_across_models'] else 'Tidak'} | "
            f"{values['minimum']:.6g} s.d. {values['maximum']:.6g} |"
        )
    lines += ["", "> Model tanpa ride-hailing adalah uji sensitivitas sampel dan tidak tersarang pada model penuh; karena itu tidak diuji dengan likelihood-ratio test.", ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--json", required=True)
    parser.add_argument("--markdown", required=True)
    args = parser.parse_args()

    rows, _ = read_csv_rows(args.input)
    report = run_sensitivity_analysis(rows)
    json_path = Path(args.json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(args.markdown, report)
    print(f"Laporan: {json_path} dan {args.markdown}")


if __name__ == "__main__":
    main()
