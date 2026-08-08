# Rencana Pembangunan Sistem

Dokumen ini menurunkan **Gambar 4 — Flowchart sistem informasi integrasi antar moda** menjadi daftar komponen yang harus dibangun, lengkap dengan status masing-masing.

Sasarannya: sistem informasi integrasi tiga moda angkutan publik Kota Palembang (LRT Sumsel, Teman Bus, Angkutan Feeder) yang tidak hanya **menghitung rute**, tetapi juga **memodelkan bagaimana calon penumpang memilih** di antara rute-rute itu.

> **Catatan arah penelitian.** Fokus bukan lagi perbandingan algoritma. Dijkstra sudah final sebagai mesin pencarian rute. Kontribusi yang sedang dibangun ada di sisi perencanaan transportasi: pemodelan preferensi dan pemilihan moda.

> **📍 Checkpoint 2026-08-08.** S-1, S-2, S-3, S-4 selesai dibangun & diuji. **Aplikasi sudah live di https://transportasi.meetsin.id** -- siap disebar ke responden. S-6 (kumpulkan ±200 observasi) **baru mulai**, 1 observasi asli terkumpul. S-5/S-7 sudah diputuskan **diganti penuh** (bukan dipertahankan berdampingan), tapi implementasinya **sengaja ditunda** sampai data S-6 cukup -- menampilkan probabilitas dari β yang belum matang ke pengguna asli berisiko mempengaruhi pilihan mereka sendiri, mencemari data yang sedang dikumpulkan. S-8 belum dikerjakan. Lihat bagian 7 untuk urutan pengerjaan terbaru.

---

## 1. Peta status

Flowchart terdiri dari dua cabang paralel yang bertemu di tengah.

| Cabang | Isi | Status |
|---|---|---|
| **Kiri (penyediaan / _supply_)** | Graf jaringan → pencarian rute → enumerasi alternatif → hitung atribut | ✅ Selesai |
| **Kanan (pemilihan / _demand_)** | Survei → estimasi β → utilitas → probabilitas | 🔶 Alat siap (S-1..S-4), data belum cukup (S-6) |
| **Integrasi & keluaran** | Gabungkan alternatif dengan probabilitas → rekomendasi | 🔶 Sebagian (S-7 menunggu S-6) |
| **Umpan balik** | Simpan hasil → re-estimasi berkala | 🔶 Skema riwayat β sudah ada, penjadwalan belum (S-8) |

Ringkasnya: **cabang kiri sudah berdiri, cabang kanan sekarang punya alat lengkap (formulir, ekspor data, estimator) -- tinggal menunggu data cukup untuk dipakai sungguhan.**

---

## 2. Masukan data

| Kotak pada flowchart | Isi | Status | Letak |
|---|---|---|---|
| Data Jaringan & Layanan | rute, trayek, halte, jadwal, peta jaringan | ✅ | `dataset/network_data_correct_bidirectional.json`, `dataset/lrt/`, `dataset/kmz_file/` |
| Data Permintaan Perjalanan | asal, tujuan, waktu berangkat | ✅ | masukan pengguna di halaman utama |
| Data Atribut Moda | waktu, biaya, kenyamanan, aksesibilitas, keandalan | ✅ | `src/core/service_model.py` |
| **Data Preferensi Pengguna (Survei)** | | | |
| — penilaian atribut | skala 1–5 lima kriteria | ✅ | halaman `/preferensi` |
| — **pilihan moda aktual** | alternatif mana yang dipilih | ✅ | `POST /api/choice` → `dataset/survey/choices.jsonl` |
| — **karakteristik responden** | usia, pekerjaan, pendapatan, kepemilikan kendaraan, frekuensi perjalanan | ✅ | halaman `/responden` → `POST /api/respondent` → `dataset/survey/respondents.jsonl` |

### S-1. Formulir karakteristik responden -- ✅ Selesai

Halaman `/responden`, tanpa autentikasi (`respondent_id` = UUID anonim di localStorage, sama dgn yg dipakai `/api/choice`). Field: usia, jenis kelamin, pekerjaan, rentang pendapatan, kepemilikan kendaraan pribadi, maksud perjalanan, frekuensi pakai angkutan umum. Digabung otomatis ke data pilihan lewat `respondent_id` saat ekspor (lihat S-3).

**Belum dikerjakan (perluasan lanjutan, bukan bagian wajib S-1/S-4):** karakteristik responden belum dipakai sbg *interaction term* di model MNL (S-4) -- kolomnya sudah tersedia di hasil ekspor, tinggal dipetakan jadi variabel model kalau β dasar sudah stabil.

---

## 3. Cabang kiri — penyediaan rute

