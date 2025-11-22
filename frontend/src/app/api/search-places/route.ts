import { NextRequest, NextResponse } from "next/server";

// Google Maps API Key
const GOOGLE_MAPS_API_KEY = "AIzaSyCnfiklOOhFtx8n6-J8OIDSAj0Hy_wAgd8";

// Palembang location (for biasing results)
const PALEMBANG_LOCATION = "-2.9911,104.7574"; // lat,lng

// Force dynamic rendering for API routes
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

interface GooglePlaceResult {
  place_id: string;
  name: string;
  formatted_address: string;
  geometry: {
    location: {
      lat: number;
      lng: number;
    };
  };
}

interface GoogleTextSearchResponse {
  results?: GooglePlaceResult[];
  status: string;
  error_message?: string;
}

interface OSMPlace {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
  google_place_id?: string;
}

// Get place details (lat, lng) from Google Places API
async function getPlaceDetails(
  placeId: string
): Promise<{ lat: number; lng: number; name: string } | null> {
  try {
    const url = `https://maps.googleapis.com/maps/api/place/details/json?place_id=${placeId}&fields=geometry,formatted_address,name&key=${GOOGLE_MAPS_API_KEY}`;

    const response = await fetch(url);

    if (!response.ok) {
      return null;
    }

    const data = (await response.json()) as {
      result?: {
        geometry: { location: { lat: number; lng: number } };
        formatted_address: string;
        name: string;
      };
      status: string;
      error_message?: string;
    };

    if (data.status === "OK" && data.result) {
      const location = data.result.geometry.location;
      return {
        lat: location.lat,
        lng: location.lng,
        name: data.result.formatted_address || data.result.name,
      };
    }

    return null;
  } catch {
    return null;
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const query = searchParams.get("q");

    if (!query || query.trim().length < 3) {
      return NextResponse.json([], { status: 200 });
    }

    // Use Places Text Search API instead of Autocomplete
    // This API is simpler and doesn't require Places API (New)
    // It uses Places API (legacy) which might be enabled by default
    const searchQuery = encodeURIComponent(query.trim() + " Palembang");
    const url = `https://maps.googleapis.com/maps/api/place/textsearch/json?query=${searchQuery}&key=${GOOGLE_MAPS_API_KEY}&language=id&region=id&location=${PALEMBANG_LOCATION}&radius=15000`;

    let response: Response;
    let data: GoogleTextSearchResponse;

    try {
      response = await fetch(url, {
        method: "GET",
        headers: {
          "Accept": "application/json",
        },
      });
    } catch (fetchError) {
      return NextResponse.json(
        {
          error: "Network error",
          details:
            fetchError instanceof Error
              ? fetchError.message
              : "Failed to connect to Google Places API",
        },
        { status: 500 }
      );
    }

    if (!response.ok) {
      const errorText = await response.text().catch(() => "Unknown error");
      
      // If 403, provide helpful error message
      if (response.status === 403) {
        return NextResponse.json(
          {
            error: "API access denied",
            details:
              "Google Places API access denied. Please ensure:\n" +
              "1. Places API (Legacy) is enabled in Google Cloud Console\n" +
              "2. API key has proper permissions\n" +
              "3. Billing is enabled for your Google Cloud project",
            status_code: response.status,
          },
          { status: 403 }
        );
      }

      return NextResponse.json(
        {
          error: "Failed to fetch places",
          details: `HTTP ${response.status}: ${errorText}`,
        },
        { status: response.status }
      );
    }

    try {
      data = (await response.json()) as GoogleTextSearchResponse;
    } catch (parseError) {
      return NextResponse.json(
        {
          error: "Invalid response format",
          details:
            parseError instanceof Error
              ? parseError.message
              : "Failed to parse Google Places API response",
        },
        { status: 500 }
      );
    }

    // Handle different status codes from Google Places API
    if (data.status === "REQUEST_DENIED") {
      return NextResponse.json(
        {
          error: "API request denied",
          details:
            data.error_message ||
            "Places API (Legacy) is not enabled or API key is invalid. " +
            "Please enable 'Places API' in Google Cloud Console > APIs & Services > Library",
        },
        { status: 403 }
      );
    }

    if (data.status === "INVALID_REQUEST") {
      return NextResponse.json(
        {
          error: "Invalid request",
          details: data.error_message || "Check request parameters",
        },
        { status: 400 }
      );
    }

    if (data.status === "OVER_QUERY_LIMIT") {
      return NextResponse.json(
        {
          error: "Query limit exceeded",
          details: "API quota exceeded. Please try again later.",
        },
        { status: 429 }
      );
    }

    if (data.status === "ZERO_RESULTS") {
      return NextResponse.json([], { status: 200 });
    }

    if (data.status !== "OK") {
      return NextResponse.json(
        {
          error: "Failed to fetch places",
          details: `Google Places API status: ${data.status}. ${data.error_message || ""}`,
        },
        { status: 500 }
      );
    }

    // If no results, return empty array
    if (!data.results || data.results.length === 0) {
      return NextResponse.json([], { status: 200 });
    }

    // Map Google Places Text Search response to our format
    const places: OSMPlace[] = data.results.slice(0, 5).map((result) => {
      // Convert place_id to number for compatibility
      const numericId = parseInt(
        result.place_id.replace(/\D/g, "").slice(0, 10) || "0",
        10
      );

      return {
        place_id: numericId,
        display_name: result.name + ", " + result.formatted_address,
        lat: result.geometry.location.lat.toString(),
        lon: result.geometry.location.lng.toString(),
        google_place_id: result.place_id,
      };
    });

    return NextResponse.json(places, {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET",
      },
    });
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error occurred";
    const errorStack = error instanceof Error ? error.stack : undefined;

    return NextResponse.json(
      {
        error: "Internal server error",
        details: errorMessage,
        ...(process.env.NODE_ENV === "development" && { stack: errorStack }),
      },
      { status: 500 }
    );
  }
}

// POST endpoint to get place details (lat, lng) from Google place_id
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { place_id } = body as { place_id?: string };

    if (!place_id) {
      return NextResponse.json(
        { error: "place_id is required" },
        { status: 400 }
      );
    }

    const details = await getPlaceDetails(place_id);

    if (!details) {
      return NextResponse.json(
        { error: "Failed to fetch place details" },
        { status: 404 }
      );
    }

    return NextResponse.json(details, {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error occurred";
    return NextResponse.json(
      {
        error: "Internal server error",
        details: errorMessage,
      },
      { status: 500 }
    );
  }
}
