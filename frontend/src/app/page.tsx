"use client";

import { useState, useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import axios from "axios";
import {
  SearchIcon,
  SwapIcon,
  ClockIcon,
  AlertIcon,
  CarIcon,
  LoaderIcon,
  NavigationIcon,
  ChevronDownIcon,
  SlidersIcon,
  MapIcon,
  modeIcon,
  modeLabel,
  modeColor,
} from "./components/icons";

// Dynamically import Map component to avoid SSR issues
const MapComponent = dynamic(() => import("./components/MapComponent"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-[var(--gmaps-surface-hover)] text-sm text-[var(--gmaps-text-secondary)]">
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
  // Nama halte perantara yang dilewati (khusus segmen naik kendaraan yang
  // sudah digabung dari beberapa hop backend) -- utk dropdown "lihat halte
  // yang dilewati" ala Google Maps.
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

interface Alternative {
  label: string;
  optimized_for: string;
  // Atribut X_ij dalam satuan asli (menit, rupiah, km, skor) -- dikirim
  // balik apa adanya saat responden memilih rute, jadi himpunan pilihan
  // terekam utuh, bukan cuma yang menang.
  attributes: Record<string, number>;
  route: Route;
}

interface AlternativesResponse {
  success: boolean;
  origin: { name: string; lat: number; lon: number };
  destination: { name: string; lat: number; lon: number };
  departure_time: string;
  alternatives: Alternative[];
  error?: string;
}

// Bentuk respons saat di luar jam operasional angkutan umum -- TIDAK punya
// key "alternatives" seperti AlternativesResponse biasa, jadi harus dicek
// terpisah sebelum mengakses response.data.alternatives (kalau tidak,
// TypeError krn alternatives undefined, ketangkep di catch block sbg
// "Failed to get route" walau server sebenarnya menjawab 200 OK).
interface OutOfServiceResponse {
  success: true;
  public_transport_available: false;
  reason: string;
  private_vehicle: {
    distance_km: number;
    duration_minutes: number;
    assumed_speed_kmh: number;
    note: string;
  };
}

export default function Home() {
  // Helper function to get current time in GMT+7 (WIB)
  const getCurrentTimeGMT7 = (): string => {
    const now = new Date();
    // Convert to GMT+7 (WIB)
    const gmt7Offset = 7 * 60; // 7 hours in minutes
    const localOffset = now.getTimezoneOffset(); // Local timezone offset in minutes
    const wibTime = new Date(
      now.getTime() + (localOffset + gmt7Offset) * 60000
    );
    // Format as datetime-local string (YYYY-MM-DDTHH:mm)
    const year = wibTime.getFullYear();
    const month = String(wibTime.getMonth() + 1).padStart(2, "0");
    const day = String(wibTime.getDate()).padStart(2, "0");
    const hours = String(wibTime.getHours()).padStart(2, "0");
    const minutes = String(wibTime.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  };

  const [routeRequest, setRouteRequest] = useState<RouteRequest>({
    origin: { name: "", lat: 0, lon: 0 },
    destination: { name: "", lat: 0, lon: 0 },
    departure_time: getCurrentTimeGMT7(),
  });

  const [alternativesResponse, setAlternativesResponse] =
    useState<AlternativesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [serviceInfo, setServiceInfo] = useState<OutOfServiceResponse | null>(
    null
  );
  const [selectedIndex, setSelectedIndex] = useState(0);
  // Pencatatan pilihan responden (data survei) -- terpisah dari state rute
  // supaya kegagalan merekam tidak pernah menghalangi tampilan rutenya.
  const [savingChoice, setSavingChoice] = useState(false);
  const [choiceSaved, setChoiceSaved] = useState(false);
  const [choiceError, setChoiceError] = useState(false);
  // Sequence segmen yg dropdown "halte yang dilewati"-nya sedang terbuka.
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const toggleStepExpanded = (sequence: number) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(sequence)) next.delete(sequence);
      else next.add(sequence);
      return next;
    });
  };

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

  // Route Next.js sendiri (search-places) & proxy ke Flask (lihat
  // next.config.ts rewrites) -- keduanya sama-sama di origin ini, jadi path
  // relatif saja. (Sebelumnya search-places hardcode ke port 3003 yang
  // sebenarnya tidak dipakai di manapun -- bug lama.)
  const SEARCH_API_BASE_URL = "/api";
  const ROUTE_API_BASE_URL = "/api";

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

  const handleSwapLocations = () => {
    setRouteRequest((prev) => ({
      ...prev,
      origin: prev.destination,
      destination: prev.origin,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setServiceInfo(null);
    setAlternativesResponse(null);
    setSelectedIndex(0);
    setExpandedSteps(new Set());
    setChoiceSaved(false);
    setChoiceError(false);

    try {
      // Convert datetime-local to ISO string with GMT+7 timezone
      // datetime-local input is already in local timezone, we assume it's GMT+7
      const departureTimeISO = routeRequest.departure_time
        ? `${routeRequest.departure_time}:00+07:00` // Add seconds and GMT+7 timezone
        : undefined;

      // Preferensi (opsional) dari halaman /preferensi -- kalau pengguna
      // belum pernah mengaturnya, tidak dikirim sama sekali (backend cuma
      // menambah opsi ke-4 "Sesuai Preferensi Saya" kalau field ini ada).
      let preferences: Record<string, number> | undefined;
      try {
        const stored = localStorage.getItem("transit_preferences_v1");
        if (stored) preferences = JSON.parse(stored);
      } catch {
        preferences = undefined;
      }

      const requestPayload = {
        origin: routeRequest.origin,
        destination: routeRequest.destination,
        departure_time: departureTimeISO,
        ...(preferences ? { preferences } : {}),
      };

      const response = await axios.post(
        `${ROUTE_API_BASE_URL}/route/alternatives`,
        requestPayload
      );

      // Di luar jam operasional: respons TIDAK punya key "alternatives"
      // (lihat OutOfServiceResponse) -- tangani terpisah sebelum menyentuh
      // response.data.alternatives, supaya tidak crash jadi "Failed to get route".
      if (response.data.public_transport_available === false) {
        setServiceInfo(response.data as OutOfServiceResponse);
        return;
      }

      setAlternativesResponse(response.data);

      if (!response.data.alternatives || response.data.alternatives.length === 0) {
        // Server menjawab 200 tapi tidak ada rute yang ditemukan (mis. asal/tujuan
        // tidak terhubung ke jaringan) -- tanpa ini, UI diam saja tanpa pesan apa pun.
        setError(
          response.data.error || "Rute tidak ditemukan antara lokasi asal dan tujuan."
        );
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

  const alternatives = alternativesResponse?.alternatives ?? [];
  const activeAlternative = alternatives[selectedIndex] ?? null;
  const activeRoute = activeAlternative?.route ?? null;

  // Rekam pilihan responden: himpunan alternatif yang ditawarkan beserta
  // atributnya + mana yang dipilih. Penilaian 1-5 di halaman /preferensi
  // saja tidak cukup utk mengestimasi parameter model pemilihan -- yang
  // dibutuhkan justru pasangan (himpunan pilihan -> yang dipilih) ini.
  const recordChoice = async () => {
    if (!alternativesResponse || alternatives.length === 0 || savingChoice) return;
    setSavingChoice(true);
    try {
      // ID responden anonim & tetap per browser, supaya beberapa perjalanan
      // dari orang yang sama bisa dikenali tanpa menyimpan identitas apa pun.
      let respondentId = localStorage.getItem("transit_respondent_v1");
      if (!respondentId) {
        respondentId = crypto.randomUUID();
        localStorage.setItem("transit_respondent_v1", respondentId);
      }

      let preferences: Record<string, number> | undefined;
      try {
        const stored = localStorage.getItem("transit_preferences_v1");
        if (stored) preferences = JSON.parse(stored);
      } catch {
        preferences = undefined;
      }

      await axios.post(`${ROUTE_API_BASE_URL}/choice`, {
        respondent_id: respondentId,
        ...(preferences ? { preferences } : {}),
        origin: alternativesResponse.origin,
        destination: alternativesResponse.destination,
        departure_time: alternativesResponse.departure_time,
        choice_set: alternatives.map((alt) => ({
          label: alt.label,
          optimized_for: alt.optimized_for,
          attributes: alt.attributes,
        })),
        chosen_index: selectedIndex,
      });
      setChoiceSaved(true);
    } catch {
      // Gagal merekam TIDAK boleh mengganggu perjalanan pengguna -- rutenya
      // tetap tampil; yang hilang cuma satu observasi survei.
      setChoiceError(true);
    } finally {
      setSavingChoice(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-white lg:h-screen lg:flex-row lg:overflow-hidden">
      {/* Left panel: search + directions, full-width & natural scroll on
          mobile, fixed-width & internally scrollable on desktop -- mirrors
          Google Maps' directions sidebar. */}
      <aside className="flex w-full flex-col border-b border-[var(--gmaps-border)] bg-white lg:h-full lg:w-[420px] lg:border-b-0 lg:border-r">
        <div className="flex items-center gap-3 px-4 py-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--gmaps-blue)] text-white">
            <NavigationIcon width={18} height={18} />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-base font-medium leading-tight text-[var(--gmaps-text)]">
              Palembang Transit Router
            </h1>
            <p className="truncate text-xs text-[var(--gmaps-text-secondary)]">
              Rute angkutan umum tercepat
            </p>
          </div>
          <Link
            href="/jaringan"
            title="Lihat peta jaringan"
            className="flex shrink-0 items-center gap-1.5 rounded-full border border-[var(--gmaps-border)] px-3 py-1.5 text-xs font-medium text-[var(--gmaps-text-secondary)] hover:bg-[var(--gmaps-surface-hover)] hover:text-[var(--gmaps-blue)]"
          >
            <MapIcon width={14} height={14} />
            Jaringan
          </Link>
          <Link
            href="/preferensi"
            title="Atur preferensi saya"
            className="flex shrink-0 items-center gap-1.5 rounded-full border border-[var(--gmaps-border)] px-3 py-1.5 text-xs font-medium text-[var(--gmaps-text-secondary)] hover:bg-[var(--gmaps-surface-hover)] hover:text-[var(--gmaps-blue)]"
          >
            <SlidersIcon width={14} height={14} />
            Preferensi
          </Link>
        </div>

        <div className="gmaps-scroll lg:flex-1 lg:overflow-y-auto">
          <form onSubmit={handleSubmit} className="px-4 pb-4">
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1 space-y-2">
                {/* Origin with OSM Autocomplete */}
                <div className="relative" ref={originInputRef}>
                  <span className="pointer-events-none absolute left-3 top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full border-2 border-[var(--gmaps-green)] bg-white" />
                  <input
                    type="text"
                    placeholder="Choose origin..."
                    value={routeRequest.origin.name}
                    onChange={(e) => handleOriginChange(e.target.value)}
                    onFocus={() => {
                      if (originSuggestions.length > 0) {
                        setShowOriginSuggestions(true);
                      }
                    }}
                    className="w-full rounded-lg border border-[var(--gmaps-border)] bg-[var(--gmaps-surface-hover)] py-2.5 pl-9 pr-8 text-sm text-[var(--gmaps-text)] outline-none placeholder:text-[var(--gmaps-text-secondary)] focus:border-[var(--gmaps-blue)] focus:bg-white focus:ring-2 focus:ring-[var(--gmaps-blue-tint)]"
                    required
                  />
                  {originSearching && (
                    <LoaderIcon
                      width={16}
                      height={16}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--gmaps-text-secondary)]"
                    />
                  )}
                  {!originSearching &&
                    showOriginSuggestions &&
                    originSuggestions.length > 0 && (
                      <div className="gmaps-scroll absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-[var(--gmaps-border)] bg-white shadow-lg">
                        {originSuggestions.map((place) => (
                          <div
                            key={place.place_id}
                            onClick={() => selectOriginPlace(place)}
                            className="flex cursor-pointer items-start gap-2 border-b border-[var(--gmaps-border)] px-3 py-2 last:border-b-0 hover:bg-[var(--gmaps-surface-hover)]"
                          >
                            <NavigationIcon
                              width={14}
                              height={14}
                              className="mt-0.5 shrink-0 text-[var(--gmaps-text-secondary)]"
                            />
                            <div className="min-w-0">
                              <div className="truncate text-sm font-medium text-[var(--gmaps-text)]">
                                {place.display_name.split(",")[0]}
                              </div>
                              <div className="truncate text-xs text-[var(--gmaps-text-secondary)]">
                                {place.display_name}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                </div>

                {/* Destination with OSM Autocomplete */}
                <div className="relative" ref={destinationInputRef}>
                  <span className="pointer-events-none absolute left-3 top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-sm bg-[var(--gmaps-red)]" />
                  <input
                    type="text"
                    placeholder="Choose destination..."
                    value={routeRequest.destination.name}
                    onChange={(e) => handleDestinationChange(e.target.value)}
                    onFocus={() => {
                      if (destinationSuggestions.length > 0) {
                        setShowDestinationSuggestions(true);
                      }
                    }}
                    className="w-full rounded-lg border border-[var(--gmaps-border)] bg-[var(--gmaps-surface-hover)] py-2.5 pl-9 pr-8 text-sm text-[var(--gmaps-text)] outline-none placeholder:text-[var(--gmaps-text-secondary)] focus:border-[var(--gmaps-blue)] focus:bg-white focus:ring-2 focus:ring-[var(--gmaps-blue-tint)]"
                    required
                  />
                  {destinationSearching && (
                    <LoaderIcon
                      width={16}
                      height={16}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--gmaps-text-secondary)]"
                    />
                  )}
                  {!destinationSearching &&
                    showDestinationSuggestions &&
                    destinationSuggestions.length > 0 && (
                      <div className="gmaps-scroll absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-[var(--gmaps-border)] bg-white shadow-lg">
                        {destinationSuggestions.map((place) => (
                          <div
                            key={place.place_id}
                            onClick={() => selectDestinationPlace(place)}
                            className="flex cursor-pointer items-start gap-2 border-b border-[var(--gmaps-border)] px-3 py-2 last:border-b-0 hover:bg-[var(--gmaps-surface-hover)]"
                          >
                            <NavigationIcon
                              width={14}
                              height={14}
                              className="mt-0.5 shrink-0 text-[var(--gmaps-text-secondary)]"
                            />
                            <div className="min-w-0">
                              <div className="truncate text-sm font-medium text-[var(--gmaps-text)]">
                                {place.display_name.split(",")[0]}
                              </div>
                              <div className="truncate text-xs text-[var(--gmaps-text-secondary)]">
                                {place.display_name}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                </div>
              </div>

              <button
                type="button"
                onClick={handleSwapLocations}
                title="Swap origin & destination"
                className="mt-1 flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full border border-[var(--gmaps-border)] text-[var(--gmaps-text-secondary)] hover:bg-[var(--gmaps-surface-hover)] hover:text-[var(--gmaps-blue)]"
              >
                <SwapIcon width={16} height={16} />
              </button>
            </div>

            {/* Departure Time */}
            <div className="mt-3 flex items-center gap-2 rounded-lg border border-[var(--gmaps-border)] px-3 py-2">
              <ClockIcon
                width={18}
                height={18}
                className="shrink-0 text-[var(--gmaps-text-secondary)]"
              />
              <input
                type="datetime-local"
                value={routeRequest.departure_time}
                onChange={(e) =>
                  setRouteRequest((prev) => ({
                    ...prev,
                    departure_time: e.target.value,
                  }))
                }
                className="w-full min-w-0 flex-1 bg-transparent text-sm text-[var(--gmaps-text)] outline-none"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="mt-3 flex w-full cursor-pointer items-center justify-center gap-2 rounded-full bg-[var(--gmaps-blue)] py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--gmaps-blue-hover)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <>
                  <LoaderIcon width={16} height={16} />
                  Finding route...
                </>
              ) : (
                <>
                  <SearchIcon width={16} height={16} />
                  Find route
                </>
              )}
            </button>
          </form>

          {/* Error Display */}
          {error && (
            <div className="mx-4 mb-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-[var(--gmaps-red)]">
              <AlertIcon width={16} height={16} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Di luar jam operasional angkutan umum */}
          {serviceInfo && (
            <div className="mx-4 mb-4 space-y-1 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-900">
              <div className="flex items-start gap-2 font-medium">
                <CarIcon
                  width={16}
                  height={16}
                  className="mt-0.5 shrink-0 text-amber-700"
                />
                <span>{serviceInfo.reason}</span>
              </div>
              <p className="pl-6 text-xs text-amber-800">
                Estimasi kendaraan pribadi: {serviceInfo.private_vehicle.distance_km} km,{" "}
                {serviceInfo.private_vehicle.duration_minutes} menit (~
                {serviceInfo.private_vehicle.assumed_speed_kmh} km/jam)
              </p>
              <p className="pl-6 text-xs text-amber-700/80">
                {serviceInfo.private_vehicle.note}
              </p>
            </div>
          )}

          {/* Tab alternatif rute -- Tercepat/Termurah/Transfer paling sedikit,
              ditambah "Sesuai Preferensi Saya" kalau preferensi sudah diatur. */}
          {alternatives.length > 1 && (
            <div className="flex gap-1.5 overflow-x-auto px-4 pb-3">
              {alternatives.map((alt, index) => (
                <button
                  key={`${alt.optimized_for}-${index}`}
                  type="button"
                  onClick={() => setSelectedIndex(index)}
                  className={`shrink-0 whitespace-nowrap rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                    index === selectedIndex
                      ? "border-[var(--gmaps-blue)] bg-[var(--gmaps-blue-tint)] text-[var(--gmaps-blue-hover)]"
                      : "border-[var(--gmaps-border)] text-[var(--gmaps-text-secondary)] hover:bg-[var(--gmaps-surface-hover)]"
                  }`}
                >
                  {alt.label}
                </button>
              ))}
            </div>
          )}

          {/* Route Results -- directions-list style, like Google Maps */}
          {activeRoute && (
            <div className="border-t border-[var(--gmaps-border)]">
              <div className="px-4 py-4">
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-medium text-[var(--gmaps-text)]">
                    {formatTime(activeRoute.summary.total_time_minutes)}
                  </span>
                  <span className="text-sm text-[var(--gmaps-text-secondary)]">
                    · {activeRoute.summary.total_distance_km.toFixed(2)} km
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <span className="rounded-full bg-[var(--gmaps-surface-hover)] px-2.5 py-1 text-xs text-[var(--gmaps-text-secondary)]">
                    {formatCost(activeRoute.summary.total_cost)}
                  </span>
                  <span className="rounded-full bg-[var(--gmaps-surface-hover)] px-2.5 py-1 text-xs text-[var(--gmaps-text-secondary)]">
                    {activeRoute.summary.num_transfers} transfer
                  </span>
                </div>

                {/* Perekaman pilihan responden. Tombol eksplisit, BUKAN
                    sekadar klik tab: berpindah tab itu perilaku menjelajah,
                    sedangkan yang perlu direkam adalah keputusan akhir. */}
                <div className="mt-3">
                  {choiceSaved ? (
                    <p className="text-xs text-[var(--gmaps-text-secondary)]">
                      Terima kasih, pilihan Anda sudah tercatat untuk penelitian ini.
                    </p>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={recordChoice}
                        disabled={savingChoice}
                        className="w-full rounded-full bg-[var(--gmaps-blue)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--gmaps-blue-hover)] disabled:opacity-60"
                      >
                        {savingChoice ? "Menyimpan..." : "Saya pilih rute ini"}
                      </button>
                      <p className="mt-1.5 text-[11px] leading-snug text-[var(--gmaps-text-secondary)]">
                        Pilihan Anda dicatat secara anonim untuk penelitian
                        pemilihan moda. Tidak ada identitas pribadi yang disimpan.
                      </p>
                      {choiceError && (
                        <p className="mt-1 text-[11px] text-[var(--gmaps-red)]">
                          Pilihan gagal dicatat, tapi rute Anda tetap bisa dipakai.
                        </p>
                      )}
                    </>
                  )}
                </div>

                {alternativesResponse?.departure_time && (
                  <div className="mt-3 rounded-lg border border-[var(--gmaps-blue-tint)] bg-[var(--gmaps-blue-tint)] px-3 py-2">
                    <div className="mb-1 flex items-center gap-1.5 text-xs font-medium text-[var(--gmaps-blue-hover)]">
                      <ClockIcon width={13} height={13} />
                      Departure Time
                    </div>
                    <div className="text-sm text-[var(--gmaps-text)]">
                      {new Date(
                        alternativesResponse.departure_time
                      ).toLocaleString("id-ID", {
                        timeZone: "Asia/Jakarta",
                        year: "numeric",
                        month: "2-digit",
                        day: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                        hour12: false,
                      })}
                    </div>
                    {(() => {
                      const hour = new Date(
                        alternativesResponse.departure_time
                      ).getHours();
                      let phase = "";
                      let color = "";
                      if (6 <= hour && hour <= 9) {
                        phase = "Peak Hour - Pagi (06:00-09:00)";
                        color = "text-orange-700 bg-orange-50";
                      } else if (12 <= hour && hour <= 14) {
                        phase = "Peak Hour - Siang (12:00-14:00)";
                        color = "text-orange-700 bg-orange-50";
                      } else if (17 <= hour && hour <= 19) {
                        phase = "Peak Hour - Sore (17:00-19:00)";
                        color = "text-orange-700 bg-orange-50";
                      } else {
                        phase = "Normal Hour";
                        color = "text-green-700 bg-green-50";
                      }
                      return (
                        <div
                          className={`mt-1 inline-block rounded px-2 py-0.5 text-xs ${color}`}
                        >
                          {phase}
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>

              {/* Steps timeline */}
              <div className="gmaps-scroll relative max-h-[420px] overflow-y-auto px-4 pb-4">
                {activeRoute.segments.length > 1 && (
                  <span className="absolute bottom-8 left-8 top-4 w-px bg-[var(--gmaps-border)]" />
                )}
                <div className="space-y-4">
                  {activeRoute.segments.map((segment, index) => (
                    <div key={index} className="flex gap-3">
                      <div
                        className="z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white"
                        style={{ backgroundColor: modeColor(segment.mode) }}
                      >
                        {modeIcon(segment.mode, { width: 16, height: 16 })}
                      </div>
                      <div className="min-w-0 flex-1 pt-0.5">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex min-w-0 items-center gap-2">
                            <span className="text-sm font-medium text-[var(--gmaps-text)]">
                              {modeLabel(segment.mode)}
                            </span>
                            {segment.route_name &&
                              segment.route_name !== "Unknown" && (
                                <span
                                  className="truncate rounded px-1.5 py-0.5 text-xs font-medium text-white"
                                  style={{
                                    backgroundColor: modeColor(segment.mode),
                                  }}
                                >
                                  {segment.route_name}
                                </span>
                              )}
                          </div>
                          <span className="shrink-0 text-xs text-[var(--gmaps-text-secondary)]">
                            {Math.round(segment.duration_minutes)} min
                          </span>
                        </div>
                        <p className="mt-0.5 truncate text-xs text-[var(--gmaps-text-secondary)]">
                          {segment.from_stop} → {segment.to_stop}
                        </p>
                        {(segment.distance_km > 0 || segment.cost > 0) && (
                          <p className="mt-0.5 text-xs text-[var(--gmaps-text-secondary)]">
                            {segment.distance_km > 0 &&
                              `${segment.distance_km.toFixed(2)} km`}
                            {segment.distance_km > 0 && segment.cost > 0 && " · "}
                            {segment.cost > 0 && formatCost(segment.cost)}
                          </p>
                        )}
                        {segment.via_stops && segment.via_stops.length > 0 && (
                          <div className="mt-1.5">
                            <button
                              type="button"
                              onClick={() => toggleStepExpanded(segment.sequence)}
                              className="flex cursor-pointer items-center gap-1 text-xs font-medium text-[var(--gmaps-blue)] hover:underline"
                            >
                              <ChevronDownIcon
                                width={14}
                                height={14}
                                className={`shrink-0 transition-transform ${
                                  expandedSteps.has(segment.sequence) ? "rotate-180" : ""
                                }`}
                              />
                              {expandedSteps.has(segment.sequence)
                                ? "Sembunyikan halte"
                                : `${segment.via_stops.length} halte dilewati`}
                            </button>
                            {expandedSteps.has(segment.sequence) && (
                              <ul className="mt-1.5 space-y-1 border-l border-dashed border-[var(--gmaps-border)] pl-3">
                                {segment.via_stops.map((stop, i) => (
                                  <li
                                    key={i}
                                    className="text-xs text-[var(--gmaps-text-secondary)]"
                                  >
                                    {stop}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Map -- fills remaining space, full height on desktop */}
      <div className="relative h-[50vh] w-full lg:h-full lg:flex-1">
        <MapComponent
          activeRoute={activeRoute}
          routeRequest={routeRequest}
        />
      </div>
    </div>
  );
}
