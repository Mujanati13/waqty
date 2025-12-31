import { useState, useEffect } from 'react';
import { 
  Layout, Card, Row, Col, Statistic, Table, Button, 
  Tag, Space, Typography, Modal, Form, Input, DatePicker,
  message, Popconfirm, Select, Tabs, InputNumber, Progress, Tooltip
} from 'antd';
import { 
  UserOutlined, ProjectOutlined, FileTextOutlined, 
  PlusOutlined, EditOutlined, DeleteOutlined,
  CheckCircleOutlined, ClockCircleOutlined, LogoutOutlined,
  EyeOutlined, BarChartOutlined, CalendarOutlined, ReloadOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { getEsnId, getUserName } from '../helper/auth';
import { getConsultantsByESN, createConsultant, updateConsultant, deleteConsultant } from '../services/consultantService';
import { getCRAsByESN, updateCRAStatus, CRA_STATUS } from '../services/craService';
import { createProject, getProjects, getProjectDetails, updateProjectConsultants, getProjectConsultants, addConsultantToProject, removeConsultantFromProject } from '../services/projectService';
import { logout } from '../services/authService';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

const ESNDashboard = () => {
  const [consultants, setConsultants] = useState([]);
  const [cras, setCras] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [projectModalVisible, setProjectModalVisible] = useState(false);
  const [editProjectModalVisible, setEditProjectModalVisible] = useState(false);
  const [editingConsultant, setEditingConsultant] = useState(null);
  const [editingProject, setEditingProject] = useState(null);
  const [selectedPeriod, setSelectedPeriod] = useState(dayjs());
  const [selectedProjectForConsultant, setSelectedProjectForConsultant] = useState(null);
  const [projectConsultants, setProjectConsultants] = useState([]);
  const [loadingConsultants, setLoadingConsultants] = useState(false);
  const [consultantModalVisible, setConsultantModalVisible] = useState(false);
  const [isViewOnlyMode, setIsViewOnlyMode] = useState(false);
  const [consultantActivityModalVisible, setConsultantActivityModalVisible] = useState(false);
  const [selectedConsultantForActivity, setSelectedConsultantForActivity] = useState(null);
  const [consultantActivityLoading, setConsultantActivityLoading] = useState(false);
  const [consultantProjects, setConsultantProjects] = useState([]);
  const [consultantCras, setConsultantCras] = useState([]);
  const [activityFilterProject, setActivityFilterProject] = useState(null);
  const [activityFilterStatus, setActivityFilterStatus] = useState(null);
  const [activityFilterType, setActivityFilterType] = useState(null);
  const [projectFilterStatus, setProjectFilterStatus] = useState(null);
  const [projectFilterDateRange, setProjectFilterDateRange] = useState(null);
  const [form] = Form.useForm();
  const [projectForm] = Form.useForm();
  const [editProjectForm] = Form.useForm();
  const [consultantAssignForm] = Form.useForm();

  const esnId = getEsnId();
  const userName = getUserName();

  useEffect(() => {
    loadData();
  }, [selectedPeriod]);

  const loadData = async () => {
    setLoading(true);
    try {
      // Load consultants
      const consultantsResult = await getConsultantsByESN(esnId);
      if (consultantsResult.success) {
        // Filter only consultants (not commercials/admins)
        const consultantsList = (consultantsResult.data || []).filter(
          c => c.Consultant === true || c.Consultant === 1 || c.est_consultant === true || c.est_consultant === 1
        );
        setConsultants(consultantsList);
      }

      // Load CRAs for selected period
      const period = selectedPeriod.format('MM_YYYY');
      console.log('📅 Loading CRAs for period:', period, 'ESN ID:', esnId);
      const crasResult = await getCRAsByESN(esnId, period);
      console.log('📊 CRAs API result:', crasResult);
      if (crasResult.success) {
        // Extract the data array from the response
        const crasData = crasResult.data?.data || crasResult.data || [];
        // Ensure cras is always an array
        const crasList = Array.isArray(crasData) ? crasData : (crasData ? [crasData] : []);
        console.log('📋 CRAs list:', crasList);
        console.log('📋 CRAs count:', crasList.length);
        if (crasList.length > 0) {
          console.log('📋 Sample CRA:', crasList[0]);
          console.log('📋 All CRA statuses:', crasList.map(c => c.statut));
        }
        setCras(crasList);
      }

      // Load projects (BDC)
      const projectsResult = await getProjects();
      console.log('Projects API result:', projectsResult);
      if (projectsResult.success) {
        const projectsData = projectsResult.data || [];
        console.log('All projects:', projectsData);
        console.log('Current ESN ID:', esnId, 'Type:', typeof esnId);
        
        // Log first project to see its structure
        if (projectsData.length > 0) {
          console.log('Sample project:', projectsData[0]);
          console.log('Sample project esn_id:', projectsData[0].esn_id, 'Type:', typeof projectsData[0].esn_id);
        }
        
        // Filter projects for this ESN (backend returns esn_id field)
        // Convert both to numbers for comparison
        const esnProjects = projectsData.filter(p => {
          const projectEsnId = parseInt(p.esn_id, 10);
          const currentEsnId = parseInt(esnId, 10);
          console.log(`Comparing project esn_id ${projectEsnId} with ${currentEsnId}: ${projectEsnId === currentEsnId}`);
          return projectEsnId === currentEsnId;
        });
        console.log('Filtered projects for ESN:', esnProjects);
        
        // Ensure all projects have 'status' field (map from 'statut' if needed)
        const projectsWithStatus = esnProjects.map(p => ({
          ...p,
          status: p.status || p.statut || 'En cours'
        }));
        
        setProjects(projectsWithStatus);
      }
    } catch (error) {
      console.error('Error loading data:', error);
      // message.error('Erreur lors du chargement des données');
    } finally {
      setLoading(false);
    }
  };

  const handleAddConsultant = () => {
    setEditingConsultant(null);
    form.resetFields();
    form.setFieldsValue({ Consultant: true, Actif: true });
    setModalVisible(true);
  };

  const handleEditConsultant = (consultant) => {
    setEditingConsultant(consultant);
    form.resetFields(); // Reset form before populating
    const dateValue = consultant.Date_naissance || consultant.date_naissance;
    const formValues = {
      Nom: consultant.Nom || consultant.nom || '',
      Prenom: consultant.Prenom || consultant.prenom || '',
      email: consultant.email || consultant.Email || '',
      Poste: consultant.Poste || consultant.poste || '',
      Date_naissance: dateValue ? dayjs(dateValue, 'YYYY-MM-DD') : null,
      LinkedIN: consultant.LinkedIN || consultant.linkedin || consultant.Linkedin || '',
    };
    console.log('📝 Editing consultant:', consultant);
    console.log('📝 Form values:', formValues);
    form.setFieldsValue(formValues);
    setModalVisible(true);
  };

  const handleDeleteConsultant = async (id) => {
    const result = await deleteConsultant(id);
    if (result.success) {
      message.success('Consultant supprimé');
      loadData();
    } else {
      message.error(result.error || 'Erreur lors de la suppression');
    }
  };

  const handleViewConsultantActivity = async (consultant) => {
    setSelectedConsultantForActivity(consultant);
    setConsultantActivityModalVisible(true);
    setConsultantActivityLoading(true);
    
    try {
      // Get consultant's projects
      const projectsResult = await getProjects(esnId);
      if (projectsResult.success) {
        // Filter projects where this consultant is assigned
        const allProjects = projectsResult.data || [];
        const consultantProjectIds = new Set();
        
        // Check each project for this consultant
        for (const project of allProjects) {
          const consultantsResult = await getProjectConsultants(project.id_bdc);
          if (consultantsResult.success) {
            const hasConsultant = (consultantsResult.data || []).some(
              pc => pc.id_consultant === consultant.ID_collab
            );
            if (hasConsultant) {
              consultantProjectIds.add(project.id_bdc);
            }
          }
        }
        
        const consultantProjs = allProjects.filter(p => consultantProjectIds.has(p.id_bdc));
        setConsultantProjects(consultantProjs);
      }
      
      // Get consultant's CRAs (all periods)
      const allCras = Array.isArray(cras) ? cras.filter(
        cra => (cra.id_consultan || cra.consultant?.id) === consultant.ID_collab
      ) : [];
      
      setConsultantCras(allCras);
    } catch (error) {
      // message.error('Erreur lors du chargement des données');
      console.error(error);
    } finally {
      setConsultantActivityLoading(false);
    }
  };

  const handleSubmitConsultant = async (values) => {
    const consultantData = {
      ...values,
      ID_ESN: parseInt(esnId),
      Date_naissance: values.Date_naissance?.format('YYYY-MM-DD') || null,
      Consultant: true,
      Commercial: false,
      Admin: false,
      Actif: true,
    };

    // Add ID_collab when editing
    if (editingConsultant) {
      consultantData.ID_collab = editingConsultant.ID_collab;
    }

    console.log('📤 Submitting consultant data:', consultantData);
    console.log('📤 Is editing:', !!editingConsultant);

    let result;
    if (editingConsultant) {
      result = await updateConsultant(editingConsultant.ID_collab, consultantData);
    } else {
      result = await createConsultant(consultantData);
    }

    console.log('📥 API result:', result);

    if (result.success) {
      message.success(editingConsultant ? 'Consultant mis à jour' : 'Consultant créé');
      setModalVisible(false);
      setEditingConsultant(null);
      form.resetFields();
      loadData();
    } else {
      message.error(result.error || 'Erreur lors de la sauvegarde');
    }
  };

  const handleValidateCRA = async (craId) => {
    const result = await updateCRAStatus(craId, CRA_STATUS.VALIDATED);
    if (result.success) {
      // message.success('CRA validé');
      loadData();
    } else {
      message.error(result.error || 'Erreur lors de la validation');
    }
  };

  const handleRejectCRA = async (craId) => {
    const result = await updateCRAStatus(craId, CRA_STATUS.REJECTED);
    if (result.success) {
      message.warning('CRA refusé');
      loadData();
    } else {
      message.error(result.error || 'Erreur lors du refus');
    }
  };

  const handleCreateProject = () => {
    projectForm.resetFields();
    setProjectModalVisible(true);
  };

  const handleSubmitProject = async (values) => {
    try {
      const projectData = {
        esn_id: esnId,
        consultant_id: null,
        project_title: values.project_title,
        description: values.description || '',
        tjm: values.tjm,
        date_debut: values.date_debut.format('YYYY-MM-DD'),
        date_fin: values.date_fin.format('YYYY-MM-DD'),
        jours: values.jours,
        montant_total: values.jours * values.tjm,
      };

      const result = await createProject(projectData);
      if (result.status) {
        message.success('Projet créé avec succès');
        setProjectModalVisible(false);
        projectForm.resetFields();
        loadData(); // Reload projects
      } else {
        message.error(result.message || 'Erreur lors de la création du projet');
      }
    } catch (error) {
      console.error('Error creating project:', error);
      message.error('Erreur lors de la création du projet');
    }
  };

  const handleEditProject = async (project) => {
    console.log('Editing project:', project);
    setEditingProject(project);
    
    // Load full project details
    const result = await getProjectDetails(project.id_bdc);
    console.log('Project details result:', result);
    
    if (result.success && result.data) {
      const projectData = result.data;
      console.log('Setting form values with:', projectData);
      editProjectForm.setFieldsValue({
        project_title: projectData.project_title || project.project_title,
        description: projectData.description || '',
        tjm: projectData.tjm || project.tjm,
        jours: projectData.jours || project.jours,
        date_debut: projectData.date_debut ? dayjs(projectData.date_debut) : (project.date_debut ? dayjs(project.date_debut) : null),
        date_fin: projectData.date_fin ? dayjs(projectData.date_fin) : (project.date_fin ? dayjs(project.date_fin) : null),
        status: projectData.status || project.status || 'En cours',
      });
    } else {
      // Fallback to project data from table
      console.log('Using fallback data from table:', project);
      editProjectForm.setFieldsValue({
        project_title: project.project_title,
        description: project.description || '',
        tjm: project.tjm,
        jours: project.jours,
        date_debut: project.date_debut ? dayjs(project.date_debut) : null,
        date_fin: project.date_fin ? dayjs(project.date_fin) : null,
        status: project.status || 'En cours',
      });
    }
    
    setEditProjectModalVisible(true);
  };

  const handleSubmitEditProject = async (values) => {
    try {
      const updateData = {
        esn_id: esnId,
        project_title: values.project_title,
        description: values.description || '',
        tjm: values.tjm,
        date_debut: values.date_debut.format('YYYY-MM-DD'),
        date_fin: values.date_fin.format('YYYY-MM-DD'),
        jours: values.jours,
        status: values.status || 'En cours',
      };

      const result = await updateProjectConsultants(editingProject.id_bdc, updateData);

      if (result.success) {
        message.success('Projet mis à jour avec succès');
        setEditProjectModalVisible(false);
        editProjectForm.resetFields();
        setEditingProject(null);
        loadData(); // Reload projects
      } else {
        message.error(result.error || 'Erreur lors de la mise à jour du projet');
      }
    } catch (error) {
      console.error('Error updating project:', error);
      message.error('Erreur lors de la mise à jour du projet');
    }
  };

  const handleChangeProjectStatus = async (project, newStatus) => {
    try {
      const updateData = {
        esn_id: esnId,
        project_title: project.project_title,
        description: project.description || '',
        tjm: project.tjm,
        date_debut: project.date_debut,
        date_fin: project.date_fin,
        jours: project.jours,
        status: newStatus,
      };

      const result = await updateProjectConsultants(project.id_bdc, updateData);

      if (result.success) {
        message.success(`Statut changé en "${newStatus}"`);
        loadData();
      } else {
        message.error(result.error || 'Erreur lors du changement de statut');
      }
    } catch (error) {
      console.error('Error changing project status:', error);
      message.error('Erreur lors du changement de statut');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case CRA_STATUS.DRAFT: return 'default';
      case CRA_STATUS.SUBMITTED: return 'processing';
      case CRA_STATUS.ESN_VALIDATED: return 'warning';
      case CRA_STATUS.VALIDATED: return 'success';
      case CRA_STATUS.REJECTED: return 'error';
      default: return 'default';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case CRA_STATUS.DRAFT: return 'Brouillon';
      case CRA_STATUS.SUBMITTED: return 'En attente';
      case CRA_STATUS.ESN_VALIDATED: return 'Validé ESN';
      case CRA_STATUS.VALIDATED: return 'Validé Client';
      case CRA_STATUS.REJECTED: return 'Refusé';
      default: return status;
    }
  };

  const consultantColumns = [
    {
      title: 'Nom',
      key: 'nom',
      render: (_, record) => `${record.Prenom || record.prenom || ''} ${record.Nom || record.nom || ''}`.trim(),
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: 'Poste',
      dataIndex: 'Poste',
      key: 'Poste',
    },
    {
      title: 'Statut',
      key: 'status',
      render: (_, record) => (
        <Tag color={(record.Actif !== undefined ? record.Actif : record.est_actif) ? 'green' : 'red'}>
          {(record.Actif !== undefined ? record.Actif : record.est_actif) ? 'Actif' : 'Inactif'}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button 
            type="text" 
            icon={<EyeOutlined />} 
            onClick={() => handleViewConsultantActivity(record)}
            title="Voir l'activité"
          />
          <Button 
            type="text" 
            icon={<EditOutlined />} 
            onClick={() => handleEditConsultant(record)}
          />
          <Popconfirm
            title="Supprimer ce consultant ?"
            onConfirm={() => handleDeleteConsultant(record.ID_collab)}
            okText="Oui"
            cancelText="Non"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const craColumns = [
    {
      title: 'Consultant',
      key: 'consultant',
      render: (_, record) => {
        // For grouped view
        if (record.consultant) {
          return `${record.consultant.prenom || record.consultant.Prenom || ''} ${record.consultant.nom || record.consultant.Nom || ''}`.trim();
        }
        // For individual entries
        const consultant = consultants.find(c => c.ID_collab === record.id_consultan || c.ID_collab === record.consultantId);
        return consultant ? `${consultant.Prenom || consultant.prenom || ''} ${consultant.Nom || consultant.nom || ''}`.trim() : '-';
      },
    },
    {
      title: 'Période',
      key: 'periode',
      render: (_, record) => {
        const val = record.period || record.période || record.periode;
        if (!val) return '-';
        const [month, year] = val.split('_');
        return `${month}/${year}`;
      },
    },
    {
      title: 'Nombre d\'entrées',
      key: 'count',
      render: (_, record) => {
        return record.entries ? record.entries.length : 1;
      },
    },
    {
      title: 'Total jours',
      key: 'totalDays',
      render: (_, record) => {
        return record.totalDays || record.Durée || record.total_jours || 0;
      },
    },
    {
      title: 'Statut',
      dataIndex: 'statut',
      key: 'statut',
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {getStatusLabel(status)}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          {record.statut === CRA_STATUS.SUBMITTED && (
            <>
              <Button 
                type="primary" 
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={() => {
                  // Validate all entries in the group
                  if (record.entries && record.entries.length > 0) {
                    // Validate each entry
                    record.entries.forEach(entry => {
                      handleValidateCRA(entry.id_imputation || entry.ID_CRA);
                    });
                  } else {
                    handleValidateCRA(record.id_imputation || record.ID_CRA);
                  }
                }}
              >
                Valider tout
              </Button>
              <Popconfirm
                title="Refuser tous les CRAs de cette période ?"
                onConfirm={() => {
                  if (record.entries && record.entries.length > 0) {
                    record.entries.forEach(entry => {
                      handleRejectCRA(entry.id_imputation || entry.ID_CRA);
                    });
                  } else {
                    handleRejectCRA(record.id_imputation || record.ID_CRA);
                  }
                }}
                okText="Oui"
                cancelText="Non"
              >
                <Button size="small" danger>Refuser tout</Button>
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ];

  // Projects table columns
  const projectColumns = [
    {
      title: 'Projet',
      dataIndex: 'project_title',
      key: 'project_title',
    },
    {
      title: 'Nombre de jours',
      dataIndex: 'jours',
      key: 'jours',
      render: (val) => val || '-',
    },
    {
      title: 'Date début',
      dataIndex: 'date_debut',
      key: 'date_debut',
      render: (val) => val ? dayjs(val).format('DD/MM/YYYY') : '-',
    },
    {
      title: 'Date fin',
      dataIndex: 'date_fin',
      key: 'date_fin',
      render: (val) => val ? dayjs(val).format('DD/MM/YYYY') : '-',
    },
    {
      title: 'TJM',
      dataIndex: 'tjm',
      key: 'tjm',
      render: (val) => val ? `${val} €` : '-',
    },
    {
      title: 'Statut',
      dataIndex: 'status',
      key: 'status',
      render: (status, record) => {
        const currentStatus = status || 'En cours';
        return (
          <Select
            value={currentStatus}
            style={{ width: 120 }}
            size="small"
            onChange={(newStatus) => handleChangeProjectStatus(record, newStatus)}
          >
            <Select.Option value="En cours">
              <Tag color="blue">En cours</Tag>
            </Select.Option>
            <Select.Option value="Terminé">
              <Tag color="green">Terminé</Tag>
            </Select.Option>
            <Select.Option value="En pause">
              <Tag color="orange">En pause</Tag>
            </Select.Option>
            <Select.Option value="Annulé">
              <Tag color="red">Annulé</Tag>
            </Select.Option>
          </Select>
        );
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button 
            type="link" 
            icon={<EditOutlined />}
            onClick={() => handleEditProject(record)}
          >
            Modifier
          </Button>
        </Space>
      ),
    },
  ];

  // Filter projects based on status and date range
  const filteredProjects = projects.filter(project => {
    // Filter by status
    if (projectFilterStatus) {
      const projectStatus = project.status || 'En cours';
      if (projectStatus !== projectFilterStatus) return false;
    }
    
    // Filter by date range
    if (projectFilterDateRange && projectFilterDateRange.length === 2) {
      const [startFilter, endFilter] = projectFilterDateRange;
      const projectStart = project.date_debut ? dayjs(project.date_debut) : null;
      const projectEnd = project.date_fin ? dayjs(project.date_fin) : null;
      
      // Project should overlap with the filter range
      if (projectStart && projectEnd) {
        const filterStart = dayjs(startFilter);
        const filterEnd = dayjs(endFilter);
        // Check if project dates overlap with filter dates
        if (projectEnd.isBefore(filterStart) || projectStart.isAfter(filterEnd)) {
          return false;
        }
      }
    }
    
    return true;
  }).sort((a, b) => {
    // Sort by most recent date_debut (descending order)
    const dateA = a.date_debut ? dayjs(a.date_debut) : dayjs(0);
    const dateB = b.date_debut ? dayjs(b.date_debut) : dayjs(0);
    return dateB.valueOf() - dateA.valueOf();
  });

  const pendingCras = Array.isArray(cras) ? cras.filter(c => c.statut === CRA_STATUS.SUBMITTED) : [];
  const validatedCras = Array.isArray(cras) ? cras.filter(c => c.statut === CRA_STATUS.VALIDATED || c.statut === CRA_STATUS.ESN_VALIDATED) : [];

  // Group CRAs by consultant and period
  const groupCRAsByConsultant = (craList) => {
    const groups = {};
    
    craList.forEach(cra => {
      const consultantId = cra.id_consultan || cra.consultant?.id;
      const period = cra.période || cra.periode;
      const key = `${consultantId}_${period}`;
      
      if (!groups[key]) {
        groups[key] = {
          key,
          consultantId,
          consultant: cra.consultant || consultants.find(c => c.ID_collab === consultantId),
          period,
          entries: [],
          totalDays: 0,
          statut: cra.statut,
        };
      }
      
      groups[key].entries.push(cra);
      groups[key].totalDays += parseFloat(cra.Durée || cra.total_jours || 0);
    });
    
    return Object.values(groups);
  };

  const groupedPendingCras = groupCRAsByConsultant(pendingCras);

  console.log('🔍 CRA_STATUS.SUBMITTED:', CRA_STATUS.SUBMITTED);
  console.log('🔍 Total CRAs:', cras.length);
  if (cras.length > 0) {
    console.log('🔍 First CRA full data:', cras[0]);
    console.log('🔍 First CRA status field:', cras[0].statut);
    console.log('🔍 Status comparison:', cras[0].statut === CRA_STATUS.SUBMITTED, `"${cras[0].statut}" === "${CRA_STATUS.SUBMITTED}"`);
  }
  console.log('🔍 Pending CRAs (EVP):', pendingCras.length, pendingCras);
  console.log('🔍 Grouped Pending CRAs:', groupedPendingCras.length, groupedPendingCras);
  console.log('🔍 Validated CRAs:', validatedCras.length);

  // Create calendar view data
  const renderCalendarView = () => {
    if (!selectedPeriod) {
      return <div>Aucune période sélectionnée</div>;
    }
    
    const daysInMonth = selectedPeriod.daysInMonth();
    
    console.log('📅 Calendar View - Projects available:', projects);
    console.log('📅 Calendar View - All CRAs:', cras);
    if (cras.length > 0) {
      console.log('📅 Sample CRA:', cras[0]);
      console.log('📅 Sample CRA id_bdc:', cras[0]?.id_bdc);
      console.log('📅 Sample CRA project:', cras[0]?.project);
    }
    
    // Get all CRAs (we'll filter by type - work needs EVP, absences show always)
    const allCrasRaw = Array.isArray(cras) ? cras : [];
    
    // Helper to check if entry is an absence
    const absenceTypes = ['Congé', 'Formation', 'Maladie', 'Absence', 'CP', 'RTT', 'Autre'];
    const isAbsenceType = (cra) => {
      const typeImputation = cra.type_imputation || cra.Type_imputation || cra.typeImputation || '';
      const craType = cra.type || cra.Type || '';
      return craType.toLowerCase() === 'absence' ||
        typeImputation.toLowerCase() === 'absence' ||
        absenceTypes.includes(typeImputation) ||
        absenceTypes.map(t => t.toLowerCase()).includes(typeImputation.toLowerCase());
    };
    
    // Filter: Work entries need EVP or Validated status, Absences appear always
    const allCras = allCrasRaw.filter(cra => {
      if (isAbsenceType(cra)) {
        return true; // Show all absences regardless of status
      }
      // Show both pending (EVP) and validated entries
      return cra.statut === CRA_STATUS.SUBMITTED || 
             cra.statut === CRA_STATUS.VALIDATED || 
             cra.statut === CRA_STATUS.ESN_VALIDATED ||
             cra.statut === 'Validé' ||
             cra.statut === 'VE' ||
             cra.statut === 'VC';
    });
    
    console.log('📅 Filtered CRAs (EVP + Validated work + all absences):', allCras.length, 'out of', cras.length);
    
    const consultantGroups = {};
    allCras.forEach(cra => {
      const consultantId = cra.id_consultan || cra.consultant?.id;
      if (!consultantGroups[consultantId]) {
        consultantGroups[consultantId] = {
          consultant: cra.consultant || consultants.find(c => c.ID_collab === consultantId),
          projects: {},
          absences: []
        };
      }
      
      // Separate work entries by project and absences
      // Get all possible type fields from the CRA
      const typeImputation = cra.type_imputation || cra.Type_imputation || cra.typeImputation || '';
      const craType = cra.type || cra.Type || '';
      
      // Debug: log all fields to understand structure
      console.log('🔎 CRA raw data:', {
        type_imputation: cra.type_imputation,
        Type_imputation: cra.Type_imputation,
        type: cra.type,
        Type: cra.Type,
        statut: cra.statut,
        jour: cra.jour,
        Durée: cra.Durée
      });
      
      // Check for absence using helper function
      const isAbsenceEntry = isAbsenceType(cra);
      
      // Work entry is when type_imputation is 'Jour Travaillé' (or similar)
      const isWorkEntry = !isAbsenceEntry && (
        typeImputation === 'Jour Travaillé' || 
        typeImputation.toLowerCase() === 'jour travaillé' ||
        typeImputation.toLowerCase() === 'travail'
      );
      
      console.log(`📋 CRA entry - type_imputation: "${typeImputation}", type: "${craType}", isWork: ${isWorkEntry}, isAbsence: ${isAbsenceEntry}`);
      
      if (isAbsenceEntry) {
        // This is an absence entry
        consultantGroups[consultantId].absences.push(cra);
      } else if (isWorkEntry) {
        let projectId = cra.id_bdc || cra.project?.id || cra.project?.id_bdc || 0;
        
        console.log('🔍 CRA project lookup:', { 
          cra_id_bdc: cra.id_bdc, 
          cra_project: cra.project,
          projectId,
          availableProjects: projects.map(p => ({ id: p.id_bdc, title: p.project_title }))
        });
        
        // If no project ID, try to find a project for this consultant
        if (projectId === 0 && projects.length > 0) {
          // First try: find project specifically assigned to this consultant
          let consultantProject = projects.find(p => p.consultant_id === consultantId);
          
          // Second try: if no specific project, use the first available project from this ESN
          // (assuming consultant is working on an available project)
          if (!consultantProject) {
            consultantProject = projects[0]; // Take the first project
            console.log(`📌 No specific project for consultant ${consultantId}, using first available project ${consultantProject.id_bdc}`);
          } else {
            console.log(`📌 Found project ${consultantProject.id_bdc} for consultant ${consultantId}`);
          }
          
          if (consultantProject) {
            projectId = consultantProject.id_bdc;
          }
        }
        
        // Look up project name from projects array - handle type mismatch (string vs number)
        const project = projects.find(p => String(p.id_bdc) === String(projectId));
        const projectName = project?.project_title || 
          cra.project?.project_title || 
          cra.project?.titre || 
          cra.project_title ||
          cra.projet ||
          cra.bdc?.project_title ||
          (projectId ? `Projet #${projectId}` : 'Sans projet');
        
        console.log('🏷️ Project name resolution:', { projectId, resolved: projectName, foundProject: !!project });
        
        if (!consultantGroups[consultantId].projects[projectId]) {
          consultantGroups[consultantId].projects[projectId] = {
            id: projectId,
            name: projectName,
            entries: []
          };
        }
        consultantGroups[consultantId].projects[projectId].entries.push(cra);
      } else {
        // Unknown type - treat as work entry by default
        console.warn('⚠️ Unknown CRA type, treating as work entry:', craType, cra);
        let projectId = cra.id_bdc || cra.project?.id || cra.project?.id_bdc || 0;
        if (projectId === 0 && projects.length > 0) {
          projectId = projects[0].id_bdc;
        }
        const project = projects.find(p => String(p.id_bdc) === String(projectId));
        const projectName = project?.project_title || 
          cra.project?.project_title || 
          cra.project?.titre ||
          (projectId ? `Projet #${projectId}` : 'Sans projet');
        
        if (!consultantGroups[consultantId].projects[projectId]) {
          consultantGroups[consultantId].projects[projectId] = {
            id: projectId,
            name: projectName,
            entries: []
          };
        }
        consultantGroups[consultantId].projects[projectId].entries.push(cra);
      }
    });

    // Create table data as TREE structure - consultants as parents with children
    const tableData = [];
    Object.values(consultantGroups).forEach((group, groupIdx) => {
      const c = group.consultant;
      const consultantName = c ? `${c.prenom || c.Prenom || ''} ${c.nom || c.Nom || ''}`.trim() : 'Consultant inconnu';
      
      console.log(`👤 Consultant: ${consultantName} - Projects: ${Object.keys(group.projects).length}, Absences: ${group.absences.length}`);
      
      // Calculate consultant total
      const allEntries = [
        ...Object.values(group.projects).flatMap(p => p.entries),
        ...group.absences
      ];
      
      // Create children array for this consultant
      const children = [];
      
      // Add project rows as children
      Object.values(group.projects).forEach((project, projIdx) => {
        const row = {
          key: `consultant_${groupIdx}_project_${projIdx}`,
          consultant: group.consultant,
          consultantName: consultantName,
          projectName: project.name,
          isAbsence: false,
          isTotal: false,
          entries: project.entries
        };
        
        // Add day data
        for (let day = 1; day <= daysInMonth; day++) {
          const dayEntries = project.entries.filter(e => e.jour === day);
          row[`day_${day}`] = dayEntries;
        }
        
        children.push(row);
      });
      
      // Add absence row as child
      const absenceRow = {
        key: `consultant_${groupIdx}_absences`,
        consultant: group.consultant,
        consultantName: consultantName,
        projectName: "Pas d'activité / Absence",
        projectSubtitle: 'Congés, formations, absences',
        isAbsence: true,
        isTotal: false,
        entries: group.absences
      };
      
      // Add day data for absences
      for (let day = 1; day <= daysInMonth; day++) {
        const dayEntries = group.absences.filter(e => e.jour === day);
        absenceRow[`day_${day}`] = dayEntries;
      }
      
      children.push(absenceRow);
      console.log(`  ✅ Absence row added with ${group.absences.length} entries`);
      
      // Create consultant parent row with children
      const consultantRow = {
        key: `consultant_${groupIdx}`,
        isConsultantHeader: true,
        consultantName: consultantName,
        consultant: group.consultant,
        entries: allEntries,
        children: children
      };
      
      // Add day data for consultant total
      for (let day = 1; day <= daysInMonth; day++) {
        const dayEntries = allEntries.filter(e => e.jour === day);
        consultantRow[`day_${day}`] = dayEntries;
      }
      
      tableData.push(consultantRow);
    });

    // Calculate totals for summary - use ALL CRAs, not just pending ones
    // Convert days to hours (1 day = 8 hours)
    const totalHours = allCras.reduce((sum, cra) => sum + (parseFloat(cra.Durée || 0) * 8), 0);
    const workDaysInMonth = Array.from({ length: daysInMonth }, (_, i) => {
      const date = selectedPeriod.date(i + 1);
      const dayOfWeek = date.day();
      return dayOfWeek !== 0 && dayOfWeek !== 6 ? 1 : 0;
    }).reduce((sum, d) => sum + d, 0);

    // Create columns
    const calendarColumns = [
      {
        title: 'Consultant / Projet',
        key: 'project',
        fixed: 'left',
        width: 250,
        render: (_, record) => {
          if (record.isConsultantHeader) {
            // Calculate total for consultant
            let total = 0;
            for (let day = 1; day <= daysInMonth; day++) {
              const dayEntries = record[`day_${day}`] || [];
              total += dayEntries.reduce((sum, e) => sum + (parseFloat(e.Durée || 0) * 8), 0);
            }
            const displayTotal = total > 0 ? (total % 1 === 0 ? `${Math.floor(total)}h` : `${total.toFixed(1)}h`) : '0h';
            
            return (
              <div style={{ 
                fontWeight: 'bold', 
                fontSize: '14px', 
                color: '#1890ff',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <span>{record.consultantName}</span>
                <span style={{ 
                  backgroundColor: '#1890ff', 
                  color: '#fff', 
                  padding: '2px 8px', 
                  borderRadius: '4px',
                  fontSize: '12px'
                }}>
                  {displayTotal}
                </span>
              </div>
            );
          }
          if (record.isAbsence) {
            return (
              <div>
                <span style={{ color: '#fa8c16', fontWeight: '500' }}>
                  {record.projectName}
                </span>
              </div>
            );
          }
          return (
            <div>
              <span style={{ color: '#000' }}>
                {record.projectName}
              </span>
            </div>
          );
        }
      },
      {
        title: 'Total',
        key: 'total',
        fixed: 'left',
        width: 70,
        className: 'total-column',
        render: (_, record) => {
          // Hide for consultant header (shown in first column)
          if (record.isConsultantHeader) {
            return null;
          }
          
          // Calculate total duration for this row - convert days to hours (1 day = 8 hours)
          let total = 0;
          for (let day = 1; day <= daysInMonth; day++) {
            const dayEntries = record[`day_${day}`] || [];
            total += dayEntries.reduce((sum, e) => sum + (parseFloat(e.Durée || 0) * 8), 0);
          }
          
          // Display in hours only
          let displayValue = '-';
          if (total > 0) {
            displayValue = total % 1 === 0 ? `${Math.floor(total)}h` : `${total.toFixed(1)}h`;
          }
          
          return (
            <span style={{ fontWeight: record.isTotal ? 'bold' : 'normal' }}>
              {displayValue}
            </span>
          );
        }
      },
      {
        title: 'Actions',
        key: 'actions',
        fixed: 'left',
        width: 100,
        render: (_, record) => {
          // Don't show actions for header rows
          if (record.isConsultantHeader) {
            return null;
          }
          
          // Check if any entries have EVP status (pending validation)
          const pendingEntries = (record.entries || []).filter(
            entry => entry.statut === CRA_STATUS.SUBMITTED
          );
          
          if (pendingEntries.length === 0) {
            return <Text type="secondary" style={{ fontSize: '11px' }}>-</Text>;
          }
          
          return (
            <Button 
              type="primary" 
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => {
                pendingEntries.forEach(entry => {
                  handleValidateCRA(entry.id_imputation || entry.ID_CRA);
                });
              }}
            >
              Valider
            </Button>
          );
        }
      }
    ];

    // Add day columns
    for (let day = 1; day <= daysInMonth; day++) {
      const date = selectedPeriod.date(day);
      const dayOfWeek = date.day();
      const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
      
      calendarColumns.push({
        title: (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontWeight: 'bold' }}>{day}</div>
            <div style={{ fontSize: '10px', color: isWeekend ? '#999' : '#666' }}>
              {date.format('ddd')}
            </div>
          </div>
        ),
        dataIndex: `day_${day}`,
        key: `day_${day}`,
        width: 55,
        align: 'center',
        className: isWeekend ? 'weekend-cell' : '',
        render: (dayEntries, record) => {
          // For header or TOTAL row, don't show individual day values
          if (record.isConsultantHeader || record.isTotal) {
            return null;
          }
          
          if (!dayEntries || dayEntries.length === 0) {
            return <span style={{ color: isWeekend ? '#bbb' : '#ddd' }}>-</span>;
          }
          
          // Convert days to hours (1 day = 8 hours)
          const totalDuration = dayEntries.reduce((sum, e) => sum + (parseFloat(e.Durée || 0) * 8), 0);
          
          // For regular rows (projects and absences), show colored badges
          // Check if this is an absence entry - flexible matching
          const absenceTypes = ['Congé', 'Formation', 'Maladie', 'Absence', 'CP', 'RTT', 'Autre'];
          const hasAbsence = dayEntries.some(e => {
            const typeImputation = e.type_imputation || e.Type_imputation || e.typeImputation || '';
            const type = e.type || e.Type || '';
            return type.toLowerCase() === 'absence' || 
              typeImputation.toLowerCase() === 'absence' ||
              absenceTypes.includes(typeImputation) ||
              absenceTypes.map(t => t.toLowerCase()).includes(typeImputation.toLowerCase());
          });
          
          // Check if all entries are validated
          const allValidated = dayEntries.every(e => 
            e.statut === CRA_STATUS.VALIDATED || 
            e.statut === CRA_STATUS.ESN_VALIDATED ||
            e.statut === 'Validé' ||
            e.statut === 'VE' ||
            e.statut === 'VC'
          );
          
          // Check if any entry is pending (EVP)
          const hasPending = dayEntries.some(e => e.statut === CRA_STATUS.SUBMITTED);
          
          // Determine background color based on status and type
          let bgColor = '#52c41a'; // Default: green for work
          if (hasAbsence) {
            bgColor = allValidated ? '#87d068' : '#fa8c16'; // Lighter orange if validated, orange if pending
          } else if (allValidated) {
            bgColor = '#87d068'; // Light green for validated work
          } else if (hasPending) {
            bgColor = '#1890ff'; // Blue for pending validation
          }
          
          // Display in hours only
          const displayValue = totalDuration % 1 === 0 ? `${Math.floor(totalDuration)}h` : `${totalDuration.toFixed(1)}h`;
          
          // Build tooltip with status
          const statusLabel = allValidated ? '✓ Validé' : (hasPending ? '⏳ En attente' : '');
          
          return (
            <div
              style={{
                cursor: 'pointer',
                backgroundColor: bgColor,
                color: '#fff',
                padding: '4px 2px',
                borderRadius: '4px',
                fontWeight: 'bold',
                fontSize: '11px'
              }}
              title={`${statusLabel}\n${dayEntries.map(e => `${e.type_imputation || e.type}: ${(parseFloat(e.Durée || 0) * 8).toFixed(1)}h`).join('\n')}`}
            >
              {displayValue}
            </div>
          );
        }
      });
    }



    return (
      <>
        {/* Summary Alert */}
        <div style={{ marginBottom: 16 }}>
          <div style={{
            padding: '12px 16px',
            backgroundColor: '#e6f7ff',
            border: '1px solid #91d5ff',
            borderRadius: '8px'
          }}>
            <Space split={<span style={{ color: '#d9d9d9' }}>|</span>}>
              <span><strong>Période:</strong> {selectedPeriod.format('MMMM YYYY')}</span>
              <span><strong>Heures travaillées:</strong> {totalHours % 1 === 0 ? Math.floor(totalHours) : totalHours.toFixed(1)}h</span>
              <span><strong>Jours ouvrés:</strong> {workDaysInMonth}</span>
            </Space>
          </div>
        </div>

        {/* Legend */}
        <div style={{ marginBottom: 16, padding: '8px 16px', background: '#fafafa', borderRadius: 8 }}>
          <Space size="large" wrap>
            <span><span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#1890ff', borderRadius: 4, marginRight: 8 }}></span>En attente</span>
            <span><span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#87d068', borderRadius: 4, marginRight: 8 }}></span>Validé</span>
            <span><span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#fa8c16', borderRadius: 4, marginRight: 8 }}></span>Absence</span>
            <span><span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#f5f5f5', border: '1px solid #d9d9d9', borderRadius: 4, marginRight: 8 }}></span>Week-end</span>
          </Space>
        </div>

        <Table
          columns={calendarColumns}
          dataSource={tableData}
          rowKey="key"
          loading={loading}
          pagination={false}
          scroll={{ x: 'max-content' }}
          size="small"
          bordered
          expandable={{
            defaultExpandAllRows: true,
            indentSize: 20,
          }}
          rowClassName={(record) => {
            if (record.isConsultantHeader) return 'consultant-header-row';
            if (record.isAbsence) return 'absence-row';
            return 'project-row';
          }}
        />
        <style jsx="true">{`
          .weekend-cell {
            background-color: #f5f5f5 !important;
          }
          .consultant-header-row {
            background-color: #e6f7ff !important;
          }
          .consultant-header-row > td:first-child {
            font-weight: bold;
          }
          .absence-row {
            background-color: #fff7e6 !important;
          }
          .project-row {
            background-color: #fff !important;
          }
          .total-column {
            background-color: #fafafa !important;
            border-right: 2px solid #d9d9d9 !important;
          }
          .ant-table-row-expand-icon {
            color: #1890ff !important;
          }
        `}</style>
      </>
    );
  };

  const tabItems = [
    {
      key: 'consultants',
      label: (
        <span>
          <UserOutlined /> Consultants ({consultants.length})
        </span>
      ),
      children: (
        <Card>
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
            <Title level={5} style={{ margin: 0 }}>Liste des Consultants</Title>
            <Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAddConsultant}>
                Ajouter un consultant
              </Button>
            </Space>
          </div>
          <Table
            columns={consultantColumns}
            dataSource={consultants.filter(c => c.email !== 'placeholder@project.esn')}
            rowKey="ID_collab"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
    {
      key: 'cras',
      label: (
        <span>
          <FileTextOutlined /> CRA à valider ({pendingCras.length})
        </span>
      ),
      children: (
        <Card>
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={5} style={{ margin: 0 }}>CRA en attente de validation</Title>
            <Space>
              <DatePicker
                picker="month"
                value={selectedPeriod}
                onChange={setSelectedPeriod}
                format="MM/YYYY"
              />
              <Button 
                icon={<ReloadOutlined />} 
                onClick={loadData}
                loading={loading}
              >
                Actualiser
              </Button>
            </Space>
          </div>
          <Tabs
            items={[
              {
                key: 'calendar',
                label: 'Vue Calendrier',
                children: renderCalendarView(),
              },
            ]}
          />
        </Card>
      ),
    },
    {
      key: 'projects',
      label: (
        <span>
          <ProjectOutlined /> Projets ({projects.length})
        </span>
      ),
      children: (
        <Card>
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={5} style={{ margin: 0 }}>Liste des Projets</Title>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateProject}>
              Créer un projet
            </Button>
          </div>
          
          {/* Filters */}
          <div style={{ marginBottom: 16, padding: '12px 16px', background: '#fafafa', borderRadius: 8 }}>
            <Space wrap>
              <span style={{ fontWeight: 500 }}>Filtres:</span>
              <Select
                placeholder="Statut"
                allowClear
                style={{ width: 150 }}
                value={projectFilterStatus}
                onChange={setProjectFilterStatus}
              >
                <Select.Option value="En cours">En cours</Select.Option>
                <Select.Option value="Terminé">Terminé</Select.Option>
                <Select.Option value="En pause">En pause</Select.Option>
                <Select.Option value="Annulé">Annulé</Select.Option>
              </Select>
              <DatePicker.RangePicker
                placeholder={['Date début', 'Date fin']}
                format="DD/MM/YYYY"
                value={projectFilterDateRange}
                onChange={setProjectFilterDateRange}
                style={{ width: 280 }}
              />
              {(projectFilterStatus || projectFilterDateRange) && (
                <Button 
                  type="link" 
                  onClick={() => {
                    setProjectFilterStatus(null);
                    setProjectFilterDateRange(null);
                  }}
                >
                  Réinitialiser
                </Button>
              )}
              <span style={{ color: '#888', marginLeft: 8 }}>
                {filteredProjects.length} projet(s) affiché(s)
              </span>
            </Space>
          </div>
          
          <Table
            columns={projectColumns}
            dataSource={filteredProjects}
            rowKey="id_bdc"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
    {
      key: 'consultant-assignment',
      label: (
        <span>
          <UserOutlined /> Gestion des consultants
        </span>
      ),
      children: (
        <Card>
          <Title level={5} style={{ marginBottom: 16 }}>Assigner des consultants aux projets</Title>
          
          <Table
            columns={[
              {
                title: 'Projet',
                dataIndex: 'project_title',
                key: 'project_title',
              },
              {
                title: 'Nombre de jours',
                dataIndex: 'jours',
                key: 'jours',
                render: (jours) => jours || '-',
              },
              {
                title: 'Période',
                key: 'period',
                render: (_, record) => (
                  <span>
                    {record.date_debut && dayjs(record.date_debut).format('DD/MM/YYYY')} - 
                    {record.date_fin && dayjs(record.date_fin).format('DD/MM/YYYY')}
                  </span>
                ),
              },
              {
                title: 'Actions',
                key: 'actions',
                align: 'center',
                render: (_, record) => (
                  <Space>
                    <Button
                      type="default"
                      size="small"
                      icon={<UserOutlined />}
                      onClick={async () => {
                        setSelectedProjectForConsultant(record);
                        setLoadingConsultants(true);
                        setIsViewOnlyMode(true);
                        const result = await getProjectConsultants(record.id_bdc);
                        if (result.success) {
                          setProjectConsultants(result.data || []);
                        } else {
                          message.error('Erreur lors du chargement des consultants');
                          setProjectConsultants([]);
                        }
                        setLoadingConsultants(false);
                        setConsultantModalVisible(true);
                      }}
                    >
                      Voir
                    </Button>
                    <Button
                      type="primary"
                      size="small"
                      icon={<PlusOutlined />}
                      onClick={async () => {
                        setSelectedProjectForConsultant(record);
                        setLoadingConsultants(true);
                        setIsViewOnlyMode(false);
                        const result = await getProjectConsultants(record.id_bdc);
                        if (result.success) {
                          setProjectConsultants(result.data || []);
                        } else {
                          message.error('Erreur lors du chargement des consultants');
                          setProjectConsultants([]);
                        }
                        setLoadingConsultants(false);
                        consultantAssignForm.resetFields();
                        setConsultantModalVisible(true);
                      }}
                    >
                      Affecter
                    </Button>
                  </Space>
                ),
              },
            ]}
            dataSource={projects}
            rowKey="id_bdc"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={styles.header}>
        <div style={styles.headerContent}>
          <Title level={4} style={styles.headerTitle}>
            MCI Mini - ESN
          </Title>
          <Space>
            <Text style={{ color: '#fff' }}>{userName}</Text>
            <Button 
              type="text" 
              icon={<LogoutOutlined />} 
              onClick={logout}
              style={{ color: '#fff' }}
            >
              Déconnexion
            </Button>
          </Space>
        </div>
      </Header>

      <Content style={styles.content}>
        {/* Main Tabs */}
        <Tabs items={tabItems} defaultActiveKey="consultants" />
      </Content>

      {/* Add/Edit Consultant Modal */}
      <Modal
        title={editingConsultant ? 'Modifier le consultant' : 'Ajouter un consultant'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingConsultant(null);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmitConsultant}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="Prenom"
                label="Prénom"
                rules={[{ required: true, message: 'Prénom requis' }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="Nom"
                label="Nom"
                rules={[{ required: true, message: 'Nom requis' }]}
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: 'Email requis' },
              { type: 'email', message: 'Email invalide' },
            ]}
          >
            <Input />
          </Form.Item>

          {!editingConsultant && (
            <Form.Item
              name="password"
              label="Mot de passe"
              rules={[{ required: true, message: 'Mot de passe requis' }]}
            >
              <Input.Password />
            </Form.Item>
          )}

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="Poste" label="Poste">
                <Select placeholder="Sélectionner un poste">
                  <Select.Option value="Développeur">Développeur</Select.Option>
                  <Select.Option value="Chef de projet">Chef de projet</Select.Option>
                  <Select.Option value="Consultant">Consultant</Select.Option>
                  <Select.Option value="Architecte">Architecte</Select.Option>
                  <Select.Option value="Tech Lead">Tech Lead</Select.Option>
                  <Select.Option value="DevOps">DevOps</Select.Option>
                  <Select.Option value="Autre">Autre</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="Date_naissance" label="Date de naissance">
                <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" picker="date" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="LinkedIN" label="LinkedIn">
            <Input placeholder="https://linkedin.com/in/..." />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => {
                setModalVisible(false);
                setEditingConsultant(null);
                form.resetFields();
              }}>Annuler</Button>
              <Button type="primary" htmlType="submit">
                {editingConsultant ? 'Mettre à jour' : 'Créer'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Project Creation Modal */}
      <Modal
        title="Créer un nouveau projet"
        open={projectModalVisible}
        onCancel={() => setProjectModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form
          form={projectForm}
          layout="vertical"
          onFinish={handleSubmitProject}
        >
          <Form.Item
            name="project_title"
            label="Titre du projet"
            rules={[{ required: true, message: 'Titre du projet requis' }]}
          >
            <Input placeholder="Développement application mobile..." />
          </Form.Item>

          <Form.Item
            name="description"
            label="Description"
          >
            <Input.TextArea rows={3} placeholder="Description détaillée du projet..." />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="tjm"
                label="TJM (€)"
                rules={[{ required: true, message: 'TJM requis' }]}
              >
                <InputNumber
                  min={0}
                  style={{ width: '100%' }}
                  placeholder="500"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="jours"
                label="Nombre de jours"
                rules={[{ required: true, message: 'Nombre de jours requis' }]}
              >
                <InputNumber
                  min={1}
                  style={{ width: '100%' }}
                  placeholder="20"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="Montant total (€)"
              >
                <Form.Item noStyle shouldUpdate={(prev, curr) => prev.tjm !== curr.tjm || prev.jours !== curr.jours}>
                  {({ getFieldValue }) => {
                    const tjm = getFieldValue('tjm') || 0;
                    const jours = getFieldValue('jours') || 0;
                    const total = tjm * jours;
                    return (
                      <InputNumber
                        value={total}
                        disabled
                        style={{ width: '100%' }}
                        formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')}
                      />
                    );
                  }}
                </Form.Item>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="date_debut"
                label="Date de début"
                rules={[{ required: true, message: 'Date de début requise' }]}
              >
                <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="date_fin"
                label="Date de fin"
                rules={[{ required: true, message: 'Date de fin requise' }]}
              >
                <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setProjectModalVisible(false)}>Annuler</Button>
              <Button type="primary" htmlType="submit">
                Créer le projet
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Project Modal - Project Information Only */}
      <Modal
        title="Modifier le projet"
        open={editProjectModalVisible}
        onCancel={() => {
          setEditProjectModalVisible(false);
          setEditingProject(null);
          editProjectForm.resetFields();
        }}
        footer={null}
        width={800}
      >
        <Form
          form={editProjectForm}
          layout="vertical"
          onFinish={handleSubmitEditProject}
        >
          <Form.Item
            name="project_title"
            label="Titre du projet"
            rules={[{ required: true, message: 'Titre du projet requis' }]}
          >
            <Input placeholder="Développement application mobile..." />
          </Form.Item>

          <Form.Item
            name="description"
            label="Description"
          >
            <Input.TextArea rows={3} placeholder="Description détaillée du projet..." />
          </Form.Item>

          <Form.Item
            name="status"
            label="Statut du projet"
            rules={[{ required: true, message: 'Statut requis' }]}
          >
            <Select placeholder="Sélectionner un statut">
              <Select.Option value="En cours">En cours</Select.Option>
              <Select.Option value="Terminé">Terminé</Select.Option>
              <Select.Option value="En pause">En pause</Select.Option>
              <Select.Option value="Annulé">Annulé</Select.Option>
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="tjm"
                label="TJM (€)"
                rules={[{ required: true, message: 'TJM requis' }]}
              >
                <InputNumber
                  min={0}
                  style={{ width: '100%' }}
                  placeholder="500"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="jours"
                label="Nombre de jours"
                rules={[{ required: true, message: 'Nombre de jours requis' }]}
              >
                <InputNumber
                  min={1}
                  style={{ width: '100%' }}
                  placeholder="20"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="Montant total (€)"
              >
                <Form.Item noStyle shouldUpdate={(prev, curr) => prev.tjm !== curr.tjm || prev.jours !== curr.jours}>
                  {({ getFieldValue }) => {
                    const tjm = getFieldValue('tjm') || 0;
                    const jours = getFieldValue('jours') || 0;
                    const total = tjm * jours;
                    return (
                      <InputNumber
                        value={total}
                        disabled
                        style={{ width: '100%' }}
                        formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')}
                      />
                    );
                  }}
                </Form.Item>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="date_debut"
                label="Date de début"
                rules={[{ required: true, message: 'Date de début requise' }]}
              >
                <DatePicker 
                  style={{ width: '100%' }} 
                  format="DD/MM/YYYY"
                  picker="date"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="date_fin"
                label="Date de fin"
                rules={[{ required: true, message: 'Date de fin requise' }]}
              >
                <DatePicker 
                  style={{ width: '100%' }} 
                  format="DD/MM/YYYY"
                  picker="date"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => {
                setEditProjectModalVisible(false);
                setEditingProject(null);
                editProjectForm.resetFields();
              }}>
                Annuler
              </Button>
              <Button type="primary" htmlType="submit">
                Mettre à jour
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Consultant Assignment Modal */}
      <Modal
        title={selectedProjectForConsultant ? `Gestion des consultants - ${selectedProjectForConsultant.project_title}` : 'Gestion des consultants'}
        open={consultantModalVisible}
        onCancel={() => {
          setConsultantModalVisible(false);
          setSelectedProjectForConsultant(null);
          setProjectConsultants([]);
          setIsViewOnlyMode(false);
          consultantAssignForm.resetFields();
        }}
        footer={null}
        width={700}
      >
        {/* List of assigned consultants */}
        <div style={{ marginBottom: 24 }}>
          <Title level={5}>Consultants assignés ({projectConsultants.filter(pc => !pc.email?.includes('placeholder')).length})</Title>
          {loadingConsultants ? (
            <Text>Chargement...</Text>
          ) : projectConsultants.filter(pc => !pc.email?.includes('placeholder')).length === 0 ? (
            <Text type="secondary">Aucun consultant assigné</Text>
          ) : (
            <Space direction="vertical" style={{ width: '100%' }}>
              {projectConsultants
                .filter(pc => !pc.email?.includes('placeholder'))
                .map((pc) => (
                <Card
                  key={pc.id_consultant}
                  size="small"
                  style={{ background: '#fafafa' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <Text strong>{pc.prenom} {pc.nom}</Text>
                      {pc.is_primary && (
                        <Tag color="blue" style={{ marginLeft: 8 }}>Principal</Tag>
                      )}
                      <br />
                      <Text type="secondary">{pc.email}</Text>
                    </div>
                    {!pc.is_primary && (
                      <Popconfirm
                        title="Retirer ce consultant?"
                        description="Êtes-vous sûr de vouloir retirer ce consultant du projet?"
                        onConfirm={async () => {
                          const result = await removeConsultantFromProject(
                            selectedProjectForConsultant.id_bdc,
                            esnId,
                            pc.id_consultant
                          );
                          if (result.success) {
                            message.success('Consultant retiré avec succès');
                            // Reload consultants
                            const refreshResult = await getProjectConsultants(selectedProjectForConsultant.id_bdc);
                            if (refreshResult.success) {
                              setProjectConsultants(refreshResult.data || []);
                            }
                            loadData(); // Reload projects
                          } else {
                            message.error(result.error || 'Erreur lors du retrait du consultant');
                          }
                        }}
                        okText="Oui"
                        cancelText="Non"
                      >
                        <Button 
                          type="text" 
                          danger
                          icon={<DeleteOutlined />}
                        >
                          Retirer
                        </Button>
                      </Popconfirm>
                    )}
                  </div>
                </Card>
              ))}
            </Space>
          )}
        </div>

        {/* Add consultant form - only show in add mode */}
        {!isViewOnlyMode && (
        <div>
          <Title level={5}>Affecter des consultants</Title>
          <Form
            form={consultantAssignForm}
            layout="vertical"
            onFinish={async (values) => {
              const consultantIds = values.consultant_ids || [];
              
              if (consultantIds.length === 0) {
                message.warning('Veuillez sélectionner au moins un consultant');
                return;
              }

              let successCount = 0;
              let errorCount = 0;

              // Add each consultant
              for (const consultantId of consultantIds) {
                const result = await addConsultantToProject(
                  selectedProjectForConsultant.id_bdc,
                  esnId,
                  consultantId
                );

                if (result.success) {
                  successCount++;
                } else {
                  errorCount++;
                }
              }

              // Show results
              if (successCount > 0) {
                message.success(`${successCount} consultant(s) ajouté(s) avec succès`);
              }
              if (errorCount > 0) {
                message.warning(`${errorCount} consultant(s) n'ont pas pu être ajoutés (peut-être déjà assignés)`);
              }

              consultantAssignForm.resetFields();
              // Reload consultants
              const refreshResult = await getProjectConsultants(selectedProjectForConsultant.id_bdc);
              if (refreshResult.success) {
                setProjectConsultants(refreshResult.data || []);
              }
              loadData(); // Reload projects
            }}
          >
            <Form.Item
              name="consultant_ids"
              label="Sélectionner des consultants"
              rules={[{ required: true, message: 'Veuillez sélectionner au moins un consultant' }]}
            >
              <Select
                mode="multiple"
                placeholder="Sélectionner un ou plusieurs consultants"
                showSearch
                optionFilterProp="children"
                filterOption={(input, option) =>
                  option.children.toLowerCase().includes(input.toLowerCase())
                }
                maxTagCount="responsive"
              >
                {consultants
                  .filter(c => !projectConsultants.some(pc => pc.id_consultant === c.ID_collab))
                  .map(c => (
                    <Select.Option key={c.ID_collab} value={c.ID_collab}>
                      {c.Prenom || c.prenom} {c.Nom || c.nom} - {c.email}
                    </Select.Option>
                  ))}
              </Select>
            </Form.Item>
            <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
              <Space>
                <Button onClick={() => {
                  setConsultantModalVisible(false);
                  setSelectedProjectForConsultant(null);
                  setProjectConsultants([]);
                  consultantAssignForm.resetFields();
                }}>
                  Fermer
                </Button>
                <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>
                  Affecter
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </div>
        )}
      </Modal>

      {/* Consultant Activity Modal */}
      <Modal
        title={
          selectedConsultantForActivity ? (
            <Space>
              <UserOutlined />
              <span>
                Activité de {selectedConsultantForActivity.Prenom} {selectedConsultantForActivity.Nom}
              </span>
            </Space>
          ) : 'Activité du consultant'
        }
        open={consultantActivityModalVisible}
        onCancel={() => {
          setConsultantActivityModalVisible(false);
          setSelectedConsultantForActivity(null);
          setConsultantProjects([]);
          setConsultantCras([]);
        }}
        footer={null}
        width={900}
      >
        {consultantActivityLoading ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Text>Chargement...</Text>
          </div>
        ) : (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            {/* Statistics Summary */}
            <Card size="small">
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic
                    title="Projets actifs"
                    value={consultantProjects.length}
                    prefix={<ProjectOutlined />}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="CRAs soumis"
                    value={consultantCras.filter(c => 
                      ['EVP', 'Envoyé', 'Validé', 'VE', 'VC'].includes(c.statut)
                    ).length}
                    prefix={<FileTextOutlined />}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="Total heures"
                    value={consultantCras
                      .filter(cra => ['EVP', 'Validé', 'VE', 'VC'].includes(cra.statut))
                      .reduce((sum, cra) => sum + (parseFloat(cra.Durée || cra.duree || cra.duration || 0) * 8), 0).toFixed(1)}
                    prefix={<CalendarOutlined />}
                    suffix="h"
                  />
                </Col>
              </Row>
            </Card>

            {/* Projects Section */}
            <div>
              <Title level={5}>
                <ProjectOutlined /> Projets assignés ({consultantProjects.length})
              </Title>
              {consultantProjects.length === 0 ? (
                <Text type="secondary">Aucun projet assigné</Text>
              ) : (
                <Table
                  dataSource={consultantProjects}
                  rowKey="id_bdc"
                  pagination={false}
                  size="small"
                  columns={[
                    {
                      title: 'Projet',
                      dataIndex: 'project_title',
                      key: 'project_title',
                    },
                   
                    {
                      title: 'Nombre de jours',
                      dataIndex: 'jours',
                      key: 'jours',
                      render: (jours) => jours || '-',
                    },
                    {
                      title: 'Jours consommés',
                      key: 'jours_consommes',
                      render: (_, record, index) => {
                        // Calculate consumed days from CRAs for this project
                        // Filter work CRAs (not absences) that are validated or pending
                        const absenceTypes = ['Congé', 'Formation', 'Maladie', 'Absence', 'CP', 'RTT', 'Autre', 'absence'];
                        const projectTitle = record.project_title || record.titre || '';
                        
                        const projectCras = consultantCras.filter(cra => {
                          const isValidOrPending = ['EVP', 'Validé', 'VE', 'VC'].includes(cra.statut);
                          if (!isValidOrPending) return false;
                          
                          // Check if it's an absence - don't count absences
                          const craType = (cra.type || '').toLowerCase();
                          const typeImputation = cra.type_imputation || cra.Type_imputation || '';
                          if (craType === 'absence' || absenceTypes.includes(typeImputation)) {
                            return false;
                          }
                          
                          // Check if CRA is linked to this specific project by ID
                          const projectId = cra.id_bdc || cra.project?.id || cra.projet_id;
                          if (projectId && String(projectId) === String(record.id_bdc)) {
                            return true;
                          }
                          
                          // Check by project name/title
                          const craProjectName = cra.project?.titre || cra.project?.project_title || cra.projet_titre || cra.project_title || '';
                          if (craProjectName && projectTitle && craProjectName.toLowerCase() === projectTitle.toLowerCase()) {
                            return true;
                          }
                          
                          // If CRA has no project info at all, attribute to the first project in the list
                          // This matches the display logic in the activity table
                          if (!projectId && !craProjectName && index === 0) {
                            return true;
                          }
                          
                          return false;
                        });
                        
                        const totalDays = projectCras.reduce((sum, cra) => {
                          return sum + parseFloat(cra.Durée || cra.duree || cra.duration || 0);
                        }, 0);
                        
                        // Get allocated days from record (jours field)
                        const allocatedDays = parseFloat(record.jours || 0);
                        
                        // Calculate percentage
                        const percentage = allocatedDays > 0 ? (totalDays / allocatedDays) * 100 : 0;
                        
                        // Determine color based on percentage
                        let color = '#d9d9d9'; // default gray
                        if (percentage >= 100) {
                          color = '#52c41a'; // green - fully consumed or exceeded
                        } else if (percentage >= 75) {
                          color = '#1890ff'; // blue - mostly consumed
                        } else if (percentage >= 50) {
                          color = '#faad14'; // orange - half consumed
                        }
                        
                        return (
                          <Tooltip title={`${totalDays.toFixed(1)} / ${allocatedDays} jours`}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <Progress 
                                percent={Math.min(percentage, 100)} 
                                strokeColor={color}
                                size="small"
                                style={{ width: '50px', minWidth: '50px' }}
                                strokeWidth={6}
                                showInfo={false}
                              />
                              <span style={{ color, fontWeight: '500' }}>
                                {percentage.toFixed(0)}%
                              </span>
                            </div>
                          </Tooltip>
                        );
                      },
                    },
                    {
                      title: 'Période',
                      key: 'period',
                      render: (_, record) => (
                        <span>
                          {record.date_debut && dayjs(record.date_debut).format('DD/MM/YYYY')} - 
                          {record.date_fin && dayjs(record.date_fin).format('DD/MM/YYYY')}
                        </span>
                      ),
                    },
                  ]}
                />
              )}
            </div>

            {/* CRA Statistics
            <div>
              <Title level={5}>
                <BarChartOutlined /> Statistiques CRA
              </Title>
              <Card size="small">
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <div>
                      <Text strong>En validation : </Text>
                      <Tag color="orange">
                        {consultantCras.filter(c => c.statut === 'EVP' || c.statut === 'Envoyé').length}
                      </Tag>
                    </div>
                  </Col>
                  <Col span={12}>
                    <div>
                      <Text strong>Validés : </Text>
                      <Tag color="green">
                        {consultantCras.filter(c => c.statut === 'Validé' || c.statut === 'VE' || c.statut === 'VC').length}
                      </Tag>
                    </div>
                  </Col>
                  <Col span={12}>
                    <div>
                      <Text strong>Brouillon : </Text>
                      <Tag color="default">
                        {consultantCras.filter(c => c.statut === 'brouillon' || c.statut === 'Brouillon').length}
                      </Tag>
                    </div>
                  </Col>
                  <Col span={12}>
                    <div>
                      <Text strong>Total entrées : </Text>
                      <Tag color="blue">{consultantCras.length}</Tag>
                    </div>
                  </Col>
                </Row>
              </Card>
            </div> */}

            {/* Recent CRA Activity */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <Title level={5} style={{ margin: 0 }}>
                  <CalendarOutlined /> Activité récente (période actuelle)
                </Title>
                <Space>
                  {/* <Select
                    placeholder="Projet"
                    allowClear
                    style={{ width: 180 }}
                    value={activityFilterProject}
                    onChange={setActivityFilterProject}
                  >
                    <Select.Option value="0">Sans projet</Select.Option>
                    {consultantProjects.map(p => (
                      <Select.Option key={p.id_bdc} value={String(p.id_bdc)}>
                        {p.project_title || p.titre}
                      </Select.Option>
                    ))}
                  </Select> */}
                  <Select
                    placeholder="Statut"
                    allowClear
                    style={{ width: 120 }}
                    value={activityFilterStatus}
                    onChange={setActivityFilterStatus}
                  >
                    <Select.Option value="EVP">EVP</Select.Option>
                    <Select.Option value="Validé">Validé</Select.Option>
                  </Select>
                  <Select
                    placeholder="Type"
                    allowClear
                    style={{ width: 120 }}
                    value={activityFilterType}
                    onChange={setActivityFilterType}
                  >
                    <Select.Option value="travail">Travail</Select.Option>
                    <Select.Option value="absence">Absence</Select.Option>
                  </Select>
                </Space>
              </div>
              {consultantCras.filter(c => {
                const period = c.période || c.periode;
                const isValidOrPending = ['EVP', 'Validé', 'VE', 'VC'].includes(c.statut);
                if (!(period === selectedPeriod.format('MM_YYYY') && isValidOrPending)) return false;
                
                // Apply project filter
                if (activityFilterProject) {
                  const projectId = c.id_bdc || c.project?.id;
                  if (String(projectId) !== String(activityFilterProject)) return false;
                }
                
                // Apply status filter
                if (activityFilterStatus && c.statut !== activityFilterStatus) return false;
                
                // Apply type filter
                if (activityFilterType) {
                  const recordType = (c.type || '').toLowerCase();
                  if (recordType !== activityFilterType) return false;
                }
                
                return true;
              }).length === 0 ? (
                <Text type="secondary">Aucune activité pour cette période</Text>
              ) : (
                <Table
                  dataSource={consultantCras.filter(c => {
                    const period = c.période || c.periode;
                    const isValidOrPending = ['EVP', 'Validé', 'VE', 'VC'].includes(c.statut);
                    if (!(period === selectedPeriod.format('MM_YYYY') && isValidOrPending)) return false;
                    
                    // Apply project filter
                    if (activityFilterProject) {
                      const projectId = c.id_bdc || c.project?.id;
                      if (String(projectId) !== String(activityFilterProject)) return false;
                    }
                    
                    // Apply status filter
                    if (activityFilterStatus && c.statut !== activityFilterStatus) return false;
                    
                    // Apply type filter
                    if (activityFilterType) {
                      const recordType = (c.type || '').toLowerCase();
                      if (recordType !== activityFilterType) return false;
                    }
                    
                    return true;
                  }).slice(0, 10)}
                  rowKey="id_cra"
                  pagination={false}
                  size="small"
                  columns={[
                    {
                      title: 'Date',
                      key: 'date',
                      render: (_, record) => {
                        const period = record.période || record.periode;
                        if (!period) return '-';
                        const [month, year] = period.split('_');
                        const day = record.jour || record.day || 1;
                        return `${day}/${month}/${year}`;
                      },
                    },
                    {
                      title: 'Projet',
                      key: 'project',
                      render: (_, record) => {
                        // Check if it's an absence type first
                        const recordType = record.type || '';
                        const typeImputation = record.type_imputation || record.Type_imputation || '';
                        const absenceTypes = ['Congé', 'Formation', 'Maladie', 'Absence', 'CP', 'RTT', 'Autre', 'absence'];
                        if (recordType.toLowerCase() === 'absence' || absenceTypes.includes(typeImputation)) {
                          return 'Absence';
                        }
                        
                        // If project object has titre (from API)
                        if (record.project?.titre) {
                          return record.project.titre;
                        }
                        
                        // If project object has project_title
                        if (record.project?.project_title) {
                          return record.project.project_title;
                        }
                        
                        // Get project ID and find in projects list
                        const projectId = record.id_bdc || record.project?.id;
                        if (projectId && projectId > 0) {
                          const project = projects.find(p => String(p.id_bdc) === String(projectId));
                          if (project) return project.project_title;
                        }
                        
                        // Fallback: if no project on CRA but consultant has assigned projects, show first one
                        if (consultantProjects.length > 0) {
                          return consultantProjects[0].project_title || consultantProjects[0].titre || 'Projet assigné';
                        }
                        
                        // If no project assigned at all
                        return 'Sans projet';
                      },
                    },
                    {
                      title: 'Type',
                      dataIndex: 'type_imputation',
                      key: 'type_imputation',
                      render: (type) => {
                        const isAbsence = ['CP', 'RTT', 'Maladie', 'Formation', 'Autre'].includes(type);
                        return (
                          <Tag color={isAbsence ? 'orange' : 'blue'}>
                            {type || 'Travail'}
                          </Tag>
                        );
                      },
                    },
                    {
                      title: 'Durée',
                      key: 'duree',
                      render: (_, record) => {
                        const duree = parseFloat(record.Durée || record.duree || record.duration || 0);
                        // Convert days to hours (1 day = 8 hours)
                        const hours = duree * 8;
                        return hours > 0 ? `${hours % 1 === 0 ? Math.floor(hours) : hours.toFixed(1)}h` : '0h';
                      },
                    },
                    {
                      title: 'Statut',
                      dataIndex: 'statut',
                      key: 'statut',
                      render: (statut) => {
                        let color = 'default';
                        if (['Validé', 'VE', 'VC'].includes(statut)) color = 'green';
                        else if (['EVP', 'Envoyé'].includes(statut)) color = 'orange';
                        else if (statut === 'Refusé') color = 'red';
                        return <Tag color={color}>{statut}</Tag>;
                      },
                    },
                  ]}
                />
              )}
            </div>
          </Space>
        )}
      </Modal>
    </Layout>
  );
};

const styles = {
  header: {
    background: '#001529',
    padding: '0 24px',
    display: 'flex',
    alignItems: 'center',
  },
  headerContent: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
  },
  headerTitle: {
    color: '#fff',
    margin: 0,
  },
  content: {
    padding: 24,
    background: '#f0f2f5',
  },
};

export default ESNDashboard;
