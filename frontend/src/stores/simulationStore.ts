import { create } from 'zustand';
import type { Scooter, Station, SimulationStatus, Metrics, ScooterGroupInfo } from '../types/simulation';

interface SimulationState {
  // Connection status
  isConnected: boolean;

  // Simulation lifecycle
  status: SimulationStatus;
  simulationTime: number;
  tick: number;
  speed: number;

  // Grid state
  gridWidth: number;
  gridHeight: number;
  scooters: Scooter[];
  stations: Station[];
  scooterGroups: ScooterGroupInfo[];

  // Metrics
  metrics: Metrics;

  // UI state
  selectedStationId: string | null;

  // Actions
  setConnected: (connected: boolean) => void;
  setStatus: (status: SimulationStatus) => void;
  setSpeed: (speed: number) => void;
  setSelectedStationId: (stationId: string | null) => void;
  updateState: (state: Partial<SimulationState>) => void;
  updateFromServer: (data: any) => void;
  reset: () => void;
}

const initialMetrics: Metrics = {
  total_swaps: 0,
  total_misses: 0,
  miss_rate: 0,
  no_battery_misses: 0,
  partial_charge_misses: 0,
  misses_per_station: {},
  swaps_per_station: {},
};

export const useSimulationStore = create<SimulationState>((set) => ({
  // Initial state
  isConnected: false,
  status: 'IDLE',
  simulationTime: 0,
  tick: 0,
  speed: 1,
  gridWidth: 100,
  gridHeight: 100,
  scooters: [],
  stations: [],
  scooterGroups: [],
  metrics: initialMetrics,
  selectedStationId: null,

  // Actions
  setConnected: (connected) => set({ isConnected: connected }),

  setStatus: (status) => set({ status }),

  setSpeed: (speed) => set({ speed }),

  setSelectedStationId: (stationId) => set({ selectedStationId: stationId }),

  updateState: (state) => set((prev) => ({ ...prev, ...state })),

  updateFromServer: (data) => set({
    simulationTime: data.simulation_time ?? data.current_time ?? 0,
    tick: data.tick ?? 0,
    status: data.status ?? 'IDLE',
    gridWidth: data.grid_width ?? 100,
    gridHeight: data.grid_height ?? 100,
    scooters: data.scooters ?? [],
    stations: data.stations ?? [],
    scooterGroups: data.scooter_groups ?? [],
    metrics: { ...initialMetrics, ...(data.metrics ?? {}) },
  }),

  reset: () => set({
    status: 'IDLE',
    simulationTime: 0,
    tick: 0,
    scooters: [],
    stations: [],
    scooterGroups: [],
    metrics: initialMetrics,
    selectedStationId: null,
  }),
}));
