import api from './api';
import { CONSULTANT_ENDPOINTS } from '../helper/endpoint';

// Get all consultants
export const getAllConsultants = async () => {
  try {
    const response = await api.get(CONSULTANT_ENDPOINTS.LIST);
    const data = response.data.data || response.data;
    return { success: true, data };
  } catch (error) {
    console.error('Get consultants error:', error);
    return { success: false, error: error.message };
  }
};

// Get consultants by ESN
export const getConsultantsByESN = async (esnId) => {
  try {
    const response = await api.get(CONSULTANT_ENDPOINTS.BY_ESN(esnId));
    // Extract data from nested response: { status: true, data: [...] }
    const data = response.data.data || response.data;
    return { success: true, data };
  } catch (error) {
    console.error('Get consultants by ESN error:', error);
    return { success: false, error: error.message };
  }
};

// Get consultant by ID
export const getConsultantById = async (id) => {
  try {
    const response = await api.get(CONSULTANT_ENDPOINTS.DETAIL(id));
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Get consultant error:', error);
    return { success: false, error: error.message };
  }
};

// Get consultant profile
export const getConsultantProfile = async (id) => {
  try {
    const response = await api.get(CONSULTANT_ENDPOINTS.PROFILE(id));
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Get consultant profile error:', error);
    return { success: false, error: error.message };
  }
};

// Get consultant projects
export const getConsultantProjects = async (id) => {
  try {
    const response = await api.get(CONSULTANT_ENDPOINTS.PROJECTS(id));
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Get consultant projects error:', error);
    return { success: false, error: error.message };
  }
};

// Create new consultant
export const createConsultant = async (consultantData) => {
  try {
    const response = await api.post(CONSULTANT_ENDPOINTS.LIST, consultantData);
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Create consultant error:', error);
    return { 
      success: false, 
      error: error.response?.data?.error || error.message 
    };
  }
};

// Update consultant
export const updateConsultant = async (id, consultantData) => {
  try {
    // Django API expects PUT to /collaborateur/ with ID_collab in the body
    const response = await api.put(CONSULTANT_ENDPOINTS.LIST, {
      ...consultantData,
      ID_collab: id,
    });
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Update consultant error:', error);
    return { 
      success: false, 
      error: error.response?.data?.error || error.response?.data?.msg || error.message 
    };
  }
};

// Delete consultant
export const deleteConsultant = async (id) => {
  try {
    await api.delete(CONSULTANT_ENDPOINTS.DETAIL(id));
    return { success: true };
  } catch (error) {
    console.error('Delete consultant error:', error);
    return { success: false, error: error.message };
  }
};

export default {
  getAllConsultants,
  getConsultantsByESN,
  getConsultantById,
  getConsultantProfile,
  getConsultantProjects,
  createConsultant,
  updateConsultant,
  deleteConsultant,
};
