import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { arbitrageAPI } from '../../services/api';
import { useWebSocketStore } from '../../services/websocket';
import { formatDistanceToNow } from 'date-fns';
import './ArbitragePanel.css';

const ArbitragePanel = ({ fullView = false }) => {
  const [minProfit, setMinProfit] = useState(0.5);
  const [selectedOpportunity, setSelectedOpportunity] = useState(null);
  
  const arbitrageAlerts = useWebSocketStore((state) => state.arbitrageAlerts);

  const { data: opportunities, isLoading } = useQuery(
    ['arbitrageOpportunities', minProfit],
    () => arbitrageAPI.getOpportunities({ min_profit: minProfit, limit: fullView ? 100 : 10 }),
    {
      refetchInterval: 10000,
      select: (response) => response.data
    }
  );

  // Merge API data with WebSocket updates
  const allOpportunities = React.useMemo(() => {
    const wsOpps = arbitrageAlerts.map(alert => 
      typeof alert === 'string' ? JSON.parse(alert) : alert
    );
    
    const apiOpps = opportunities || [];
    
    // Deduplicate by opportunity_id
    const merged = [...wsOpps, ...apiOpps];
    const unique = merged.reduce((acc, opp) => {
      if (!acc.find(o => o.opportunity_id === opp.opportunity_id)) {
        acc.push(opp);
      }
      return acc;
    }, []);
    
    return unique.sort((a, b) => b.profit_percent - a.profit_percent);
  }, [opportunities, arbitrageAlerts]);

  const displayOpportunities = fullView ? allOpportunities : allOpportunities.slice(0, 5);

  return (
    <div className={`arbitrage-panel ${fullView ? 'full-view' : ''}`}>
      <div className="panel-header">
        <h2>🔍 Arbitrage Opportunities</h2>
        
        <div className="panel-controls">
          <label>
            Min Profit:
            <input
              type="number"
              value={minProfit}
              onChange={(e) => setMinProfit(parseFloat(e.target.value))}
              min="0"
              max="10"
              step="0.1"
              className="profit-input"
            />
            %
          </label>
        </div>
      </div>

      <div className="opportunities-list">
        {isLoading ? (
          <div className="loading">Loading opportunities...</div>
        ) : displayOpportunities.length === 0 ? (
          <div className="empty-state">
            <p>No arbitrage opportunities found</p>
            <p className="empty-subtitle">Try lowering the minimum profit threshold</p>
          </div>
        ) : (
          <AnimatePresence>
            {displayOpportunities.map((opp) => (
              <motion.div
                key={opp.opportunity_id}
                className="opportunity-card"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                whileHover={{ scale: 1.02 }}
                onClick={() => setSelectedOpportunity(opp)}
              >
                <div className="opportunity-header">
                  <span className="token-symbol">{opp.token_symbol}</span>
                  <span className={`profit-badge profit-${getProfitLevel(opp.profit_percent)}`}>
                    +{opp.profit_percent.toFixed(2)}%
                  </span>
                </div>

                <div className="opportunity-body">
                  <div className="exchange-flow">
                    <div className="exchange">
                      <span className="label">Buy</span>
                      <span className="exchange-name">{opp.buy_exchange}</span>
                      <span className="price">${parseFloat(opp.buy_price).toFixed(4)}</span>
                    </div>

                    <div className="arrow">→</div>

                    <div className="exchange">
                      <span className="label">Sell</span>
                      <span className="exchange-name">{opp.sell_exchange}</span>
                      <span className="price">${parseFloat(opp.sell_price).toFixed(4)}</span>
                    </div>
                  </div>

                  <div className="opportunity-metrics">
                    <div className="metric">
                      <span className="metric-label">Net Profit</span>
                      <span className="metric-value">${parseFloat(opp.net_profit).toFixed(2)}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Confidence</span>
                      <span className="metric-value">{(opp.confidence_score * 100).toFixed(0)}%</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Risk</span>
                      <span className={`metric-value risk-${getRiskLevel(opp.risk_score)}`}>
                        {opp.risk_score.toFixed(1)}/10
                      </span>
                    </div>
                  </div>

                  {opp.execution_path && (
                    <div className="execution-path">
                      <span className="path-label">Path:</span>
                      <span className="path-value">{opp.execution_path.join(' → ')}</span>
                    </div>
                  )}

                  <div className="opportunity-footer">
                    <span className="timestamp">
                      {formatDistanceToNow(new Date(opp.timestamp), { addSuffix: true })}
                    </span>
                    <span className="expires">
                      Expires {formatDistanceToNow(new Date(opp.expires_at), { addSuffix: true })}
                    </span>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      {/* Opportunity Detail Modal */}
      {selectedOpportunity && (
        <OpportunityDetailModal
          opportunity={selectedOpportunity}
          onClose={() => setSelectedOpportunity(null)}
        />
      )}
    </div>
  );
};

const OpportunityDetailModal = ({ opportunity, onClose }) => (
  <motion.div
    className="modal-overlay"
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    onClick={onClose}
  >
    <motion.div
      className="modal-content"
      initial={{ scale: 0.9 }}
      animate={{ scale: 1 }}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="modal-header">
        <h3>Arbitrage Opportunity Details</h3>
        <button className="close-btn" onClick={onClose}>×</button>
      </div>

      <div className="modal-body">
        <div className="detail-section">
          <h4>Token & Exchanges</h4>
          <p><strong>Token:</strong> {opportunity.token_symbol}</p>
          <p><strong>Buy from:</strong> {opportunity.buy_exchange} @ ${parseFloat(opportunity.buy_price).toFixed(6)}</p>
          <p><strong>Sell on:</strong> {opportunity.sell_exchange} @ ${parseFloat(opportunity.sell_price).toFixed(6)}</p>
        </div>

        <div className="detail-section">
          <h4>Profitability</h4>
          <p><strong>Gross Profit:</strong> {opportunity.profit_percent.toFixed(2)}%</p>
          <p><strong>Absolute Profit:</strong> ${parseFloat(opportunity.profit_absolute).toFixed(4)}</p>
          <p><strong>Gas Cost:</strong> ${parseFloat(opportunity.estimated_gas_cost).toFixed(4)}</p>
          <p><strong>Net Profit:</strong> ${parseFloat(opportunity.net_profit).toFixed(4)}</p>
        </div>

        <div className="detail-section">
          <h4>Risk Assessment</h4>
          <p><strong>Confidence Score:</strong> {(opportunity.confidence_score * 100).toFixed(1)}%</p>
          <p><strong>Risk Score:</strong> {opportunity.risk_score.toFixed(1)}/10</p>
          <p><strong>Volume Available:</strong> ${parseFloat(opportunity.volume_available).toFixed(2)}</p>
        </div>

        {opportunity.execution_path && (
          <div className="detail-section">
            <h4>Execution Path</h4>
            <div className="execution-diagram">
              {opportunity.execution_path.map((step, index) => (
                <React.Fragment key={index}>
                  <div className="path-step">{step}</div>
                  {index < opportunity.execution_path.length - 1 && (
                    <div className="path-arrow">→</div>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  </motion.div>
);

const getProfitLevel = (profit) => {
  if (profit >= 2) return 'high';
  if (profit >= 1) return 'medium';
  return 'low';
};

const getRiskLevel = (risk) => {
  if (risk <= 3) return 'low';
  if (risk <= 6) return 'medium';
  return 'high';
};

export default ArbitragePanel;
