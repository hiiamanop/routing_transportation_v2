# Desain Manuskrip Bilingual dan Figure Pemodelan Pemilihan Moda

## Tujuan

Menghasilkan dua paket manuskrip lengkap dan terpisah—Bahasa Indonesia dan Bahasa Inggris—mengikuti struktur *Manuscript Template Jurnal Kejuruteraan 2025 (anonymous double-blind manuscript)*. Artikel berfokus pada analisis pemilihan moda dengan Multinomial Logit (MNL); sistem pencarian rute diposisikan sebagai instrumen pembentuk alternatif perjalanan.

## Judul

**Bahasa Indonesia**

*Pemodelan Pemilihan Moda dalam Jaringan Transportasi Publik Terintegrasi di Kota Palembang Menggunakan Multinomial Logit*

**English**

*Mode Choice Modelling in Palembang’s Integrated Public Transport Network Using Multinomial Logit*

## Struktur keluaran

```text
docs/manuscript/
├── id/
│   ├── manuscript.md
│   └── figures/
│       ├── figure_01_alur_penelitian.svg
│       ├── figure_01_alur_penelitian.png
│       └── ...
└── en/
    ├── manuscript.md
    └── figures/
        ├── figure_01_research_flow.svg
        ├── figure_01_research_flow.png
        └── ...
```

Setiap figure dibuat dalam dua versi bahasa terpisah. Angka, geometri, skala, warna, dan susunan panel identik; semua teks internal, anotasi, legenda, sumbu, serta caption diterjemahkan.

## Sumber data dan integritas

Sumber tunggal analisis:

```text
dataset/choices_long_20260919_112629_diseragamkan.csv
```

Dataset terbaru dinyatakan mewakili 400 responden berbeda dan satu observasi per responden. Semua artefak olahan lama harus dibangkitkan ulang agar tidak mencampur hasil versi dataset sebelumnya.

Prinsip integritas:

- CSV sumber tidak diubah.
- Checksum SHA-256 sumber dicatat dalam laporan audit.
- Tabel, angka manuskrip, dan figure berasal dari artefak JSON/CSV yang dibangkitkan skrip.
- Tidak ada angka hasil yang diketik berdasarkan ingatan.
- Usia tidak ditampilkan atau dibahas.
- Naskah tetap anonim.
- Pendanaan menggunakan placeholder.
- Nama dan nomor komite etik tidak dicantumkan.
- Partisipasi sukarela, persetujuan sebelum pengisian, dan anonimitas dinyatakan secara faktual.

## Konteks dan desain survei

Periode pengumpulan data: 1 Agustus–16 September 2026.

Kriteria inklusi:

1. berdomisili dan rutin beraktivitas di Kota Palembang; dan
2. mengetahui pilihan transportasi yang tersedia di Kota Palembang.

Teknik pengambilan sampel adalah *non-probability convenience sampling*. Tautan/instrumen disebarkan melalui:

1. survei langsung kepada warga umum;
2. jaringan mahasiswa; dan
3. media sosial.

Survei langsung dilakukan melalui wawancara. Enumerator membacakan dan menjelaskan pertanyaan serta urutan alternatif yang sama seperti aplikasi secara netral, tanpa menyarankan pilihan. Pengisian melalui jaringan mahasiswa dan media sosial dilakukan secara mandiri.

Setiap responden menentukan titik asal dan tujuan untuk perjalanan rutin mereka. Waktu keberangkatan ditetapkan otomatis sesuai waktu pengisian atau wawancara. Aplikasi membentuk beberapa alternatif rute beserta atributnya, lalu responden memilih satu alternatif yang paling disukai.

Pilihan didefinisikan sebagai **pilihan rute yang diniatkan untuk perjalanan rutin nyata responden** (*intended route choice for the respondent’s actual routine trip*). Pilihan bukan *revealed preference*, karena realisasi perjalanan setelah pengisian tidak diverifikasi.

## Klasifikasi moda

1. **Transportasi publik:** LRT, Teman Bus, dan Angkot Feeder.
2. **Kendaraan pribadi:** motor atau mobil pribadi.
3. **Transportasi nonpublik berbayar:** layanan berbasis permintaan atau sewaan di luar jaringan transportasi publik.

Istilah *ride-hailing* pada data lama tidak digunakan sebagai istilah substantif umum dalam manuskrip.

