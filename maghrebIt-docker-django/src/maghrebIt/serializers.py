from rest_framework import serializers
from .models import *

# serializer Client
class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model= Client
        fields = (  'ID_clt', 
            'raison_sociale', 
            'siret', 
            'img_path', 
            'rce', 
            'pays', 
            'adresse', 
            'cp', 
            'ville', 
            'province', 
            'mail_contact', 
            'password', 
            'tel_contact', 
            'statut', 
            'date_validation', 
            'n_tva', 
            'iban', 
            'bic', 
            'banque',
            'responsible',
            'linkedin',
            'twitter'
            ) 
        
# serializer doc_clt
class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doc_clt
        fields = [
            'ID_DOC_CLT',
            'ID_CLT',
            'Doc_URL',
            'Titre',
            'Date_Valid',
            'Statut',
            'Description'
        ]
        

# serializer ENS
class ESNSerializer(serializers.ModelSerializer):
    class Meta:
        model = ESN
        fields = [
            'ID_ESN', 
            'Raison_sociale', 
            'SIRET', 
            'RCE', 
            'Pays', 
            'Adresse', 
            'CP', 
            'Ville', 
            'Province', 
            'mail_Contact', 
            'password', 
            'Tel_Contact', 
            'Statut', 
            'Date_validation', 
            'N_TVA', 
            'IBAN', 
            'BIC', 
            'Banque',
            'responsible'
        ]
# serializer DocumentESN      
class DocumentESNSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentESN
        fields = [
            'ID_DOC_ESN',
            'ID_ESN',
            'Doc_URL',
            'Titre',
            'Date_Valid',
            'Statut',
            'Description'
        ]
        
# serializer Collaborateur      
class CollaborateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collaborateur
        fields = [
            'ID_collab',
            'ID_ESN',
            'Admin',
            'Commercial',
            'Consultant',
            'Actif',
            'Nom',
            'Prenom',
            'Date_naissance',
            'Poste',
            'date_debut_activ',
            'date_debut_active_esn',
            'date_dé',
            'CV',
            'LinkedIN',
            'Mobilité',
            'Disponibilité',
            'email',
            'password',
        ]
        
class AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admin
        fields = ['ID_Admin', 'Mail', 'mdp']
        
class AppelOffreSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppelOffre
        fields = ['id', 'client_id', 'titre','description', 'profil', 'tjm_min','tjm_max', 'date_publication', 'date_limite','date_debut', 'statut', 'jours']
       


