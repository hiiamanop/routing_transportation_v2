"""
S-5/S-7: rekomendasi berbasis probabilitas MNL (utilitas -> softmax),
dibangun begitu S-4 punya beta -- TAPI defaultnya OFF di produksi (lihat
ENABLE_MODEL_RECOMMENDATION di api/app.py) sampai beta dari data SURVEI ASLI
(bukan sintetis) tersedia. Menampilkan rekomendasi model ke pengguna
sementara S-6 masih mengumpulkan data berisiko mencemari pilihan mereka
sendiri (bias sirkular) -- lihat docs/RENCANA_SISTEM.md.

Sengaja TIDAK import numpy: API produksi sengaja tidak membawa dependency
itu (lihat scripts/requirements.txt), dan skoring per choice-set kecil
(2-5 alternatif) tidak butuh aljabar matriks, cukup exp/softmax stdlib.
"""
import json
import math
from pathlib import Path
from typing import Dict, List, Optional

from core.gmaps_style_routing import route_attributes

BASE_ATTRIBUTES = ("time_minutes", "cost_rupiah", "transfers", "access_km", "comfort", "reliability")

# atribut -> kriteria preferensi terkait, sama persis dgn INTERACTION_SPEC
# di scripts/estimate_mnl.py (satu sumber makna, dua tempat -- duplikasi
# kecil ini sengaja, drpd API production ikut import skrip riset yg bawa
# numpy). "transfers" sengaja tak ada di sini: tak ada kriteria preferensi
# utk itu di PREFERENCE_CRITERIA.
INTERACTION_ATTR_TO_PREF = {
    "time_minutes": "time",
    "cost_rupiah": "cost",
    "access_km": "accessibility",
    "comfort": "comfort",
    "reliability": "reliability",
}


def load_latest_beta(history_path: str) -> Optional[Dict[str, float]]:
    """Baca entri TERAKHIR di beta_history.jsonl (hasil estimasi paling
    baru, S-8 append-only). None kalau file tak ada/kosong/rusak --
    fail closed, caller lalu tetap pakai heuristik lama."""
    path = Path(history_path)
    if not path.exists():
        return None
    last_line = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last_line = line
    if last_line is None:
        return None
    try:
        entry = json.loads(last_line)
        return {k: v["beta"] for k, v in entry["coefficients"].items()}
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def _utility(attrs: Dict[str, float], beta: Dict[str, float],
             preferences: Optional[Dict[str, float]]) -> float:
    u = sum(beta.get(k, 0.0) * attrs[k] for k in BASE_ATTRIBUTES)
    if preferences:
        for attr, pref_key in INTERACTION_ATTR_TO_PREF.items():
            gamma = beta.get(f"{attr}_x_pref_{pref_key}")
            if gamma is not None:
                u += gamma * attrs[attr] * preferences[pref_key]
    return u


def probabilities_from_attrs(attrs_list: List[Dict[str, float]], beta: Dict[str, float],
                              preferences: Optional[Dict[str, float]] = None) -> List[float]:
    """P_ij softmax atas utilitas semua alternatif dlm SATU choice set.
    Bagian murni (tanpa Route) -- dipisah dari compute_probabilities() spy
    bisa diuji langsung dgn atribut sintetis, tanpa perlu bikin Route palsu."""
    utilities = [_utility(attrs, beta, preferences) for attrs in attrs_list]
    max_u = max(utilities)
    exp_u = [math.exp(u - max_u) for u in utilities]
    total = sum(exp_u)
    return [e / total for e in exp_u]


def compute_probabilities(alternatives: List[Dict], beta: Dict[str, float],
                           preferences: Optional[Dict[str, float]] = None) -> List[float]:
    return probabilities_from_attrs(
        [route_attributes(alt["route"]) for alt in alternatives], beta, preferences)


def select_model_recommendation(alternatives: List[Dict], beta: Dict[str, float],
                                 preferences: Optional[Dict[str, float]] = None) -> Optional[Dict]:
    """Alternatif dgn probabilitas tertinggi. argmax(P) == argmax(U) krn
    softmax monoton -- tak perlu hitung P penuh cuma utk memilih."""
    if not alternatives:
        return None
    best = max(alternatives, key=lambda alt: _utility(route_attributes(alt["route"]), beta, preferences))
    return {"label": "Rekomendasi Model (β)", "optimized_for": "model_recommendation", "route": best["route"]}


def demo():
    """Self-check: RUM sederhana -- alt dgn utilitas lebih tinggi harus dpt
    probabilitas lebih tinggi, dan interaksi preferensi harus mengubah
    urutan begitu preferensi condong ke kriteria yg atributnya beda jauh."""
    beta = {"time_minutes": -0.05, "cost_rupiah": -0.0004, "transfers": -0.3,
            "access_km": -0.5, "comfort": 0.4, "reliability": 0.4,
            "time_minutes_x_pref_time": -0.02}

    cepat_mahal = {"time_minutes": 20, "cost_rupiah": 6000, "transfers": 1,
                   "access_km": 0.5, "comfort": 3, "reliability": 3}
    lambat_murah = {"time_minutes": 60, "cost_rupiah": 5000, "transfers": 1,
                    "access_km": 0.5, "comfort": 3, "reliability": 3}

    probs = probabilities_from_attrs([cepat_mahal, lambat_murah], beta)
    assert abs(sum(probs) - 1.0) < 1e-9, "probabilitas harus jumlah ke 1"
    assert probs[0] > probs[1], (
        "beta['time_minutes'] jauh lebih negatif drpd cost -> yg cepat harusnya menang "
        f"tanpa preferensi, tapi P(cepat)={probs[0]:.3f} <= P(murah)={probs[1]:.3f}"
    )

    # Preferensi waktu sangat tinggi (5) harus memperkuat keunggulan opsi cepat
    probs_pref_time = probabilities_from_attrs(
        [cepat_mahal, lambat_murah], beta, preferences={"time": 5})
    assert probs_pref_time[0] > probs[0], (
        "interaksi time_minutes_x_pref_time negatif + preferensi waktu tinggi "
        "harusnya memperbesar P(opsi cepat), tapi malah tidak"
    )

    print("OK - probabilitas jumlah ke 1, urutan sesuai tanda beta, interaksi preferensi berfungsi")


if __name__ == "__main__":
    demo()
