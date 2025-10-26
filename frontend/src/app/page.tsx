"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import axios from "axios";

// Dynamically import Map component to avoid SSR issues
const MapComponent = dynamic(() => import("./components/MapComponent"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-96 bg-gray-100">
      Loading map...
    </div>
  ),
});

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

export default function Home() {
  const [routeRequest, setRouteRequest] = useState<RouteRequest>({
    origin: { name: "", lat: 0, lon: 0 },
    destination: { name: "", lat: 0, lon: 0 },
    algorithm: "both",
    departure_time: new Date().toISOString().slice(0, 16),
  });

  const [routeResults, setRouteResults] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedRoute, setSelectedRoute] = useState<"dijkstra" | "dfs" | null>(
    null
  );

  const API_BASE_URL = "http://localhost:5001/api";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setRouteResults(null);
    setSelectedRoute(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/route`, routeRequest);
      setRouteResults(response.data);

      // Auto-select first available route
      if (response.data.results.dijkstra?.success) {
        setSelectedRoute("dijkstra");
      } else if (response.data.results.dfs?.success) {
        setSelectedRoute("dfs");
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } } };
      setError(error.response?.data?.error || "Failed to get route");
    } finally {
      setLoading(false);
    }
  };

  const getCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setRouteRequest((prev) => ({
            ...prev,
            origin: {
              ...prev.origin,
              lat: position.coords.latitude,
              lon: position.coords.longitude,
            },
          }));
        },
        (error) => {
          console.error("Error getting location:", error);
        }
      );
    }
  };

  const formatTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = Math.floor(minutes % 60);
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  const formatCost = (cost: number) => {
    return new Intl.NumberFormat("id-ID", {
      style: "currency",
      currency: "IDR",
      minimumFractionDigits: 0,
    }).format(cost);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <h1 className="text-2xl font-bold text-black">
            🗺️ Palembang Public Transport Routing
          </h1>
          <p className="text-black mt-1">
            Find optimal routes using Dijkstra and DFS algorithms
          </p>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Route Planning Form */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold text-black mb-4">
                📍 Plan Your Route
              </h2>

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Origin */}
                <div>
                  <label className="block text-sm font-medium text-black mb-2">
                    Origin
                  </label>
                  <div className="space-y-2">
                    <input
                      type="text"
                      placeholder="Origin name"
                      value={routeRequest.origin.name}
                      onChange={(e) =>
                        setRouteRequest((prev) => ({
                          ...prev,
                          origin: { ...prev.origin, name: e.target.value },
                        }))
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
                      required
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="number"
                        step="any"
                        placeholder="Latitude"
                        value={routeRequest.origin.lat || ""}
                        onChange={(e) =>
                          setRouteRequest((prev) => ({
                            ...prev,
                            origin: {
                              ...prev.origin,
                              lat: parseFloat(e.target.value) || 0,
                            },
                          }))
                        }
                        className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
                        required
                      />
                      <input
                        type="number"
                        step="any"
                        placeholder="Longitude"
                        value={routeRequest.origin.lon || ""}
                        onChange={(e) =>
                          setRouteRequest((prev) => ({
                            ...prev,
                            origin: {
                              ...prev.origin,
                              lon: parseFloat(e.target.value) || 0,
                            },
                          }))
                        }
                        className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
                        required
                      />
                    </div>
                    <button
                      type="button"
                      onClick={getCurrentLocation}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      📍 Use current location
                    </button>
                  </div>
                </div>

                {/* Destination */}
                <div>
                  <label className="block text-sm font-medium text-black mb-2">
                    Destination
                  </label>
                  <div className="space-y-2">
                    <input
                      type="text"
                      placeholder="Destination name"
                      value={routeRequest.destination.name}
                      onChange={(e) =>
                        setRouteRequest((prev) => ({
                          ...prev,
                          destination: {
                            ...prev.destination,
                            name: e.target.value,
                          },
                        }))
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
                      required
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="number"
                        step="any"
                        placeholder="Latitude"
                        value={routeRequest.destination.lat || ""}
                        onChange={(e) =>
                          setRouteRequest((prev) => ({
                            ...prev,
                            destination: {
                              ...prev.destination,
                              lat: parseFloat(e.target.value) || 0,
                            },
                          }))
                        }
                        className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
                        required
                      />
                      <input
                        type="number"
                        step="any"
                        placeholder="Longitude"
                        value={routeRequest.destination.lon || ""}
                        onChange={(e) =>
                          setRouteRequest((prev) => ({
                            ...prev,
                            destination: {
                              ...prev.destination,
                              lon: parseFloat(e.target.value) || 0,
                            },
                          }))
                        }
                        className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
                        required
                      />
                    </div>
                  </div>
                </div>

                {/* Algorithm Selection */}
                <div>
                  <label className="block text-sm font-medium text-black mb-2">
                    Algorithm
                  </label>
                  <select
                    value={routeRequest.algorithm}
                    onChange={(e) =>
                      setRouteRequest((prev) => ({
                        ...prev,
                        algorithm: e.target.value as
                          | "dijkstra"
                          | "dfs"
                          | "both",
                      }))
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
                  >
                    <option value="both">Both (Compare Dijkstra vs DFS)</option>
                    <option value="dijkstra">Dijkstra Only</option>
                    <option value="dfs">Optimized DFS Only</option>
                  </select>
                </div>

                {/* Departure Time */}
                <div>
                  <label className="block text-sm font-medium text-black mb-2">
                    Departure Time
                  </label>
                  <input
                    type="datetime-local"
                    value={routeRequest.departure_time}
                    onChange={(e) =>
                      setRouteRequest((prev) => ({
                        ...prev,
                        departure_time: e.target.value,
                      }))
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
                  />
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? "🔄 Finding Route..." : "🚀 Find Route"}
                </button>
              </form>

              {/* Error Display */}
              {error && (
                <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md">
                  ❌ {error}
                </div>
              )}
            </div>

            {/* Route Results */}
            {routeResults && (
              <div className="mt-6 space-y-4">
                {/* Algorithm Selection */}
                {routeResults.results.dijkstra?.success &&
                  routeResults.results.dfs?.success && (
                    <div className="bg-white rounded-lg shadow-sm p-4">
                      <h3 className="font-semibold text-black mb-3">
                        Choose Route to Display:
                      </h3>
                      <div className="flex space-x-2">
                        <button
                          onClick={() => setSelectedRoute("dijkstra")}
                          className={`px-3 py-1 rounded text-sm ${
                            selectedRoute === "dijkstra"
                              ? "bg-blue-600 text-white"
                              : "bg-gray-200 text-black hover:bg-gray-300"
                          }`}
                        >
                          Dijkstra
                        </button>
                        <button
                          onClick={() => setSelectedRoute("dfs")}
                          className={`px-3 py-1 rounded text-sm ${
                            selectedRoute === "dfs"
                              ? "bg-blue-600 text-white"
                              : "bg-gray-200 text-black hover:bg-gray-300"
                          }`}
                        >
                          Optimized DFS
                        </button>
                      </div>
                    </div>
                  )}

                {/* Route Summary */}
                {selectedRoute &&
                  routeResults.results[selectedRoute]?.success && (
                    <div className="bg-white rounded-lg shadow-sm p-4">
                      <h3 className="font-semibold text-black mb-3">
                        📊 Route Summary (
                        {selectedRoute === "dijkstra"
                          ? "Dijkstra"
                          : "Optimized DFS"}
                        )
                      </h3>
                      {routeResults.results[selectedRoute]?.route && (
                        <div className="space-y-2 text-sm text-black">
                          <div className="flex justify-between">
                            <span>⏱️ Total Time:</span>
                            <span className="font-medium">
                              {formatTime(
                                routeResults.results[selectedRoute]!.route!
                                  .summary.total_time_minutes
                              )}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>💰 Total Cost:</span>
                            <span className="font-medium">
                              {formatCost(
                                routeResults.results[selectedRoute]!.route!
                                  .summary.total_cost
                              )}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>📏 Distance:</span>
                            <span className="font-medium">
                              {routeResults.results[
                                selectedRoute
                              ]!.route!.summary.total_distance_km.toFixed(
                                2
                              )}{" "}
                              km
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>🔄 Transfers:</span>
                            <span className="font-medium">
                              {
                                routeResults.results[selectedRoute]!.route!
                                  .summary.num_transfers
                              }
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>🚌 Segments:</span>
                            <span className="font-medium">
                              {
                                routeResults.results[selectedRoute]!.route!
                                  .segments.length
                              }
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                {/* Route Details */}
                {selectedRoute &&
                  routeResults.results[selectedRoute]?.success && (
                    <div className="bg-white rounded-lg shadow-sm p-4">
                      <h3 className="font-semibold text-black mb-3">
                        🚌 Route Details (
                        {selectedRoute === "dijkstra"
                          ? "Dijkstra"
                          : "Optimized DFS"}
                        )
                      </h3>
                      {routeResults.results[selectedRoute]?.route && (
                        <div className="space-y-3">
                          {routeResults.results[
                            selectedRoute
                          ]!.route!.segments.map((segment, index) => (
                            <div
                              key={index}
                              className="border-l-4 border-blue-500 pl-3 py-2"
                            >
                              <div className="flex items-center space-x-2 mb-1">
                                <span className="text-sm font-medium text-blue-600">
                                  {segment.sequence}.
                                </span>
                                <span className="text-sm font-medium text-black">
                                  {segment.mode === "WALK"
                                    ? "🚶 Walk"
                                    : segment.mode === "FEEDER_ANGKOT"
                                    ? "🚐 Feeder Angkot"
                                    : segment.mode === "TEMAN_BUS"
                                    ? "🚌 Teman Bus"
                                    : segment.mode === "LRT"
                                    ? "🚇 LRT"
                                    : "🚌 Transit"}
                                </span>
                                {segment.route_name &&
                                  segment.route_name !== "Unknown" && (
                                    <span className="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded">
                                      {segment.route_name}
                                    </span>
                                  )}
                              </div>
                              <div className="text-sm text-black">
                                <div className="font-medium">
                                  {segment.from_stop} → {segment.to_stop}
                                </div>
                                <div className="text-xs text-gray-600 mt-1">
                                  ⏱️ {Math.round(segment.duration_minutes)} min
                                  {segment.distance_km > 0 && (
                                    <>
                                      {" "}
                                      • 📏 {segment.distance_km.toFixed(2)} km
                                    </>
                                  )}
                                  {segment.cost > 0 && (
                                    <> • 💰 {formatCost(segment.cost)}</>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                {/* Algorithm Info for DFS */}
                {selectedRoute === "dfs" &&
                  routeResults.results.dfs?.algorithm_info && (
                    <div className="bg-white rounded-lg shadow-sm p-4">
                      <h3 className="font-semibold text-black mb-3">
                        🔍 DFS Algorithm Info
                      </h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>Algorithm:</span>
                          <span className="font-medium">
                            {routeResults.results.dfs.algorithm_info.algorithm}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Iterations:</span>
                          <span className="font-medium">
                            {routeResults.results.dfs.algorithm_info.iterations}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Max Depth:</span>
                          <span className="font-medium">
                            {routeResults.results.dfs.algorithm_info.max_depth}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Pruned Paths:</span>
                          <span className="font-medium">
                            {
                              routeResults.results.dfs.algorithm_info
                                .pruned_paths
                            }
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                {/* Comparison */}
                {routeResults.results.comparison && (
                  <div className="bg-white rounded-lg shadow-sm p-4">
                    <h3 className="font-semibold text-black mb-3">
                      📊 Algorithm Comparison
                    </h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>🏆 Fastest:</span>
                        <span className="font-medium">
                          {routeResults.results.comparison.fastest}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>💰 Cheapest:</span>
                        <span className="font-medium">
                          {routeResults.results.comparison.cheapest}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>⏱️ Dijkstra Time:</span>
                        <span className="font-medium">
                          {formatTime(
                            routeResults.results.comparison.dijkstra_time
                          )}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>⏱️ DFS Time:</span>
                        <span className="font-medium">
                          {formatTime(routeResults.results.comparison.dfs_time)}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Map */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-sm overflow-hidden">
              <MapComponent
                routeResults={routeResults}
                selectedRoute={selectedRoute}
                routeRequest={routeRequest}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
