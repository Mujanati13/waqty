import api from './api';
import { CRA_IMPUTATION_ENDPOINTS, CRA_CONSULTANT_ENDPOINTS, BDC_ENDPOINTS } from '../helper/endpoint';

// ============ CRA IMPUTATION (Daily Entries) ============

// Get all imputations
export const getAllImputations = async () => {
  try {
    const response = await api.get(CRA_IMPUTATION_ENDPOINTS.LIST);
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Get imputations error:', error);
    return { success: false, error: error.message };
  }
};

// Get imputations by consultant and period
export const getImputationsByConsultant = async (consultantId, period) => {
  try {
    const response = await api.get(CRA_IMPUTATION_ENDPOINTS.BY_CONSULTANT(consultantId, period));
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Get imputations by consultant error:', error);
    return { success: false, error: error.message };
  }
};

// Get imputations by ESN and period
export const getImputationsByESN = async (esnId, period) => {
  try {
    const response = await api.get(CRA_IMPUTATION_ENDPOINTS.BY_ESN(esnId, period));
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Get imputations by ESN error:', error);
    return { success: false, error: error.message };
  }
};

// Create new imputation (daily entry)
export const createImputation = async (imputationData) => {
  try {
    const response = await api.post(CRA_IMPUTATION_ENDPOINTS.LIST, imputationData);
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Create imputation error:', error);
    return { 
      success: false, 
      error: error.response?.data?.error || error.message 
    };
  }
};

// Update imputation
export const updateImputation = async (id, imputationData) => {
  try {
    const response = await api.put(CRA_IMPUTATION_ENDPOINTS.DETAIL(id), imputationData);
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Update imputation error:', error);
    return { 
      success: false, 
      error: error.response?.data?.error || error.message 
    };
  }
};

// Delete imputation
export const deleteImputation = async (id) => {
  try {
    await api.delete(CRA_IMPUTATION_ENDPOINTS.DETAIL(id));
    return { success: true };
  } catch (error) {
    console.error('Delete imputation error:', error);
    return { success: false, error: error.message };
  }
};

// ============ CRA CONSULTANT (Monthly Summary) ============

// Get all CRA consultant records
export const getAllCRAConsultants = async () => {
  try {
    const response = await api.get(CRA_CONSULTANT_ENDPOINTS.LIST);
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Get CRA consultants error:', error);
    return { success: false, error: error.message };
  }
};

// Get CRA by consultant and period
export const getCRAByConsultant = async (consultantId, period) => {
  try {
    const response = await api.get(CRA_CONSULTANT_ENDPOINTS.BY_CONSULTANT(consultantId, period));
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Get CRA by consultant error:', error);
    return { success: false, error: error.message };
  }
};

// Get CRAs by ESN and period
export const getCRAsByESN = async (esnId, period) => {
  try {
    const response = await api.get(CRA_CONSULTANT_ENDPOINTS.BY_ESN(esnId, period));
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Get CRAs by ESN error:', error);
    return { success: false, error: error.message };
  }
};

// Update CRA status (for validation workflow)
// Uses CRA_IMPUTATION endpoint since we're updating individual daily entries
export const updateCRAStatus = async (id, status, commentaire = '') => {
  try {
    const response = await api.put(CRA_IMPUTATION_ENDPOINTS.DETAIL(id), {
      statut: status,
      commentaire,
    });
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Update CRA status error:', error);
    return { 
      success: false, 
      error: error.response?.data?.error || error.message 
    };
  }
};

// Get CRA detail
export const getCRADetail = async (id) => {
  try {
    const response = await api.get(CRA_CONSULTANT_ENDPOINTS.DETAIL(id));
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Get CRA detail error:', error);
    return { success: false, error: error.message };
  }
};

// ============ BON DE COMMANDE (Projects/Contracts) ============

// Get all BDCs
export const getAllBDCs = async () => {
  try {
    const response = await api.get(BDC_ENDPOINTS.LIST);
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Get BDCs error:', error);
    return { success: false, error: error.message };
  }
};

