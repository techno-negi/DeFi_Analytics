import React, { useState } from 'react';
import { FaBell, FaWifi, FaCog, FaUser } from 'react-icons/fa';
import { useWebSocketStore } from '../../services/websocket';
import { useQuery } from 'react-query';
import { systemAPI } from '../../services/api';
import './Header.css';

const Header = () => {
  const [showNotifications, setShowNotifications] = useState(false);
  const connected = useWebSocketStore((state) => state.connected);
  const arbitrageAlerts = useWebSocketStore((state) => state.arbitrageAlerts);

  const { data: systemInfo } = useQuery(
    'systemInfo',
    () => systemAPI.getInfo(),
    {
      refetchInterval: 30000,
      select: (response) => response.data
    }
  );

  const unreadCount = arbitrageAlerts.length;

  return (
    <header className="app-header">
      <div className="header-left">
        <h1 className="app-title">DeFi Analytics</h1>
        <span className="version">v{systemInfo?.version || '1.0.0'}</span>
      </div>

      <div className="header-right">
        {/* Connection Status */}
        <div className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
          <FaWifi />
          <span>{connected ? 'Live' : 'Offline'}</span>
        </div>

        {/* Notifications */}
        <div className="notifications">
          <button
            className="icon-btn"
            onClick={() => setShowNotifications(!showNotifications)}
          >
            <FaBell />
            {unreadCount > 0 && (
              <span className="notification-badge">{unreadCount}</span>
            )}
          </button>

          {showNotifications && (
            <div className="notifications-dropdown">
              <div className="dropdown-header">
                <h3>Notifications</h3>
                <span className="notification-count">{unreadCount} new</span>
              </div>
              
              <div className="notifications-list">
                {unreadCount === 0 ? (
                  <div className="empty-notifications">
                    No new notifications
                  </div>
                ) : (
                  arbitrageAlerts.slice(0, 5).map((alert, idx) => {
                    const data = typeof alert === 'string' ? JSON.parse(alert) : alert;
                    return (
                      <div key={idx} className="notification-item">
                        <div className="notification-icon">💰</div>
                        <div className="notification-content">
                          <div className="notification-title">
                            New Arbitrage: {data.token_symbol}
                          </div>
                          <div className="notification-subtitle">
                            {data.profit_percent?.toFixed(2)}% profit opportunity
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>

        {/* Settings */}
        <button className="icon-btn">
          <FaCog />
        </button>

        {/* User */}
        <button className="icon-btn user-btn">
          <FaUser />
        </button>
      </div>
    </header>
  );
};

export default Header;
