# Palembang Public Transport Network

## 📋 Deskripsi Proyek

Proyek ini membuat visualisasi jaringan transportasi umum Palembang yang komprehensif, mencakup:

- **Angkot Feeder** (8 Koridor)
- **Teman Bus** (2 Koridor)
- **LRT Sumsel** (1 Jalur)

## 🎯 Hasil Akhir

### File-file yang Dihasilkan

1. **`network_data_complete.json`** (124 KB)

   - Data jaringan lengkap dalam format JSON
   - Berisi nodes (halte), edges (koneksi), dan informasi rute
   - Total: 402 halte, 391 koneksi, 11 rute

2. **`all_stops_matched.csv`** (34 KB)

   - Daftar lengkap semua halte yang telah dicocokkan
   - Kolom: stop_id, stop_name, lat, lon, route

3. **`public_transport_network_complete.html`** (169 KB)
   - Visualisasi interaktif menggunakan Leaflet.js
   - Fitur: filter rute, info halte, legenda warna
   - Dapat dibuka langsung di browser

## 📊 Statistik Jaringan

| Jenis Transportasi | Jumlah Koridor | Total Halte |
| ------------------ | -------------- | ----------- |
| Angkot Feeder      | 8              | 232         |
| Teman Bus          | 2              | 157         |
| LRT Sumsel         | 1              | 13          |
| **TOTAL**          | **11**         | **402**     |

### Detail per Koridor

#### Angkot Feeder

- **Koridor 1**: Talang Kelapa - Talang Buruk (45 halte)
- **Koridor 2**: Asrama Haji - Sematang Borang (71 halte)
- **Koridor 3**: Asrama Haji - Talang Betutu (13 halte)
- **Koridor 4**: Polresta - Perum OPI (9 halte)
- **Koridor 5**: DJKA - Terminal Plaju (21 halte)
- **Koridor 6**: RSUD - Sukawinatan (12 halte)
- **Koridor 7**: Kamboja - Bukit Siguntang (25 halte)
- **Koridor 8**: Asrama Haji - Talang Jambe (36 halte)

#### Teman Bus

- **Koridor 2**: Terminal Sako - Circular Route (60 halte)
- **Koridor 5**: Route 5 (97 halte)

#### LRT Sumsel

- **Jalur Utama**: 13 stasiun
  - Bandara SMB 2
  - Asrama Haji
  - Punti Kayu
  - RSUD Prov Sumsel
  - Garuda Dempo
  - Demang
  - Bumi Sriwijaya
  - Dishub
  - Pasar Cinde
  - Pasar 16 Ilir
  - Polresta
  - Jakabaring
  - DJKA

## 🔧 Proses Pembuatan

### Step 1: Ekstraksi Data KMZ

- Mengekstrak semua file KMZ dari folder `dataset/kmz_file/`
- Mendukung ekstraksi Point (marker halte) dan LineString (jalur rute)
- Total: 8 KMZ Feeder + 2 KMZ Teman Bus + 1 KMZ LRT

### Step 2: Matching dengan CSV

- Mencocokkan koordinat dari CSV dengan data KMZ
- Untuk halte tanpa nama: mencari titik terdekat di KMZ (radius 500m)
- Untuk Koridor 3 & 4 yang tidak ada nama: generate nama otomatis dari posisi

### Step 3: Pembuatan Network

- Membuat struktur graph dengan nodes (halte) dan edges (koneksi)
- Menghitung jarak antar halte menggunakan Haversine formula
- Mengelompokkan halte berdasarkan koridor/rute

### Step 4: Visualisasi

- Membuat peta interaktif dengan Leaflet.js
- Setiap rute memiliki warna unik
- Fitur klik untuk filter rute tertentu
- Popup informasi detail setiap halte

## 📁 Struktur File

```
DFS_final/
├── dataset/
│   ├── network_data_complete.json      # Data jaringan lengkap
│   ├── all_stops_matched.csv           # Daftar halte tercocokkan
│   ├── public_transport_network_complete.html  # Visualisasi interaktif
│   ├── Angkot Feeder/                  # CSV data feeder
│   ├── Bis Teman Bus/                  # CSV data teman bus
│   ├── lrt/                            # CSV data LRT
│   └── kmz_file/                       # File KMZ sumber
├── extract_kmz_improved.py             # Script ekstraksi & matching
├── create_visualization.py             # Script pembuatan visualisasi
└── README_NETWORK.md                   # Dokumentasi ini
```

## 🚀 Cara Menggunakan

### Melihat Visualisasi

1. Buka file `dataset/public_transport_network_complete.html` di browser
2. Klik pada item koridor di sidebar untuk melihat rute tertentu
3. Klik marker halte untuk melihat informasi detail
4. Gunakan tombol "Semua Rute" untuk menampilkan semua rute
5. Gunakan tombol "Reset View" untuk kembali ke tampilan awal