Semua sudah berjalan. Didaftar agar dokumen ini utuh.

| Langkah | Status | Letak |
|---|---|---|
| Bangun graf jaringan antar moda | ✅ | `data_loader.py` |
| Algoritma pencarian rute (Dijkstra) | ✅ | `dijkstra.py` |
| Enumerasi alternatif (interchange) | ✅ | `find_route_alternatives()` |
| Hitung atribut tiap alternatif | ✅ | `route_attributes()` |
| Simpan himpunan $A_i$ + atribut $X_{ij}$ | ✅ | field `attributes` pada respons |

### S-2. Perbanyak alternatif per perjalanan -- ✅ Selesai

**Diagnosis** (dibuktikan lewat pengujian langsung, bukan dugaan): mekanisme "cari jalur lain dgn koridor terbaik dihukum" (`avoid_routes`) sudah ada duluan tapi tidak berdaya -- hukuman sampai 100.000 menit tetap balik ke koridor yang sama. Kesimpulan: jaringan 11 koridor ini **jarang secara topologis**, banyak pasangan titik cuma punya SATU jalur multi-moda dlm radius transfer 500m. Melonggarkan penalti tidak akan pernah cukup di kasus ini.

**Solusi**: alternatif **"Kendaraan Pribadi"** ditambahkan sbg anggota TETAP himpunan pilihan (`private_vehicle_route()` di `gmaps_style_routing.py`), bukan cuma fallback saat transit gagal total. Jarak & jalur dari OSRM (profil driving, real road), waktu dihitung dari asumsi kecepatan motor efektif (bukan durasi bawaan OSRM yg terlalu optimis). Sekaligus relevan dgn topik penelitian: yg diperebutkan memang perpindahan dari kendaraan pribadi.

**Hasil ukur**: 10 pasang asal-tujuan acak, sebelumnya 0/10 hasilkan ≥2 alternatif, sekarang **10/10**.

---

## 4. Cabang kanan — model pemilihan

Alat sudah lengkap (S-3, S-4). Yang masih kurang murni **data** (S-6).

### S-3. Berkas data pilihan siap-estimasi -- ✅ Selesai

`scripts/export_long_format.py` (CLI) dan `GET /api/survey/export` (unduh langsung dari server) -- keduanya pakai satu sumber logika yang sama, `src/core/survey_export.py`. Ubah `choices.jsonl` jadi tabel long-format (satu baris per observasi × alternatif, kolom `chosen` 0/1), **digabung otomatis** dgn karakteristik responden (`respondents.jsonl`) lewat `respondent_id`. Melaporkan % observasi yang berhasil ter-*join* sbg indikator kesiapan data.

| observation_id | label | time_minutes | cost_rupiah | ... | vehicle_ownership | chosen |
|---|---|---|---|---|---|---|
| 0 | Rekomendasi | 42,0 | 8000 | ... | Motor | 0 |
| 0 | Termurah | 55,0 | 5000 | ... | Motor | 1 |

Diuji dgn 200 observasi sintetis (ditandai `synthetic: true`, file terpisah `*.dummy.jsonl`, di-gitignore) -- setiap observasi tepat 1 baris `chosen=1`, tidak ada yg hilang.

### S-4. Estimasi parameter β -- ✅ Skrip siap, menunggu data

`scripts/estimate_mnl.py` -- Newton-Raphson murni (cukup `numpy`, dependency terpisah `scripts/requirements.txt`, tidak membebani image API). Koefisien generic (satu β per atribut, standar utk pemilihan rute/moda).

$$L(\beta) = \sum_{n}\sum_{j} y_{nj} \ln P_{nj}, \qquad P_{nj} = \frac{e^{U_{nj}}}{\sum_{m} e^{U_{nm}}}, \qquad U_{nj} = \beta^{\top} X_{nj}$$

Keluaran yang **wajib** dilaporkan di naskah -- semua sudah diimplementasikan:

- nilai $\beta$ tiap atribut beserta galat bakunya
- **statistik t** tiap koefisien (signifikan atau tidak)
- $\rho^2$ McFadden (kecocokan model)
- **tanda koefisien harus masuk akal**: waktu dan biaya negatif, kenyamanan dan keandalan positif. Tanda yang terbalik adalah pertanda ada yang salah pada data, bukan temuan -- skrip mendeteksi & memperingatkan otomatis.
- nilai waktu (_value of time_) = $\beta_{\text{waktu}} / \beta_{\text{biaya}}$ — **cuma dilaporkan kalau kedua koefisien bertanda benar**, kalau tidak ditulis eksplisit "tidak dilaporkan" (drpd angka yg menyesatkan)

