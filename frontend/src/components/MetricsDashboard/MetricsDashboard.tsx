import { useSimulationStore } from '../../stores/simulationStore';

function formatTime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

function getStationMissRate(
  stationId: string,
  misses: Record<string, number>,
  swaps: Record<string, number>
): number {
  const m = misses[stationId] ?? 0;
  const s = swaps[stationId] ?? 0;
  const total = m + s;
  return total === 0 ? 0 : m / total;
}

function getMissRateColor(rate: number): string {
  if (rate <= 0.10) return 'bg-green-500';
  if (rate <= 0.20) return 'bg-yellow-500';
  return 'bg-red-500';
}

function getMissRateTextColor(rate: number): string {
  if (rate <= 0.10) return 'text-green-600';
  if (rate <= 0.20) return 'text-yellow-600';
  return 'text-red-600';
}

export function MetricsDashboard() {
  const { simulationTime, tick, metrics, scooters, stations } = useSimulationStore();

  // Calculate some derived metrics
  const totalScooters = scooters.length;
  const scootersMoving = scooters.filter(s => s.state === 'MOVING').length;
  const scootersAtStation = scooters.filter(s =>
    s.state === 'SWAPPING' || s.state === 'WAITING_FOR_BATTERY'
  ).length;
  const scootersTraveling = scooters.filter(s => s.state === 'TRAVELING_TO_STATION').length;
  const scootersIdle = scooters.filter(s => s.state === 'IDLE').length;

  const totalSlots = stations.reduce((sum, s) => sum + s.num_slots, 0);
  const totalFullBatteries = stations.reduce((sum, s) => sum + s.full_batteries, 0);
  const avgUtilization = totalSlots > 0 ? totalFullBatteries / totalSlots : 0;

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h2 className="text-lg font-semibold mb-4">Metrics Dashboard</h2>

      {/* Time info */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="text-sm text-gray-500">Simulation Time</div>
          <div className="text-xl font-semibold">{formatTime(simulationTime)}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="text-sm text-gray-500">Events Processed</div>
          <div className="text-xl font-semibold">{tick.toLocaleString()}</div>
        </div>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-blue-50 rounded-lg p-3">
          <div className="text-sm text-blue-600">Total Swaps</div>
          <div className="text-2xl font-bold text-blue-700">
            {metrics.total_swaps}
          </div>
        </div>
        <div className="bg-red-50 rounded-lg p-3">
          <div className="text-sm text-red-600">Total Misses</div>
          <div className="text-2xl font-bold text-red-700">
            {metrics.total_misses}
          </div>
        </div>
        <div className="bg-yellow-50 rounded-lg p-3">
          <div className="text-sm text-yellow-600">Miss Rate</div>
          <div className="text-2xl font-bold text-yellow-700">
            {(metrics.miss_rate * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Miss breakdown */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-gray-700 mb-2">Miss Breakdown</h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-gray-50 rounded p-2">
            <div className="text-xs text-gray-500">No Battery Available</div>
            <div className="font-semibold">{metrics.no_battery_misses}</div>
          </div>
          <div className="bg-gray-50 rounded p-2">
            <div className="text-xs text-gray-500">Partial Charge</div>
            <div className="font-semibold">{metrics.partial_charge_misses}</div>
          </div>
        </div>
      </div>

      {/* Scooter status */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-gray-700 mb-2">Scooter Status</h3>
        <div className="grid grid-cols-5 gap-2">
          <div className="text-center p-2 bg-green-50 rounded">
            <div className="text-xs text-green-600">Moving</div>
            <div className="font-semibold text-green-700">{scootersMoving}</div>
          </div>
          <div className="text-center p-2 bg-blue-50 rounded">
            <div className="text-xs text-blue-600">Traveling</div>
            <div className="font-semibold text-blue-700">{scootersTraveling}</div>
          </div>
          <div className="text-center p-2 bg-purple-50 rounded">
            <div className="text-xs text-purple-600">At Station</div>
            <div className="font-semibold text-purple-700">{scootersAtStation}</div>
          </div>
          <div className="text-center p-2 bg-slate-100 rounded">
            <div className="text-xs text-slate-600">Idle</div>
            <div className="font-semibold text-slate-700">{scootersIdle}</div>
          </div>
          <div className="text-center p-2 bg-gray-50 rounded">
            <div className="text-xs text-gray-600">Total</div>
            <div className="font-semibold text-gray-700">{totalScooters}</div>
          </div>
        </div>
      </div>

      {/* Station utilization */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-gray-700 mb-2">Station Utilization</h3>
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-gray-600">
              {totalFullBatteries} / {totalSlots} full batteries
            </span>
            <span className="font-semibold">
              {(avgUtilization * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-blue-500 h-3 rounded-full transition-all"
              style={{ width: `${avgUtilization * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Station details */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2">Stations</h3>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {stations.map((station) => {
            const missRate = getStationMissRate(
              station.id,
              metrics.misses_per_station,
              metrics.swaps_per_station
            );
            return (
              <div
                key={station.id}
                className="flex items-center justify-between bg-gray-50 rounded p-2 text-sm"
              >
                <span className="text-gray-600 truncate max-w-[80px]" title={station.id}>
                  {station.id}
                </span>
                <div className="flex items-center gap-3">
                  <span className="font-medium">
                    {station.full_batteries}/{station.num_slots}
                  </span>
                  <div className="flex items-center gap-1">
                    <span className={`text-xs font-medium ${getMissRateTextColor(missRate)}`}>
                      {(missRate * 100).toFixed(0)}%
                    </span>
                    <div
                      className={`w-3 h-3 rounded-full ${getMissRateColor(missRate)}`}
                      title={`Miss rate: ${(missRate * 100).toFixed(1)}%`}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
