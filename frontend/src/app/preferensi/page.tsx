"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { NavigationIcon } from "../components/icons";

export const PREFERENCE_STORAGE_KEY = "transit_preferences_v1";

export interface Preferences {
  time: number;
  cost: number;
  comfort: number;
  accessibility: number;
  reliability: number;
}

const DEFAULT_PREFERENCES: Preferences = {
  time: 3,
  cost: 3,
  comfort: 3,
  accessibility: 3,
  reliability: 3,
};

const CRITERIA: Array<{
  key: keyof Preferences;
  label: string;
  description: string;
}> = [
  {
    key: "time",
    label: "Waktu tempuh",
    description: "Seberapa penting sampai secepat mungkin?",
  },
  {
    key: "cost",
    label: "Biaya perjalanan",
    description: "Seberapa penting biaya perjalanan seminimal mungkin?",
  },
  {
    key: "comfort",
    label: "Kenyamanan",
    description: "Seberapa penting kenyamanan (moda ber-AC, tidak berdesakan)?",
  },
  {
    key: "accessibility",
    label: "Aksesibilitas",
    description: "Seberapa penting halte/titik naik-turun dekat dari lokasi Anda?",
  },
  {
    key: "reliability",
    label: "Keandalan",
    description: "Seberapa penting jadwal yang bisa diandalkan/tepat waktu?",
  },
];

export default function PreferensiPage() {
  const router = useRouter();
  const [preferences, setPreferences] = useState<Preferences>(DEFAULT_PREFERENCES);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(PREFERENCE_STORAGE_KEY);
    if (stored) {
      try {
        setPreferences({ ...DEFAULT_PREFERENCES, ...JSON.parse(stored) });
      } catch {
        // biarkan default kalau data tersimpan rusak
      }
    }
  }, []);

  const handleChange = (key: keyof Preferences, value: number) => {
    setSaved(false);
    setPreferences((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem(PREFERENCE_STORAGE_KEY, JSON.stringify(preferences));
    setSaved(true);
    router.push("/");
  };

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
        Preferensi Saya
      </h1>
      <p className="mt-1.5 text-sm text-[var(--gmaps-text-secondary)]">
        Nilai seberapa penting tiap aspek berikut untuk Anda, dari 1 (tidak
        penting) sampai 5 (sangat penting). Sistem akan merekomendasikan rute
        yang paling sesuai dengan penilaian Anda.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-7">
        {CRITERIA.map(({ key, label, description }) => (
          <div key={key}>
            <div className="flex items-baseline justify-between gap-2">
              <label
                htmlFor={key}
                className="text-sm font-medium text-[var(--gmaps-text)]"
              >
                {label}
              </label>
              <span className="text-sm font-semibold text-[var(--gmaps-blue)]">
                {preferences[key]}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-[var(--gmaps-text-secondary)]">
              {description}
            </p>
            <input
              id={key}
              type="range"
              min={1}
              max={5}
              step={1}
              value={preferences[key]}
              onChange={(e) => handleChange(key, Number(e.target.value))}
              className="mt-2.5 w-full accent-[var(--gmaps-blue)]"
            />
            <div className="mt-1 flex justify-between text-[11px] text-[var(--gmaps-text-secondary)]">
              <span>1 · Tidak penting</span>
              <span>3 · Netral</span>
              <span>5 · Sangat penting</span>
            </div>
          </div>
        ))}

        <button
          type="submit"
          className="w-full rounded-lg bg-[var(--gmaps-blue)] py-2.5 text-sm font-medium text-white hover:bg-[var(--gmaps-blue-hover)]"
        >
          Simpan preferensi
        </button>
        {saved && (
          <p className="text-center text-xs text-[var(--gmaps-green)]">
            Preferensi tersimpan.
          </p>
        )}
      </form>
    </div>
  );
}
