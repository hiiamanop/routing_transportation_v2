#!/usr/bin/env python3
"""Generate six bilingual scientific figures as SVG and 300 dpi PNG."""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

WIDTH_IN = 17 / 2.54
COLORS = ["#1565C0", "#E64A19", "#00897B", "#7B1FA2", "#F9A825", "#3949AB"]
ATTRS = ("time_minutes", "cost_rupiah", "transfers", "access_km", "comfort", "reliability")

LABELS = {
    "id": {
        "public": "Transportasi publik", "private": "Kendaraan pribadi",
        "paid": "Transportasi nonpublik\nberbayar", "count": "Jumlah pilihan responden",
        "percent": "Choice set dengan atribut bervariasi (%)", "correlation": "Koefisien korelasi",
        "time_minutes": "Waktu perjalanan", "cost_rupiah": "Biaya", "transfers": "Transfer",
        "access_km": "Jarak akses", "comfort": "Kenyamanan", "reliability": "Keandalan",
        "asc_private_vehicle": "ASC kendaraan pribadi", "coefficient": "Koefisien terstandar (β × SD)",
        "lower_better": "Nilai kriteria informasi (lebih rendah lebih baik)",
        "od": "Asal–tujuan\nperjalanan rutin", "network": "Jaringan publik\nterintegrasi",
        "alternatives": "Alternatif perjalanan\nuntuk setiap responden",
        "attributes": "Enam atribut\nsetiap alternatif", "choice": "Satu pilihan\nyang diniatkan",
        "audit": "Audit dan\npembersihan data", "mnl": "Estimasi MNL\ndan uji sensitivitas",
        "input": "MASUKAN RESPONDEN", "generation": "PEMBENTUKAN CHOICE SET",
        "analysis": "ANALISIS EMPIRIS", "full_asc": "Penuh + ASC",
        "without_access": "Tanpa akses", "without_transfers": "Tanpa transfer",
        "without_access_transfers": "Tanpa akses\n& transfer",
        "variation_panel": "A. Informasi yang tersedia untuk estimasi",
        "correlation_panel": "B. Hubungan antaratribut",
        "expected": "Arah sesuai teori", "unexpected": "Arah berlawanan teori",
        "fit_note": "Model tanpa transportasi nonpublik berbayar tidak ditampilkan karena menggunakan sampel berbeda.",
        "stability_y": "Estimasi koefisien (β)",
        "m1": "Penuh", "m2": "Tanpa\nakses", "m3": "Tanpa\ntransfer", "m4": "Tanpa\nkeduanya",
    },
    "en": {
        "public": "Public transport", "private": "Private vehicle",
        "paid": "Paid non-public\ntransport", "count": "Number of respondent choices",
        "percent": "Choice sets with attribute variation (%)", "correlation": "Correlation coefficient",
        "time_minutes": "Travel time", "cost_rupiah": "Cost", "transfers": "Transfers",
        "access_km": "Access distance", "comfort": "Comfort", "reliability": "Reliability",
        "asc_private_vehicle": "Private-vehicle ASC", "coefficient": "Standardised coefficient (β × SD)",
        "lower_better": "Information criterion (lower is better)",
        "od": "Routine trip\norigin–destination", "network": "Integrated public\ntransport network",
        "alternatives": "Respondent-specific\ntravel alternatives",
        "attributes": "Six attributes for\neach alternative", "choice": "One intended\nroute choice",
        "audit": "Data audit\nand cleaning", "mnl": "MNL estimation and\nsensitivity analysis",
        "input": "RESPONDENT INPUT", "generation": "CHOICE-SET GENERATION",
        "analysis": "EMPIRICAL ANALYSIS", "full_asc": "Full + ASC",
        "without_access": "Without access", "without_transfers": "Without transfers",
        "without_access_transfers": "Without access\n& transfers",
        "variation_panel": "A. Information available for estimation",
        "correlation_panel": "B. Relationships among attributes",
        "expected": "Theory-consistent sign", "unexpected": "Theory-inconsistent sign",
        "fit_note": "The model excluding paid non-public transport is omitted because it uses a different sample.",
        "stability_y": "Coefficient estimate (β)",
        "m1": "Full", "m2": "Without\naccess", "m3": "Without\ntransfers", "m4": "Without\nboth",
    },
}
NAMES = {
    "id": ["figure_01_alur_penelitian", "figure_02_distribusi_pilihan",
           "figure_03_diagnostik_atribut", "figure_04_koefisien_mnl",
           "figure_05_kecocokan_model", "figure_06_stabilitas_koefisien"],
    "en": ["figure_01_research_flow", "figure_02_choice_distribution",
           "figure_03_attribute_diagnostics", "figure_04_mnl_coefficients",
           "figure_05_model_fit", "figure_06_coefficient_stability"],
}


