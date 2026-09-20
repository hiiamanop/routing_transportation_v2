#!/usr/bin/env python3
"""Generate six bilingual scientific figures as SVG and 300 dpi PNG."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

WIDTH_IN = 17 / 2.54
COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"]
ATTRS = ("time_minutes", "cost_rupiah", "transfers", "access_km", "comfort", "reliability")

LABELS = {
    "id": {
        "public": "Transportasi publik", "private": "Kendaraan pribadi",
        "paid": "Transportasi nonpublik berbayar", "count": "Jumlah pilihan",
        "percent": "Persentase choice set bervariasi (%)", "correlation": "Korelasi",
        "time_minutes": "Waktu", "cost_rupiah": "Biaya", "transfers": "Transfer",
        "access_km": "Jarak akses", "comfort": "Kenyamanan", "reliability": "Keandalan",
        "asc_private_vehicle": "ASC kendaraan pribadi", "coefficient": "Koefisien (β)",
        "models": "Spesifikasi model", "lower_better": "Lebih rendah lebih baik",
        "source": "Data survei", "audit": "Audit data", "mnl": "Estimasi MNL",
        "od": "Asal–tujuan rutin", "network": "Jaringan terintegrasi",
        "alternatives": "Alternatif rute", "attributes": "Atribut perjalanan",
        "choice": "Pilihan responden", "full_asc": "Penuh + ASC",
        "without_access": "Tanpa akses", "without_transfers": "Tanpa transfer",
        "without_access_transfers": "Tanpa akses & transfer",
        "model": "Model", "normalized": "Koefisien relatif terhadap model penuh",
    },
    "en": {
        "public": "Public transport", "private": "Private vehicle",
        "paid": "Paid non-public transport", "count": "Number of choices",
        "percent": "Choice sets with attribute variation (%)", "correlation": "Correlation",
        "time_minutes": "Travel time", "cost_rupiah": "Cost", "transfers": "Transfers",
        "access_km": "Access distance", "comfort": "Comfort", "reliability": "Reliability",
        "asc_private_vehicle": "Private-vehicle ASC", "coefficient": "Coefficient (β)",
        "models": "Model specification", "lower_better": "Lower is better",
        "source": "Survey data", "audit": "Data audit", "mnl": "MNL estimation",
        "od": "Routine origin–destination", "network": "Integrated network",
        "alternatives": "Route alternatives", "attributes": "Travel attributes",
        "choice": "Respondent choice", "full_asc": "Full + ASC",
        "without_access": "Without access", "without_transfers": "Without transfers",
        "without_access_transfers": "Without access & transfers",
        "model": "Model", "normalized": "Coefficient relative to full model",
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
    fig.savefig(png_path, format="png", dpi=300, bbox_inches=None)
    plt.close(fig)


def _fig(height=4.2):
    return plt.subplots(figsize=(WIDTH_IN, height), constrained_layout=True)


def figure_01(language, data):
    t = LABELS[language]
    fig, ax = _fig(3.1)
    ax.set_xlim(0, 7); ax.set_ylim(0, 1); ax.axis("off")
    labels = [t["od"], t["network"], t["alternatives"], t["attributes"], t["choice"], t["audit"], t["mnl"]]
    for i, label in enumerate(labels):
        x = i + 0.5
        box = FancyBboxPatch((x - .42, .35), .84, .3, boxstyle="round,pad=0.03",
                             facecolor=COLORS[i % len(COLORS)] + "25", edgecolor="#333333")
        ax.add_patch(box); ax.text(x, .5, label, ha="center", va="center", fontsize=7.5, wrap=True)
        if i < len(labels)-1:
            ax.annotate("", xy=(x+.53,.5), xytext=(x+.43,.5), arrowprops={"arrowstyle":"->","color":"#333333"})
    return fig


def figure_02(language, data):
    t = LABELS[language]; counts = data["diagnostics"]["choices"]["by_group"]
    values = [counts.get("transit",0), counts.get("private_vehicle",0), counts.get("ride_hailing",0)]
    labels = [t["public"], t["private"], t["paid"]]
    fig, ax = _fig(3.3); y = np.arange(3)
    bars=ax.barh(y, values, color=COLORS[:3], edgecolor="#333333", hatch=["","//",".."])
    ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlabel(t["count"])
    total=sum(values)
    for bar,value in zip(bars,values): ax.text(value+max(values)*.02,bar.get_y()+bar.get_height()/2,f"{value} ({100*value/total:.1f}%)",va="center",fontsize=9)
    ax.spines[["top","right"]].set_visible(False); ax.set_xlim(0,max(values)*1.28)
    return fig


def figure_03(language, data):
    t=LABELS[language]; d=data["diagnostics"]
    fig,(ax1,ax2)=plt.subplots(1,2,figsize=(WIDTH_IN,3.8),constrained_layout=True)
    values=[d["within_choice_set_variation"][a]["varying_percentage"] for a in ATTRS]
    labels=[t[a] for a in ATTRS]
    ax1.barh(np.arange(6),values,color=COLORS[0],edgecolor="#333333")
    ax1.set_yticks(np.arange(6),labels); ax1.invert_yaxis(); ax1.set_xlabel(t["percent"]); ax1.set_xlim(0,105)
    corr=np.array([[d["correlations"][a][b] if d["correlations"][a][b] is not None else 0 for b in ATTRS] for a in ATTRS])
    im=ax2.imshow(corr,vmin=-1,vmax=1,cmap="RdBu_r")
    ax2.set_xticks(range(6),labels,rotation=45,ha="right"); ax2.set_yticks(range(6),labels)
    for i in range(6):
        for j in range(6): ax2.text(j,i,f"{corr[i,j]:.2f}",ha="center",va="center",fontsize=6,color="white" if abs(corr[i,j])>.55 else "black")
    fig.colorbar(im,ax=ax2,label=t["correlation"],fraction=.046)
    return fig


def figure_04(language, data):
    t=LABELS[language]; coeff=data["diagnostics"]["models"]["private_vehicle_asc"]["coefficients"]
    features=list(coeff); beta=np.array([coeff[f]["beta"] for f in features]); se=np.array([coeff[f]["se"] for f in features])
    labels=[t[f] for f in features]; y=np.arange(len(features))
    fig,ax=_fig(4.1); ax.axvline(0,color="#333333",lw=1)
    expected=np.array([beta[i] < 0 if f in ("time_minutes","cost_rupiah","transfers","access_km") else True for i,f in enumerate(features)])
    for i in range(len(features)):
        ax.errorbar(beta[i],y[i],xerr=1.96*se[i],fmt="o" if expected[i] else "s",color=COLORS[0] if expected[i] else COLORS[1],capsize=3)
    ax.set_yticks(y,labels); ax.invert_yaxis(); ax.set_xlabel(t["coefficient"]); ax.spines[["top","right"]].set_visible(False)
    return fig


def figure_05(language, data):
    t=LABELS[language]; models=data["sensitivity"]["models"]
    keys=["full_asc","without_access","without_transfers","without_access_transfers"]
    labels=[t[k] for k in keys]; aic=[models[k]["aic"] for k in keys]; bic=[models[k]["bic"] for k in keys]
    x=np.arange(len(keys)); fig,ax=_fig(3.7); width=.35
    ax.bar(x-width/2,aic,width,label="AIC",color=COLORS[0],edgecolor="#333333")
    ax.bar(x+width/2,bic,width,label="BIC",color=COLORS[2],edgecolor="#333333",hatch="//")
    ax.set_xticks(x,labels,rotation=15,ha="right"); ax.set_ylabel(t["lower_better"]); ax.legend(frameon=False); ax.spines[["top","right"]].set_visible(False)
    return fig


def figure_06(language, data):
    t=LABELS[language]; models=data["sensitivity"]["models"]
    model_keys=["full_asc","without_access","without_transfers","without_access_transfers"]
    features=["time_minutes","cost_rupiah","comfort","reliability","asc_private_vehicle"]
    fig,axes=plt.subplots(1,len(features),figsize=(WIDTH_IN,3.7),constrained_layout=True,sharey=True)
    for ax,feature in zip(axes,features):
        base=models["full_asc"]["coefficients"][feature]["beta"]
        vals=[]
        for key in model_keys:
            value=models[key]["coefficients"][feature]["beta"]
            vals.append(value/base if base else np.nan)
        ax.axhline(1,color="#666666",ls="--",lw=.8); ax.plot(range(len(model_keys)),vals,"o-",color=COLORS[0])
        ax.set_title(t[feature],fontsize=8); ax.set_xticks(range(len(model_keys)),["M1","M2","M3","M4"],fontsize=7); ax.spines[["top","right"]].set_visible(False)
    axes[0].set_ylabel(t["normalized"])
    return fig


def generate_all(processed_dir, manuscript_dir):
    processed_dir, manuscript_dir=Path(processed_dir),Path(manuscript_dir); data=_read(processed_dir); paths=[]
    functions=[figure_01,figure_02,figure_03,figure_04,figure_05,figure_06]
    for language in ("id","en"):
        output=manuscript_dir/language/"figures"
        for name,function in zip(NAMES[language],functions):
            svg,png=output/f"{name}.svg",output/f"{name}.png"
            save_figure(function(language,data),svg,png); paths.extend([svg,png])
    return paths


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--processed-dir",required=True,type=Path); parser.add_argument("--manuscript-dir",required=True,type=Path); args=parser.parse_args()
    for path in generate_all(args.processed_dir,args.manuscript_dir): print(path)


if __name__ == "__main__": main()
