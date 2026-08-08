"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { NavigationIcon } from "../components/icons";

const RESPONDENT_ID_KEY = "transit_respondent_v1";
const RESPONDENT_DONE_KEY = "transit_respondent_done_v1";

interface RespondentForm {
  age: string;
  gender: string;
  occupation: string;
  income: string;
  vehicle_ownership: string;
  trip_purpose: string;
  transit_frequency: string;
}

const DEFAULT_FORM: RespondentForm = {
  age: "",
  gender: "",
  occupation: "",
  income: "",
  vehicle_ownership: "",
  trip_purpose: "",
  transit_frequency: "",
};

const FIELDS: Array<{
  key: keyof RespondentForm;
  label: string;
  options: string[];
}> = [
  { key: "age", label: "Usia", options: ["<18", "18-25", "26-35", "36-50", ">50"] },
  { key: "gender", label: "Jenis kelamin", options: ["Laki-laki", "Perempuan"] },
  {
    key: "occupation",
    label: "Pekerjaan",
    options: ["Pelajar/Mahasiswa", "Karyawan", "Wiraswasta", "PNS/TNI/Polri", "Lainnya"],
  },
  {
    key: "income",
    label: "Pendapatan per bulan",
    options: ["<1 juta", "1-3 juta", "3-5 juta", "5-10 juta", ">10 juta"],
  },
  {
    key: "vehicle_ownership",
    label: "Kepemilikan kendaraan pribadi",
    options: ["Tidak punya", "Motor", "Mobil", "Motor dan mobil"],
  },
  {
    key: "trip_purpose",
    label: "Maksud perjalanan yang biasa dilakukan",
    options: ["Kerja", "Sekolah/Kuliah", "Belanja/Rekreasi", "Lainnya"],
  },
  {
    key: "transit_frequency",
    label: "Frekuensi memakai angkutan umum",
    options: ["Setiap hari", "Beberapa kali seminggu", "Beberapa kali sebulan", "Jarang/tidak pernah"],
  },
];

export default function RespondenPage() {
  const router = useRouter();
  const [form, setForm] = useState<RespondentForm>(DEFAULT_FORM);
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [alreadyDone, setAlreadyDone] = useState(false);

  useEffect(() => {
    setAlreadyDone(localStorage.getItem(RESPONDENT_DONE_KEY) === "1");
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("saving");

    let respondentId = localStorage.getItem(RESPONDENT_ID_KEY);
    if (!respondentId) {
      respondentId = crypto.randomUUID();
      localStorage.setItem(RESPONDENT_ID_KEY, respondentId);
    }

    try {
      await axios.post("/api/respondent", { respondent_id: respondentId, ...form });
      localStorage.setItem(RESPONDENT_DONE_KEY, "1");
      setStatus("saved");
      router.push("/");
    } catch {
      setStatus("error");
    }
  };

  const isComplete = FIELDS.every(({ key }) => form[key] !== "");

  return (
    <div className="mx-auto min-h-screen max-w-xl px-4 py-8">
      <button
        type="button"
        onClick={() => router.push("/")}
        className="mb-6 flex items-center gap-1.5 text-sm font-medium text-[var(--gmaps-blue)] hover:underline"
      >
        <NavigationIcon width={16} height={16} className="rotate-[-135deg]" />
        Kembali ke pencarian rute
      </button>

      <h1 className="text-xl font-semibold text-[var(--gmaps-text)]">
        Karakteristik Responden
      </h1>
      <p className="mt-1.5 text-sm text-[var(--gmaps-text-secondary)]">
        Data ini anonim -- tidak perlu akun atau login. Dipakai untuk memahami
        mengapa kelompok orang berbeda memilih moda transportasi berbeda.
      </p>
      {alreadyDone && (
        <p className="mt-2 text-xs text-[var(--gmaps-text-secondary)]">
          Anda sudah pernah mengisi formulir ini di perangkat ini. Mengisi
          ulang akan menambah baris baru.
        </p>
      )}

      <form onSubmit={handleSubmit} className="mt-8 space-y-6">
        {FIELDS.map(({ key, label, options }) => (
          <div key={key}>
            <label className="text-sm font-medium text-[var(--gmaps-text)]">
              {label}
            </label>
            <select
              value={form[key]}
              onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))}
              required
              className="mt-1.5 w-full rounded-lg border border-[var(--gmaps-border)] px-3 py-2 text-sm text-[var(--gmaps-text)]"
            >
              <option value="" disabled>
                Pilih salah satu
              </option>
              {options.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
        ))}

        <button
          type="submit"
          disabled={!isComplete || status === "saving"}
          className="w-full rounded-lg bg-[var(--gmaps-blue)] py-2.5 text-sm font-medium text-white hover:bg-[var(--gmaps-blue-hover)] disabled:opacity-50"
        >
          {status === "saving" ? "Menyimpan..." : "Simpan"}
        </button>
        {status === "error" && (
          <p className="text-center text-xs text-red-600">
            Gagal menyimpan, coba lagi.
          </p>
        )}
      </form>
    </div>
  );
}
