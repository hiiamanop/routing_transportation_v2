# Analisis Sensitivitas Model MNL

## Perbandingan kecocokan model

| Model | N | Parameter | LL | rho² | AIC | BIC |
|---|---:|---:|---:|---:|---:|---:|
| Penuh + ASC | 248 | 7 | -160.772 | 0.2033 | 335.54 | 360.14 |
| Tanpa akses | 248 | 6 | -161.730 | 0.1985 | 335.46 | 356.54 |
| Tanpa transfer | 248 | 6 | -160.892 | 0.2027 | 333.78 | 354.86 |
| Tanpa kenyamanan | 248 | 6 | -161.092 | 0.2017 | 334.18 | 355.26 |
| Tanpa akses & transfer | 248 | 5 | -161.730 | 0.1985 | 333.46 | 351.03 |

## Likelihood-ratio test terhadap model penuh

| Model tereduksi | LR | df | p-value |
|---|---:|---:|---:|
| Tanpa akses | 1.915 | 1 | 0.1664 |
| Tanpa transfer | 0.239 | 1 | 0.6247 |
| Tanpa kenyamanan | 0.639 | 1 | 0.4241 |
| Tanpa akses & transfer | 1.915 | 2 | 0.3838 |

## Koefisien dan clustered t-stat

### Penuh + ASC

| Fitur | Beta | t cluster | Signifikan 5% |
|---|---:|---:|---|
| time_minutes | -0.0323753 | -3.10 | Ya |
| cost_rupiah | 9.89737e-06 | 0.13 | Tidak |
| transfers | 0.222538 | 0.53 | Tidak |
| access_km | 0.277189 | 1.46 | Tidak |
| comfort | -0.371371 | -0.85 | Tidak |
| reliability | 1.18051 | 2.23 | Ya |
| asc_private_vehicle | -1.25968 | -2.62 | Ya |

### Tanpa akses

| Fitur | Beta | t cluster | Signifikan 5% |
|---|---:|---:|---|
| time_minutes | -0.0230789 | -2.73 | Ya |
| cost_rupiah | 3.86693e-06 | 0.05 | Tidak |
| transfers | -0.000915175 | -0.00 | Tidak |
| comfort | -0.249415 | -0.55 | Tidak |
| reliability | 1.09568 | 2.02 | Ya |
| asc_private_vehicle | -1.47763 | -3.11 | Ya |

### Tanpa transfer

| Fitur | Beta | t cluster | Signifikan 5% |
|---|---:|---:|---|
| time_minutes | -0.0281181 | -3.74 | Ya |
| cost_rupiah | 2.07186e-05 | 0.28 | Tidak |
| access_km | 0.240357 | 1.34 | Tidak |
| comfort | -0.484057 | -1.30 | Tidak |
| reliability | 1.21223 | 2.32 | Ya |
| asc_private_vehicle | -1.14248 | -2.69 | Ya |

### Tanpa kenyamanan

| Fitur | Beta | t cluster | Signifikan 5% |
|---|---:|---:|---|
| time_minutes | -0.0327343 | -3.12 | Ya |
| cost_rupiah | 4.64473e-06 | 0.06 | Tidak |
| transfers | 0.399572 | 1.11 | Tidak |
| access_km | 0.248726 | 1.30 | Tidak |
| reliability | 0.920472 | 2.03 | Ya |
| asc_private_vehicle | -1.58302 | -4.67 | Ya |

### Tanpa akses & transfer

| Fitur | Beta | t cluster | Signifikan 5% |
|---|---:|---:|---|
| time_minutes | -0.0230929 | -3.56 | Ya |
| cost_rupiah | 3.80805e-06 | 0.05 | Tidak |
| comfort | -0.248782 | -0.71 | Tidak |
| reliability | 1.09548 | 2.04 | Ya |
| asc_private_vehicle | -1.47834 | -4.00 | Ya |

## Stabilitas tanda

| Fitur | Tanda sama di semua model | Rentang beta |
|---|---|---:|
| time_minutes | Ya | -0.0327343 s.d. -0.0230789 |
| cost_rupiah | Ya | 3.80805e-06 s.d. 2.07186e-05 |
| comfort | Ya | -0.484057 s.d. -0.248782 |
| reliability | Ya | 0.920472 s.d. 1.21223 |
| asc_private_vehicle | Ya | -1.58302 s.d. -1.14248 |

## Uji tanpa penggabungan alternatif identik

Observasi valid: **313**; LL -228.413; rho² 0.3033.

| Fitur | Beta | t |
|---|---:|---:|
| time_minutes | -0.0142878 | -1.35 |
| cost_rupiah | 4.85008e-05 | 0.59 |
| transfers | -0.939784 | -2.39 |
| access_km | 0.612365 | 3.04 |
| comfort | -2.47177 | -7.17 |
| reliability | 3.17988 | 5.82 |
| asc_private_vehicle | 1.46891 | 7.09 |
