import { useSimulationStore } from '../stores/simulationStore';

const WS_URL = 'ws://localhost:8000/api/v1/ws/simulation';

class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectTimeout: number | undefined;
  private isConnecting = false;

  constructor() {
    // Auto-connect on instantiation
    this.connect();
  }

  connect() {
    if (this.isConnecting) {
      console.log('[WSManager] Already connecting, skipping');
      return;
    }
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[WSManager] Already connected, skipping');
      return;
    }
    if (this.ws?.readyState === WebSocket.CONNECTING) {
      console.log('[WSManager] Connection in progress, skipping');
      return;
    }

    this.isConnecting = true;
    console.log('[WSManager] Creating new WebSocket connection...');

    // Clean up existing connection if any
    if (this.ws) {
      this.ws.onclose = null; // Prevent reconnect loop
      this.ws.close();
      this.ws = null;
    }

    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('[WSManager] Connected successfully');
      this.isConnecting = false;
      useSimulationStore.getState().setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('[WSManager] Message received:', data.type);

        const store = useSimulationStore.getState();

        switch (data.type) {
          case 'initial_state':
          case 'state_update':
            store.updateFromServer(data);
            break;
          case 'command_ack':
            store.setStatus(data.status);
            break;
          case 'error':
            console.error('[WSManager] Server error:', data.message);
            break;
        }
      } catch (e) {
        console.error('[WSManager] Failed to parse message:', e);
      }
    };

    ws.onclose = (event) => {
      console.log('[WSManager] Disconnected, code:', event.code);
      this.isConnecting = false;
      this.ws = null;
      useSimulationStore.getState().setConnected(false);

      // Reconnect unless it was a clean close
      if (event.code !== 1000) {
        this.reconnectTimeout = window.setTimeout(() => {
          console.log('[WSManager] Attempting reconnect...');
          this.connect();
        }, 2000);
      }
    };

    ws.onerror = (error) => {
      console.error('[WSManager] Error:', error);
      this.isConnecting = false;
    };

    this.ws = ws;
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = undefined;
    }
    if (this.ws) {
      this.ws.onclose = null; // Prevent reconnect
      this.ws.close(1000, 'User disconnect');
      this.ws = null;
    }
    useSimulationStore.getState().setConnected(false);
  }

  sendCommand(command: string) {
    console.log('[WSManager] sendCommand called:', command, 'ws state:', this.ws?.readyState);
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[WSManager] Sending command:', command);
      this.ws.send(JSON.stringify({ type: 'command', command }));
    } else {
      console.warn('[WSManager] Cannot send command, not connected. State:', this.ws?.readyState);
    }
  }

  setSpeed(speed: number) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'set_speed', speed }));
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN || false;
  }
}

// Create singleton instance - survives HMR via window
declare global {
  interface Window {
    __wsManager?: WebSocketManager;
  }
}

// Get or create the singleton
function getManager(): WebSocketManager {
  if (!window.__wsManager) {
    console.log('[WSManager] Creating singleton instance');
    window.__wsManager = new WebSocketManager();
  }
  return window.__wsManager;
}

// Export singleton instance
export const wsManager = getManager();