## Pipeline analisis

```text
Dataset survei terbaru
→ audit dan pembersihan reproducible
→ dataset analisis final
→ statistik deskriptif
→ MNL dasar
→ MNL + ASC kendaraan pribadi
→ analisis sensitivitas
→ tabel dan figure
→ manuskrip Indonesia dan Inggris
```

Aturan kualitas data yang telah disetujui:

- identitas observasi diverifikasi;
- alternatif identik dalam satu choice set digabung;
- choice set dengan kurang dari dua alternatif unik dikeluarkan;
- observasi harus mempunyai tepat satu pilihan;
- observasi dengan `time_minutes > 1000` dikeluarkan;
- observasi dengan `cost_rupiah > 100000` dikeluarkan;
- setiap eksklusi dicatat bersama alasannya.

Karena dataset terbaru mempunyai satu UUID per responden dan satu observasi per UUID, standard error MNL biasa menjadi inferensi utama. Clustered standard error tidak diposisikan sebagai kebutuhan utama.

## Spesifikasi model

Model dasar:

\[
U_{ij}=\beta_1 Time_{ij}+\beta_2 Cost_{ij}+\beta_3 Transfer_{ij}+\beta_4 Access_{ij}+\beta_5 Comfort_{ij}+\beta_6 Reliability_{ij}
\]

Model utama dengan alternative-specific constant (ASC):

\[
U_{ij}=\alpha_{private}I(private\ vehicle)_{ij}+\beta^T X_{ij}
\]

Transportasi publik menjadi kategori acuan. Transportasi nonpublik berbayar tidak diklasifikasikan sebagai kendaraan pribadi.

Keluaran estimasi:

- koefisien;
- standard error;
- statistik t dan signifikansi 5%;
- log-likelihood;
- McFadden \(\rho^2\);
- AIC dan BIC;
- *value of time* hanya ketika tanda koefisien waktu dan biaya bermakna;
- peringatan otomatis untuk tanda koefisien yang bertentangan dengan teori.

Analisis sensitivitas:

1. model penuh + ASC;
2. tanpa `access_km`;
3. tanpa `transfers`;
4. tanpa `access_km` dan `transfers`;
5. tanpa transportasi nonpublik berbayar.

Likelihood-ratio test hanya digunakan untuk model tersarang dengan sampel yang sama. Model tanpa transportasi nonpublik berbayar diperlakukan sebagai sensitivitas sampel dan tidak dibandingkan langsung memakai LR, AIC, atau BIC terhadap model dengan sampel berbeda.

## Struktur manuskrip

Struktur mengikuti template Jurnal Kejuruteraan:

1. Title
2. Abstract dan Keywords
3. Introduction
4. Methodology
5. Results and Discussion
6. Conclusion
7. Acknowledgement
8. Declaration of Competing Interest
9. References

### Abstract

Masing-masing 200–250 kata, maksimal lima kata kunci, berisi konteks, tujuan, sampel, metode, hasil utama setelah estimasi ulang, implikasi, dan keterbatasan.

### Introduction

- peralihan kendaraan pribadi ke transportasi publik;
- konteks jaringan Palembang;
- pentingnya memahami pemilihan moda;
- dasar MNL;
- celah choice set yang disesuaikan dengan perjalanan rutin responden;
- tujuan dan kontribusi penelitian.

### Methodology

Subbagian:

1. Study Context and Integrated Transport Network
2. Application-Generated Choice Sets
3. Survey Design and Data Collection
4. Variables
5. Data Quality and Exclusion Rules
6. Multinomial Logit Specification
7. Sensitivity Analysis

Enam atribut adalah waktu, biaya, transfer, jarak akses, kenyamanan, dan keandalan. Skor kenyamanan dan keandalan dijelaskan sebagai parameter sistem, bukan pengukuran objektif lapangan.

### Results and Discussion

Subbagian:

1. Final Analytical Sample
2. Descriptive Choice Patterns
3. Attribute Variation and Correlation
4. MNL Estimation Results
5. Sensitivity and Model Selection
6. Interpretation and Policy Implications

### Conclusion

Tidak mengklaim kausalitas. Merangkum determinan relatif stabil, kecenderungan kendaraan pribadi, performa dan keterbatasan model, implikasi kebijakan, dan kebutuhan validasi lanjutan.

