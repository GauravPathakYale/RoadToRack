# Battery Swap Station Simulation

A discrete event simulation (DES) system for modeling battery swap stations for electric scooters, with real-time visualization via web UI.

## Features

- **Event-driven simulation** with configurable parameters
- **Real-time visualization** of scooters and stations on a grid
- **Metrics tracking** including miss rate (primary metric)
- **WebSocket-based updates** for smooth real-time display
- **Configurable parameters** via web UI

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The UI will be available at `http://localhost:3000`

## Usage

1. Start both backend and frontend servers
2. Open `http://localhost:3000` in your browser
3. Configure simulation parameters in the left panel
4. Click "Apply Configuration" to set up the simulation
5. Click "Start" to begin the simulation
6. Watch the grid visualization and metrics in real-time
7. Adjust speed using the slider (1x to 100x)

## Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| Grid Width/Height | Size of the simulation grid | 100x100 |
| Stations | Number of swap stations | 5 |
| Slots per Station | Battery slots per station | 10 |
| Scooter Count | Number of scooters | 50 |
| Swap Threshold | Battery % that triggers swap | 20% |
| Duration | Simulation duration in hours | 24h |

## Key Metrics

- **Miss Rate**: Times a scooter received a non-full battery
  - **No Battery Miss**: Station had no batteries available
  - **Partial Charge Miss**: Battery wasn't fully charged
- **Total Swaps**: Number of completed battery swaps
- **Station Utilization**: Battery availability across stations

## Architecture

```
RoadToRack/
├── backend/           # Python FastAPI backend
│   ├── app/
│   │   ├── api/       # REST & WebSocket endpoints
│   │   ├── core/      # Simulation engine & manager
│   │   ├── models/    # Entities & Pydantic schemas
│   │   └── simulation/ # DES events & mechanics
│   └── requirements.txt
│
└── frontend/          # React TypeScript frontend
    ├── src/
    │   ├── components/ # UI components
    │   ├── stores/    # Zustand state management
    │   ├── hooks/     # Custom React hooks
    │   └── lib/       # Utilities & API client
    └── package.json
```

## API Endpoints

### REST API

- `GET /api/v1/config/` - Get current configuration
- `PUT /api/v1/config/` - Set configuration
- `POST /api/v1/simulation/start` - Start simulation
- `POST /api/v1/simulation/pause` - Pause simulation
- `POST /api/v1/simulation/resume` - Resume simulation
- `POST /api/v1/simulation/stop` - Stop simulation
- `PATCH /api/v1/simulation/speed` - Adjust speed
- `GET /api/v1/metrics/current` - Get current metrics
- `GET /api/v1/metrics/summary` - Get metrics summary

### WebSocket

- `ws://localhost:8000/api/v1/ws/simulation` - Real-time updates

## Tech Stack

- **Backend**: Python, FastAPI, Pydantic, NumPy
- **Frontend**: React, TypeScript, Zustand, Recharts, Tailwind CSS
- **Communication**: REST API + WebSocket
