import { NextRequest, NextResponse } from "next/server";

// Nominatim (OpenStreetMap) -- geocoding gratis, tanpa API key. Dulu file ini
// pakai Google Places Text Search, tapi API key-nya sudah tidak valid
// ("The provided API key is invalid") dan ter-hardcode di source code.
// Nominatim kebetulan sudah cocok dgn interface OSMPlace di bawah tanpa
// transformasi tambahan (place_id, lat, lon, display_name -- sama persis).
const NOMINATIM_BASE = "https://nominatim.openstreetmap.org/search";
// Nominatim mewajibkan User-Agent yang jelas (kebijakan pemakaian mereka),
// bukan header browser generik.
const NOMINATIM_USER_AGENT = "routing-transportation-v2/1.0";
const PALEMBANG_VIEWBOX = "104.55,-3.15,104.90,-2.85"; // min_lon,min_lat,max_lon,max_lat

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

interface NominatimResult {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
}

interface OSMPlace {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const query = searchParams.get("q");

    if (!query || query.trim().length < 3) {
      return NextResponse.json([], { status: 200 });
    }

    const searchQuery = encodeURIComponent(query.trim() + ", Palembang");
    const url =
      `${NOMINATIM_BASE}?q=${searchQuery}&format=json&limit=5` +
      `&countrycodes=id&viewbox=${PALEMBANG_VIEWBOX}&accept-language=id`;

    const response = await fetch(url, {
      headers: { "User-Agent": NOMINATIM_USER_AGENT },
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => "Unknown error");
      return NextResponse.json(
        { error: "Failed to fetch places", details: `HTTP ${response.status}: ${errorText}` },
        { status: response.status }
      );
    }

    const results = (await response.json()) as NominatimResult[];

    const places: OSMPlace[] = results.map((r) => ({
      place_id: r.place_id,
      display_name: r.display_name,
      lat: r.lat,
      lon: r.lon,
    }));

    return NextResponse.json(places, {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET",
      },
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
    return NextResponse.json(
      { error: "Internal server error", details: errorMessage },
      { status: 500 }
    );
  }
}