### Bagian akhir

Acknowledgement menggunakan:

- ID: “Penelitian ini didukung oleh `[NAMA PEMBERI DANA]` melalui hibah nomor `[NOMOR HIBAH]`.”
- EN: “This research was supported by `[FUNDING AGENCY]` under grant number `[GRANT NUMBER]`.”

Declaration of Competing Interest menggunakan “None” bila tidak ada konflik.

## Tabel utama

1. Definisi, satuan, dan dugaan tanda variabel.
2. Karakteristik responden selain usia.
3. Alur pembersihan dan eksklusi data.
4. Estimasi model dasar dan MNL + ASC.
5. Analisis sensitivitas dan likelihood-ratio test.

Tabel dan teks tidak mengulang seluruh informasi figure.

## Figure

Semua figure dibuat dalam dua bahasa, SVG vektor dan PNG 300 dpi, lebar sekitar 17 cm, palet ramah buta warna, dan tetap dapat dibedakan dalam grayscale.

### Figure 1 — Alur penelitian dan pembentukan choice set

Asal–tujuan responden → jaringan transportasi → alternatif rute → atribut → pilihan → audit → MNL.

### Figure 2 — Distribusi pilihan moda

Diagram batang horizontal untuk transportasi publik, kendaraan pribadi, dan transportasi nonpublik berbayar, dengan jumlah dan persentase.

### Figure 3 — Variasi dan korelasi atribut

- Panel A: persentase choice set dengan variasi tiap atribut.
- Panel B: heatmap korelasi enam atribut.

### Figure 4 — Koefisien MNL + ASC

Forest plot koefisien dan 95% confidence interval, garis nol, serta pembedaan arah sesuai/tidak sesuai teori.

### Figure 5 — Perbandingan kecocokan model

AIC dan BIC untuk model dengan sampel sama. Model tanpa transportasi nonpublik berbayar ditampilkan terpisah atau hanya melalui catatan sensitivitas sampel.

### Figure 6 — Stabilitas koefisien

Perbandingan koefisien waktu, biaya, kenyamanan, keandalan, dan ASC antarspesifikasi.

## Implementasi figure

Satu generator, `scripts/generate_research_figures.py`, membaca artefak analisis yang sama dan memakai kamus label `id`/`en`. Tidak ada duplikasi logika statistik. Diagram alur juga dibangkitkan secara programatis.

## Referensi eksternal

Referensi mengutamakan:

1. artikel jurnal mengenai pemilihan moda dan integrasi transportasi publik;
2. literatur utama discrete choice dan MNL;
3. dokumen resmi transportasi Palembang;
4. sumber resmi pemerintah/operator;
5. metadata DOI atau URL penerbit yang dapat diverifikasi.

Referensi disusun alfabetis mengikuti template. Klaim tanpa sumber kuat ditulis sebagai asumsi atau keterbatasan.

## Validasi

### Data dan analisis

- checksum sumber cocok dengan audit;
- setiap choice set final mempunyai ≥2 alternatif unik dan tepat satu pilihan;
- hasil estimasi dapat direproduksi dari satu perintah;
- angka tabel dan figure cocok dengan JSON/CSV.

### Figure

- SVG valid;
- PNG 300 dpi;
- lebar sekitar 17 cm;
- tidak ada label terpotong atau bertumpuk;
- terbaca dalam grayscale;
- versi Indonesia dan Inggris memakai data identik.

### Manuskrip

- susunan bagian mengikuti template;
- abstrak masing-masing 200–250 kata;
- maksimal lima kata kunci;
- jumlah dan urutan tabel/figure identik;
- angka statistik identik;
- referensi dan sitasi konsisten;
- tidak memuat identitas penulis;
- placeholder pendanaan tetap terlihat untuk pemeriksaan prapengiriman.

## Batas klaim ilmiah

Manuskrip tidak akan:

- menyebut pilihan sebagai *revealed preference*;
- mengklaim hubungan kausal;
- mengklaim probability sampling;
- menafsirkan tanda koefisien yang tidak wajar sebagai preferensi substantif;
- menyembunyikan rendahnya McFadden \(\rho^2\);
- memakai koefisien yang belum layak sebagai rekomendasi produksi;
- mengarang rincian etika, pendanaan, demografi, atau prosedur yang tidak tersedia.
