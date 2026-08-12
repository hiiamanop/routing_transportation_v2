# Desain: Mode Tagging GPS untuk Koreksi Titik Halte per Koridor

**Status**: disetujui, siap masuk fase perencanaan implementasi.

## Latar belakang

Data 402 halte di `dataset/network_data_complete.json` (field `nodes`) hasil ekstraksi KMZ/CSV awal, sebagian koordinatnya meleset dari posisi halte sebenarnya di lapangan. Pemilik proyek ingin memperbaikinya dengan cara turun langsung: naik tiap transum, dan menandai (tag) posisi GPS aktual setiap kali kendaraan berhenti di halte.

Fitur ini ditambahkan ke tab **Jaringan** yang sudah ada di `frontend/src/app/jaringan/page.tsx` (saat ini read-only), bukan halaman terpisah.

## Keputusan yang sudah dikonfirmasi user

| Pertanyaan | Keputusan |
|---|---|
| Arti "tagging" | Reposisi koordinat lat/lon, bukan label kategori |
| Akses | Publik, tanpa login/password |
| Lokasi menu | Diperluas dari tab Jaringan yang sudah ada |
| Mekanisme | Sesi GPS live: pilih koridor → keliling naik transum → tekan "Tag" tiap berhenti di halte |
| Hasil akhir | Menimpa (replace) seluruh data halte koridor itu setelah sesi selesai & direview, bukan mencocokkan satu-satu ke halte lama |
| Cakupan | Reposisi + tambah/hapus halte + ubah urutan (bukan cuma reposisi) |
| Ambang akurasi GPS 2,5m | Peringatan saja, tidak memblokir tombol Tag |
| Penamaan halte | Auto-numbering ("Halte 1, 2, ...") saat tag, nama asli diisi di layar review |

## Alur pengguna

1. Di tab Jaringan, pilih koridor dari dropdown yang sudah ada → tombol baru **"Mulai Sesi Tagging"**.
2. Browser minta izin lokasi (`navigator.geolocation.watchPosition`, `enableHighAccuracy: true`). Peta menampilkan marker posisi live + lingkaran radius akurasi saat ini.
3. Pengguna naik transum, keliling koridor. Tiap berhenti di halte, tekan tombol **Tag**:
   - Simpan `{name: "Halte N", lat, lon, accuracy, taggedAt}` ke daftar sesi.
   - Kalau `accuracy > 2.5` meter saat ditekan, titik tetap masuk daftar tapi diberi ikon/warna peringatan.
   - Titik baru langsung muncul sebagai pin di peta dan baris baru di daftar sesi (panel bawah/samping).
4. Sepanjang sesi berjalan, daftar tag disimpan otomatis ke `localStorage` (key per koridor, mis. `tagging_session_<route>`) — supaya kalau tab browser ter-refresh atau HP terkunci di tengah perjalanan, progres tidak hilang. Saat halaman dibuka lagi dengan sesi tagging koridor yang sama masih tersimpan, tawarkan lanjutkan atau mulai ulang.
5. Pengguna bisa, selama sesi berjalan atau di layar review:
   - Hapus titik yang salah tekan.
   - Reorder titik (drag di daftar).
   - Tambah titik manual dengan klik langsung di peta (untuk halte yang kelewat saat naik kendaraan).
   - Ganti nama tiap titik dari "Halte N" ke nama asli.
6. Tombol **"Selesai Keliling"** → masuk layar **Review**: peta menampilkan garis koridor baru (hasil sambung titik-titik tertag berurutan) berdampingan/overlay dengan data lama untuk perbandingan visual, plus tabel semua titik (editable seperti poin 5).
7. Tombol **"Simpan ke Server"** → kirim daftar final `[{name, lat, lon}, ...]` terurut ke backend. Setelah sukses, `localStorage` sesi koridor itu dibersihkan, dan peta di tab Jaringan otomatis refresh menampilkan data baru.

## Backend

### Endpoint baru

`PUT /api/network/corridor/<route_name>/stops`

Body: `{"stops": [{"name": str, "lat": float, "lon": float}, ...]}` (terurut sesuai urutan fisik di koridor).

