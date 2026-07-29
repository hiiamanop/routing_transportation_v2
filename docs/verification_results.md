# Hasil Verifikasi Ulang (2026-07-19)

Semua angka di bawah dihasilkan dari kode dan dataset asli di repo ini (bukan
diasumsikan/dihaluskan dari naskah). Script sumber ada di `backend/experiments/`
dan bisa dijalankan ulang kapan saja untuk reproduksi:
- `ground_truth.py` — cakupan ground truth (Task 1 & 3.1)
- `run_case_study.py` — studi kasus OPI Jakabaring → Unsri (Task 1)
- `baselines.py` — implementasi Standard DFS & Conventional Routing
- `run_scenarios.py` — sampel 20 rute real, error, uji statistik (Task 2)
- `weight_sensitivity.py` — sensitivitas bobot w1 (Task 3.2)

Perbaikan kode terkait: `src/algorithms/ida_star_routing/ida_star_balanced.py`
— tiga aturan pruning non-admissible (depth cap 20 hop, dua filter jarak lurus)
diperbaiki karena membuang jalur valid. Hasilnya pencarian lebih lengkap tapi
lebih lambat; fallback rate ke Dijkstra di bawah timeout 60 detik kira-kira
tidak berubah (~7/15 vs baseline 6/15 pada uji 15 pasangan acak) — perbaikan
parsial, bukan solusi tuntas.

---

## Task 1 — Studi Kasus OPI Jakabaring → Universitas Sriwijaya

Rute 22 segmen yang sama seperti di naskah Bagian 3.2 (estimasi sistem
56.86650973326238 menit).

| Metrik | Nilai |
|---|---|
| Total segmen | 22 |
| Segmen dengan ground truth riil | 17 (77.272727%) |
| Segmen formula-only (WALK×2, TRANSFER×3) | 5 |
| Sum ground truth riil (17 segmen) | 29.788479 menit |
| Sum estimasi formula (5 segmen) | 28.966249 menit |
| **Waktu teranchor-data (real+formula)** | **58.754728 menit** |
| Estimasi sistem | 56.866510 menit |
| Selisih absolut | 1.888219 menit |
| Persentase error | 3.320441% |

Rincian 22 segmen (mode, koridor, from→to lokal, durasi formula, durasi real,
sumber) ada di output `run_case_study.py`. 4 segmen LRT bersumber jadwal
resmi, 13 segmen Feeder K4+K7 bersumber survei 30 hari, 5 segmen WALK/TRANSFER
formula-only sesuai definisi.

---

## Task 3.1 — Cakupan Ground Truth Aktual

**319/423 edge = 75.4137%** (bukan 184/423 = 43,5% seperti klaim naskah).

Bug ditemukan dan diperbaiki dalam proses verifikasi: kolom `corridor` di CSV
survei pakai format "Angkot Feeder Koridor N", sedangkan field `route` di graf
pakai "Feeder Koridor N" (tanpa "Angkot") — mismatch ini membuat hampir semua
match Feeder gagal secara diam-diam pada perhitungan pertama (yang sempat
menghasilkan angka salah 23,4%).

Rincian 104 edge yang genuinely tidak tercakup:
| Sumber ketidaktercakupan | Jumlah edge | Penjelasan |
|---|---|---|
| Teman Bus Koridor 5 | 75/96 | Survei 30 hari korridor ini hanya mencakup 22 dari 97 halte lokal |
| Feeder Koridor 5 | 20/40 | Graf punya edge dua arah, survei hanya mencatat satu arah |
| LRT Sumsel | 5/24 | Edge non-adjacent (lompat beberapa stasiun), tak cocok ke selisih jadwal antar-stasiun bertetangga |
| Feeder Koridor 7 | 3 | Di luar rentang halte yang tersurvei |
| Feeder Koridor 8 | 1 | Di luar rentang halte yang tersurvei |

---

## Task 3.2 — Sensitivitas Bobot w1–w4

**Temuan utama: tidak ada implementasi formula weighted-sum w1–w4 di codebase.**
`calculate_optimization_score()` (`data_structures.py`) adalah satu-satunya
kode terkait, tapi pakai 3 kriteria (time/cost/transfers, tanpa jarak) dengan
bobot berbeda (0.4/0.3/0.3), dan hanya dipanggil dari `ida_star.py` yang tidak
dipakai produksi (`api/app.py` memakai `ida_star_balanced.py`). Seluruh
pemanggilan routing di codebase memakai `optimization_mode="time"` —
sistem produksi tidak pernah menjalankan skoring 4-kriteria berbobot.

