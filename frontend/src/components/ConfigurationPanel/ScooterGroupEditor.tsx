import { useState } from 'react';
import { useConfigStore } from '../../stores/configStore';
import type { ScooterGroupConfig, ActivityStrategyType } from '../../types/simulation';
import { GROUP_COLORS } from '../../types/simulation';

interface ScooterGroupEditorProps {
  disabled?: boolean;
}

export function ScooterGroupEditor({ disabled = false }: ScooterGroupEditorProps) {
  const {
    config,
    addScooterGroup,
    updateScooterGroup,
    removeScooterGroup,
    updateGroupActivitySchedule,
    clearScooterGroups,
  } = useConfigStore();
  const [expandedGroup, setExpandedGroup] = useState<number | null>(null);

  const groups = config.scooter_groups || [];

  const handleAddGroup = () => {
    const nextColor = GROUP_COLORS[groups.length % GROUP_COLORS.length];
    const newGroup: ScooterGroupConfig = {
      name: `Group ${groups.length + 1}`,
      count: 10,
      color: nextColor,
      activity_strategy: 'always_active',
    };
    addScooterGroup(newGroup);
    setExpandedGroup(groups.length);
  };

  const handleRemoveGroup = (index: number) => {
    removeScooterGroup(index);
    if (expandedGroup === index) {
      setExpandedGroup(null);
    }
  };

  const handleToggleExpand = (index: number) => {
    setExpandedGroup(expandedGroup === index ? null : index);
  };

  const getTotalScooters = () => {
    if (groups.length === 0) {
      return config.scooters.count;
    }
    return groups.reduce((sum, g) => sum + g.count, 0);
  };

  const formatHour = (hour: number) => {
    const h = Math.floor(hour);
    const m = Math.round((hour - h) * 60);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className="flex justify-between items-center">
        <span className="text-xs text-gray-500">
          {groups.length > 0
            ? `${groups.length} groups, ${getTotalScooters()} total scooters`
            : `${config.scooters.count} scooters (no groups)`
          }
        </span>
        {groups.length > 0 && (
          <button
            onClick={clearScooterGroups}
            disabled={disabled}
            className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
          >
            Clear All
          </button>
        )}
      </div>

      {/* Group List */}
      {groups.map((group, index) => (
        <div key={index} className="border rounded-lg overflow-hidden">
          {/* Group Header */}
          <div
            className="flex items-center justify-between p-2 bg-gray-50 cursor-pointer"
            onClick={() => handleToggleExpand(index)}
          >
            <div className="flex items-center gap-2">
              <div
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: group.color }}
              />
              <span className="text-sm font-medium">{group.name}</span>
              <span className="text-xs text-gray-500">({group.count})</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400">
                {group.activity_strategy === 'scheduled' ? 'Scheduled' : 'Always Active'}
              </span>
              <span className="text-xs">{expandedGroup === index ? '▼' : '▶'}</span>
            </div>
          </div>

          {/* Group Details */}
          {expandedGroup === index && (
            <div className="p-3 space-y-3 bg-white">
              {/* Name and Count */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Name</label>
                  <input
                    type="text"
                    value={group.name}
                    onChange={(e) => updateScooterGroup(index, { name: e.target.value })}
                    disabled={disabled}
                    className="w-full px-2 py-1 border rounded text-sm disabled:bg-gray-100"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Count</label>
                  <input
                    type="number"
                    min="1"
                    max="10000"
                    value={group.count}
                    onChange={(e) => updateScooterGroup(index, { count: parseInt(e.target.value) || 1 })}
                    disabled={disabled}
                    className="w-full px-2 py-1 border rounded text-sm disabled:bg-gray-100"
                  />
                </div>
              </div>

              {/* Color Picker */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Color</label>
                <div className="flex gap-1">
                  {GROUP_COLORS.map((color) => (
                    <button
                      key={color}
                      onClick={() => updateScooterGroup(index, { color })}
                      disabled={disabled}
                      className={`w-6 h-6 rounded-full border-2 transition-all ${
                        group.color === color ? 'border-gray-800 scale-110' : 'border-transparent'
                      } disabled:opacity-50`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>

              {/* Speed and Swap Threshold (optional overrides) */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Speed (override)</label>
                  <input
                    type="number"
                    min="0.1"
                    max="50"
                    step="0.5"
                    value={group.speed ?? ''}
                    placeholder={`Default: ${config.scooters.speed}`}
                    onChange={(e) => updateScooterGroup(index, {
                      speed: e.target.value ? parseFloat(e.target.value) : undefined
                    })}
                    disabled={disabled}
                    className="w-full px-2 py-1 border rounded text-sm disabled:bg-gray-100"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Swap % (override)</label>
                  <input
                    type="number"
                    min="5"
                    max="50"
                    value={group.swap_threshold ? Math.round(group.swap_threshold * 100) : ''}
                    placeholder={`Default: ${Math.round(config.scooters.swap_threshold * 100)}%`}
                    onChange={(e) => updateScooterGroup(index, {
                      swap_threshold: e.target.value ? parseInt(e.target.value) / 100 : undefined
                    })}
                    disabled={disabled}
                    className="w-full px-2 py-1 border rounded text-sm disabled:bg-gray-100"
                  />
                </div>
              </div>

              {/* Activity Strategy */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Activity Strategy</label>
                <select
                  value={group.activity_strategy}
                  onChange={(e) => {
                    const strategy = e.target.value as ActivityStrategyType;
                    updateScooterGroup(index, {
                      activity_strategy: strategy,
                      activity_schedule: strategy === 'scheduled' ? {
                        activity_start_hour: 8.0,
                        activity_end_hour: 20.0,
                        low_battery_threshold: 0.3,
                      } : undefined,
                    });
                  }}
                  disabled={disabled}
                  className="w-full px-2 py-1 border rounded text-sm disabled:bg-gray-100"
                >
                  <option value="always_active">Always Active</option>
                  <option value="scheduled">Scheduled Hours</option>
                </select>
              </div>

              {/* Activity Schedule (if scheduled) */}
              {group.activity_strategy === 'scheduled' && group.activity_schedule && (
                <div className="p-2 bg-gray-50 rounded space-y-2">
                  <div className="text-xs font-medium text-gray-600">Schedule Settings</div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Start Hour</label>
                      <input
                        type="number"
                        min="0"
                        max="23.99"
                        step="0.5"
                        value={group.activity_schedule.activity_start_hour}
                        onChange={(e) => updateGroupActivitySchedule(index, {
                          activity_start_hour: parseFloat(e.target.value) || 0
                        })}
                        disabled={disabled}
                        className="w-full px-2 py-1 border rounded text-xs disabled:bg-gray-100"
                      />
                      <span className="text-xs text-gray-400">
                        {formatHour(group.activity_schedule.activity_start_hour)}
                      </span>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">End Hour</label>
                      <input
                        type="number"
                        min="0"
                        max="23.99"
                        step="0.5"
                        value={group.activity_schedule.activity_end_hour}
                        onChange={(e) => updateGroupActivitySchedule(index, {
                          activity_end_hour: parseFloat(e.target.value) || 0
                        })}
                        disabled={disabled}
                        className="w-full px-2 py-1 border rounded text-xs disabled:bg-gray-100"
                      />
                      <span className="text-xs text-gray-400">
                        {formatHour(group.activity_schedule.activity_end_hour)}
                      </span>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Max Distance/Day (km)</label>
                      <input
                        type="number"
                        min="0"
                        step="10"
                        value={group.activity_schedule.max_distance_per_day_km ?? ''}
                        placeholder="Unlimited"
                        onChange={(e) => updateGroupActivitySchedule(index, {
                          max_distance_per_day_km: e.target.value ? parseFloat(e.target.value) : undefined
                        })}
                        disabled={disabled}
                        className="w-full px-2 py-1 border rounded text-xs disabled:bg-gray-100"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Pre-Idle Swap %</label>
                      <input
                        type="number"
                        min="10"
                        max="90"
                        value={Math.round(group.activity_schedule.low_battery_threshold * 100)}
                        onChange={(e) => updateGroupActivitySchedule(index, {
                          low_battery_threshold: (parseInt(e.target.value) || 30) / 100
                        })}
                        disabled={disabled}
                        className="w-full px-2 py-1 border rounded text-xs disabled:bg-gray-100"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Remove Button */}
              <button
                onClick={() => handleRemoveGroup(index)}
                disabled={disabled}
                className="w-full text-xs text-red-500 hover:text-red-700 py-1 disabled:opacity-50"
              >
                Remove Group
              </button>
            </div>
          )}
        </div>
      ))}

      {/* Add Group Button */}
      <button
        onClick={handleAddGroup}
        disabled={disabled}
        className="w-full px-3 py-2 border-2 border-dashed border-gray-300 rounded-lg
                   text-sm text-gray-500 hover:border-blue-400 hover:text-blue-500
                   disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        + Add Scooter Group
      </button>

      {/* Hint */}
      {groups.length === 0 && (
        <p className="text-xs text-gray-400 text-center">
          Create groups to define different activity schedules and visual identities for scooters.
        </p>
      )}
    </div>
  );
}
