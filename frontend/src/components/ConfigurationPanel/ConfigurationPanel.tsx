import { useState } from 'react';
import { useConfigStore } from '../../stores/configStore';
import { useSimulationStore } from '../../stores/simulationStore';
import { configApi } from '../../lib/api';
import {
  calculateRealWorldSpeed,
  calculateRealWorldRange,
  calculateRealWorldChargeTime,
  MovementStrategyType,
} from '../../types/simulation';

export function ConfigurationPanel() {
  const {
    config,
    updateConfig,
    updateGridConfig,
    updateScaleConfig,
    updateScooterConfig,
    updateBatterySpec,
  } = useConfigStore();
  const { status } = useSimulationStore();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  const isRunning = status === 'RUNNING';

  // Calculate real-world values
  const realWorldSpeed = calculateRealWorldSpeed(
    config.scooters.speed,
    config.scale.meters_per_grid_unit
  );

  const realWorldRange = calculateRealWorldRange(
    config.scooters.battery_spec.capacity_kwh,
    config.scooters.battery_spec.consumption_rate,
    config.scale.meters_per_grid_unit
  );

  const realWorldChargeTime = calculateRealWorldChargeTime(
    config.scooters.battery_spec.capacity_kwh,
    config.station_charge_rate_kw,
    0.2 // From 20% (typical swap-in level)
  );

  const handleApply = async () => {
    setError(null);
    setSuccess(false);

    try {
      // Validate first
      const validation = await configApi.validate(config);
      if (!validation.valid) {
        setError(validation.errors.join(', '));
        return;
      }

      // Apply configuration
      await configApi.set(config);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to apply configuration');
    }
  };

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const SectionHeader = ({ title, section }: { title: string; section: string }) => (
    <button
      onClick={() => toggleSection(section)}
      className="w-full flex items-center justify-between text-sm font-medium text-gray-700 mb-2 hover:text-blue-600"
    >
      <span>{title}</span>
      <span className="text-xs">{expandedSection === section ? '▼' : '▶'}</span>
    </button>
  );

  const RealWorldHint = ({ children }: { children: React.ReactNode }) => (
    <span className="text-xs text-blue-600 font-medium">{children}</span>
  );

  return (
    <div className="bg-white rounded-lg shadow p-4 max-h-[calc(100vh-200px)] overflow-y-auto">
      <h2 className="text-lg font-semibold mb-4">Configuration</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-3 bg-green-100 text-green-700 rounded-lg text-sm">
          Configuration applied successfully!
        </div>
      )}

      {/* Scale Settings - NEW */}
      <div className="mb-4 border-b pb-4">
        <SectionHeader title="Scale (Real-World Units)" section="scale" />
        {expandedSection === 'scale' && (
          <div className="grid grid-cols-2 gap-3 mt-2">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Meters/Grid Unit</label>
              <input
                type="number"
                min="10"
                max="1000"
                step="10"
                value={config.scale.meters_per_grid_unit}
                onChange={(e) => updateScaleConfig({ meters_per_grid_unit: parseFloat(e.target.value) || 100 })}
                disabled={isRunning}
                className="w-full px-3 py-2 border rounded-lg text-sm
                           disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Time Scale</label>
              <input
                type="number"
                min="1"
                max="3600"
                step="1"
                value={config.scale.time_scale}
                onChange={(e) => updateScaleConfig({ time_scale: parseFloat(e.target.value) || 60 })}
                disabled={isRunning}
                className="w-full px-3 py-2 border rounded-lg text-sm
                           disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <span className="text-xs text-gray-400">1 sim-sec = {config.scale.time_scale} real-sec</span>
            </div>
          </div>
        )}
      </div>

      {/* Grid Settings */}
      <div className="mb-4 border-b pb-4">
        <SectionHeader title="Grid" section="grid" />
        {expandedSection === 'grid' && (
          <div className="grid grid-cols-2 gap-3 mt-2">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Width</label>
              <input
                type="number"
                min="10"
                max="1000"
                value={config.grid.width}
                onChange={(e) => updateGridConfig({ width: parseInt(e.target.value) || 100 })}
                disabled={isRunning}
                className="w-full px-3 py-2 border rounded-lg text-sm
                           disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <RealWorldHint>{(config.grid.width * config.scale.meters_per_grid_unit / 1000).toFixed(1)} km</RealWorldHint>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Height</label>
              <input
                type="number"
                min="10"
                max="1000"
                value={config.grid.height}
                onChange={(e) => updateGridConfig({ height: parseInt(e.target.value) || 100 })}
                disabled={isRunning}
                className="w-full px-3 py-2 border rounded-lg text-sm
                           disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <RealWorldHint>{(config.grid.height * config.scale.meters_per_grid_unit / 1000).toFixed(1)} km</RealWorldHint>
            </div>
          </div>
        )}
      </div>

      {/* Station Settings */}
      <div className="mb-4 border-b pb-4">
        <SectionHeader title="Stations" section="stations" />
        {expandedSection === 'stations' && (
          <div className="space-y-3 mt-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Count</label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={config.num_stations}
                  onChange={(e) => updateConfig({ num_stations: parseInt(e.target.value) || 5 })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border rounded-lg text-sm
                             disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Slots/Station</label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={config.slots_per_station}
                  onChange={(e) => updateConfig({ slots_per_station: parseInt(e.target.value) || 10 })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border rounded-lg text-sm
                             disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Charge Rate (kW)</label>
                <input
                  type="number"
                  min="0.1"
                  max="10"
                  step="0.1"
                  value={config.station_charge_rate_kw}
                  onChange={(e) => updateConfig({ station_charge_rate_kw: parseFloat(e.target.value) || 0.5 })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border rounded-lg text-sm
                             disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
                <RealWorldHint>{realWorldChargeTime.toFixed(1)}h to full</RealWorldHint>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Initial Batteries</label>
                <input
                  type="number"
                  min="0"
                  max="50"
                  value={config.initial_batteries_per_station}
                  onChange={(e) => updateConfig({ initial_batteries_per_station: parseInt(e.target.value) || 8 })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border rounded-lg text-sm
                             disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Scooter Settings */}
      <div className="mb-4 border-b pb-4">
        <SectionHeader title="Scooters" section="scooters" />
        {expandedSection === 'scooters' && (
          <div className="space-y-3 mt-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Count</label>
                <input
                  type="number"
                  min="1"
                  max="10000"
                  value={config.scooters.count}
                  onChange={(e) => updateScooterConfig({ count: parseInt(e.target.value) || 50 })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border rounded-lg text-sm
                             disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Speed (units/sim-sec)</label>
                <input
                  type="number"
                  min="0.1"
                  max="50"
                  step="0.5"
                  value={config.scooters.speed}
                  onChange={(e) => updateScooterConfig({ speed: parseFloat(e.target.value) || 5 })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border rounded-lg text-sm
                             disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
                <RealWorldHint>{realWorldSpeed.toFixed(1)} km/h</RealWorldHint>
              </div>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Swap Threshold (%)</label>
              <input
                type="number"
                min="5"
                max="50"
                value={Math.round(config.scooters.swap_threshold * 100)}
                onChange={(e) => updateScooterConfig({ swap_threshold: (parseInt(e.target.value) || 20) / 100 })}
                disabled={isRunning}
                className="w-full px-3 py-2 border rounded-lg text-sm
                           disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            </div>
          </div>
        )}
      </div>

      {/* Battery Settings - NEW */}
      <div className="mb-4 border-b pb-4">
        <SectionHeader title="Battery" section="battery" />
        {expandedSection === 'battery' && (
          <div className="space-y-3 mt-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Capacity (kWh)</label>
                <input
                  type="number"
                  min="0.1"
                  max="10"
                  step="0.1"
                  value={config.scooters.battery_spec.capacity_kwh}
                  onChange={(e) => updateBatterySpec({ capacity_kwh: parseFloat(e.target.value) || 1.5 })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border rounded-lg text-sm
                             disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Consumption (kWh/unit)</label>
                <input
                  type="number"
                  min="0.0001"
                  max="0.1"
                  step="0.0001"
                  value={config.scooters.battery_spec.consumption_rate}
                  onChange={(e) => updateBatterySpec({ consumption_rate: parseFloat(e.target.value) || 0.001 })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border rounded-lg text-sm
                             disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
                <RealWorldHint>{realWorldRange.toFixed(0)} km range</RealWorldHint>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Simulation Settings */}
      <div className="mb-4 border-b pb-4">
        <SectionHeader title="Simulation" section="simulation" />
        {expandedSection === 'simulation' && (
          <div className="space-y-3 mt-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Duration (hours)</label>
                <input
                  type="number"
                  min="1"
                  max="168"
                  value={config.duration_hours}
                  onChange={(e) => updateConfig({ duration_hours: parseFloat(e.target.value) || 24 })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border rounded-lg text-sm
                             disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Random Seed</label>
                <input
                  type="number"
                  value={config.random_seed ?? ''}
                  onChange={(e) => updateConfig({
                    random_seed: e.target.value ? parseInt(e.target.value) : undefined
                  })}
                  placeholder="Auto"
                  disabled={isRunning}
                  className="w-full px-3 py-2 border rounded-lg text-sm
                             disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Movement Strategy</label>
              <select
                value={config.movement_strategy}
                onChange={(e) => updateConfig({ movement_strategy: e.target.value as MovementStrategyType })}
                disabled={isRunning}
                className="w-full px-3 py-2 border rounded-lg text-sm
                           disabled:bg-gray-100 disabled:cursor-not-allowed"
              >
                <option value="random_walk">Random Walk</option>
                <option value="directed">Directed (External Control)</option>
              </select>
              <span className="text-xs text-gray-400">
                {config.movement_strategy === 'random_walk'
                  ? 'Scooters move randomly between neighboring cells'
                  : 'Scooters receive destinations from external system'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Real-World Summary */}
      <div className="mb-4 p-3 bg-blue-50 rounded-lg">
        <h3 className="text-xs font-medium text-blue-800 mb-2">Real-World Equivalents</h3>
        <div className="text-xs text-blue-700 space-y-1">
          <p>Grid: {(config.grid.width * config.scale.meters_per_grid_unit / 1000).toFixed(1)} x {(config.grid.height * config.scale.meters_per_grid_unit / 1000).toFixed(1)} km</p>
          <p>Scooter speed: {realWorldSpeed.toFixed(1)} km/h</p>
          <p>Battery range: {realWorldRange.toFixed(0)} km</p>
          <p>Charge time (20%→100%): {realWorldChargeTime.toFixed(1)} hours</p>
        </div>
      </div>

      {/* Apply button */}
      <button
        onClick={handleApply}
        disabled={isRunning}
        className="w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg
                   disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Apply Configuration
      </button>
    </div>
  );
}
