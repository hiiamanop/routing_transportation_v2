# Diagnostik Model Pemilihan Moda

## Sampel

- Observasi valid: **248**
- Responden unik: **248**
- Responden dengan observasi berulang: **0**
- Observasi dengan preferensi: **225**

## Pilihan menurut kelompok

| Kelompok | Pilihan |
|---|---:|
| transit | 178 |
| private_vehicle | 70 |

## Variasi atribut di dalam choice set

| Atribut | Observasi bervariasi | Persentase |
|---|---:|---:|
| time_minutes | 248 | 100.0% |
| cost_rupiah | 248 | 100.0% |
| transfers | 110 | 44.4% |
| access_km | 225 | 90.7% |
| comfort | 245 | 98.8% |
| reliability | 245 | 98.8% |

## Perbandingan model

| Model | LL | McFadden rho² | AIC | BIC |
|---|---:|---:|---:|---:|
| Dasar | -163.875 | 0.1879 | 339.75 | 360.83 |
| ASC kendaraan pribadi | -160.772 | 0.2033 | 335.54 | 360.14 |

## Koefisien model ASC kendaraan pribadi

| Fitur | Beta | SE naïf | SE cluster | t cluster | Signifikan 5% |
|---|---:|---:|---:|---:|---|
| time_minutes | -0.0323753 | 0.0120529 | 0.0104341 | -3.10 | Ya |
| cost_rupiah | 9.89737e-06 | 8.11166e-05 | 7.47524e-05 | 0.13 | Tidak |
| transfers | 0.222538 | 0.457394 | 0.419702 | 0.53 | Tidak |
| access_km | 0.277189 | 0.204569 | 0.189772 | 1.46 | Tidak |
| comfort | -0.371371 | 0.466123 | 0.438593 | -0.85 | Tidak |
| reliability | 1.18051 | 0.615339 | 0.529137 | 2.23 | Ya |
| asc_private_vehicle | -1.25968 | 0.520092 | 0.48012 | -2.62 | Ya |

> ASC memakai angkutan umum sebagai kategori acuan.
