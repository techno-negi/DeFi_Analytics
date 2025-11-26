import React, { useState, useEffect } from 'react';
import { useQuery } from 'react-query';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { priceAPI } from '../../services/api';
import { useWebSocketStore } from '../../services/websocket';
import { format } from 'date-fns';
import './PriceChart.css';

const PriceChart = ({ symbol = 'BTC/USDT' }) => {
  const [timeRange, setTimeRange] = useState('24h');
  const [chartData, setChartData] = useState([]);
  const [livePrice, setLivePrice] = useState(null);

  const priceUpdates = useWebSocketStore((state) => state.priceUpdates);

  // Fetch historical data
  const { data: historyData, isLoading } = useQuery(
    ['priceHistory', symbol, timeRange],
    () => priceAPI.getPriceHistory(symbol, {
      hours: getHoursFromRange(timeRange)
    }),
    {
      refetchInterval: 60000,
      select: (response) => response.data.data
    }
  );

  // Update chart data when history loads
  useEffect(() => {
    if (historyData) {
      const formatted = historyData.map(item => ({
        time: new Date(item.timestamp).getTime(),
        price: parseFloat(item.price),
        volume: parseFloat(item.volume_24h)
      })).sort((a, b) => a.time - b.time);
      
      setChartData(formatted);
    }
  }, [historyData]);

  // Update with live WebSocket data
  useEffect(() => {
    if (priceUpdates.length > 0) {
      const latestUpdate = priceUpdates[0];
      
      if (typeof latestUpdate === 'string') {
        try {
          const parsed = JSON.parse(latestUpdate);
          if (parsed.symbol === symbol) {
            setLivePrice(parseFloat(parsed.price));
            
            // Add to chart data
            setChartData(prev => {
              const newData = [...prev, {
                time: new Date(parsed.timestamp).getTime(),
                price: parseFloat(parsed.price),
                volume: parseFloat(parsed.volume_24h || 0)
              }];
              
              // Keep last 100 points
              return newData.slice(-100);
            });
          }
        } catch (e) {
          console.error('Error parsing price update:', e);
        }
      }
    }
  }, [priceUpdates, symbol]);

  const timeRanges = ['1h', '4h', '24h', '7d', '30d'];

  const priceChange = chartData.length >= 2
    ? ((chartData[chartData.length - 1].price - chartData[0].price) / chartData[0].price) * 100
    : 0;

  const currentPrice = livePrice || (chartData.length > 0 ? chartData[chartData.length - 1].price : 0);

  return (
    <div className="price-chart-container">
      <div className="chart-header">
        <div className="price-info">
          <h3>{symbol}</h3>
          <div className="current-price">
            ${currentPrice.toFixed(2)}
            <span className={`price-change ${priceChange >= 0 ? 'positive' : 'negative'}`}>
              {priceChange >= 0 ? '▲' : '▼'} {Math.abs(priceChange).toFixed(2)}%
            </span>
          </div>
        </div>

        <div className="time-range-selector">
          {timeRanges.map(range => (
            <button
              key={range}
              className={`range-btn ${timeRange === range ? 'active' : ''}`}
              onClick={() => setTimeRange(range)}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      <div className="chart-content">
        {isLoading ? (
          <div className="loading">Loading chart data...</div>
        ) : chartData.length === 0 ? (
          <div className="empty-state">No price data available</div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              
              <XAxis
                dataKey="time"
                tickFormatter={(time) => format(new Date(time), 'HH:mm')}
                stroke="#9ca3af"
              />
              
              <YAxis
                domain={['auto', 'auto']}
                tickFormatter={(value) => `$${value.toFixed(2)}`}
                stroke="#9ca3af"
              />
              
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '8px'
                }}
                labelFormatter={(time) => format(new Date(time), 'PPpp')}
                formatter={(value) => [`$${value.toFixed(2)}`, 'Price']}
              />
              
              <Area
                type="monotone"
                dataKey="price"
                stroke="#3b82f6"
                strokeWidth={2}
                fill="url(#priceGradient)"
                animationDuration={300}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {chartData.length > 0 && (
        <div className="chart-stats">
          <div className="stat">
            <span className="stat-label">High</span>
            <span className="stat-value">${Math.max(...chartData.map(d => d.price)).toFixed(2)}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Low</span>
            <span className="stat-value">${Math.min(...chartData.map(d => d.price)).toFixed(2)}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Avg</span>
            <span className="stat-value">
              ${(chartData.reduce((sum, d) => sum + d.price, 0) / chartData.length).toFixed(2)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

const getHoursFromRange = (range) => {
  switch (range) {
    case '1h': return 1;
    case '4h': return 4;
    case '24h': return 24;
    case '7d': return 168;
    case '30d': return 720;
    default: return 24;
  }
};

export default PriceChart;
