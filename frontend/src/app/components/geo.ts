// Pergeseran garis ke sisi jalan sesuai arah perjalanan.
//
// Satu koridor melayani rute A->B lalu B->A lewat titik halte yang SAMA.
// Kalau dua arah itu digambar tepat di atas garis yang sama, keduanya
// bertumpuk jadi satu dan arah perjalanan tidak terbaca. Jadi tiap arah
// digeser sedikit ke sisi kiri arah jalannya -- karena arah pulang adalah
// garis yang sama dibalik, "kiri arah jalan" otomatis jatuh di sisi
// seberang, persis seperti dua lajur berlawanan di jalan sungguhan.
//
// Indonesia berkendara di lajur KIRI, jadi kendaraan berada di sisi kiri
// relatif arah majunya.

export const LANE_OFFSET_M = 9;

/**
 * Geser polyline tegak lurus sejauh `meters` ke sisi kiri arah jalan.
 * Titik pertama & terakhir ikut digeser supaya garis tetap sejajar utuh.
 */
export function offsetPolyline(
  points: Array<[number, number]>,
  meters: number = LANE_OFFSET_M
): Array<[number, number]> {
  if (points.length < 2 || meters === 0) return points;

  const M_PER_DEG_LAT = 111320;
  const mPerDegLon =
    M_PER_DEG_LAT * Math.cos((points[0][0] * Math.PI) / 180) || M_PER_DEG_LAT;

  return points.map((p, i) => {
    // arah lokal diambil dari tetangga depan-belakang supaya di tikungan
    // pergeserannya mengikuti lengkungan, bukan mematah
    const a = points[Math.max(0, i - 1)];
    const b = points[Math.min(points.length - 1, i + 1)];
    const dx = (b[1] - a[1]) * mPerDegLon; // ke timur
    const dy = (b[0] - a[0]) * M_PER_DEG_LAT; // ke utara
    const len = Math.hypot(dx, dy);
    if (len === 0) return p;

    // putar arah maju 90 derajat berlawanan jarum jam = sisi kiri
    const nx = -dy / len;
    const ny = dx / len;
    return [
      p[0] + (ny * meters) / M_PER_DEG_LAT,
      p[1] + (nx * meters) / mPerDegLon,
    ] as [number, number];
  });
}
