// Simulation types

export interface Position {
  x: number;
  y: number;
}

export type ScooterState = 'MOVING' | 'TRAVELING_TO_STATION' | 'SWAPPING' | 'WAITING_FOR_BATTERY' | 'IDLE';

export interface Scooter {
  id: string;
  position: Position;
  battery_id: string;
  battery_level: number;
  state: ScooterState;
  target_station_id?: string;
  group_id?: string;
  distance_traveled_today?: number;
}

export interface BatterySlot {
  index: number;
  battery_id?: string;
  is_charging: boolean;
  charge_level?: number;
}

export interface Station {
  id: string;
  position: Position;
  num_slots: number;
  available_batteries: number;
  full_batteries: number;
  empty_slots: number;
  slots: BatterySlot[];
}

export interface SimulationState {
  simulation_time: number;
  tick: number;
  status: string;
  grid_width: number;
  grid_height: number;
  scooters: Scooter[];
  stations: Station[];
  scooter_groups?: ScooterGroupInfo[];  // Group metadata for visualization
}

export interface Metrics {
  total_swaps: number;
  total_misses: number;
  miss_rate: number;
  no_battery_misses: number;
  partial_charge_misses: number;
  misses_per_station: Record<string, number>;
  swaps_per_station: Record<string, number>;
}

export interface SwapEventRecord {
  timestamp: number;
  scooter_id: string;
  station_id: string;
  old_battery_level: number;
  new_battery_level: number;
  was_partial: boolean;
}

export interface MetricsSummary extends Metrics {
  no_battery_miss_rate: number;
  partial_charge_miss_rate: number;
  average_wait_time: number;
  max_wait_time: number;
  swaps_per_station: Record<string, number>;
  miss_rate_history: [number, number][];
}

export interface StationSwapEvents {
  station_id: string;
  total: number;
  offset: number;
  limit: number;
  sort_by: 'battery' | 'time';
  order: 'asc' | 'desc';
  swaps: SwapEventRecord[];
}

// Movement strategy types
export type MovementStrategyType = 'random_walk' | 'directed';

// Activity strategy types
export type ActivityStrategyType = 'always_active' | 'scheduled';

// Activity schedule configuration
export interface ActivityScheduleConfig {
  activity_start_hour: number;  // 0-23.99
  activity_end_hour: number;    // 0-23.99
  max_distance_per_day_km?: number;  // Optional daily distance limit
  low_battery_threshold: number;  // 0.1-0.9
}

// Scooter group configuration
export interface ScooterGroupConfig {
  name: string;
  count: number;
  color: string;  // Hex color
  speed?: number;
  swap_threshold?: number;
  movement_strategy?: MovementStrategyType;
  activity_strategy: ActivityStrategyType;
  activity_schedule?: ActivityScheduleConfig;
}

// Scooter group info (returned from backend)
export interface ScooterGroupInfo {
  id: string;
  name: string;
  color: string;
  count: number;
}

// Default group colors
export const GROUP_COLORS = [
  '#22C55E',  // Green
  '#3B82F6',  // Blue
  '#F97316',  // Orange
  '#8B5CF6',  // Purple
  '#EF4444',  // Red
  '#EC4899',  // Pink
  '#14B8A6',  // Teal
  '#F59E0B',  // Amber
];

export interface SimulationConfig {
  grid: {
    width: number;
    height: number;
  };
  // Scale factors for real-world unit conversion
  scale: {
    meters_per_grid_unit: number;  // How many meters one grid unit represents
    time_scale: number;            // Real seconds per simulation second (e.g., 60 means 1 sim-sec = 1 real-min)
  };
  num_stations: number;
  slots_per_station: number;
  station_charge_rate_kw: number;
  initial_batteries_per_station: number;
  scooters: {
    count: number;
    speed: number;              // Grid units per simulation second
    swap_threshold: number;
    battery_spec: {
      capacity_kwh: number;
      charge_rate_kw: number;
      consumption_rate: number; // kWh per grid unit
    };
  };
  scooter_groups?: ScooterGroupConfig[];  // Optional scooter groups (overrides scooters.count if provided)
  duration_hours: number;
  random_seed?: number;
  movement_strategy: MovementStrategyType;
}

// Helper functions for real-world unit conversions
export function calculateRealWorldSpeed(
  speedGridUnitsPerSimSec: number,
  metersPerGridUnit: number
): number {
  // Returns speed in km/h
  // 1 sim-second = 1 real second in the simulation
  const metersPerSecond = speedGridUnitsPerSimSec * metersPerGridUnit;
  return metersPerSecond * 3.6; // m/s to km/h
}

export function calculateRealWorldRange(
  capacityKwh: number,
  consumptionRateKwhPerUnit: number,
  metersPerGridUnit: number
): number {
  // Returns range in km
  const rangeInGridUnits = capacityKwh / consumptionRateKwhPerUnit;
  return (rangeInGridUnits * metersPerGridUnit) / 1000;
}

export function calculateRealWorldChargeTime(
  capacityKwh: number,
  chargeRateKw: number,
  fromChargeLevel: number = 0
): number {
  // Returns charge time in hours (real-world, not simulation)
  const energyToCharge = capacityKwh * (1 - fromChargeLevel);
  return energyToCharge / chargeRateKw;
}

export function calculateSimulationChargeTime(
  capacityKwh: number,
  chargeRateKw: number,
  timeScale: number,
  fromChargeLevel: number = 0
): number {
  // Returns charge time in simulation seconds
  const realHours = calculateRealWorldChargeTime(capacityKwh, chargeRateKw, fromChargeLevel);
  const realSeconds = realHours * 3600;
  return realSeconds / timeScale; // Convert to simulation seconds
}

export type SimulationStatus = 'IDLE' | 'RUNNING' | 'PAUSED' | 'STOPPED' | 'COMPLETED';