// Get BDCs by consultant
export const getBDCsByConsultant = async (consultantId, period) => {
  try {
    const response = await api.get(BDC_ENDPOINTS.BY_CONSULTANT(consultantId, period));
    // Extract data from nested response structure
    const projectsData = response.data.data || response.data || [];
    
    console.log('getBDCsByConsultant response:', projectsData);
    
    // Transform projects to BDC format
    const bdcs = [];
    if (Array.isArray(projectsData)) {
      projectsData.forEach(project => {
        const candidatures = project.candidatures || [];
        const bdcList = project.bdcs || [];
        
        // Get ESN info from candidatures
        let esnId = project.client_id;
        let esnName = project.client_name;
        
        // Find the candidature for the current consultant to extract allocated days
        const consultantCandidature = candidatures.find(c => String(c.id_consultant) === String(consultantId)) || candidatures[0];
        
        if (candidatures.length > 0) {
          const candidature = candidatures[0];
          esnId = candidature.esn_id || esnId;
          esnName = `ESN ${esnId}`;
        }
        
        // Extract consultant-specific allocated days from candidature.commentaire
        // Format: "jours:XX" stored in commentaire field
        let consultantAllocatedDays = null;
        if (consultantCandidature?.commentaire) {
          const joursMatch = consultantCandidature.commentaire.match(/jours:(\d+)/);
          if (joursMatch) {
            consultantAllocatedDays = parseInt(joursMatch[1], 10);
            console.log(`Found consultant-specific jours in commentaire: ${consultantAllocatedDays} for project ${project.titre}`);
          }
        }
        
        // If project has BDCs, process them
        if (bdcList.length > 0) {
          bdcList.forEach(bdc => {
            // Use consultant-specific days if available, otherwise fall back to BDC jours
            const jours = consultantAllocatedDays || bdc.jours;
            console.log(`BDC ${bdc.id_bdc} - Consultant allocated: ${consultantAllocatedDays}, BDC jours: ${bdc.jours}, Final jours: ${jours}`);
            
            bdcs.push({
              ...bdc,
              jours: jours, // Override with consultant-specific days
              jours_consultant: consultantAllocatedDays,
              jours_total: bdc.jours,
              has_real_bdc: true,
              project_title: project.titre,
              client_name: project.client_name,
              client_id: project.client_id,
              esn_id: esnId,
              esn_name: esnName,
              // Include project status for filtering (bdc.statut should already be there from spread)
              status: bdc.statut || project.statut
            });
          });
        } else {
          // If no BDCs, create a pseudo-BDC from project data
          const candidature = candidatures[0] || {};
          const date_debut = candidature.date_disponibilite || project.date_debut;
          let date_fin = null;
          
          // Use consultant-specific days if available
          const jours = consultantAllocatedDays || project.jours;
          
          // Calculate date_fin from date_debut + jours if available
          if (date_debut && jours) {
            const startDate = new Date(date_debut);
            startDate.setDate(startDate.getDate() + parseInt(jours));
            date_fin = startDate.toISOString().split('T')[0];
          }
          
          bdcs.push({
            id_bdc: project.id,
            has_real_bdc: false,
            project_title: project.titre,
            client_name: project.client_name,
            client_id: project.client_id,
            esn_id: esnId,
            esn_name: esnName,
            TJM: candidature.tjm,
            date_debut: date_debut,
            date_fin: date_fin,
            jours: jours, // Use consultant-specific days
            jours_consultant: consultantAllocatedDays,
            jours_total: project.jours,
            numero_bdc: `AO-${project.id}`,
            statut: project.statut,  // Use project status (set by ESN), not candidature status
            status: project.statut   // Also add as 'status' for compatibility
          });
        }
      });
    }
    
    console.log('Transformed BDCs:', bdcs);
    return { success: true, data: bdcs };
  } catch (error) {
    console.error('Get BDCs by consultant error:', error);
    return { success: false, error: error.message, data: [] };
  }
};

