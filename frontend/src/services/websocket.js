import { create } from 'zustand';
import toast from 'react-hot-toast';

const WS_URL = process.env.WS_URL || 'ws://localhost:8000/ws';

export const useWebSocketStore = create((set, get) => ({
  ws: null,
  connected: false,
  priceUpdates: [],
  arbitrageAlerts: [],
  yieldUpdates: [],
  subscriptions: new Set(),

  connect: () => {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('WebSocket connected');
      set({ connected: true, ws });
      toast.success('Connected to real-time data stream');
      
      // Resubscribe to previous subscriptions
      const { subscriptions } = get();
      if (subscriptions.size > 0) {
        ws.send(JSON.stringify({
          type: 'subscribe',
          channels: Array.from(subscriptions)
        }));
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      set({ connected: false, ws: null });
      toast.error('Disconnected from data stream');
      
      // Attempt reconnection after 5 seconds
      setTimeout(() => {
        const { connect } = get();
        connect();
      }, 5000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      toast.error('WebSocket connection error');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'connected':
            console.log('WebSocket welcome:', data.message);
            break;
          
          case 'price_update':
            set((state) => ({
              priceUpdates: [data.data, ...state.priceUpdates].slice(0, 100)
            }));
            break;
          
          case 'arbitrage_alert':
            set((state) => ({
              arbitrageAlerts: [data.data, ...state.arbitrageAlerts].slice(0, 50)
            }));
            
            // Show toast for high-profit opportunities
            if (data.data.profit_percent > 2.0) {
              toast.success(
                `New arbitrage: ${data.data.token_symbol} - ${data.data.profit_percent.toFixed(2)}% profit`,
                { duration: 6000 }
              );
            }
            break;
          
          case 'yield_update':
            set((state) => ({
              yieldUpdates: [data.data, ...state.yieldUpdates].slice(0, 50)
            }));
            break;
          
          case 'subscribed':
            console.log('Subscribed to channels:', data.channels);
            break;
          
          case 'pong':
            console.log('Pong received');
            break;
          
          default:
            console.log('Unknown message type:', data.type);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    set({ ws });
  },

  disconnect: () => {
    const { ws } = get();
    if (ws) {
      ws.close();
      set({ ws: null, connected: false });
    }
  },

  subscribe: (channels) => {
    const { ws, subscriptions } = get();
    
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'subscribe',
        channels
      }));
      
      const newSubscriptions = new Set([...subscriptions, ...channels]);
      set({ subscriptions: newSubscriptions });
    }
  },

  unsubscribe: (channels) => {
    const { ws, subscriptions } = get();
    
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'unsubscribe',
        channels
      }));
      
      const newSubscriptions = new Set(subscriptions);
      channels.forEach(ch => newSubscriptions.delete(ch));
      set({ subscriptions: newSubscriptions });
    }
  },

  sendPing: () => {
    const { ws } = get();
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }));
    }
  }
}));

// Heartbeat mechanism
setInterval(() => {
  const { sendPing, connected } = useWebSocketStore.getState();
  if (connected) {
    sendPing();
  }
}, 30000); // Every 30 seconds
