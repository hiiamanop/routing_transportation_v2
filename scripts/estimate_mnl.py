#!/usr/bin/env python3
"""
S-4: estimasi parameter beta model logit multinomial (MNL) dari tabel
long-format hasil export_long_format.py (S-3), pakai maximum likelihood
(Newton-Raphson -- log-likelihood MNL cekung global, jadi metode ini pasti
konvergen tanpa perlu starting value yang bagus).

Koefisien BERSIFAT GENERIC (satu beta per atribut, dipakai sama utk semua
alternatif) -- ini standar utk model pemilihan rute/moda dgn atribut yang
berlaku universal (waktu, biaya, dst tetap berarti sama apapun alternatifnya).
Karakteristik responden (age/income/dst, hasil join S-3) BELUM dipakai sbg
interaction term di sini -- itu perluasan lanjutan, bukan bagian wajib S-4
(lihat RENCANA_SISTEM.md: yang wajib cuma model dgn 6 atribut rute).

Keluaran yang dilaporkan (wajib menurut RENCANA_SISTEM.md S-4):
- beta + galat baku (standard error) tiap atribut
- statistik-t
- rho^2 McFadden
- flag kalau tanda koefisien tidak masuk akal (waktu/biaya harusnya negatif,
  kenyamanan/keandalan harusnya positif)
- value of time = beta_waktu / beta_biaya

Usage:
    pip install -r scripts/requirements.txt
    python scripts/estimate_mnl.py --input dataset/survey/choices_long.csv
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from core.survey_export import ATTRIBUTE_KEYS as ATTRIBUTES  # noqa: E402

EXPECTED_SIGN = {
    "time_minutes": -1, "cost_rupiah": -1, "transfers": -1, "access_km": -1,
    "comfort": 1, "reliability": 1,
}
WIB_TZ = timezone(timedelta(hours=7))


def load_long_format(path: Path):
    """CSV long-format -> list of (X, chosen_index) per observasi.
    X: array (n_alt, n_attr). chosen_index: posisi alternatif yg dipilih
    DI DALAM observasi itu (bukan alternative_index global)."""
    by_obs = {}
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            obs_id = row["observation_id"]
            by_obs.setdefault(obs_id, []).append(row)

    X_list, chosen_list = [], []
    for obs_id, rows in by_obs.items():
        rows.sort(key=lambda r: int(r["alternative_index"]))
        X = np.array([[float(r[a]) for a in ATTRIBUTES] for r in rows])
        chosen = next(i for i, r in enumerate(rows) if r["chosen"] == "1")
        X_list.append(X)
        chosen_list.append(chosen)
    return X_list, chosen_list


def log_likelihood_grad_hess(beta, X_list, chosen_list):
    """LL, gradien, dan Hessian model MNL pada beta -- rumus baku (lihat
    Train, 'Discrete Choice Methods with Simulation', bab 3)."""
    n_attr = len(beta)
    ll = 0.0
    grad = np.zeros(n_attr)
    hess = np.zeros((n_attr, n_attr))

    for X, c in zip(X_list, chosen_list):
        U = X @ beta
        U = U - U.max()  # stabilitas numerik, tidak mengubah P
        expU = np.exp(U)
        P = expU / expU.sum()

        ll += np.log(P[c])
        grad += X[c] - P @ X
        hess -= X.T @ (np.diag(P) - np.outer(P, P)) @ X

    return ll, grad, hess


def null_log_likelihood(X_list):
    """LL saat beta=0 (semua alternatif berpeluang sama) -- acuan rho^2."""
    return -sum(np.log(len(X)) for X in X_list)


def fit_mnl(X_list, chosen_list, max_iter=100, tol=1e-8):
    n_attr = len(ATTRIBUTES)
    beta = np.zeros(n_attr)

    for iteration in range(1, max_iter + 1):
        ll, grad, hess = log_likelihood_grad_hess(beta, X_list, chosen_list)
        try:
            step = np.linalg.solve(hess, grad)
        except np.linalg.LinAlgError:
            raise RuntimeError(
                "Hessian singular -- kemungkinan atribut kolinear sempurna "
                "(mis. semua observasi punya jumlah alternatif & pola atribut "
                "identik). Butuh data yang lebih bervariasi."
            )
        beta_new = beta - step
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            break
        beta = beta_new
    else:
        print(f"   PERINGATAN: belum konvergen setelah {max_iter} iterasi", file=sys.stderr)

    ll_final, _, hess_final = log_likelihood_grad_hess(beta, X_list, chosen_list)
    cov = np.linalg.inv(-hess_final)
    se = np.sqrt(np.diag(cov))

    return {
        "beta": beta, "se": se, "log_likelihood": ll_final,
        "iterations": iteration, "cov": cov,
    }


def build_report(fit: dict, X_list) -> dict:
    beta, se = fit["beta"], fit["se"]
    t_stat = beta / se
    ll_final = fit["log_likelihood"]
    ll_null = null_log_likelihood(X_list)
    rho2 = 1 - ll_final / ll_null

    coefficients = {}
    sign_warnings = []
    for i, attr in enumerate(ATTRIBUTES):
        coefficients[attr] = {
            "beta": float(beta[i]), "se": float(se[i]), "t_stat": float(t_stat[i]),
            "significant_at_5pct": bool(abs(t_stat[i]) > 1.96),
        }
        actual_sign = 1 if beta[i] > 0 else -1
        if actual_sign != EXPECTED_SIGN[attr]:
            sign_warnings.append(
                f"{attr}: beta={beta[i]:.5f} (tanda TERBALIK -- harusnya "
                f"{'positif' if EXPECTED_SIGN[attr] > 0 else 'negatif'})"
            )

    time_idx, cost_idx = ATTRIBUTES.index("time_minutes"), ATTRIBUTES.index("cost_rupiah")
    # VOT cuma bermakna kalau KEDUA koefisien bertanda benar (sama2 negatif) --
    # kalau salah satu terbalik, rasionya bisa jadi angka negatif yg
    # kelihatan seperti angka sungguhan tapi sebenarnya omong kosong
    # (mis. "value of time -Rp4.000/jam"). Lebih baik None drpd melaporkan
    # angka yg menyesatkan.
    value_of_time = None
    time_ok = beta[time_idx] < 0
    cost_ok = beta[cost_idx] < 0
    if time_ok and cost_ok:
        # Rupiah per menit -> per jam (x60), lazim dilaporkan per jam.
        value_of_time = float(beta[time_idx] / beta[cost_idx] * 60)

    return {
        "timestamp": datetime.now(WIB_TZ).isoformat(),
        "n_observations": len(X_list),
        "iterations": fit["iterations"],
        "log_likelihood": float(ll_final),
        "log_likelihood_null": float(ll_null),
        "rho_squared_mcfadden": float(rho2),
        "coefficients": coefficients,
        "value_of_time_rupiah_per_hour": value_of_time,
        "sign_warnings": sign_warnings,
    }


def print_report(report: dict):
    print("=" * 70)
    print("  HASIL ESTIMASI MODEL LOGIT MULTINOMIAL (S-4)")
    print("=" * 70)
    print(f"Observasi         : {report['n_observations']}")
    print(f"Iterasi Newton-Raphson: {report['iterations']}")
    print(f"Log-likelihood    : {report['log_likelihood']:.3f}")
    print(f"Log-likelihood(0) : {report['log_likelihood_null']:.3f}")
    print(f"rho^2 McFadden    : {report['rho_squared_mcfadden']:.4f}")
    print()
    print(f"{'Atribut':<15}{'beta':>12}{'SE':>12}{'t-stat':>10}  signifikan?")
    print("-" * 70)
    for attr, c in report["coefficients"].items():
        sig = "ya (5%)" if c["significant_at_5pct"] else "tidak"
        print(f"{attr:<15}{c['beta']:>12.5f}{c['se']:>12.5f}{c['t_stat']:>10.2f}  {sig}")
    print()
    if report["value_of_time_rupiah_per_hour"] is not None:
        print(f"Value of time     : Rp {report['value_of_time_rupiah_per_hour']:,.0f} / jam")
    else:
        print("Value of time     : tidak dilaporkan (beta waktu dan/atau biaya "
              "bertanda terbalik, rasionya tidak bermakna)")
    if report["sign_warnings"]:
        print("\nPERINGATAN TANDA KOEFISIEN (kemungkinan ada yg salah pada data, BUKAN temuan):")
        for w in report["sign_warnings"]:
            print(f"   - {w}")
    else:
        print("\nSemua tanda koefisien masuk akal (waktu/biaya negatif, "
              "kenyamanan/keandalan positif).")
    print("=" * 70)


def demo():
    """
    Self-check: bangkitkan data dari model MNL dgn beta yang SUDAH DIKETAHUI
    (bukan data survei/dummy yg penuh noise), lalu cek estimator berhasil
    memulihkan tanda & signifikansi yang benar. Ini menguji ESTIMATORNYA
    (matematikanya), terpisah dari pertanyaan "apakah data survei nanti
    cukup kuat sinyalnya" -- dua hal beda yg jangan tercampur.
    """
    rng = np.random.RandomState(0)
    true_beta = np.array([-0.05, -0.0004, -0.3, -0.5, 0.4, 0.4])  # urutan = ATTRIBUTES
    scale = np.array([60, 10000, 3, 2, 5, 5])  # rentang nilai wajar tiap atribut

    X_list, chosen_list = [], []
    for _ in range(3000):
        n_alt = rng.randint(2, 4)
        X = rng.rand(n_alt, len(ATTRIBUTES)) * scale
        U = X @ true_beta
        P = np.exp(U - U.max())
        P /= P.sum()
        chosen_list.append(rng.choice(n_alt, p=P))
        X_list.append(X)

    fit = fit_mnl(X_list, chosen_list)
    report = build_report(fit, X_list)

    for i, attr in enumerate(ATTRIBUTES):
        recovered = report["coefficients"][attr]["beta"]
        assert np.sign(recovered) == np.sign(true_beta[i]), \
            f"{attr}: tanda salah pulih -- recovered={recovered}, true={true_beta[i]}"
        assert report["coefficients"][attr]["significant_at_5pct"], \
            f"{attr}: harusnya signifikan dgn N=3000 & sinyal kuat, tapi tidak"
    assert report["rho_squared_mcfadden"] > 0.05, "rho^2 terlalu rendah utk data bersinyal kuat"
    assert report["value_of_time_rupiah_per_hour"] is not None

    print(f"OK - self-check lulus: {len(X_list)} observasi sintetis (beta diketahui), "
          f"semua tanda & signifikansi koefisien pulih benar, "
          f"rho^2={report['rho_squared_mcfadden']:.3f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default="dataset/survey/choices_long.csv")
    parser.add_argument("--history", default="dataset/survey/beta_history.jsonl",
                        help="S-8 prep: tiap run ditambahkan sbg baris baru, bukan menimpa -- "
                             "jadi riwayat re-estimasi tersimpan otomatis.")
    parser.add_argument("--demo", action="store_true", help="Jalankan self-check, abaikan --input.")
    args = parser.parse_args()

    if args.demo:
        demo()
        return

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"File tidak ditemukan: {input_path}", file=sys.stderr)
        print("Jalankan scripts/export_long_format.py dulu (S-3).", file=sys.stderr)
        sys.exit(1)

    X_list, chosen_list = load_long_format(input_path)
    if len(X_list) < 30:
        print(f"PERINGATAN: cuma {len(X_list)} observasi -- di bawah patokan minimal "
              f"30 obs/parameter x {len(ATTRIBUTES)} atribut = {30*len(ATTRIBUTES)} observasi. "
              f"Hasil di bawah ini TIDAK layak dilaporkan sbg temuan final.", file=sys.stderr)

    try:
        fit = fit_mnl(X_list, chosen_list)
    except RuntimeError as e:
        print(f"\nGagal mengestimasi: {e}", file=sys.stderr)
        sys.exit(1)

    report = build_report(fit, X_list)
    print_report(report)

    history_path = Path(args.history)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")
    print(f"\nHasil ditambahkan ke riwayat: {history_path}")


if __name__ == "__main__":
    main()
