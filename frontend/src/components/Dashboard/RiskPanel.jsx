import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { motion } from 'framer-motion';
import { riskAPI } from '../../services/api';
import { FaShieldAlt, FaExclamationTriangle, FaCheckCircle } from 'react-icons/fa';
import './RiskPanel.css';

const RiskPanel = () => {
  const [selectedProtocol, setSelectedProtocol] = useState('Aave');

  const protocols = [
    'Aave', 'Compound', 'Uniswap_V3', 'Curve', 
    'SushiSwap', 'PancakeSwap', 'Osmosis'
  ];

  const { data: riskAssessment, isLoading } = useQuery(
    ['riskAssessment', selectedProtocol],
    () => riskAPI.getAssessment(selectedProtocol),
    {
      enabled: !!selectedProtocol,
      select: (response) => response.data
    }
  );

  return (
    <div className="risk-panel">
      <div className="panel-header">
        <h2><FaShieldAlt /> Risk Assessment</h2>
        
        <select
          value={selectedProtocol}
          onChange={(e) => setSelectedProtocol(e.target.value)}
          className="protocol-select"
        >
          {protocols.map(protocol => (
            <option key={protocol} value={protocol}>{protocol}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="loading">Analyzing risk...</div>
      ) : riskAssessment ? (
        <div className="risk-content">
          {/* Overall Risk Score */}
          <div className="overall-risk">
            <div className="risk-score-container">
              <RiskGauge score={riskAssessment.overall_risk_score} />
              <div className="risk-label">
                <span className="score">{riskAssessment.overall_risk_score.toFixed(1)}</span>
                <span className="out-of">/10</span>
              </div>
            </div>
            <div className="risk-classification">
              <span className={`risk-level risk-${getRiskCategory(riskAssessment.overall_risk_score)}`}>
                {getRiskCategory(riskAssessment.overall_risk_score).toUpperCase()} RISK
              </span>
            </div>
          </div>

          {/* Risk Breakdown */}
          <div className="risk-breakdown">
            <h3>Risk Factors</h3>
            
            <RiskFactor
              label="Smart Contract"
              score={riskAssessment.smart_contract_risk}
              icon={<FaShieldAlt />}
            />
            
            <RiskFactor
              label="Liquidity"
              score={riskAssessment.liquidity_risk}
              icon={<FaShieldAlt />}
            />
            
            <RiskFactor
              label="Volatility"
              score={riskAssessment.volatility_risk}
              icon={<FaExclamationTriangle />}
            />
            
            <RiskFactor
              label="Market"
              score={riskAssessment.market_risk}
              icon={<FaExclamationTriangle />}
            />
            
            <RiskFactor
              label="Concentration"
              score={riskAssessment.concentration_risk}
              icon={<FaExclamationTriangle />}
            />
          </div>

          {/* Protocol Info */}
          <div className="protocol-info">
            <h3>Protocol Information</h3>
            
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Asset:</span>
                <span className="info-value">{riskAssessment.asset_symbol}</span>
              </div>
              
              <div className="info-item">
                <span className="info-label">Audit Status:</span>
                <span className={`info-value ${riskAssessment.audit_status ? 'audited' : 'not-audited'}`}>
                  {riskAssessment.audit_status ? (
                    <><FaCheckCircle /> Audited</>
                  ) : (
                    <><FaExclamationTriangle /> Not Audited</>
                  )}
                </span>
              </div>
              
              <div className="info-item">
                <span className="info-label">Exploits History:</span>
                <span className={`info-value ${riskAssessment.exploits_history === 0 ? 'safe' : 'warning'}`}>
                  {riskAssessment.exploits_history} exploit{riskAssessment.exploits_history !== 1 ? 's' : ''}
                </span>
              </div>
              
              <div className="info-item">
                <span className="info-label">Time in Market:</span>
                <span className="info-value">{riskAssessment.time_in_market_days} days</span>
              </div>
            </div>
          </div>

          {/* Recommendations */}
          <div className="recommendations">
            <h3>Risk Mitigation Recommendations</h3>
            <ul>
              {riskAssessment.recommendations.map((rec, idx) => (
                <motion.li
                  key={idx}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.1 }}
                >
                  {rec}
                </motion.li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <div className="empty-state">No risk data available</div>
      )}
    </div>
  );
};

const RiskGauge = ({ score }) => {
  const percentage = (score / 10) * 100;
  const rotation = (percentage / 100) * 180 - 90;
  
  return (
    <svg className="risk-gauge" viewBox="0 0 200 120">
      <defs>
        <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#10b981" />
          <stop offset="50%" stopColor="#f59e0b" />
          <stop offset="100%" stopColor="#ef4444" />
        </linearGradient>
      </defs>
      
      {/* Background arc */}
      <path
        d="M 20 100 A 80 80 0 0 1 180 100"
        fill="none"
        stroke="#374151"
        strokeWidth="20"
        strokeLinecap="round"
      />
      
      {/* Progress arc */}
      <path
        d="M 20 100 A 80 80 0 0 1 180 100"
        fill="none"
        stroke="url(#gaugeGradient)"
        strokeWidth="20"
        strokeLinecap="round"
        strokeDasharray={`${percentage * 2.51}, 251`}
      />
      
      {/* Needle */}
      <line
        x1="100"
        y1="100"
        x2="100"
        y2="30"
        stroke="#ffffff"
        strokeWidth="3"
        strokeLinecap="round"
        transform={`rotate(${rotation} 100 100)`}
      />
      
      <circle cx="100" cy="100" r="8" fill="#ffffff" />
    </svg>
  );
};

const RiskFactor = ({ label, score, icon }) => {
  const percentage = (score / 10) * 100;
  
  return (
    <div className="risk-factor">
      <div className="factor-header">
        <span className="factor-icon">{icon}</span>
        <span className="factor-label">{label}</span>
        <span className={`factor-score risk-${getRiskCategory(score)}`}>
          {score.toFixed(1)}
        </span>
      </div>
      <div className="factor-bar">
        <motion.div
          className={`factor-fill risk-${getRiskCategory(score)}`}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
    </div>
  );
};

const getRiskCategory = (score) => {
  if (score <= 3) return 'low';
  if (score <= 6) return 'medium';
  return 'high';
};

export default RiskPanel;
