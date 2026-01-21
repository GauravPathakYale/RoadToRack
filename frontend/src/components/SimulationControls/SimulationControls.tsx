import { useSimulationStore } from '../../stores/simulationStore';
import { useSimulationSocket } from '../../hooks/useSimulationSocket';

export function SimulationControls() {
  const { status, speed, isConnected } = useSimulationStore();
  const { sendCommand, setSpeed } = useSimulationSocket();

  const isRunning = status === 'RUNNING';
  const isPaused = status === 'PAUSED';
  const isIdle = status === 'IDLE';

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h2 className="text-lg font-semibold mb-4">Simulation Controls</h2>

      {/* Connection status */}
      <div className="flex items-center gap-2 mb-4">
        <div
          className={`w-3 h-3 rounded-full ${
            isConnected ? 'bg-green-500' : 'bg-red-500'
          }`}
        />
        <span className="text-sm text-gray-600">
          {isConnected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      {/* Status */}
      <div className="mb-4">
        <span className="text-sm text-gray-500">Status: </span>
        <span className={`font-medium ${
          isRunning ? 'text-green-600' :
          isPaused ? 'text-yellow-600' :
          status === 'COMPLETED' ? 'text-blue-600' :
          'text-gray-600'
        }`}>
          {status}
        </span>
      </div>

      {/* Control buttons */}
      <div className="flex flex-wrap gap-2 mb-4">
        {(isIdle || isPaused) && (
          <button
            onClick={() => sendCommand(isIdle ? 'start' : 'resume')}
            disabled={!isConnected}
            className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg
                       disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isIdle ? 'Start' : 'Resume'}
          </button>
        )}

        {isRunning && (
          <button
            onClick={() => sendCommand('pause')}
            disabled={!isConnected}
            className="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-white rounded-lg
                       disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Pause
          </button>
        )}

        {(isRunning || isPaused) && (
          <button
            onClick={() => sendCommand('stop')}
            disabled={!isConnected}
            className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg
                       disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Stop
          </button>
        )}

        <button
          onClick={() => sendCommand('reset')}
          disabled={!isConnected || isRunning}
          className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Reset
        </button>
      </div>

      {/* Speed control */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Speed: {speed}x
        </label>
        <input
          type="range"
          min="0.1"
          max="100"
          step="0.1"
          value={speed}
          onChange={(e) => {
            const newSpeed = parseFloat(e.target.value);
            useSimulationStore.getState().setSpeed(newSpeed);
            setSpeed(newSpeed);
          }}
          disabled={!isConnected}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>0.1x</span>
          <span>Real-time</span>
          <span>100x</span>
        </div>
      </div>

      {/* Quick speed buttons */}
      <div className="flex gap-2">
        {[1, 10, 50, 100].map((s) => (
          <button
            key={s}
            onClick={() => {
              useSimulationStore.getState().setSpeed(s);
              setSpeed(s);
            }}
            disabled={!isConnected}
            className={`px-3 py-1 rounded text-sm transition-colors
                       ${speed === s
                         ? 'bg-blue-500 text-white'
                         : 'bg-gray-100 hover:bg-gray-200 text-gray-700'}
                       disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {s}x
          </button>
        ))}
      </div>
    </div>
  );
}
