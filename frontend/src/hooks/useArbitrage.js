import { useQuery } from 'react-query';
import { arbitrageAPI } from '../services/api';
import { useWebSocketStore } from '../services/websocket';
import { useMemo } from 'react';

export const useArbitrage = (minProfit = 0.5, limit = 50) => {
  // Fetch from API
  const { data, isLoading, error, refetch } = useQuery(
    ['arbitrageOpportunities', minProfit, limit],
    () => arbitrageAPI.getOpportunities({ min_profit: minProfit, limit }),
    {
      refetchInterval: 10000,
      select: (response) => response.data
    }
  );

  // Get WebSocket updates
  const wsAlerts = useWebSocketStore((state) => state.arbitrageAlerts);

  // Merge API data with WebSocket updates
  const opportunities = useMemo(() => {
    const wsOpps = wsAlerts.map(alert => {
      try {
        return typeof alert === 'string' ? JSON.parse(alert) : alert;
      } catch (e) {
        return null;
      }
    }).filter(Boolean);

    const apiOpps = data || [];
    
    // Deduplicate by opportunity_id
    const merged = [...wsOpps, ...apiOpps];
    const unique = merged.reduce((acc, opp) => {
      if (!acc.find(o => o.opportunity_id === opp.opportunity_id)) {
        acc.push(opp);
      }
      return acc;
    }, []);

    return unique.sort((a, b) => b.profit_percent - a.profit_percent);
  }, [data, wsAlerts]);

  // Calculate statistics
  const stats = useMemo(() => {
    if (opportunities.length === 0) {
      return {
        count: 0,
        avgProfit: 0,
        maxProfit: 0,
        totalVolume: 0
      };
    }

    return {
      count: opportunities.length,
      avgProfit: opportunities.reduce((sum, o) => sum + o.profit_percent, 0) / opportunities.length,
      maxProfit: Math.max(...opportunities.map(o => o.profit_percent)),
      totalVolume: opportunities.reduce((sum, o) => sum + parseFloat(o.volume_available), 0)
    };
  }, [opportunities]);

  return {
    opportunities,
    stats,
    isLoading,
    error,
    refetch
  };
};