class CandidatureSerializer(serializers.ModelSerializer):
    commercial_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Candidature
        fields = [
            'id_cd',
            'AO_id',
            'esn_id',
            'responsable_compte',
            'id_consultant',
            'date_candidature',
            'statut',
            'tjm',
            'date_disponibilite',
            'commentaire',
            'nom_cn',
            'commercial_id',
        ]
        extra_kwargs = {
            'commercial_id': {'required': False, 'allow_null': True},
            'responsable_compte': {'required': False, 'allow_null': True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if data.get('commercial_id') is None:
            raw_value = getattr(instance, 'responsable_compte', None)
            try:
                data['commercial_id'] = int(raw_value) if raw_value not in (None, "", "null") else None
            except (TypeError, ValueError):
                data['commercial_id'] = None

        return data
       
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id',
            'dest_id',
            'user_id',
            'message',
            'status',
            'categorie',
            'created_at',
            'event',
            'event_id',
        ]
        
      
class BondecommandeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bondecommande
        fields = ['id_bdc', 'candidature_id', 'numero_bdc','date_creation', 'montant_total', 'statut', 'description' , 'has_contract' ,  'TJM' ,'date_debut' , 'date_fin' , 'jours' , 'benefit']
        
class ContratSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contrat
        fields = ['id_contrat', 'candidature_id', 'numero_contrat','date_signature', 'date_debut', 'date_fin', 'montant','statut', 'conditions' ,'esn_trace', 'client_trace']
        

class PartenariatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partenariat
        fields = ['id_part','id_client', 'id_esn', 'statut', 'description', 'categorie']
        
class Partenariat1Serializer(serializers.ModelSerializer):
    class Meta:
        model = Partenariat1
        fields = ['id_part','id_client', 'id_esn', 'statut','date_debut','date_fin' ,'description', 'categorie']


class CRA_imputationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRA_imputation
        fields = [
            'id_imputation',
            'période',
            'jour',
            'type',
            'id_consultan',
            'id_esn',
            'id_client',
            'id_bdc',
            "Durée",
            "statut",
        ]

class CRA_CONSULTANTSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRA_CONSULTANT
        fields = [
            'id_CRA',
            'id_consultan',
            'période',
            'statut',
            'id_bdc',
            'n_jour',
            'commentaire',
            'id_esn',
            "id_client",
        ]

class NDF_CONSULTANTSerializer(serializers.ModelSerializer):
    class Meta:
        model = NDF_CONSULTANT
        fields = [
            'id_ndf',
            'période',
            'jour',
            'type_frais',
            'id_consultan',
            'id_esn',
            'id_client',
            'id_bdc',
            'id_commercial',
            'description',
            'montant_ht',
            'montant_ttc',
            'devise',
            'justificatif',
            'statut'
        ]

class FactureSerializer(serializers.ModelSerializer):
    # Add read-only fields for related data
    esn_name = serializers.SerializerMethodField()
    esn_email = serializers.SerializerMethodField()
    esn_tel = serializers.SerializerMethodField()
    
    client_name = serializers.SerializerMethodField()
    client_email = serializers.SerializerMethodField()
    client_tel = serializers.SerializerMethodField()
    
    consultant_prenom = serializers.SerializerMethodField()
    consultant_nom = serializers.SerializerMethodField()
    consultant_name = serializers.SerializerMethodField()
    consultant_email = serializers.SerializerMethodField()
    
    commercial_prenom = serializers.SerializerMethodField()
    commercial_nom = serializers.SerializerMethodField()
    commercial_name = serializers.SerializerMethodField()
    commercial_email = serializers.SerializerMethodField()
    
    tjm = serializers.SerializerMethodField()
    nombre_jours = serializers.SerializerMethodField()
    date_echeance = serializers.SerializerMethodField()
    
    class Meta:
        model = Facture
        fields = [
            'id_facture',
            'id_esn', 
            'id_client',
            'bdc_id',
            'date_emission',
            'date_echeance',
            'montant_ht',
            'montant_ttc', 
            'taux_tva',
            'statut',
            'attachment',
            'type_facture',
            'periode',
            # ESN info
            'esn_name',
            'esn_email',
            'esn_tel',
            # Client info
            'client_name',
            'client_email',
            'client_tel',
            # Consultant info
            'consultant_prenom',
            'consultant_nom',
            'consultant_name',
            'consultant_email',
            # Commercial info
            'commercial_prenom',
            'commercial_nom',
            'commercial_name',
            'commercial_email',
            # Financial details
            'tjm',
            'nombre_jours',
        ]
    
    def get_esn_name(self, obj):
        try:
            esn = ESN.objects.get(ID_ESN=obj.id_esn)
            return esn.Raison_sociale
        except ESN.DoesNotExist:
            return None
    
    def get_esn_email(self, obj):
        try:
            esn = ESN.objects.get(ID_ESN=obj.id_esn)
            return esn.mail_Contact
        except ESN.DoesNotExist:
            return None
    
    def get_esn_tel(self, obj):
        try:
            esn = ESN.objects.get(ID_ESN=obj.id_esn)
            return esn.Tel_Contact
        except ESN.DoesNotExist:
            return None
    
    def get_client_name(self, obj):
        try:
            client = Client.objects.get(ID_clt=obj.id_client)
            return client.raison_sociale
        except Client.DoesNotExist:
            return None
    
    def get_client_email(self, obj):
        try:
            client = Client.objects.get(ID_clt=obj.id_client)
            return client.mail_contact
        except Client.DoesNotExist:
            return None
    
    def get_client_tel(self, obj):
        try:
            client = Client.objects.get(ID_clt=obj.id_client)
            return client.tel_contact
        except Client.DoesNotExist:
            return None
    
    def get_consultant_prenom(self, obj):
        try:
            bdc = Bondecommande.objects.get(id_bdc=obj.bdc_id)
            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
            consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
            return consultant.Prenom
        except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, Collaborateur.DoesNotExist):
            return None
    
    def get_consultant_nom(self, obj):
        try:
            bdc = Bondecommande.objects.get(id_bdc=obj.bdc_id)
            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
            consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
            return consultant.Nom
        except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, Collaborateur.DoesNotExist):
            return None
    
    def get_consultant_name(self, obj):
        try:
            bdc = Bondecommande.objects.get(id_bdc=obj.bdc_id)
            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
            consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
            return f"{consultant.Prenom} {consultant.Nom}"
        except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, Collaborateur.DoesNotExist):
            return None
    
    def get_consultant_email(self, obj):
        try:
            bdc = Bondecommande.objects.get(id_bdc=obj.bdc_id)
            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
            consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
            return consultant.email
        except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, Collaborateur.DoesNotExist):
            return None
    
    def get_commercial_prenom(self, obj):
        try:
            bdc = Bondecommande.objects.get(id_bdc=obj.bdc_id)
            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
            if candidature.commercial_id:
                commercial = Collaborateur.objects.get(ID_collab=candidature.commercial_id)
                return commercial.Prenom
        except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, Collaborateur.DoesNotExist):
            pass
        return None
    
    def get_commercial_nom(self, obj):
        try:
            bdc = Bondecommande.objects.get(id_bdc=obj.bdc_id)
            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
            if candidature.commercial_id:
                commercial = Collaborateur.objects.get(ID_collab=candidature.commercial_id)
                return commercial.Nom
        except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, Collaborateur.DoesNotExist):
            pass
        return None
    
    def get_commercial_name(self, obj):
        try:
            bdc = Bondecommande.objects.get(id_bdc=obj.bdc_id)
            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
            if candidature.commercial_id:
                commercial = Collaborateur.objects.get(ID_collab=candidature.commercial_id)
                return f"{commercial.Prenom} {commercial.Nom}"
        except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, Collaborateur.DoesNotExist):
            pass
        return None
    
    def get_commercial_email(self, obj):
        try:
            bdc = Bondecommande.objects.get(id_bdc=obj.bdc_id)
            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
            if candidature.commercial_id:
                commercial = Collaborateur.objects.get(ID_collab=candidature.commercial_id)
                return commercial.email
        except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, Collaborateur.DoesNotExist):
            pass
        return None
    
    def get_tjm(self, obj):
        try:
            bdc = Bondecommande.objects.get(id_bdc=obj.bdc_id)
            return float(bdc.TJM) if bdc.TJM else None
        except Bondecommande.DoesNotExist:
            return None
    
    def get_nombre_jours(self, obj):
        try:
            bdc = Bondecommande.objects.get(id_bdc=obj.bdc_id)
            return float(bdc.jours) if bdc.jours else None
        except Bondecommande.DoesNotExist:
            return None
    
    def get_date_echeance(self, obj):
        if obj.date_emission:
            from datetime import timedelta
            # Default 30 days payment term
            return obj.date_emission + timedelta(days=30)
        return None
