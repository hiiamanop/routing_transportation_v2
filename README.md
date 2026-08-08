# Palembang Public Transport Routing System

Sistem informasi integrasi tiga moda angkutan umum Kota Palembang (LRT Sumsel, Teman Bus, Angkutan Feeder): pencarian rute antar moda, alternatif perjalanan, dan pemodelan preferensi pengguna.

Rencana pembangunan sistem selengkapnya: [docs/RENCANA_SISTEM.md](docs/RENCANA_SISTEM.md).

**Repository**: https://github.com/hiiamanop/routing_transportation_v2.git

## 🚀 Features

- **Multi-modal Routing**: Mendukung Angkot Feeder, Teman Bus, dan LRT
- **Alternatif Rute**: Tercepat, termurah, transfer paling sedikit, dan lewat rute lain
- **Preferensi Pengguna**: Rekomendasi personal dari penilaian 5 kriteria
- **Survei Pemilihan Moda**: Perekaman pilihan responden untuk estimasi model
- **Interactive Map**: Visualisasi rute dengan Leaflet.js

## 📁 Project Structure

```
routing_transportation_v2/
├── api/                    # Flask API Backend (entrypoint: app.py)
│   ├── app.py             # Main API server
│   └── requirements.txt   # Python dependencies
├── frontend/              # Next.js Frontend
│   ├── src/
│   │   └── app/
│   │       ├── page.tsx   # Main application
│   │       └── components/
│   │           └── MapComponent.tsx
│   └── package.json
├── src/                   # Core routing algorithms
│   ├── core/              # Dijkstra + gmaps-style output formatting
│   └── algorithms/
│       └── routing/       # Struktur data, pemuat jaringan, Dijkstra
├── experiments/           # Skrip verifikasi ground truth dari data survei
├── scripts/               # One-off data processing scripts (KMZ extraction, etc.)
├── dataset/               # Network data
└── docs/                  # Rencana sistem + naskah penelitian
```

## 🚀 Quick Deployment

Untuk deployment ke server, lihat [DEPLOYMENT.md](DEPLOYMENT.md) untuk panduan lengkap.

**Deployment via Git (Recommended):**

```bash
chmod +x deploy_git.sh
./deploy_git.sh
```

## 🛠️ Local Development Setup

### 1. Backend API Setup

```bash
# Install Python dependencies
cd api
pip install -r requirements.txt

# Run the API server
python app.py
```

API akan berjalan di `http://localhost:5000`

### 2. Frontend Setup

```bash
# Install dependencies
cd frontend
npm install

# Run the development server
npm run dev
```

Frontend akan berjalan di `http://localhost:3000`

## 📡 API Endpoints

### Health Check

```
GET /api/health
```

### Network Information

```
GET /api/network/info
```

### Route Planning

```
POST /api/route
Content-Type: application/json

{
  "origin": {
    "name": "Universitas Sriwijaya",
    "lat": -2.985256,
    "lon": 104.732880
  },
  "destination": {
    "name": "PTC Mall",
    "lat": -2.95115,
    "lon": 104.76090
  },
  "algorithm": "both",
  "departure_time": "2025-01-01T10:00:00"
}
```

### Get All Stops

```
GET /api/stops
```

## 🗺️ Map Visualization

- **Origin Marker**: 🟢 Green marker untuk titik asal
- **Destination Marker**: 🔴 Red marker untuk tujuan
- **Route Lines**: Garis berwarna sesuai mode transportasi
  - 🟢 Green: Walking
  - 🔵 Blue: Teman Bus
  - 🟠 Orange: Feeder Angkot
  - 🟣 Purple: LRT
- **Stop Markers**: Marker kecil untuk semua halte

## 🔧 Pencarian Rute

Memakai **Dijkstra** sebagai satu-satunya mesin pencarian rute — hasilnya optimal
dan terjamin. Pemilihan algoritma bukan lagi bahan penelitian; fokusnya ada pada
pemodelan preferensi dan pemilihan moda (lihat
[docs/RENCANA_SISTEM.md](docs/RENCANA_SISTEM.md)).

## 💰 Fare System

- **Angkot Feeder**: FREE (Rp 0)
- **Teman Bus**: Rp 5,000 per trip
- **LRT**:
  - Rp 5,000 (inter-station)
  - Rp 10,000 (end-to-end)
- **No additional cost** for same mode/corridor transfers

## 🎯 Usage Example

1. **Open Frontend**: Navigate to `http://localhost:3000`
2. **Enter Origin**: Input name and coordinates
3. **Enter Destination**: Input name and coordinates
4. **Find Route**: Klik tombol cari rute
5. **View Results**:
   - Ringkasan rute di panel samping
   - Visualisasi peta interaktif
   - Tab alternatif: tercepat, termurah, transfer paling sedikit

## 🔍 Research Context

Sistem ini dikembangkan untuk penelitian:
**"Sistem Informasi Integrasi Tiga Moda Transportasi Publik Kota Palembang (LRT Sumsel, Teman Bus, dan Angkutan Feeder)"** — Warta Penelitian Perhubungan (P-ISSN 0852-1824).

Latar masalah: mode share angkutan umum Palembang hanya 4,9%.

## 📊 Network Data

- **Total Stops**: 402 halte
- **Total Edges**: 423 koneksi
- **Transport Modes**:
  - 8 Feeder Angkot routes
  - 2 Teman Bus routes
  - 1 LRT route
- **Smart Bidirectional**: Circuit routes one-way, Linear routes bidirectional

## 🚀 Quick Start

```bash
# Terminal 1 - Start API
cd api && python app.py

# Terminal 2 - Start Frontend
cd frontend && npm run dev

# Open browser
open http://localhost:3000
```

## 🎨 Features

- ✅ Real-time route planning
- ✅ Interactive map visualization
- ✅ Algorithm performance comparison
- ✅ Multi-modal transport support
- ✅ Responsive design
- ✅ Google Maps style output
- ✅ Current location detection
- ✅ Route optimization
- ✅ Cost calculation
- ✅ Time estimation

## 🔧 Development

### Adding New Transport Modes

1. Update network data in `dataset/`
2. Modify fare calculation in `api/app.py`
3. Add color mapping in `frontend/src/app/components/MapComponent.tsx`

### Menyesuaikan Pencarian Rute

1. Ubah `src/algorithms/routing/dijkstra.py` untuk biaya per-ruas
2. Ubah `src/core/service_model.py` untuk parameter layanan (headway, kecepatan)
3. Ubah `src/core/gmaps_style_routing.py` untuk alternatif & preferensi

## 📝 Notes

- **Local Development**:
  - API runs on port 5000
  - Frontend runs on port 3000
- **Production Server**:
  - API runs on port 5001
  - Frontend runs on port 3000
  - Nginx reverse proxy on port 80
- Map uses OpenStreetMap tiles
- All coordinates in decimal degrees
- Time format: ISO 8601
- Cost in Indonesian Rupiah (IDR)
