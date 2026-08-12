"use client";

import { useEffect } from "react";
import { Circle, MapContainer, Marker, Polyline, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { TaggedPoint } from "./useTaggingSession";

// Marker bernomor sederhana (divIcon) -- tidak butuh file gambar terpisah,
// cukup utk membedakan urutan titik tertag di peta.
function numberedIcon(n: number) {
  return L.divIcon({
    className: "",
    html: `<div style="background:#1a73e8;color:white;border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.4)">${n}</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
}

const currentPositionIcon = L.divIcon({
  className: "",
  html: `<div style="background:#ea4335;border-radius:50%;width:16px;height:16px;border:3px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.5)"></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

function RecenterOnPosition({ position }: { position: { lat: number; lon: number } | null }) {
  const map = useMap();
  useEffect(() => {
    if (position) map.setView([position.lat, position.lon], map.getZoom());
  }, [position, map]);
  return null;
}

function ClickToAdd({ onMapClick }: { onMapClick: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) {
      onMapClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

export default function TaggingMapComponent({
  points,
  currentPosition,
  onMapClick,
}: {
  points: TaggedPoint[];
  currentPosition: { lat: number; lon: number; accuracy: number } | null;
  onMapClick: (lat: number, lon: number) => void;
}) {
  const center: [number, number] = currentPosition
    ? [currentPosition.lat, currentPosition.lon]
    : [-2.9911, 104.7574];

  return (
    <MapContainer center={center} zoom={16} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClickToAdd onMapClick={onMapClick} />
      <RecenterOnPosition position={currentPosition} />

      {currentPosition && (
        <>
          <Marker position={[currentPosition.lat, currentPosition.lon]} icon={currentPositionIcon} />
          <Circle
            center={[currentPosition.lat, currentPosition.lon]}
            radius={currentPosition.accuracy}
            pathOptions={{ color: "#ea4335", fillOpacity: 0.1, weight: 1 }}
          />
        </>
      )}

      {points.length > 1 && (
        <Polyline positions={points.map((p) => [p.lat, p.lon])} color="#1a73e8" weight={4} opacity={0.7} />
      )}

      {points.map((p, i) => (
        <Marker key={p.id} position={[p.lat, p.lon]} icon={numberedIcon(i + 1)} />
      ))}
    </MapContainer>
  );
}
