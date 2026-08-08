"use client";

import { useRouter } from "next/navigation";
import { NavigationIcon } from "../components/icons";

interface Section {
  title: string;
  body: React.ReactNode;
}

const SECTIONS: Section[] = [
  {
    title: "Pencarian rute",
    body: (
      <>
        <p>
          Rute dicari dengan algoritma <strong>Dijkstra</strong> di atas graf
          402 halte dan 11 koridor (8 Feeder Angkot, 2 Teman Bus, 1 LRT).
          Setiap ruas (dua halte bersebelahan di satu koridor) punya bobot
          waktu tempuh + waktu tunggu, dan pencarian menemukan jalur dengan
          total bobot terkecil, termasuk kemungkinan pindah koridor/moda di
          tengah jalan (transfer jalan kaki, radius 500m).
        </p>
        <p>
          Sistem menawarkan beberapa alternatif sekaligus: <em>Rekomendasi</em>{" "}
          (tercepat), <em>Termurah</em>, <em>Paling sedikit transfer</em>, dan
          bila tersedia jalur lain yang benar-benar berbeda koridornya,{" "}
          <em>Lewat rute lain</em>. Kendaraan pribadi selalu ditambahkan
          sebagai pembanding.
        </p>
      </>
    ),
  },
  {
    title: "Waktu tempuh angkutan umum",
    body: (
      <>
        <p>
          Feeder Angkot &amp; Teman Bus: kecepatan tetap per jam, 25 km/jam
          saat jam sibuk (07:00-09:00, 12:00-14:00 saat anak pulang sekolah,
          &amp; 16:00-19:00), 32,5 km/jam di luar itu. Ini asumsi kota, bukan
          kecepatan per ruas jalan yang diukur.
        </p>
        <p>
          LRT: memakai jadwal resmi (bukan asumsi kecepatan). Waktu tempuh
          antar stasiun dan jadwal keberangkatan diambil langsung dari data
          jadwal DJKA.
        </p>
        <p>
          Waktu tunggu kendaraan baru: LRT memakai selisih ke keberangkatan
          terdekat di jadwal resmi. Feeder &amp; Teman Bus memakai asumsi
          headway (12 menit Feeder, 15 menit Teman Bus), <strong>bukan data
          pengamatan lapangan</strong>, karena tidak ada data headway nyata
          untuk angkutan informal ini.
        </p>
      </>
    ),
  },
  {
    title: "Kendaraan pribadi",
    body: (
      <>
        <p>
          Jarak &amp; jalur digambar dari <strong>OSRM</strong> (mesin
          routing jalan raya publik, profil &quot;driving&quot;) kalau
          tersedia, jalur jalan nyata, bukan garis lurus. Kalau OSRM gagal
          dihubungi, sistem jatuh ke estimasi garis lurus × 1,3 (faktor
          kelokan jalan).
        </p>
        <p>
          Waktu tempuh <strong>tidak</strong> memakai durasi bawaan OSRM
          (itu mengasumsikan jalan lengang sesuai batas kecepatan, terlalu
          optimis untuk lalu lintas kota), dihitung sendiri dari asumsi
          kecepatan motor efektif: 20 km/jam jam sibuk, 28 km/jam di luar
          itu.
        </p>
        <p>
          Biaya = estimasi BBM motor saja (~Rp250/km, dari asumsi 40 km/liter
          @ Rp10.000/liter), tidak termasuk parkir atau penyusutan kendaraan.
        </p>
      </>
    ),
  },
  {
    title: "Tarif",
    body: (
      <ul className="list-disc space-y-1 pl-5">
        <li>Angkot Feeder: gratis</li>
        <li>Teman Bus: Rp 5.000 sekali naik</li>
        <li>LRT: Rp 5.000 antar-stasiun, Rp 10.000 ujung ke ujung</li>
        <li>Pindah koridor/kendaraan pada moda yang sama: tidak ada tarif tambahan</li>
      </ul>
    ),
  },
  {
    title: "Skor kenyamanan & keandalan",
    body: (
      <p>
        Diberi nilai 1-5 <strong>secara editorial</strong> per moda (LRT
        dinilai paling nyaman &amp; andal karena berjadwal resmi; Feeder
        Angkot paling rendah karena angkutan informal tanpa data headway),
        bukan hasil pengukuran atau survei kepuasan penumpang. Dipakai untuk
        fitur &quot;Sesuai Preferensi Saya&quot; dan rekomendasi personal.
      </p>
    ),
  },
  {
    title: "Rekomendasi personal (preferensi)",
    body: (
      <p>
        Halaman <em>Preferensi</em> membiarkan Anda menilai 5 kriteria
        (waktu, biaya, kenyamanan, aksesibilitas, keandalan) skala 1-5.
        Sistem menimbang ulang alternatif yang <strong>sudah dihitung</strong>{" "}
        sesuai penilaian itu, bukan pencarian baru, dan tidak memengaruhi
        rekomendasi umum (Rekomendasi/Termurah/dst. selalu sama untuk semua
        orang).
      </p>
    ),
  },
  {
    title: "Keterbatasan yang perlu diketahui",
    body: (
      <ul className="list-disc space-y-1 pl-5">
        <li>Bukan rute belok-per-belok untuk kendaraan pribadi, OSRM dipakai untuk jarak &amp; jalur, bukan navigasi turn-by-turn lengkap</li>
        <li>Headway Feeder/Teman Bus adalah taksiran, bukan data pengamatan</li>
        <li>Kecepatan angkutan umum seragam per koridor, bukan per ruas jalan</li>
        <li>Skor kenyamanan/keandalan bersifat editorial, bukan hasil pengukuran</li>
        <li>Beberapa halte masih menyimpang &gt;50m dari jalur terekam</li>
      </ul>
    ),
  },
];

export default function AboutPage() {
  const router = useRouter();

  return (
    <div className="mx-auto min-h-screen max-w-2xl px-4 py-8">
      <button
        type="button"
        onClick={() => router.push("/")}
        className="mb-6 flex items-center gap-1.5 text-sm font-medium text-[var(--gmaps-blue)] hover:underline"
      >
        <NavigationIcon width={16} height={16} className="rotate-[-135deg]" />
        Kembali ke pencarian rute
      </button>

      <h1 className="text-xl font-semibold text-[var(--gmaps-text)]">
        Tentang Sistem Ini
      </h1>
      <p className="mt-1.5 text-sm text-[var(--gmaps-text-secondary)]">
        Bagaimana rute, waktu, dan biaya di aplikasi ini dihitung.
      </p>

      <div className="mt-8 space-y-8">
        {SECTIONS.map((section) => (
          <section key={section.title}>
            <h2 className="text-sm font-semibold text-[var(--gmaps-text)]">
              {section.title}
            </h2>
            <div className="mt-2 space-y-2 text-sm leading-relaxed text-[var(--gmaps-text-secondary)]">
              {section.body}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
