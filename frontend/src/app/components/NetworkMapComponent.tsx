"use client";

import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { modeColor } from "./icons";
import { offsetPolyline } from "./geo";

export interface NetworkRoute {
  name: string;
  mode: string;
}

// Peta jaringan: menampilkan SATU koridor yang dipilih user (bukan satu
// rute perjalanan spt MapComponent.tsx, dan bukan semua koridor sekaligus).
// Peta sengaja kosong sampai user klik koridor -- 11 koridor digambar
// bersamaan bikin peta penuh & sulit dibaca.
//
// Waypoint di-fetch HANYA saat koridornya dipilih (bukan semua di awal),
// lalu di-cache per nama supaya klik ulang koridor yang sama tidak
// memanggil API lagi.
export default function NetworkMapComponent({
  selectedRoute,
}: {
  selectedRoute: NetworkRoute | null;
}) {
  const [waypoints, setWaypoints] = useState<
    Record<string, Array<[number, number]>>
  >({});

  useEffect(() => {
    if (!selectedRoute || waypoints[selectedRoute.name]) return;

    let cancelled = false;
    const routeName = selectedRoute.name;

    (async () => {
      try {
        const response = await fetch(
          `/api/route/waypoints/${encodeURIComponent(routeName)}`
        );
        if (!response.ok) return;
        const data = await response.json();
        if (!cancelled && data.success && data.waypoints) {
          setWaypoints((prev) => ({ ...prev, [routeName]: data.waypoints }));
        }
      } catch {
        // koridor ini gagal dimuat -- peta tetap tampil, garis tidak digambar
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [selectedRoute, waypoints]);

  const path = selectedRoute ? waypoints[selectedRoute.name] : undefined;

  return (
    <MapContainer
      center={[-2.9911, 104.7574]}
      zoom={12}
      className="h-full w-full"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {/* Dua arah digambar terpisah: koridor melayani A->B lalu B->A lewat
          titik halte yang sama, jadi masing-masing arah digeser ke sisi
          jalannya sendiri agar terlihat sebagai dua garis sejajar di ruas
          berbeda, bukan satu garis bertumpuk. */}
      {selectedRoute && path && path.length > 1 && (
        <>
          <Polyline
            positions={offsetPolyline(path)}
            color={modeColor(selectedRoute.mode)}
            weight={5}
            opacity={0.9}
          />
          <Polyline
            positions={offsetPolyline([...path].reverse())}
            color={modeColor(selectedRoute.mode)}
            weight={5}
            opacity={0.45}
            dashArray="10, 6"
          />
        </>
      )}
    </MapContainer>
  );
}