// Get all projects for a consultant (without period filter)
export const getAllProjectsByConsultant = async (consultantId) => {
  try {
    const response = await api.get(BDC_ENDPOINTS.BY_CONSULTANT_ALL(consultantId));
    const projectsData = response.data.data || response.data || [];
    
    console.log('Raw projects data from API:', projectsData);
    
    // Transform projects into a format similar to BDCs
    const projects = [];
    if (Array.isArray(projectsData)) {
      projectsData.forEach(project => {
        const bdc = project.bdc;
        const candidature = project.candidature;
        
        console.log('Processing project:', project.titre, 'BDC:', bdc, 'BDC statut:', bdc?.statut, 'Candidature:', candidature);
        
        // Track if this is a real BDC or just a project reference
        const hasRealBdc = !!bdc?.id_bdc;
        
        // Get date_fin: try BDC first, then calculate from project data
        let date_fin = bdc?.date_fin || null;
        let date_debut = bdc?.date_debut || candidature?.date_disponibilite || project.date_debut;
        
        // Extract consultant-specific allocated days from candidature.commentaire
        // Format: "jours:XX" stored in commentaire field
        let consultantAllocatedDays = null;
        if (candidature?.commentaire) {
          const joursMatch = candidature.commentaire.match(/jours:(\d+)/);
          if (joursMatch) {
            consultantAllocatedDays = parseInt(joursMatch[1], 10);
            console.log(`Found consultant-specific jours in commentaire: ${consultantAllocatedDays}`);
          }
        }
        
        // Use consultant-specific days if available, otherwise fall back to BDC/project jours
        let jours = consultantAllocatedDays || bdc?.jours || project.jours;
        console.log(`Project ${project.titre} - Consultant allocated: ${consultantAllocatedDays}, BDC jours: ${bdc?.jours}, Final jours: ${jours}`);
        
        // If no date_fin but we have date_debut and jours, calculate it
        if (!date_fin && date_debut && jours) {
          const startDate = new Date(date_debut);
          startDate.setDate(startDate.getDate() + parseInt(jours));
          date_fin = startDate.toISOString().split('T')[0];
        }
        
        // Get status: try bdc.statut first (where ESN stores it), then other fields
        const projectStatus = bdc?.statut || bdc?.status || project.status || project.statut || candidature?.statut || 'En cours';
        console.log('Project status resolved to:', projectStatus, 'from bdc.statut:', bdc?.statut);
        
        projects.push({
          id_bdc: bdc?.id_bdc || project.id,
          has_real_bdc: hasRealBdc,
          project_title: project.titre,
          client_name: project.client_name,
          client_id: project.client_id,
          esn_id: candidature?.esn_id,
          esn_name: project.esn_name || 'N/A',
          tjm: bdc?.TJM || candidature?.tjm,
          date_debut: date_debut,
          date_fin: date_fin,
          status: projectStatus,  // Add status field
          statut: projectStatus,  // Add statut field (for compatibility)
          statut_bdc: candidature?.statut || 'N/A',
          numero_bdc: bdc?.numero_bdc || `AO-${project.id}`,
          jours: jours,
          jours_consultant: consultantAllocatedDays, // Store consultant-specific allocation separately
          jours_total: bdc?.jours || project.jours // Store total project days for reference
        });
      });
    }
    return { success: true, data: projects };
  } catch (error) {
    console.error('Get all projects by consultant error:', error);
    return { success: false, error: error.message, data: [] };
  }
};

// Get BDCs by ESN
export const getBDCsByESN = async (esnId) => {
  try {
    const response = await api.get(BDC_ENDPOINTS.BY_ESN(esnId));
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Get BDCs by ESN error:', error);
    return { success: false, error: error.message };
  }
};

// Get BDC detail
export const getBDCDetail = async (id) => {
  try {
    const response = await api.get(BDC_ENDPOINTS.DETAIL(id));
    return { success: true, data: response.data };
  } catch (error) {
    console.error('Get BDC detail error:', error);
    return { success: false, error: error.message };
  }
};

// CRA Status Constants
export const CRA_STATUS = {
  DRAFT: 'Brouillon',
  SUBMITTED: 'EVP', // En Validation Prestataire (submitted by consultant)
  ESN_VALIDATED: 'EVC', // En Validation Client (validated by ESN)
  VALIDATED: 'Validé',
  REJECTED: 'Refusé',
  CANCELLED: 'Annulé', // Cancelled by ESN with remark, consultant can resubmit
};

export default {
  // Imputations
  getAllImputations,
  getImputationsByConsultant,
  getImputationsByESN,
  createImputation,
  updateImputation,
  deleteImputation,
  // CRA Consultant
  getAllCRAConsultants,
  getCRAByConsultant,
  getCRAsByESN,
  updateCRAStatus,
  getCRADetail,
  // BDC
  getAllBDCs,
  getBDCsByConsultant,
  getAllProjectsByConsultant,
  getBDCsByESN,
  getBDCDetail,
  // Constants
  CRA_STATUS,
};
