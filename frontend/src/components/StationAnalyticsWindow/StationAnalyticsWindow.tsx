import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSimulationStore } from '../../stores/simulationStore';
import { metricsApi } from '../../lib/api';
import type { SwapEventRecord, StationSwapEvents } from '../../types/simulation';

function formatTime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m ${secs}s`;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function StationAnalyticsWindow() {
  const { selectedStationId, setSelectedStationId } = useSimulationStore();
  const [swapEvents, setSwapEvents] = useState<SwapEventRecord[]>([]);
  const [totalSwaps, setTotalSwaps] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedStationIdRef = useRef<string | null>(selectedStationId);

  useEffect(() => {
    selectedStationIdRef.current = selectedStationId;
  }, [selectedStationId]);

  const loadSwaps = useCallback(async (stationId: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response: StationSwapEvents = await metricsApi.getStationSwaps(stationId, {
        sort_by: 'battery',
        order: 'asc',
      });

      if (selectedStationIdRef.current !== stationId) {
        return;
      }

      setSwapEvents(response.swaps ?? []);
      setTotalSwaps(response.total ?? response.swaps?.length ?? 0);
    } catch (err) {
      if (selectedStationIdRef.current !== stationId) {
        return;
      }
      const message = err instanceof Error ? err.message : 'Failed to load station swaps';
      setError(message);
      setSwapEvents([]);
      setTotalSwaps(0);
    } finally {
      if (selectedStationIdRef.current === stationId) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    if (!selectedStationId) {
      setSwapEvents([]);
      setTotalSwaps(0);
      setError(null);
      setIsLoading(false);
      return;
    }

    loadSwaps(selectedStationId);
  }, [selectedStationId, loadSwaps]);

  const stationEvents = useMemo(() => {
    return swapEvents
      .slice()
      .sort((a, b) => {
        const levelDiff = a.new_battery_level - b.new_battery_level;
        if (levelDiff !== 0) return levelDiff;
        return a.timestamp - b.timestamp;
      });
  }, [swapEvents]);

  const partialSwaps = stationEvents.filter((event) => event.was_partial).length;

  if (!selectedStationId) return null;

  return (
    <div className="fixed right-6 bottom-6 w-[420px] max-w-[90vw] max-h-[70vh] bg-white border border-gray-200 rounded-xl shadow-xl flex flex-col">
      <div className="flex items-center justify-between border-b px-4 py-3 bg-gray-50 rounded-t-xl">
        <div>
          <div className="text-sm text-gray-500">Station Analytics</div>
          <div className="text-lg font-semibold text-gray-900">{selectedStationId}</div>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="text-xs px-2 py-1 rounded border border-gray-200 text-gray-600 hover:text-gray-900 hover:border-gray-300 transition"
            onClick={() => selectedStationId && loadSwaps(selectedStationId)}
            disabled={isLoading}
          >
            {isLoading ? 'Refreshing…' : 'Refresh'}
          </button>
          <button
            className="text-gray-400 hover:text-gray-700 transition"
            onClick={() => setSelectedStationId(null)}
            aria-label="Close station analytics"
          >
            &#10005;
          </button>
        </div>
      </div>

      <div className="px-4 py-3 border-b text-sm text-gray-600 flex items-center gap-4">
        <span>
          Swaps: <span className="font-semibold text-gray-900">{totalSwaps}</span>
        </span>
        <span>
          Partial: <span className="font-semibold text-gray-900">{partialSwaps}</span>
        </span>
        <span className="text-xs text-gray-400">Ordered by lowest battery out</span>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        {error ? (
          <div className="text-sm text-red-600">{error}</div>
        ) : isLoading && stationEvents.length === 0 ? (
          <div className="text-sm text-gray-500">Loading swaps…</div>
        ) : stationEvents.length === 0 ? (
          <div className="text-sm text-gray-500">No swaps recorded for this station yet.</div>
        ) : (
          <div className="space-y-2">
            {stationEvents.map((event, index) => (
              <div
                key={`${event.station_id}-${event.scooter_id}-${event.timestamp}-${index}`}
                className="flex items-center justify-between bg-gray-50 rounded-md px-3 py-2 text-sm"
              >
                <div className="flex flex-col">
                  <span className="font-medium text-gray-900">
                    {formatPercent(event.new_battery_level)}
                  </span>
                  <span className="text-xs text-gray-500">
                    time {formatTime(event.timestamp)}
                  </span>
                </div>
                <div className="text-right">
                  <div className="text-xs text-gray-500">scooter</div>
                  <div className="text-sm text-gray-700">{event.scooter_id}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
