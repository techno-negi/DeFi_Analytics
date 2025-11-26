/**
 * Formatting utilities for display
 */

export const formatCurrency = (value, decimals = 2) => {
  if (value === null || value === undefined) return '$0.00';
  
  const num = typeof value === 'string' ? parseFloat(value) : value;
  
  if (num >= 1_000_000_000) {
    return `$${(num / 1_000_000_000).toFixed(decimals)}B`;
  } else if (num >= 1_000_000) {
    return `$${(num / 1_000_000).toFixed(decimals)}M`;
  } else if (num >= 1_000) {
    return `$${(num / 1_000).toFixed(decimals)}K`;
  }
  
  return `$${num.toFixed(decimals)}`;
};

export const formatPercentage = (value, decimals = 2, showSign = true) => {
  if (value === null || value === undefined) return '0.00%';
  
  const num = typeof value === 'string' ? parseFloat(value) : value;
  const sign = showSign && num > 0 ? '+' : '';
  
  return `${sign}${num.toFixed(decimals)}%`;
};

export const formatNumber = (value, decimals = 2) => {
  if (value === null || value === undefined) return '0';
  
  const num = typeof value === 'string' ? parseFloat(value) : value;
  
  return num.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
};

export const formatAddress = (address, start = 6, end = 4) => {
  if (!address || address.length < start + end) return address;
  
  return `${address.slice(0, start)}...${address.slice(-end)}`;
};

export const formatTimeAgo = (timestamp) => {
  const now = Date.now();
  const diff = now - new Date(timestamp).getTime();
  
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return `${seconds}s ago`;
};

export const formatDuration = (seconds) => {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  if (hrs > 0) {
    return `${hrs}h ${mins}m`;
  } else if (mins > 0) {
    return `${mins}m ${secs}s`;
  }
  return `${secs}s`;
};
