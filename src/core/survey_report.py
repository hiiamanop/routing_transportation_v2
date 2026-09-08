"""
Logika rekapitulasi dan visualisasi laporan hasil survei pemilihan moda.
Digunakan oleh endpoint GET /api/survey/report.
"""

import html
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from core.survey_export import ATTRIBUTE_KEYS, RESPONDENT_KEYS, load_respondents

TARGET_OBSERVATIONS = 200


def generate_survey_report_data(
    choices_path: Union[str, Path],
    respondents_path: Union[str, Path],
    beta_history_path: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Kompilasi ringkasan statistik dan metrik laporan survei dari
    choices.jsonl dan respondents.jsonl.
    """
    respondents_path = Path(respondents_path)
    choices_path = Path(choices_path)

    # 1. Baca data karakteristik responden
    respondents = load_respondents(respondents_path)
    total_respondents = len(respondents)

    demographics: Dict[str, Dict[str, int]] = {}
    for key in RESPONDENT_KEYS:
        counts = Counter(r.get(key, "").strip() for r in respondents.values() if r.get(key, "").strip())
        demographics[key] = dict(counts.most_common())

    # 2. Baca observasi pilihan
    total_observations = 0
    observations_with_respondent = 0
    observations_with_preference = 0
    unique_choice_respondents = set()

    label_counts: Dict[str, int] = Counter()
    optimized_for_counts: Dict[str, int] = Counter()
    mode_split = {"transit": 0, "private_vehicle": 0}

    attr_sums = {k: 0.0 for k in ATTRIBUTE_KEYS}
    attr_counts = {k: 0 for k in ATTRIBUTE_KEYS}

    first_timestamp = None
    last_timestamp = None

    if choices_path.exists():
        with open(choices_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obs = json.loads(line)
                except json.JSONDecodeError:
                    continue

                total_observations += 1
                ts = obs.get("timestamp")
                if ts:
                    if first_timestamp is None:
                        first_timestamp = ts
                    last_timestamp = ts

                rid = obs.get("respondent_id")
                if rid:
                    unique_choice_respondents.add(rid)
                    if rid in respondents:
                        observations_with_respondent += 1

                if obs.get("preferences") is not None:
                    observations_with_preference += 1

                choice_set = obs.get("choice_set") or []
                chosen_idx = obs.get("chosen_index")
                if isinstance(chosen_idx, int) and 0 <= chosen_idx < len(choice_set):
                    chosen_alt = choice_set[chosen_idx]
                    label = chosen_alt.get("label") or "Tanpa Label"
                    opt_for = chosen_alt.get("optimized_for") or "unknown"

                    label_counts[label] += 1
                    optimized_for_counts[opt_for] += 1

                    if opt_for == "private_vehicle" or "pribadi" in label.lower():
                        mode_split["private_vehicle"] += 1
                    else:
                        mode_split["transit"] += 1

                    attrs = chosen_alt.get("attributes") or {}
                    for k in ATTRIBUTE_KEYS:
                        val = attrs.get(k)
                        if isinstance(val, (int, float)):
                            attr_sums[k] += float(val)
                            attr_counts[k] += 1

    # Hitung rata-rata atribut pilihan
    avg_attributes = {}
    for k in ATTRIBUTE_KEYS:
        if attr_counts[k] > 0:
            avg_attributes[k] = round(attr_sums[k] / attr_counts[k], 2)
        else:
            avg_attributes[k] = None

    # Hitung persentase
    progress_pct = round((total_observations / TARGET_OBSERVATIONS) * 100, 1) if TARGET_OBSERVATIONS else 0.0
    join_pct = round((observations_with_respondent / total_observations) * 100, 1) if total_observations else 0.0
    pref_pct = round((observations_with_preference / total_observations) * 100, 1) if total_observations else 0.0

    transit_pct = round((mode_split["transit"] / total_observations) * 100, 1) if total_observations else 0.0
    private_pct = round((mode_split["private_vehicle"] / total_observations) * 100, 1) if total_observations else 0.0

    # 3. Model MNL estimation status (jika ada riwayat)
    latest_estimation = None
    if beta_history_path:
        hist_path = Path(beta_history_path)
        if hist_path.exists():
            last_entry_line = None
            with open(hist_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last_entry_line = line
            if last_entry_line:
                try:
                    latest_estimation = json.loads(last_entry_line)
                except Exception:
                    latest_estimation = None

    return {
        "success": True,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_observations": total_observations,
            "target_observations": TARGET_OBSERVATIONS,
            "progress_percentage": min(100.0, progress_pct),
            "total_registered_respondents": total_respondents,
            "unique_respondents_in_choices": len(unique_choice_respondents),
            "observations_with_respondent": observations_with_respondent,
            "observations_with_respondent_percentage": join_pct,
            "observations_with_preference": observations_with_preference,
            "observations_with_preference_percentage": pref_pct,
            "is_ready_for_mnl": total_observations >= TARGET_OBSERVATIONS,
            "first_observation_time": first_timestamp,
            "last_observation_time": last_timestamp,
        },
        "choice_distribution": {
            "by_label": dict(label_counts.most_common()),
            "by_optimized_for": dict(optimized_for_counts.most_common()),
            "mode_split": {
                "transit": mode_split["transit"],
                "transit_percentage": transit_pct,
                "private_vehicle": mode_split["private_vehicle"],
                "private_vehicle_percentage": private_pct,
            },
        },
        "average_attributes_chosen": avg_attributes,
        "demographics": demographics,
        "latest_model_estimation": latest_estimation,
    }


def render_survey_report_html(report: dict) -> str:
    """
    Render ringkasan laporan survei menjadi halaman web HTML yang rapi,
    responsif, dan modern tanpa ketergantungan library eksternal.
    """
    summary = report.get("summary", {})
    choice_dist = report.get("choice_distribution", {})
    mode_split = choice_dist.get("mode_split", {})
    by_label = choice_dist.get("by_label", {})
    avg_attrs = report.get("average_attributes_chosen", {})
    demographics = report.get("demographics", {})
    latest_model = report.get("latest_model_estimation")

    total_obs = summary.get("total_observations", 0)
    target_obs = summary.get("target_observations", 200)
    progress_pct = summary.get("progress_percentage", 0.0)
    total_resp = summary.get("total_registered_respondents", 0)
    join_pct = summary.get("observations_with_respondent_percentage", 0.0)
    pref_pct = summary.get("observations_with_preference_percentage", 0.0)

    # Label pemetaan atribut ke nama ramah pengguna
    attr_labels = {
        "time_minutes": "Waktu Tempuh (menit)",
        "cost_rupiah": "Biaya (Rp)",
        "transfers": "Jumlah Transfer",
        "access_km": "Jarak Akses Jalan Kaki (km)",
        "comfort": "Tingkat Kenyamanan (1-5)",
        "reliability": "Tingkat Keandalan (1-5)",
    }

    # Label pemetaan demografi ke judul bahasa Indonesia
    demo_titles = {
        "gender": "Jenis Kelamin",
        "age": "Kelompok Usia",
        "occupation": "Pekerjaan",
        "income": "Pendapatan Per Bulan",
        "vehicle_ownership": "Kepemilikan Kendaraan",
        "trip_purpose": "Tujuan Perjalanan Utama",
        "transit_frequency": "Frekuensi Menggunakan Angkutan Umum",
    }

    # Bar chart distribusi label pilihan
    label_bars_html = ""
    for label, count in by_label.items():
        pct = round((count / total_obs) * 100, 1) if total_obs else 0
        safe_label = html.escape(label)
        label_bars_html += f"""
        <div class="bar-item">
          <div class="bar-header">
            <span class="bar-label">{safe_label}</span>
            <span class="bar-count"><strong>{count}</strong> ({pct}%)</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill" style="width: {pct}%;"></div>
          </div>
        </div>
        """
    if not label_bars_html:
        label_bars_html = "<p class='empty-text'>Belum ada data observasi pilihan.</p>"

    # Tabel atribut rata-rata
    attr_rows_html = ""
    for key, label in attr_labels.items():
        val = avg_attrs.get(key)
        if val is None:
            val_str = "-"
        elif key == "cost_rupiah":
            val_str = f"Rp {val:,.0f}".replace(",", ".")
        elif key in ("time_minutes", "access_km"):
            val_str = f"{val:.2f}"
        else:
            val_str = f"{val:.2f}"

        attr_rows_html += f"""
        <tr>
          <td>{html.escape(label)}</td>
          <td class="text-right font-mono"><strong>{val_str}</strong></td>
        </tr>
        """

    # Demographics sections
    demo_cards_html = ""
    for demo_key, demo_title in demo_titles.items():
        counts_dict = demographics.get(demo_key, {})
        if not counts_dict:
            continue
        sum_counts = sum(counts_dict.values())
        items_html = ""
        for cat, cnt in counts_dict.items():
            pct = round((cnt / sum_counts) * 100, 1) if sum_counts else 0
            items_html += f"""
            <div class="demo-item">
              <span class="demo-cat">{html.escape(cat)}</span>
              <span class="demo-badge">{cnt} ({pct}%)</span>
            </div>
            """
        demo_cards_html += f"""
        <div class="demo-card">
          <h4>{html.escape(demo_title)}</h4>
          <div class="demo-list">
            {items_html}
          </div>
        </div>
        """
    if not demo_cards_html:
        demo_cards_html = "<p class='empty-text'>Belum ada responden yang mengisi formulir karakteristik profil.</p>"

    # Model status badge
    if latest_model:
        rho2 = latest_model.get("rho_squared_mcfadden", "-")
        vot = latest_model.get("value_of_time_rupiah_per_hour")
        vot_str = f"Rp {vot:,.0f} / jam".replace(",", ".") if vot else "-"
        n_obs = latest_model.get("n_observations", "-")
        model_status_html = f"""
        <div class="model-info-grid">
          <div class="mini-stat">
            <span class="label">Observasi Model</span>
            <span class="value">{n_obs}</span>
          </div>
          <div class="mini-stat">
            <span class="label">McFadden Rho²</span>
            <span class="value">{rho2:.4f if isinstance(rho2, (int, float)) else rho2}</span>
          </div>
          <div class="mini-stat">
            <span class="label">Value of Time</span>
            <span class="value">{vot_str}</span>
          </div>
          <div class="mini-stat">
            <span class="label">Status</span>
            <span class="badge badge-success">Terestimasi</span>
          </div>
        </div>
        """
    else:
        status_text = "Siap Diestimasi" if summary.get("is_ready_for_mnl") else f"Menunggu kuota ({total_obs}/{target_obs})"
        badge_cls = "badge-success" if summary.get("is_ready_for_mnl") else "badge-warning"
        model_status_html = f"""
        <div class="model-placeholder">
          <p>Model MNL asli belum diestimasi. Target observasi adalah minimal <strong>{target_obs} data</strong>.</p>
          <p>Status saat ini: <span class="badge {badge_cls}">{status_text}</span></p>
          <p class="model-help">Setelah data cukup, jalankan <code>python scripts/estimate_mnl.py</code> di server.</p>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Laporan Hasil Survei Pemilihan Moda - Kota Palembang</title>
  <style>
    :root {{
      --primary: #2563eb;
      --primary-dark: #1d4ed8;
      --primary-light: #dbeafe;
      --success: #16a34a;
      --warning: #d97706;
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --text-main: #0f172a;
      --text-muted: #64748b;
      --border: #e2e8f0;
      --radius: 12px;
      --shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
      --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text-main);
      line-height: 1.5;
      padding: 24px 16px 48px;
    }}
    .container {{
      max-width: 1040px;
      margin: 0 auto;
    }}
    header {{
      background: var(--card-bg);
      border-radius: var(--radius);
      padding: 24px 28px;
      margin-bottom: 24px;
      box-shadow: var(--shadow);
      border: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    @media (min-width: 768px) {{
      header {{
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
      }}
    }}
    .header-title h1 {{
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .header-title p {{
      color: var(--text-muted);
      font-size: 0.9rem;
      margin-top: 4px;
    }}
    .actions {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 9px 16px;
      font-size: 0.875rem;
      font-weight: 600;
      border-radius: 8px;
      text-decoration: none;
      transition: all 0.2s;
      cursor: pointer;
      border: 1px solid transparent;
    }}
    .btn-primary {{
      background: var(--primary);
      color: #fff;
    }}
    .btn-primary:hover {{
      background: var(--primary-dark);
    }}
    .btn-outline {{
      background: #fff;
      color: var(--text-main);
      border-color: var(--border);
    }}
    .btn-outline:hover {{
      background: #f1f5f9;
    }}

    /* Stat Cards Grid */
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .stat-card {{
      background: var(--card-bg);
      border-radius: var(--radius);
      padding: 20px;
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
    }}
    .stat-card .label {{
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      font-weight: 600;
    }}
    .stat-card .value {{
      font-size: 2rem;
      font-weight: 800;
      color: var(--text-main);
      margin: 4px 0 6px;
    }}
    .stat-card .sub {{
      font-size: 0.825rem;
      color: var(--text-muted);
    }}

    /* Progress section */
    .progress-card {{
      background: var(--card-bg);
      border-radius: var(--radius);
      padding: 20px 24px;
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
      margin-bottom: 24px;
    }}
    .progress-header {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
      font-size: 0.9rem;
      font-weight: 600;
    }}
    .progress-bar-wrap {{
      background: #e2e8f0;
      border-radius: 999px;
      height: 12px;
      overflow: hidden;
    }}
    .progress-bar-inner {{
      background: var(--primary);
      height: 100%;
      border-radius: 999px;
      transition: width 0.3s ease;
    }}

    /* Layout Sections */
    .grid-2 {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 24px;
      margin-bottom: 24px;
    }}
    @media (min-width: 840px) {{
      .grid-2 {{
        grid-template-columns: 1fr 1fr;
      }}
    }}
    .card {{
      background: var(--card-bg);
      border-radius: var(--radius);
      padding: 24px;
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
    }}
    .card h3 {{
      font-size: 1.15rem;
      font-weight: 700;
      margin-bottom: 16px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    /* Mode Split */
    .mode-split-box {{
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
    }}
    .mode-badge {{
      flex: 1;
      padding: 14px;
      border-radius: 10px;
      background: #f8fafc;
      border: 1px solid var(--border);
      text-align: center;
    }}
    .mode-badge .mode-name {{
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
    }}
    .mode-badge .mode-val {{
      font-size: 1.4rem;
      font-weight: 800;
      margin-top: 4px;
    }}
    .mode-badge.transit .mode-val {{ color: var(--primary); }}
    .mode-badge.private .mode-val {{ color: #e11d48; }}

    /* Bar items */
    .bar-item {{
      margin-bottom: 12px;
    }}
    .bar-header {{
      display: flex;
      justify-content: space-between;
      font-size: 0.85rem;
      margin-bottom: 4px;
    }}
    .bar-track {{
      background: #f1f5f9;
      height: 8px;
      border-radius: 4px;
      overflow: hidden;
    }}
    .bar-fill {{
      background: var(--primary);
      height: 100%;
      border-radius: 4px;
    }}

    /* Tables */
    table.data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
    }}
    table.data-table th, table.data-table td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      text-align: left;
    }}
    table.data-table tr:last-child td {{
      border-bottom: none;
    }}
    .text-right {{ text-align: right !important; }}
    .font-mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}

    /* Demographics */
    .demographics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-top: 12px;
    }}
    .demo-card {{
      background: #f8fafc;
      border-radius: 8px;
      border: 1px solid var(--border);
      padding: 14px;
    }}
    .demo-card h4 {{
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--text-muted);
      margin-bottom: 10px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    .demo-list {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .demo-item {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.825rem;
    }}
    .demo-badge {{
      background: #e2e8f0;
      color: var(--text-main);
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: 600;
      font-size: 0.775rem;
    }}

    /* Model Status */
    .model-info-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }}
    .mini-stat {{
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
    }}
    .mini-stat .label {{
      display: block;
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
    }}
    .mini-stat .value {{
      font-size: 1.15rem;
      font-weight: 700;
      margin-top: 4px;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      font-size: 0.75rem;
      font-weight: 700;
      border-radius: 999px;
      text-transform: uppercase;
    }}
    .badge-success {{ background: #dcfce7; color: #15803d; }}
    .badge-warning {{ background: #fef3c7; color: #b45309; }}
    .model-placeholder {{
      font-size: 0.9rem;
      color: var(--text-muted);
    }}
    .model-placeholder p {{
      margin-bottom: 8px;
    }}
    .model-help {{
      font-size: 0.825rem;
      margin-top: 8px;
    }}
    code {{
      background: #f1f5f9;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: monospace;
      color: #0f172a;
    }}
    .empty-text {{
      color: var(--text-muted);
      font-size: 0.875rem;
      font-style: italic;
    }}
    footer {{
      text-align: center;
      margin-top: 32px;
      font-size: 0.8rem;
      color: var(--text-muted);
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="header-title">
        <h1>📊 Laporan Hasil Survei Pemilihan Moda</h1>
        <p>Sistem Informasi Integrasi Antar Moda Transportasi Kota Palembang</p>
      </div>
      <div class="actions">
        <a href="/api/survey/export" class="btn btn-primary" download>
          ⬇️ Unduh CSV
        </a>
        <a href="/api/survey/report?format=json" class="btn btn-outline" target="_blank">
          📄 Lihat JSON
        </a>
        <a href="/api/survey/report" class="btn btn-outline">
          🔄 Segarkan
        </a>
      </div>
    </header>

    <!-- Stat Cards -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="label">Total Observasi</div>
        <div class="value">{total_obs}</div>
        <div class="sub">Pilihan rute tercatat</div>
      </div>
      <div class="stat-card">
        <div class="label">Responden Profil</div>
        <div class="value">{total_resp}</div>
        <div class="sub">Tercatat di form demografi</div>
      </div>
      <div class="stat-card">
        <div class="label">Data Ter-Join</div>
        <div class="value">{join_pct}%</div>
        <div class="sub">Observasi dengan profil responden</div>
      </div>
      <div class="stat-card">
        <div class="label">Data Berpreferensi</div>
        <div class="value">{pref_pct}%</div>
        <div class="sub">Responden dengan bobot nilai</div>
      </div>
    </div>

    <!-- Progress Card -->
    <div class="progress-card">
      <div class="progress-header">
        <span>Progress Menuju Target Estimasi MNL</span>
        <span>{total_obs} / {target_obs} ({progress_pct}%)</span>
      </div>
      <div class="progress-bar-wrap">
        <div class="progress-bar-inner" style="width: {min(100.0, progress_pct)}%;"></div>
      </div>
    </div>

    <!-- Main Grid: Choice Distribution & Average Attributes -->
    <div class="grid-2">
      <div class="card">
        <h3>Pilihan Moda Responden</h3>
        <div class="mode-split-box">
          <div class="mode-badge transit">
            <div class="mode-name">Angkutan Umum</div>
            <div class="mode-val">{mode_split.get("transit", 0)} ({mode_split.get("transit_percentage", 0)}%)</div>
          </div>
          <div class="mode-badge private">
            <div class="mode-name">Kendaraan Pribadi</div>
            <div class="mode-val">{mode_split.get("private_vehicle", 0)} ({mode_split.get("private_vehicle_percentage", 0)}%)</div>
          </div>
        </div>

        <h4 style="font-size: 0.9rem; margin-bottom: 8px; color: var(--text-muted); text-transform: uppercase;">Berdasarkan Alternatif Rute</h4>
        {label_bars_html}
      </div>

      <div class="card">
        <h3>Rata-rata Atribut Rute Terpilih</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>Atribut Perjalanan</th>
              <th class="text-right">Rata-rata Terpilih</th>
            </tr>
          </thead>
          <tbody>
            {attr_rows_html}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Model Status Card -->
    <div class="card" style="margin-bottom: 24px;">
      <h3>Status Model Multinomial Logit (MNL)</h3>
      {model_status_html}
    </div>

    <!-- Demographics Card -->
    <div class="card">
      <h3>Karakteristik & Demografi Responden</h3>
      <div class="demographics-grid">
        {demo_cards_html}
      </div>
    </div>

    <footer>
      <p>Data diperbarui secara otomatis dari penyimpanan survei server.</p>
    </footer>
  </div>
</body>
</html>
"""
