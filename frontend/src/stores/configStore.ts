import { create } from 'zustand';
import type { SimulationConfig } from '../types/simulation';

interface ConfigState {
  config: SimulationConfig;
  updateConfig: (config: Partial<SimulationConfig>) => void;
  updateGridConfig: (grid: Partial<SimulationConfig['grid']>) => void;
  updateScaleConfig: (scale: Partial<SimulationConfig['scale']>) => void;
  updateScooterConfig: (scooters: Partial<SimulationConfig['scooters']>) => void;
  updateBatterySpec: (spec: Partial<SimulationConfig['scooters']['battery_spec']>) => void;
  resetConfig: () => void;
}

const defaultConfig: SimulationConfig = {
  grid: {
    width: 100,
    height: 100,
  },
  scale: {
    meters_per_grid_unit: 100,  // 1 grid unit = 100 meters
    time_scale: 60,             // 1 sim-second = 60 real seconds (1 minute)
  },
  num_stations: 5,
  slots_per_station: 10,
  station_charge_rate_kw: 0.5,
  initial_batteries_per_station: 8,
  scooters: {
    count: 50,
    speed: 5.0,           // 5 grid units per sim-sec = 30 km/h with default scale
    swap_threshold: 0.2,
    battery_spec: {
      capacity_kwh: 1.5,
      charge_rate_kw: 0.5,
      consumption_rate: 0.001,  // kWh per grid unit → 150 km range with default scale
    },
  },
  duration_hours: 24,
  random_seed: undefined,
  movement_strategy: 'random_walk',
};

export const useConfigStore = create<ConfigState>((set) => ({
  config: defaultConfig,

  updateConfig: (updates) => set((state) => ({
    config: { ...state.config, ...updates },
  })),

  updateGridConfig: (grid) => set((state) => ({
    config: {
      ...state.config,
      grid: { ...state.config.grid, ...grid },
    },
  })),

  updateScaleConfig: (scale) => set((state) => ({
    config: {
      ...state.config,
      scale: { ...state.config.scale, ...scale },
    },
  })),

  updateScooterConfig: (scooters) => set((state) => ({
    config: {
      ...state.config,
      scooters: { ...state.config.scooters, ...scooters },
    },
  })),

  updateBatterySpec: (spec) => set((state) => ({
    config: {
      ...state.config,
      scooters: {
        ...state.config.scooters,
        battery_spec: { ...state.config.scooters.battery_spec, ...spec },
      },
    },
  })),

  resetConfig: () => set({ config: defaultConfig }),
}));
