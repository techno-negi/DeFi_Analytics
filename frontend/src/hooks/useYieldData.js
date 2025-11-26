import { useQuery } from 'react-query';
import { yieldAPI } from '../services/api';
import { useMemo } from 'react';

export const useYieldData = (chain = null, minApy = 0) => {
  const { data, isLoading, error } = useQuery(
    ['yieldOpportunities', chain, minApy],
    () => yieldAPI.getOpportunities({ chain, min_apy: minApy }),
    {
      refetchInterval: 60000,
      select: (response) => response.data
    }
  );

  const opportunities = data || [];

  // Calculate aggregated statistics
  const stats = useMemo(() => {
    if (opportunities.length === 0) {
      return {
        count: 0,
        avgApy: 0,
        maxApy: 0,
        totalTvl: 0,
        byProtocol: {},
        byChain: {}
      };
    }

    const byProtocol = {};
    const byChain = {};

    opportunities.forEach(opp => {
      // By protocol
      if (!byProtocol[opp.protocol_name]) {
        byProtocol[opp.protocol_name] = {
          count: 0,
          totalTvl: 0,
          avgApy: 0
        };
      }
      byProtocol[opp.protocol_name].count++;
      byProtocol[opp.protocol_name].totalTvl += parseFloat(opp.tvl);
      byProtocol[opp.protocol_name].avgApy += opp.apy;

      // By chain
      if (!byChain[opp.chain]) {
        byChain[opp.chain] = {
          count: 0,
          totalTvl: 0,
          avgApy: 0
        };
      }
      byChain[opp.chain].count++;
      byChain[opp.chain].totalTvl += parseFloat(opp.tvl);
      byChain[opp.chain].avgApy += opp.apy;
    });

    // Calculate averages
    Object.keys(byProtocol).forEach(protocol => {
      byProtocol[protocol].avgApy /= byProtocol[protocol].count;
    });

    Object.keys(byChain).forEach(chain => {
      byChain[chain].avgApy /= byChain[chain].count;
    });

    return {
      count: opportunities.length,
      avgApy: opportunities.reduce((sum, o) => sum + o.apy, 0) / opportunities.length,
      maxApy: Math.max(...opportunities.map(o => o.apy)),
      totalTvl: opportunities.reduce((sum, o) => sum + parseFloat(o.tvl), 0),
      byProtocol,
      byChain
    };
  }, [opportunities]);

  return {
    opportunities,
    stats,
    isLoading,
    error
  };
};
