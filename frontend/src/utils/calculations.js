/**
 * Calculation utilities for financial metrics
 */

export const calculateROI = (initialInvestment, finalValue) => {
  if (initialInvestment === 0) return 0;
  return ((finalValue - initialInvestment) / initialInvestment) * 100;
};

export const calculateAPY = (rate, compoundFrequency = 365) => {
  // APY = (1 + r/n)^n - 1
  return (Math.pow(1 + rate / compoundFrequency, compoundFrequency) - 1) * 100;
};

export const calculateCompoundInterest = (principal, rate, time, frequency = 365) => {
  // A = P(1 + r/n)^(nt)
  return principal * Math.pow(1 + rate / frequency, frequency * time);
};

export const calculateImpermanentLoss = (priceRatio) => {
  // IL = 2 * sqrt(priceRatio) / (1 + priceRatio) - 1
  const sqrtRatio = Math.sqrt(priceRatio);
  return (2 * sqrtRatio / (1 + priceRatio) - 1) * 100;
};

export const calculateSharpeRatio = (returns, riskFreeRate = 0.02) => {
  if (returns.length === 0) return 0;
  
  const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
  const variance = returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length;
  const stdDev = Math.sqrt(variance);
  
  if (stdDev === 0) return 0;
  
  return (avgReturn - riskFreeRate) / stdDev;
};

export const calculateVolatility = (prices) => {
  if (prices.length < 2) return 0;
  
  const returns = [];
  for (let i = 1; i < prices.length; i++) {
    returns.push((prices[i] - prices[i - 1]) / prices[i - 1]);
  }
  
  const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
  const variance = returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length;
  
  return Math.sqrt(variance) * 100; // As percentage
};

export const calculateMovingAverage = (values, period) => {
  if (values.length < period) return values;
  
  const result = [];
  for (let i = period - 1; i < values.length; i++) {
    const sum = values.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
    result.push(sum / period);
  }
  
  return result;
};

export const calculateRSI = (prices, period = 14) => {
  if (prices.length < period + 1) return 50;
  
  let gains = 0;
  let losses = 0;
  
  for (let i = 1; i <= period; i++) {
    const change = prices[i] - prices[i - 1];
    if (change > 0) {
      gains += change;
    } else {
      losses += Math.abs(change);
    }
  }
  
  const avgGain = gains / period;
  const avgLoss = losses / period;
  
  if (avgLoss === 0) return 100;
  
  const rs = avgGain / avgLoss;
  return 100 - (100 / (1 + rs));
};