**Verifikasi yang sudah dilakukan**: gradien & Hessian analitik dicocokkan dgn *finite-difference* numerik (cocok sampai presisi ~5×10⁻⁵); self-check bawaan (`--demo`) membangkitkan data dgn β yg SUDAH DIKETAHUI dan membuktikan estimator berhasil memulihkannya; diuji juga dgn 1 observasi asli utk pastikan gagal dgn pesan jelas (Hessian singular), bukan crash, saat data belum cukup.

**Riwayat re-estimasi (S-8) sudah tersiapkan sekalian**: tiap run **ditambahkan** (bukan menimpa) ke `dataset/survey/beta_history.jsonl`.

**Perluasan: interaction term preferensi (`--interactions`).** Data "Penilaian Atribut" dari `/preferensi` (skala 1-5) ditelaah ulang terhadap Gambar 4 -- sudah sejak rancangan awal dimaksudkan masuk ke cabang estimasi MNL, bukan cuma fitur UX. Tapi rating itu **sama nilainya utk semua alternatif** dlm satu observasi, jadi tidak bisa masuk sbg efek utama berdiri sendiri (otomatis coret sendiri di rumus $P_{ij}$ krn pembilang & penyebut sama-sama kena kali angka yg sama). Solusinya: **interaction term**, dikalikan dgn atribut rute yg memang beda-beda antar alternatif --

$$U_{ij} = \sum_{k=1}^{6} \beta_k X_{kij} + \sum_{k=1}^{5} \gamma_k \big(X_{kij} \times p_{k,n}\big)$$

tetap rumus $U_{ij}=\sum\beta_k X_{kij}$ yang SAMA PERSIS dgn di flowchart, cuma $X_{kij}$-nya diperkaya (11 kolom, bukan 6) -- bukan model/metode baru. "Jumlah transfer" tidak punya pasangan interaksi krn `/preferensi` tidak punya kriteria itu. Preferensi yang belum diisi (`respondent_id` belum pernah buka `/preferensi`) diimputasi netral (3, titik tengah skala) drpd dibuang -- data masih sedikit selama S-6 berjalan. Diverifikasi dgn self-check terpisah (data sintetis dgn efek interaksi yg SUDAH DIKETAHUI, termasuk skenario preferensi hilang).

### S-5. Perhitungan utilitas dan probabilitas saat melayani permintaan

Setelah β tersedia, hitung $U_{ij}$ dan $P_{ij}$ untuk setiap alternatif pada setiap pencarian, lalu sertakan dalam respons.

### S-6. Ukuran sampel

Reviewer sudah pernah mempermasalahkan jumlah pengujian yang terlalu sedikit. Patokan lazim studi pemilihan moda: **minimal 30 observasi per parameter yang diestimasi**. Dengan 6 atribut, artinya **±200 observasi pilihan**, bukan 200 responden — satu responden bisa menyumbang beberapa perjalanan.

---

## 5. Integrasi dan keluaran

| Kotak pada flowchart | Status | Catatan |
|---|---|---|
| Gabungkan $A_i$ dengan $P_{ij}$, rekomendasi = probabilitas tertinggi | ❌ | kini masih memakai penjumlahan berbobot dari penilaian mandiri pengguna |
| Rekomendasi rute (moda + titik transfer) | ✅ | |
| Estimasi perjalanan (waktu, biaya, transfer) | ✅ | |
| **Probabilitas pemilihan moda (semua alternatif)** | ❌ | perlu tampilan baru |
| Ulangi bila pengguna mengubah preferensi/masukan | ✅ | lewat halaman `/preferensi` |

### S-7. Peralihan dari penjumlahan berbobot ke probabilitas

Perbedaannya mendasar, dan inilah yang menjawab keberatan reviewer soal bobot yang tidak dijustifikasi:

| | Sekarang | Sasaran |
|---|---|---|
| Sumber bobot | pengguna menilai dirinya sendiri (1–5) | β diestimasi dari pilihan nyata banyak responden |
| Sifat | subjektif, berbeda tiap pengguna | empiris, satu set untuk populasi |
| Keluaran | satu rute terpilih | sebaran probabilitas antar alternatif |
| Uji statistik | tidak ada | statistik t, $\rho^2$ |

**Yang tidak boleh berubah:** preferensi hanya **menambah** rekomendasi personal. Jawaban umum — Tercepat, Termurah, Transfer paling sedikit — harus tetap sama bagi siapa pun. Saat ini hal itu dijamin secara struktural: `find_route_alternatives()` dipanggil tanpa mengetahui apa pun tentang preferensi. **Pertahankan sifat ini ketika probabilitas ditambahkan.**

