import React from 'react';
import { motion } from 'framer-motion';
import {
  FaHome,
  FaExchangeAlt,
  FaChartLine,
  FaShieldAlt,
  FaHistory,
  FaCog
} from 'react-icons/fa';
import './Sidebar.css';

const Sidebar = ({ activeView, setActiveView }) => {
  const menuItems = [
    { id: 'overview', label: 'Overview', icon: <FaHome /> },
    { id: 'arbitrage', label: 'Arbitrage', icon: <FaExchangeAlt /> },
    { id: 'yield', label: 'Yield Farming', icon: <FaChartLine /> },
    { id: 'risk', label: 'Risk Analysis', icon: <FaShieldAlt /> },
    { id: 'history', label: 'History', icon: <FaHistory /> },
    { id: 'settings', label: 'Settings', icon: <FaCog /> }
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">📊</div>
        <span className="logo-text">DeFi</span>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <motion.button
            key={item.id}
            className={`nav-item ${activeView === item.id ? 'active' : ''}`}
            onClick={() => setActiveView(item.id)}
            whileHover={{ x: 5 }}
            whileTap={{ scale: 0.95 }}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
            
            {activeView === item.id && (
              <motion.div
                className="active-indicator"
                layoutId="activeIndicator"
                initial={false}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              />
            )}
          </motion.button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="footer-stats">
          <div className="stat-item">
            <span className="stat-label">Active Since</span>
            <span className="stat-value">Today</span>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
