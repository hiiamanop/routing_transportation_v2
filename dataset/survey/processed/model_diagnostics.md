# Diagnostik Model Pemilihan Moda

## Sampel

- Observasi valid: **318**
- Responden unik: **318**
- Responden dengan observasi berulang: **0**
- Observasi dengan preferensi: **294**

## Pilihan menurut kelompok

| Kelompok | Pilihan |
|---|---:|
| transit | 176 |
| private_vehicle | 136 |
| ride_hailing | 6 |

## Variasi atribut di dalam choice set

| Atribut | Observasi bervariasi | Persentase |
|---|---:|---:|
| time_minutes | 318 | 100.0% |
| cost_rupiah | 312 | 98.1% |
| transfers | 131 | 41.2% |
| access_km | 304 | 95.6% |
| comfort | 312 | 98.1% |
| reliability | 318 | 100.0% |

## Perbandingan model

| Model | LL | McFadden rho² | AIC | BIC |
|---|---:|---:|---:|---:|
| Dasar | -255.166 | 0.0397 | 522.33 | 544.91 |
| ASC kendaraan pribadi | -252.049 | 0.0514 | 518.10 | 544.43 |

## Koefisien model ASC kendaraan pribadi

| Fitur | Beta | SE naïf | SE cluster | t cluster | Signifikan 5% |
|---|---:|---:|---:|---:|---|
| time_minutes | -0.00238604 | 0.00861281 | 0.00805404 | -0.30 | Tidak |
| cost_rupiah | -2.11488e-05 | 1.78531e-05 | 1.57343e-05 | -1.34 | Tidak |
| transfers | 0.231171 | 0.26296 | 0.220882 | 1.05 | Tidak |
| access_km | 0.501608 | 0.214241 | 0.207674 | 2.42 | Ya |
| comfort | 0.255047 | 0.174297 | 0.158628 | 1.61 | Tidak |
| reliability | 0.353102 | 0.166415 | 0.168726 | 2.09 | Ya |
| asc_private_vehicle | 0.610006 | 0.246991 | 0.241209 | 2.53 | Ya |

> ASC memakai angkutan umum sebagai kategori acuan; ride-hailing tidak diklasifikasikan sebagai kendaraan pribadi.
