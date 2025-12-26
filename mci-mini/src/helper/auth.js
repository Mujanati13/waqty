// Authentication Helper Functions

// Storage Keys
const STORAGE_KEYS = {
  TOKEN: 'mci_token',
  USER_ID: 'mci_user_id',
  USER_ROLE: 'mci_user_role',
  ESN_ID: 'mci_esn_id',
  ESN_NAME: 'mci_esn_name',
  USER_NAME: 'mci_user_name',
  USER_EMAIL: 'mci_user_email',
};

// Save authentication data after login
export const saveAuthData = (data) => {
  if (data.token) localStorage.setItem(STORAGE_KEYS.TOKEN, data.token);
  if (data.userId) localStorage.setItem(STORAGE_KEYS.USER_ID, data.userId);
  if (data.role) localStorage.setItem(STORAGE_KEYS.USER_ROLE, data.role);
  if (data.esnId) localStorage.setItem(STORAGE_KEYS.ESN_ID, String(data.esnId));
  if (data.esnName) localStorage.setItem(STORAGE_KEYS.ESN_NAME, data.esnName);
  if (data.userName) localStorage.setItem(STORAGE_KEYS.USER_NAME, data.userName);
  if (data.userEmail) localStorage.setItem(STORAGE_KEYS.USER_EMAIL, data.userEmail);
};

// Clear all auth data (logout)
export const clearAuthData = () => {
  Object.values(STORAGE_KEYS).forEach(key => localStorage.removeItem(key));
};

// Get stored auth token
export const getAuthToken = () => {
  return localStorage.getItem(STORAGE_KEYS.TOKEN);
};

// Get current user ID
export const getUserId = () => {
  return localStorage.getItem(STORAGE_KEYS.USER_ID);
};

// Get current user role (esn, consultant)
export const getUserRole = () => {
  return localStorage.getItem(STORAGE_KEYS.USER_ROLE);
};

// Get ESN ID
export const getEsnId = () => {
  const esnId = localStorage.getItem(STORAGE_KEYS.ESN_ID);
  return esnId ? parseInt(esnId, 10) : null;
};

export const getEsnName = () => {
  return localStorage.getItem(STORAGE_KEYS.ESN_NAME);
};

// Get user display name
export const getUserName = () => {
  return localStorage.getItem(STORAGE_KEYS.USER_NAME);
};

// Get user email
export const getUserEmail = () => {
  return localStorage.getItem(STORAGE_KEYS.USER_EMAIL);
};

// Check if user is logged in
export const isLoggedIn = () => {
  const token = getAuthToken();
  return !!token;
};

// Check if user is ESN
export const isESN = () => {
  return getUserRole() === 'esn';
};

// Check if user is Consultant
export const isConsultant = () => {
  return getUserRole() === 'consultant';
};

// Get auth headers for API requests
export const getAuthHeaders = () => {
  const token = getAuthToken();
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

// Get full user data
export const getCurrentUser = () => {
  return {
    token: getAuthToken(),
    userId: getUserId(),
    role: getUserRole(),
    esnId: getEsnId(),
    userName: getUserName(),
    userEmail: getUserEmail(),
  };
};

export default {
  saveAuthData,
  clearAuthData,
  getAuthToken,
  getUserId,
  getUserRole,
  getEsnId,
  getEsnName,
  getUserName,
  getUserEmail,
  isLoggedIn,
  isESN,
  isConsultant,
  getAuthHeaders,
  getCurrentUser,
  STORAGE_KEYS,
};
