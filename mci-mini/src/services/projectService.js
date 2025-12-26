import api from './api';
import { PROJECT_ENDPOINTS } from '../helper/endpoint';

/**
 * Create a new project for a consultant
 * @param {Object} projectData - Project details
 * @param {number} projectData.esn_id - ESN ID
 * @param {number} projectData.consultant_id - Consultant ID
 * @param {string} projectData.project_title - Project title
 * @param {number} projectData.tjm - Daily rate (TJM)
 * @param {string} projectData.date_debut - Start date (YYYY-MM-DD)
 * @param {string} projectData.date_fin - End date (YYYY-MM-DD)
 * @param {string} projectData.description - Project description (optional)
 * @param {number} projectData.montant_total - Total amount (optional)
 * @param {number} projectData.jours - Number of days (optional)
 */
export const createProject = async (projectData) => {
  try {
    const response = await api.post(PROJECT_ENDPOINTS.CREATE_BY_ESN, projectData);
    return response.data;
  } catch (error) {
    console.error('Error creating project:', error);
    throw error;
  }
};

/**
 * Get all projects
 */
export const getProjects = async () => {
  try {
    const response = await api.get(PROJECT_ENDPOINTS.LIST);
    // Backend returns {total: X, data: [...]}
    return {
      success: true,
      data: response.data.data || [],
      total: response.data.total || 0
    };
  } catch (error) {
    console.error('Error fetching projects:', error);
    return {
      success: false,
      error: error.response?.data?.message || error.message,
      data: []
    };
  }
};

/**
 * Get project by ID
 */
export const getProjectById = async (id) => {
  try {
    const response = await api.get(PROJECT_ENDPOINTS.DETAIL(id));
    return response.data;
  } catch (error) {
    console.error('Error fetching project:', error);
    throw error;
  }
};

/**
 * Get detailed project information with consultant data
 * @param {number} bdcId - BDC ID
 */
export const getProjectDetails = async (bdcId) => {
  try {
    const response = await api.get(PROJECT_ENDPOINTS.UPDATE_CONSULTANTS(bdcId));
    return {
      success: response.data.status || false,
      data: response.data.data
    };
  } catch (error) {
    console.error('Error fetching project details:', error);
    return {
      success: false,
      error: error.response?.data?.message || error.message
    };
  }
};

/**
 * Update consultants linked to a project
 * @param {number} bdcId - BDC ID
 * @param {Object} data - Update data
 * @param {number} data.esn_id - ESN ID
 * @param {number[]} data.consultant_ids - Array of consultant IDs to link to the project
 */
export const updateProjectConsultants = async (bdcId, data) => {
  try {
    const response = await api.put(PROJECT_ENDPOINTS.UPDATE_CONSULTANTS(bdcId), data);
    return {
      success: response.data.status || false,
      message: response.data.message,
      data: response.data.data
    };
  } catch (error) {
    console.error('Error updating project consultants:', error);
    return {
      success: false,
      error: error.response?.data?.message || error.message
    };
  }
};

/**
 * Get all consultants assigned to a project
 * @param {number} bdcId - BDC ID
 */
export const getProjectConsultants = async (bdcId) => {
  try {
    const response = await api.get(PROJECT_ENDPOINTS.MANAGE_CONSULTANTS(bdcId));
    return {
      success: response.data.status || false,
      data: response.data.data || [],
      total: response.data.total || 0
    };
  } catch (error) {
    console.error('Error fetching project consultants:', error);
    return {
      success: false,
      error: error.response?.data?.message || error.message,
      data: []
    };
  }
};

/**
 * Add a consultant to a project
 * @param {number} bdcId - BDC ID
 * @param {number} esnId - ESN ID
 * @param {number} consultantId - Consultant ID to add
 */
export const addConsultantToProject = async (bdcId, esnId, consultantId) => {
  try {
    const response = await api.post(PROJECT_ENDPOINTS.MANAGE_CONSULTANTS(bdcId), {
      esn_id: esnId,
      consultant_id: consultantId
    });
    return {
      success: response.data.status || false,
      message: response.data.message,
      data: response.data.data
    };
  } catch (error) {
    console.error('Error adding consultant to project:', error);
    return {
      success: false,
      error: error.response?.data?.message || error.message
    };
  }
};

/**
 * Remove a consultant from a project
 * @param {number} bdcId - BDC ID
 * @param {number} esnId - ESN ID
 * @param {number} consultantId - Consultant ID to remove
 */
export const removeConsultantFromProject = async (bdcId, esnId, consultantId) => {
  try {
    const response = await api.delete(PROJECT_ENDPOINTS.MANAGE_CONSULTANTS(bdcId), {
      data: {
        esn_id: esnId,
        consultant_id: consultantId
      }
    });
    return {
      success: response.data.status || false,
      message: response.data.message
    };
  } catch (error) {
    console.error('Error removing consultant from project:', error);
    return {
      success: false,
      error: error.response?.data?.message || error.message
    };
  }
};

export default {
  createProject,
  getProjects,
  getProjectById,
  getProjectDetails,
  updateProjectConsultants,
  getProjectConsultants,
  addConsultantToProject,
  removeConsultantFromProject,
};