---

## 6. Umpan balik dan pembaruan berkala

### S-8. Re-estimasi berkala

Kotak terakhir flowchart: simpan hasil perjalanan aktual, lalu perbarui β secara berkala. Yang diperlukan: penjadwalan estimasi ulang, penyimpanan riwayat β (agar perubahan preferensi masyarakat bisa ditelusuri), dan pencatatan versi model pada setiap rekomendasi.

Tidak mendesak sampai S-4 selesai, tetapi **skema penyimpanannya harus disiapkan sejak awal** — menambah kolom pada data yang sudah terkumpul jauh lebih sulit daripada menyediakannya sekarang.

---

## 7. Urutan pengerjaan

Berurutan menurut ketergantungan, bukan menurut kemudahan.

| # | Pekerjaan | Status | Menghambat apa |
|---|---|---|---|
| S-2 | Perbanyak alternatif per perjalanan | ✅ Selesai | — |
| S-1 | Formulir karakteristik responden | ✅ Selesai | — |
| S-3 | Ekspor data siap-estimasi | ✅ Selesai | — |
| S-4 | Estimasi β (skrip) | ✅ Selesai | — |
| **S-6** | **Kumpulkan ±200 observasi** | 🔶 **Baru 1 observasi asli** | **S-5, S-7 — blocker satu-satunya sekarang** |
| S-5 | Utilitas & probabilitas saat melayani | ❌ Belum | Setelah S-6 cukup + S-4 dijalankan di data asli |
| S-7 | Tampilkan probabilitas, alihkan rekomendasi | ❌ Belum | Setelah S-5 |
| S-8 | Re-estimasi berkala (penjadwalan) | 🔶 Riwayat β (S-4) sudah tersimpan otomatis, penjadwalannya belum | — |

**Satu-satunya pekerjaan mendesak sekarang: sebar aplikasi & kumpulkan data nyata (S-6).** Semua alat (formulir, pencarian alternatif, ekspor, estimator) sudah teruji dan siap pakai -- begitu ±200 observasi terkumpul, tinggal jalankan `scripts/export_long_format.py` lalu `scripts/estimate_mnl.py` (atau unduh lewat `GET /api/survey/export`), tanpa perlu sentuh kode lagi.

---

## 8. Keterbatasan yang harus dinyatakan di naskah

Bukan cacat yang perlu disembunyikan, melainkan syarat kejujuran ilmiah.

1. **Headway armada belum terukur.** Feeder 12 menit dan Teman Bus 15 menit adalah taksiran; tidak ada data headway nyata pada dataset manapun. Hanya LRT yang memakai jadwal resmi.
2. **Kecepatan operasi disederhanakan.** 25 km/jam jam sibuk (07:00-09:00, 12:00-14:00, 16:00-19:00) dan 32,5 km/jam di luar itu, seragam per koridor, bukan per ruas jalan. Jendela jam sibuk sendiri berdasarkan pengetahuan lokal pemilik penelitian (bukan data pengukuran lalu lintas), termasuk jendela siang (anak pulang sekolah).
3. **Skor kenyamanan dan keandalan bersifat redaksional.** Ditetapkan per moda berdasarkan pertimbangan, bukan hasil pengukuran. Idealnya kelak diganti dengan penilaian responden.
4. **Sepuluh halte masih menyimpang >50 m** dari jalur terekam dan perlu survei ulang lapangan.
5. **Responden bersifat swa-pilih** (siapa pun yang memakai aplikasi), bukan sampel acak — sehingga hasilnya belum tentu mewakili seluruh penduduk kota.
6. **Perilaku terungkap di dalam aplikasi belum tentu sama dengan perjalanan nyata**: memilih rute pada layar tidak sama dengan benar-benar menempuhnya.
7. **Estimasi kendaraan pribadi bukan navigasi belok-per-belok.** Jarak & jalur dari OSRM (mesin publik, tanpa SLA, ada cooldown 30 detik kalau gagal) kalau tersedia, kalau tidak jatuh ke estimasi garis lurus × 1,3. Waktu tempuh dari asumsi kecepatan motor efektif (20/28 km/jam sibuk/normal) -- bukan hasil pengukuran GPS kendaraan nyata, dan biaya cuma estimasi BBM motor (tidak termasuk parkir/penyusutan, tidak memodelkan mobil).
8. **Karakteristik responden belum dipakai sbg interaction term di model (S-4).** Datanya sudah terkumpul & tergabung di ekspor, tapi β saat ini murni dari 6 atribut rute -- variabel sosio-ekonomi baru bisa menjelaskan variasi antar kelompok kalau ditambahkan sbg perluasan lanjutan.
