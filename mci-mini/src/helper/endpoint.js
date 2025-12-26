// API Base URL Configuration
export const API_BASE_URL = 'http://localhost:8000/api';

// Authentication Endpoints
export const AUTH_ENDPOINTS = {
  LOGIN_ESN: `${API_BASE_URL}/login_esn/`,
  LOGIN_CONSULTANT: `${API_BASE_URL}/login_consultant/`,
  LOGOUT: `${API_BASE_URL}/logout/`,
};

// ESN Endpoints
export const ESN_ENDPOINTS = {
  LIST: `${API_BASE_URL}/ESN/`,
  DETAIL: (id) => `${API_BASE_URL}/ESN/${id}`,
};

// Collaborateur/Consultant Endpoints
export const CONSULTANT_ENDPOINTS = {
  LIST: `${API_BASE_URL}/collaborateur/`,
  DETAIL: (id) => `${API_BASE_URL}/collaborateur/${id}`,
  PROFILE: (id) => `${API_BASE_URL}/consultants/${id}/profile/`,
  DASHBOARD: (id) => `${API_BASE_URL}/consultants/${id}/dashboard/`,
  PROJECTS: (id) => `${API_BASE_URL}/consultant/${id}/projects/`,
  BY_ESN: (esnId) => `${API_BASE_URL}/consultants_par_esn/?esn_id=${esnId}`,
};

// Project Endpoints (BDC - Bon de Commande)
export const PROJECT_ENDPOINTS = {
  CREATE_BY_ESN: `${API_BASE_URL}/esn/create-project/`,
  LIST: `${API_BASE_URL}/Bondecommande/`,
  DETAIL: (id) => `${API_BASE_URL}/Bondecommande/${id}`,
  UPDATE_CONSULTANTS: (bdcId) => `${API_BASE_URL}/esn/project/${bdcId}/consultants/`,
  MANAGE_CONSULTANTS: (bdcId) => `${API_BASE_URL}/esn/project/${bdcId}/consultants/manage/`,
};

// CRA Imputation Endpoints (Daily entries)
export const CRA_IMPUTATION_ENDPOINTS = {
  LIST: `${API_BASE_URL}/cra_imputation`,
  DETAIL: (id) => `${API_BASE_URL}/cra_imputation/${id}/`,
  BY_CONSULTANT: (consultantId, period) => 
    `${API_BASE_URL}/cra-by-period/?consultant_id=${consultantId}&period=${period}`,
  BY_ESN: (esnId, period) => 
    `${API_BASE_URL}/cra-by-esn-period/?esn_id=${esnId}&period=${period}`,
};

// CRA Consultant Endpoints (Monthly summaries)
export const CRA_CONSULTANT_ENDPOINTS = {
  LIST: `${API_BASE_URL}/cra_consultant/`,
  DETAIL: (id) => `${API_BASE_URL}/cra_consultant/${id}/`,
  BY_CONSULTANT: (consultantId, period) => 
    `${API_BASE_URL}/cra-by-period/?consultant_id=${consultantId}&period=${period}`,
  BY_ESN: (esnId, period) => 
    `${API_BASE_URL}/cra-by-esn-period/?esn_id=${esnId}&period=${period}`,
  RECORDS: `${API_BASE_URL}/cra-consultant-records/`,
};

// Bon de Commande (Contract/Project) Endpoints
export const BDC_ENDPOINTS = {
  LIST: `${API_BASE_URL}/Bondecommande/`,
  DETAIL: (id) => `${API_BASE_URL}/Bondecommande/${id}`,
  BY_CONSULTANT: (consultantId, period) => 
    `${API_BASE_URL}/projects-by-consultant-period/?consultant_id=${consultantId}&period=${period}&include_bdcs=true`,
  BY_CONSULTANT_ALL: (consultantId) => 
    `${API_BASE_URL}/consultant/${consultantId}/projects/`,
  BY_ESN: (esnId) => 
    `${API_BASE_URL}/get_bon_de_commande_by_esn/${esnId}/`,
};

// Candidature Endpoints
export const CANDIDATURE_ENDPOINTS = {
  LIST: `${API_BASE_URL}/candidature/`,
  DETAIL: (id) => `${API_BASE_URL}/candidature/${id}/`,
};

// Appel d'Offre (Project/Tender) Endpoints  
export const APPEL_OFFRE_ENDPOINTS = {
  LIST: `${API_BASE_URL}/appelOffre/`,
  DETAIL: (id) => `${API_BASE_URL}/appelOffre/${id}/`,
};

// Client Endpoints
export const CLIENT_ENDPOINTS = {
  LIST: `${API_BASE_URL}/client/`,
  DETAIL: (id) => `${API_BASE_URL}/client/${id}/`,
};

export default {
  API_BASE_URL,
  AUTH_ENDPOINTS,
  ESN_ENDPOINTS,
  CONSULTANT_ENDPOINTS,
  CRA_IMPUTATION_ENDPOINTS,
  CRA_CONSULTANT_ENDPOINTS,
  BDC_ENDPOINTS,
  CANDIDATURE_ENDPOINTS,
  APPEL_OFFRE_ENDPOINTS,
  CLIENT_ENDPOINTS,
};
