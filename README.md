# Palembang Public Transport Routing System

A comprehensive multi-modal public transport routing system for Palembang, Indonesia, supporting Angkot Feeder, Teman Bus, and LRT Sumsel.

## 🚌 Features

- **Multi-modal Routing**: Seamless integration of Angkot Feeder, Teman Bus, and LRT
- **Google Maps Style**: Door-to-door routing with walking segments
- **Smart Network**: Circuit routes (one-way) vs Linear routes (bidirectional)
- **Multiple Algorithms**: Dijkstra and IDA\* pathfinding algorithms
- **Real-time Optimization**: Time, cost, and transfer optimization modes
- **REST API**: JSON-based backend API for integration

## 📁 Project Structure

```
├── src/                          # Main source code
│   ├── core/                     # Core routing functionality
│   │   └── gmaps_style_routing.py
│   ├── algorithms/               # Advanced routing algorithms
│   │   └── ida_star_routing/     # IDA* implementation
│   ├── utils/                    # Utility functions
│   ├── app.py                    # Flask REST API
│   └── interactive_routing.py    # Interactive CLI
├── scripts/                      # Data processing scripts
│   ├── create_correct_bidirectional.py
│   ├── create_visualization.py
│   ├── extract_kmz_improved.py
│   └── smart_bidirectional_analyzer.py
├── dataset/                      # Network data and CSV files
│   ├── network_data_correct_bidirectional.json
│   ├── Angkot Feeder/
│   ├── Bis Teman Bus/
│   └── kmz_file/
└── docs/                         # Documentation
```

## 🚀 Quick Start

### Interactive Routing

```bash
python src/interactive_routing.py
```

### REST API

```bash
python src/app.py
```

### Test Route

```python
from src.core.gmaps_style_routing import gmaps_style_route
from src.algorithms.ida_star_routing.data_loader import load_network_data

# Load network
graph = load_network_data("dataset/network_data_correct_bidirectional.json")

# Find route
route = gmaps_style_route(
    graph=graph,
    origin_name="Universitas Sriwijaya",
    origin_coords=(-2.985256, 104.732880),
    dest_name="PTC Mall",
    dest_coords=(-2.95115, 104.76090),
    optimization_mode="time"
)
```

## 🛠️ Network Configuration

- **8 Angkot Feeder Routes**: Circuit routes (one-way)
- **2 Teman Bus Routes**: Circuit routes (one-way)
- **1 LRT Route**: Linear route (bidirectional)
- **402 Stops**: Complete coverage of Palembang
- **423 Edges**: Optimized connectivity

## 📊 Supported Routes

### Angkot Feeder (8 routes)

- Koridor 1: Talang Kelapa - Talang Buruk
- Koridor 2: Asrama Haji - Sematang Borang
- Koridor 3: Asrama Haji - Talang Betutu
- Koridor 4: Polresta - Perum OPI
- Koridor 5: DJKA - Terminal Plaju (Linear)
- Koridor 6: RSUD - Sukawinatan
- Koridor 7: Kamboja - Bukit Siguntang
- Koridor 8: Asrama Haji - Talang Jambe

### Teman Bus (2 routes)

- Koridor 2: Circuit route
- Koridor 5: Circuit route

### LRT Sumsel (1 route)

- Linear route (bidirectional)

## 🔧 API Endpoints

### POST /route

```json
{
  "origin_name": "Universitas Sriwijaya",
  "origin_lat": -2.985256,
  "origin_lon": 104.73288,
  "dest_name": "PTC Mall",
  "dest_lat": -2.95115,
  "dest_lon": 104.7609,
  "algorithm": "1",
  "optimization_mode": "time",
  "max_walking_km": 2.0
}
```

## 📈 Performance

- **Dijkstra**: Fast, reliable, optimal solutions
- **IDA\***: Memory-efficient, same results as Dijkstra
- **Average Response Time**: < 1 second
- **Network Coverage**: 100% of Palembang public transport

## 🎯 Optimization Modes

- **Time**: Minimize total journey time
- **Cost**: Minimize total cost
- **Transfers**: Minimize number of transfers
- **Balanced**: Balance time, cost, and transfers

## 📝 License

This project is part of the DFS (Data Structures and Algorithms) course work for Palembang public transport optimization.

## 🤝 Contributing

This is an academic project. For questions or improvements, please contact the development team.
