"use client";

import React, { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  CircleMarker,
  Tooltip,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { modeColor, modeLabel } from "./icons";
import { offsetPolyline } from "./geo";

// Pin ala Google Maps: lingkaran biru (asal) & tetesan merah (tujuan),
// dibuat lewat divIcon inline SVG -- lebih mirip Maps drpd marker default Leaflet.
const originIcon = L.divIcon({
  className: "",
  html: `<svg width="22" height="22" viewBox="0 0 22 22"><circle cx="11" cy="11" r="7" fill="#1a73e8" stroke="white" stroke-width="3"/></svg>`,
  iconSize: [22, 22],
  iconAnchor: [11, 11],
});

const destinationIcon = L.divIcon({
  className: "",
  html: `<svg width="28" height="40" viewBox="0 0 28 40"><path d="M14 0C6.3 0 0 6.3 0 14c0 10.5 14 26 14 26s14-15.5 14-26C28 6.3 21.7 0 14 0Z" fill="#d93025"/><circle cx="14" cy="14" r="5.5" fill="white"/></svg>`,
  iconSize: [28, 40],
  iconAnchor: [14, 40],
});

interface RouteSegment {
  sequence: number;
  mode: string;
  route_name: string;
  from_stop: string;
  to_stop: string;
  duration_minutes: number;
  cost: number;
  distance_km: number;
  departure_time: string;
  arrival_time: string;
  from_coords: {
    lat: number;
    lon: number;
  };
  to_coords: {
    lat: number;
    lon: number;
  };
  // Jalur trotoar/jalan asli utk segmen jalan kaki (dari OSRM), kalau
  // berhasil didapat backend. undefined/null = pakai garis lurus.
  path?: [number, number][] | null;
  // Nama halte yang dilewati di antara titik naik dan titik turun.
  via_stops?: string[];
}

interface Route {
  route_id: string;
  origin: string;
  destination: string;
  summary: {
    total_time_minutes: number;
    total_cost: number;
    total_distance_km: number;
    num_transfers: number;
    departure_time: string;
    arrival_time: string;
  };
  segments: RouteSegment[];
}

interface RouteRequest {
  origin: {
    name: string;
    lat: number;
    lon: number;
  };
  destination: {
    name: string;
    lat: number;
    lon: number;
  };
  departure_time?: string;
}

// Component to fit map bounds
function MapBounds({
  activeRoute,
  routeRequest,
}: {
  activeRoute: Route | null;
  routeRequest: RouteRequest;
}) {
  const map = useMap();

  useEffect(() => {
    if (activeRoute) {
      const route = activeRoute;
      const coordinates: [number, number][] = [];

      // Add origin and destination
      coordinates.push([routeRequest.origin.lat, routeRequest.origin.lon]);
      coordinates.push([
        routeRequest.destination.lat,
        routeRequest.destination.lon,
      ]);

      // Add all segment coordinates
      route.segments.forEach((segment) => {
        if (segment.from_coords.lat && segment.from_coords.lon) {
          coordinates.push([segment.from_coords.lat, segment.from_coords.lon]);
        }
        if (segment.to_coords.lat && segment.to_coords.lon) {
          coordinates.push([segment.to_coords.lat, segment.to_coords.lon]);
        }
      });

      if (coordinates.length > 0) {
        const bounds = L.latLngBounds(coordinates);
        map.fitBounds(bounds, { padding: [20, 20] });
      }
    } else if (
      routeRequest.origin.lat &&
      routeRequest.origin.lon &&
      routeRequest.destination.lat &&
      routeRequest.destination.lon
    ) {
      // Fit to origin and destination if no route
      const bounds = L.latLngBounds([
        [routeRequest.origin.lat, routeRequest.origin.lon],
        [routeRequest.destination.lat, routeRequest.destination.lon],
      ]);
      map.fitBounds(bounds, { padding: [20, 20] });
    }
  }, [map, activeRoute, routeRequest]);

  return null;
}

export default function MapComponent({
  activeRoute,
  routeRequest,
}: {
  activeRoute: Route | null;
  routeRequest: RouteRequest;
}) {
  // State for route waypoints (from KMZ)
  const [routeWaypoints, setRouteWaypoints] = React.useState<
    Record<string, Array<[number, number]>>
  >({});
  // [lat, lon, waypoint_index] per halte asli -- dicatat backend saat
  // polyline dibuat. Dipakai utk cari indeks awal/akhir tiap segmen
  // TANPA nearest-search di seluruh polyline: koridor berbentuk loop
  // bisa lewat berdekatan dgn dirinya sendiri di titik yg beda, jadi
  // "titik terdekat" di polyline penuh bisa salah nyasar ke bagian lain
  // dari loop. Anchor ini himpunan kecil (cuma sebanyak halte asli) yg
  // semuanya representasi halte sungguhan, jauh lebih aman dicocokkan.
  const [routeStopAnchors, setRouteStopAnchors] = React.useState<
    Record<string, Array<[number, number, number]>>
  >({});

  // Fetch waypoints for routes used in segments
  React.useEffect(() => {
    if (!activeRoute) {
      return;
    }

    const route = activeRoute;
    const uniqueRoutes = new Set(
      route.segments
        .filter(
          (seg) =>
            seg.route_name &&
            seg.mode !== "WALK" &&
            seg.mode !== "PRIVATE_VEHICLE"
        )
        .map((seg) => seg.route_name)
    );

    // Fetch waypoints for each route
    uniqueRoutes.forEach(async (routeName) => {
      if (routeWaypoints[routeName]) return; // Already loaded

      try {
        const response = await fetch(
          `/api/route/waypoints/${encodeURIComponent(routeName)}`
        );
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.waypoints) {
            setRouteWaypoints((prev) => ({
              ...prev,
              [routeName]: data.waypoints,
            }));
            setRouteStopAnchors((prev) => ({
              ...prev,
              [routeName]: data.stop_anchors ?? [],
            }));
          }
        }
      } catch {
        // Silently fail - will use straight line instead
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeRoute]);

  // Get route segments for visualization - with waypoints if available
  const getRouteSegments = () => {
    if (!activeRoute) {
      return [];
    }

    const route = activeRoute;
    return route.segments
      .filter(
        (segment) =>
          segment.from_coords.lat &&
          segment.from_coords.lon &&
          segment.to_coords.lat &&
          segment.to_coords.lon
      )
      .map((segment) => {
        let coordinates: Array<[number, number]> = [];
        // Titik halte yang dilewati segmen ini (naik, lewat, turun).
        let stopPoints: Array<{ lat: number; lon: number; name?: string }> = [];

        // Segmen jalan kaki: pakai jalur trotoar asli dari backend kalau ada,
        // supaya tidak digambar sebagai garis lurus menembus bangunan.
        if (segment.mode === "WALK" && segment.path && segment.path.length > 1) {
          coordinates = [...segment.path];
          coordinates[0] = [segment.from_coords.lat, segment.from_coords.lon];
          coordinates[coordinates.length - 1] = [
            segment.to_coords.lat,
            segment.to_coords.lon,
          ];
        } else if (
          segment.route_name &&
          routeWaypoints[segment.route_name] &&
          segment.mode !== "WALK" &&
          segment.mode !== "PRIVATE_VEHICLE"
        ) {
          const waypoints = routeWaypoints[segment.route_name];
          const anchors = routeStopAnchors[segment.route_name] ?? [];
          const fromLat = segment.from_coords.lat;
          const fromLon = segment.from_coords.lon;
          const toLat = segment.to_coords.lat;
          const toLon = segment.to_coords.lon;

          // Cocokkan ke daftar ANCHOR (halte asli, himpunan kecil), bukan
          // cari "titik terdekat" di seluruh polyline -- utk koridor loop,
          // polyline penuh bisa lewat berdekatan dgn dirinya sendiri di
          // bagian yg berbeda, jadi nearest-search di situ rawan salah
          // nyasar jauh dari halte yg dimaksud.
          let fromIdx = 0;
          let toIdx = waypoints.length - 1;
          let minFromDist = Infinity;
          let minToDist = Infinity;

          for (const [aLat, aLon, aIdx] of anchors) {
            const distFrom = Math.sqrt(
              Math.pow(aLat - fromLat, 2) + Math.pow(aLon - fromLon, 2)
            );
            const distTo = Math.sqrt(
              Math.pow(aLat - toLat, 2) + Math.pow(aLon - toLon, 2)
            );

            if (distFrom < minFromDist) {
              minFromDist = distFrom;
              fromIdx = aIdx;
            }
            if (distTo < minToDist) {
              minToDist = distTo;
              toIdx = aIdx;
            }
          }

          // Extract waypoints between from and to
          if (fromIdx < toIdx) {
            coordinates = waypoints.slice(fromIdx, toIdx + 1);
          } else if (fromIdx > toIdx) {
            // Reverse route
            coordinates = waypoints.slice(toIdx, fromIdx + 1).reverse();
          } else {
            // Same point, use direct line
            coordinates = [
              [fromLat, fromLon],
              [toLat, toLon],
            ];
          }

          // Ensure start and end match exactly
          if (coordinates.length > 0) {
            coordinates[0] = [fromLat, fromLon];
            coordinates[coordinates.length - 1] = [toLat, toLon];
          }

          // Geser ke sisi jalan sesuai arah tempuh. Untuk arah pulang,
          // koordinatnya sudah dibalik di atas, jadi "sisi kiri arah jalan"
          // otomatis jatuh di seberang -- dua arah tidak lagi bertumpuk
          // jadi satu garis.
          coordinates = offsetPolyline(coordinates);

          // Halte sepanjang segmen ini diambil dari anchor yang indeksnya
          // berada di antara titik naik dan titik turun -- jadi ikut
          // menandai halte yang cuma DILEWATI, bukan cuma ujung-ujungnya.
          const lo = Math.min(fromIdx, toIdx);
          const hi = Math.max(fromIdx, toIdx);
          const between = anchors
            .filter(([, , aIdx]) => aIdx >= lo && aIdx <= hi)
            .sort((a, b) => a[2] - b[2]);
          if (fromIdx > toIdx) between.reverse();

          stopPoints = between.map(([aLat, aLon]) => ({ lat: aLat, lon: aLon }));
          // Nama: ujung-ujungnya sudah pasti; yang di tengah dinamai dari
          // via_stops HANYA kalau jumlahnya cocok -- kalau tidak, biarkan
          // tanpa nama drpd salah memberi label.
          if (stopPoints.length > 0) {
            stopPoints[0].name = segment.from_stop;
            stopPoints[stopPoints.length - 1].name = segment.to_stop;
            const via = segment.via_stops ?? [];
            if (via.length === stopPoints.length - 2) {
              via.forEach((nm, k) => {
                stopPoints[k + 1].name = nm;
              });
            }
          }
        } else {
          // No waypoints available - use straight line
          coordinates = [
            [segment.from_coords.lat, segment.from_coords.lon],
            [segment.to_coords.lat, segment.to_coords.lon],
          ];
        }

        // Segmen transit tanpa data anchor (mis. koridor yang waypoint-nya
        // gagal dimuat) tetap ditandai titik naik & turunnya.
        const isOwnLeg =
          segment.mode === "WALK" || segment.mode === "PRIVATE_VEHICLE";
        if (stopPoints.length === 0 && !isOwnLeg) {
          stopPoints = [
            {
              lat: segment.from_coords.lat,
              lon: segment.from_coords.lon,
              name: segment.from_stop,
            },
            {
              lat: segment.to_coords.lat,
              lon: segment.to_coords.lon,
              name: segment.to_stop,
            },
          ];
        }

        return {
          ...segment,
          coordinates,
          stopPoints,
        };
      });
  };

  const routeSegments = getRouteSegments();
  const usedModes = Array.from(new Set(routeSegments.map((s) => s.mode)));

  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={[-2.9911, 104.7574]} // Palembang center
        zoom={12}
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Fit bounds to route */}
        <MapBounds
          activeRoute={activeRoute}
          routeRequest={routeRequest}
        />

        {/* Origin Marker */}
        {routeRequest.origin.lat && routeRequest.origin.lon && (
          <Marker
            position={[routeRequest.origin.lat, routeRequest.origin.lon]}
            icon={originIcon}
          >
            <Popup>
              <div className="text-sm">
                <div className="font-medium text-[var(--gmaps-blue)]">Origin</div>
                <div className="text-[var(--gmaps-text)]">
                  {routeRequest.origin.name}
                </div>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Destination Marker */}
        {routeRequest.destination.lat && routeRequest.destination.lon && (
          <Marker
            position={[
              routeRequest.destination.lat,
              routeRequest.destination.lon,
            ]}
            icon={destinationIcon}
          >
            <Popup>
              <div className="text-sm">
                <div className="font-medium text-[var(--gmaps-red)]">
                  Destination
                </div>
                <div className="text-[var(--gmaps-text)]">
                  {routeRequest.destination.name}
                </div>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Route Segments */}
        {routeSegments.map((segment, index) => {
          const isOwnLeg = segment.mode === "WALK" || segment.mode === "PRIVATE_VEHICLE";
          return (
            <Polyline
              // Key HARUS ikut berubah saat alternatif rute diganti. Dulu
              // key-nya `${route_id}-${index}`, padahal SEMUA alternatif
              // (Tercepat/Termurah/Preferensi) memakai route_id yang sama
              // yaitu 1 -- jadi saat pindah tab React memakai ulang objek
              // garis Leaflet yang lama dan warnanya tidak ikut diperbarui.
              key={`${segment.mode}|${segment.route_name}|${segment.from_stop}|${segment.to_stop}|${index}`}
              positions={segment.coordinates}
              color={modeColor(segment.mode)}
              weight={isOwnLeg ? 3 : 5}
              opacity={isOwnLeg ? 0.7 : 0.9}
              // Selalu dikirim eksplisit (string kosong utk garis tegas),
              // bukan dipasang bersyarat. Kalau prop-nya cuma dihilangkan,
              // Leaflet tidak menghapus gaya putus-putus yang menempel
              // sebelumnya pada objek garis yang dipakai ulang.
              dashArray={isOwnLeg ? "1, 8" : ""}
            />
          );
        })}

        {/* Titik halte sepanjang rute. Digambar setelah garis supaya tidak
            tertimpa. Titik naik & turun dibuat lebih besar drpd halte yang
            hanya dilewati, supaya mudah dibedakan sekilas. */}
        {routeSegments.flatMap((segment, si) =>
          (segment.stopPoints ?? []).map((sp, k, arr) => {
            const isEnd = k === 0 || k === arr.length - 1;
            return (
              <CircleMarker
                key={`stop-${si}-${k}-${sp.lat}-${sp.lon}`}
                center={[sp.lat, sp.lon]}
                radius={isEnd ? 6 : 3.5}
                pathOptions={{
                  color: "#ffffff",
                  weight: 2,
                  fillColor: modeColor(segment.mode),
                  fillOpacity: 1,
                }}
              >
                {sp.name && (
                  <Tooltip direction="top" offset={[0, -4]}>
                    {sp.name}
                  </Tooltip>
                )}
              </CircleMarker>
            );
          })
        )}
      </MapContainer>

      {/* Legend -- hanya moda yang benar-benar dipakai di rute saat ini */}
      {usedModes.length > 0 && (
        <div className="absolute bottom-4 left-4 z-[1000] rounded-lg bg-white p-3 shadow-lg">
          <div className="mb-1.5 text-xs font-medium text-[var(--gmaps-text-secondary)]">
            Legend
          </div>
          <div className="space-y-1.5">
            {usedModes.map((mode) => (
              <div key={mode} className="flex items-center gap-2">
                <span
                  className="h-1 w-4 rounded-full"
                  style={{ backgroundColor: modeColor(mode) }}
                />
                <span className="text-xs text-[var(--gmaps-text)]">
                  {modeLabel(mode)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
