import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
});

export const fetchDashboard = () => api.get('/api/dashboard').then(r => r.data);
export const fetchStocks = () => api.get('/api/stocks/').then(r => r.data);
export const fetchStockDetail = (symbol) => api.get(`/api/stocks/${symbol}`).then(r => r.data);
export const fetchNews = (symbol = null, limit = 50) => {
  const params = { limit };
  if (symbol) params.symbol = symbol;
  return api.get('/api/news/', { params }).then(r => r.data);
};
export const fetchMacro = () => api.get('/api/macro/latest').then(r => r.data);
export const fetchTrending = () => api.get('/api/stocks/trending').then(r => r.data);
export const triggerRefresh = () => api.post('/api/sentiment/refresh').then(r => r.data);

export default api;
