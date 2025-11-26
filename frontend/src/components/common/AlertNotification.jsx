import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FaCheckCircle, FaExclamationTriangle, FaInfoCircle, FaTimes } from 'react-icons/fa';
import './AlertNotification.css';

const AlertNotification = ({ alerts, onDismiss }) => {
  return (
    <div className="alerts-container">
      <AnimatePresence>
        {alerts.map((alert) => (
          <motion.div
            key={alert.id}
            className={`alert alert-${alert.type}`}
            initial={{ opacity: 0, y: -50, scale: 0.8 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8, transition: { duration: 0.2 } }}
            transition={{ type: 'spring', stiffness: 500, damping: 30 }}
          >
            <div className="alert-icon">
              {alert.type === 'success' && <FaCheckCircle />}
              {alert.type === 'warning' && <FaExclamationTriangle />}
              {alert.type === 'info' && <FaInfoCircle />}
              {alert.type === 'error' && <FaExclamationTriangle />}
            </div>
            
            <div className="alert-content">
              {alert.title && <div className="alert-title">{alert.title}</div>}
              <div className="alert-message">{alert.message}</div>
            </div>
            
            <button
              className="alert-close"
              onClick={() => onDismiss(alert.id)}
            >
              <FaTimes />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

export default AlertNotification;
