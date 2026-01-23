// API client for REST endpoints

import type { StationSwapEvents } from '../types/simulation';

const API_BASE = '/api/v1';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Configuration API
export const configApi = {
  get: () => fetchJson<any>('/config/'),

  set: (config: any) => fetchJson<any>('/config/', {
    method: 'PUT',
    body: JSON.stringify(config),
  }),

  validate: (config: any) => fetchJson<{ valid: boolean; errors: string[] }>('/config/validate', {
    method: 'POST',
    body: JSON.stringify(config),
  }),
};

// Simulation control API
export const simulationApi = {
  getStatus: () => fetchJson<any>('/simulation/status'),

  getSnapshot: () => fetchJson<any>('/simulation/snapshot'),

  start: () => fetchJson<any>('/simulation/start', { method: 'POST' }),

  pause: () => fetchJson<any>('/simulation/pause', { method: 'POST' }),

  resume: () => fetchJson<any>('/simulation/resume', { method: 'POST' }),

  stop: () => fetchJson<any>('/simulation/stop', { method: 'POST' }),

  reset: () => fetchJson<any>('/simulation/reset', { method: 'POST' }),

  setSpeed: (speed: number) => fetchJson<any>('/simulation/speed', {
    method: 'PATCH',
    body: JSON.stringify({ speed_multiplier: speed }),
  }),

  step: () => fetchJson<any>('/simulation/step', { method: 'POST' }),
};

// Metrics API
export const metricsApi = {
  getCurrent: () => fetchJson<any>('/metrics/current'),

  getSummary: () => fetchJson<any>('/metrics/summary'),

  getStationSwaps: (
    stationId: string,
    params?: {
      limit?: number;
      offset?: number;
      sort_by?: 'battery' | 'time';
      order?: 'asc' | 'desc';
      since?: number;
    }
  ) => {
    const searchParams = new URLSearchParams();
    if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
    if (params?.offset !== undefined) searchParams.set('offset', String(params.offset));
    if (params?.sort_by) searchParams.set('sort_by', params.sort_by);
    if (params?.order) searchParams.set('order', params.order);
    if (params?.since !== undefined) searchParams.set('since', String(params.since));
    const query = searchParams.toString();
    const suffix = query ? `?${query}` : '';
    return fetchJson<StationSwapEvents>(`/metrics/stations/${encodeURIComponent(stationId)}/swaps${suffix}`);
  },
};
