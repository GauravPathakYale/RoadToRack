import { create } from 'zustand';
import type { Scooter, Station, SimulationStatus, Metrics } from '../types/simulation';

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

  // Metrics
  metrics: Metrics;

  // Actions
  setConnected: (connected: boolean) => void;
  setStatus: (status: SimulationStatus) => void;
  setSpeed: (speed: number) => void;
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
  metrics: initialMetrics,

  // Actions
  setConnected: (connected) => set({ isConnected: connected }),

  setStatus: (status) => set({ status }),

  setSpeed: (speed) => set({ speed }),

  updateState: (state) => set((prev) => ({ ...prev, ...state })),

  updateFromServer: (data) => set({
    simulationTime: data.simulation_time ?? data.current_time ?? 0,
    tick: data.tick ?? 0,
    status: data.status ?? 'IDLE',
    gridWidth: data.grid_width ?? 100,
    gridHeight: data.grid_height ?? 100,
    scooters: data.scooters ?? [],
    stations: data.stations ?? [],
    metrics: data.metrics ?? initialMetrics,
  }),

  reset: () => set({
    status: 'IDLE',
    simulationTime: 0,
    tick: 0,
    scooters: [],
    stations: [],
    metrics: initialMetrics,
  }),
}));
