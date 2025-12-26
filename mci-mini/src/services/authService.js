import api from './api';
import { AUTH_ENDPOINTS } from '../helper/endpoint';
import { saveAuthData, clearAuthData } from '../helper/auth';

// Login as ESN
export const loginESN = async (email, password) => {
  try {
    const response = await api.post(AUTH_ENDPOINTS.LOGIN_ESN, {
      username: email,  // Backend expects 'username' field
      password,
    });
    
    if (response.data) {
      const data = response.data;
      saveAuthData({
        token: data.token,
        userId: data.data?.[0]?.ID_ESN || data.ID_ESN || data.id,
        role: 'esn',
        esnId: data.data?.[0]?.ID_ESN || data.ID_ESN || data.id,
        userName: data.data?.[0]?.Raison_sociale || data.Raison_sociale || 'ESN',
        userEmail: email,
      });
      return { success: true, data };
    }
    return { success: false, error: 'Login failed' };
  } catch (error) {
    console.error('ESN Login error:', error);
    return { 
      success: false, 
      error: error.response?.data?.error || error.response?.data?.msg || error.message || 'Login failed' 
    };
  }
};

// Login as Consultant
export const loginConsultant = async (email, password) => {
  try {
    const response = await api.post(AUTH_ENDPOINTS.LOGIN_CONSULTANT, {
      email,
      password,
    });
    
    if (response.data && response.data.success) {
      const data = response.data;
      const userData = data.data;
      
      saveAuthData({
        token: data.token,
        userId: userData.ID_collab || userData.id,
        role: 'consultant',
        esnId: userData.ID_ESN,
        userName: `${userData.Prenom || ''} ${userData.Nom || ''}`.trim() || 'Consultant',
        userEmail: email,
      });
      return { success: true, data };
    }
    return { success: false, error: 'Login failed' };
  } catch (error) {
    console.error('Consultant Login error:', error);
    return { 
      success: false, 
      error: error.response?.data?.error || error.response?.data?.msg || error.message || 'Login failed' 
    };
  }
};

// Logout
export const logout = () => {
  clearAuthData();
  window.location.href = '/login';
};

export default {
  loginESN,
  loginConsultant,
  logout,
};
