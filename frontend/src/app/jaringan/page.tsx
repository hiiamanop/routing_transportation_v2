"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { NavigationIcon, modeColor, modeLabel } from "../components/icons";
import type { NetworkRoute } from "../components/NetworkMapComponent";

const NetworkMapComponent = dynamic(
  () => import("../components/NetworkMapComponent"),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full w-full items-center justify-center bg-[var(--gmaps-surface-hover)] text-sm text-[var(--gmaps-text-secondary)]">
        Memuat peta...
      </div>
    ),
  }
);

interface StopApiResponse {
  success: boolean;
  stops: Array<{ name: string; lat: number; lon: number; mode: string; route: string }>;
  total: number;
}

export default function JaringanPage() {
  const router = useRouter();
  const [routes, setRoutes] = useState<NetworkRoute[]>([]);
  // Nama koridor yang sedang dipilih. null = belum ada yang diklik, dan
  // peta memang sengaja dibiarkan kosong sampai user memilih koridor.
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/stops")
      .then((res) => res.json())
      .then((data: StopApiResponse) => {
        if (!data.success) {
          setError("Gagal memuat daftar koridor.");
          return;
        }
        // Satu entri per koridor (nama rute unik), bukan per halte --
        // urutan kemunculan pertama di data cukup utk moda-nya, semua
        // halte di koridor yg sama pasti punya moda yg sama.
        const seen = new Map<string, string>();
        for (const stop of data.stops) {
          if (!seen.has(stop.route)) seen.set(stop.route, stop.mode);
        }
        setRoutes(
          Array.from(seen.entries()).map(([name, mode]) => ({ name, mode }))
        );
      })
      .catch(() => setError("Gagal memuat daftar koridor."))
      .finally(() => setLoading(false));
  }, []);

  const routesByMode = useMemo(() => {
    const grouped = new Map<string, NetworkRoute[]>();
    for (const route of routes) {
      const list = grouped.get(route.mode) ?? [];
      list.push(route);
      grouped.set(route.mode, list);
    }
    return grouped;
  }, [routes]);

  const selectedRoute =
    routes.find((route) => route.name === selectedName) ?? null;

  return (
    <div className="flex min-h-screen flex-col bg-white lg:h-screen lg:flex-row lg:overflow-hidden">
      <aside className="flex w-full flex-col border-b border-[var(--gmaps-border)] bg-white lg:h-full lg:w-[360px] lg:border-b-0 lg:border-r">
        <div className="flex items-center gap-3 px-4 py-3">
          <button
            type="button"
            onClick={() => router.push("/")}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-[var(--gmaps-border)] text-[var(--gmaps-text-secondary)] hover:bg-[var(--gmaps-surface-hover)]"
            title="Kembali ke pencarian rute"
          >
            <NavigationIcon width={16} height={16} className="rotate-[-135deg]" />
          </button>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-base font-medium leading-tight text-[var(--gmaps-text)]">
              Peta Jaringan
            </h1>
            <p className="truncate text-xs text-[var(--gmaps-text-secondary)]">
              Semua koridor angkutan umum di Palembang
            </p>
          </div>
        </div>

        <div className="gmaps-scroll px-4 pb-4 lg:flex-1 lg:overflow-y-auto">
          {loading && (
            <p className="text-sm text-[var(--gmaps-text-secondary)]">Memuat...</p>
          )}
          {error && (
            <p className="text-sm text-[var(--gmaps-red)]">{error}</p>
          )}

          {Array.from(routesByMode.entries()).map(([mode, modeRoutes]) => (
            <div key={mode} className="mb-5">
              <div className="mb-2 flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: modeColor(mode) }}
                />
                <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--gmaps-text-secondary)]">
                  {modeLabel(mode)} ({modeRoutes.length})
                </h2>
              </div>
              <ul className="space-y-1">
                {modeRoutes.map((route) => (
                  <li key={route.name}>
                    <button
                      type="button"
                      onClick={() =>
                        setSelectedName((cur) =>
                          cur === route.name ? null : route.name
                        )
                      }
                      className={`w-full truncate rounded-md px-2.5 py-1.5 text-left text-sm hover:bg-[var(--gmaps-surface-hover)] ${
                        selectedName === route.name
                          ? "bg-[var(--gmaps-surface-hover)] font-medium text-[var(--gmaps-blue)]"
                          : "text-[var(--gmaps-text)]"
                      }`}
                    >
                      {route.name}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </aside>

      <main className="relative h-[60vh] w-full lg:h-full lg:flex-1">
        <NetworkMapComponent selectedRoute={selectedRoute} />

        {/* Peta sengaja kosong sampai koridor dipilih -- tanpa petunjuk ini
            peta kosong terlihat seperti gagal memuat. */}
        {!selectedRoute && (
          <div className="pointer-events-none absolute inset-x-0 top-4 z-[1000] flex justify-center px-4">
            <p className="rounded-full bg-white/95 px-4 py-2 text-sm text-[var(--gmaps-text-secondary)] shadow-md">
              Pilih koridor di daftar untuk menampilkan rutenya di peta
            </p>
          </div>
        )}

        {selectedRoute && (
          <div className="pointer-events-none absolute inset-x-0 top-4 z-[1000] flex justify-center px-4">
            <p className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 rounded-full bg-white/95 px-4 py-2 text-sm font-medium text-[var(--gmaps-text)] shadow-md">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: modeColor(selectedRoute.mode) }}
              />
              {selectedRoute.name}
              <span className="text-xs font-normal text-[var(--gmaps-text-secondary)]">
                · garis tegas = berangkat, putus-putus = pulang
              </span>
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