def _read(processed):
    audit = json.loads((processed / "choices_audit.json").read_text())
    diagnostics = json.loads((processed / "model_diagnostics.json").read_text())
    sensitivity = json.loads((processed / "sensitivity_analysis.json").read_text())
    with (processed / "choices_long_clean.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {"audit": audit, "diagnostics": diagnostics, "sensitivity": sensitivity, "rows": rows}


def save_figure(fig, svg_path, png_path):
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(svg_path, format="svg", bbox_inches="tight")
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text().splitlines()) + "\n",
        encoding="utf-8",
    )
    fig.savefig(png_path, format="png", dpi=300, bbox_inches=None)
    plt.close(fig)


def _fig(height=4.2):
    return plt.subplots(figsize=(WIDTH_IN, height), constrained_layout=True)


def _clean_axes(ax, grid_axis="x"):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis=grid_axis, color="#D7DEE8", linewidth=.7)
    ax.set_axisbelow(True)


def figure_01(language, data):
    """Three clearly separated stages instead of seven cramped boxes in one row."""
    t = LABELS[language]
    fig, ax = _fig(5.2)
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
    stages = [
        (t["input"], 8.8, COLORS[0], [(t["od"], 2.1), (t["network"], 7.9)]),
        (t["generation"], 5.6, COLORS[1], [(t["alternatives"], 2.1), (t["attributes"], 5.0), (t["choice"], 7.9)]),
        (t["analysis"], 2.3, COLORS[2], [(t["audit"], 3.2), (t["mnl"], 6.8)]),
    ]
    previous_centres = []
    for heading, y, color, items in stages:
        ax.text(.45, y + .72, heading, color=color, fontsize=9, fontweight="bold", va="center")
        ax.plot([.45, 9.55], [y + .48, y + .48], color=color, linewidth=2)
        centres = []
        for label, x in items:
            width = 2.35 if len(items) == 3 else 2.7
            box = FancyBboxPatch(
                (x - width/2, y - .62), width, 1.18,
                boxstyle="round,pad=0.08,rounding_size=0.12",
                facecolor=color, edgecolor=color, linewidth=1.3,
            )
            ax.add_patch(box)
            ax.text(x, y - .03, label, ha="center", va="center", color="white",
                    fontsize=9, fontweight="bold", linespacing=1.35)
            centres.append((x, y))
        if previous_centres:
            start = previous_centres[-1]
            end = centres[0]
            ax.annotate("", xy=(end[0], end[1] + .7), xytext=(start[0], start[1] - .72),
                        arrowprops={"arrowstyle": "-|>", "color": "#455A64", "lw": 1.8,
                                    "connectionstyle": "arc3,rad=0.12"})
        for left, right in zip(centres, centres[1:]):
            ax.annotate("", xy=(right[0] - 1.32, right[1]), xytext=(left[0] + 1.32, left[1]),
                        arrowprops={"arrowstyle": "-|>", "color": "#455A64", "lw": 1.5})
        previous_centres = centres
    ax.text(5, .55, f"400 → {data['audit']['valid_observations']}", ha="center",
            color="#37474F", fontsize=9, fontweight="bold")
    return fig


