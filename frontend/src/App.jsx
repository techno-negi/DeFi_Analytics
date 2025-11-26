import React, { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import Dashboard from './components/Dashboard/Dashboard';
import { useWebSocketStore } from './services/websocket';
import './styles/app.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000
    }
  }
});

function App() {
  const { connect, disconnect } = useWebSocketStore();

  useEffect(() => {
    // Connect to WebSocket on mount
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return (
    <QueryClientProvider client={queryClient}>
      <div className="app">
        <Dashboard />
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#1f2937',
              color: '#fff',
              borderRadius: '8px'
            },
            success: {
              iconTheme: {
                primary: '#10b981',
                secondary: '#fff'
              }
            },
            error: {
              iconTheme: {
                primary: '#ef4444',
                secondary: '#fff'
              }
            }
          }}
        />
      </div>
    </QueryClientProvider>
  );
}

export default App;
