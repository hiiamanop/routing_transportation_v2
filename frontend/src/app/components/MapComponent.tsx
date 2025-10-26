"use client";

import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix for default markers in react-leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
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

interface RouteResult {
  success: boolean;
  route?: Route;
  algorithm_info?: {
    algorithm: string;
    iterations: number;
    max_depth: number;
    pruned_paths: number;
  };
  error?: string;
}

interface ApiResponse {
  success: boolean;
  results: {
    dijkstra?: RouteResult;
    dfs?: RouteResult;
    comparison?: {
      dijkstra_time: number;
      dfs_time: number;
      dijkstra_cost: number;
      dfs_cost: number;
      dijkstra_segments: number;
      dfs_segments: number;
      fastest: string;
      cheapest: string;
    };
  };
  request_info: {
    origin: { name: string; lat: number; lon: number };
    destination: { name: string; lat: number; lon: number };
    algorithm: string;
    departure_time: string;
  };
  error?: string;
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
  algorithm: "dijkstra" | "dfs" | "both";
  departure_time?: string;
}

// Component to fit map bounds
function MapBounds({
  routeResults,
  selectedRoute,
  routeRequest,
}: {
  routeResults: ApiResponse | null;
  selectedRoute: "dijkstra" | "dfs" | null;
  routeRequest: RouteRequest;
}) {
  const map = useMap();

  useEffect(() => {
    if (
      routeResults &&
      selectedRoute &&
      routeResults.results[selectedRoute]?.success
    ) {
      const route = routeResults.results[selectedRoute]!.route!;
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
  }, [map, routeResults, selectedRoute, routeRequest]);

  return null;
}

export default function MapComponent({
  routeResults,
  selectedRoute,
  routeRequest,
}: {
  routeResults: ApiResponse | null;
  selectedRoute: "dijkstra" | "dfs" | null;
  routeRequest: RouteRequest;
}) {
  const [stops, setStops] = useState<any[]>([]);

  // Load stops for visualization
  useEffect(() => {
    const loadStops = async () => {
      try {
        const response = await fetch("http://localhost:5001/api/stops");
        const data = await response.json();
        if (data.success) {
          setStops(data.stops);
        }
      } catch (error) {
        console.error("Failed to load stops:", error);
      }
    };

    loadStops();
  }, []);

  // Get route segments for visualization - EXACT coordinates from algorithm
  const getRouteSegments = () => {
    if (
      !routeResults ||
      !selectedRoute ||
      !routeResults.results[selectedRoute]?.success
    ) {
      return [];
    }

    const route = routeResults.results[selectedRoute]!.route!;
    return route.segments
      .filter(
        (segment) =>
          segment.from_coords.lat &&
          segment.from_coords.lon &&
          segment.to_coords.lat &&
          segment.to_coords.lon
      )
      .map((segment) => {
        // Use EXACT coordinates from algorithm - no modification
        const coordinates: Array<[number, number]> = [
          [segment.from_coords.lat, segment.from_coords.lon],
          [segment.to_coords.lat, segment.to_coords.lon],
        ];

        return {
          ...segment,
          coordinates,
        };
      });
  };

  // Get color for different transport modes
  const getModeColor = (mode: string) => {
    switch (mode.toLowerCase()) {
      case "walking":
        return "#10B981"; // Green
      case "teman_bus":
        return "#3B82F6"; // Blue
      case "feeder_angkot":
        return "#F59E0B"; // Orange
      case "lrt":
        return "#8B5CF6"; // Purple
      default:
        return "#6B7280"; // Gray
    }
  };

  const routeSegments = getRouteSegments();

  return (
    <div className="h-96 w-full">
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
          routeResults={routeResults}
          selectedRoute={selectedRoute}
          routeRequest={routeRequest}
        />

        {/* Origin Marker */}
        {routeRequest.origin.lat && routeRequest.origin.lon && (
          <Marker position={[routeRequest.origin.lat, routeRequest.origin.lon]}>
            <Popup>
              <div className="text-center">
                <div className="font-semibold text-green-600">📍 Origin</div>
                <div>{routeRequest.origin.name}</div>
                <div className="text-sm text-black">
                  {routeRequest.origin.lat.toFixed(6)},{" "}
                  {routeRequest.origin.lon.toFixed(6)}
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
          >
            <Popup>
              <div className="text-center">
                <div className="font-semibold text-red-600">🎯 Destination</div>
                <div>{routeRequest.destination.name}</div>
                <div className="text-sm text-black">
                  {routeRequest.destination.lat.toFixed(6)},{" "}
                  {routeRequest.destination.lon.toFixed(6)}
                </div>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Route Segments */}
        {routeSegments.map((segment, index) => (
          <Polyline
            key={`${selectedRoute}-${index}`}
            positions={segment.coordinates}
            color={getModeColor(segment.mode)}
            weight={4}
            opacity={0.8}
          />
        ))}

        {/* Stop Markers (smaller, less prominent) */}
        {stops.slice(0, 100).map((stop) => (
          <Marker key={stop.id} position={[stop.lat, stop.lon]} opacity={0.6}>
            <Popup>
              <div className="text-center">
                <div className="font-semibold">{stop.name}</div>
                <div className="text-sm text-black">{stop.mode}</div>
                <div className="text-xs text-black">{stop.route}</div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg p-3 z-[1000]">
        <div className="text-sm font-semibold mb-2 text-black">
          Transport Modes
        </div>
        <div className="space-y-1 text-xs text-black">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-1 bg-green-500"></div>
            <span className="text-black">Walking</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-1 bg-blue-500"></div>
            <span className="text-black">Teman Bus</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-1 bg-orange-500"></div>
            <span className="text-black">Feeder Angkot</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-1 bg-purple-500"></div>
            <span className="text-black">LRT</span>
          </div>
        </div>
      </div>

      {/* Route Info Overlay */}
      {routeSegments.length > 0 && (
        <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg p-3 z-[1000] max-w-xs">
          <div className="text-sm font-semibold mb-2 text-black">
            🗺️ Route (
            {selectedRoute === "dijkstra" ? "Dijkstra" : "Optimized DFS"})
          </div>
          <div className="space-y-1 text-xs text-black">
            {routeSegments.map((segment, index) => (
              <div key={index} className="flex items-center space-x-2">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: getModeColor(segment.mode) }}
                ></div>
                <span className="truncate text-black">
                  {segment.from_stop} → {segment.to_stop}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
