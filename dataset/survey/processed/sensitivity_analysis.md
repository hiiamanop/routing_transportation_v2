# Analisis Sensitivitas Model MNL

## Perbandingan kecocokan model

| Model | N | Parameter | LL | rho² | AIC | BIC |
|---|---:|---:|---:|---:|---:|---:|
| Penuh + ASC | 318 | 7 | -252.049 | 0.0514 | 518.10 | 544.43 |
| Tanpa akses | 318 | 6 | -255.122 | 0.0399 | 522.24 | 544.82 |
| Tanpa transfer | 318 | 6 | -252.436 | 0.0500 | 516.87 | 539.44 |
| Tanpa akses & transfer | 318 | 5 | -255.143 | 0.0398 | 520.29 | 539.10 |
| Tanpa ride-hailing | 298 | 7 | -237.397 | 0.0404 | 488.79 | 514.67 |

## Likelihood-ratio test terhadap model penuh

| Model tereduksi | LR | df | p-value |
|---|---:|---:|---:|
| Tanpa akses | 6.148 | 1 | 0.0132 |
| Tanpa transfer | 0.774 | 1 | 0.3790 |
| Tanpa akses & transfer | 6.189 | 2 | 0.0453 |

## Koefisien dan clustered t-stat

### Penuh + ASC

| Fitur | Beta | t cluster | Signifikan 5% |
|---|---:|---:|---|
| time_minutes | -0.00238604 | -0.30 | Tidak |
| cost_rupiah | -2.11488e-05 | -1.34 | Tidak |
| transfers | 0.231171 | 1.05 | Tidak |
| access_km | 0.501608 | 2.42 | Ya |
| comfort | 0.255047 | 1.61 | Tidak |
| reliability | 0.353102 | 2.09 | Ya |
| asc_private_vehicle | 0.610006 | 2.53 | Ya |

### Tanpa akses

| Fitur | Beta | t cluster | Signifikan 5% |
|---|---:|---:|---|
| time_minutes | 0.0100289 | 1.52 | Tidak |
| cost_rupiah | -2.29724e-05 | -1.47 | Tidak |
| transfers | -0.0476705 | -0.24 | Tidak |
| comfort | 0.297084 | 1.84 | Tidak |
| reliability | 0.355514 | 2.15 | Ya |
| asc_private_vehicle | 0.417952 | 1.85 | Tidak |

### Tanpa transfer

| Fitur | Beta | t cluster | Signifikan 5% |
|---|---:|---:|---|
| time_minutes | 0.00291742 | 0.47 | Tidak |
| cost_rupiah | -1.78242e-05 | -1.15 | Tidak |
| access_km | 0.423059 | 2.33 | Ya |
| comfort | 0.229307 | 1.46 | Tidak |
| reliability | 0.352965 | 2.10 | Ya |
| asc_private_vehicle | 0.611525 | 2.55 | Ya |

### Tanpa akses & transfer

| Fitur | Beta | t cluster | Signifikan 5% |
|---|---:|---:|---|
| time_minutes | 0.00917034 | 1.65 | Tidak |
| cost_rupiah | -2.38925e-05 | -1.52 | Tidak |
| comfort | 0.3055 | 1.92 | Tidak |
| reliability | 0.355397 | 2.15 | Ya |
| asc_private_vehicle | 0.409518 | 1.83 | Tidak |

### Tanpa ride-hailing

| Fitur | Beta | t cluster | Signifikan 5% |
|---|---:|---:|---|
| time_minutes | -0.00392365 | -0.47 | Tidak |
| cost_rupiah | 1.2894e-05 | 0.45 | Tidak |
| transfers | 0.161507 | 0.70 | Tidak |
| access_km | 0.510815 | 2.41 | Ya |
| comfort | 0.272815 | 1.67 | Tidak |
| reliability | 0.30972 | 1.79 | Tidak |
| asc_private_vehicle | 0.475679 | 1.83 | Tidak |

## Stabilitas tanda

| Fitur | Tanda sama di semua model | Rentang beta |
|---|---|---:|
| time_minutes | Tidak | -0.00392365 s.d. 0.0100289 |
| cost_rupiah | Tidak | -2.38925e-05 s.d. 1.2894e-05 |
| comfort | Ya | 0.229307 s.d. 0.3055 |
| reliability | Ya | 0.30972 s.d. 0.355514 |
| asc_private_vehicle | Ya | 0.409518 s.d. 0.611525 |

> Model tanpa ride-hailing adalah uji sensitivitas sampel dan tidak tersarang pada model penuh; karena itu tidak diuji dengan likelihood-ratio test.
