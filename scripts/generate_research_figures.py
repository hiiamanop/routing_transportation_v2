#!/usr/bin/env python3
"""Generate six publication-quality bilingual figures as SVG and 300 dpi PNG."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle

WIDTH_IN = 17.0 / 2.54  # 6.69 inches (~17 cm)
DPI = 300

# Professional journal palette
PRIMARY_BLUE = "#1A5276"
SECONDARY_BLUE = "#2E86C1"
ACCENT_ORANGE = "#D35400"
ACCENT_GREEN = "#1E8449"
DARK_GRAY = "#2C3E50"
MID_GRAY = "#7F8C8D"
LIGHT_GRAY = "#EAEDED"
BORDER_GRAY = "#BDC3C7"

ATTRS = ("time_minutes", "cost_rupiah", "transfers", "access_km", "comfort", "reliability")

LABELS = {
    "id": {
        "public": "Transportasi Publik",
        "private": "Kendaraan Pribadi",
        "paid": "Transportasi Nonpublik\nBerbayar",
        "count": "Jumlah Pilihan Responden",
        "percent": "Choice Set dengan Variasi Atribut (%)",
        "correlation": "Koefisien Korelasi",
        "time_minutes": "Waktu Perjalanan",
        "cost_rupiah": "Biaya Perjalanan",
        "transfers": "Jumlah Transfer",
        "access_km": "Jarak Akses",
        "comfort": "Kenyamanan",
        "reliability": "Keandalan",
        "asc_private_vehicle": "ASC Kendaraan Pribadi",
        "std_coef": "Koefisien Terstandar (β × SD)",
        "param_est": "Estimasi (β)",
        "lower_better": "Nilai Kriteria Informasi (Lebih Rendah Lebih Baik)",
        "full_asc": "Penuh + ASC",
        "without_access": "Tanpa Akses",
        "without_transfers": "Tanpa Transfer",
        "without_access_transfers": "Tanpa Akses\n& Transfer",
        "variation_title": "A. Variasi Atribut dalam Choice Set",
        "correlation_title": "B. Matriks Korelasi Antaratribut",
        "expected_legend": "Arah Sesuai Teori",
        "unexpected_legend": "Arah Berlawanan Teori",
        "fit_footnote": "Catatan: Model tanpa transportasi nonpublik berbayar tidak ditampilkan karena menggunakan ukuran sampel berbeda.",
        "m1": "M1 (Penuh)",
        "m2": "M2 (-Akses)",
        "m3": "M3 (-Transfer)",
        "m4": "M4 (-Keduanya)",
        # Flow diagram texts
        "stage1_title": "TAHAP 1: MASUKAN DARI RESPONDEN",
        "stage1_box1": "Asal & Tujuan\nPerjalanan Rutin",
        "stage1_desc1": "Ditentukan sendiri oleh\nmasing-masing responden",
        "stage1_box2": "Jaringan Publik\nTerintegrasi",
        "stage1_desc2": "11 Koridor (LRT, Teman Bus,\ndan Angkot Feeder Palembang)",
        "stage2_title": "TAHAP 2: PEMBENTUKAN ALTERNATIF (CHOICE SET)",
        "stage2_box1": "Pembangkitan Rute\n(Algoritma Dijkstra)",
        "stage2_desc1": "Rute tercepat, termurah,\ndan transfer minimal",
        "stage2_box2": "Perhitungan 6 Atribut\nPerjalanan",
        "stage2_desc2": "Waktu, biaya, transfer,\nakses, kenyamanan, keandalan",
        "stage2_box3": "Pilihan Rute yang\nDiniatkan",
        "stage2_desc3": "Responden memilih 1 rute\nsebelum keberangkatan",
        "stage3_title": "TAHAP 3: AUDIT DATA & ESTIMASI MODEL",
        "stage3_box1": "Audit & Pembersihan Data",
        "stage3_desc1": "400 respons disaring: buang ekstrem\ndan gabung duplikat → 318 valid",
        "stage3_box2": "Pemodelan Logit Multinomial",
        "stage3_desc2": "Estimasi MNL dasar, MNL + ASC,\ndan 4 uji sensitivitas spesifikasi",
    },
    "en": {
        "public": "Public Transport",
        "private": "Private Vehicle",
        "paid": "Paid Non-Public\nTransport",
        "count": "Number of Respondent Choices",
        "percent": "Choice Sets with Attribute Variation (%)",
        "correlation": "Correlation Coefficient",
        "time_minutes": "Travel Time",
        "cost_rupiah": "Travel Cost",
        "transfers": "Number of Transfers",
        "access_km": "Access Distance",
        "comfort": "Comfort",
        "reliability": "Reliability",
        "asc_private_vehicle": "Private-Vehicle ASC",
        "std_coef": "Standardised Coefficient (β × SD)",
        "param_est": "Estimate (β)",
        "lower_better": "Information Criterion (Lower is Better)",
        "full_asc": "Full + ASC",
        "without_access": "Without Access",
        "without_transfers": "Without Transfers",
        "without_access_transfers": "Without Access\n& Transfers",
        "variation_title": "A. Attribute Variation in Choice Sets",
        "correlation_title": "B. Attribute Correlation Matrix",
        "expected_legend": "Theory-Consistent Sign",
        "unexpected_legend": "Theory-Inconsistent Sign",
        "fit_footnote": "Note: Model excluding paid non-public transport is omitted because it uses a different sample size.",
        "m1": "M1 (Full)",
        "m2": "M2 (-Access)",
        "m3": "M3 (-Transfers)",
        "m4": "M4 (-Both)",
        # Flow diagram texts
        "stage1_title": "STAGE 1: RESPONDENT INPUTS",
        "stage1_box1": "Routine Origin\n& Destination",
        "stage1_desc1": "Self-specified by each\nsurvey respondent",
        "stage1_box2": "Integrated Public\nTransport Network",
        "stage1_desc2": "11 Corridors (LRT, Teman Bus,\nand Feeder Angkot in Palembang)",
        "stage2_title": "STAGE 2: CHOICE-SET GENERATION",
        "stage2_box1": "Route Generation\n(Dijkstra Algorithm)",
        "stage2_desc1": "Fastest, cheapest, and\nleast-transfer alternatives",
        "stage2_box2": "Calculation of Six\nTravel Attributes",
        "stage2_desc2": "Time, cost, transfers,\naccess, comfort, reliability",
        "stage2_box3": "Intended Route\nChoice",
        "stage2_desc3": "Respondent selects one\noption before travelling",
        "stage3_title": "STAGE 3: DATA AUDIT & MODEL ESTIMATION",
        "stage3_box1": "Data Audit & Cleaning",
        "stage3_desc1": "400 responses screened: drop extremes\n& merge duplicates → 318 valid",
        "stage3_box2": "Multinomial Logit Modelling",
        "stage3_desc2": "Basic MNL, MNL + ASC,\nand 4 sensitivity specifications",
    },
}

NAMES = {
    "id": [
        "figure_01_alur_penelitian",
        "figure_02_distribusi_pilihan",
        "figure_03_diagnostik_atribut",
        "figure_04_koefisien_mnl",
        "figure_05_kecocokan_model",
        "figure_06_stabilitas_koefisien",
    ],
    "en": [
        "figure_01_research_flow",
        "figure_02_choice_distribution",
        "figure_03_attribute_diagnostics",
        "figure_04_mnl_coefficients",
        "figure_05_model_fit",
        "figure_06_coefficient_stability",
    ],
}


def _read_data(processed_dir: Path):
    audit = json.loads((processed_dir / "choices_audit.json").read_text(encoding="utf-8"))
    diagnostics = json.loads((processed_dir / "model_diagnostics.json").read_text(encoding="utf-8"))
    sensitivity = json.loads((processed_dir / "sensitivity_analysis.json").read_text(encoding="utf-8"))
    with (processed_dir / "choices_long_clean.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {"audit": audit, "diagnostics": diagnostics, "sensitivity": sensitivity, "rows": rows}


def save_figure(fig, svg_path: Path, png_path: Path):
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(svg_path, format="svg")
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    fig.savefig(png_path, format="png", dpi=DPI)
    plt.close(fig)


# ==============================================================================
# FIGURE 1: RESEARCH FLOW DIAGRAM (SPACIOUS 3-TIER CARD PIPELINE)
# ==============================================================================
def figure_01(language: str, data: dict):
    t = LABELS[language]
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 6.2), constrained_layout=True)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    stages = [
        {
            "title": t["stage1_title"],
            "y_top": 98,
            "card_color": "#EBF5FB",
            "accent": PRIMARY_BLUE,
            "boxes": [
                {"title": t["stage1_box1"], "desc": t["stage1_desc1"], "x": 26, "w": 40},
                {"title": t["stage1_box2"], "desc": t["stage1_desc2"], "x": 74, "w": 40},
            ],
            "h": 22,
        },
        {
            "title": t["stage2_title"],
            "y_top": 66,
            "card_color": "#FEF9E7",
            "accent": ACCENT_ORANGE,
            "boxes": [
                {"title": t["stage2_box1"], "desc": t["stage2_desc1"], "x": 18, "w": 28},
                {"title": t["stage2_box2"], "desc": t["stage2_desc2"], "x": 50, "w": 28},
                {"title": t["stage2_box3"], "desc": t["stage2_desc3"], "x": 82, "w": 28},
            ],
            "h": 22,
        },
        {
            "title": t["stage3_title"],
            "y_top": 34,
            "card_color": "#E8F8F5",
            "accent": ACCENT_GREEN,
            "boxes": [
                {"title": t["stage3_box1"], "desc": t["stage3_desc1"], "x": 26, "w": 40},
                {"title": t["stage3_box2"], "desc": t["stage3_desc2"], "x": 74, "w": 40},
            ],
            "h": 22,
        },
    ]

    for stage in stages:
        y_top = stage["y_top"]
        h = stage["h"]
        accent = stage["accent"]

        # Stage background container
        container = FancyBboxPatch(
            (2, y_top - h), 96, h,
            boxstyle="round,pad=0.5,rounding_size=1.5",
            facecolor=stage["card_color"],
            edgecolor=accent,
            linewidth=1.2,
        )
        ax.add_patch(container)

        # Stage header title
        ax.text(
            5, y_top - 3.5, stage["title"],
            fontsize=8.5, fontweight="bold", color=accent, va="center",
        )
        ax.plot([4.8, 95.2], [y_top - 6.2, y_top - 6.2], color=accent, linewidth=0.8, alpha=0.5)

        # Draw internal boxes
        for box_info in stage["boxes"]:
            cx = box_info["x"]
            bw = box_info["w"]
            bx = cx - bw / 2.0
            by = y_top - h + 2.0
            bh = h - 10.0

            inner_box = FancyBboxPatch(
                (bx, by), bw, bh,
                boxstyle="round,pad=0.3,rounding_size=1.0",
                facecolor="#FFFFFF",
                edgecolor=BORDER_GRAY,
                linewidth=0.8,
            )
            ax.add_patch(inner_box)

            # Box Title
            ax.text(
                cx, by + bh * 0.62, box_info["title"],
                ha="center", va="center", fontsize=8.2, fontweight="bold",
                color=DARK_GRAY, linespacing=1.25,
            )
            # Box Description
            ax.text(
                cx, by + bh * 0.24, box_info["desc"],
                ha="center", va="center", fontsize=7.2,
                color=MID_GRAY, linespacing=1.15,
            )

    # Connecting vertical flow arrows between stages
    arrow_props = dict(arrowstyle="-|>", color=DARK_GRAY, lw=1.8, mutation_scale=14)
    # Stage 1 -> Stage 2
    ax.annotate("", xy=(50, 66.5), xytext=(50, 75.5), arrowprops=arrow_props)
    # Stage 2 -> Stage 3
    ax.annotate("", xy=(50, 34.5), xytext=(50, 43.5), arrowprops=arrow_props)

    # Horizontal step connectors within Stage 2
    step_arrow = dict(arrowstyle="-|>", color=ACCENT_ORANGE, lw=1.4, mutation_scale=10)
    ax.annotate("", xy=(35.5, 53), xytext=(32.5, 53), arrowprops=step_arrow)
    ax.annotate("", xy=(67.5, 53), xytext=(64.5, 53), arrowprops=step_arrow)

    # Horizontal step connector within Stage 3
    stage3_arrow = dict(arrowstyle="-|>", color=ACCENT_GREEN, lw=1.4, mutation_scale=10)
    ax.annotate("", xy=(53.5, 21), xytext=(46.5, 21), arrowprops=stage3_arrow)

    # Footnote summary tag
    ax.text(
        50, 4.0,
        f"400 Respons Sumber  →  82 Dieksklusi (Nilai Ekstrem / Opsi Tunggal)  →  {data['audit']['valid_observations']} Observasi Analisis Final",
        ha="center", va="center", fontsize=7.6, fontweight="bold", color=DARK_GRAY,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFFFFF", edgecolor=BORDER_GRAY, lw=0.8),
    )

    return fig


# ==============================================================================
# FIGURE 2: CHOICE DISTRIBUTION (CLEAN HORIZONTAL BARS)
# ==============================================================================
def figure_02(language: str, data: dict):
    t = LABELS[language]
    counts = data["diagnostics"]["choices"]["by_group"]
    values = [counts.get("transit", 0), counts.get("private_vehicle", 0), counts.get("ride_hailing", 0)]
    labels = [t["public"], t["private"], t["paid"]]
    total = sum(values)

    fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.8), constrained_layout=True)
    y_pos = np.arange(len(labels))
    bar_colors = [PRIMARY_BLUE, ACCENT_ORANGE, MID_GRAY]

    bars = ax.barh(y_pos, values, color=bar_colors, height=0.52, edgecolor=DARK_GRAY, linewidth=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9.2, fontweight="bold", color=DARK_GRAY)
    ax.invert_yaxis()
    ax.set_xlabel(t["count"], fontsize=9.2, fontweight="bold", color=DARK_GRAY)

    # Clean axes
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BORDER_GRAY)
    ax.spines["bottom"].set_color(BORDER_GRAY)
    ax.grid(axis="x", color="#EAECEE", linestyle="--", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.set_xlim(0, max(values) * 1.30)

    # Direct labels on / beside bars
    for bar, val in zip(bars, values):
        pct = (val / total) * 100.0
        label_text = f"{val}  ({pct:.1f}%)"
        ax.text(
            val + (max(values) * 0.025),
            bar.get_y() + bar.get_height() / 2.0,
            label_text,
            va="center", ha="left",
            fontsize=9.0, fontweight="bold", color=DARK_GRAY,
        )

    return fig


# ==============================================================================
# FIGURE 3: ATTRIBUTE VARIATION & CORRELATION HEATMAP (SIDE BY SIDE)
# ==============================================================================
def figure_03(language: str, data: dict):
    t = LABELS[language]
    d = data["diagnostics"]
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(WIDTH_IN, 4.8), constrained_layout=True,
        gridspec_kw={"width_ratios": [1.0, 1.18]},
    )

    # Panel A: Variation
    var_values = [d["within_choice_set_variation"][a]["varying_percentage"] for a in ATTRS]
    attr_labels = [t[a] for a in ATTRS]
    y_pos = np.arange(len(ATTRS))

    bars = ax1.barh(y_pos, var_values, color=SECONDARY_BLUE, height=0.58, edgecolor=DARK_GRAY, linewidth=0.7)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(attr_labels, fontsize=8.5, color=DARK_GRAY)
    ax1.invert_yaxis()
    ax1.set_xlabel(t["percent"], fontsize=8.5, fontweight="bold", color=DARK_GRAY)
    ax1.set_title(t["variation_title"], loc="left", fontsize=9.2, fontweight="bold", color=DARK_GRAY, pad=10)
    ax1.set_xlim(0, 115)

    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.spines["left"].set_color(BORDER_GRAY)
    ax1.spines["bottom"].set_color(BORDER_GRAY)
    ax1.grid(axis="x", color="#EAECEE", linestyle="--", linewidth=0.7)
    ax1.set_axisbelow(True)

    for bar, val in zip(bars, var_values):
        ax1.text(
            val + 2.0, bar.get_y() + bar.get_height() / 2.0,
            f"{val:.1f}%", va="center", ha="left", fontsize=8.0, fontweight="bold", color=DARK_GRAY,
        )

    # Panel B: Correlation Heatmap
    corr_matrix = np.array([
        [d["correlations"][a][b] if d["correlations"][a][b] is not None else 0.0 for b in ATTRS]
        for a in ATTRS
    ])
    short_labels = [
        "Waktu" if language == "id" else "Time",
        "Biaya" if language == "id" else "Cost",
        "Transfer" if language == "id" else "Transfers",
        "Akses" if language == "id" else "Access",
        "Nyaman" if language == "id" else "Comfort",
        "Andal" if language == "id" else "Reliability",
    ]

    im = ax2.imshow(corr_matrix, vmin=-1.0, vmax=1.0, cmap="coolwarm")
    ax2.set_xticks(range(6))
    ax2.set_xticklabels(short_labels, rotation=35, ha="right", fontsize=8.0, color=DARK_GRAY)
    ax2.set_yticks(range(6))
    ax2.set_yticklabels(short_labels, fontsize=8.0, color=DARK_GRAY)
    ax2.set_title(t["correlation_title"], loc="left", fontsize=9.2, fontweight="bold", color=DARK_GRAY, pad=10)

    for i in range(6):
        for j in range(6):
            val = corr_matrix[i, j]
            text_color = "#FFFFFF" if abs(val) > 0.50 else DARK_GRAY
            ax2.text(
                j, i, f"{val:.2f}",
                ha="center", va="center", fontsize=7.2, fontweight="bold", color=text_color,
            )

    cb = fig.colorbar(im, ax=ax2, fraction=0.046, pad=0.04)
    cb.set_label(t["correlation"], fontsize=8.0, color=DARK_GRAY)
    cb.ax.tick_params(labelsize=7.5)

    return fig


# ==============================================================================
# FIGURE 4: MNL COEFFICIENTS (FOREST PLOT + SIDE METRIC TABLE)
# ==============================================================================
def _within_choice_sd(rows, feature):
    from collections import defaultdict
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["observation_id"]].append(float(row[feature]))
    diffs = [v - np.mean(vals) for vals in grouped.values() for v in vals]
    return float(np.std(diffs)) if diffs else 1.0


def figure_04(language: str, data: dict):
    t = LABELS[language]
    coeff_dict = data["diagnostics"]["models"]["private_vehicle_asc"]["coefficients"]
    features = list(coeff_dict.keys())

    # Calculate standardized effect sizes (beta * SD)
    scales = {
        f: (_within_choice_sd(data["rows"], f) if f != "asc_private_vehicle" else 1.0)
        for f in features
    }
    betas_raw = [coeff_dict[f]["beta"] for f in features]
    ses_raw = [coeff_dict[f]["se"] for f in features]
    betas_std = [b * scales[f] for b, f in zip(betas_raw, features)]
    ses_std = [s * scales[f] for s, f in zip(ses_raw, features)]
    attr_labels = [t[f] for f in features]

    fig, ax = plt.subplots(figsize=(WIDTH_IN, 4.4), constrained_layout=True)
    y_pos = np.arange(len(features))

    # Reference zero line
    ax.axvline(0, color=DARK_GRAY, linestyle="-", linewidth=1.0, alpha=0.8)

    # Plot confidence intervals
    for i, f in enumerate(features):
        b_std = betas_std[i]
        ci_std = 1.96 * ses_std[i]
        b_raw = betas_raw[i]
        p_sig = abs(coeff_dict[f]["t_stat"]) > 1.96

        is_theory_consistent = (b_raw < 0) if f in ("time_minutes", "cost_rupiah", "transfers", "access_km") else True
        point_color = PRIMARY_BLUE if is_theory_consistent else ACCENT_ORANGE

        # Error bar
        ax.errorbar(
            b_std, y_pos[i], xerr=ci_std,
            fmt="o", markersize=6.5,
            color=point_color, ecolor=point_color,
            elinewidth=1.8, capsize=4.0, capthick=1.4,
        )

        # Side text showing actual raw parameter estimate & significance
        sig_star = " *" if p_sig else ""
        if abs(b_raw) < 0.001:
            raw_text = f"β = {b_raw:.2e}{sig_star}"
        else:
            raw_text = f"β = {b_raw:+.3f}{sig_star}"

        # Place text safely to the right
        ax.text(
            0.88, y_pos[i], raw_text,
            va="center", ha="left", fontsize=8.0, fontweight="bold",
            color=point_color,
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(attr_labels, fontsize=9.0, fontweight="bold", color=DARK_GRAY)
    ax.invert_yaxis()
    ax.set_xlabel(t["std_coef"], fontsize=9.0, fontweight="bold", color=DARK_GRAY)
    ax.set_xlim(-0.35, 1.45)

    # Spines and grid
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BORDER_GRAY)
    ax.spines["bottom"].set_color(BORDER_GRAY)
    ax.grid(axis="x", color="#EAECEE", linestyle="--", linewidth=0.7)
    ax.set_axisbelow(True)

    # Clean legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=PRIMARY_BLUE, markersize=7, label=t["expected_legend"]),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=ACCENT_ORANGE, markersize=7, label=t["unexpected_legend"]),
    ]
    ax.legend(handles=legend_elements, loc="lower right", frameon=True, facecolor="#FAFAFA", edgecolor=BORDER_GRAY, fontsize=8.0)

    return fig


# ==============================================================================
# FIGURE 5: MODEL FIT COMPARISON (AIC & BIC WITHOUT PATTERNS)
# ==============================================================================
def figure_05(language: str, data: dict):
    t = LABELS[language]
    models = data["sensitivity"]["models"]
    keys = ["full_asc", "without_access", "without_transfers", "without_access_transfers"]
    model_labels = [t[k] for k in keys]
    aic_vals = [models[k]["aic"] for k in keys]
    bic_vals = [models[k]["bic"] for k in keys]

    fig, ax = plt.subplots(figsize=(WIDTH_IN, 4.4), constrained_layout=True)
    x = np.arange(len(keys))
    bar_width = 0.35

    # Solid colors, no patterns/hatches
    bars_aic = ax.bar(x - bar_width / 2.0, aic_vals, bar_width, label="AIC", color=PRIMARY_BLUE, edgecolor=DARK_GRAY, linewidth=0.8)
    bars_bic = ax.bar(x + bar_width / 2.0, bic_vals, bar_width, label="BIC", color=ACCENT_ORANGE, edgecolor=DARK_GRAY, linewidth=0.8)

    # Focus axis on relevant differences (baseline around 480)
    min_val = min(aic_vals + bic_vals)
    max_val = max(aic_vals + bic_vals)
    ax.set_ylim(490, max_val + 14)

    ax.set_xticks(x)
    ax.set_xticklabels(model_labels, fontsize=8.8, fontweight="bold", color=DARK_GRAY)
    ax.set_ylabel(t["lower_better"], fontsize=8.8, fontweight="bold", color=DARK_GRAY)

    # Spines and grid
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BORDER_GRAY)
    ax.spines["bottom"].set_color(BORDER_GRAY)
    ax.grid(axis="y", color="#EAECEE", linestyle="--", linewidth=0.7)
    ax.set_axisbelow(True)

    # Value tags with safe vertical offset
    for bar in bars_aic:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0, h + 1.2,
            f"{h:.2f}",
            ha="center", va="bottom", fontsize=8.0, fontweight="bold", color=PRIMARY_BLUE,
        )
    for bar in bars_bic:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0, h + 1.2,
            f"{h:.2f}",
            ha="center", va="bottom", fontsize=8.0, fontweight="bold", color=ACCENT_ORANGE,
        )

    ax.legend(loc="upper left", frameon=True, facecolor="#FAFAFA", edgecolor=BORDER_GRAY, fontsize=8.5)

    # Footnote note placed at bottom
    ax.text(0.5, -0.15, t["fit_footnote"], transform=ax.transAxes, ha="center", fontsize=7.2, color=MID_GRAY, style="italic")

    return fig


# ==============================================================================
# FIGURE 6: COEFFICIENT STABILITY ACROSS SPECIFICATIONS (CLEAN FACET PLOT)
# ==============================================================================
def figure_06(language: str, data: dict):
    t = LABELS[language]
    models = data["sensitivity"]["models"]
    model_keys = ["full_asc", "without_access", "without_transfers", "without_access_transfers"]
    model_labels = [t["m1"], t["m2"], t["m3"], t["m4"]]
    features = ["time_minutes", "cost_rupiah", "comfort", "reliability", "asc_private_vehicle"]

    fig, axes = plt.subplots(2, 3, figsize=(WIDTH_IN, 5.6), constrained_layout=True)
    axes = axes.ravel()

    facet_colors = [PRIMARY_BLUE, SECONDARY_BLUE, ACCENT_GREEN, ACCENT_ORANGE, DARK_GRAY]

    for idx, (ax, feat) in enumerate(zip(axes, features)):
        vals = [models[k]["coefficients"][feat]["beta"] for k in model_keys]
        ses = [models[k]["coefficients"][feat]["se"] for k in model_keys]
        x_coords = np.arange(len(model_keys))
        c = facet_colors[idx]

        # Zero reference line
        ax.axhline(0, color=BORDER_GRAY, linestyle="-", linewidth=0.9)

        # Plot line + points with confidence interval
        ax.errorbar(
            x_coords, vals, yerr=[1.96 * s for s in ses],
            fmt="o-", color=c, ecolor=c,
            linewidth=1.8, markersize=5.5, capsize=3.5, capthick=1.2,
        )

        ax.set_title(t[feat], fontsize=8.8, fontweight="bold", color=DARK_GRAY, loc="left", pad=8)
        ax.set_xticks(x_coords)
        ax.set_xticklabels(model_labels, fontsize=7.2, color=DARK_GRAY)
        ax.tick_params(axis="y", labelsize=7.5)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(BORDER_GRAY)
        ax.spines["bottom"].set_color(BORDER_GRAY)
        ax.grid(axis="y", color="#EAECEE", linestyle="--", linewidth=0.7)
        ax.set_axisbelow(True)

        # Value annotations on first and last point
        ax.text(0, vals[0], f" {vals[0]:.2e}" if abs(vals[0]) < 0.001 else f" {vals[0]:+.2f}",
                va="bottom", ha="left", fontsize=6.8, color=c, fontweight="bold")
        ax.text(3, vals[3], f" {vals[3]:.2e}" if abs(vals[3]) < 0.001 else f" {vals[3]:+.2f}",
                va="bottom", ha="left", fontsize=6.8, color=c, fontweight="bold")

    # Hide 6th empty subplot
    axes[5].axis("off")

    return fig


# ==============================================================================
# MAIN GENERATOR FUNCTION
# ==============================================================================
def generate_all(processed_dir: Path, manuscript_dir: Path):
    processed_dir = Path(processed_dir)
    manuscript_dir = Path(manuscript_dir)
    data = _read_data(processed_dir)
    paths = []
    functions = [figure_01, figure_02, figure_03, figure_04, figure_05, figure_06]

    for language in ("id", "en"):
        out_dir = manuscript_dir / language / "figures"
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, fn in zip(NAMES[language], functions):
            svg_path = out_dir / f"{name}.svg"
            png_path = out_dir / f"{name}.png"
            fig = fn(language, data)
            save_figure(fig, svg_path, png_path)
            paths.extend([svg_path, png_path])

    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", required=True, type=Path)
    parser.add_argument("--manuscript-dir", required=True, type=Path)
    args = parser.parse_args()
    for path in generate_all(args.processed_dir, args.manuscript_dir):
        print(path)


if __name__ == "__main__":
    main()
