import { GridCanvas } from './components/GridVisualization/GridCanvas';
import { SimulationControls } from './components/SimulationControls/SimulationControls';
import { ConfigurationPanel } from './components/ConfigurationPanel/ConfigurationPanel';
import { MetricsDashboard } from './components/MetricsDashboard/MetricsDashboard';
import { StationAnalyticsWindow } from './components/StationAnalyticsWindow/StationAnalyticsWindow';
import { useSimulationSocket } from './hooks/useSimulationSocket';

function App() {
  // Initialize WebSocket connection
  useSimulationSocket();

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">
            Battery Swap Station Simulation
          </h1>
          <p className="text-sm text-gray-500">
            Discrete event simulation for electric scooter battery swap networks
          </p>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left sidebar - Controls & Config */}
          <div className="lg:col-span-1 space-y-6">
            <SimulationControls />
            <ConfigurationPanel />
          </div>

          {/* Main area - Grid visualization */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold mb-4">Grid Visualization</h2>
              <div className="h-[500px]">
                <GridCanvas />
              </div>
              {/* Legend */}
              <div className="mt-4 flex flex-wrap gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-gray-800 rounded" />
                  <span>Station</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500" />
                  <span>Scooter (High Battery)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-yellow-500" />
                  <span>Scooter (Medium)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500" />
                  <span>Scooter (Low)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right sidebar - Metrics */}
          <div className="lg:col-span-1">
            <MetricsDashboard />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-8">
        <div className="max-w-7xl mx-auto px-4 py-4 text-center text-sm text-gray-500">
          Battery Swap Station Simulation System
        </div>
      </footer>

      <StationAnalyticsWindow />
    </div>
  );
}

export default App;
