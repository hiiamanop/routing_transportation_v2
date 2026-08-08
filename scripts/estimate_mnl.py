#!/usr/bin/env python3
"""
S-4: estimasi parameter beta model logit multinomial (MNL) dari tabel
long-format hasil export_long_format.py (S-3), pakai maximum likelihood
(Newton-Raphson -- log-likelihood MNL cekung global, jadi metode ini pasti
konvergen tanpa perlu starting value yang bagus).

Koefisien BERSIFAT GENERIC (satu beta per atribut, dipakai sama utk semua
alternatif) -- ini standar utk model pemilihan rute/moda dgn atribut yang
berlaku universal (waktu, biaya, dst tetap berarti sama apapun alternatifnya).

Model dasar (default): U_ij = sum_k beta_k * X_kij, 6 atribut rute.

Model dgn --interactions: tambah 5 kolom X_kij BARU = atribut x rating
preferensi responden (dari /preferensi, skala 1-5). Preferensi TIDAK bisa
masuk sbg efek utama berdiri sendiri -- nilainya sama utk semua alternatif
dlm satu observasi, jadi otomatis coret sendiri di rumus softmax P_ij.
Harus dikalikan dgn atribut yg BEDA-BEDA antar alternatif spy berpengaruh.
Ini masih rumus U_ij yg SAMA PERSIS (jumlah beta*X), cuma X_kij-nya
diperkaya -- bukan model/metode yg berbeda.

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
    python scripts/estimate_mnl.py --input dataset/survey/choices_long.csv --interactions
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from core.survey_export import ATTRIBUTE_KEYS as BASE_ATTRIBUTES  # noqa: E402

EXPECTED_SIGN = {
    "time_minutes": -1, "cost_rupiah": -1, "transfers": -1, "access_km": -1,
    "comfort": 1, "reliability": 1,
}
WIB_TZ = timezone(timedelta(hours=7))

# (kolom atribut, kolom preferensi, nama fitur interaksi). "transfers" tidak
# punya pasangan -- /preferensi tidak punya kriteria "jumlah transfer".
INTERACTION_SPEC = (
    ("time_minutes", "pref_time", "time_minutes_x_pref_time"),
    ("cost_rupiah", "pref_cost", "cost_rupiah_x_pref_cost"),
    ("access_km", "pref_accessibility", "access_km_x_pref_accessibility"),
    ("comfort", "pref_comfort", "comfort_x_pref_comfort"),
    ("reliability", "pref_reliability", "reliability_x_pref_reliability"),
)
# Rating netral (titik tengah skala 1-5) dipakai kalau responden belum
# pernah isi /preferensi -- BUKAN dibuang (data sudah sedikit, S-6 masih
# berjalan), dan netral tidak menarik interaksi ke arah manapun.
NEUTRAL_PREFERENCE = 3.0

INTERACTION_FEATURE_NAMES = tuple(name for _, _, name in INTERACTION_SPEC)


def expected_sign(feature_name: str) -> int:
    """Interaksi diharapkan SEARAH dgn atribut dasarnya -- orang yg mengaku
    lebih peduli suatu atribut (rating tinggi) semestinya efek atributnya
    makin kuat ke arah yg sama, bukan berbalik."""
    if feature_name in EXPECTED_SIGN:
        return EXPECTED_SIGN[feature_name]
    for attr, _, name in INTERACTION_SPEC:
        if name == feature_name:
            return EXPECTED_SIGN[attr]
    raise KeyError(feature_name)


def load_long_format(path: Path, use_interactions: bool = False):
    """
    CSV long-format -> (X_list, chosen_list, feature_names, n_with_preference).

    X_list: list of array (n_alt, n_feature) per observasi.
    chosen_list: posisi alternatif yg dipilih DI DALAM observasi itu.
    n_with_preference: jumlah observasi yg punya preferensi asli (bukan
    hasil imputasi netral) -- dilaporkan sbg indikator kualitas data.
    """
    feature_names = list(BASE_ATTRIBUTES)
    if use_interactions:
        feature_names += list(INTERACTION_FEATURE_NAMES)

    by_obs = {}
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            by_obs.setdefault(row["observation_id"], []).append(row)

    X_list, chosen_list = [], []
    n_with_preference = 0
    for obs_id, rows in by_obs.items():
        rows.sort(key=lambda r: int(r["alternative_index"]))

        has_preference = use_interactions and all(r.get("pref_time", "") != "" for r in rows)
        if has_preference:
            n_with_preference += 1

        feature_rows = []
        for r in rows:
            values = [float(r[a]) for a in BASE_ATTRIBUTES]
            if use_interactions:
                for attr, pref_col, _ in INTERACTION_SPEC:
                    raw_pref = r.get(pref_col, "")
                    pref = float(raw_pref) if raw_pref != "" else NEUTRAL_PREFERENCE
                    values.append(float(r[attr]) * pref)
            feature_rows.append(values)

        X_list.append(np.array(feature_rows))
        chosen_list.append(next(i for i, r in enumerate(rows) if r["chosen"] == "1"))

    return X_list, chosen_list, feature_names, n_with_preference


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
    n_attr = X_list[0].shape[1]
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


def build_report(fit: dict, X_list, feature_names, n_with_preference=None) -> dict:
    beta, se = fit["beta"], fit["se"]
    t_stat = beta / se
    ll_final = fit["log_likelihood"]
    ll_null = null_log_likelihood(X_list)
    rho2 = 1 - ll_final / ll_null

    coefficients = {}
    sign_warnings = []
    for i, name in enumerate(feature_names):
        coefficients[name] = {
            "beta": float(beta[i]), "se": float(se[i]), "t_stat": float(t_stat[i]),
            "significant_at_5pct": bool(abs(t_stat[i]) > 1.96),
        }
        actual_sign = 1 if beta[i] > 0 else -1
        if actual_sign != expected_sign(name):
            sign_warnings.append(
                f"{name}: beta={beta[i]:.5f} (tanda TERBALIK -- harusnya "
                f"{'positif' if expected_sign(name) > 0 else 'negatif'})"
            )

    time_idx, cost_idx = feature_names.index("time_minutes"), feature_names.index("cost_rupiah")
    # VOT cuma bermakna kalau KEDUA koefisien bertanda benar (sama2 negatif) --
    # kalau salah satu terbalik, rasionya bisa jadi angka negatif yg
    # kelihatan seperti angka sungguhan tapi sebenarnya omong kosong
    # (mis. "value of time -Rp4.000/jam"). Lebih baik None drpd melaporkan
    # angka yg menyesatkan.
    value_of_time = None
    if beta[time_idx] < 0 and beta[cost_idx] < 0:
        # Rupiah per menit -> per jam (x60), lazim dilaporkan per jam.
        value_of_time = float(beta[time_idx] / beta[cost_idx] * 60)

    report = {
        "timestamp": datetime.now(WIB_TZ).isoformat(),
        "n_observations": len(X_list),
        "iterations": fit["iterations"],
        "log_likelihood": float(ll_final),
        "log_likelihood_null": float(ll_null),
        "rho_squared_mcfadden": float(rho2),
        "coefficients": coefficients,
        "value_of_time_rupiah_per_hour": value_of_time,
        "sign_warnings": sign_warnings,
        "uses_interactions": bool(any(n in INTERACTION_FEATURE_NAMES for n in feature_names)),
    }
    if n_with_preference is not None:
        report["n_with_preference"] = n_with_preference
    return report


def print_report(report: dict):
    print("=" * 70)
    title = "HASIL ESTIMASI MODEL LOGIT MULTINOMIAL (S-4)"
    if report.get("uses_interactions"):
        title += " + INTERACTION TERM PREFERENSI"
    print(f"  {title}")
    print("=" * 70)
    print(f"Observasi         : {report['n_observations']}")
    if "n_with_preference" in report:
        pct = 100 * report["n_with_preference"] / max(report["n_observations"], 1)
        print(f"   -> punya preferensi asli: {report['n_with_preference']} ({pct:.0f}%), "
              f"sisanya diimputasi netral ({NEUTRAL_PREFERENCE})")
    print(f"Iterasi Newton-Raphson: {report['iterations']}")
    print(f"Log-likelihood    : {report['log_likelihood']:.3f}")
    print(f"Log-likelihood(0) : {report['log_likelihood_null']:.3f}")
    print(f"rho^2 McFadden    : {report['rho_squared_mcfadden']:.4f}")
    print()
    print(f"{'Fitur':<32}{'beta':>12}{'SE':>12}{'t-stat':>10}  signifikan?")
    print("-" * 80)
    for name, c in report["coefficients"].items():
        sig = "ya (5%)" if c["significant_at_5pct"] else "tidak"
        print(f"{name:<32}{c['beta']:>12.5f}{c['se']:>12.5f}{c['t_stat']:>10.2f}  {sig}")
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
        print("\nSemua tanda koefisien masuk akal.")
    print("=" * 70)


def demo():
    """
    Self-check: bangkitkan data dari model MNL dgn beta yang SUDAH DIKETAHUI
    (bukan data survei/dummy yg penuh noise), lalu cek estimator berhasil
    memulihkan tanda & signifikansi yang benar. Ini menguji ESTIMATORNYA
    (matematikanya), terpisah dari pertanyaan "apakah data survei nanti
    cukup kuat sinyalnya" -- dua hal beda yg jangan tercampur.

    Dua bagian: model dasar (6 atribut), lalu model + interaction term
    (termasuk kasus preferensi hilang & diimputasi netral).
    """
    rng = np.random.RandomState(0)

    # --- Bagian 1: model dasar ---
    true_beta = np.array([-0.05, -0.0004, -0.3, -0.5, 0.4, 0.4])  # urutan = BASE_ATTRIBUTES
    scale = np.array([60, 10000, 3, 2, 5, 5])

    X_list, chosen_list = [], []
    for _ in range(3000):
        n_alt = rng.randint(2, 4)
        X = rng.rand(n_alt, len(BASE_ATTRIBUTES)) * scale
        U = X @ true_beta
        P = np.exp(U - U.max())
        P /= P.sum()
        chosen_list.append(rng.choice(n_alt, p=P))
        X_list.append(X)

    fit = fit_mnl(X_list, chosen_list)
    report = build_report(fit, X_list, list(BASE_ATTRIBUTES))

    for i, attr in enumerate(BASE_ATTRIBUTES):
        recovered = report["coefficients"][attr]["beta"]
        assert np.sign(recovered) == np.sign(true_beta[i]), \
            f"{attr}: tanda salah pulih -- recovered={recovered}, true={true_beta[i]}"
        assert report["coefficients"][attr]["significant_at_5pct"], \
            f"{attr}: harusnya signifikan dgn N=3000 & sinyal kuat, tapi tidak"
    assert report["rho_squared_mcfadden"] > 0.05
    assert report["value_of_time_rupiah_per_hour"] is not None
    print(f"OK - model dasar: {len(X_list)} observasi sintetis, semua tanda & "
          f"signifikansi pulih benar, rho^2={report['rho_squared_mcfadden']:.3f}")

    # --- Bagian 2: model + interaction term, termasuk preferensi yg hilang ---
    feature_names = list(BASE_ATTRIBUTES) + list(INTERACTION_FEATURE_NAMES)
    n_feat = len(feature_names)
    true_beta2 = np.zeros(n_feat)
    true_beta2[:6] = true_beta
    # Interaksi waktu & biaya dibuat kuat & searah beta dasarnya, spy mudah
    # dites pulih benar; sisanya nol (tidak ada efek interaksi).
    idx_time_x = feature_names.index("time_minutes_x_pref_time")
    idx_cost_x = feature_names.index("cost_rupiah_x_pref_cost")
    true_beta2[idx_time_x] = -0.01
    true_beta2[idx_cost_x] = -0.00006

    X_list2, chosen_list2 = [], []
    n_missing = 0
    for _ in range(3000):
        n_alt = rng.randint(2, 4)
        base = rng.rand(n_alt, len(BASE_ATTRIBUTES)) * scale
        # ~30% responden belum isi /preferensi -- SEMUA 5 kriteria kosong,
        # load_long_format() akan imputasi netral (3.0) di jalur nyata; di
        # sini disimulasikan langsung dgn NEUTRAL_PREFERENCE spy demo() tidak
        # perlu menulis file CSV cuma utk diuji.
        if rng.rand() < 0.3:
            prefs = {k: NEUTRAL_PREFERENCE for k in ("time", "cost", "access", "comfort", "reliability")}
            n_missing += 1
        else:
            prefs = {k: rng.randint(1, 6) for k in ("time", "cost", "access", "comfort", "reliability")}

        X = np.zeros((n_alt, n_feat))
        X[:, :6] = base
        # SEMUA 5 kolom interaksi harus terisi (bukan cuma yg beta-nya
        # nonzero) -- kolom yg dibiarkan nol terus menerus bikin Hessian
        # singular (kurva log-likelihood terhadap beta itu rata sempurna,
        # tidak ada info sama sekali utk parameter itu).
        X[:, idx_time_x] = base[:, 0] * prefs["time"]
        X[:, idx_cost_x] = base[:, 1] * prefs["cost"]
        X[:, feature_names.index("access_km_x_pref_accessibility")] = base[:, 3] * prefs["access"]
        X[:, feature_names.index("comfort_x_pref_comfort")] = base[:, 4] * prefs["comfort"]
        X[:, feature_names.index("reliability_x_pref_reliability")] = base[:, 5] * prefs["reliability"]

        U = X @ true_beta2
        P = np.exp(U - U.max())
        P /= P.sum()
        chosen_list2.append(rng.choice(n_alt, p=P))
        X_list2.append(X)

    fit2 = fit_mnl(X_list2, chosen_list2)
    report2 = build_report(fit2, X_list2, feature_names, n_with_preference=3000 - n_missing)

    for name, true_val in zip(feature_names, true_beta2):
        recovered = report2["coefficients"][name]["beta"]
        if true_val == 0:
            continue  # efek nol tidak selalu pulih tanda yg "benar" -- cuma cek yg nonzero
        assert np.sign(recovered) == np.sign(true_val), \
            f"{name}: tanda salah pulih -- recovered={recovered}, true={true_val}"
    assert report2["coefficients"]["time_minutes_x_pref_time"]["significant_at_5pct"]
    assert report2["coefficients"]["cost_rupiah_x_pref_cost"]["significant_at_5pct"]
    print(f"OK - model + interaction: {len(X_list2)} observasi sintetis ({n_missing} "
          f"preferensi hilang & diimputasi netral), efek interaksi waktu & biaya "
          f"berhasil pulih benar dan signifikan.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default="dataset/survey/choices_long.csv")
    parser.add_argument("--history", default="dataset/survey/beta_history.jsonl",
                        help="S-8 prep: tiap run ditambahkan sbg baris baru, bukan menimpa -- "
                             "jadi riwayat re-estimasi tersimpan otomatis.")
    parser.add_argument("--interactions", action="store_true",
                        help="Tambah 5 interaction term (atribut x preferensi /preferensi).")
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

    X_list, chosen_list, feature_names, n_with_preference = load_long_format(
        input_path, use_interactions=args.interactions)
    n_params = len(feature_names)
    if len(X_list) < 30 * n_params / 6:  # skala patokan sesuai jumlah parameter
        print(f"PERINGATAN: cuma {len(X_list)} observasi -- di bawah patokan minimal "
              f"30 obs/parameter x {n_params} parameter = {30*n_params} observasi. "
              f"Hasil di bawah ini TIDAK layak dilaporkan sbg temuan final.", file=sys.stderr)

    try:
        fit = fit_mnl(X_list, chosen_list)
    except RuntimeError as e:
        print(f"\nGagal mengestimasi: {e}", file=sys.stderr)
        sys.exit(1)

    report = build_report(fit, X_list, feature_names,
                          n_with_preference if args.interactions else None)
    print_report(report)

    history_path = Path(args.history)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")
    print(f"\nHasil ditambahkan ke riwayat: {history_path}")


if __name__ == "__main__":
    main()
