import React, { useState, useEffect, useRef } from 'react';
import {
  Card, Typography, Table, Row, Col, Button, Tag, Spin, Modal,
  Form, Select, message, Empty, Input, Drawer, List, Space, Tabs, Switch, Alert, Tooltip, Checkbox
} from 'antd';
import {
  LeftOutlined, RightOutlined, ReloadOutlined, LogoutOutlined,
  CalendarOutlined, ProjectOutlined, PlusOutlined, EditOutlined, DeleteOutlined, CheckOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import 'dayjs/locale/fr';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import { getUserId, getUserName } from '../helper/auth';
import {
  getImputationsByConsultant, createImputation, updateImputation, deleteImputation,
  getBDCsByConsultant, getAllProjectsByConsultant, updateCRAStatus, getCRAByConsultant
} from '../services/craService';
import { logout } from '../services/authService';

dayjs.extend(isSameOrBefore);
dayjs.extend(isSameOrAfter);
dayjs.locale('fr');

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const ConsultantCRA = () => {
  // Helper function to normalize IDs for comparison (handles string vs number)
  const normalizeId = (value) =>
    value === null || value === undefined ? null : String(value);

  // State variables
  const [loading, setLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState(dayjs());
  const [craData, setCraData] = useState(null);
  const [projects, setProjects] = useState([]);
  const [allProjects, setAllProjects] = useState([]);
  const [projectsById, setProjectsById] = useState({});
  const [clientsById, setClientsById] = useState({});
  const [imputations, setImputations] = useState([]);

  // Holiday states
  const [holidays, setHolidays] = useState([]);
  const [selectedCountry, setSelectedCountry] = useState('FR');
  const [showHolidays, setShowHolidays] = useState(true);

  // Modal states
  const [craEntryModalVisible, setCraEntryModalVisible] = useState(false);
  const [editDrawerVisible, setEditDrawerVisible] = useState(false);
  const [selectedDay, setSelectedDay] = useState(null);
  const [dayEntries, setDayEntries] = useState([]);
  const [selectedCraEntry, setSelectedCraEntry] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [remainingDuration, setRemainingDuration] = useState(1);
  const [preFilledFields, setPreFilledFields] = useState({ day: false, client: false, project: false, type: false });

  // Submission modal states
  const [submissionModalVisible, setSubmissionModalVisible] = useState(false);
  const [selectedContractId, setSelectedContractId] = useState(null);
  const [craEntriesToSubmit, setCraEntriesToSubmit] = useState([]);

  const [craForm] = Form.useForm();
  const [editForm] = Form.useForm();

  const consultantId = getUserId();
  const userName = getUserName();
  
  // Ref to preserve scroll position
  const tableScrollRef = useRef(null);

  useEffect(() => {
    fetchMonthlyReport(selectedMonth);
    fetchHolidays(selectedMonth);
  }, [selectedMonth]);

  // Fetch holidays from Nager.Date API
  const fetchHolidays = async (date) => {
    try {
      const year = date.year();
      const response = await fetch(`https://date.nager.at/api/v3/PublicHolidays/${year}/${selectedCountry}`);
      if (response.ok) {
        const data = await response.json();
        setHolidays(data);
      }
    } catch (error) {
      console.error('Error fetching holidays:', error);
    }
  };

  const isHoliday = (date) => {
    if (!showHolidays) return null;
    const dateStr = date.format('YYYY-MM-DD');
    return holidays.find(h => h.date === dateStr);
  };

  // Convert decimal days to hours display (1 day = 8h)
  const formatDuration = (days) => {
    const hours = days * 8;
    if (hours === 8) return '1j'; // 1 day
    return `${hours}h`;
  };

  // Calculate total consumed days for a project (for the current month)
  const getProjectConsumedDays = (projectId) => {
    const normalizedProjectId = normalizeId(projectId);
    const projectImputations = imputations.filter(imp =>
      normalizeId(imp.id_bdc) === normalizedProjectId
    );
    return projectImputations.reduce((sum, imp) => sum + parseFloat(imp.Durée || 0), 0);
  };

  // Get allocated days for a project
  const getProjectAllocatedDays = (projectId) => {
    const normalizedProjectId = normalizeId(projectId);
    const project = projectsById[normalizedProjectId];
    return project?.jours || null; // null means unlimited
  };

  // Check if project has reached its allocated days limit
  const isProjectLimitReached = (projectId) => {
    const allocatedDays = getProjectAllocatedDays(projectId);
    if (allocatedDays === null || allocatedDays === undefined) return false;
    const consumedDays = getProjectConsumedDays(projectId);
    return consumedDays >= allocatedDays;
  };

  // Get remaining days available for a project
  const getProjectRemainingDays = (projectId) => {
    const allocatedDays = getProjectAllocatedDays(projectId);
    if (allocatedDays === null || allocatedDays === undefined) return null;
    const consumedDays = getProjectConsumedDays(projectId);
    return Math.max(0, allocatedDays - consumedDays);
  };

  // Check if a day is within the project's contract date range
  const isDayInProjectRange = (day, project) => {
    if (!project) return false;

    const currentDate = selectedMonth.date(day);

    // Get project dates
    const dateDebut = project.date_debut ? dayjs(project.date_debut) : null;
    const dateFin = project.date_fin ? dayjs(project.date_fin) : null;

    // If no dates defined, assume available
    if (!dateDebut && !dateFin) return true;

    // Check if current date is within range
    if (dateDebut && currentDate.isBefore(dateDebut, 'day')) return false;
    if (dateFin && currentDate.isAfter(dateFin, 'day')) return false;

    return true;
  };

  // Check if any project is available for a given day
  const isAnyProjectAvailable = (day) => {
    return Object.values(projectsById).some(project => isDayInProjectRange(day, project));
  };

  const fetchAllProjects = async () => {
    try {
      const result = await getAllProjectsByConsultant(consultantId);
      console.log('All projects result:', result);
      if (result.success) {
        const projectsData = result.data || [];
        console.log('Projects data:', projectsData);
        if (projectsData.length > 0) {
          console.log('Sample project fields:', Object.keys(projectsData[0]));
          console.log('Sample project status field:', projectsData[0].status);
          console.log('Sample project statut field:', projectsData[0].statut);
        }
        setAllProjects(projectsData);
      } else {
        console.error('Failed to fetch projects:', result.error);
        setAllProjects([]);
      }
    } catch (error) {
      console.error('Error fetching all projects:', error);
      setAllProjects([]);
    }
  };

  const fetchMonthlyReport = async (date, preserveScroll = false) => {
    // Save scroll position before loading
    let scrollPosition = { x: 0, y: 0 };
    if (preserveScroll && tableScrollRef.current) {
      const scrollContainer = tableScrollRef.current.querySelector('.ant-table-body');
      if (scrollContainer) {
        scrollPosition = {
          x: scrollContainer.scrollLeft,
          y: scrollContainer.scrollTop
        };
      }
    }
    
    // Only show loading spinner if not preserving scroll (to avoid table unmount)
    if (!preserveScroll) {
      setLoading(true);
    }
    try {
      const period = date.format('MM_YYYY');

      // First refresh allProjects to get latest status
      const allProjectsResult = await getAllProjectsByConsultant(consultantId);
      let latestProjects = [];
      if (allProjectsResult.success) {
        latestProjects = allProjectsResult.data || [];
        setAllProjects(latestProjects);
        console.log('Refreshed allProjects:', latestProjects);
      }

      // Fetch BDCs for this period
      const bdcsResult = await getBDCsByConsultant(consultantId, period);
      console.log('BDCs result:', bdcsResult);

      if (bdcsResult.success && bdcsResult.data) {
        const bdcsList = Array.isArray(bdcsResult.data) ? bdcsResult.data : [bdcsResult.data];
        
        // Filter out inactive projects (En pause, Terminé, Annulé) from CRA view
        const inactiveStatuses = ['Terminé', 'En pause', 'Annulé'];
        
        // Get the first and last day of the selected month for period filtering
        const monthStart = date.startOf('month');
        const monthEnd = date.endOf('month');
        
        const activeBdcsList = bdcsList.filter(bdc => {
          // First check in the bdc itself
          let status = bdc.status || bdc.statut;
          
          // If no status in bdc, look it up in latestProjects (freshly fetched)
          if (!status) {
            const matchingProject = latestProjects.find(p => 
              String(p.id_bdc) === String(bdc.id_bdc)
            );
            status = matchingProject?.status || matchingProject?.statut;
          }
          
          // Default to 'En cours' only if still no status
          if (!status) {
            status = 'En cours';
          }
          
          // Check if project status is active
          const isActiveStatus = !inactiveStatuses.includes(status);
          
          // Check if project period overlaps with selected month
          const projectStart = bdc.date_debut ? dayjs(bdc.date_debut) : null;
          const projectEnd = bdc.date_fin ? dayjs(bdc.date_fin) : null;
          
          let isInPeriod = true;
          if (projectStart && projectStart.isAfter(monthEnd, 'day')) {
            // Project starts after this month ends
            isInPeriod = false;
          }
          if (projectEnd && projectEnd.isBefore(monthStart, 'day')) {
            // Project ended before this month starts
            isInPeriod = false;
          }
          
          console.log(`Project ${bdc.project_title} (id: ${bdc.id_bdc}) - Status: "${status}" - Active: ${isActiveStatus} - InPeriod: ${isInPeriod} (${projectStart?.format('YYYY-MM-DD')} to ${projectEnd?.format('YYYY-MM-DD')})`);
          return isActiveStatus && isInPeriod;
        });
        
        console.log(`Filtered projects: ${activeBdcsList.length} active out of ${bdcsList.length} total`);
        setProjects(activeBdcsList);

        // Build lookup objects - normalize IDs to strings for consistent matching
        const projectsMap = {};
        const clientsMap = {};

        activeBdcsList.forEach(bdc => {
          // Normalize id_bdc to string for consistent key lookup
          const normalizedBdcId = normalizeId(bdc.id_bdc);
          projectsMap[normalizedBdcId] = { ...bdc, id_bdc: normalizedBdcId };

          // Use esn_id, client_id, or fallback to 'default' group
          const groupId = normalizeId(bdc.esn_id || bdc.client_id || 'default');
          let groupName = bdc.esn_name || bdc.client_name;

          if (!groupName || groupName === 'Unknown Client') {
            groupName = 'ESN';
          }

          if (!clientsMap[groupId]) {
            clientsMap[groupId] = {
              id: groupId,
              name: groupName,
              projects: []
            };
          }
          clientsMap[groupId].projects.push(normalizedBdcId);
        });

        console.log('Projects map (normalized):', projectsMap);
        console.log('Clients map (normalized):', clientsMap);

        setProjectsById(projectsMap);
        setClientsById(clientsMap);
      } else {
        console.log('No BDCs returned or error:', bdcsResult);
        setProjectsById({});
        setClientsById({});
      }

      // Fetch imputations for this period
      const imputationsResult = await getImputationsByConsultant(consultantId, period);
      console.log('Imputations result:', imputationsResult);

      if (imputationsResult.success) {
        // API returns { status, data, grouped_data } - extract the data array
        const apiResponse = imputationsResult.data;
        const imputationsList = Array.isArray(apiResponse?.data)
          ? apiResponse.data
          : (Array.isArray(apiResponse) ? apiResponse : []);
        console.log('Imputations list:', imputationsList);
        // Debug: log all statuts to check for cancelled entries
        console.log('📋 All imputation statuts:', imputationsList.map(imp => ({ 
          id: imp.id_imputation, 
          jour: imp.jour, 
          statut: imp.statut, 
          commentaire: imp.commentaire 
        })));
        const cancelledEntries = imputationsList.filter(imp => imp.statut === 'Annulé');
        console.log('🚫 Cancelled entries:', cancelledEntries);
        setImputations(imputationsList);
        processCraData(imputationsList, date);
      } else {
        processCraData([], date);
      }

    } catch (error) {
      console.error('Error fetching monthly report:', error);
      message.error('Erreur lors du chargement des données');
    } finally {
      setLoading(false);
      
      // Restore scroll position after data loads
      if (preserveScroll && tableScrollRef.current) {
        // Use requestAnimationFrame to ensure DOM has updated
        requestAnimationFrame(() => {
          const scrollContainer = tableScrollRef.current?.querySelector('.ant-table-body');
          if (scrollContainer) {
            scrollContainer.scrollLeft = scrollPosition.x;
            scrollContainer.scrollTop = scrollPosition.y;
          }
        });
      }
    }
  };

  const processCraData = (imputationsList, monthDate) => {
    const daysInMonth = monthDate.daysInMonth();
    const days = [];

    let totalDays = 0;
    let potentialWorkDays = 0;

    for (let day = 1; day <= daysInMonth; day++) {
      const date = monthDate.date(day);
      const dayOfWeek = date.day();
      const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
      const holiday = isHoliday(date);

      if (!isWeekend && !holiday) {
        potentialWorkDays++;
      }

      // Get entries for this day
      const dayEntries = imputationsList.filter(imp => {
        const impDay = parseInt(imp.jour);
        return impDay === day;
      });

      const dayTotal = dayEntries.reduce((sum, e) => sum + parseFloat(e.Durée || 0), 0);
      totalDays += dayTotal;

      days.push({
        day,
        date: date.format('YYYY-MM-DD'),
        dayOfWeek,
        isWeekend,
        isHoliday: !!holiday,
        holidayName: holiday?.localName || holiday?.name,
        entries: dayEntries,
        total: dayTotal
      });
    }

    // Build client work data
    const clientWork = [];
    Object.values(clientsById).forEach(client => {
      const clientData = {
        clientId: client.id,
        clientName: client.name,
        projects: client.projects.map(projectId => {
          const project = projectsById[projectId];
          const projectTotal = imputationsList
            .filter(imp => imp.id_bdc === projectId)
            .reduce((sum, e) => sum + parseFloat(e.Durée || 0), 0);

          return {
            projectId,
            projectTitle: project?.project_title || `Projet ${projectId}`,
            total: projectTotal,
            days: {}
          };
        }),
        total: 0
      };

      clientData.total = clientData.projects.reduce((sum, p) => sum + p.total, 0);
      if (clientData.total > 0 || clientData.projects.length > 0) {
        clientWork.push(clientData);
      }
    });

    setCraData({
      days,
      clientWork,
      totalDays,
      potentialWorkDays,
      month: monthDate.format('MMMM YYYY')
    });
  };

  const openAddCraModal = (day, clientId = null, projectId = null, isWorkEntry = false) => {
    setSelectedDay(day);

    // Calculate remaining duration for this day
    const dayData = craData?.days?.find(d => d.day === day);
    const existingTotal = dayData?.total || 0;
    const remaining = Math.max(0, 1 - existingTotal);
    setRemainingDuration(remaining);

    // Track which fields are pre-filled
    setPreFilledFields({
      day: day !== null,
      client: clientId !== null,
      project: projectId !== null,
      type: isWorkEntry // Hide type field for work entries from project row
    });

    craForm.resetFields();
    craForm.setFieldsValue({
      type_imputation: 'Jour Travaillé',
      jour: day,
      Durée: 1,
      id_client: clientId,
      id_bdc: projectId
    });

    setCraEntryModalVisible(true);
  };

  const openEditDrawer = (day) => {
    setSelectedDay(day);
    const dayData = craData?.days?.find(d => d.day === day);
    setDayEntries(dayData?.entries || []);
    setSelectedCraEntry(null);
    setEditDrawerVisible(true);
  };

  const submitCraEntry = async (values) => {
    setSubmitting(true);
    try {
      const period = selectedMonth.format('MM_YYYY');
      // Use form value or default to 'Jour Travaillé' if type field was hidden (pre-filled)
      const typeImputation = values.type_imputation || craForm.getFieldValue('type_imputation') || 'Jour Travaillé';
      const isWork = typeImputation === 'Jour Travaillé';

      // Check if adding this entry would exceed 1 day for this day
      const dayToCheck = values.jour || selectedDay;
      const dayData = craData?.days?.find(d => d.day === dayToCheck);
      const existingTotal = dayData?.total || 0;
      const newTotal = existingTotal + parseFloat(values.Durée);

      if (newTotal > 1) {
        message.error(`Le total pour ce jour (${newTotal.toFixed(2)} jours) dépasserait 1 jour (8h). Actuellement: ${existingTotal} jour(s).`);
        setSubmitting(false);
        return;
      }

      // Validate project period and allocated days limit for work entries
      if (isWork) {
        const bdcId = values.id_bdc || craForm.getFieldValue('id_bdc');
        if (bdcId) {
          const normalizedBdcId = normalizeId(bdcId);
          const project = projectsById[normalizedBdcId];
          console.log('Period validation - bdcId:', bdcId, 'normalized:', normalizedBdcId, 'project:', project);
          if (project) {
            const currentDate = selectedMonth.date(dayToCheck);
            const dateDebut = project.date_debut ? dayjs(project.date_debut) : null;
            const dateFin = project.date_fin ? dayjs(project.date_fin) : null;
            
            console.log('Period validation - currentDate:', currentDate.format('YYYY-MM-DD'), 
                        'dateDebut:', dateDebut?.format('YYYY-MM-DD'), 
                        'dateFin:', dateFin?.format('YYYY-MM-DD'));
            
            if (dateDebut && currentDate.isBefore(dateDebut, 'day')) {
              message.error(`La date sélectionnée (${currentDate.format('DD/MM/YYYY')}) est avant le début du projet (${dateDebut.format('DD/MM/YYYY')})`);
              setSubmitting(false);
              return;
            }
            if (dateFin && currentDate.isAfter(dateFin, 'day')) {
              message.error(`La date sélectionnée (${currentDate.format('DD/MM/YYYY')}) est après la fin du projet (${dateFin.format('DD/MM/YYYY')})`);
              setSubmitting(false);
              return;
            }

            // Check if adding this entry would exceed allocated days for the project
            const allocatedDays = project.jours;
            if (allocatedDays !== null && allocatedDays !== undefined) {
              const consumedDays = getProjectConsumedDays(bdcId);
              const newProjectTotal = consumedDays + parseFloat(values.Durée);
              
              if (newProjectTotal > allocatedDays) {
                message.error(`Cette entrée dépasserait le quota de jours alloués pour ce projet. Jours alloués: ${allocatedDays}, Déjà consommés: ${consumedDays}, Restants: ${Math.max(0, allocatedDays - consumedDays)}`);
                setSubmitting(false);
                return;
              }
            }
          }
        }
      }

      // Build base data
      const entryData = {
        id_consultan: consultantId,
        période: period,
        jour: dayToCheck,
        Durée: values.Durée,
        type_imputation: typeImputation,
        commentaire: values.commentaire || '',
        type: isWork ? 'travail' : 'absence',
        statut: 'À saisir',
        id_bdc: 0,
        id_client: 0
      };

      // Add client and BDC for work entries
      if (isWork && (values.id_client || craForm.getFieldValue('id_client')) && (values.id_bdc || craForm.getFieldValue('id_bdc'))) {
        const clientId = values.id_client || craForm.getFieldValue('id_client');
        const bdcId = values.id_bdc || craForm.getFieldValue('id_bdc');

        entryData.id_client = clientId;
        // Always send the project ID - backend now accepts both BDC IDs and AppelOffre IDs
        entryData.id_bdc = bdcId;
      }

      console.log('Submitting imputation:', entryData);

      const result = await createImputation(entryData);

      if (result.success) {
        message.success('Imputation ajoutée avec succès');
        setCraEntryModalVisible(false);
        fetchMonthlyReport(selectedMonth, true);
      } else {
        message.error(result.error || 'Erreur lors de la création');
      }
    } catch (error) {
      console.error('Error creating imputation:', error);
      message.error('Erreur lors de la création');
    } finally {
      setSubmitting(false);
    }
  };

  const editCraEntry = (entry) => {
    setSelectedCraEntry(entry);
    editForm.setFieldsValue({
      id_client: entry.id_client,
      id_bdc: entry.id_bdc,
      type_imputation: entry.type_imputation,
      Durée: parseFloat(entry.Durée),
      commentaire: entry.commentaire
    });
  };

  const updateCraEntry = async (values) => {
    if (!selectedCraEntry) return;

    setSubmitting(true);
    try {
      const isWork = values.type_imputation === 'Jour Travaillé';
      
      // Validate project period for work entries
      if (isWork && values.id_bdc) {
        const normalizedBdcId = normalizeId(values.id_bdc);
        const project = projectsById[normalizedBdcId];
        console.log('Update period validation - bdcId:', values.id_bdc, 'normalized:', normalizedBdcId, 'project:', project);
        if (project) {
          const currentDate = selectedMonth.date(selectedDay);
          const dateDebut = project.date_debut ? dayjs(project.date_debut) : null;
          const dateFin = project.date_fin ? dayjs(project.date_fin) : null;
          
          console.log('Update period validation - currentDate:', currentDate.format('YYYY-MM-DD'), 
                      'dateDebut:', dateDebut?.format('YYYY-MM-DD'), 
                      'dateFin:', dateFin?.format('YYYY-MM-DD'));
          
          if (dateDebut && currentDate.isBefore(dateDebut, 'day')) {
            message.error(`La date sélectionnée (${currentDate.format('DD/MM/YYYY')}) est avant le début du projet (${dateDebut.format('DD/MM/YYYY')})`);
            setSubmitting(false);
            return;
          }
          if (dateFin && currentDate.isAfter(dateFin, 'day')) {
            message.error(`La date sélectionnée (${currentDate.format('DD/MM/YYYY')}) est après la fin du projet (${dateFin.format('DD/MM/YYYY')})`);
            setSubmitting(false);
            return;
          }
        }
      }

      const updatedData = {
        ...selectedCraEntry,
        id_client: values.id_client,
        id_bdc: values.id_bdc,
        type_imputation: values.type_imputation,
        Durée: values.Durée,
        commentaire: values.commentaire || '',
        type: isWork ? 'travail' : 'absence'
      };

      const result = await updateImputation(selectedCraEntry.id_imputation, updatedData);

      if (result.success) {
        message.success('Imputation mise à jour');
        setSelectedCraEntry(null);
        setEditDrawerVisible(false);
        fetchMonthlyReport(selectedMonth, true);
      } else {
        message.error(result.error || 'Erreur lors de la mise à jour');
      }
    } catch (error) {
      console.error('Error updating imputation:', error);
      message.error('Erreur lors de la mise à jour');
    } finally {
      setSubmitting(false);
    }
  };

  const deleteCraEntry = async (entryId) => {
    try {
      const result = await deleteImputation(entryId);

      if (result.success) {
        message.success('Imputation supprimée');
        // Update drawer entries
        setDayEntries(prev => prev.filter(e => e.id_imputation !== entryId));
        fetchMonthlyReport(selectedMonth, true);
      } else {
        message.error(result.error || 'Erreur lors de la suppression');
      }
    } catch (error) {
      console.error('Error deleting imputation:', error);
      message.error('Erreur lors de la suppression');
    }
  };

  const toggleCountry = () => {
    const newCountry = selectedCountry === 'FR' ? 'MA' : 'FR';
    setSelectedCountry(newCountry);
    fetchHolidays(selectedMonth);
  };

  // Open submission modal for specific project
  const openSubmissionModalForProject = (projectId, projectTitle, projectImputations) => {
    console.log('🔍 openSubmissionModalForProject called:', { projectId, projectTitle, projectImputations });
    console.log('🔍 All imputations:', imputations);

    // Statuses that indicate the entry has been submitted and is in process or validated
    const submittedStatuses = ['EVP', 'Envoyé', 'Validé', 'VE', 'VC'];

    // Filter entries that can be submitted: not yet submitted OR cancelled by ESN (can resubmit)
    const projectEntries = projectImputations.filter(imp =>
      !submittedStatuses.includes(imp.statut) && 
      (imp.statut === 'À saisir' || imp.statut === 'Annulé' || !imp.statut || imp.statut === '')
    );

    console.log('🔍 Filtered projectEntries:', projectEntries);

    if (projectEntries.length === 0) {
      // Debug: check what statuses we have
      const statuses = projectImputations.map(imp => imp.statut);
      console.log('❌ No entries to submit. Existing statuses:', statuses);
      message.info('Aucune entrée CRA à soumettre pour ce projet');
      return;
    }

    // Mark all project entries as selected
    const entriesWithSelection = projectEntries.map(entry => ({
      ...entry,
      selected: true
    }));

    setCraEntriesToSubmit(entriesWithSelection);
    setSelectedContractId(projectId);
    setSubmissionModalVisible(true);
  };

  // Submit CRA for validation
  const submitForValidation = async (selectedEntries) => {
    setSubmitting(true);
    try {
      const formattedPeriod = selectedMonth.format('MM_YYYY');

      console.log('🔍 submitForValidation - selectedEntries:', selectedEntries);

      // Update each selected imputation's status to EVP (En Validation Prestataire)
      const updatePromises = selectedEntries.map(entry => {
        console.log('Updating imputation:', entry.id_imputation, 'to status EVP');

        // Send ALL required fields for the update - handle undefined values
        const updateData = {
          id_consultan: entry.id_consultan,
          période: entry.période,
          jour: entry.jour,
          Durée: entry.Durée,
          type_imputation: entry.type_imputation || (entry.type === 'travail' ? 'Jour Travaillé' : 'Absence'),
          type: entry.type,
          id_bdc: entry.id_bdc || 0,
          id_client: entry.id_client || 0,
          id_esn: entry.id_esn,
          statut: 'EVP',  // This is what we're changing
          commentaire: entry.commentaire || ''
        };

        console.log('🔍 Update data being sent:', updateData);

        return updateImputation(entry.id_imputation, updateData);
      });

      const results = await Promise.all(updatePromises);

      console.log('🔍 Update results:', results);

      // Log actual response data
      results.forEach((result, index) => {
        console.log(`🔍 Result ${index}:`, {
          success: result.success,
          data: result.data,
          error: result.error
        });
      });

      // Check if all updates were successful
      const allSuccess = results.every(result => result.success);
      const failedCount = results.filter(result => !result.success).length;
      const failedResults = results.filter(result => !result.success);

      if (failedResults.length > 0) {
        console.log('❌ Failed updates:', failedResults);
      }

      if (allSuccess) {
        message.success(`${selectedEntries.length} imputation(s) soumise(s) pour validation avec succès`);
        setSubmissionModalVisible(false);
        setSelectedContractId(null);
        setCraEntriesToSubmit([]);

        // Refresh data
        fetchMonthlyReport(selectedMonth);
      } else if (failedCount < selectedEntries.length) {
        message.warning(`${selectedEntries.length - failedCount} imputation(s) soumise(s), ${failedCount} échec(s)`);
        setSubmissionModalVisible(false);
        setSelectedContractId(null);
        setCraEntriesToSubmit([]);

        // Refresh data
        fetchMonthlyReport(selectedMonth);
      } else {
        message.error('Erreur lors de la soumission des imputations');
      }
    } catch (error) {
      console.error('Error submitting CRA:', error);
      message.error('Erreur lors de la soumission du CRA');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSendProjectCRA = async (projectId, projectTitle, projectImputations) => {
    openSubmissionModalForProject(projectId, projectTitle, projectImputations);
  };

  const handleSendCRA = async () => {
    Modal.confirm({
      title: 'Envoyer le CRA',
      content: `Voulez-vous envoyer le CRA de ${craData.month} à votre ESN ? Cette action changera le statut de toutes vos imputations.`,
      okText: 'Envoyer',
      cancelText: 'Annuler',
      onOk: async () => {
        try {
          setLoading(true);
          const period = selectedMonth.format('MM_YYYY');

          // Update all imputations for this period to "Envoyé"
          const updatePromises = imputations.map(imp =>
            updateImputation(imp.id_imputation, {
              ...imp,
              statut: 'Envoyé'
            })
          );

          await Promise.all(updatePromises);

          message.success('CRA envoyé avec succès');
          fetchMonthlyReport(selectedMonth);
        } catch (error) {
          console.error('Error sending CRA:', error);
          message.error('Erreur lors de l\'envoi du CRA');
        } finally {
          setLoading(false);
        }
      }
    });
  };

  const createColumns = () => {
    const columns = [
      {
        title: 'Projet / Client',
        dataIndex: 'info',
        key: 'info',
        fixed: 'left',
        width: 250,
        render: (text, record) => {
          if (record.isClientGroup) {
            return <strong style={{ color: '#1890ff', fontSize: '14px' }}>{record.clientName}</strong>;
          }
          if (record.isAbsence) {
            return (
              <div style={{ paddingLeft: 16 }}>
                <div style={{ fontWeight: 500, color: '#fa8c16' }}>{record.projectTitle}</div>
                <div style={{ fontSize: '11px', color: '#888' }}>Congés, formations, absences</div>
              </div>
            );
          }
          if (record.isTotal) {
            return <strong style={{ fontSize: '14px' }}>TOTAL</strong>;
          }
          // Get project info for display
          const project = projectsById[normalizeId(record.projectId)];
          const allocatedDays = project?.jours;
          const consumedDays = getProjectConsumedDays(record.projectId);
          const isLimitReached = isProjectLimitReached(record.projectId);
          const dateDebut = project?.date_debut ? dayjs(project.date_debut).format('DD/MM/YY') : null;
          const dateFin = project?.date_fin ? dayjs(project.date_fin).format('DD/MM/YY') : null;
          
          return (
            <div style={{ paddingLeft: 16 }}>
              <div style={{ fontWeight: 500 }}>{record.projectTitle}</div>
              <div style={{ fontSize: '11px', color: '#666', marginTop: 2 }}>
                {dateDebut && dateFin ? (
                  <span> {dateDebut} → {dateFin}</span>
                ) : dateDebut ? (
                  <span> Début: {dateDebut}</span>
                ) : dateFin ? (
                  <span> Fin: {dateFin}</span>
                ) : null}
              </div>
              {allocatedDays && (
                <div style={{ fontSize: '11px', marginTop: 2 }}>
                  <span style={{ 
                    color: isLimitReached ? '#ff4d4f' : consumedDays >= allocatedDays * 0.8 ? '#fa8c16' : '#52c41a',
                    fontWeight: 500 
                  }}>
                     {consumedDays}/{allocatedDays}j
                    {isLimitReached && ' (Limite)'}
                  </span>
                </div>
              )}
            </div>
          );
        }
      },
      {
        title: 'Statut',
        dataIndex: 'statut',
        key: 'statut',
        width: 100,
        align: 'center',
        render: (text, record) => {
          if (record.isTotal) return null;

          // Handle absence row
          if (record.isAbsence) {
            const absenceImputations = imputations.filter(imp =>
              imp.type === 'absence' ||
              ['Congé', 'Formation', 'Maladie', 'Absence'].includes(imp.type_imputation)
            );

            const submittedStatuses = ['EVP', 'Envoyé', 'Validé', 'VE', 'VC'];
            const allSent = absenceImputations.length > 0 && absenceImputations.every(imp => submittedStatuses.includes(imp.statut));
            const someSent = absenceImputations.some(imp => submittedStatuses.includes(imp.statut));
            const hasCancelled = absenceImputations.some(imp => imp.statut === 'Annulé');

            if (allSent) {
              return <Tag color="green">Envoyé</Tag>;
            } else if (hasCancelled) {
              return <Tag color="red">Annulé - À renvoyer</Tag>;
            } else if (someSent) {
              return <Tag color="orange">Partiel</Tag>;
            }
            return absenceImputations.length > 0 ? <Tag color="default">À saisir</Tag> : null;
          }

          // Match by exact project ID (normalized for type consistency)
          const projectImputations = imputations.filter(imp =>
            normalizeId(imp.id_bdc) === normalizeId(record.projectId)
          );

          // Check for submitted statuses: EVP (En Validation Prestataire), Envoyé, Validé
          const submittedStatuses = ['EVP', 'Envoyé', 'Validé', 'VE', 'VC'];
          const allSent = projectImputations.length > 0 && projectImputations.every(imp => submittedStatuses.includes(imp.statut));
          const someSent = projectImputations.some(imp => submittedStatuses.includes(imp.statut));
          const hasCancelled = projectImputations.some(imp => imp.statut === 'Annulé');

          if (allSent) {
            return <Tag color="green">Envoyé</Tag>;
          } else if (hasCancelled) {
            return <Tag color="red">Annulé - À renvoyer</Tag>;
          } else if (someSent) {
            return <Tag color="orange">Partiel</Tag>;
          }
          return <Tag color="default">À saisir</Tag>;
        }
      },
      {
        title: 'Total',
        dataIndex: 'total',
        key: 'total',
        width: 90,
        align: 'center',
        className: 'total-column',
        render: (total, record) => {
          if (record.isAbsence || record.isTotal) {
            return <strong>{total ? formatDuration(total) : '0h'}</strong>;
          }
          const project = projectsById[normalizeId(record.projectId)];
          const allocatedDays = project?.jours;
          const consumedDays = total || 0;
          const isLimitReached = allocatedDays && consumedDays >= allocatedDays;
          
          if (allocatedDays) {
            return (
              <Tooltip title={`${consumedDays} jour(s) sur ${allocatedDays} alloués`}>
                <strong style={{ color: isLimitReached ? '#ff4d4f' : undefined }}>
                  {formatDuration(consumedDays)}/{allocatedDays}j
                </strong>
              </Tooltip>
            );
          }
          return <strong>{consumedDays ? formatDuration(consumedDays) : '0h'}</strong>;
        }
      },
      {
        title: 'Action',
        key: 'action',
        width: 80,
        align: 'center',
        render: (text, record) => {
          if (record.isTotal) return null;

          // Handle absence row
          if (record.isAbsence) {
            const absenceImputations = imputations.filter(imp =>
              imp.type === 'absence' ||
              ['Congé', 'Formation', 'Maladie', 'Absence'].includes(imp.type_imputation)
            );

            const submittedStatuses = ['EVP', 'Envoyé', 'Validé', 'VE', 'VC'];
            const allSent = absenceImputations.length > 0 && absenceImputations.every(imp => submittedStatuses.includes(imp.statut));
            const hasImputations = absenceImputations.length > 0;

            if (!hasImputations) return null;

            return (
              <Button
                size="small"
                type={allSent ? "default" : "primary"}
                icon={<CheckOutlined />}
                disabled={allSent}
                onClick={() => handleSendProjectCRA('absence', "Pas d'activité / Absence", absenceImputations)}
                style={{
                  backgroundColor: allSent ? '#52c41a' : undefined,
                  borderColor: allSent ? '#52c41a' : undefined,
                  color: allSent ? '#fff' : undefined
                }}
              >
                {allSent ? 'Envoyé' : 'Envoyer'}
              </Button>
            );
          }

          // Match by exact project ID (normalized for type consistency)
          const projectImputations = imputations.filter(imp =>
            normalizeId(imp.id_bdc) === normalizeId(record.projectId)
          );

          // Check for submitted statuses: EVP (En Validation Prestataire), Envoyé, Validé
          const submittedStatuses = ['EVP', 'Envoyé', 'Validé', 'VE', 'VC'];
          const allSent = projectImputations.length > 0 && projectImputations.every(imp => submittedStatuses.includes(imp.statut));
          const hasImputations = projectImputations.length > 0;

          return (
            <Button
              size="small"
              type={allSent ? "default" : "primary"}
              icon={allSent ? <CheckOutlined /> : <CheckOutlined />}
              disabled={allSent}
              onClick={() => handleSendProjectCRA(record.projectId, record.projectTitle, projectImputations)}
              style={{
                backgroundColor: allSent ? '#52c41a' : undefined,
                borderColor: allSent ? '#52c41a' : undefined,
                color: allSent ? '#fff' : undefined
              }}
            >
              {allSent ? 'Envoyé' : 'Envoyer'}
            </Button>
          );
        }
      }
    ];

    // Add day columns
    const daysInMonth = selectedMonth.daysInMonth();
    for (let day = 1; day <= daysInMonth; day++) {
      const date = selectedMonth.date(day);
      const dayOfWeek = date.day();
      const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
      const holiday = isHoliday(date);

      columns.push({
        title: (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontWeight: 'bold' }}>{day}</div>
            <div style={{ fontSize: '10px', color: isWeekend ? '#999' : '#666' }}>
              {date.format('ddd')}
            </div>
            {holiday && showHolidays && (
              <Tooltip title={holiday.localName || holiday.name}>
                <div style={{ fontSize: '8px', color: '#fa8c16' }}>🎉</div>
              </Tooltip>
            )}
          </div>
        ),
        dataIndex: `day_${day}`,
        key: `day_${day}`,
        width: 55,
        align: 'center',
        className: isWeekend ? 'weekend-cell' : (holiday && showHolidays ? 'holiday-cell' : ''),
        render: (value, record) => {
          if (record.isClientGroup) {
            return null;
          }

          if (record.isTotal) {
            return null;
          }

          // Check if day has reached maximum (1 day = 8h)
          const dayData = craData?.days?.find(d => d.day === day);
          const dayTotal = dayData?.total || 0;
          const isDayFull = dayTotal >= 1;

          // For absence row, allow adding absences
          if (record.isAbsence) {
            const cellData = record.days?.[day];
            if (!cellData || cellData.duration === 0) {
              if (isWeekend) {
                return <span style={{ color: '#bbb' }}>-</span>;
              }
              // Empty cell - allow adding absence only if day not full
              if (isDayFull) {
                return (
                  <Tooltip title="Jour complet (8h)">
                    <div
                      style={{
                        minHeight: '24px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: '#f5f5f5',
                        cursor: 'not-allowed'
                      }}
                    >
                      <span style={{ color: '#d9d9d9' }}>✓</span>
                    </div>
                  </Tooltip>
                );
              }
              return (
                <div
                  onClick={() => {
                    setSelectedDay(day);
                    craForm.resetFields();
                    craForm.setFieldsValue({
                      type_imputation: 'Congé',
                      jour: day,
                      Durée: 1
                    });
                    setPreFilledFields({
                      day: true,
                      client: true, // Hide client field for absence
                      project: true, // Hide project field for absence
                      type: false,
                      isAbsenceMode: true // Flag to indicate absence-only mode
                    });
                    setCraEntryModalVisible(true);
                  }}
                  style={{
                    cursor: 'pointer',
                    minHeight: '24px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: '#fff7e6',
                    border: '1px dashed #ffa940',
                    borderRadius: '4px'
                  }}
                  className="available-cell"
                >
                  <span style={{ color: '#fa8c16', fontSize: '10px' }}>+</span>
                </div>
              );
            }
            return (
              <div
                onClick={() => openEditDrawer(day)}
                style={{
                  cursor: 'pointer',
                  backgroundColor: '#fa8c16',
                  color: '#fff',
                  padding: '4px',
                  borderRadius: '4px',
                  fontWeight: 'bold',
                  fontSize: '12px'
                }}
              >
                {formatDuration(cellData.duration)}
              </div>
            );
          }

          // Get project for this row
          const project = projectsById[record.projectId];
          const isInRange = isDayInProjectRange(day, project);
          const projectLimitReached = isProjectLimitReached(record.projectId);
          const allocatedDays = project?.jours;
          const consumedDays = getProjectConsumedDays(record.projectId);

          const cellData = record.days?.[day];
          if (!cellData || cellData.duration === 0) {
            if (isWeekend) {
              return <span style={{ color: '#bbb' }}>-</span>;
            }

            // Day is outside project date range
            if (!isInRange) {
              return (
                <Tooltip title="Hors période du contrat">
                  <div
                    style={{
                      minHeight: '24px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: '#f5f5f5',
                      cursor: 'not-allowed'
                    }}
                  >
                    <span style={{ color: '#d9d9d9' }}>✕</span>
                  </div>
                </Tooltip>
              );
            }

            // Project allocated days limit reached
            if (projectLimitReached) {
              return (
                <Tooltip title={`Limite de jours (${consumedDays}/${allocatedDays}j)`}>
                  <div
                    style={{
                      minHeight: '24px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: '#fff1f0',
                      cursor: 'not-allowed',
                      border: '1px dashed #ffa39e'
                    }}
                  >
                    <span style={{ color: '#ff4d4f', fontSize: '10px' }}>🚫</span>
                  </div>
                </Tooltip>
              );
            }

            // Day is full (8h reached)
            if (isDayFull) {
              return (
                <Tooltip title="Jour complet (8h atteintes)">
                  <div
                    style={{
                      minHeight: '24px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: '#f5f5f5',
                      cursor: 'not-allowed'
                    }}
                  >
                    <span style={{ color: '#d9d9d9' }}>✓</span>
                  </div>
                </Tooltip>
              );
            }

            // Available day within project range
            return (
              <div
                onClick={() => openAddCraModal(day, record.clientId, record.projectId, true)}
                style={{
                  cursor: 'pointer',
                  minHeight: '24px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: '#f6ffed',
                  border: '1px dashed #b7eb8f',
                  borderRadius: '4px'
                }}
                className="available-cell"
              >
                <span style={{ color: '#52c41a', fontSize: '10px' }}>+</span>
              </div>
            );
          }

          return (
            <Tooltip title={cellData.hasCancelled ? 'Annulé par ESN - Cliquez pour modifier' : undefined}>
              <div
                onClick={() => openEditDrawer(day)}
                style={{
                  cursor: 'pointer',
                  backgroundColor: cellData.hasCancelled 
                    ? '#ff4d4f' 
                    : (cellData.type === 'Congé' || cellData.type === 'Absence' ? '#fa8c16' : '#52c41a'),
                  color: '#fff',
                  padding: '4px',
                  borderRadius: '4px',
                  fontWeight: 'bold',
                  fontSize: '12px',
                  border: cellData.hasCancelled ? '2px solid #a8071a' : 'none'
                }}
              >
                {cellData.hasCancelled ? '⚠️' : ''}{formatDuration(cellData.duration)}
              </div>
            </Tooltip>
          );
        }
      });
    }

    return columns;
  };

  const createTableData = () => {
    const data = [];

    console.log('=== createTableData Debug ===');
    console.log('All imputations:', imputations);
    console.log('Projects by ID:', projectsById);
    console.log('Clients by ID:', clientsById);

    // Add all projects directly without client grouping
    Object.values(clientsById).forEach(client => {
      console.log(`Processing client ${client.name}, projects:`, client.projects);

      const clientProjects = client.projects
        .map(projectId => {
          const project = projectsById[projectId];
          if (!project) {
            console.log(`  ⚠️ Project not found for ID: ${projectId} (type: ${typeof projectId})`);
            console.log(`     Available keys:`, Object.keys(projectsById));
          }
          return project;
        })
        .filter(Boolean);

      // Project rows
      clientProjects.forEach(project => {
        // Get imputations for this project - match by normalized id_bdc (handles string vs number)
        const projectImputations = imputations.filter(imp =>
          normalizeId(imp.id_bdc) === normalizeId(project.id_bdc)
        );

        console.log(`Project "${project.project_title}" (id_bdc: ${project.id_bdc}):`,
          projectImputations.length, 'imputations found');

        // Debug: show all imputation id_bdc values for comparison
        if (projectImputations.length === 0 && imputations.length > 0) {
          console.log('  🔍 No matches found. Imputation id_bdcs:',
            [...new Set(imputations.map(imp => `${imp.id_bdc} (${typeof imp.id_bdc})`))]);
          console.log('  🔍 Looking for project.id_bdc:', project.id_bdc, `(${typeof project.id_bdc})`);
        }

        const projectTotal = projectImputations.reduce((sum, e) => sum + parseFloat(e.Durée || 0), 0);

        const days = {};
        craData?.days?.forEach(dayData => {
          const dayEntries = projectImputations.filter(imp => parseInt(imp.jour) === dayData.day);
          const dayTotal = dayEntries.reduce((sum, e) => sum + parseFloat(e.Durée || 0), 0);
          if (dayTotal > 0) {
            days[dayData.day] = {
              duration: dayTotal,
              type: dayEntries[0]?.type_imputation,
              statut: dayEntries[0]?.statut,
              hasCancelled: dayEntries.some(e => e.statut === 'Annulé')
            };
          }
        });

        data.push({
          key: `project_${project.id_bdc}`,
          isProject: true,
          projectId: project.id_bdc,
          hasRealBdc: project.has_real_bdc,
          projectTitle: project.project_title,
          bdcNumber: project.numero_bdc,
          clientId: client.id,
          total: projectTotal,
          days,
          dateDebut: project.date_debut,
          dateFin: project.date_fin,
          allocatedDays: project.jours // Add allocated days from project
        });
      });
    });

    // Add Absence row for all non-work imputations (Congé, Formation, Maladie, Absence)
    // Only show this row when there are active projects in the calendar
    const hasProjects = data.length > 0;
    
    if (hasProjects) {
      const absenceImputations = imputations.filter(imp =>
        imp.type === 'absence' ||
        ['Congé', 'Formation', 'Maladie', 'Absence'].includes(imp.type_imputation)
      );

      const absenceTotal = absenceImputations.reduce((sum, e) => sum + parseFloat(e.Durée || 0), 0);
      const absenceDays = {};

      craData?.days?.forEach(dayData => {
        const dayEntries = absenceImputations.filter(imp => parseInt(imp.jour) === dayData.day);
        const dayTotal = dayEntries.reduce((sum, e) => sum + parseFloat(e.Durée || 0), 0);
        if (dayTotal > 0) {
          absenceDays[dayData.day] = {
            duration: dayTotal,
            type: dayEntries[0]?.type_imputation || dayEntries[0]?.type,
            statut: dayEntries[0]?.statut,
            hasCancelled: dayEntries.some(e => e.statut === 'Annulé')
          };
        }
      });

      // Add absence row only when there are projects
      data.push({
        key: 'absence_row',
        isAbsence: true,
        projectTitle: "Pas d'activité / Absence",
        bdcNumber: '-',
        total: absenceTotal,
        days: absenceDays
      });
    }

    // Grand total row - only show when there are projects
    if (hasProjects) {
      data.push({
        key: 'grand_total',
        isTotal: true,
        total: craData?.totalDays?.toFixed(1) || 0
      });
    }

    return data;
  };

  const renderLegend = () => (
    <div style={{ marginTop: 16, padding: '12px 16px', background: '#fafafa', borderRadius: 8 }}>
      <Space size="large" wrap>
        <span><span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#f6ffed', border: '1px dashed #b7eb8f', borderRadius: 4, marginRight: 8 }}></span>Disponible</span>
        <span><span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#52c41a', borderRadius: 4, marginRight: 8 }}></span>Travail</span>
        <span><span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#fa8c16', borderRadius: 4, marginRight: 8 }}></span>Congé / Absence</span>
        <span><span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#ff4d4f', border: '2px solid #a8071a', borderRadius: 4, marginRight: 8 }}></span>Annulé par ESN</span>
        <span><span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#fff1f0', border: '1px dashed #ffa39e', borderRadius: 4, marginRight: 8 }}></span>Limite jours</span>
        <span><span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#f5f5f5', borderRadius: 4, marginRight: 8 }}></span>Hors contrat</span>
        <span><span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#f0f0f0', borderRadius: 4, marginRight: 8 }}></span>Week-end</span>
        {showHolidays && <span><span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 4, marginRight: 8 }}></span>Jour férié</span>}
      </Space>
    </div>
  );

  const tabItems = [
    {
      key: 'cra',
      label: (
        <span>
          <CalendarOutlined />
          CRA
        </span>
      ),
      children: (
        <div>
          {/* Controls */}
          <div style={{ marginBottom: 16 }}>
            <Row gutter={16} align="middle" justify="space-between">
              <Col>
                <Space>
                  <Button icon={<LeftOutlined />} onClick={() => setSelectedMonth(selectedMonth.subtract(1, 'month'))} />
                  <input
                    type="month"
                    value={selectedMonth.format('YYYY-MM')}
                    onChange={(e) => setSelectedMonth(dayjs(e.target.value))}
                    style={{ padding: '4px 11px', borderRadius: '6px', border: '1px solid #d9d9d9' }}
                  />
                  <Button icon={<RightOutlined />} onClick={() => setSelectedMonth(selectedMonth.add(1, 'month'))} />
                  <Button icon={<ReloadOutlined />} onClick={() => fetchMonthlyReport(selectedMonth)} />
                </Space>
              </Col>
              <Col>
                <Space>
                  <Switch
                    checked={showHolidays}
                    onChange={(checked) => setShowHolidays(checked)}
                    size="small"
                  />
                  <span>Jours fériés ({selectedCountry === 'FR' ? 'France' : 'Maroc'})</span>
                  <Button size="small" type="text" onClick={toggleCountry}>
                    {selectedCountry === 'FR' ? '🇫🇷 → 🇲🇦' : '🇲🇦 → 🇫🇷'}
                  </Button>
                </Space>
              </Col>
            </Row>
          </div>

          {/* Summary */}
          {craData && (
            <Alert
              message={
                <Space split={<span style={{ color: '#d9d9d9' }}>|</span>}>
                  <span><strong>Période:</strong> {craData.month}</span>
                  <span><strong>Heures travaillées:</strong> {formatDuration(craData.totalDays || 0)}</span>
                  <span><strong>Jours ouvrés:</strong> {craData.potentialWorkDays}</span>
                </Space>
              }
              type="info"
              style={{ marginBottom: 16 }}
            />
          )}

          {/* Alert for cancelled CRAs
          {imputations.some(imp => imp.statut === 'Annulé') && (
            <Alert
              message="CRA Annulé par l'ESN"
              description={
                <div>
                  <p>Certaines de vos imputations ont été annulées par votre ESN et nécessitent des corrections.</p>
                  {imputations.filter(imp => imp.statut === 'Annulé').map((imp, idx) => (
                    <div key={idx} style={{ marginTop: 8, padding: '8px 12px', background: '#fff', borderRadius: 4, border: '1px solid #ffa39e' }}>
                      <strong>Jour {imp.jour}:</strong> {imp.commentaire || 'Aucune remarque'}
                    </div>
                  ))}
                  <p style={{ marginTop: 12, marginBottom: 0 }}>
                    <strong>Action requise:</strong> Modifiez les entrées concernées puis renvoyez le CRA pour validation.
                  </p>
                </div>
              }
              type="error"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )} */}

          {loading ? (
            <div style={{ textAlign: 'center', padding: 40 }}><Spin size="large" /></div>
          ) : (
            <div ref={tableScrollRef}>
              <Table
                columns={createColumns()}
                dataSource={createTableData()}
                bordered
                size="small"
                pagination={false}
                scroll={{ x: 'max-content' }}
                className="cra-monthly-table"
              rowClassName={(record) => {
                if (record.isClientGroup) return 'client-group-header-row';
                if (record.isAbsence) return 'absence-row';
                if (record.isTotal) return 'grand-total-row';
                return '';
              }}
              />
            </div>
          )}

          {renderLegend()}
        </div>
      ),
    },
    {
      key: 'projects',
      label: (
        <span>
          <ProjectOutlined />
          Mes projets
        </span>
      ),
      children: (
        <Table
          columns={[
            {
              title: 'Projet',
              dataIndex: 'project_title',
              key: 'project_title',
              render: (text) => <strong>{text}</strong>,
            },
            {
              title: 'ESN',
              dataIndex: 'esn_name',
              key: 'esn_name',
            },
            {
              title: 'Date début',
              dataIndex: 'date_debut',
              key: 'date_debut',
              render: (date) => date ? dayjs(date).format('DD/MM/YYYY') : '-',
            },
            {
              title: 'Date fin',
              dataIndex: 'date_fin',
              key: 'date_fin',
              render: (date) => date ? dayjs(date).format('DD/MM/YYYY') : '-',
            },
            {
              title: 'Jours',
              dataIndex: 'jours',
              key: 'jours',
            },
            {
              title: 'Statut',
              key: 'status',
              render: (_, record) => {
                const statusValue = record.status || record.statut || 'En cours';
                let color = 'default';
                if (statusValue === 'En cours') color = 'blue';
                else if (statusValue === 'Terminé') color = 'green';
                else if (statusValue === 'Annulé') color = 'red';
                return <Tag color={color}>{statusValue}</Tag>;
              },
            },
          ]}
          dataSource={allProjects}
          rowKey="id_bdc"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      ),
    },
  ];

  return (
    <div className="monthly-cra-report">
      <Card>
        <div className="report-header" style={{ marginBottom: 24 }}>
          <Row justify="space-between" align="middle" gutter={16}>
            <Col>
              <Title level={4} style={{ margin: 0 }}>
                CRA - {userName}
              </Title>
            </Col>
            <Col>
              <Button icon={<LogoutOutlined />} onClick={logout}>Déconnexion</Button>
            </Col>
          </Row>
        </div>

        <Tabs defaultActiveKey="cra" items={tabItems} />

        <style jsx="true">{`
          .weekend-cell {
            background-color: #f0f0f0 !important;
          }
          .holiday-cell {
            background-color: #fffbe6 !important;
          }
          .client-group-header-row {
            background-color: #f0f7ff !important;
            font-weight: bold;
          }
          .absence-row {
            background-color: #fff7e6 !important;
          }
          .grand-total-row {
            background-color: #e6f7ff !important;
            font-weight: bold;
            border-top: 2px solid #1890ff !important;
          }
          .total-column {
            border-right: 2px solid #d9d9d9 !important;
            background-color: #fafafa !important;
          }
          .cra-monthly-table .ant-table-cell {
            padding: 8px 4px;
            text-align: center;
          }
          .empty-cell:hover {
            background-color: #e6f7ff;
          }
          .available-cell:hover {
            background-color: #d9f7be !important;
            border-color: #73d13d !important;
          }
        `}</style>
      </Card>

      {/* Add Entry Modal */}
      <Modal
        title={`Ajouter une imputation - ${selectedMonth.format('MMMM YYYY')}`}
        open={craEntryModalVisible}
        onCancel={() => setCraEntryModalVisible(false)}
        footer={null}
        destroyOnClose
      >
        <Form
          form={craForm}
          layout="vertical"
          onFinish={submitCraEntry}
          onValuesChange={(changedValues) => {
            if (changedValues.type_imputation && changedValues.type_imputation !== 'Jour Travaillé') {
              craForm.setFieldsValue({ id_client: undefined, id_bdc: undefined });
            }
          }}
        >
          <Row gutter={16}>
            {!preFilledFields.type && (
              <Col span={preFilledFields.day ? 24 : 12}>
                <Form.Item
                  name="type_imputation"
                  label="Type"
                  rules={[{ required: true, message: 'Type requis' }]}
                >
                  <Select>
                    {!preFilledFields.isAbsenceMode && <Option value="Jour Travaillé">Travail</Option>}
                    <Option value="Absence">Absence</Option>
                    <Option value="Congé">Congé</Option>
                    <Option value="Formation">Formation</Option>
                    <Option value="Maladie">Maladie</Option>
                  </Select>
                </Form.Item>
              </Col>
            )}
            {!preFilledFields.day && (
              <Col span={12}>
                <Form.Item
                  name="jour"
                  label="Jour"
                  rules={[{ required: true, message: 'Jour requis' }]}
                >
                  <Select>
                    {Array.from({ length: selectedMonth.daysInMonth() }, (_, i) => i + 1).map(day => (
                      <Option key={day} value={day}>{day}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
            )}
          </Row>
          {!preFilledFields.client && !preFilledFields.project && (
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="id_client" label="Client">
                  <Select
                    placeholder="Sélectionner un client"
                    allowClear
                    disabled={craForm.getFieldValue('type_imputation') !== 'Jour Travaillé'}
                    onChange={() => craForm.setFieldsValue({ id_bdc: undefined })}
                  >
                    {Object.values(clientsById).map(client => (
                      <Option key={client.id} value={client.id}>{client.name}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="id_bdc" label="Projet">
                  <Select
                    placeholder="Sélectionner un projet"
                    allowClear
                    disabled={craForm.getFieldValue('type_imputation') !== 'Jour Travaillé' || !craForm.getFieldValue('id_client')}
                  >
                    {craForm.getFieldValue('id_client') &&
                      clientsById[craForm.getFieldValue('id_client')]?.projects?.map(projectId => {
                        const project = projectsById[projectId];
                        return (
                          <Option key={projectId} value={projectId}>
                            {project?.project_title || projectId}
                          </Option>
                        );
                      })}
                  </Select>
                </Form.Item>
              </Col>
            </Row>
          )}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="Durée"
                label="Durée"
                rules={[{ required: true, message: 'Durée requise' }]}
              >
                <Select>
                  <Option value={0.125}>1h</Option>
                  <Option value={0.25}>2h</Option>
                  <Option value={0.375}>3h</Option>
                  <Option value={0.5}>4h (0.5 jour)</Option>
                  <Option value={0.625}>5h</Option>
                  <Option value={0.75}>6h</Option>
                  <Option value={0.875}>7h</Option>
                  <Option value={1}>8h (1 jour)</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="commentaire" label="Commentaire">
            <TextArea rows={2} />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setCraEntryModalVisible(false)}>Annuler</Button>
              <Button type="primary" htmlType="submit" loading={submitting}>Soumettre</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Drawer */}
      <Drawer
        title={`Imputations du ${selectedDay} ${selectedMonth.format('MMMM YYYY')}`}
        placement="right"
        onClose={() => {
          setEditDrawerVisible(false);
          setSelectedCraEntry(null);
        }}
        open={editDrawerVisible}
        width={500}
      >
        {dayEntries.length === 0 ? (
          <Empty description="Aucune imputation" />
        ) : (
          <>
            <div style={{ marginBottom: 16 }}>
              <Text strong>Total: {dayEntries.reduce((sum, e) => sum + parseFloat(e.Durée || 0), 0)} jour(s)</Text>
            </div>
            <List
              dataSource={dayEntries}
              renderItem={entry => {
                const project = projectsById[entry.id_bdc];
                const client = clientsById[entry.id_client];
                const isCancelled = entry.statut === 'Annulé';

                return (
                  <List.Item
                    actions={[
                      <Button size="small" onClick={() => editCraEntry(entry)}>Modifier</Button>,
                      <Button size="small" danger onClick={() => deleteCraEntry(entry.id_imputation)}>Supprimer</Button>
                    ]}
                    style={isCancelled ? { backgroundColor: '#fff2f0', borderLeft: '3px solid #ff4d4f', paddingLeft: 12 } : {}}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <Tag color={entry.type_imputation === 'Congé' || entry.type_imputation === 'Absence' ? 'orange' : 'green'}>
                            {entry.type_imputation}
                          </Tag>
                          <Text>{entry.Durée} jour(s)</Text>
                          {isCancelled && <Tag color="red">Annulé par ESN</Tag>}
                        </Space>
                      }
                      description={
                        <>
                          <div>Client: {client?.name || 'N/A'}</div>
                          <div>Projet: {project?.project_title || 'N/A'}</div>
                          {isCancelled && entry.commentaire && (
                            <div style={{ marginTop: 8, padding: '8px 12px', background: '#fff', borderRadius: 4, border: '1px solid #ffa39e' }}>
                              <strong style={{ color: '#cf1322' }}>Motif d'annulation:</strong> {entry.commentaire}
                            </div>
                          )}
                          {!isCancelled && entry.commentaire && <div>Commentaire: {entry.commentaire}</div>}
                        </>
                      }
                    />
                  </List.Item>
                );
              }}
            />

            {selectedCraEntry && (
              <div style={{ marginTop: 24, borderTop: '1px solid #f0f0f0', paddingTop: 24 }}>
                <Title level={5}>Modifier l'imputation</Title>
                <Form form={editForm} layout="vertical" onFinish={updateCraEntry}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="id_client" label="Client">
                        <Select onChange={() => editForm.setFieldsValue({ id_bdc: undefined })}>
                          {Object.values(clientsById).map(client => (
                            <Option key={client.id} value={client.id}>{client.name}</Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="id_bdc" label="Projet">
                        <Select disabled={!editForm.getFieldValue('id_client')}>
                          {editForm.getFieldValue('id_client') &&
                            clientsById[editForm.getFieldValue('id_client')]?.projects?.map(projectId => (
                              <Option key={projectId} value={projectId}>
                                {projectsById[projectId]?.project_title || projectId}
                              </Option>
                            ))}
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="type_imputation" label="Type">
                        <Select>
                          <Option value="Jour Travaillé">Travail</Option>
                          <Option value="Congé">Congé</Option>
                          <Option value="Formation">Formation</Option>
                          <Option value="Maladie">Maladie</Option>
                          <Option value="Absence">Absence</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="Durée" label="Durée">
                        <Select>
                          <Option value={0.5}>0.5 jour</Option>
                          <Option value={1}>1 jour</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>
                  <Form.Item name="commentaire" label="Commentaire">
                    <TextArea rows={3} />
                  </Form.Item>
                  <Form.Item>
                    <Space style={{ float: 'right' }}>
                      <Button onClick={() => setSelectedCraEntry(null)}>Annuler</Button>
                      <Button type="primary" htmlType="submit" loading={submitting}>Mettre à jour</Button>
                    </Space>
                  </Form.Item>
                </Form>
              </div>
            )}
          </>
        )}
      </Drawer>

      {/* Submission Modal */}
      <Modal
        title={`Soumettre le CRA pour validation${selectedContractId ? ' - Contrat spécifique' : ''}`}
        open={submissionModalVisible}
        onCancel={() => {
          setSubmissionModalVisible(false);
          setSelectedContractId(null);
          setCraEntriesToSubmit([]);
        }}
        footer={[
          <Button
            key="cancel"
            onClick={() => {
              setSubmissionModalVisible(false);
              setSelectedContractId(null);
              setCraEntriesToSubmit([]);
            }}
          >
            Annuler
          </Button>,
          <Button
            key="submit"
            type="primary"
            onClick={() => {
              const selectedEntries = craEntriesToSubmit.filter(e => e.selected);
              if (selectedEntries.length === 0) {
                message.info('Veuillez sélectionner au moins une imputation');
                return;
              }
              submitForValidation(selectedEntries);
            }}
            loading={submitting}
            disabled={!craEntriesToSubmit.some(e => e.selected)}
          >
            Soumettre pour validation
          </Button>
        ]}
      >
        <Alert
          message="Soumission pour validation ESN"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <List
          dataSource={craEntriesToSubmit}
          renderItem={(item) => {
            const client = clientsById[item.id_client];
            const project = projectsById[item.id_bdc];

            return (
              <List.Item>
                <Checkbox
                  checked={item.selected}
                  onChange={(e) => {
                    const updatedEntries = craEntriesToSubmit.map(entry =>
                      entry.id_imputation === item.id_imputation
                        ? { ...entry, selected: e.target.checked }
                        : entry
                    );
                    setCraEntriesToSubmit(updatedEntries);
                  }}
                >
                  <div style={{ width: '100%' }}>
                    <div>
                      <strong>Date:</strong> {item.jour} {selectedMonth.format('MMMM YYYY')}
                    </div>
                    {item.id_client && item.id_bdc ? (
                      <>
                        <div><strong>Client:</strong> {client?.name || 'N/A'}</div>
                        <div><strong>Projet:</strong> {project?.project_title || 'N/A'}</div>
                      </>
                    ) : (
                      <div>
                        <strong>Type:</strong> {item.type_imputation || item.type}
                      </div>
                    )}
                    <div>
                      <strong>Durée:</strong> {formatDuration(parseFloat(item.Durée))}
                    </div>
                    {item.commentaire && (
                      <div><strong>Commentaire:</strong> {item.commentaire}</div>
                    )}
                  </div>
                </Checkbox>
              </List.Item>
            );
          }}
          locale={{
            emptyText: <Empty description="Aucune imputation à soumettre" />
          }}
          style={{ maxHeight: '400px', overflowY: 'auto' }}
        />

        <div style={{ marginTop: 16, textAlign: 'right' }}>
          <Text strong>
            {craEntriesToSubmit.filter(e => e.selected).length} imputation(s) sélectionnée(s)
          </Text>
        </div>
      </Modal>
    </div>
  );
};

export default ConsultantCRA;
