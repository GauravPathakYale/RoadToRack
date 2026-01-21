import { useCallback, useEffect } from 'react';
import { wsManager } from '../lib/websocketManager';

export function useSimulationSocket() {
  const sendCommand = useCallback((command: string) => {
    wsManager.sendCommand(command);
  }, []);

  const setSpeed = useCallback((speed: number) => {
    wsManager.setSpeed(speed);
  }, []);

  const connect = useCallback(() => {
    wsManager.connect();
  }, []);

  const disconnect = useCallback(() => {
    wsManager.disconnect();
  }, []);

  // Ensure connection is established (manager auto-connects, but this ensures it)
  useEffect(() => {
    wsManager.connect();
  }, []);

  return {
    sendCommand,
    setSpeed,
    connect,
    disconnect,
  };
}