Formula direkonstruksi sesuai deskripsi naskah (normalisasi min-max per
kriteria, weighted sum) dan diuji pada rute kandidat nyata dari 3 algoritma:

| Pasangan O-D | n kandidat | Hasil |
|---|---|---|
| OPI Jakabaring → Unsri | 2 (Standard DFS gagal) | **Pergeseran skor maksimum 25,000000%** untuk w1 ±0,10 |
| 2 pasangan pendek lain | 3 masing-masing | Kandidat identik dari ketiga algoritma → tidak informatif |

**Klaim naskah "<8%" tidak terverifikasi** — angka aktual yang terukur adalah 25%.

---

## Task 3.3 — Struktur Skenario Pengujian

Tabel 2 = 2 kategori (simple/complex) × 3 algoritma = 6 baris, dengan n=1 rute
per sel — dikonfirmasi langsung dari struktur tabel naskah.

**Inkonsistensi internal ditemukan**: bagian Kesimpulan menulis "enam skenario
pengujian yang representatif (tiga skenario sederhana dan tiga skenario
kompleks)" — klaim ini menyiratkan 3 rute simple + 3 rute complex yang
berbeda-beda, padahal Tabel 2 hanya menunjukkan 1 baris per kategori per
algoritma. Kedua klaim ini tidak sama dan naskah tidak menjelaskan mana yang
benar.

---

## Task 2 — Analisis Error & Uji Statistik (sampel baru, n=20 rute real)

Kategori berdasarkan jarak lurus origin-destination (naskah tidak memberi
definisi kuantitatif lain): simple = 1,5–5 km (n=10 disampel), complex =
8–16 km (n=10 disampel). O-D pairs adalah halte nyata dari graf jaringan
(seeded, reproducible), bukan titik sintetis.

**Catatan metodologi**: percobaan pertama sempat memakai timeout 30 detik
khusus untuk Enhanced DFS-IDA* (agar tidak menggantung), tapi ini memberi
handicap tidak adil karena Standard DFS/Conventional tidak dibatasi wall-clock
serupa. Angka final di bawah adalah dari run TANPA cap 30 detik itu (timeout
internal algoritma sendiri tetap berlaku: 15 detik × ≤9 kombinasi = ≤135
detik per query) — perbandingan yang adil antar ketiga algoritma.

### Success rate aktual (dibandingkan klaim Tabel 2: 100% / 87% / 78%)

| Algoritma | Berhasil | Rate aktual | Klaim naskah |
|---|---|---|---|
| Enhanced DFS-IDA* | 15/20 | 75% | 100% |
| Standard DFS | 3/20 | 15% | 87% |
| Conventional Routing | 7/20 | 35% | 78% |

### Distribusi error absolut + normalitas (Shapiro-Wilk, alpha=0.05)

| Algoritma | n | Mean abs error (menit) | Shapiro W | p-value | Normal? |
|---|---|---|---|---|---|
| Enhanced DFS-IDA* | 15 | 6.935896 | 0.524289 | 0.000006 | Tidak |
| Standard DFS | 3 | 6.276866 | 0.863892 | 0.278348 | Ya |
| Conventional Routing | 7 | 10.975898 | 0.778479 | 0.024930 | Tidak |

### Uji signifikansi berpasangan (hanya skenario di mana KEDUA algoritma berhasil)

**Enhanced DFS-IDA* vs Standard DFS** — n_pairs=3, kedua distribusi normal → paired t-test
- t = -0.888368, df = 2, **p = 0.468071** → TIDAK signifikan
- Arah t negatif: Standard DFS punya error lebih kecil di 3 pasangan sampel ini

**Enhanced DFS-IDA* vs Conventional Routing** — n_pairs=7, distribusi enhanced tidak normal → Wilcoxon signed-rank
- W = 9.000000, **p = 0.843750** → tidak signifikan

**Ini bertentangan langsung dengan klaim naskah** (paired t-test p<0,05, MAE
rata-rata Enhanced DFS-IDA* 1,35 menit vs Standard DFS 2,685 menit vs
Conventional 4,115 menit, "superior secara statistik").

Catatan keterbatasan: n_pairs kecil (3 dan 6) karena success rate ketiga
algoritma rendah pada sampel 20 rute ini, dan tidak semua skenario berhasil
di ketiga algoritma sekaligus. Ini bukan artefak metodologi — ini sendiri
konsisten dengan temuan bahwa success rate asli jauh di bawah klaim naskah.
