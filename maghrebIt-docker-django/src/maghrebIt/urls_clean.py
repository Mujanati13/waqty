from maghrebIt import views
from django.urls import path, re_path



urlpatterns = [
    # Gestion des clients
    path('client/', views.client_view),
    # Route pour gérer les clients (opérations globales comme GET tous les clients ou POST pour ajouter un client).
    re_path(r'^client/([0-9]+)$', views.client_view),
    # Route pour gérer un client spécifique par son ID (opérations GET, PUT, DELETE).

    # Gestion des documents des clients
    path('documentClient/', views.Document_view),
    # Route pour gérer les documents des clients (exemple : ajout d'un document).
    re_path(r'^documentClient/([0-9]+)$', views.Document_view),
    # Route pour gérer un document client spécifique par son ID.

    # Gestion des entreprises ESN (Entreprises de Services Numériques)
    path('ESN/', views.esn_view),
    # Route pour gérer les ESN (opérations globales comme GET tous les ESN ou POST pour ajouter une ESN).
    re_path(r'^ESN/([0-9]+)$', views.esn_view),
    # Route pour gérer une ESN spécifique par son ID.
    path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/create/', views.create_admin_account, name='create_admin_account'),

    # Gestion des documents des ESN
    path('docEsn/', views.docEsn_view),
    # Route pour gérer les documents associés aux ESN.
    re_path(r'^docEsn/([0-9]+)$', views.docEsn_view),
    # Route pour gérer un document ESN spécifique par son ID.

    # Gestion des administrateurs
    path('admin/', views.admin_view),
    # Route pour gérer les administrateurs (exemple : ajout ou récupération de tous les administrateurs).
    re_path(r'^admin/([0-9]+)$', views.admin_view),
    # Route pour gérer un administrateur spécifique par son ID.

    # Authentification
    path('login/', views.login),
    # Route pour authentifier un administrateur.
    re_path(r'^login/([0-9]+)$', views.login),
    # Authentification par ID (non standard, à adapter si nécessaire).
    path('login_esn/', views.login_esn),
    # Route pour authentifier une ESN.
    re_path(r'^login_esn/([0-9]+)$', views.login_esn),
    # Authentification ESN avec paramètre (non standard).
    path('login_client/', views.login_client),
    # Route pour authentifier un client.
    re_path(r'^login_client/([0-9]+)$', views.login_client),
    # Authentification client avec paramètre (non standard).

    # Gestion des collaborateurs
    path('collaborateur/', views.collaborateur_view),
    # Route pour gérer les collaborateurs associés aux ESN.
    re_path(r'^collaborateur/([0-9]+)$', views.collaborateur_view),
    # Route pour gérer un collaborateur spécifique par son ID.

    # Gestion des appels d'offres
    path('appelOffre/', views.appelOffre_view),
    # Route pour gérer les appels d'offres (exemple : ajout d'un nouvel appel d'offres).
    re_path(r'^appelOffre/([0-9]+)$', views.appelOffre_view),
    # Route pour gérer un appel d'offres spécifique par son ID.

    # Gestion des candidatures
    path('candidature/', views.candidature_view),
    # Route pour gérer les candidatures des ESN aux appels d'offres.
    re_path(r'^candidature/([0-9]+)$', views.candidature_view),
    # Route pour gérer une candidature spécifique par son ID.

    # Gestion des bons de commande
    path('bondecommande/', views.bondecommande_view),
    # Route pour gérer les bons de commande associés aux candidatures validées.
    re_path(r'^bondecommande/([0-9]+)$', views.bondecommande_view),
    # Route pour gérer un bon de commande spécifique par son ID.

    # Gestion des factures
    path('facture/', views.facture_view),
    # Route pour gérer les factures générées.
    re_path(r'^facture/([0-9]+)$', views.facture_view),
    # Route pour gérer une facture spécifique par son ID.

    # Gestion des contrats
    path('contrat/', views.contrat_view),
    # Route pour gérer les contrats entre clients et ESN.
    re_path(r'^contrat/([0-9]+)$', views.contrat_view),
    # Route pour gérer un contrat spécifique par son ID.

    # Gestion des CRA (Comptes Rendus d'Activité)
    path('cra/', views.cra_view),
    # Route pour gérer les CRA soumis par les collaborateurs.
    re_path(r'^cra/([0-9]+)$', views.cra_view),
    # Route pour gérer un CRA spécifique par son ID.

    # Gestion des notifications
    path('notification/', views.notification_view),
    # Route pour gérer les notifications du système.
    re_path(r'^notification/([0-9]+)$', views.notification_view),
    # Route pour gérer une notification spécifique par son ID.

    # Gestion des partenariats
    path('partenariat/', views.partenariat_view),
    # Route pour gérer les partenariats.
    re_path(r'^partenariat/([0-9]+)$', views.partenariat_view),
    # Route pour gérer un partenariat spécifique par son ID.

    # Gestion des avantages des partenariats
    path('avantagePartenariat/', views.avantagePartenariat_view),
    # Route pour gérer les avantages associés aux partenariats.
    re_path(r'^avantagePartenariat/([0-9]+)$', views.avantagePartenariat_view),
    # Route pour gérer un avantage de partenariat spécifique par son ID.

    # Gestion des virements
    path('virement/', views.virement_view),
    # Route pour gérer les virements financiers.
    re_path(r'^virement/([0-9]+)$', views.virement_view),
    # Route pour gérer un virement spécifique par son ID.

    # Gestion des documents
    path('save_doc/', views.save_doc, name='save_doc'),
    # Route pour sauvegarder un document (téléchargement de fichier).

    # Récupération des fichiers
    path('file_view/', views.file_view, name='file_view'),
    # Route pour visualiser ou télécharger un fichier.

    # Gestion des statuts de candidatures
    path('update_candidature_status/', views.update_candidature_status, name='update_candidature_status'),
    # Route pour mettre à jour le statut d'une candidature.

    # Notifications spécialisées
    path('notify_appel_offre/', views.notify_appel_offre, name='notify_appel_offre'),
    # Route pour envoyer des notifications liées aux appels d'offres.

    # Gestion des candidatures avec état
    path('candidature_state/', views.candidature_state, name='candidature_state'),
    # Route pour gérer l'état des candidatures.

    # Notifications de candidatures
    path('send_candidature_notification/', views.send_candidature_notification, name='send_candidature_notification'),
    # Route pour envoyer des notifications relatives aux candidatures.

    # Validation des BDC par administrateur
    path('admin_validate_bdc/', views.admin_validate_bdc, name='admin_validate_bdc'),
    # Route pour valider un bon de commande par un administrateur.

    # Gestion des notifications aux ESN
    path('notify_esn_bdc/', views.notify_esn_bdc, name='notify_esn_bdc'),
    # Route pour notifier les ESN concernant les bons de commande.

    # Notifications de rejet de BDC
    path('notify_bdc_rejection/', views.notify_bdc_rejection, name='notify_bdc_rejection'),
    # Route pour notifier le rejet d'un bon de commande.

    # Fonctionnalités avancées de gestion des CRA
    path('cra_management/', views.cra_management, name='cra_management'),
    # Route pour des fonctionnalités de gestion avancée des CRA.

    # Authentification et token management
    path('refresh_token/', views.refresh_token, name='refresh_token'),
    # Route pour renouveler les tokens d'authentification.

    # Gestion des sessions collaborateurs
    path('collaborateur_session/', views.collaborateur_session, name='collaborateur_session'),
    # Route pour gérer les sessions des collaborateurs.

    # Validation et workflows administratifs
    path('admin_workflow/', views.admin_workflow, name='admin_workflow'),
    # Route pour les workflows administratifs.

    # Fonctionnalités d'export et reporting
    path('export_data/', views.export_data, name='export_data'),
    # Route pour exporter des données.

    # Gestion des emails et notifications
    path('email_management/', views.email_management, name='email_management'),
    # Route pour gérer l'envoi d'emails.

    # Synchronisation des données
    path('data_sync/', views.data_sync, name='data_sync'),
    # Route pour synchroniser les données.

    # Tableau de bord et analytics
    path('dashboard_analytics/', views.dashboard_analytics, name='dashboard_analytics'),
    # Route pour les analytics du tableau de bord.

    # Gestion des permissions et accès
    path('permission_management/', views.permission_management, name='permission_management'),
    # Route pour gérer les permissions d'accès.

    # Configuration système
    path('system_config/', views.system_config, name='system_config'),
    # Route pour la configuration du système.

    # Audit et logs
    path('audit_logs/', views.audit_logs, name='audit_logs'),
    # Route pour consulter les logs d'audit.

    # Backup et restauration
    path('backup_restore/', views.backup_restore, name='backup_restore'),
    # Route pour les opérations de sauvegarde et restauration.

    # Intégrations externes
    path('external_integrations/', views.external_integrations, name='external_integrations'),
    # Route pour les intégrations avec des services externes.

    # Maintenance système
    path('system_maintenance/', views.system_maintenance, name='system_maintenance'),
    # Route pour les opérations de maintenance système.

    # Advanced CRA workflow
    path('admin-cra-workflow/', views.admin_cra_workflow, name='admin_cra_workflow'),
    
    # New notification endpoints
    path('notify-new-client-registration/', views.notify_new_client_registration, name='notify_new_client_registration'),
    path('notify-client-contract-signature/', views.notify_client_contract_signature, name='notify_client_contract_signature'),
    
    # Reminder notification endpoints
    path('send-client-reminder/', views.send_client_reminder, name='send_client_reminder'),
    path('send-esn-reminder/', views.send_esn_reminder, name='send_esn_reminder'),

]
