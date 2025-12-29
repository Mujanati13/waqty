import axios from 'axios';
import { getAuthToken } from '../helper/auth';
import { API_BASE_URL } from '../helper/endpoint';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  withCredentials: true, // Enable sending credentials with cross-origin requests
  timeout: 30000, // 30 second timeout
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle network errors
    if (!error.response) {
      console.error('Network error:', error.message);
      return Promise.reject(new Error('Network error. Please check your connection.'));
    }
    
    if (error.response?.status === 401) {
      // Token expired or invalid - redirect to login
      localStorage.clear();
      window.location.href = '/login';
    }
    
    // Handle CORS errors
    if (error.response?.status === 0 || error.code === 'ERR_NETWORK') {
      console.error('CORS or network error:', error);
      return Promise.reject(new Error('Connection error. Please try again.'));
    }
    
    return Promise.reject(error);
  }
);

export default api;
