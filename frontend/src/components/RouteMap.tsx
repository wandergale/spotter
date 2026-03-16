import { useEffect } from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import MapIcon from '@mui/icons-material/Map';
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import type { TripResponse, Stop, StopType } from '../types/api';

// Fix Leaflet's default icon broken by Vite/webpack module bundling
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// ── Custom colored circle markers ──────────────────────────────────────────────

const STOP_COLORS: Record<StopType | 'start', { bg: string; border: string; label: string }> = {
  start:   { bg: '#4caf50', border: '#2e7d32', label: '▶ Start' },
  pickup:  { bg: '#1565c0', border: '#003c8f', label: '📦 Pickup' },
  dropoff: { bg: '#c62828', border: '#7f0000', label: '🏁 Dropoff' },
  rest:    { bg: '#6a1b9a', border: '#4a148c', label: '🛏 Rest' },
  break:   { bg: '#f57c00', border: '#e65100', label: '☕ Break' },
  fuel:    { bg: '#00838f', border: '#006064', label: '⛽ Fuel' },
};

function makeCircleIcon(color: string, border: string, size = 14): L.DivIcon {
  return L.divIcon({
    className: '',
    html: `<div style="
      width:${size}px;height:${size}px;border-radius:50%;
      background:${color};border:2.5px solid ${border};
      box-shadow:0 2px 6px rgba(0,0,0,0.35);
    "></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2 - 4],
  });
}

// ── Fit-bounds helper (must be a child of MapContainer) ────────────────────────

function FitBounds({ bounds }: { bounds: L.LatLngBoundsExpression }) {
  const map = useMap();
  useEffect(() => {
    map.fitBounds(bounds, { padding: [40, 40] });
  }, [map, bounds]);
  return null;
}

// ── Format helpers ─────────────────────────────────────────────────────────────

function fmt(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit', hour12: true,
  });
}

function fmtDur(h: number): string {
  const hrs = Math.floor(h);
  const mins = Math.round((h - hrs) * 60);
  return mins > 0 ? `${hrs}h ${mins}m` : `${hrs}h`;
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props { result: TripResponse }

export default function RouteMap({ result }: Props) {
  const { route, stops } = result;

  // Convert GeoJSON [lon, lat] → Leaflet [lat, lng]
  const polylinePositions: L.LatLngTuple[] = route.geometry.coordinates.map(
    ([lon, lat]) => [lat, lon]
  );

  // Compute bounds from the polyline
  const bounds = L.latLngBounds(polylinePositions);

  // Build map markers: "start" marker + all stops
  const startCoord = polylinePositions[0];

  return (
    <Card sx={{ overflow: 'hidden' }}>
      {/* Header */}
      <Box
        sx={{
          px: 2.5, py: 1.5,
          background: 'linear-gradient(90deg, #1565c0 0%, #1976d2 100%)',
          display: 'flex', alignItems: 'center', gap: 1,
        }}
      >
        <MapIcon sx={{ color: '#fff', fontSize: 20 }} />
        <Typography variant="subtitle1" sx={{ color: '#fff', fontWeight: 600 }}>
          Route Map
        </Typography>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.75)', ml: 'auto' }}>
          {result.route.total_distance_miles.toFixed(0)} mi
        </Typography>
      </Box>

      {/* Map */}
      <Box sx={{ height: { xs: 320, sm: 420, md: 480 } }}>
        <MapContainer
          style={{ height: '100%', width: '100%' }}
          center={[39.5, -98.35]} // geographic center of USA as default
          zoom={4}
          scrollWheelZoom={false}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <FitBounds bounds={bounds} />

          {/* Route polyline */}
          <Polyline
            positions={polylinePositions}
            pathOptions={{ color: '#1565c0', weight: 4, opacity: 0.85, dashArray: undefined }}
          />

          {/* Start marker */}
          {startCoord && (
            <Marker
              position={startCoord}
              icon={makeCircleIcon(STOP_COLORS.start.bg, STOP_COLORS.start.border, 16)}
            >
              <Popup>
                <strong>Start</strong><br />
                {stops.length > 0 ? stops[0]?.location.name : 'Current Location'}
              </Popup>
            </Marker>
          )}

          {/* Stop markers */}
          {stops.map((stop: Stop, i: number) => {
            const cfg = STOP_COLORS[stop.type] ?? STOP_COLORS.rest;
            return (
              <Marker
                key={i}
                position={[stop.location.lat, stop.location.lng]}
                icon={makeCircleIcon(cfg.bg, cfg.border, stop.type === 'pickup' || stop.type === 'dropoff' ? 18 : 13)}
              >
                <Popup minWidth={180}>
                  <Box>
                    <Typography fontWeight={700} fontSize={13}>{cfg.label}</Typography>
                    <Typography fontSize={12} color="text.secondary">{stop.location.name}</Typography>
                    <Box sx={{ mt: 0.5, borderTop: '1px solid #eee', pt: 0.5 }}>
                      <Typography fontSize={11}>Arrival: {fmt(stop.arrival_time)}</Typography>
                      <Typography fontSize={11}>Departure: {fmt(stop.departure_time)}</Typography>
                      <Typography fontSize={11} fontWeight={600}>Duration: {fmtDur(stop.duration_hours)}</Typography>
                    </Box>
                  </Box>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </Box>

      {/* Legend */}
      <CardContent sx={{ py: 1.5, px: 2.5 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5 }}>
          {(Object.entries(STOP_COLORS) as [string, { bg: string; label: string }][]).map(([key, val]) => (
            <Box key={key} sx={{ display: 'flex', alignItems: 'center', gap: 0.6 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: val.bg, flexShrink: 0 }} />
              <Typography variant="caption" color="text.secondary" textTransform="capitalize">
                {key}
              </Typography>
            </Box>
          ))}
        </Box>
      </CardContent>
    </Card>
  );
}
