# Rencana Pembangunan Sistem

Dokumen ini menurunkan **Gambar 4 — Flowchart sistem informasi integrasi antar moda** menjadi daftar komponen yang harus dibangun, lengkap dengan status masing-masing.

Sasarannya: sistem informasi integrasi tiga moda angkutan publik Kota Palembang (LRT Sumsel, Teman Bus, Angkutan Feeder) yang tidak hanya **menghitung rute**, tetapi juga **memodelkan bagaimana calon penumpang memilih** di antara rute-rute itu.

> **Catatan arah penelitian.** Fokus bukan lagi perbandingan algoritma. Dijkstra sudah final sebagai mesin pencarian rute. Kontribusi yang sedang dibangun ada di sisi perencanaan transportasi: pemodelan preferensi dan pemilihan moda.

---

## 1. Peta status

Flowchart terdiri dari dua cabang paralel yang bertemu di tengah.

| Cabang | Isi | Status |
|---|---|---|
| **Kiri (penyediaan / _supply_)** | Graf jaringan → pencarian rute → enumerasi alternatif → hitung atribut | ✅ Selesai |
| **Kanan (pemilihan / _demand_)** | Survei → estimasi β → utilitas → probabilitas | 🔶 Baru pengumpulan datanya |
| **Integrasi & keluaran** | Gabungkan alternatif dengan probabilitas → rekomendasi | 🔶 Sebagian |
| **Umpan balik** | Simpan hasil → re-estimasi berkala | ❌ Belum |

Ringkasnya: **separuh kiri sudah berdiri, separuh kanan baru diletakkan pondasinya.**

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
| — **karakteristik responden** | usia, pekerjaan, pendapatan, kepemilikan kendaraan, frekuensi perjalanan | ❌ **belum ada** | — |

### Yang harus dibangun

**S-1. Formulir karakteristik responden.** Tanpa ini, model tidak bisa memuat variabel sosio-ekonomi, padahal justru variabel itu yang menjelaskan **mengapa** kelompok berbeda memilih berbeda. Cukup satu halaman, diisi sekali, disimpan bersama `respondent_id` yang sudah ada.

Variabel minimal yang lazim pada studi pemilihan moda:

- usia, jenis kelamin
- pekerjaan dan rentang pendapatan
- kepemilikan kendaraan pribadi (motor/mobil) — **paling menentukan**
- maksud perjalanan (kerja, sekolah, lainnya)
- frekuensi memakai angkutan umum

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

### Yang masih harus diperbaiki

**S-2. Perbanyak alternatif per perjalanan.** Ini **penghambat nyata**, bukan penyempurnaan. Pengujian pada tiga pasang asal–tujuan menghasilkan **hanya satu alternatif** setiap kali. Model pemilihan diskret memerlukan **himpunan pilihan berisi lebih dari satu opsi** — bila hanya ada satu, maka $P_{ij} = 1$ dengan sendirinya dan tidak ada yang bisa diestimasi.

Arah penanganan:

- longgarkan penalti koridor pada pencarian alternatif ke-4
- pertimbangkan memasukkan "kendaraan pribadi" sebagai alternatif pembanding di dalam himpunan pilihan — ini justru sesuai dengan masalah penelitian (_mode share_ 4,9%), karena yang sesungguhnya diperebutkan adalah perpindahan dari kendaraan pribadi ke angkutan umum
- ukur berapa persen perjalanan yang menghasilkan ≥2 alternatif, jadikan itu indikator kesiapan data

---

## 4. Cabang kanan — model pemilihan

Belum ada satu pun. Inilah inti pekerjaan berikutnya.

### S-3. Berkas data pilihan siap-estimasi

Ubah `choices.jsonl` menjadi tabel format panjang (_long format_): satu baris per **pasangan (observasi × alternatif)**, dengan penanda `dipilih` bernilai 0/1. Ini bentuk baku yang diterima semua perkakas estimasi.

| observasi | alternatif | waktu | biaya | transfer | akses_km | nyaman | andal | dipilih |
|---|---|---|---|---|---|---|---|---|
| 1 | Tercepat | 42,0 | 8000 | 1 | 0,40 | 3,2 | 3,5 | 0 |
| 1 | Termurah | 55,0 | 5000 | 0 | 1,10 | 2,4 | 2,2 | 1 |

### S-4. Estimasi parameter β

Estimasi kemungkinan maksimum (_maximum likelihood_) atas fungsi log-likelihood model logit multinomial:

$$L(\beta) = \sum_{n}\sum_{j} y_{nj} \ln P_{nj}, \qquad P_{nj} = \frac{e^{U_{nj}}}{\sum_{m} e^{U_{nm}}}, \qquad U_{nj} = \beta^{\top} X_{nj}$$

Keluaran yang **wajib** dilaporkan di naskah:

- nilai $\beta$ tiap atribut beserta galat bakunya
- **statistik t** tiap koefisien (signifikan atau tidak)
- $\rho^2$ McFadden (kecocokan model)
- **tanda koefisien harus masuk akal**: waktu dan biaya negatif, kenyamanan dan keandalan positif. Tanda yang terbalik adalah pertanda ada yang salah pada data, bukan temuan.
- nilai waktu (_value of time_) = $\beta_{\text{waktu}} / \beta_{\text{biaya}}$ — besaran yang punya arti langsung bagi perencanaan tarif

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

| # | Pekerjaan | Menghambat apa | Prioritas |
|---|---|---|---|
| S-2 | Perbanyak alternatif per perjalanan | **seluruh cabang kanan** | Mendesak |
| S-1 | Formulir karakteristik responden | mutu model, harus ada sebelum survei berjalan | Mendesak |
| S-6 | Kumpulkan ±200 observasi | S-4 | Berjalan terus |
| S-3 | Ekspor data siap-estimasi | S-4 | Setelah data masuk |
| S-4 | Estimasi β | S-5, S-7 | Inti |
| S-5 | Utilitas & probabilitas saat melayani | S-7 | Setelah S-4 |
| S-7 | Tampilkan probabilitas, alihkan rekomendasi | — | Setelah S-5 |
| S-8 | Re-estimasi berkala | — | Terakhir |

**S-2 dan S-1 harus dikerjakan lebih dulu.** Selama satu perjalanan hanya menghasilkan satu alternatif, setiap observasi yang terkumpul tidak bernilai untuk estimasi — dan waktu pengumpulan data terbuang percuma.

---

## 8. Keterbatasan yang harus dinyatakan di naskah

Bukan cacat yang perlu disembunyikan, melainkan syarat kejujuran ilmiah.

1. **Headway armada belum terukur.** Feeder 12 menit dan Teman Bus 15 menit adalah taksiran; tidak ada data headway nyata pada dataset manapun. Hanya LRT yang memakai jadwal resmi.
2. **Kecepatan operasi disederhanakan.** 25 km/jam jam sibuk dan 32,5 km/jam di luar itu, seragam per koridor, bukan per ruas jalan.
3. **Skor kenyamanan dan keandalan bersifat redaksional.** Ditetapkan per moda berdasarkan pertimbangan, bukan hasil pengukuran. Idealnya kelak diganti dengan penilaian responden.
4. **Sepuluh halte masih menyimpang >50 m** dari jalur terekam dan perlu survei ulang lapangan.
5. **Responden bersifat swa-pilih** (siapa pun yang memakai aplikasi), bukan sampel acak — sehingga hasilnya belum tentu mewakili seluruh penduduk kota.
6. **Perilaku terungkap di dalam aplikasi belum tentu sama dengan perjalanan nyata**: memilih rute pada layar tidak sama dengan benar-benar menempuhnya.