def figure_02(language, data):
    t = LABELS[language]
    counts = data["diagnostics"]["choices"]["by_group"]
    values = [counts.get("transit", 0), counts.get("private_vehicle", 0), counts.get("ride_hailing", 0)]
    labels = [t["public"], t["private"], t["paid"]]
    fig, ax = _fig(3.5); y = np.arange(3)
    bars = ax.barh(y, values, color=COLORS[:3], height=.58)
    ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlabel(t["count"])
    total = sum(values)
    for bar, value in zip(bars, values):
        ax.text(value + max(values)*.025, bar.get_y()+bar.get_height()/2,
                f"{value}  |  {100*value/total:.1f}%", va="center", fontsize=9, fontweight="bold")
    _clean_axes(ax); ax.set_xlim(0, max(values)*1.32)
    return fig


def figure_03(language, data):
    t = LABELS[language]; d = data["diagnostics"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(WIDTH_IN, 4.4), constrained_layout=True,
                                   gridspec_kw={"width_ratios": [1, 1.12]})
    values = [d["within_choice_set_variation"][a]["varying_percentage"] for a in ATTRS]
    labels = [t[a] for a in ATTRS]
    bars = ax1.barh(np.arange(6), values, color=COLORS[0], height=.62)
    ax1.set_yticks(np.arange(6), labels); ax1.invert_yaxis(); ax1.set_xlabel(t["percent"]); ax1.set_xlim(0, 112)
    ax1.set_title(t["variation_panel"], loc="left", fontsize=10, fontweight="bold")
    for bar, value in zip(bars, values):
        ax1.text(value + 1.5, bar.get_y()+bar.get_height()/2, f"{value:.1f}%", va="center", fontsize=8)
    _clean_axes(ax1)

    corr = np.array([[d["correlations"][a][b] if d["correlations"][a][b] is not None else 0
                      for b in ATTRS] for a in ATTRS])
    im = ax2.imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")
    short = [t[a].replace(" perjalanan", "") for a in ATTRS]
    ax2.set_xticks(range(6), short, rotation=42, ha="right"); ax2.set_yticks(range(6), short)
    ax2.set_title(t["correlation_panel"], loc="left", fontsize=10, fontweight="bold")
    for i in range(6):
        for j in range(6):
            ax2.text(j, i, f"{corr[i,j]:.2f}", ha="center", va="center", fontsize=7,
                     color="white" if abs(corr[i,j]) > .52 else "#17202A")
    fig.colorbar(im, ax=ax2, label=t["correlation"], fraction=.046, pad=.04)
    return fig


def _within_choice_sd(rows, feature):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["observation_id"]].append(float(row[feature]))
    differences = [value - np.mean(values) for values in grouped.values() for value in values]
    return float(np.std(differences))


def figure_04(language, data):
    """Standardise continuous coefficients so rupiah-scale cost remains visible."""
    t = LABELS[language]
    coeff = data["diagnostics"]["models"]["private_vehicle_asc"]["coefficients"]
    features = list(coeff)
    scales = {feature: (_within_choice_sd(data["rows"], feature) if feature != "asc_private_vehicle" else 1.0)
              for feature in features}
    beta = np.array([coeff[f]["beta"] * scales[f] for f in features])
    se = np.array([coeff[f]["se"] * scales[f] for f in features])
    labels = [t[f] for f in features]; y = np.arange(len(features))
    theory_consistent = [
        beta[i] <= 0 if feature in ("time_minutes", "cost_rupiah", "transfers", "access_km") else True
        for i, feature in enumerate(features)
    ]
    fig, ax = _fig(4.5); ax.axvline(0, color="#263238", lw=1.1)
    for i, consistent in enumerate(theory_consistent):
        color = COLORS[0] if consistent else COLORS[1]
        ax.errorbar(beta[i], y[i], xerr=1.96*se[i], fmt="o", markersize=6,
                    color=color, ecolor=color, capsize=4, linewidth=1.8)
        ax.text(beta[i], y[i]-.27, f"{beta[i]:+.2f}", ha="center", va="bottom", color=color, fontsize=8)
    ax.scatter([], [], color=COLORS[0], label=t["expected"])
    ax.scatter([], [], color=COLORS[1], label=t["unexpected"])
    ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlabel(t["coefficient"])
    ax.legend(frameon=False, loc="lower right", fontsize=8); _clean_axes(ax)
    return fig


