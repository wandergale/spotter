"""
route_service.py
~~~~~~~~~~~~~~~~
Handles geocoding (Nominatim/OpenStreetMap) and routing (OSRM) for the ELD
trip planner.  Both APIs are completely free with no API key required.

Nominatim ToS: https://operations.osmfoundation.org/policies/nominatim/
  — Requires a meaningful User-Agent header.
  — Rate limit: max 1 request/second (enforced by time.sleep between calls).

OSRM public demo: http://router.project-osrm.org
  — Free for low-volume use.  Timeout set to 30s to avoid Render 60s limit.
"""

import time
import logging
from dataclasses import dataclass

import requests
from django.conf import settings
from django.db import OperationalError

logger = logging.getLogger(__name__)

NOMINATIM_BASE = "https://nominatim.openstreetmap.org/search"
OSRM_BASE = "http://router.project-osrm.org/route/v1/driving"

METERS_TO_MILES = 0.000621371
SECONDS_TO_HOURS = 1 / 3600


class RouteServiceError(Exception):
    """Raised when an external geocoding or routing API call fails."""


@dataclass
class Coordinates:
    lat: float
    lon: float
    display_name: str


@dataclass
class RouteSegment:
    origin: Coordinates
    destination: Coordinates
    distance_miles: float
    duration_hours: float
    # GeoJSON LineString geometry: {"type": "LineString", "coordinates": [[lon, lat], ...]}
    geometry: dict


