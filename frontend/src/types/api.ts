// ── Request ────────────────────────────────────────────────────────────────────

export interface TripRequest {
  current_location: string;
  pickup_location: string;
  dropoff_location: string;
  current_cycle_used: number;
}

// ── Response ───────────────────────────────────────────────────────────────────

export interface GeoJSONLineString {
  type: 'LineString';
  coordinates: [number, number][]; // [lon, lat] pairs
}

export interface RouteInfo {
  geometry: GeoJSONLineString;
  total_distance_miles: number;
  total_duration_hours: number;
}

export interface StopLocation {
  lat: number;
  lng: number;
  name: string;
}

export type StopType = 'pickup' | 'dropoff' | 'rest' | 'break' | 'fuel';

export interface Stop {
  type: StopType;
  location: StopLocation;
  arrival_time: string;   // ISO 8601
  departure_time: string; // ISO 8601
  duration_hours: number;
}

export type HosStatus = 'OFF' | 'SB' | 'D' | 'ON';

export interface ELDEntry {
  status: HosStatus;
  start_hour: number; // 0.0 – 24.0
  end_hour: number;   // 0.0 – 24.0
  location: string;
}

export interface DaySummary {
  off_duty_hours: number;
  sleeper_berth_hours: number;
  driving_hours: number;
  on_duty_hours: number;
}

export interface DailyLog {
  date: string; // "YYYY-MM-DD"
  entries: ELDEntry[];
  summary: DaySummary;
}

export interface TripResponse {
  route: RouteInfo;
  stops: Stop[];
  daily_logs: DailyLog[];
  total_trip_days: number;
  total_driving_hours: number;
}

// ── Form state ─────────────────────────────────────────────────────────────────

export interface FormValues {
  current_location: string;
  pickup_location: string;
  dropoff_location: string;
  current_cycle_used: string; // string so the input is controlled
}

export interface FormErrors {
  current_location?: string;
  pickup_location?: string;
  dropoff_location?: string;
  current_cycle_used?: string;
}
