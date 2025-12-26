
DROP TABLE IF EXISTS `admin`;
CREATE TABLE IF NOT EXISTS `admin` (
  `ID_Admin` int NOT NULL AUTO_INCREMENT,
  `Mail` varchar(191) COLLATE utf8mb4_general_ci NOT NULL,
  `mdp` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`ID_Admin`),
  UNIQUE KEY `Mail` (`Mail`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `admin`
--

INSERT INTO `admin` (`ID_Admin`, `Mail`, `mdp`) VALUES
(1, 'admin@example.com', '0a3dbb07cffe7b84adbff2b66c1208ad09099e4f');

-- --------------------------------------------------------

--
-- Structure de la table `appeloffre`
--

DROP TABLE IF EXISTS `appeloffre`;
CREATE TABLE IF NOT EXISTS `appeloffre` (
  `id` int NOT NULL,
  `client_id` int NOT NULL,
  `titre` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `description` text COLLATE utf8mb4_general_ci,
  `profil` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `tjm_min` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `tjm_max` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `date_publication` date DEFAULT NULL,
  `date_limite` date DEFAULT NULL,
  `date_debut` date DEFAULT NULL,
  `statut` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `client_id` (`client_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `appeloffre`
--

INSERT INTO `appeloffre` (`id`, `client_id`, `titre`, `description`, `profil`, `tjm_min`, `tjm_max`, `date_publication`, `date_limite`, `date_debut`, `statut`) VALUES
(1, 1, 'testtt', 'testtt', 'testtt', '100', '1000', '2024-11-08', '2018-11-13', '2024-11-08', '1');

-- --------------------------------------------------------

--
-- Structure de la table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
CREATE TABLE IF NOT EXISTS `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
CREATE TABLE IF NOT EXISTS `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissions_group_id_b120cbf9` (`group_id`),
  KEY `auth_group_permissions_permission_id_84c5c92e` (`permission_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
CREATE TABLE IF NOT EXISTS `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  KEY `auth_permission_content_type_id_2f476e4b` (`content_type_id`)
) ENGINE=MyISAM AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `auth_permission`
--

INSERT INTO `auth_permission` (`id`, `name`, `content_type_id`, `codename`) VALUES
(1, 'Can add log entry', 1, 'add_logentry'),
(2, 'Can change log entry', 1, 'change_logentry'),
(3, 'Can delete log entry', 1, 'delete_logentry'),
(4, 'Can view log entry', 1, 'view_logentry'),
(5, 'Can add permission', 2, 'add_permission'),
(6, 'Can change permission', 2, 'change_permission'),
(7, 'Can delete permission', 2, 'delete_permission'),
(8, 'Can view permission', 2, 'view_permission'),
(9, 'Can add group', 3, 'add_group'),
(10, 'Can change group', 3, 'change_group'),
(11, 'Can delete group', 3, 'delete_group'),
(12, 'Can view group', 3, 'view_group'),
(13, 'Can add user', 4, 'add_user'),
(14, 'Can change user', 4, 'change_user'),
(15, 'Can delete user', 4, 'delete_user'),
(16, 'Can view user', 4, 'view_user'),
(17, 'Can add content type', 5, 'add_contenttype'),
(18, 'Can change content type', 5, 'change_contenttype'),
(19, 'Can delete content type', 5, 'delete_contenttype'),
(20, 'Can view content type', 5, 'view_contenttype'),
(21, 'Can add session', 6, 'add_session'),
(22, 'Can change session', 6, 'change_session'),
(23, 'Can delete session', 6, 'delete_session'),
(24, 'Can view session', 6, 'view_session');

-- --------------------------------------------------------

--
-- Structure de la table `auth_user`
--

DROP TABLE IF EXISTS `auth_user`;
CREATE TABLE IF NOT EXISTS `auth_user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `password` varchar(128) COLLATE utf8mb4_general_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `first_name` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `last_name` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `email` varchar(254) COLLATE utf8mb4_general_ci NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `auth_user_groups`
--

DROP TABLE IF EXISTS `auth_user_groups`;
CREATE TABLE IF NOT EXISTS `auth_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_user_id_6a12ed8b` (`user_id`),
  KEY `auth_user_groups_group_id_97559544` (`group_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `auth_user_user_permissions`
--

DROP TABLE IF EXISTS `auth_user_user_permissions`;
CREATE TABLE IF NOT EXISTS `auth_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permissions_user_id_a95ead1b` (`user_id`),
  KEY `auth_user_user_permissions_permission_id_1fbb5f2c` (`permission_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `bondecommande`
--

DROP TABLE IF EXISTS `bondecommande`;
CREATE TABLE IF NOT EXISTS `bondecommande` (
  `id_bdc` int NOT NULL AUTO_INCREMENT,
  `candidature_id` int NOT NULL,
  `numero_bdc` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `date_creation` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `montant_total` float NOT NULL,
  `statut` varchar(20) COLLATE utf8mb4_general_ci DEFAULT 'En attente',
  `description` text COLLATE utf8mb4_general_ci,
  PRIMARY KEY (`id_bdc`),
  UNIQUE KEY `numero_bdc` (`numero_bdc`),
  KEY `candidature_id` (`candidature_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `candidature`
--

DROP TABLE IF EXISTS `candidature`;
CREATE TABLE IF NOT EXISTS `candidature` (
  `id_cd` int NOT NULL AUTO_INCREMENT,
  `AO_id` int NOT NULL,
  `esn_id` int NOT NULL,
  `responsable_compte` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `id_consultant` int DEFAULT NULL,
  `date_candidature` date NOT NULL,
  `statut` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `tjm` decimal(10,2) NOT NULL,
  `date_disponibilite` date NOT NULL,
  `commentaire` text COLLATE utf8mb4_general_ci,
  PRIMARY KEY (`id_cd`),
  KEY `AO_id` (`AO_id`),
  KEY `esn_id` (`esn_id`),
  KEY `id_consultant` (`id_consultant`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `candidature`
--

INSERT INTO `candidature` (`id_cd`, `AO_id`, `esn_id`, `responsable_compte`, `id_consultant`, `date_candidature`, `statut`, `tjm`, `date_disponibilite`, `commentaire`) VALUES
(1, 1, 1, 'Jean Dupont', 1, '2024-11-10', 'En cours', 450.00, '2024-11-20', 'Expérience solide dans des projets similaires.');

-- --------------------------------------------------------

--
-- Structure de la table `client`
--

CREATE TABLE IF NOT EXISTS `client` (
  `ID_clt` int NOT NULL AUTO_INCREMENT,
  `Raison_sociale` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `SIRET` varchar(14) COLLATE utf8mb4_unicode_ci NOT NULL,
  `RCE` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Pays` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `Adresse` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CP` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `Ville` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `Province` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mail_Contact` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `Password` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `Tel_Contact` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Statut` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Date_validation` date DEFAULT NULL,
  `N_TVA` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `IBAN` varchar(34) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `BIC` varchar(11) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Banque` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`ID_clt`),
  UNIQUE KEY `SIRET` (`SIRET`),
  UNIQUE KEY `mail_Contact` (`mail_Contact`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC;

--
-- Déchargement des données de la table `client`
--

INSERT INTO `client` (`ID_clt`, `Raison_sociale`, `SIRET`, `RCE`, `Pays`, `Adresse`, `CP`, `Ville`, `Province`, `mail_Contact`, `Password`, `Tel_Contact`, `Statut`, `Date_validation`, `N_TVA`, `IBAN`, `BIC`, `Banque`) VALUES
(1, 'Entreprise XYZ', '12345678901234', 'RC123456', 'France', '123 Rue Exemple', '75001', 'Paris', 'Île-de-France', 'contact@xyz.com', '797350adcb79e42b6795c62fc5fefaba80e7d418', '0123456789', 'Validé', '2024-10-29', 'FR123456789', 'FR7630006000011234567890189', 'AGRIFRPP', 'Crédit Agricole');

-- --------------------------------------------------------

--
-- Structure de la table `collaboration`
--

DROP TABLE IF EXISTS `collaboration`;
CREATE TABLE IF NOT EXISTS `collaboration` (
  `ID_collab` int NOT NULL AUTO_INCREMENT,
  `ID_ESN` int NOT NULL,
  `Admin` tinyint(1) DEFAULT '0',
  `Commercial` tinyint(1) DEFAULT '0',
  `Consultant` tinyint(1) DEFAULT '0',
  `Actif` tinyint(1) DEFAULT '1',
  `Nom` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `Prenom` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `Date_naissance` date DEFAULT NULL,
  `Poste` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `date_dé` date DEFAULT NULL,
  `date_debut_activ` date DEFAULT NULL,
  `CV` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `LinkedIN` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `Mobilité` enum('National','International','Autres') COLLATE utf8mb4_general_ci DEFAULT 'National',
  `Disponibilité` date DEFAULT NULL,
  PRIMARY KEY (`ID_collab`),
  KEY `ID_ESN` (`ID_ESN`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `collaboration`
--

INSERT INTO `collaboration` (`ID_collab`, `ID_ESN`, `Admin`, `Commercial`, `Consultant`, `Actif`, `Nom`, `Prenom`, `Date_naissance`, `Poste`, `date_dé`, `date_debut_activ`, `CV`, `LinkedIN`, `Mobilité`, `Disponibilité`) VALUES
(1, 1, 0, 1, 0, 1, 'Dupont', 'Jean', '1990-05-14', 'Commercial', NULL, '2023-01-01', 'https://example.com/cv.pdf', 'https://www.linkedin.com/in/jeandupont', 'National', '2023-12-31');

-- --------------------------------------------------------

--
-- Structure de la table `contrat`
--

DROP TABLE IF EXISTS `contrat`;
CREATE TABLE IF NOT EXISTS `contrat` (
  `id_contrat` int NOT NULL AUTO_INCREMENT,
  `candidature_id` int NOT NULL,
  `numero_contrat` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `date_signature` date NOT NULL,
  `date_debut` date NOT NULL,
  `date_fin` date DEFAULT NULL,
  `montant` float NOT NULL,
  `statut` varchar(20) COLLATE utf8mb4_general_ci DEFAULT 'En cours',
  `conditions` text COLLATE utf8mb4_general_ci,
  PRIMARY KEY (`id_contrat`),
  UNIQUE KEY `numero_contrat` (`numero_contrat`),
  KEY `candidature_id` (`candidature_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
CREATE TABLE IF NOT EXISTS `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext COLLATE utf8mb4_general_ci,
  `object_repr` varchar(200) COLLATE utf8mb4_general_ci NOT NULL,
  `action_flag` smallint UNSIGNED NOT NULL,
  `change_message` longtext COLLATE utf8mb4_general_ci NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6` (`user_id`)
) ;

-- --------------------------------------------------------

--
-- Structure de la table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
CREATE TABLE IF NOT EXISTS `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `model` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=MyISAM AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `django_content_type`
--

INSERT INTO `django_content_type` (`id`, `app_label`, `model`) VALUES
(1, 'admin', 'logentry'),
(2, 'auth', 'permission'),
(3, 'auth', 'group'),
(4, 'auth', 'user'),
(5, 'contenttypes', 'contenttype'),
(6, 'sessions', 'session');

-- --------------------------------------------------------

--
-- Structure de la table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
CREATE TABLE IF NOT EXISTS `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `django_migrations`
--

INSERT INTO `django_migrations` (`id`, `app`, `name`, `applied`) VALUES
(1, 'contenttypes', '0001_initial', '2024-10-29 11:58:52.657911'),
(2, 'auth', '0001_initial', '2024-10-29 11:58:53.052350'),
(3, 'admin', '0001_initial', '2024-10-29 11:58:53.186128'),
(4, 'admin', '0002_logentry_remove_auto_add', '2024-10-29 11:58:53.190608'),
(5, 'admin', '0003_logentry_add_action_flag_choices', '2024-10-29 11:58:53.194608'),
(6, 'contenttypes', '0002_remove_content_type_name', '2024-10-29 11:58:53.244841'),
(7, 'auth', '0002_alter_permission_name_max_length', '2024-10-29 11:58:53.268136'),
(8, 'auth', '0003_alter_user_email_max_length', '2024-10-29 11:58:53.296248'),
(9, 'auth', '0004_alter_user_username_opts', '2024-10-29 11:58:53.301050'),
(10, 'auth', '0005_alter_user_last_login_null', '2024-10-29 11:58:53.326658'),
(11, 'auth', '0006_require_contenttypes_0002', '2024-10-29 11:58:53.328170'),
(12, 'auth', '0007_alter_validators_add_error_messages', '2024-10-29 11:58:53.333300'),
(13, 'auth', '0008_alter_user_username_max_length', '2024-10-29 11:58:53.356428'),
(14, 'auth', '0009_alter_user_last_name_max_length', '2024-10-29 11:58:53.380229'),
(15, 'auth', '0010_alter_group_name_max_length', '2024-10-29 11:58:53.404570'),
(16, 'auth', '0011_update_proxy_permissions', '2024-10-29 11:58:53.410229'),
(17, 'auth', '0012_alter_user_first_name_max_length', '2024-10-29 11:58:53.434243'),
(18, 'sessions', '0001_initial', '2024-10-29 11:58:53.464270');

-- --------------------------------------------------------

--
-- Structure de la table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
CREATE TABLE IF NOT EXISTS `django_session` (
  `session_key` varchar(40) COLLATE utf8mb4_general_ci NOT NULL,
  `session_data` longtext COLLATE utf8mb4_general_ci NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `doc_clt`
--

DROP TABLE IF EXISTS `doc_clt`;
CREATE TABLE IF NOT EXISTS `doc_clt` (
  `ID_DOC_CLT` int NOT NULL AUTO_INCREMENT,
  `ID_CLT` int NOT NULL,
  `Doc_URL` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `Titre` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `Date_Valid` date DEFAULT NULL,
  `Statut` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Description` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`ID_DOC_CLT`),
  KEY `ID_CLT` (`ID_CLT`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Déchargement des données de la table `doc_clt`
--

INSERT INTO `doc_clt` (`ID_DOC_CLT`, `ID_CLT`, `Doc_URL`, `Titre`, `Date_Valid`, `Statut`, `Description`) VALUES
(1, 1, 'https://example.com/document.pdf', 'Contrat de Partenariat', '2024-12-01', 'Validé', 'Document de partenariat signé avec le client.');

-- --------------------------------------------------------

--
-- Structure de la table `doc_esn`
--

DROP TABLE IF EXISTS `doc_esn`;
CREATE TABLE IF NOT EXISTS `doc_esn` (
  `ID_DOC_ESN` int NOT NULL AUTO_INCREMENT,
  `ID_ESN` int NOT NULL,
  `Doc_URL` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `Titre` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `Date_Valid` date DEFAULT NULL,
  `Statut` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `Description` text COLLATE utf8mb4_general_ci,
  PRIMARY KEY (`ID_DOC_ESN`),
  KEY `ID_ESN` (`ID_ESN`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `doc_esn`
--

INSERT INTO `doc_esn` (`ID_DOC_ESN`, `ID_ESN`, `Doc_URL`, `Titre`, `Date_Valid`, `Statut`, `Description`) VALUES
(1, 1, 'https://example.com/document.pdf', 'Contrat de Partenariat', '2024-12-01', 'Validé', 'Document de partenariat signé avec l\'ESN.');

-- --------------------------------------------------------

--
-- Structure de la table `esn`
--

DROP TABLE IF EXISTS `esn`;
CREATE TABLE IF NOT EXISTS `esn` (
  `ID_ESN` int NOT NULL AUTO_INCREMENT,
  `Raison_sociale` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `SIRET` varchar(14) COLLATE utf8mb4_general_ci NOT NULL,
  `RCE` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `Pays` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `Adresse` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `CP` varchar(10) COLLATE utf8mb4_general_ci NOT NULL,
  `Ville` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `Province` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `mail_Contact` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `Password` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `Tel_Contact` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `Statut` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `Date_validation` date DEFAULT NULL,
  `N_TVA` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `IBAN` varchar(34) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `BIC` varchar(11) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `Banque` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`ID_ESN`),
  UNIQUE KEY `SIRET` (`SIRET`),
  UNIQUE KEY `mail_Contact` (`mail_Contact`(191))
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `esn`
--

INSERT INTO `esn` (`ID_ESN`, `Raison_sociale`, `SIRET`, `RCE`, `Pays`, `Adresse`, `CP`, `Ville`, `Province`, `mail_Contact`, `Password`, `Tel_Contact`, `Statut`, `Date_validation`, `N_TVA`, `IBAN`, `BIC`, `Banque`) VALUES
(1, 'Tech Solutions', '12345678901234', 'RC123456', 'France', '10 Rue de l\'Innovation', '75001', 'Paris', 'Île-de-France', 'contact@techsolutions.com', '0a3dbb07cffe7b84adbff2b66c1208ad09099e4f', '0123456789', 'Validé', '2024-10-30', 'FR123456789', 'FR7630006000011234567890189', 'AGRIFRPP', 'Crédit Agricole');

-- --------------------------------------------------------

--
-- Structure de la table `notifications`
--

DROP TABLE IF EXISTS `notifications`;
CREATE TABLE IF NOT EXISTS `notifications` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `message` text COLLATE utf8mb4_general_ci NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_general_ci DEFAULT 'Unread',
  `categorie` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `partenariat`
--

DROP TABLE IF EXISTS `partenariat`;
CREATE TABLE IF NOT EXISTS `partenariat` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ID_client` int NOT NULL,
  `ID_ESN` int NOT NULL,
  `Statut` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `Description` text COLLATE utf8mb4_general_ci,
  `Categorie` enum('Diamond','Golden','Silver') COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ID_ESN` (`ID_ESN`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Contraintes pour les tables déchargées
--

--
-- Contraintes pour la table `doc_clt`
--
ALTER TABLE `doc_clt`
  ADD CONSTRAINT `doc_clt_ibfk_1` FOREIGN KEY (`ID_CLT`) REFERENCES `client` (`ID_clt`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
