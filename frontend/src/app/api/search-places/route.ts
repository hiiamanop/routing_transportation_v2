import { NextRequest, NextResponse } from "next/server";

// Palembang bounding box (south, west, north, east)
const PALEMBANG_BOUNDS = "-3.2,104.5,-2.8,105.0";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const query = searchParams.get("q");

  if (!query || query.length < 3) {
    return NextResponse.json([]);
  }

  try {
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
      query
    )}&bounded=1&viewbox=${PALEMBANG_BOUNDS}&limit=5&countrycodes=id`;

    const response = await fetch(url, {
      headers: {
        "User-Agent": "PalembangTransportRouting/1.0",
      },
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch places" },
        { status: response.status }
      );
    }

    const data = await response.json();

    // Map response to our format
    const places = data.map((place: {
      place_id: number;
      display_name: string;
      lat: string;
      lon: string;
    }) => ({
      place_id: place.place_id,
      display_name: place.display_name,
      lat: place.lat,
      lon: place.lon,
    }));

    return NextResponse.json(places);
  } catch (error) {
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

