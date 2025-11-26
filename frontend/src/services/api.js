import axios from 'axios';

const API_BASE_URL = process.env.API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Arbitrage API
export const arbitrageAPI = {
  getOpportunities: (params) => 
    api.get('/api/v1/arbitrage/opportunities', { params }),
  
  getOpportunity: (id) => 
    api.get(`/api/v1/arbitrage/opportunities/${id}`),
  
  getStats: () => 
    api.get('/api/v1/arbitrage/stats')
};

// Yield API
export const yieldAPI = {
  getOpportunities: (params) => 
    api.get('/api/v1/yield/opportunities', { params }),
  
  optimizePortfolio: (data) => 
    api.post('/api/v1/yield/optimize', data)
};

// Risk API
export const riskAPI = {
  getAssessment: (protocol) => 
    api.get(`/api/v1/risk/assessment/${protocol}`)
};

// Price API
export const priceAPI = {
  getCurrentPrice: (symbol, exchange) => 
    api.get(`/api/v1/prices/${symbol}`, { params: { exchange } }),
  
  getPriceHistory: (symbol, params) => 
    api.get(`/api/v1/prices/${symbol}/history`, { params })
};

// Market API
export const marketAPI = {
  getOverview: () => 
    api.get('/api/v1/market/overview')
};

// System API
export const systemAPI = {
  getHealth: () => 
    api.get('/api/health'),
  
  getInfo: () => 
    api.get('/api/v1/system/info')
};

export default api;
