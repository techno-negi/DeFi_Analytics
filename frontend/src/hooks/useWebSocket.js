import { useEffect, useCallback } from 'react';
import { useWebSocketStore } from '../services/websocket';

export const useWebSocket = (channels = []) => {
  const {
    connected,
    subscribe,
    unsubscribe,
    priceUpdates,
    arbitrageAlerts,
    yieldUpdates
  } = useWebSocketStore();

  useEffect(() => {
    if (connected && channels.length > 0) {
      subscribe(channels);
    }

    return () => {
      if (channels.length > 0) {
        unsubscribe(channels);
      }
    };
  }, [connected, channels, subscribe, unsubscribe]);

  return {
    connected,
    priceUpdates,
    arbitrageAlerts,
    yieldUpdates
  };
};
