/**
 * Data processing utilities for transforming API responses
 */

export const processArbitrageData = (opportunities) => {
  return opportunities.map(opp => ({
    ...opp,
    netProfitUsd: parseFloat(opp.net_profit),
    profitPercent: parseFloat(opp.profit_percent),
    volumeUsd: parseFloat(opp.volume_available),
    gasUsd: parseFloat(opp.estimated_gas_cost),
    executionPath: Array.isArray(opp.execution_path) ? opp.execution_path : []
  }));
};

export const processYieldData = (opportunities) => {
  return opportunities.map(opp => ({
    ...opp,
    apy: parseFloat(opp.apy),
    tvl: parseFloat(opp.tvl),
    dailyVolume: parseFloat(opp.daily_volume),
    ilRisk: parseFloat(opp.impermanent_loss_risk),
    entryBarrier: parseFloat(opp.entry_barrier)
  }));
};

export const aggregateByExchange = (data) => {
  const aggregated = {};
  
  data.forEach(item => {
    const exchange = item.exchange || item.buy_exchange;
    
    if (!aggregated[exchange]) {
      aggregated[exchange] = {
        count: 0,
        totalVolume: 0,
        opportunities: []
      };
    }
    
    aggregated[exchange].count++;
    aggregated[exchange].totalVolume += parseFloat(item.volume_available || 0);
    aggregated[exchange].opportunities.push(item);
  });
  
  return aggregated;
};

export const calculatePortfolioMetrics = (allocations) => {
  const total = Object.values(allocations).reduce((sum, val) => sum + val, 0);
  
  return {
    totalAllocated: total,
    count: Object.keys(allocations).length,
    largest: Math.max(...Object.values(allocations)),
    smallest: Math.min(...Object.values(allocations)),
    average: total / Object.keys(allocations).length
  };
};
