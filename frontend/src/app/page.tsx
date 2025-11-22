"use client";

import { useState, useEffect, useRef } from "react";
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
  algorithm: "dijkstra";
  departure_time?: string;
}

interface OSMPlace {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
  google_place_id?: string; // Google Places API place_id
}

interface PlaceDetails {
  lat: number;
  lng: number;
  name: string;
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
    algorithm: "dijkstra",
    departure_time: new Date().toISOString().slice(0, 16),
  });

  const [routeResults, setRouteResults] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedRoute, setSelectedRoute] = useState<"dijkstra" | "dfs" | null>(
    null
  );

  // OSM Places API states
  const [originSuggestions, setOriginSuggestions] = useState<OSMPlace[]>([]);
  const [destinationSuggestions, setDestinationSuggestions] = useState<
    OSMPlace[]
  >([]);
  const [showOriginSuggestions, setShowOriginSuggestions] = useState(false);
  const [showDestinationSuggestions, setShowDestinationSuggestions] =
    useState(false);
  const [originSearching, setOriginSearching] = useState(false);
  const [destinationSearching, setDestinationSearching] = useState(false);
  const originInputRef = useRef<HTMLInputElement>(null);
  const destinationInputRef = useRef<HTMLInputElement>(null);
  const originSearchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const destinationSearchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Next.js API routes (search-places)
  const SEARCH_API_BASE_URL =
    typeof window !== "undefined"
      ? `http://${window.location.hostname}:3003/api`
      : "/api";

  // Flask API backend (routing)
  const ROUTE_API_BASE_URL =
    typeof window !== "undefined" ? `http://localhost:5001/api` : "/api";

  // Debounce delay (500ms)
  const DEBOUNCE_DELAY = 500;

  // Search Google Places API via Next.js API route
  const searchOSMPlaces = async (query: string): Promise<OSMPlace[]> => {
    if (!query || query.trim().length < 3) {
      return [];
    }

    try {
      const response = await fetch(
        `${SEARCH_API_BASE_URL}/search-places?q=${encodeURIComponent(
          query.trim()
        )}`
      );

      if (!response.ok) {
        return [];
      }

      const data = (await response.json()) as OSMPlace[];

      // Validate data structure
      if (Array.isArray(data)) {
        return data;
      }

      return [];
    } catch {
      // Silent fail - return empty array
      return [];
    }
  };

  // Fetch place details (lat, lng) from Google Places API
  const fetchPlaceDetails = async (
    googlePlaceId: string
  ): Promise<PlaceDetails | null> => {
    if (!googlePlaceId) {
      return null;
    }

    try {
      const response = await fetch(`${SEARCH_API_BASE_URL}/search-places`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ place_id: googlePlaceId }),
      });

      if (!response.ok) {
        return null;
      }

      const data = (await response.json()) as PlaceDetails;
      return data;
    } catch {
      return null;
    }
  };

  // Handle origin input change with debouncing
  const handleOriginChange = (value: string) => {
    setRouteRequest((prev) => ({
      ...prev,
      origin: { ...prev.origin, name: value },
    }));

    // Clear existing timeout
    if (originSearchTimeoutRef.current) {
      clearTimeout(originSearchTimeoutRef.current);
    }

    if (value.trim().length < 3) {
      setOriginSuggestions([]);
      setShowOriginSuggestions(false);
      setOriginSearching(false);
      return;
    }

    // Show loading state
    setOriginSearching(true);

    // Debounce search
    originSearchTimeoutRef.current = setTimeout(async () => {
      const suggestions = await searchOSMPlaces(value);
      setOriginSuggestions(suggestions);
      setShowOriginSuggestions(suggestions.length > 0);
      setOriginSearching(false);
    }, DEBOUNCE_DELAY);
  };

  // Handle destination input change with debouncing
  const handleDestinationChange = (value: string) => {
    setRouteRequest((prev) => ({
      ...prev,
      destination: { ...prev.destination, name: value },
    }));

    // Clear existing timeout
    if (destinationSearchTimeoutRef.current) {
      clearTimeout(destinationSearchTimeoutRef.current);
    }

    if (value.trim().length < 3) {
      setDestinationSuggestions([]);
      setShowDestinationSuggestions(false);
      setDestinationSearching(false);
      return;
    }

    // Show loading state
    setDestinationSearching(true);

    // Debounce search
    destinationSearchTimeoutRef.current = setTimeout(async () => {
      const suggestions = await searchOSMPlaces(value);
      setDestinationSuggestions(suggestions);
      setShowDestinationSuggestions(suggestions.length > 0);
      setDestinationSearching(false);
    }, DEBOUNCE_DELAY);
  };

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      if (originSearchTimeoutRef.current) {
        clearTimeout(originSearchTimeoutRef.current);
      }
      if (destinationSearchTimeoutRef.current) {
        clearTimeout(destinationSearchTimeoutRef.current);
      }
    };
  }, []);

  // Select origin place
  const selectOriginPlace = async (place: OSMPlace) => {
    setShowOriginSuggestions(false);

    // If we have coordinates from Text Search API, use them directly
    if (place.lat && place.lon && place.lat !== "0" && place.lon !== "0") {
      setRouteRequest((prev) => ({
        ...prev,
        origin: {
          name: place.display_name,
          lat: parseFloat(place.lat),
          lon: parseFloat(place.lon),
        },
      }));
      setOriginSuggestions([]);
      return;
    }

    // Otherwise, fetch place details from Google Places API
    if (place.google_place_id) {
      setOriginSearching(true);
      const details = await fetchPlaceDetails(place.google_place_id);
      setOriginSearching(false);

      if (details) {
        setRouteRequest((prev) => ({
          ...prev,
          origin: {
            name: place.display_name,
            lat: details.lat,
            lon: details.lng,
          },
        }));
      } else {
        // Fallback: use display name only
        setRouteRequest((prev) => ({
          ...prev,
          origin: {
            name: place.display_name,
            lat: 0,
            lon: 0,
          },
        }));
      }
    } else {
      // No Google place ID, use display name only
      setRouteRequest((prev) => ({
        ...prev,
        origin: {
          name: place.display_name,
          lat: 0,
          lon: 0,
        },
      }));
    }

    setOriginSuggestions([]);
  };

  // Select destination place
  const selectDestinationPlace = async (place: OSMPlace) => {
    setShowDestinationSuggestions(false);

    // If we have coordinates from Text Search API, use them directly
    if (place.lat && place.lon && place.lat !== "0" && place.lon !== "0") {
      setRouteRequest((prev) => ({
        ...prev,
        destination: {
          name: place.display_name,
          lat: parseFloat(place.lat),
          lon: parseFloat(place.lon),
        },
      }));
      setDestinationSuggestions([]);
      return;
    }

    // Otherwise, fetch place details from Google Places API
    if (place.google_place_id) {
      setDestinationSearching(true);
      const details = await fetchPlaceDetails(place.google_place_id);
      setDestinationSearching(false);

      if (details) {
        setRouteRequest((prev) => ({
          ...prev,
          destination: {
            name: place.display_name,
            lat: details.lat,
            lon: details.lng,
          },
        }));
      } else {
        // Fallback: use display name only
        setRouteRequest((prev) => ({
          ...prev,
          destination: {
            name: place.display_name,
            lat: 0,
            lon: 0,
          },
        }));
      }
    } else {
      // No Google place ID, use display name only
      setRouteRequest((prev) => ({
        ...prev,
        destination: {
          name: place.display_name,
          lat: 0,
          lon: 0,
        },
      }));
    }

    setDestinationSuggestions([]);
  };

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        originInputRef.current &&
        !originInputRef.current.contains(event.target as Node)
      ) {
        setShowOriginSuggestions(false);
      }
      if (
        destinationInputRef.current &&
        !destinationInputRef.current.contains(event.target as Node)
      ) {
        setShowDestinationSuggestions(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setRouteResults(null);
    setSelectedRoute(null);

    try {
      const response = await axios.post(
        `${ROUTE_API_BASE_URL}/route`,
        routeRequest
      );
      setRouteResults(response.data);

      // Auto-select dijkstra route (Enhanced DFS uses Dijkstra)
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
            Find optimal routes using Enhanced DFS algorithm
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
                {/* Origin with OSM Autocomplete */}
                <div>
                  <label className="block text-sm font-medium text-black mb-2">
                    Origin
                  </label>
                  <div className="space-y-2 relative" ref={originInputRef}>
                    <input
                      type="text"
                      placeholder="Search location in Palembang..."
                      value={routeRequest.origin.name}
                      onChange={(e) => handleOriginChange(e.target.value)}
                      onFocus={() => {
                        if (originSuggestions.length > 0) {
                          setShowOriginSuggestions(true);
                        }
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
                      required
                    />
                    {originSearching && (
                      <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg p-3">
                        <div className="text-sm text-gray-500 text-center">
                          🔍 Searching...
                        </div>
                      </div>
                    )}
                    {!originSearching &&
                      showOriginSuggestions &&
                      originSuggestions.length > 0 && (
                        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
                          {originSuggestions.map((place) => (
                            <div
                              key={place.place_id}
                              onClick={() => selectOriginPlace(place)}
                              className="px-4 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                            >
                              <div className="text-sm font-medium text-black">
                                {place.display_name.split(",")[0]}
                              </div>
                              <div className="text-xs text-gray-500">
                                {place.display_name}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    <div className="text-xs text-gray-500">
                      Coordinates: {routeRequest.origin.lat.toFixed(6)},{" "}
                      {routeRequest.origin.lon.toFixed(6)}
                    </div>
                  </div>
                </div>

                {/* Destination with OSM Autocomplete */}
                <div>
                  <label className="block text-sm font-medium text-black mb-2">
                    Destination
                  </label>
                  <div className="space-y-2 relative" ref={destinationInputRef}>
                    <input
                      type="text"
                      placeholder="Search location in Palembang..."
                      value={routeRequest.destination.name}
                      onChange={(e) => handleDestinationChange(e.target.value)}
                      onFocus={() => {
                        if (destinationSuggestions.length > 0) {
                          setShowDestinationSuggestions(true);
                        }
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
                      required
                    />
                    {destinationSearching && (
                      <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg p-3">
                        <div className="text-sm text-gray-500 text-center">
                          🔍 Searching...
                        </div>
                      </div>
                    )}
                    {!destinationSearching &&
                      showDestinationSuggestions &&
                      destinationSuggestions.length > 0 && (
                        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
                          {destinationSuggestions.map((place) => (
                            <div
                              key={place.place_id}
                              onClick={() => selectDestinationPlace(place)}
                              className="px-4 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                            >
                              <div className="text-sm font-medium text-black">
                                {place.display_name.split(",")[0]}
                              </div>
                              <div className="text-xs text-gray-500">
                                {place.display_name}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    <div className="text-xs text-gray-500">
                      Coordinates: {routeRequest.destination.lat.toFixed(6)},{" "}
                      {routeRequest.destination.lon.toFixed(6)}
                    </div>
                  </div>
                </div>

                {/* Algorithm - Fixed to Enhanced DFS */}
                <div>
                  <label className="block text-sm font-medium text-black mb-2">
                    Algorithm
                  </label>
                  <input
                    type="text"
                    value="Enhanced DFS"
                    disabled
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-600 cursor-not-allowed"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Using Dijkstra algorithm for optimal routing
                  </p>
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

        {/* Route Results */}
        {routeResults &&
          selectedRoute &&
          routeResults.results[selectedRoute]?.success && (
            <div className="mt-6 space-y-4">
              {/* Route Summary */}
              <div className="bg-white rounded-lg shadow-sm p-4">
                <h3 className="font-semibold text-black mb-3">
                  📊 Route Summary (Enhanced DFS)
                </h3>
                {routeResults.results[selectedRoute]?.route && (
                  <div className="space-y-2 text-sm text-black">
                    <div className="flex justify-between">
                      <span>⏱️ Total Time:</span>
                      <span className="font-medium">
                        {formatTime(
                          routeResults.results[selectedRoute]!.route!.summary
                            .total_time_minutes
                        )}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>💰 Total Cost:</span>
                      <span className="font-medium">
                        {formatCost(
                          routeResults.results[selectedRoute]!.route!.summary
                            .total_cost
                        )}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>📏 Distance:</span>
                      <span className="font-medium">
                        {routeResults.results[
                          selectedRoute
                        ]!.route!.summary.total_distance_km.toFixed(2)}{" "}
                        km
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>🔄 Transfers:</span>
                      <span className="font-medium">
                        {
                          routeResults.results[selectedRoute]!.route!.summary
                            .num_transfers
                        }
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>🚌 Segments:</span>
                      <span className="font-medium">
                        {
                          routeResults.results[selectedRoute]!.route!.segments
                            .length
                        }
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Route Details */}
              <div className="bg-white rounded-lg shadow-sm p-4">
                <h3 className="font-semibold text-black mb-3">
                  🚌 Route Details
                </h3>
                {routeResults.results[selectedRoute]?.route && (
                  <div className="space-y-3">
                    {routeResults.results[selectedRoute]!.route!.segments.map(
                      (segment, index) => (
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
                                <> • 📏 {segment.distance_km.toFixed(2)} km</>
                              )}
                              {segment.cost > 0 && (
                                <> • 💰 {formatCost(segment.cost)}</>
                              )}
                            </div>
                          </div>
                        </div>
                      )
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
      </div>
    </div>
  );
}