### Mengakses Data Terstruktur

#### JSON (untuk aplikasi)

```python
import json

with open('dataset/network_data_complete.json', 'r') as f:
    network = json.load(f)

print(f"Total halte: {len(network['nodes'])}")
print(f"Total rute: {len(network['routes'])}")
```

#### CSV (untuk analisis)

```python
import pandas as pd

stops = pd.read_csv('dataset/all_stops_matched.csv')
print(stops.head())
print(stops['route'].value_counts())
```

## 🎨 Warna Rute

| Rute                | Warna           | Hex Code |
| ------------------- | --------------- | -------- |
| Feeder Koridor 1    | 🔴 Merah        | #FF6B6B  |
| Feeder Koridor 2    | 🔵 Tosca        | #4ECDC4  |
| Feeder Koridor 3    | 💙 Biru Muda    | #45B7D1  |
| Feeder Koridor 4    | 💚 Hijau Muda   | #96CEB4  |
| Feeder Koridor 5    | 💛 Kuning Muda  | #FFEAA7  |
| Feeder Koridor 6    | ⚪ Abu-abu Muda | #DFE6E9  |
| Feeder Koridor 7    | 🔵 Biru Langit  | #74B9FF  |
| Feeder Koridor 8    | 💜 Ungu         | #A29BFE  |
| Teman Bus Koridor 2 | 💗 Pink         | #FD79A8  |
| Teman Bus Koridor 5 | 🧡 Oranye       | #FDCB6E  |
| LRT Sumsel          | 🟢 Hijau        | #00B894  |

## 📈 Fitur Visualisasi

### Fitur Utama

- ✅ Peta interaktif dengan zoom dan pan
- ✅ Filter rute per koridor
- ✅ Info popup detail setiap halte
- ✅ Legenda warna rute
- ✅ Statistik jaringan (total halte, rute, koneksi)
- ✅ Design responsif dan modern

### Teknologi

- **Leaflet.js** - Library peta interaktif
- **OpenStreetMap** - Tile map provider
- **Vanilla JavaScript** - No framework dependencies
- **CSS3** - Modern styling with gradients and shadows

## 🔄 Script Pembuatan

### 1. `extract_kmz_improved.py`

Script untuk ekstraksi KMZ dan matching dengan CSV:

```bash
python3 extract_kmz_improved.py
```

Fungsi utama:

- `extract_kmz_enhanced()` - Ekstrak Point dan LineString dari KMZ
- `match_csv_with_kmz()` - Cocokkan CSV dengan KMZ
- `find_nearest_stop()` - Cari halte terdekat (Haversine)
- `build_network_data()` - Buat struktur network

### 2. `create_visualization.py`

Script untuk membuat visualisasi HTML:

```bash
python3 create_visualization.py
```

Output: `public_transport_network_complete.html`

## 📝 Catatan Teknis

### Matching Algorithm

- Menggunakan Haversine distance untuk menghitung jarak geodesik
- Threshold matching: 500 meter
- Prioritas: KMZ Point > KMZ LineString > Generated Name

### Koordinat System

- Format: WGS84 (lat, lon)
- Latitude: -2.8 to -3.1 (Palembang area)
- Longitude: 104.6 to 104.8 (Palembang area)

### Data Completeness

| Aspek         | Status            |
| ------------- | ----------------- |
| KMZ Files     | ✅ 11/11 (100%)   |
| CSV Files     | ✅ 11/11 (100%)   |
| Matched Stops | ✅ 402/402 (100%) |
| Network Edges | ✅ 391 koneksi    |

## 🎯 Kegunaan Data

### Untuk Developer

- Integrasi dengan aplikasi mobile/web
- Routing algorithm development
- Real-time tracking integration

### Untuk Analyst

- Analisis coverage area
- Optimasi rute
- Perencanaan transportasi

### Untuk Public

- Informasi rute dan halte
- Perencanaan perjalanan
- Akses transportasi umum

## 🔮 Potensi Pengembangan

1. **Real-time Tracking**

   - Integrasi GPS kendaraan
   - Live location update

2. **Route Planning**

   - Algoritma pencarian rute terbaik
   - Multi-modal transport planning

3. **Analytics Dashboard**

   - Passenger flow analysis
   - Peak hour identification
   - Service optimization

4. **Mobile App**

   - Native Android/iOS app
   - Push notifications
   - User reviews & ratings

5. **Integration**
   - Google Maps integration
   - Payment system
   - Ticketing system

## 📞 Informasi

- **Lokasi**: Palembang, Sumatera Selatan
- **Cakupan**: 3 sistem transportasi umum
- **Data Update**: Oktober 2025
- **Format**: JSON, CSV, HTML

---

**Catatan**: Data ini dibuat berdasarkan file KMZ dan CSV yang tersedia. Untuk informasi real-time dan perubahan rute terbaru, mohon konfirmasi dengan operator transportasi terkait.
