# Sistem Informasi Integrasi Tiga Moda Angkutan Umum Kota Palembang

Pencarian rute antarmoda (LRT Sumsel, Teman Bus, Angkutan Feeder), penyediaan
alternatif perjalanan, dan pemodelan preferensi pengguna melalui survei
pemilihan rute.

**Aplikasi**: https://transportasi.meetsin.id
**Repositori**: https://github.com/hiiamanop/routing_transportation_v2.git
**Rencana pembangunan sistem**: [docs/RENCANA_SISTEM.md](docs/RENCANA_SISTEM.md)

---

## Kemampuan Sistem

- **Pencarian rute antarmoda** — Dijkstra atas jaringan gabungan Feeder, Teman
  Bus, dan LRT, termasuk segmen jalan kaki dan perpindahan antarmoda.
- **Empat alternatif per perjalanan** — tercepat, termurah, transfer paling
  sedikit, dan lewat rute lain. Estimasi kendaraan pribadi selalu disertakan
  sebagai pembanding.
- **Rekomendasi personal** — alternatif kelima "Sesuai Preferensi Saya" muncul
  bila pengguna telah mengisi penilaian lima kriteria di halaman `/preferensi`.
- **Perekaman pilihan responden** — himpunan alternatif yang ditawarkan beserta
  atributnya dan mana yang dipilih, sebagai bahan estimasi model logit
  multinomial.
- **Pengisian titik asal dari GPS** — memerlukan koneksi HTTPS (sudah terpenuhi
  pada domain produksi).
- **Peta jaringan & tagging GPS koridor** — halaman `/jaringan` untuk menyusuri
  koridor dan memperbaiki koordinat halte langsung dari lapangan.
- **Peta interaktif** — Leaflet.js dengan ubin OpenStreetMap.

Antarmuka aplikasi sepenuhnya berbahasa Indonesia.

---

## Struktur Proyek

```
routing_transportation_v2/
├── api/
│   ├── app.py                    # Server Flask (port 5001)
│   └── requirements.txt
├── frontend/                     # Next.js 16 + Tailwind
│   └── src/app/
│       ├── page.tsx              # Pencarian rute (halaman utama)
│       ├── jaringan/             # Peta jaringan + tagging GPS koridor
│       ├── preferensi/           # Penilaian 5 kriteria (skala 1-5)
│       ├── responden/            # Karakteristik responden
│       ├── about/                # Penjelasan asumsi & keterbatasan
│       ├── api/search-places/    # Proksi pencarian tempat
│       └── components/
├── src/
│   ├── core/
│   │   ├── gmaps_style_routing.py   # Penyusunan alternatif & preferensi
│   │   ├── service_model.py         # Headway, kecepatan, jam sibuk
│   │   ├── survey_export.py         # choices.jsonl -> tabel long-format
│   │   └── network_edit.py          # Penyuntingan koordinat halte
│   └── algorithms/routing/          # Dijkstra, struktur data, pemuat jaringan
├── scripts/
│   ├── export_long_format.py     # S-3: ekspor data siap estimasi
│   ├── estimate_mnl.py           # S-4: estimasi parameter beta (MNL)
│   └── ...                       # Pengolahan KMZ, waypoint, visualisasi
├── experiments/ground_truth.py   # Verifikasi terhadap data lapangan
├── dataset/                      # Data jaringan, KMZ, hasil survei
└── docs/
    ├── RENCANA_SISTEM.md         # Rencana & status pekerjaan
    └── EDARAN_GOOGLE_FORM.md     # Draft isi Google Form untuk edaran survei
```

---

## Menjalankan Secara Lokal

### Backend

```bash
cd api
pip install -r requirements.txt
python app.py
```

API berjalan di `http://localhost:5001`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend berjalan di `http://localhost:3000`. Permintaan ke `/api/*` diteruskan
ke Flask lewat rewrite di `next.config.ts`, jadi Nginx tidak diperlukan saat
pengembangan.

> Fitur GPS (pengisian titik asal, tagging koridor) berfungsi di `localhost`
> maupun HTTPS, tetapi diblokir peramban pada alamat HTTP polos selain
> localhost.

---

## Endpoint API

| Metode | Endpoint | Kegunaan |
|---|---|---|
| GET | `/api/health` | Pemeriksaan status server |
| GET | `/api/network/info` | Ringkasan jaringan (jumlah simpul, ruas, koridor) |
| POST | `/api/route/alternatives` | Pencarian rute, mengembalikan seluruh alternatif |
| GET | `/api/stops` | Daftar seluruh halte |
| GET | `/api/route/waypoints/<route_name>` | Geometri polyline satu koridor |
| PUT | `/api/network/corridor/<route_name>/stops` | Perbarui koordinat halte (tagging GPS) |
| POST | `/api/choice` | Rekam pilihan rute responden |
| POST | `/api/respondent` | Rekam karakteristik responden |
| GET | `/api/survey/export` | Unduh data survei dalam format long |

Contoh permintaan pencarian rute:

