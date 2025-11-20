# Palembang Public Transport Routing System

Sistem routing transportasi umum Palembang menggunakan algoritma Dijkstra dan Optimized DFS dengan visualisasi peta interaktif.

**Repository**: https://github.com/hiiamanop/routing_transportation_v2.git

## 🚀 Features

- **Multi-modal Routing**: Mendukung Angkot Feeder, Teman Bus, dan LRT
- **Dual Algorithms**: Dijkstra dan Optimized DFS untuk perbandingan
- **Interactive Map**: Visualisasi rute dengan Leaflet.js
- **Real-time Comparison**: Perbandingan performa algoritma
- **Google Maps Style Output**: Format output yang mudah dipahami

## 📁 Project Structure

```
DFS_final/
├── api/                    # Flask API Backend
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
├── dataset/               # Network data
└── optimized_dfs_test.py  # Optimized DFS implementation
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

## 🔧 Algorithms

### Dijkstra Algorithm

- **Type**: Shortest path algorithm
- **Use Case**: Optimal route finding
- **Performance**: Fast and reliable

### Optimized DFS Algorithm

- **Type**: Depth-First Search with heuristics
- **Features**:
  - A\* style heuristics
  - Iterative deepening
  - Best-first ordering
  - Cost-based pruning
- **Use Case**: Research comparison

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
4. **Select Algorithm**: Choose Dijkstra, DFS, or Both
5. **Find Route**: Click "Find Route" button
6. **View Results**:
   - Route summary in sidebar
   - Interactive map visualization
   - Algorithm comparison (if both selected)

## 🔍 Research Context

Sistem ini dikembangkan untuk penelitian:
**"PERANCANGAN SISTEM INFORMASI INTEGRASI OPERASIONAL ANTAR MODA ANGKUTAN UMUM MENGGUNAKAN ALGORITMA DEPTH FIRST SEARCH (DFS) DI KOTA PALEMBANG"**

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

### Customizing Algorithms

1. Modify `optimized_dfs_test.py` for DFS improvements
2. Update `src/core/gmaps_style_routing.py` for Dijkstra changes
3. Test with `src/interactive_routing.py`

## 📝 Notes

- API runs on port 5000
- Frontend runs on port 3000
- Map uses OpenStreetMap tiles
- All coordinates in decimal degrees
- Time format: ISO 8601
- Cost in Indonesian Rupiah (IDR)