**Koreksi penting ditemukan saat penyusunan rencana implementasi**: API (`load_network()` di `api/app.py`) ternyata memuat graf routing dari `dataset/network_data_correct_bidirectional.json`, BUKAN `network_data_complete.json`. File itu adalah turunan: `scripts/create_correct_bidirectional.py` membaca `network_data_complete.json`, menambah edge balik hanya untuk 2 koridor linear (`Feeder Koridor 5`, `LRT Sumsel` — daftar `linear_routes` di baris ~30 skrip itu), lalu menyimpan hasilnya sebagai file terpisah. File turunan itu juga punya 2 key tambahan (`route_waypoints`, `route_stop_anchors`) yang TIDAK ada di `network_data_complete.json` — dipakai endpoint `GET /api/route/waypoints/<route>` untuk polyline jalan di peta. Konsekuensinya: endpoint tagging harus memperbarui **kedua file**, dan tidak boleh regenerasi penuh `network_data_correct_bidirectional.json` dari nol (itu akan menghapus `route_waypoints`/`route_stop_anchors`) — cukup ganti isi `nodes`/`edges` koridor terkait di kedua file, key lain dibiarkan apa adanya.

Perilaku:
1. Validasi: `route_name` harus cocok salah satu nilai `route` yang sudah ada di `nodes`/`routes`; minimal 2 titik; tiap titik punya lat/lon valid (rentang koordinat masuk akal untuk area Palembang, cek longgar).
2. **Backup dulu**: salin `dataset/network_data_complete.json` DAN `dataset/network_data_correct_bidirectional.json` masing-masing ke `<nama>.backup-<YYYYMMDDHHMMSS>.json` sebelum menulis apa pun (jaring pengaman murah karena tidak ada auth/login di fitur ini).
3. Untuk `network_data_complete.json`: hapus semua entri `nodes` yang `route == route_name` dan semua entri `edges` yang `from`/`to` merujuk ke node yang dihapus. Buat node baru (`id` lanjut dari `max(existing id) + 1` di seluruh file, `stop_id` pola `<route_slug>_<index>` meniru pola lama mis. `Feeder_Koridor_1_1`, `name`, `lat`, `lon`, `route`). Buat edge baru berurutan (`stop[i] -> stop[i+1]`), `distance` haversine — meniru `build_network_data()` di `scripts/extract_kmz_improved.py`, satu arah saja.
4. Untuk `network_data_correct_bidirectional.json`: lakukan penggantian `nodes`/`edges` koridor yang SAMA PERSIS seperti langkah 3 (id node sama, supaya kedua file tetap konsisten), lalu — HANYA kalau `route_name` termasuk `linear_routes = {"Feeder Koridor 5", "LRT Sumsel"}` — tambahkan juga edge balik (`is_reverse: True`) meniru logika `create_correct_bidirectional_network()`. Key `route_waypoints`/`route_stop_anchors` tidak disentuh sama sekali.
5. Tulis kedua file yang sudah diperbarui.
6. **Reload graf routing in-memory** (panggil ulang `load_network_data("dataset/network_data_correct_bidirectional.json")` dan timpa `network_graph` global di `api/app.py`) supaya endpoint pencarian rute langsung pakai data baru tanpa perlu restart container.
7. Response: jumlah node lama vs baru, dan path kedua file backup yang dibuat (untuk transparansi/manual rollback kalau perlu).

### Yang sengaja tidak disentuh

- `dataset/all_stops.csv` / `all_stops_matched.csv` tidak diupdate otomatis (tidak dipakai runtime routing) — dicatat sebagai known gap, bisa disinkronkan manual belakangan kalau perlu.
- Tidak menambah auth/login (sesuai keputusan eksplisit user).
- Tidak mengubah logika arah edge dua-arah (`is_reverse`) yang sudah ada terpisah untuk 2 koridor — koridor yang ditag ulang tetap ikut pola satu-arah yang berlaku sekarang untuk semua koridor lain.
- Tidak regenerasi polyline jalan (OSRM/KMZ) — itu proses terpisah untuk garis visual jalan, di luar scope perbaikan titik halte.

## Penanganan error

- Geolocation ditolak/tidak tersedia di browser: tampilkan pesan jelas, tombol "Mulai Sesi Tagging" nonaktif sampai izin diberikan.
- Request `PUT` gagal (network/500): daftar tag TIDAK dihapus dari `localStorage` sampai server konfirmasi sukses — pengguna bisa coba simpan lagi tanpa kehilangan data hasil keliling.
- Nama koridor tidak valid/tidak dikenal backend: response 400 dengan pesan jelas.

## Testing / verifikasi

- Backend: skrip kecil (`scripts/` atau test manual) yang memanggil endpoint dengan data dummy untuk 1 koridor kecil, verifikasi `nodes`/`edges` ter-update benar, file backup dibuat, dan graf routing bisa dipakai cari rute lagi tanpa restart.
- Frontend: uji manual di browser mobile (Chrome Android) dengan GPS aktif — alur lengkap mulai sesi → tag beberapa titik → refresh browser di tengah sesi (pastikan localStorage recovery jalan) → selesai → review → simpan → verifikasi peta tab Jaringan menampilkan data baru.