class RouteService:
    """Wraps Nominatim geocoding and OSRM routing into a clean service interface."""

    def __init__(self):
        self.user_agent = getattr(settings, 'NOMINATIM_USER_AGENT', 'eld-trip-planner/1.0')
        self.timeout = getattr(settings, 'EXTERNAL_API_TIMEOUT', 30)
        self._headers = {'User-Agent': self.user_agent}

    # ── Geocoding ─────────────────────────────────────────────────────────────

    def geocode(self, location: str) -> Coordinates:
        """
        Convert a human-readable location string into lat/lng coordinates.
        Checks the DB cache first to avoid Nominatim rate limits across workers.
        Falls back to Nominatim with exponential backoff on 429 errors.
        """
        from trips.models import GeocodingCache

        cache_key = location.strip().lower()

        # Check DB cache (shared across all Gunicorn workers)
        try:
            cached = GeocodingCache.objects.get(query=cache_key)
            logger.info("Geocoding cache hit for '%s'", location)
            return Coordinates(
                lat=cached.lat,
                lon=cached.lon,
                display_name=cached.display_name,
            )
        except GeocodingCache.DoesNotExist:
            pass
        except OperationalError:
            # Table may not exist yet (first deploy before migrate)
            logger.warning("GeocodingCache table not available, skipping cache lookup")

        params = {
            'q': location,
            'format': 'json',
            'limit': 1,
            'addressdetails': 0,
        }

        # Retry with exponential backoff: 1s, 2s, 4s
        last_exc = None
        for attempt in range(3):
            if attempt > 0:
                wait = 2 ** attempt
                logger.warning("Nominatim 429 for '%s', retrying in %ds (attempt %d/3)", location, wait, attempt + 1)
                time.sleep(wait)
            try:
                resp = requests.get(
                    NOMINATIM_BASE,
                    params=params,
                    headers=self._headers,
                    timeout=self.timeout,
                )
                if resp.status_code == 429:
                    last_exc = requests.HTTPError(f"429 Too Many Requests", response=resp)
                    continue
                resp.raise_for_status()
                results = resp.json()
                break
            except requests.RequestException as exc:
                last_exc = exc
                if hasattr(exc, 'response') and getattr(exc.response, 'status_code', None) == 429:
                    continue
                raise RouteServiceError(f"Geocoding failed for '{location}': {exc}") from exc
        else:
            raise RouteServiceError(f"Geocoding failed for '{location}': {last_exc}") from last_exc

        if not results:
            raise RouteServiceError(
                f"Could not geocode location: '{location}'. "
                "Please provide a more specific address or city name."
            )

        best = results[0]
        coords = Coordinates(
            lat=float(best['lat']),
            lon=float(best['lon']),
            display_name=best.get('display_name', location),
        )

        # Save to DB cache
        try:
            GeocodingCache.objects.get_or_create(
                query=cache_key,
                defaults={'lat': coords.lat, 'lon': coords.lon, 'display_name': coords.display_name},
            )
        except OperationalError:
            logger.warning("GeocodingCache table not available, skipping cache write")

        return coords

    def geocode_locations(self, *locations: str) -> list[Coordinates]:
        """
        Geocode multiple location strings.
        Cache hits are free; only uncached locations sleep to respect Nominatim's 1 req/sec.
        """
        from trips.models import GeocodingCache

        # Bulk-check cache for all locations at once
        cache_keys = [loc.strip().lower() for loc in locations]
        try:
            cached_map = {
                c.query: c for c in GeocodingCache.objects.filter(query__in=cache_keys)
            }
        except OperationalError:
            cached_map = {}

        coords = []
        needs_api_call = False
        for loc, key in zip(locations, cache_keys):
            if key in cached_map:
                c = cached_map[key]
                coords.append(Coordinates(lat=c.lat, lon=c.lon, display_name=c.display_name))
                logger.info("Geocoding cache hit for '%s'", loc)
            else:
                if needs_api_call:
                    time.sleep(1)  # Nominatim 1 req/sec — only between real API calls
                coords.append(self.geocode(loc))
                needs_api_call = True
        return coords

    # ── Routing ───────────────────────────────────────────────────────────────

    def get_segment(self, origin: Coordinates, destination: Coordinates) -> RouteSegment:
        """
        Get driving route between two coordinates using the OSRM public API.
        Returns a RouteSegment with distance (miles), duration (hours), and
        GeoJSON LineString geometry.
        """
        coord_str = f"{origin.lon},{origin.lat};{destination.lon},{destination.lat}"
        url = f"{OSRM_BASE}/{coord_str}"
        params = {
            'overview': 'full',
            'geometries': 'geojson',
            'steps': 'false',
        }

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise RouteServiceError(
                f"Routing failed between '{origin.display_name}' and "
                f"'{destination.display_name}': {exc}"
            ) from exc

        if data.get('code') != 'Ok' or not data.get('routes'):
            raise RouteServiceError(
                f"OSRM returned no route between '{origin.display_name}' "
                f"and '{destination.display_name}'. Code: {data.get('code')}"
            )

        route = data['routes'][0]
        distance_miles = route['distance'] * METERS_TO_MILES
        duration_hours = route['duration'] * SECONDS_TO_HOURS
        geometry = route['geometry']  # GeoJSON LineString

        return RouteSegment(
            origin=origin,
            destination=destination,
            distance_miles=round(distance_miles, 2),
            duration_hours=round(duration_hours, 3),
            geometry=geometry,
        )

    def get_route(self, coords: list[Coordinates]) -> dict:
        """
        Get the full route for current → pickup → dropoff.
        Returns a dict with:
          - 'route': dict with geometry (merged GeoJSON), total_distance_miles,
                     total_duration_hours
          - 'segments': list of RouteSegment for HOS simulation
        """
        if len(coords) < 2:
            raise RouteServiceError("At least two coordinates are required for routing.")

        segments = []
        for i in range(len(coords) - 1):
            if i > 0:
                time.sleep(0.5)  # small courtesy delay between OSRM calls
            seg = self.get_segment(coords[i], coords[i + 1])
            segments.append(seg)
            logger.info(
                "Segment %d: %.1f mi / %.2f hr  (%s → %s)",
                i + 1,
                seg.distance_miles,
                seg.duration_hours,
                coords[i].display_name[:30],
                coords[i + 1].display_name[:30],
            )

        total_distance = sum(s.distance_miles for s in segments)
        total_duration = sum(s.duration_hours for s in segments)
        merged_geometry = self._merge_geometries(segments)

        return {
            'route': {
                'geometry': merged_geometry,
                'total_distance_miles': round(total_distance, 2),
                'total_duration_hours': round(total_duration, 3),
            },
            'segments': segments,
            # Coordinate objects for reference by HOS calculator
            'coords': coords,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _merge_geometries(self, segments: list[RouteSegment]) -> dict:
        """
        Merge multiple GeoJSON LineString geometries into a single LineString
        by concatenating their coordinate arrays (de-duplicating junction points).
        """
        if not segments:
            return {'type': 'LineString', 'coordinates': []}

        all_coords = list(segments[0].geometry['coordinates'])
        for seg in segments[1:]:
            # Skip the first coordinate of subsequent segments to avoid duplicating
            # the shared waypoint (e.g., pickup location appears as last coord of
            # segment 1 and first coord of segment 2).
            all_coords.extend(seg.geometry['coordinates'][1:])

        return {'type': 'LineString', 'coordinates': all_coords}
