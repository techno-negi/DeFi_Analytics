import React, { useState, useEffect } from 'react';
import { useQuery } from 'react-query';
import { motion } from 'framer-motion';
import Header from '../common/Header';
import Sidebar from '../common/Sidebar';
import ArbitragePanel from './ArbitragePanel';
import YieldPanel from './YieldPanel';
import RiskPanel from './RiskPanel';
import PriceChart from './PriceChart';
import { marketAPI } from '../../services/api';
import { useWebSocketStore } from '../../services/websocket';
import './Dashboard.css';

const Dashboard = () => {
  const [activeView, setActiveView] = useState('overview');
  const { connected, subscribe } = useWebSocketStore();

  // Subscribe to WebSocket channels
  useEffect(() => {
    if (connected) {
      subscribe(['prices', 'arbitrage', 'yield']);
    }
  }, [connected, subscribe]);

  // Fetch market overview
  const { data: marketOverview, isLoading } = useQuery(
    'marketOverview',
    () => marketAPI.getOverview(),
    {
      refetchInterval: 60000, // Refetch every minute
      select: (response) => response.data
    }
  );

  const renderContent = () => {
    switch (activeView) {
      case 'overview':
        return (
          <div className="dashboard-grid">
            <div className="stats-row">
              <StatsCard
                title="Arbitrage Opportunities"
                value={marketOverview?.arbitrage?.count || 0}
                subtitle={`Best: ${marketOverview?.arbitrage?.best_profit?.toFixed(2) || 0}%`}
                trend="up"
                color="green"
              />
              <StatsCard
                title="Yield Opportunities"
                value={marketOverview?.yield?.count || 0}
                subtitle={`Best APY: ${marketOverview?.yield?.best_apy?.toFixed(2) || 0}%`}
                trend="up"
                color="blue"
              />
              <StatsCard
                title="WebSocket Status"
                value={connected ? 'Connected' : 'Disconnected'}
                subtitle="Real-time data stream"
                trend={connected ? 'up' : 'down'}
                color={connected ? 'green' : 'red'}
              />
            </div>

            <div className="panels-row">
              <ArbitragePanel />
              <YieldPanel />
            </div>

            <div className="chart-row">
              <PriceChart symbol="BTC/USDT" />
            </div>
          </div>
        );
      
      case 'arbitrage':
        return <ArbitragePanel fullView />;
      
      case 'yield':
        return <YieldPanel fullView />;
      
      case 'risk':
        return <RiskPanel />;
      
      default:
        return null;
    }
  };

  return (
    <div className="dashboard">
      <Sidebar activeView={activeView} setActiveView={setActiveView} />
      
      <div className="dashboard-main">
        <Header />
        
        <div className="dashboard-content">
          {isLoading ? (
            <div className="loading-spinner">Loading...</div>
          ) : (
            <motion.div
              key={activeView}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              {renderContent()}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
};

const StatsCard = ({ title, value, subtitle, trend, color }) => (
  <motion.div
    className={`stats-card stats-card-${color}`}
    whileHover={{ scale: 1.02 }}
    transition={{ type: 'spring', stiffness: 300 }}
  >
    <div className="stats-header">
      <h3>{title}</h3>
      <span className={`trend trend-${trend}`}>
        {trend === 'up' ? '↑' : '↓'}
      </span>
    </div>
    <div className="stats-value">{value}</div>
    <div className="stats-subtitle">{subtitle}</div>
  </motion.div>
);

export default Dashboard;