def figure_05(language, data):
    t = LABELS[language]; models = data["sensitivity"]["models"]
    keys = ["full_asc", "without_access", "without_transfers", "without_access_transfers"]
    labels = [t[k] for k in keys]; aic = [models[k]["aic"] for k in keys]; bic = [models[k]["bic"] for k in keys]
    x = np.arange(len(keys)); fig, ax = _fig(4.25); width = .34
    bars_a = ax.bar(x-width/2, aic, width, label="AIC", color=COLORS[0])
    bars_b = ax.bar(x+width/2, bic, width, label="BIC", color=COLORS[3])
    ax.set_ylim(min(aic+bic)-8, max(aic+bic)+7)
    ax.set_xticks(x, labels); ax.set_ylabel(t["lower_better"]); ax.legend(frameon=False, ncol=2, loc="upper left")
    for bars in (bars_a, bars_b):
        for bar in bars:
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+.7, f"{bar.get_height():.2f}",
                    ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.text(.5, -.21, t["fit_note"], transform=ax.transAxes, ha="center", fontsize=7.5, color="#546E7A")
    _clean_axes(ax, "y")
    return fig


def figure_06(language, data):
    """Small multiples retain each coefficient's native unit and sign."""
    t = LABELS[language]; models = data["sensitivity"]["models"]
    model_keys = ["full_asc", "without_access", "without_transfers", "without_access_transfers"]
    model_labels = [t["m1"], t["m2"], t["m3"], t["m4"]]
    features = ["time_minutes", "cost_rupiah", "comfort", "reliability", "asc_private_vehicle"]
    fig, axes = plt.subplots(2, 3, figsize=(WIDTH_IN, 6.0), constrained_layout=True)
    axes = axes.ravel()
    for index, (ax, feature) in enumerate(zip(axes, features)):
        values = np.array([models[key]["coefficients"][feature]["beta"] for key in model_keys])
        ses = np.array([models[key]["coefficients"][feature]["se"] for key in model_keys])
        ax.axhline(0, color="#455A64", linewidth=.9)
        ax.errorbar(range(4), values, yerr=1.96*ses, fmt="o-", color=COLORS[index],
                    ecolor=COLORS[index], linewidth=1.8, capsize=3, markersize=5)
        ax.set_title(t[feature], fontsize=9, fontweight="bold", loc="left")
        ax.set_xticks(range(4), model_labels, fontsize=7)
        ax.tick_params(axis="y", labelsize=7); _clean_axes(ax, "y")
        if index % 3 == 0: ax.set_ylabel(t["stability_y"], fontsize=8)
    axes[-1].axis("off")
    return fig


def generate_all(processed_dir, manuscript_dir):
    processed_dir, manuscript_dir = Path(processed_dir), Path(manuscript_dir)
    data = _read(processed_dir); paths = []
    functions = [figure_01, figure_02, figure_03, figure_04, figure_05, figure_06]
    for language in ("id", "en"):
        output = manuscript_dir / language / "figures"
        for name, function in zip(NAMES[language], functions):
            svg, png = output/f"{name}.svg", output/f"{name}.png"
            save_figure(function(language, data), svg, png); paths.extend([svg, png])
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", required=True, type=Path)
    parser.add_argument("--manuscript-dir", required=True, type=Path)
    args = parser.parse_args()
    for path in generate_all(args.processed_dir, args.manuscript_dir): print(path)


if __name__ == "__main__":
    main()
