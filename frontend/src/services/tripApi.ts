import axios from 'axios';
import type { TripRequest, TripResponse } from '../types/api';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

const client = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120_000, // 2 min — OSRM + Nominatim can be slow on cold start
});

export async function calculateTrip(payload: TripRequest): Promise<TripResponse> {
  const { data } = await client.post<TripResponse>('/api/trip/calculate/', payload);
  return data;
}

export type ApiError = {
  message: string;
  status?: number;
};

export function parseApiError(err: unknown): ApiError {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    const serverMsg =
      err.response?.data?.error ??
      err.response?.data?.detail ??
      Object.values(err.response?.data ?? {})
        .flat()
        .join(' ');

    if (status === 400) return { message: serverMsg || 'Invalid request. Please check your inputs.', status };
    if (status === 502 || status === 503) return { message: 'Could not reach the routing service. Please try again in a moment.', status };
    if (err.code === 'ECONNABORTED') return { message: 'The request timed out. The route may be too complex — please try again.' };
    return { message: serverMsg || `Server error (${status ?? 'unknown'}).`, status };
  }
  return { message: 'An unexpected error occurred.' };
}
