import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { yieldAPI } from '../../services/api';
import { formatDistanceToNow } from 'date-fns';
import './YieldPanel.css';

const YieldPanel = ({ fullView = false }) => {
  const [selectedChain, setSelectedChain] = useState('all');
  const [minApy, setMinApy] = useState(5.0);
  const [selectedPool, setSelectedPool] = useState(null);

  const { data: opportunities, isLoading } = useQuery(
    ['yieldOpportunities', selectedChain, minApy],
    () => yieldAPI.getOpportunities({
      chain: selectedChain === 'all' ? null : selectedChain,
      min_apy: minApy,
      limit: fullView ? 100 : 10
    }),
    {
      refetchInterval: 60000,
      select: (response) => response.data
    }
  );

  const chains = ['all', 'ethereum', 'bsc', 'polygon', 'arbitrum', 'osmosis'];

  const displayOpportunities = fullView ? opportunities : opportunities?.slice(0, 5);

  return (
    <div className={`yield-panel ${fullView ? 'full-view' : ''}`}>
      <div className="panel-header">
        <h2>💰 Yield Opportunities</h2>
        
        <div className="panel-controls">
          <select
            value={selectedChain}
            onChange={(e) => setSelectedChain(e.target.value)}
            className="chain-select"
          >
            {chains.map(chain => (
              <option key={chain} value={chain}>
                {chain === 'all' ? 'All Chains' : chain.charAt(0).toUpperCase() + chain.slice(1)}
              </option>
            ))}
          </select>

          <label>
            Min APY:
            <input
              type="number"
              value={minApy}
              onChange={(e) => setMinApy(parseFloat(e.target.value))}
              min="0"
              max="1000"
              step="1"
              className="apy-input"
            />
            %
          </label>
        </div>
      </div>

      <div className="opportunities-list">
        {isLoading ? (
          <div className="loading">Loading yield opportunities...</div>
        ) : !displayOpportunities || displayOpportunities.length === 0 ? (
          <div className="empty-state">
            <p>No yield opportunities found</p>
            <p className="empty-subtitle">Try lowering the minimum APY</p>
          </div>
        ) : (
          <AnimatePresence>
            {displayOpportunities.map((opp) => (
              <motion.div
                key={opp.pool_address}
                className="yield-card"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                whileHover={{ scale: 1.02 }}
                onClick={() => setSelectedPool(opp)}
              >
                <div className="yield-header">
                  <div className="pool-info">
                    <span className="protocol-name">{opp.protocol_name}</span>
                    <span className="chain-badge">{opp.chain}</span>
                  </div>
                  <span className={`apy-badge apy-${getApyLevel(opp.apy)}`}>
                    {opp.apy.toFixed(2)}% APY
                  </span>
                </div>

                <div className="token-pair">
                  {opp.token_pair.map((token, idx) => (
                    <React.Fragment key={idx}>
                      <span className="token">{token}</span>
                      {idx < opp.token_pair.length - 1 && <span className="separator">/</span>}
                    </React.Fragment>
                  ))}
                </div>

                <div className="yield-metrics">
                  <div className="metric">
                    <span className="metric-label">TVL</span>
                    <span className="metric-value">${formatNumber(parseFloat(opp.tvl))}</span>
                  </div>
                  <div className="metric">
                    <span className="metric-label">24h Volume</span>
                    <span className="metric-value">${formatNumber(parseFloat(opp.daily_volume))}</span>
                  </div>
                  <div className="metric">
                    <span className="metric-label">IL Risk</span>
                    <span className={`metric-value risk-${getRiskLevel(opp.impermanent_loss_risk)}`}>
                      {opp.impermanent_loss_risk.toFixed(1)}/10
                    </span>
                  </div>
                </div>

                {opp.rewards_tokens && opp.rewards_tokens.length > 0 && (
                  <div className="rewards">
                    <span className="rewards-label">Rewards:</span>
                    {opp.rewards_tokens.map((token, idx) => (
                      <span key={idx} className="reward-token">{token}</span>
                    ))}
                  </div>
                )}

                <div className="yield-footer">
                  <span className="entry-barrier">
                    Min: ${formatNumber(parseFloat(opp.entry_barrier))}
                  </span>
                  <span className="timestamp">
                    Updated {formatDistanceToNow(new Date(opp.timestamp), { addSuffix: true })}
                  </span>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      {selectedPool && (
        <PoolDetailModal
          pool={selectedPool}
          onClose={() => setSelectedPool(null)}
        />
      )}
    </div>
  );
};

const PoolDetailModal = ({ pool, onClose }) => (
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
        <h3>Yield Pool Details</h3>
        <button className="close-btn" onClick={onClose}>×</button>
      </div>

      <div className="modal-body">
        <div className="detail-section">
          <h4>Pool Information</h4>
          <p><strong>Protocol:</strong> {pool.protocol_name}</p>
          <p><strong>Chain:</strong> {pool.chain}</p>
          <p><strong>Token Pair:</strong> {pool.token_pair.join(' / ')}</p>
          <p><strong>Pool Address:</strong> <code>{pool.pool_address}</code></p>
        </div>

        <div className="detail-section">
          <h4>Returns</h4>
          <p><strong>APY:</strong> {pool.apy.toFixed(2)}%</p>
          <p><strong>Reward Tokens:</strong> {pool.rewards_tokens.join(', ') || 'None'}</p>
          <p>
            <strong>Daily Earnings (per $1000):</strong> $
            {((pool.apy / 100 / 365) * 1000).toFixed(2)}
          </p>
        </div>

        <div className="detail-section">
          <h4>Liquidity & Volume</h4>
          <p><strong>TVL:</strong> ${formatNumber(parseFloat(pool.tvl))}</p>
          <p><strong>24h Volume:</strong> ${formatNumber(parseFloat(pool.daily_volume))}</p>
          <p><strong>Liquidity Depth:</strong> ${formatNumber(parseFloat(pool.liquidity_depth))}</p>
        </div>

        <div className="detail-section">
          <h4>Risk Assessment</h4>
          <p>
            <strong>Impermanent Loss Risk:</strong>{' '}
            <span className={`risk-${getRiskLevel(pool.impermanent_loss_risk)}`}>
              {pool.impermanent_loss_risk.toFixed(1)}/10
            </span>
          </p>
          <p><strong>Entry Barrier:</strong> ${formatNumber(parseFloat(pool.entry_barrier))}</p>
        </div>
      </div>
    </motion.div>
  </motion.div>
);

const getApyLevel = (apy) => {
  if (apy >= 50) return 'high';
  if (apy >= 20) return 'medium';
  return 'low';
};

const getRiskLevel = (risk) => {
  if (risk <= 3) return 'low';
  if (risk <= 6) return 'medium';
  return 'high';
};

const formatNumber = (num) => {
  if (num >= 1_000_000_000) return `${(num / 1_000_000_000).toFixed(2)}B`;
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(2)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(2)}K`;
  return num.toFixed(2);
};

export default YieldPanel;
