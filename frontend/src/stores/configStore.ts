import { create } from 'zustand';
import type { SimulationConfig, ScooterGroupConfig, ActivityScheduleConfig } from '../types/simulation';

interface ConfigState {
  config: SimulationConfig;
  updateConfig: (config: Partial<SimulationConfig>) => void;
  updateGridConfig: (grid: Partial<SimulationConfig['grid']>) => void;
  updateScaleConfig: (scale: Partial<SimulationConfig['scale']>) => void;
  updateScooterConfig: (scooters: Partial<SimulationConfig['scooters']>) => void;
  updateBatterySpec: (spec: Partial<SimulationConfig['scooters']['battery_spec']>) => void;
  // Scooter group management
  addScooterGroup: (group: ScooterGroupConfig) => void;
  updateScooterGroup: (index: number, updates: Partial<ScooterGroupConfig>) => void;
  removeScooterGroup: (index: number) => void;
  updateGroupActivitySchedule: (index: number, schedule: Partial<ActivityScheduleConfig>) => void;
  clearScooterGroups: () => void;
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
  station_charge_rate_kw: 1.3,
  initial_batteries_per_station: 8,
  scooters: {
    count: 50,
    speed: 0.025,         // 0.025 grid units per sim-sec = 9 km/h with default scale
    swap_threshold: 0.2,
    battery_spec: {
      capacity_kwh: 1.6,
      charge_rate_kw: 1.3,
      consumption_rate: 0.005,  // kWh per grid unit
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

  // Scooter group management
  addScooterGroup: (group) => set((state) => ({
    config: {
      ...state.config,
      scooter_groups: [...(state.config.scooter_groups || []), group],
    },
  })),

  updateScooterGroup: (index, updates) => set((state) => {
    const groups = [...(state.config.scooter_groups || [])];
    if (index >= 0 && index < groups.length) {
      groups[index] = { ...groups[index], ...updates };
    }
    return {
      config: {
        ...state.config,
        scooter_groups: groups,
      },
    };
  }),

  removeScooterGroup: (index) => set((state) => {
    const groups = [...(state.config.scooter_groups || [])];
    if (index >= 0 && index < groups.length) {
      groups.splice(index, 1);
    }
    return {
      config: {
        ...state.config,
        scooter_groups: groups.length > 0 ? groups : undefined,
      },
    };
  }),

  updateGroupActivitySchedule: (index, schedule) => set((state) => {
    const groups = [...(state.config.scooter_groups || [])];
    if (index >= 0 && index < groups.length) {
      groups[index] = {
        ...groups[index],
        activity_schedule: {
          activity_start_hour: 8.0,
          activity_end_hour: 20.0,
          low_battery_threshold: 0.3,
          ...groups[index].activity_schedule,
          ...schedule,
        },
      };
    }
    return {
      config: {
        ...state.config,
        scooter_groups: groups,
      },
    };
  }),

  clearScooterGroups: () => set((state) => ({
    config: {
      ...state.config,
      scooter_groups: undefined,
    },
  })),

  resetConfig: () => set({ config: defaultConfig }),
}));