```jsonc
POST /api/route/alternatives
Content-Type: application/json

{
  "origin":      { "name": "Universitas Sriwijaya", "lat": -2.985256, "lon": 104.732880 },
  "destination": { "name": "PTC Mall",              "lat": -2.951150, "lon": 104.760900 },
  "departure_time": "2026-08-24T10:00:00+07:00",
  "preferences": { "time": 5, "cost": 3, "comfort": 2, "accessibility": 4, "reliability": 3 }
}
```

`name` bersifat opsional — hanya `lat` dan `lon` yang dipakai mesin pencarian.
`preferences` juga opsional; bila tidak dikirim, alternatif "Sesuai Preferensi
Saya" tidak dibentuk. Di luar jam operasional angkutan umum, respons **tidak**
memuat kunci `alternatives`, melainkan `public_transport_available: false`
beserta estimasi kendaraan pribadi.

---

## Data Jaringan

Graf yang dimuat API: `dataset/network_data_correct_bidirectional.json`.

- **385 simpul** (halte) dan **748 ruas** berarah
- **11 koridor**: Feeder Koridor 1–8, Teman Bus Koridor 2 dan 5, LRT Sumsel
- Koridor melingkar diperlakukan searah; koridor linier dua arah

---

## Tarif

| Moda | Tarif |
|---|---|
| Angkot Feeder | Gratis |
| Teman Bus | Rp5.000 per perjalanan |
| LRT — antarstasiun | Rp5.000 |
| LRT — ujung ke ujung | Rp10.000 |
| Perpindahan pada koridor yang sama | Tanpa biaya tambahan |

Estimasi kendaraan pribadi memakai biaya bahan bakar motor Rp250/km (±40
km/liter pada harga ±Rp10.000/liter), belum termasuk parkir maupun penyusutan.

---

## Warna Moda pada Peta

Ditetapkan di `frontend/src/app/components/icons.tsx` dan dipakai konsisten pada
kartu rute maupun polyline peta.

| Moda | Warna |
|---|---|
| Jalan kaki | Abu-abu `#5f6368` |
| Kendaraan pribadi | Hijau `#188038` |
| Teman Bus | Biru `#1a73e8` |
| Feeder Angkot | Merah `#d93025` |
| LRT | Ungu `#8430ce` |

---

## Alur Survei

1. Responden membuka aplikasi, mengisi `/responden` dan `/preferensi`.
2. Responden mencari rute perjalanan nyata, lalu menekan "Saya pilih rute ini".
   Himpunan pilihan dan pilihannya tersimpan di `dataset/survey/choices.jsonl`.
3. Ekspor ke tabel siap estimasi:
   ```bash
   python scripts/export_long_format.py --output dataset/survey/choices_long.csv
   ```
4. Estimasi parameter model:
   ```bash
   pip install -r scripts/requirements.txt
   python scripts/estimate_mnl.py --input dataset/survey/choices_long.csv
   python scripts/estimate_mnl.py --input dataset/survey/choices_long.csv --interactions
   ```

Ketiga sumber data terikat pada satu `respondent_id` anonim per peramban,
sehingga dapat digabungkan tanpa penautan manual. Draft isi Google Form untuk
edaran tersedia di [docs/EDARAN_GOOGLE_FORM.md](docs/EDARAN_GOOGLE_FORM.md).

---

## Pengembangan Lanjutan

**Menambah moda angkutan**
1. Perbarui data jaringan di `dataset/`
2. Sesuaikan perhitungan tarif di `src/algorithms/routing/data_structures.py`
3. Tambahkan pemetaan warna dan ikon di `frontend/src/app/components/icons.tsx`

**Menyesuaikan pencarian rute**
1. `src/algorithms/routing/dijkstra.py` — biaya per ruas
2. `src/core/service_model.py` — headway, kecepatan operasi, jendela jam sibuk
3. `src/core/gmaps_style_routing.py` — penyusunan alternatif dan preferensi

---

## Konteks Penelitian

Dikembangkan untuk penelitian **"Sistem Informasi Integrasi Tiga Moda
Transportasi Publik Kota Palembang (LRT Sumsel, Teman Bus, dan Angkutan
Feeder)"** — Warta Penelitian Perhubungan (P-ISSN 0852-1824).

Latar masalah: pangsa perjalanan angkutan umum Kota Palembang baru 4,9%.

Pemilihan algoritma bukan lagi bahan penelitian — Dijkstra dipakai sebagai
satu-satunya mesin pencarian karena hasilnya optimal dan terjamin. Fokus
penelitian ada pada pemodelan preferensi dan pemilihan moda.

Asumsi dan keterbatasan yang harus dinyatakan pada naskah dirangkum di
[docs/RENCANA_SISTEM.md](docs/RENCANA_SISTEM.md) bagian 8, dan disampaikan
kepada pengguna melalui halaman `/about`.

---

## Catatan Teknis

- Koordinat dalam derajat desimal (WGS 84)
- Waktu dalam format ISO 8601, zona waktu WIB (GMT+7)
- Biaya dalam Rupiah
- Ubin peta dari OpenStreetMap
- Jam sibuk: 07.00–09.00, 12.00–14.00, 16.00–19.00 WIB
