import React from 'react';
import { motion } from 'framer-motion';
import './HeatMap.css';

const HeatMap = ({ data, title = 'Market Heat Map' }) => {
  if (!data || data.length === 0) {
    return <div className="heatmap-empty">No data available</div>;
  }

  // Calculate min/max for color scaling
  const values = data.map(d => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);

  const getColor = (value) => {
    const normalized = (value - min) / (max - min);
    
    if (normalized > 0.66) {
      // Green (high values)
      return `rgba(16, 185, 129, ${0.3 + normalized * 0.7})`;
    } else if (normalized > 0.33) {
      // Yellow (medium values)
      return `rgba(245, 158, 11, ${0.3 + normalized * 0.7})`;
    } else {
      // Red (low values)
      return `rgba(239, 68, 68, ${0.3 + normalized * 0.7})`;
    }
  };

  return (
    <div className="heatmap-container">
      <h3 className="heatmap-title">{title}</h3>
      
      <div className="heatmap-grid">
        {data.map((item, index) => (
          <motion.div
            key={index}
            className="heatmap-cell"
            style={{ backgroundColor: getColor(item.value) }}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.02 }}
            whileHover={{ scale: 1.05, zIndex: 10 }}
          >
            <div className="cell-label">{item.label}</div>
            <div className="cell-value">{item.value.toFixed(2)}%</div>
          </motion.div>
        ))}
      </div>

      <div className="heatmap-legend">
        <span>Low</span>
        <div className="legend-gradient"></div>
        <span>High</span>
      </div>
    </div>
  );
};

export default HeatMap;
