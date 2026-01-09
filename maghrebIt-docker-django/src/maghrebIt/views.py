from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404             
from .models import Candidature
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.http import FileResponse
from django.conf import settings
import hashlib
import jwt
import datetime
import json
import unicodedata

from django.core.files.storage import default_storage
import random
import string
import os
from collections import defaultdict

from django.db.models import Q

from .models import *
from .serializers import *
from rest_framework import status

from .models import Admin
from .serializers import AdminSerializer

# --- Notification feature flags -------------------------------------------------
# Centralized toggles to disable specific notification flows without removing
# the underlying business logic. Adjust these flags as needed when a workflow
# must be silenced temporarily.
ENABLE_CRA_CLIENT_VALIDATION_ESN_NOTIFICATION = False
ENABLE_NDF_CLIENT_VALIDATION_ESN_NOTIFICATION = False
ENABLE_INVOICE_CREATION_NOTIFICATIONS = False
ENABLE_BDC_CREATION_ESN_NOTIFICATION = False
ENABLE_CRA_CREATION_ESN_NOTIFICATION = False
ENABLE_AO_NOTIFICATIONS = False  # Disable Appel d'Offre notifications

import hashlib
import jwt

from django.core.mail import send_mail
from django.urls import reverse

def checkAuth(request):
    token = request.META.get('HTTP_AUTHORIZATION')
    if token == None:
        print("Non authentifié 1")
        return False
    try:
        token = token.replace('Bearer ', "")
        payload = jwt.decode(token, 'maghrebIt', algorithms=["HS256"])
        return True
    except Exception as e:
        print("Non authentifié 2")
        print(e)
        return False

@csrf_exempt
def save_doc(request):
    # Vérifie si la méthode HTTP est autorisée (seules les requêtes POST sont acceptées)
    if request.method != 'POST':
        return JsonResponse({"status": False, "msg": "Méthode non autorisée"}, status=405)
    file = request.FILES.get('uploadedFile')
    # Récupère le chemin où le fichier doit être sauvegardé, spécifié dans le corps de la requête
    path = request.POST.get('path')
    # Vérifie si le fichier est fourni dans la requête
    if not file:
        return JsonResponse({"status": False, "msg": "Aucun fichier fourni"}, status=400)
    # Vérifie si le chemin de sauvegarde est fourni
    if not path:
        return JsonResponse({"status": False, "msg": "Chemin de sauvegarde non fourni"}, status=400)

    # Récupère l'extension du fichier (par exemple, '.jpg', '.png')
    file_extension = os.path.splitext(file.name)[1]
    # Définit un ensemble de caractères pour générer des noms aléatoires
    char_set = string.ascii_uppercase + string.digits
    # Génère une chaîne aléatoire de 6 caractères pour le nom du fichier
    file_name_gen = ''.join(random.sample(char_set * 6, 6))
    # Génère une autre chaîne aléatoire pour assurer l'unicité du nom
    file_name_base = ''.join(random.sample(char_set * 6, 6))
    # Construit le nom final du fichier avec le chemin spécifié, un identifiant unique et l'extension
    file_name = f"{path}{file_name_base}-{file_name_gen}{file_extension}"

    # Tente de sauvegarder le fichier en utilisant le chemin généré
    try:
        saved_path = default_storage.save(file_name, file)
        # Renvoie une réponse JSON avec l'indication que l'opération a réussi et le chemin du fichier sauvegardé
        return JsonResponse({"status": True, "path": saved_path}, safe=False)
    except Exception as e:
        # Capture les erreurs potentielles et renvoie un message d'erreur JSON avec un statut HTTP 500
        return JsonResponse({"status": False, "msg": str(e)}, status=500)

# Login view
@csrf_exempt
def login(request):
    # Exempte cette vue de la vérification CSRF (Cross-Site Request Forgery),
    # ce qui est souvent nécessaire pour les API qui ne passent pas par un formulaire HTML classique.

    if request.method == "POST":
        # Vérifie si la méthode de la requête est POST. Si ce n'est pas le cas, aucune autre action n'est effectuée.

        data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans le corps de la requête.

        username = data["username"]
        # Récupère le champ "username" des données JSON.

        mdp = data["mdp"]
        # Récupère le champ "mdp" (mot de passe) des données JSON.

        users = Admin.objects.filter(Mail=username)
        # Requête pour rechercher un utilisateur dans le modèle `Admin` avec un email correspondant au "username".

        if users.exists():
            # Vérifie si un utilisateur avec cet email existe.

            user = users.first()
            # Récupère le premier utilisateur correspondant à la requête.

            pwd_utf = mdp.encode()
            # Encode le mot de passe fourni en UTF-8 pour la compatibilité avec le hachage.

            pwd_sh = hashlib.sha1(pwd_utf)
            # Calcule le hachage SHA-1 du mot de passe encodé.

            password_crp = pwd_sh.hexdigest()
            # Convertit le hachage en chaîne hexadécimale.
            
            if user.mdp == password_crp:
                # Compare le mot de passe haché fourni avec le mot de passe haché stocké dans la base de données.

                client_serializer = AdminSerializer(users, many=True)
                # Sérialise les données de l'utilisateur pour les inclure dans la réponse.

                payload = {
                    'id': user.ID_Admin,  # Inclut l'identifiant de l'utilisateur dans le jeton.
                    'email': user.Mail   # Inclut l'email de l'utilisateur dans le jeton.
                }
                token = jwt.encode(payload, 'maghrebIt', algorithm='HS256')
                # Génère un token JWT avec les informations utilisateur et une clé secrète ('maghrebIt').

                response = JsonResponse(
                    {"success": True, "token": token, "data": client_serializer.data}, safe=False)
                # Crée une réponse JSON contenant le token et les données utilisateur.

                response.set_cookie(key='jwt', value=token, max_age=86400)
                # Ajoute le token JWT en tant que cookie dans la réponse, avec une durée de validité de 24 heures (86 400 secondes).

                return response
                # Retourne la réponse contenant le token et les données utilisateur.

            return JsonResponse({"success": False, "msg": "Password not valid for this user"}, safe=False)
            # Retourne une erreur si le mot de passe ne correspond pas à celui stocké dans la base de données.

        else:
            return JsonResponse({"success": False, "msg": "user not found"}, safe=False)
            # Retourne une erreur si aucun utilisateur avec cet email n'a été trouvé.

@csrf_exempt
def admin_login(request):
    if request.method == "POST":
        data = JSONParser().parse(request)
        username = data["username"]
        password = data["mdp"]

        users = Admin.objects.filter(Mail=username)

        if users.exists():
            user = users.first()

            if check_password(password, user.mdp):
                client_serializer = AdminSerializer(users, many=True)
                payload = {
                    'id': user.ID_Admin,
                    'email': user.Mail,
                }
                token = jwt.encode(payload, 'maghrebIt', algorithm='HS256')

                response = JsonResponse({"success": True, "token": token, "data": client_serializer.data}, safe=False)
                response.set_cookie(key='jwt', value=token, max_age=86400)  # 24h (86,400s)

                return response
            return JsonResponse({"success": False, "msg": "Password not valid for this user"}, safe=False)
        else:
            return JsonResponse({"success": False, "msg": "user not found"}, safe=False)

@csrf_exempt
def create_admin_account(request):
    if request.method == "POST":
        data = JSONParser().parse(request)
        username = data["username"]
        mdp = data["mdp"]

        if Admin.objects.filter(Mail=username).exists():
            return JsonResponse({"success": False, "msg": "User already exists"}, safe=False)

        hashed_password = make_password(mdp)

        admin_data = {
            "Mail": username,
            "mdp": hashed_password,
            "is_staff": True
        }

        admin_serializer = AdminSerializer(data=admin_data)

        if admin_serializer.is_valid():
            admin_serializer.save()
            return JsonResponse({"success": True, "msg": "Admin account created successfully"}, safe=False)

        return JsonResponse({"success": False, "msg": "Failed to create admin account", "errors": admin_serializer.errors}, safe=False)

    return JsonResponse({"success": False, "msg": "Only POST method is allowed"}, safe=False, status=405)

@csrf_exempt
def login_client(request):
    # Fonction pour authentifier un client à partir de son email et de son mot de passe.
    if request.method == "POST":
        # Vérifie si la méthode de la requête est POST. Si ce n'est pas le cas, la requête n'est pas traitée.

        data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête POST.

        username = data["username"]
        # Récupère le champ "username" (adresse email) des données JSON envoyées.

        password = data["password"]
        # Récupère le champ "password" des données JSON envoyées.

        users = Client.objects.filter(mail_contact=username)
        # Requête pour rechercher un client dans le modèle `Client` avec un email correspondant au "username".

        if users.exists():
            # Vérifie si un client avec cet email existe.

            user = users.first()
            # Récupère le premier client correspondant à la requête.

            pwd_utf = password.encode()
            # Encode le mot de passe fourni en UTF-8 pour le préparer au hachage.

            pwd_sh = hashlib.sha1(pwd_utf)
            # Calcule le hachage SHA-1 du mot de passe encodé.

            password_crp = pwd_sh.hexdigest()
            # Convertit le hachage en chaîne hexadécimale.

            if user.password == password_crp:
                # Compare le mot de passe haché fourni avec le mot de passe haché stocké dans la base de données.

                client_serializer = ClientSerializer(users, many=True)
                # Sérialise les données du client pour les inclure dans la réponse.

                payload = {
                    'id': user.ID_clt,  # Inclut l'identifiant du client dans le token.
                    'email': user.mail_contact  # Inclut l'email du client dans le token.
                }
                token = jwt.encode(payload, 'maghrebIt', algorithm='HS256')
                # Génère un token JWT avec les informations du client et une clé secrète ('maghrebIt').

                response = JsonResponse(
                    {"success": True, "token": token, "data": client_serializer.data}, safe=False)
                # Crée une réponse JSON contenant le token et les données du client.

                response.set_cookie(key='jwt', value=token, max_age=86400)
                # Ajoute le token JWT en tant que cookie dans la réponse, avec une durée de validité de 24 heures (86 400 secondes).

                return response
                # Retourne la réponse contenant le token et les données du client.

            return JsonResponse({"success": False, "msg": "Password not valid for this user"}, safe=False)
            # Retourne une erreur si le mot de passe ne correspond pas à celui stocké dans la base de données.

        else:
            return JsonResponse({"success": False, "msg": "user not found"}, safe=False)
            # Retourne une erreur si aucun client avec cet email n'a été trouvé.

@csrf_exempt
def login_esn(request):
    if request.method == "POST":

        data = JSONParser().parse(request)
        username = data["username"]
        password = data["password"]

        users = ESN.objects.filter(mail_Contact=username)

        if users.exists():
            user = users.first()
            pwd_utf = password.encode()
            pwd_sh = hashlib.sha1(pwd_utf)
            password_crp = pwd_sh.hexdigest()
            if user.password == password_crp:
                client_serializer = ESNSerializer(users, many=True)
                payload = {
                    'id': user.ID_ESN,
                    'email': user.mail_Contact,
                   
                }
                token = jwt.encode(payload, 'maghrebIt', algorithm='HS256')

                response = JsonResponse( {"success": True,  "token": token, "data": client_serializer.data}, safe=False)

                response.set_cookie(key='jwt', value = token, max_age=86400) # 24h (86.400s)

                return response
                #return JsonResponse({"success": True, "data": client_serializer.data}, safe=False)
            return JsonResponse({"success": False, "msg": "Password not valid for this user"}, safe=False)
        else:
            return JsonResponse({"success": False, "msg": "user not found"}, safe=False)
# Create your views here.

def client_view(request, id=0):
    # Fonction pour gérer les opérations CRUD (Create, Read, Update, Delete) sur les clients.

    # if checkAuth(request) == False:
    #     # Vérifie si l'utilisateur est authentifié à l'aide de la fonction `checkAuth`.
    #     return JsonResponse({
    #         "status": False,
    #         "msg": "Non authentifié"
    #     }, safe=False, status=401)
    #     # Si l'utilisateur n'est pas authentifié, retourne une réponse JSON avec un statut HTTP 401 (Non autorisé).

    if request.method == 'GET':
        # Gère la récupération des clients (opération READ).

        clients = Client.objects.filter()
        # Récupère tous les clients dans la base de données.

        client_serializer = ClientSerializer(clients, many=True)
        # Sérialise les données des clients récupérés pour les rendre exploitables sous forme de JSON.

        data = []
        # Initialise une liste vide pour stocker les données.

        for client in client_serializer.data:
            # Parcourt les données sérialisées des clients.
            data.append(client)
            # Ajoute chaque client dans la liste `data`.

        return JsonResponse({"total": len(data), "data": data}, safe=False)
        # Retourne une réponse JSON contenant le nombre total de clients et leurs données.

    if request.method == 'POST':
        # Gère la création d'un nouveau client (opération CREATE).

        client_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête POST.

        # Hash password
        password = client_data["password"]
        # Récupère le mot de passe fourni dans les données JSON.

        pwd_utf = password.encode()
        # Encode le mot de passe en UTF-8 pour le préparer au hachage.

        pwd_sh = hashlib.sha1(pwd_utf)
        # Calcule le hachage SHA-1 du mot de passe encodé.

        password_crp = pwd_sh.hexdigest()
        # Convertit le hachage en chaîne hexadécimale.

        # updated password to hashed password
        client_data["password"] = password_crp
        # Met à jour le mot de passe dans les données du client avec le mot de passe haché.

        client_serializer = ClientSerializer(data=client_data)
        # Crée une instance de sérialiseur avec les données du client.

        if client_serializer.is_valid():
            # Vérifie si les données sérialisées sont valides.
            client = client_serializer.save()
            # Sauvegarde le nouveau client dans la base de données.
            
            # Send notification to admins about new client registration
            try:
                # Get all admin users
                admins = Admin.objects.all()
                if admins.exists():
                    notifications_sent = 0
                    
                    # Create notification message for admins
                    admin_message = (
                        f"Un nouveau client \"{client.raison_sociale}\" (Email: {client.Email_clt}) s'est inscrit sur la plateforme. "
                        f"Les documents soumis doivent être vérifiés et validés avant activation du compte. "
                        f"<a href='/interface-ad/clients/{client.ID_clt}' class='notification-link'>Vérifier les documents</a>"
                    )
                    
                    # Send notification to all admins
                    for admin in admins:
                        send_notification(
                            user_id=client.ID_clt,  # Client triggered the event
                            dest_id=admin.ID_Admin,  # Notification goes to admin
                            message=admin_message,
                            categorie="Admin",
                            event="Inscription Client",
                            event_id=client.ID_clt
                        )
                        notifications_sent += 1
                    
                    print(f"Sent {notifications_sent} notifications to admins for new client registration")
            except Exception as e:
                print(f"Error sending admin notifications for new client: {e}")
                # Don't fail the registration if notification fails

            return JsonResponse({
                "status": True,
                "msg": "Added Successfully!!e",
                "errors": client_serializer.errors
            }, safe=False, status=200)
            # Retourne une réponse JSON indiquant que le client a été ajouté avec succès.

        return JsonResponse({
            "status": False,
            "msg": "Failed to Add",
            "errors": client_serializer.errors
        }, safe=False, status=400)
        # Retourne une réponse JSON indiquant que l'ajout du client a échoué.
    if request.method == 'PUT':
    # Gère la mise à jour des informations d'un client existant (opération UPDATE).

        client_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête PUT.

        try:
            # Use ID from URL if provided, otherwise from body
            client_id = id if id != 0 else client_data.get("ID_clt")
            if not client_id:
                return JsonResponse({
                    "status": False,
                    "msg": "Client ID is required"
                }, safe=False, status=400)
                
            client = Client.objects.get(ID_clt=client_id)
            # Récupère le client à mettre à jour en fonction de l'identifiant fourni.
            
            # Store old status for comparison
            old_statut = client.statut
            
            # Préserver le mot de passe existant et s'assurer que l'ID est correct
            client_data["password"] = client.password
            client_data["ID_clt"] = client_id  # Ensure ID is set correctly
            
            client_serializer = ClientSerializer(client, data=client_data)
            # Crée une instance de sérialiseur avec les données mises à jour.

            if client_serializer.is_valid():
                # Vérifie si les données sérialisées sont valides.
                client_serializer.save()
                # Sauvegarde les modifications dans la base de données.

                # Check if client status changed to "à signer" - send contract signature notification
                new_statut = client_data.get("statut")
                if new_statut == "à signer" and old_statut != "à signer":
                    try:
                        # Create contract signature notification message for client
                        contract_link = f"/interface-cl?menu=contrats"
                        client_message = (
                            f"Félicitations ! Votre compte client a été validé par l'administrateur. "
                            f"Vous pouvez maintenant accéder à toutes les fonctionnalités de la plateforme. "
                            f"Pour finaliser votre inscription, vous devez signer le contrat cadre. "
                            f"<a href='{contract_link}' class='notification-link'>Signer le contrat maintenant</a>"
                        )
                        
                        # Send notification to client about account validation and contract signing
                        send_notification(
                            user_id=1,  # System/admin notification
                            dest_id=client.ID_clt,  # Notification goes to client
                            message=client_message,
                            categorie="Client",
                            event="Compte Validé - Contrat à Signer",
                            event_id=client.ID_clt
                        )
                        
                        print(f"DEBUG: Notification de validation et signature de contrat envoyée au client {client.ID_clt}")
                        
                    except Exception as e:
                        print(f"DEBUG: Erreur lors de l'envoi de notification de validation client: {e}")
                        # Continue anyway, don't block the update

                return JsonResponse({
                    "status": True,
                    "msg": "Updated Successfully!",
                    "errors": client_serializer.errors
                }, safe=False)
                # Retourne une réponse JSON indiquant que la mise à jour a réussi.

            return JsonResponse({
                "status": False,
                "msg": "Failed to Update",
                "errors": client_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON avec les erreurs de validation si la mise à jour échoue.
        
        except Client.DoesNotExist:
            return JsonResponse({
                "status": False,
                "msg": "Client not found",
            }, safe=False, status=404)
        except Exception as e:
            return JsonResponse({
                "status": False,
                "msg": f"Error: {str(e)}",
            }, safe=False, status=500)
    
    if request.method == 'DELETE':
        # Gère la suppression d'un client (opération DELETE).

        try:
            client = Client.objects.get(ID_clt=id)
            # Récupère le client à supprimer en fonction de l'identifiant fourni dans l'URL.

            client.delete()
            # Supprime le client de la base de données.

            return JsonResponse("Deleted Succeffuly!!", safe=False)
            # Retourne une réponse JSON indiquant que le client a été supprimé avec succès.

        except Exception as e:
            # Capture les exceptions en cas d'erreur (par exemple, si le client n'existe pas).

            return JsonResponse({
                "status": 404,
                "msg": "client n'existe pas"
            }, safe=False)
            # Retourne une réponse JSON avec un message d'erreur.

# Document view
@csrf_exempt
def Document_view(request, id=0):
    # Vue permettant de gérer les documents des clients avec des opérations CRUD (Create, Read, Update, Delete).

    # if checkAuth(request) == False:
    #     # Vérifie si l'utilisateur est authentifié en appelant la fonction `checkAuth`.
    #     return JsonResponse({
    #         "status": False,
    #         "msg": "Non authentifié"
    #     }, safe=False, status=401)
        # Si l'utilisateur n'est pas authentifié, retourne une réponse JSON avec un statut 401 (Non autorisé).

    if request.method == 'GET':
        # Gère la récupération de tous les documents ou d'un document spécifique.

        docs = Doc_clt.objects.filter()
        # Récupère tous les documents clients dans la base de données.

        doc_serializer = DocumentSerializer(docs, many=True)
        # Sérialise les documents récupérés pour les convertir en JSON.

        data = []
        # Initialise une liste pour stocker les données enrichies des documents.

        for doc in doc_serializer.data:
            # Parcourt chaque document sérialisé.

            client = Client.objects.get(ID_clt=doc['ID_CLT'])
            # Récupère les informations du client associé au document en fonction de l'ID_CLT.

            doc["client"] = client.raison_sociale
            # Ajoute le champ "raison_sociale" du client au dictionnaire du document.

            data.append(doc)
            # Ajoute le document enrichi dans la liste `data`.

        return JsonResponse({"total": len(data), "data": data}, safe=False)
        # Retourne une réponse JSON avec le nombre total de documents et leurs données.

    if request.method == 'POST':
        # Gère la création d'un nouveau document (opération CREATE).

        doc_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête POST.

        doc_serializer = DocumentSerializer(data=doc_data)
        # Sérialise les données du document pour les valider et les sauvegarder.

        if doc_serializer.is_valid():
            # Vérifie si les données du document sont valides.

            doc_serializer.save()
            # Sauvegarde le document dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "Added Successfully!!",
                "errors": doc_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que le document a été ajouté avec succès.

        return JsonResponse({
            "status": False,
            "msg": "Failed to Add",
            "errors": doc_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'PUT':
        # Gère la mise à jour d'un document existant (opération UPDATE).

        doc_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête PUT.

        doc = Doc_clt.objects.get(ID_DOC_CLT=doc_data["ID_DOC_CLT"])
        # Récupère le document à mettre à jour en fonction de l'ID_DOC_CLT fourni.

        doc_serializer = DocumentSerializer(doc, data=doc_data)
        # Sérialise les données mises à jour pour les valider.

        if doc_serializer.is_valid():
            # Vérifie si les données mises à jour sont valides.

            doc_serializer.save()
            # Sauvegarde les modifications dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "updated Successfully!!",
                "errors": doc_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que la mise à jour a réussi.

        return JsonResponse({
            "status": False,
            "msg": "Failed to update",
            "errors": doc_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'DELETE':
        # Gère la suppression d'un document (opération DELETE).

        try:
            doc = Doc_clt.objects.get(ID_DOC_CLT=id)
            # Récupère le document à supprimer en fonction de l'ID_DOC_CLT fourni dans l'URL.

            doc.delete()
            # Supprime le document de la base de données.

            return JsonResponse("Deleted Succeffuly!!", safe=False)
            # Retourne une réponse JSON indiquant que le document a été supprimé avec succès.

        except Exception as e:
            # Capture les exceptions, par exemple si le document n'existe pas.

            return JsonResponse({
                "status": 404,
                "msg": "col n'existe pas"
            }, safe=False)
            # Retourne une réponse JSON avec un message d'erreur.

    
# Create your views here.
@csrf_exempt
def esn_view(request, id=0):
    # Vue pour gérer les opérations CRUD (Create, Read, Update, Delete) sur les ESN (Entreprises de Services du Numérique).

    # if checkAuth(request) == False:
    #     # Vérifie si l'utilisateur est authentifié via la fonction `checkAuth`.
    #     return JsonResponse({
    #         "status": False,
    #         "msg": "Non authentifié"
    #     }, safe=False, status=401)
        # Si l'utilisateur n'est pas authentifié, retourne une réponse JSON avec un statut HTTP 401 (Non autorisé).

    if request.method == 'GET':
        # Gère la récupération des ESN (opération READ).

        ESNS = ESN.objects.filter()
        # Récupère toutes les ESN de la base de données.

        ens_serializer = ESNSerializer(ESNS, many=True)
        # Sérialise les données des ESN récupérées pour les convertir en JSON.

        data = []
        # Initialise une liste pour stocker les données des ESN.

        for esn in ens_serializer.data:
            # Parcourt les données sérialisées des ESN.
            data.append(esn)
            # Ajoute chaque ESN à la liste `data`.

        return JsonResponse({"total": len(data), "data": data}, safe=False)
        # Retourne une réponse JSON contenant le nombre total d'ESN et leurs données.

    if request.method == 'POST':
        # Gère la création d'une nouvelle ESN (opération CREATE).

        esn_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête POST.

        # Hash password
        password = esn_data["password"]
        # Récupère le mot de passe fourni dans les données JSON.

        pwd_utf = password.encode()
        # Encode le mot de passe en UTF-8 pour le préparer au hachage.

        pwd_sh = hashlib.sha1(pwd_utf)
        # Calcule le hachage SHA-1 du mot de passe encodé.

        password_crp = pwd_sh.hexdigest()
        # Convertit le hachage en chaîne hexadécimale.

        # updated password to hashed password
        esn_data["password"] = password_crp
        # Remplace le mot de passe dans les données par le mot de passe haché.

        esn_serializer = ESNSerializer(data=esn_data)
        # Sérialise les données de l'ESN pour les valider et les sauvegarder.

        if esn_serializer.is_valid():
            # Vérifie si les données sérialisées sont valides.

            esn_serializer.save()
            # Sauvegarde la nouvelle ESN dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "Added Successfully!!e",
                "errors": esn_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que l'ESN a été ajoutée avec succès.

        if request.method == 'PATCH':
            # Gère la mise à jour partielle d'un appel d'offre (ex: activer/désactiver).
            try:
                patch_data = JSONParser().parse(request)
            except Exception:
                patch_data = {}

            target_id = id or patch_data.get("id")

            if not target_id:
                return JsonResponse({
                    "status": False,
                    "message": "Identifiant de l'appel d'offre requis pour la mise à jour partielle"
                }, safe=False, status=400)

            try:
                appel_offre = AppelOffre.objects.get(id=target_id)
            except AppelOffre.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"Appel d'offre avec l'identifiant {target_id} introuvable"
                }, safe=False, status=404)

            serializer = AppelOffreSerializer(appel_offre, data=patch_data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return JsonResponse({
                    "status": True,
                    "msg": "Appel d'offre mis à jour",
                    "data": serializer.data
                }, safe=False, status=200)

            return JsonResponse({
                "status": False,
                "message": "Échec de la mise à jour partielle",
                "errors": serializer.errors
            }, safe=False, status=400)

        return JsonResponse({
            "status": False,
            "msg": "Failed to Add",
            "errors": esn_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'PUT':
    # Gère la mise à jour d'une ESN existante (opération UPDATE).

        esn_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête PUT.

        try:
            # Handle ESN ID from URL parameter or request body (for admin interface compatibility)
            esn_id = id if id != 0 else esn_data.get("ID_ESN")
            
            esn = ESN.objects.get(ID_ESN=esn_id)
            # Récupère l'ESN à mettre à jour en fonction de l'ID_ESN fourni.

            # Store previous status for comparison
            previous_status = esn.Statut

            # CRITICAL: Password handling - preserve existing password in all cases
            # The password should NEVER be updated during profile/status updates
            current_hashed_password = esn.password
            incoming_password = esn_data.get("password", "")
            
            # Check if incoming password is actually a NEW password (not empty, not the existing hash)
            is_new_password = (
                incoming_password and 
                incoming_password.strip() != "" and
                incoming_password != current_hashed_password and
                len(incoming_password) < 40  # SHA1 hash is 40 chars, plain passwords are typically shorter
            )
            
            if is_new_password:
                # Only hash if it's genuinely a NEW plain-text password
                pwd_utf = incoming_password.encode()
                pwd_sh = hashlib.sha1(pwd_utf)
                password_crp = pwd_sh.hexdigest()
                esn_data["password"] = password_crp
                print(f"ESN {esn_id}: New password detected and hashed")
            else:
                # In ALL other cases, preserve the existing password
                # Remove password from update data to ensure it's not modified
                if "password" in esn_data:
                    del esn_data["password"]
                print(f"ESN {esn_id}: Password preserved - not included in update")

            # Use partial=True to allow updating only specific fields without requiring all fields
            esn_serializer = ESNSerializer(esn, data=esn_data, partial=True)
            # Sérialise les données mises à jour pour les valider.

            if esn_serializer.is_valid():
                # Vérifie si les données sérialisées mises à jour sont valides.

                esn_serializer.save()
                # Sauvegarde les modifications dans la base de données.

                # Check if status changed to "à signer" and send notification
                current_status = esn_data.get("Statut") or esn_data.get("statut")
                if (previous_status != "à signer" and current_status == "à signer"):
                    try:
                        # Send notification to ESN about account validation and contract signing
                        profile_link = f"/interface-en?menu=Profile"
                        esn_message = (
                            f"Félicitations {esn.Raison_sociale} ! Votre compte ESN a été validé par l'administrateur. "
                            f"Vous pouvez maintenant accéder à toutes les fonctionnalités de la plateforme. "
                            f"Pour finaliser votre inscription, vous devez signer le contrat de prestation. "
                            f"<a href='{profile_link}' class='notification-link' style='color: #1890ff; text-decoration: underline;'>Signer le contrat maintenant</a>"
                        )
                        
                        send_notification(
                            user_id=1,  # System/admin notification
                            dest_id=esn.ID_ESN,  # Notification goes to ESN
                            message=esn_message,
                            categorie="ESN",
                            event="Compte Validé - Contrat à Signer",
                            event_id=esn.ID_ESN
                        )
                        print(f"Notification sent to ESN {esn.ID_ESN}: Status changed to 'à signer'")
                    except Exception as notification_error:
                        print(f"Failed to send notification to ESN {esn.ID_ESN}: {str(notification_error)}")
                        # Continue execution even if notification fails

                return JsonResponse({
                    "status": True,
                    "msg": "Updated Successfully!",
                    "errors": esn_serializer.errors
                }, safe=False)
                # Retourne une réponse JSON indiquant que la mise à jour a réussi.

            return JsonResponse({
                "status": False,
                "msg": "Failed to Update",
                "errors": esn_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON contenant les erreurs si la validation échoue.

        except ESN.DoesNotExist:
            return JsonResponse({
                "status": False,
                "msg": "ESN not found",
            }, safe=False, status=404)
        except Exception as e:
            return JsonResponse({
                "status": False,
                "msg": f"Error: {str(e)}",
            }, safe=False, status=500)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'DELETE':
        # Gère la suppression d'une ESN (opération DELETE).

        try:
            esn = ESN.objects.get(ID_ESN=id)
            # Récupère l'ESN à supprimer en fonction de l'ID_ESN fourni dans l'URL.

            esn.delete()
            # Supprime l'ESN de la base de données.

            return JsonResponse("Deleted Succeffuly!!", safe=False)
            # Retourne une réponse JSON indiquant que l'ESN a été supprimée avec succès.

        except Exception as e:
            # Capture les exceptions en cas d'erreur (par exemple, si l'ESN n'existe pas).

            return JsonResponse({
                "status": 404,
                "msg": "esn n'existe pas"
            }, safe=False)
            # Retourne une réponse JSON avec un message d'erreur.



# Document view
@csrf_exempt
def docEsn_view(request, id=0):
    # Vue permettant de gérer les documents associés aux ESN avec des opérations CRUD (Create, Read, Update, Delete).

    if checkAuth(request) == False:
        # Vérifie si l'utilisateur est authentifié via la fonction `checkAuth`.
        return JsonResponse({
            "status": False,
            "msg": "Non authentifié"
        }, safe=False, status=401)
        # Si l'utilisateur n'est pas authentifié, retourne une réponse JSON avec un statut 401 (Non autorisé).

    if request.method == 'GET':
        
        # Gère la récupération des documents ESN (opération READ).

        docesns = DocumentESN.objects.filter()
        # Récupère tous les documents ESN depuis la base de données.

        docesn_serializer = DocumentESNSerializer(docesns, many=True)
        # Sérialise les documents récupérés pour les convertir en JSON.

        data = []
        # Initialise une liste pour stocker les données enrichies des documents ESN.

        for doc in docesn_serializer.data:
            # Parcourt chaque document sérialisé.

            esn = ESN.objects.get(ID_ESN=doc['ID_ESN'])
            # Récupère l'ESN associée au document en fonction de l'ID_ESN.

            doc["esn"] = esn.Raison_sociale
            # Ajoute le champ "Raison sociale" de l'ESN au dictionnaire du document.

            data.append(doc)
            # Ajoute le document enrichi dans la liste `data`.

        return JsonResponse({"total": len(data), "data": data}, safe=False)
        # Retourne une réponse JSON contenant le nombre total de documents et leurs données enrichies.

    if request.method == 'POST':
        # Gère la création d'un nouveau document ESN (opération CREATE).

        doc_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête POST.

        doc_serializer = DocumentESNSerializer(data=doc_data)
        # Sérialise les données du document pour les valider et les sauvegarder.

        if doc_serializer.is_valid():
            # Vérifie si les données sérialisées sont valides.

            doc_serializer.save()
            # Sauvegarde le document ESN dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "Added Successfully!!",
                "errors": doc_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que le document a été ajouté avec succès.

        return JsonResponse({
            "status": False,
            "msg": "Failed to Add",
            "errors": doc_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'PUT':
        # Gère la mise à jour d'un document existant (opération UPDATE).

        doc_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête PUT.

        doc = DocumentESN.objects.get(ID_DOC_ESN=doc_data["ID_DOC_ESN"])
        # Récupère le document à mettre à jour en fonction de l'ID_DOC_ESN fourni.

        doc_serializer = DocumentESNSerializer(doc, data=doc_data)
        # Sérialise les données mises à jour pour les valider.

        if doc_serializer.is_valid():
            # Vérifie si les données mises à jour sont valides.

            doc_serializer.save()
            # Sauvegarde les modifications dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "updated Successfully!!",
                "errors": doc_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que la mise à jour a réussi.

        return JsonResponse({
            "status": False,
            "msg": "Failed to update",
            "errors": doc_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'DELETE':
        # Gère la suppression d'un document ESN (opération DELETE).

        try:
            doc = DocumentESN.objects.get(ID_DOC_ESN=id)
            # Récupère le document à supprimer en fonction de l'ID_DOC_ESN fourni dans l'URL.

            doc.delete()
            # Supprime le document de la base de données.

            return JsonResponse("Deleted Succeffuly!!", safe=False)
            # Retourne une réponse JSON indiquant que le document a été supprimé avec succès.

        except Exception as e:
            # Capture les exceptions en cas d'erreur (par exemple, si le document n'existe pas).

            return JsonResponse({
                "status": 404,
                "msg": "docESN n'existe pas"
            }, safe=False)
            # Retourne une réponse JSON avec un message d'erreur.


# collaborateur_view
@csrf_exempt
def collaborateur_view(request, id=0):
    # Vue pour gérer les collaborateurs avec des opérations CRUD (Create, Read, Update, Delete).

    # if checkAuth(request) == False:
    #     # Vérifie si l'utilisateur est authentifié via la fonction `checkAuth`.
    #     return JsonResponse({
    #         "status": False,
    #         "msg": "Non authentifié"
    #     }, safe=False, status=401)
    #     # Si l'utilisateur n'est pas authentifié, retourne une réponse JSON avec un statut 401 (Non autorisé).

    if request.method == 'GET':
        # Gère la récupération des collaborateurs (opération READ).

        colls = Collaborateur.objects.filter()
        # Récupère tous les collaborateurs dans la base de données.

        Collaborateur_serializer = CollaborateurSerializer(colls, many=True)
        # Sérialise les collaborateurs récupérés pour les convertir en JSON.

        data = []
        # Initialise une liste pour stocker les données des collaborateurs.

        for col in Collaborateur_serializer.data:
            # Parcourt les collaborateurs sérialisés.
            data.append(col)
            # Ajoute chaque collaborateur à la liste `data`.

        return JsonResponse({"total": len(data), "data": data}, safe=False)
        # Retourne une réponse JSON contenant le nombre total de collaborateurs et leurs données.

    if request.method == 'POST':
        Collaborateur_data = JSONParser().parse(request)
        print(Collaborateur_data)
        # Check if email and password are present
        if not Collaborateur_data.get("email"):
            return JsonResponse({
                "status": False,
                "msg": "Email is required"
            }, safe=False)
            
        if not Collaborateur_data.get("password"):
            return JsonResponse({
                "status": False,
                "msg": "Password is required"
            }, safe=False)
        
        # Hash password
        password = Collaborateur_data.get("password")
        pwd_utf = password.encode()
        pwd_sh = hashlib.sha1(pwd_utf)
        password_crp = pwd_sh.hexdigest()
        Collaborateur_data["password"] = password_crp
        
        col_serializer = CollaborateurSerializer(data=Collaborateur_data)
        
        if col_serializer.is_valid():
            col_serializer.save()
            
            return JsonResponse({
                "status": True,
                "msg": "Added Successfully!!",
                "errors": col_serializer.errors
            }, safe=False)

        return JsonResponse({
            "status": False,
            "msg": "Failed to Add",
            "errors": col_serializer.errors
        }, safe=False)
        
    if request.method == 'PUT':
        # Gère la mise à jour d'un collaborateur existant (opération UPDATE).

        col_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête PUT.

        col = Collaborateur.objects.get(ID_collab=col_data["ID_collab"])
        # Récupère le collaborateur à mettre à jour en fonction de l'ID_collab fourni.

        # Preserve existing password if not provided in update
        if 'password' not in col_data or not col_data.get('password'):
            col_data['password'] = col.password
        else:
            # Hash the new password if provided
            password = col_data.get("password")
            pwd_utf = password.encode()
            pwd_sh = hashlib.sha1(pwd_utf)
            col_data['password'] = pwd_sh.hexdigest()

        col_serializer = CollaborateurSerializer(col, data=col_data)
        # Sérialise les données mises à jour pour les valider.

        if col_serializer.is_valid():
            # Vérifie si les données mises à jour sont valides.

            col_serializer.save()
            # Sauvegarde les modifications dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "updated Successfully!!",
                "errors": col_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que la mise à jour a réussi.

        return JsonResponse({
            "status": False,
            "msg": "Failed to update",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'DELETE':
        # Gère la suppression d'un collaborateur (opération DELETE).

        try:
            col = Collaborateur.objects.get(ID_collab=id)
            # Récupère le collaborateur à supprimer en fonction de l'ID_collab fourni dans l'URL.

            col.delete()
            # Supprime le collaborateur de la base de données.

            return JsonResponse("Deleted Succeffuly!!", safe=False)
            # Retourne une réponse JSON indiquant que le collaborateur a été supprimé avec succès.

        except Exception as e:
            # Capture les exceptions en cas d'erreur (par exemple, si le collaborateur n'existe pas).

            return JsonResponse({
                "status": 404,
                "msg": "col n'existe pas"
            }, safe=False)
            # Retourne une réponse JSON avec un message d'erreur.


# Admin views .
@csrf_exempt
def admin_view(request, id=0):
    # Vue permettant de gérer les administrateurs avec des opérations CRUD (Create, Read, Update, Delete).

    if checkAuth(request) == False:
        # Vérifie si l'utilisateur est authentifié via la fonction `checkAuth`.
        return JsonResponse({
            "status": False,
            "msg": "Non authentifié"
        }, safe=False, status=401)
        # Si l'utilisateur n'est pas authentifié, retourne une réponse JSON avec un statut HTTP 401 (Non autorisé).

    if request.method == 'GET':
        # Gère la récupération des administrateurs (opération READ).

        admins = Admin.objects.filter()
        # Récupère tous les administrateurs dans la base de données.

        admin_serializer = AdminSerializer(admins, many=True)
        # Sérialise les administrateurs récupérés pour les convertir en JSON.

        data = []
        # Initialise une liste pour stocker les données des administrateurs.

        for admin in admin_serializer.data:
            # Parcourt les administrateurs sérialisés.
            data.append(admin)
            # Ajoute chaque administrateur à la liste `data`.

        return JsonResponse({"total": len(data), "data": data}, safe=False)
        # Retourne une réponse JSON contenant le nombre total d'administrateurs et leurs données.

    if request.method == 'POST':
        # Gère la création d'un nouvel administrateur (opération CREATE).

        admin_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête POST.

        # Hash password
        mdp = admin_data["mdp"]
        # Récupère le mot de passe fourni dans les données JSON.

        pwd_utf = mdp.encode()
        # Encode le mot de passe en UTF-8 pour le préparer au hachage.

        pwd_sh = hashlib.sha1(pwd_utf)
        # Calcule le hachage SHA-1 du mot de passe encodé.

        password_crp = pwd_sh.hexdigest()
        # Convertit le hachage en chaîne hexadécimale.

        # updated password to hashed password
        admin_data["mdp"] = password_crp
        # Met à jour le mot de passe avec sa version hachée.

        admin_serializer = AdminSerializer(data=admin_data)
        # Sérialise les données de l'administrateur pour les valider et les sauvegarder.

        if admin_serializer.is_valid():
            # Vérifie si les données sérialisées sont valides.

            admin_serializer.save()
            # Sauvegarde l'administrateur dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "Added Successfully!!",
                "errors": admin_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que l'administrateur a été ajouté avec succès.

        return JsonResponse({
            "status": False,
            "msg": "Failed to Add",
            "errors": admin_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'PUT':
        # Gère la mise à jour d'un administrateur existant (opération UPDATE).

        admin_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête PUT.

        admin = Admin.objects.get(ID_Admin=admin_data["ID_Admin"])
        # Récupère l'administrateur à mettre à jour en fonction de l'ID_Admin fourni.

        # Hash password
        mdp = admin_data["mdp"]
        # Récupère le mot de passe fourni dans les données JSON.

        pwd_utf = mdp.encode()
        # Encode le mot de passe en UTF-8 pour le préparer au hachage.

        pwd_sh = hashlib.sha1(pwd_utf)
        # Calcule le hachage SHA-1 du mot de passe encodé.

        password_crp = pwd_sh.hexdigest()
        # Convertit le hachage en chaîne hexadécimale.

        # updated password to hashed password
        admin_data["mdp"] = password_crp
        # Met à jour le mot de passe avec sa version hachée.

        admin_serializer = AdminSerializer(admin, data=admin_data)
        # Sérialise les données mises à jour pour les valider.

        if admin_serializer.is_valid():
            # Vérifie si les données mises à jour sont valides.

            admin_serializer.save()
            # Sauvegarde les modifications dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "updated Successfully!!",
                "errors": admin_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que la mise à jour a réussi.

        return JsonResponse({
            "status": False,
            "msg": "Failed to update",
            "errors": admin_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'DELETE':
        # Gère la suppression d'un administrateur (opération DELETE).

        admin = Admin.objects.get(ID_Admin=id)
        # Récupère l'administrateur à supprimer en fonction de l'ID_Admin fourni dans l'URL.

        admin.delete()
        # Supprime l'administrateur de la base de données.

        return JsonResponse("Deleted Succeffuly!!", safe=False)
        # Retourne une réponse JSON indiquant que l'administrateur a été supprimé avec succès.

    
@csrf_exempt
def get_appel_offre_with_candidatures_by_esn(request):
    esn_id = request.GET.get("esn_id")
    if request.method == 'GET':
    
        if not esn_id:
            return JsonResponse({"status": False, "message": "esn_id manquant"}, safe=False, status=400)

        appel_offres = AppelOffre.objects.filter(
            id__in=Candidature.objects.filter(esn_id=esn_id).values_list('AO_id', flat=True)
        ).distinct().order_by('-id')

        # Sérialiser les données des appels d'offres
        appel_offre_serializer = AppelOffreSerializer(appel_offres, many=True)
        data = appel_offre_serializer.data  # No need to iterate manually

        return JsonResponse({"status": True, "data": data}, safe=False)   
@csrf_exempt
def appelOffre_view(request, id=0):
    # Vue permettant de gérer les appels d'offres avec des opérations CRUD (Create, Read, Update, Delete).

    if request.method == 'GET':
        # Gère la récupération des appels d'offres (opération READ).

        colls = AppelOffre.objects.filter()
        # Récupère tous les appels d'offres dans la base de données.

        Collaborateur_serializer = AppelOffreSerializer(colls, many=True)
        # Sérialise les appels d'offres récupérés pour les convertir en JSON.

        data = []
        # Initialise une liste pour stocker les données des appels d'offres.

        for col in Collaborateur_serializer.data:
            # Parcourt les appels d'offres sérialisés.
            ao_data = dict(col)
            
            # Get the latest client information
            try:
                if ao_data.get('client_id'):
                    client = Client.objects.get(ID_clt=ao_data['client_id'])
                    ao_data['client_name'] = client.raison_sociale
                    ao_data['client_raison_sociale'] = client.raison_sociale
            except Client.DoesNotExist:
                ao_data['client_name'] = 'Client introuvable'
                ao_data['client_raison_sociale'] = 'Client introuvable'
            except Exception as e:
                print(f"Warning: Could not retrieve client info for AO {ao_data['id']}: {str(e)}")
                ao_data['client_name'] = 'Erreur de récupération'
                ao_data['client_raison_sociale'] = 'Erreur de récupération'
            
            # Check if this Appel d'Offre has any accepted BDC
            try:
                # Get all candidatures for this AO
                candidatures = Candidature.objects.filter(AO_id=ao_data['id'])
                candidature_ids = list(candidature_ids_queryset := candidatures.values_list('id_cd', flat=True))
                
                print(f"DEBUG AO {ao_data['id']} ({ao_data.get('titre', 'No title')}): Found {len(candidature_ids)} candidatures")
                
                # Check if any BDC for these candidatures has active status
                accepted_statuses = ['active', 'ACTIVE', 'Active', 'ACTIF', 'Actif', 'accepted_esn']
                accepted_bdcs = Bondecommande.objects.filter(
                    candidature_id__in=candidature_ids,
                    statut__in=accepted_statuses
                )
                has_accepted_bdc = accepted_bdcs.exists()
                
                if accepted_bdcs.exists():
                    print(f"DEBUG: AO {ao_data['id']} HAS ACCEPTED BDC:")
                    for bdc in accepted_bdcs:
                        print(f"  - BDC {bdc.id_bdc}, statut: {bdc.statut}, candidature: {bdc.candidature_id}")
                else:
                    print(f"DEBUG: AO {ao_data['id']} has NO accepted BDC")
                
                ao_data['has_accepted_bdc'] = has_accepted_bdc
            except Exception as e:
                print(f"Error checking BDC status for AO {ao_data['id']}: {str(e)}")
                import traceback
                traceback.print_exc()
                ao_data['has_accepted_bdc'] = False
            
            data.append(ao_data)
            # Ajoute chaque appel d'offre à la liste `data`.

        return JsonResponse({"total": len(data), "data": data}, safe=False)
        # Retourne une réponse JSON contenant le nombre total d'appels d'offres et leurs données.

    if request.method == 'POST':
        # Gère la création d'un nouvel appel d'offre (opération CREATE).

        Collaborateur_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête POST.

        col_serializer = AppelOffreSerializer(data=Collaborateur_data)
        # Sérialise les données de l'appel d'offre pour les valider et les sauvegarder.

        if col_serializer.is_valid():
            # Vérifie si les données sérialisées sont valides.

            col_serializer.save()

            # Sauvegarde l'appel d'offre dans la base de données.
            esn_tokens = list(ESN.objects.values_list('token', flat=True))
            
            # Send notifications to all ESNs if AO is Public (statut = "1")
            ao_id = col_serializer.data["id"]
            ao_statut = col_serializer.data.get("statut")
            
            if ao_statut == "1":  # Public
                try:
                    # Get client and AO details
                    appel_offre = AppelOffre.objects.get(id=ao_id)
                    client_id = appel_offre.client_id
                    ao_title = appel_offre.titre
                    ao_date_limite = appel_offre.date_limite
                    
                    try:
                        client = Client.objects.get(ID_clt=client_id)
                        client_name = client.raison_sociale
                    except Client.DoesNotExist:
                        client_name = f"Client ID={client_id}"
                    
                    # Get all ESNs
                    all_esns = ESN.objects.all()
                    
                    # Create detail link for ESN
                    ao_detail_link_esn = f"/interface-en/appeldoffre/{ao_id}"
                    
                    # Send notifications to all ESNs
                    for esn in all_esns:
                        message_esn = (
                            # f"<strong>Nouvel Appel d'Offres Public</strong><br><br>"
                            f"Projet: <strong>{ao_title}</strong><br>"
                            f"Client: {client_name}<br>"
                            f"Date limite: {ao_date_limite}<br><br>"
                            f"<a href='{ao_detail_link_esn}' class='notification-link'>Voir les details et postuler</a>"
                        )
                        
                        send_notification(
                            user_id=client_id,
                            dest_id=esn.ID_ESN,
                            message=message_esn,
                            categorie="ESN",
                            event="Nouvel Appel d'Offres Public",
                            event_id=ao_id
                        )
                    
                    print(f"Notifications envoyées à {all_esns.count()} ESNs pour l'AO public {ao_id}")
                except Exception as e:
                    print(f"Erreur lors de l'envoi des notifications ESN: {str(e)}")
                    # Don't fail the AO creation if notification fails
            
            return JsonResponse({
                "status": True,
                "msg": "Added Successfully!!",
                "errors": col_serializer.errors,
                "id" : col_serializer.data["id"],
                "data" : col_serializer.data,
                "esn_tokens": esn_tokens
            }, safe=False)
            # Retourne une réponse JSON indiquant que l'appel d'offre a été ajouté avec succès.

        return JsonResponse({
            "status": False,
            "msg": "Failed to Add",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'PUT':
        # Gère la mise à jour d'un appel d'offre existant (opération UPDATE).

        col_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête PUT.

        col = AppelOffre.objects.get(id=col_data["id"])
        # Récupère l'appel d'offre à mettre à jour en fonction de l'identifiant fourni.

        col_serializer = AppelOffreSerializer(col, data=col_data)
        # Sérialise les données mises à jour pour les valider.

        if col_serializer.is_valid():
            # Vérifie si les données mises à jour sont valides.

            col_serializer.save()
            # Sauvegarde les modifications dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "updated Successfully!!",
                "errors": col_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que la mise à jour a réussi.

        return JsonResponse({
            "status": False,
            "msg": "Failed to update",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'PATCH':
        # Gère les actions partielles comme l'activation/désactivation.
        try:
            payload = JSONParser().parse(request)
        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": f"Corps de requête invalide: {str(e)}"
            }, safe=False, status=400)

        try:
            col = AppelOffre.objects.get(id=id)
        except AppelOffre.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": f"Appel d'offre avec l'identifiant {id} introuvable"
            }, safe=False, status=404)

        action = payload.get("action")
        target_status = payload.get("statut")

        if action == "activate":
            target_status = target_status or "1"
        elif action == "deactivate":
            target_status = target_status or "inactive"

        if not target_status:
            return JsonResponse({
                "status": False,
                "message": "Le champ 'statut' est requis pour cette action"
            }, safe=False, status=400)

        col.statut = str(target_status)
        col.save(update_fields=["statut"])

        return JsonResponse({
            "status": True,
            "message": "Statut mis à jour avec succès",
            "data": {
                "id": col.id,
                "statut": col.statut
            }
        }, safe=False)

    if request.method == 'DELETE':
        # Gère la désactivation d'un appel d'offre au lieu de le supprimer définitivement.
        try:
            col = AppelOffre.objects.get(id=id)
        except AppelOffre.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": f"Appel d'offre avec l'identifiant {id} introuvable"
            }, safe=False, status=404)

        # Marquer l'appel d'offre comme désactivé pour conserver l'historique
        col.statut = "inactive"
        col.save(update_fields=["statut"])

        return JsonResponse({
            "status": True,
            "message": "Appel d'offre désactivé avec succès"
        }, safe=False)
        # Retourne une réponse JSON indiquant que l'appel d'offre a été désactivé avec succès.

    
@csrf_exempt
def candidature_view(request, id=0):
    # Vue pour gérer les candidatures avec des opérations CRUD (Create, Read, Update, Delete).

    def _normalize_commercial_identifier(raw_value):
        if raw_value in (None, "", "null"):
            return None

        try:
            return int(raw_value)
        except (TypeError, ValueError):
            try:
                cleaned = str(raw_value).strip()
                return int(cleaned)
            except (TypeError, ValueError):
                return None

    if request.method == 'GET':
        # Gère la récupération des candidatures (opération READ).

        colls = Candidature.objects.filter()
        # Récupère toutes les candidatures de la base de données.

        Collaborateur_serializer = CandidatureSerializer(colls, many=True)
        # Sérialise les candidatures récupérées pour les convertir en JSON.

        data = []
        # Initialise une liste pour stocker les données des candidatures.

        for col in Collaborateur_serializer.data:
            # Parcourt les candidatures sérialisées.
            data.append(col)
            # Ajoute chaque candidature à la liste `data`.

        return JsonResponse({"total": len(data), "data": data}, safe=False)
        # Retourne une réponse JSON contenant le nombre total de candidatures et leurs données.

    if request.method == 'POST':
        # Gère la création d'une nouvelle candidature (opération CREATE).
        Collaborateur_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête POST.

        raw_commercial_id = Collaborateur_data.get("commercial_id")
        normalized_commercial = _normalize_commercial_identifier(raw_commercial_id)

        if normalized_commercial is None:
            normalized_commercial = _normalize_commercial_identifier(
                Collaborateur_data.get("id_responsable")
            )

        Collaborateur_data["commercial_id"] = normalized_commercial
        Collaborateur_data.pop("id_responsable", None)

        col_serializer = CandidatureSerializer(data=Collaborateur_data)
        # Sérialise les données de la candidature pour les valider et les sauvegarder.

        if col_serializer.is_valid():
            # Vérifie si les données sérialisées sont valides.

            col_serializer.save()
            # Sauvegarde la candidature dans la base de données.

            # Fetch the project and client token
            token = None

        # Fetch the project and client token
            try:
                project = AppelOffre.objects.get(id=Collaborateur_data["AO_id"])
                client = Client.objects.get(ID_clt=project.client_id)
                token = client.token

            except AppelOffre.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "msg": "Appel d'offre not found"
                }, safe=False)    
            except Client.DoesNotExist:
                token = None

            return JsonResponse({
                "status": True,
                "msg": "Added Successfully!!",
                "id": col_serializer.data["id_cd"],
                "errors": col_serializer.errors,
                "token": token
            }, safe=False)        # Retourne une réponse JSON indiquant que la candidature a été ajoutée avec succès.

        return JsonResponse({
            "status": False,
            "msg": "Failed to Add",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'PUT':
        # Gère la mise à jour d'une candidature existante (opération UPDATE).

        col_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête PUT.

        raw_commercial_id = col_data.get("commercial_id")
        normalized_commercial = _normalize_commercial_identifier(raw_commercial_id)

        if normalized_commercial is None:
            normalized_commercial = _normalize_commercial_identifier(
                col_data.get("id_responsable")
            )

        col_data["commercial_id"] = normalized_commercial
        col_data.pop("id_responsable", None)

        col = Candidature.objects.get(id_cd=col_data["id_cd"])
        # Récupère la candidature à mettre à jour en fonction de l'identifiant fourni.

        col_serializer = CandidatureSerializer(col, data=col_data)
        # Sérialise les données mises à jour pour les valider.

        if col_serializer.is_valid():
            # Vérifie si les données mises à jour sont valides.

            col_serializer.save()
            # Sauvegarde les modifications dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "updated Successfully!!",
                "errors": col_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que la mise à jour a réussi.

        return JsonResponse({
            "status": False,
            "msg": "Failed to update",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'DELETE':
        # Gère la suppression d'une candidature (opération DELETE).

        col = Candidature.objects.get(id_cd=id)
        # Récupère la candidature à supprimer en fonction de son identifiant fourni dans l'URL.

        col.delete()
        # Supprime la candidature de la base de données.

        return JsonResponse("Deleted Successfully!!", safe=False)
        # Retourne une réponse JSON indiquant que la candidature a été supprimée avec succès.


@csrf_exempt
def update_candidature_status(request):
    if request.method == 'PUT':
        # Parse the JSON data from the request
        data = JSONParser().parse(request)

        def _normalize_status(value):
            if not value:
                return ""
            normalized = unicodedata.normalize('NFKD', str(value))
            return ''.join(ch for ch in normalized if not unicodedata.combining(ch)).strip().lower()

        # Check if 'id' and 'status' are in the data
        if 'id_cd' not in data or 'statut' not in data:
            return JsonResponse({
                "status": False,
                "msg": "Missing 'id' or 'status' in request data"
            }, safe=False)

        # Update the status of the candidature
        id = data['id_cd']
        statut = data['statut']

        try:
            candidature = Candidature.objects.get(id_cd=id)
            old_statut = candidature.statut  # Store old status for comparison
            candidature.statut = statut
            candidature.save()

            normalized_new_status = _normalize_status(statut)
            normalized_old_status = _normalize_status(old_statut)

            print(f"DEBUG: Candidature {id} - Old status: '{old_statut}' (normalized: '{normalized_old_status}'), New status: '{statut}' (normalized: '{normalized_new_status}')")

            # If candidature is being accepted (status changed to "Accepté"), send notification to ESN
            if (
                normalized_new_status == "accepte"
                and normalized_new_status != normalized_old_status
            ):
                try:
                    # Get related information for notification
                    appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                    ao_title = appel_offre.titre
                    client_id = appel_offre.client_id
                    
                    # Get client details with fallback
                    client_name = "Client non spécifié"
                    try:
                        client = Client.objects.get(ID_clt=client_id)
                        client_name = client.raison_sociale
                    except Client.DoesNotExist:
                        # Use fallback client name if client not found
                        client_name = f"Client (ID: {client_id})"
                    
                    # Get consultant details if available
                    consultant_name = "Non spécifié"
                    if candidature.id_consultant:
                        try:
                            consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
                            consultant_name = f"{consultant.Nom} {consultant.Prenom}"
                        except Collaborateur.DoesNotExist:
                            consultant_name = f"Consultant (ID: {candidature.id_consultant})"
                    
                    # Send notification to ESN with updated message
                    bdc_link = f"/interface-en?menu=Bon-de-Commande"
                    message_esn = (
                        f"Félicitations ! Votre candidature pour l'appel d'offre \"{ao_title}\" "
                        f"a été acceptée par {client_name}. Consultant proposé : {consultant_name}. "
                        f"Prochaine étape : Valider le bon de commande. "
                        f"<a href='{bdc_link}' style='color: #1890ff; text-decoration: underline;'>BDC</a>"
                    )
                    
                    # Use a default user_id for notification (admin or system)
                    # Since client may not exist, use client_id or 1 as fallback
                    notification_user_id = 1  # Default to admin user
                    
                    send_notification(
                        user_id=notification_user_id,  # System/admin triggered notification
                        dest_id=candidature.esn_id,  # Notification goes to ESN
                        event_id=id,
                        event="Candidature Acceptée",
                        message=message_esn,
                        categorie="ESN"
                    )
                    
                    print(f"DEBUG: Notification envoyée à l'ESN {candidature.esn_id} pour candidature acceptée {id}")
                    
                except Exception as e:
                    print(f"DEBUG: Erreur lors de l'envoi de notification: {e}")
                    # Continue anyway, don't block the status update

            # Notify ESN when candidature is refused by the client
            if (
                (normalized_new_status.startswith("refus") or normalized_new_status.startswith("rejet"))
                and normalized_new_status != normalized_old_status
                and normalized_new_status != "accepte"  # Explicitly exclude acceptance
                and candidature.esn_id
            ):
                try:
                    appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                    ao_title = appel_offre.titre
                    client_id = appel_offre.client_id

                    client_name = "Client"
                    if client_id:
                        try:
                            client = Client.objects.get(ID_clt=client_id)
                            client_name = client.raison_sociale
                        except Client.DoesNotExist:
                            client_name = f"Client (ID: {client_id})"

                    message_esn = (
                        f"Votre candidature pour l'appel d'offre \"{ao_title}\" "
                        f"n'a pas été retenue par {client_name}. "
                        f"Nous vous encourageons à consulter d'autres opportunités disponibles. "
                        f'<a href="/interface-en?menu=Liste-Candidature" style="color: #1890ff; text-decoration: underline;">Voir mes candidatures</a>'
                    )

                    notification_user_id = client_id or 1

                    send_notification(
                        user_id=notification_user_id,
                        dest_id=candidature.esn_id,
                        event_id=id,
                        event="Candidature Refusée",
                        message=message_esn,
                        categorie="ESN"
                    )

                    print(
                        f"DEBUG: Notification de refus envoyée à l'ESN {candidature.esn_id} pour la candidature {id}"
                    )
                except Exception as e:
                    print(f"DEBUG: Erreur lors de l'envoi de notification de refus: {e}")

            return JsonResponse({
                "status": True,
                "msg": "Status updated successfully"
            }, safe=False)
        except Candidature.DoesNotExist:
            return JsonResponse({
                "status": False,
                "msg": "Candidature not found"
            }, safe=False)

    return JsonResponse({
        "status": False,
        "msg": "Invalid request method"
    }, safe=False)


    
@csrf_exempt
def notification_view(request, id=0):
    # Vue pour gérer les notifications avec des opérations CRUD (Create, Read, Update, Delete).

    if request.method == 'GET':
        # Gère la récupération des notifications (opération READ).

        colls = Notification.objects.filter()
        # Récupère toutes les notifications dans la base de données.

        Collaborateur_serializer = NotificationSerializer(colls, many=True)
        # Sérialise les notifications récupérées pour les convertir en JSON.

        data = []
        # Initialise une liste pour stocker les données des notifications.

        for col in Collaborateur_serializer.data:
            # Parcourt les notifications sérialisées.
            data.append(col)
            # Ajoute chaque notification à la liste `data`.

        return JsonResponse({"total": len(data), "data": data}, safe=False)
        # Retourne une réponse JSON contenant le nombre total de notifications et leurs données.

    if request.method == 'POST':
        # Gère la création d'une nouvelle notification (opération CREATE).

        Collaborateur_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête POST.

        col_serializer = NotificationSerializer(data=Collaborateur_data)
        # Sérialise les données de la notification pour les valider et les sauvegarder.

        if col_serializer.is_valid():
            # Vérifie si les données sérialisées sont valides.

            col_serializer.save()
            # Sauvegarde la notification dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "Added Successfully!!",
                "errors": col_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que la notification a été ajoutée avec succès.

        return JsonResponse({
            "status": False,
            "msg": "Failed to Add",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'PUT':
        # Gère la mise à jour d'une notification existante (opération UPDATE).

        col_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête PUT.

        # Use the id from the URL path if provided, otherwise fall back to request body
        notification_id = id if id else col_data.get("id")
        if not notification_id:
            return JsonResponse({
                "status": False,
                "msg": "Failed to update",
                "errors": {"id": ["Notification ID is required"]}
            }, safe=False)

        col = Notification.objects.get(id=notification_id)
        # Récupère la notification à mettre à jour en fonction de l'identifiant fourni.

        if 'status' in col_data:
            col.status = col_data['status']
        # Met à jour le champ status dans la notification.

        if 'event_id' not in col_data:
            col_data['event_id'] = col.event_id
        # Assure que l'event_id n'est pas nul.

        col_serializer = NotificationSerializer(col, data=col_data)
        # Sérialise les données mises à jour pour les valider.

        if col_serializer.is_valid():
            # Vérifie si les données mises à jour sont valides.

            col_serializer.save()
            # Sauvegarde les modifications dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "updated Successfully!!",
                "errors": col_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que la mise à jour a réussi.

        return JsonResponse({
            "status": False,
            "msg": "Failed to update",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON indiquant que la mise à jour a échoué.

        return JsonResponse({
            "status": False,
            "msg": "Failed to update",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON indiquant que la mise à jour a échoué.
        return JsonResponse({
            "status": False,
            "msg": "Failed to update",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'DELETE':
        # Gère la suppression d'une notification (opération DELETE).

        col = Notification.objects.get(id=id)
        # Récupère la notification à supprimer en fonction de l'identifiant fourni dans l'URL.

        col.delete()
        # Supprime la notification de la base de données.

        return JsonResponse("Deleted Successfully!!", safe=False)
        # Retourne une réponse JSON indiquant que la notification a été supprimée avec succès.

@csrf_exempt
def update_token(request):
    if request.method == 'PUT':
        # Parse the JSON data from the request
        data = JSONParser().parse(request)
        # Check if 'type', 'id', and 'token' are in the data
        if 'type' not in data or 'id' not in data or 'token' not in data:
            return JsonResponse({
                "status": False,
                "msg": "Missing 'type', 'id' or 'token' in request data"
            }, safe=False)

        # Update the token based on the type and id
        type = data['type']
        id = data['id']
        token = data['token']

        try:
            if type == 'esn':
                esn = ESN.objects.get(ID_ESN=id)
                esn.token = token
                esn.save()
            elif type == 'client':
                client = Client.objects.get(ID_clt=id)
                client.token = token
                client.save()
            else:
                return JsonResponse({
                    "status": False,
                    "msg": "Invalid type"
                }, safe=False)

            return JsonResponse({
                "status": True,
                "msg": "Token updated successfully"
            }, safe=False)
        except (ESN.DoesNotExist, Client.DoesNotExist):
            return JsonResponse({
                "status": False,
                "msg": f"{type.capitalize()} not found"
            }, safe=False)

    return JsonResponse({
        "status": False,
        "msg": "Invalid request method"
    }, safe=False)




@csrf_exempt
def Bondecommande_view(request, id=0):
    # Vue permettant de gérer les bons de commande avec des opérations CRUD (Create, Read, Update, Delete).

    if request.method == 'GET':
        # Gère la récupération des bons de commande (opération READ).

        colls = Bondecommande.objects.filter()
        # Récupère tous les bons de commande depuis la base de données.

        Collaborateur_serializer = BondecommandeSerializer(colls, many=True)
        # Sérialise les bons de commande récupérés pour les convertir en JSON.

        data = []
        # Initialise une liste pour stocker les données des bons de commande.

        for col in Collaborateur_serializer.data:
            # Parcourt les bons de commande sérialisés.
            bdc_data = dict(col)
            # Convertit les données du BDC en dictionnaire
            
            # Enrichir avec les informations du projet (titre de l'appel d'offre)
            try:
                # Récupérer la candidature associée
                candidature = Candidature.objects.get(id_cd=bdc_data['candidature_id'])
                
                # Récupérer l'appel d'offre pour obtenir le titre du projet
                appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                
                # Ajouter le titre du projet aux données du BDC
                bdc_data['project_title'] = appel_offre.titre
                
                # Add project status from AppelOffre (this is the work status set by ESN)
                bdc_data['status'] = appel_offre.statut
                
                # Ajouter d'autres informations utiles
                try:
                    # Informations client
                    client = Client.objects.get(ID_clt=appel_offre.client_id)
                    bdc_data['client_name'] = client.raison_sociale
                    bdc_data['client_id'] = client.ID_clt
                except Client.DoesNotExist:
                    bdc_data['client_name'] = f"Client ID: {appel_offre.client_id}"
                    bdc_data['client_id'] = appel_offre.client_id
                
                try:
                    # Informations ESN
                    esn = ESN.objects.get(ID_ESN=candidature.esn_id)
                    bdc_data['esn_name'] = esn.Raison_sociale
                    bdc_data['esn_id'] = esn.ID_ESN
                except ESN.DoesNotExist:
                    bdc_data['esn_name'] = f"ESN ID: {candidature.esn_id}"
                    bdc_data['esn_id'] = candidature.esn_id
                
                try:
                    # Informations consultant
                    if candidature.id_consultant:
                        consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
                        bdc_data['consultant_name'] = f"{consultant.Nom} {consultant.Prenom}"
                        bdc_data['consultant_id'] = consultant.ID_collab
                    else:
                        bdc_data['consultant_name'] = "Non assigné"
                        bdc_data['consultant_id'] = None
                except Collaborateur.DoesNotExist:
                    bdc_data['consultant_name'] = "Consultant non trouvé"
                    bdc_data['consultant_id'] = candidature.id_consultant
                
                # Informations candidature
                bdc_data['responsable_compte'] = candidature.responsable_compte
                bdc_data['commercial_id'] = candidature.commercial_id
                bdc_data['tjm'] = candidature.tjm
                bdc_data['budget'] = bdc_data.get('montant_total', 0)  # Expose montant_total as budget
                
                # Calculate consumed days and budget for this project
                # Prévisionnelle: CRAs submitted by consultants (EVP status and validated)
                # Réelle: Only VALIDATED CRAs
                # Budget consumption is calculated per consultant using their specific TJM
                try:
                    # Get AppelOffre ID for this BDC (for backwards compatibility with CRAs stored with AO ID)
                    ao_id = candidature.AO_id
                    
                    # Get all CRAs for this project - check both BDC ID and AppelOffre ID
                    # (Some CRAs may have been stored with AppelOffre ID instead of BDC ID)
                    from django.db.models import Q
                    all_cras = CRA_imputation.objects.filter(
                        Q(id_bdc=bdc_data['id_bdc']) | Q(id_bdc=ao_id)
                    )
                    
                    # Build a TJM lookup per consultant from candidatures
                    # Get all candidatures for this project
                    project_candidatures = Candidature.objects.filter(
                        AO_id=ao_id,
                        esn_id=candidature.esn_id
                    )
                    consultant_tjm_map = {}
                    for cand in project_candidatures:
                        consultant_tjm_map[cand.id_consultant] = float(cand.tjm) if cand.tjm else 0
                    
                    # Default TJM from BDC if consultant not found
                    default_tjm = float(bdc_data.get('TJM', 0) or candidature.tjm or 0)
                    
                    # Prévisionnelle: À saisir + a_saisir + EVP (all planned/submitted CRAs)
                    previsional_statuses = ['À saisir', 'a_saisir', 'EVP']
                    previsional_cras = all_cras.filter(statut__in=previsional_statuses)
                    jours_previsionnels = sum(float(cra.Durée or 0) for cra in previsional_cras)
                    
                    # Calculate budget consumption using per-consultant TJM
                    montant_previsionnel = 0
                    for cra in previsional_cras:
                        cra_days = float(cra.Durée or 0)
                        cra_consultant_id = cra.id_consultan
                        cra_tjm = consultant_tjm_map.get(cra_consultant_id, default_tjm)
                        montant_previsionnel += cra_days * cra_tjm
                    
                    # Réelle: only validated CRAs
                    validated_cras = all_cras.filter(statut__in=['Validé'])
                    jours_reels = sum(float(cra.Durée or 0) for cra in validated_cras)
                    
                    # Calculate validated budget consumption using per-consultant TJM
                    montant_reel = 0
                    for cra in validated_cras:
                        cra_days = float(cra.Durée or 0)
                        cra_consultant_id = cra.id_consultan
                        cra_tjm = consultant_tjm_map.get(cra_consultant_id, default_tjm)
                        montant_reel += cra_days * cra_tjm
                    
                    bdc_data['jours_consommes_previsionnels'] = jours_previsionnels
                    bdc_data['jours_consommes_reels'] = jours_reels
                    bdc_data['montant_consomme_previsionnel'] = montant_previsionnel
                    bdc_data['montant_consomme_reel'] = montant_reel
                except Exception as e:
                    bdc_data['jours_consommes_previsionnels'] = 0
                    bdc_data['jours_consommes_reels'] = 0
                    bdc_data['montant_consomme_previsionnel'] = 0
                    bdc_data['montant_consomme_reel'] = 0
                
            except (Candidature.DoesNotExist, AppelOffre.DoesNotExist):
                # Si les données liées ne sont pas trouvées, continuer sans le titre du projet
                bdc_data['project_title'] = f"Projet BDC-{bdc_data['id_bdc']}"
                bdc_data['budget'] = bdc_data.get('montant_total', 0)  # Expose montant_total as budget
                bdc_data['jours_consommes_previsionnels'] = 0
                bdc_data['jours_consommes_reels'] = 0
                bdc_data['montant_consomme_previsionnel'] = 0
                bdc_data['montant_consomme_reel'] = 0
            
            data.append(bdc_data)
            # Ajoute chaque bon de commande enrichi à la liste `data`.

        return JsonResponse({"total": len(data), "data": data}, safe=False)
        # Retourne une réponse JSON contenant le nombre total de bons de commande et leurs données.

    if request.method == 'POST':
        # Gère la création d'un nouveau bon de commande (opération CREATE).

        Collaborateur_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête POST.

        col_serializer = BondecommandeSerializer(data=Collaborateur_data)
        # Sérialise les données du bon de commande pour les valider et les sauvegarder.

        if col_serializer.is_valid():
            # Vérifie si les données sérialisées sont valides.

            bdc = col_serializer.save()
            # Sauvegarde le bon de commande dans la base de données.

            # Send notifications to consultant, ESN, and commercial when BDC is created
            try:
                candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                project_title = appel_offre.titre
                bdc_number = bdc.numero_bdc or f"BDC-{bdc.id_bdc}"
                
                # Get client info
                try:
                    client = Client.objects.get(ID_clt=appel_offre.client_id)
                    client_name = client.raison_sociale
                except:
                    client_name = "Client"
                
                # Notification to consultant
                if candidature.id_consultant:
                    # Format date if available
                    date_demarrage = ""
                    if bdc.date_debut:
                        try:
                            date_demarrage = bdc.date_debut.strftime("%d/%m/%Y")
                        except:
                            date_demarrage = str(bdc.date_debut)
                    
                    consultant_msg = (
                        f"Vous avez été positionné sur un nouveau projet : \"{project_title}\""
                        f"{', date de démarrage le ' + date_demarrage if date_demarrage else ''}."
                    )
                    send_notification(
                        user_id=appel_offre.client_id,
                        dest_id=candidature.id_consultant,
                        message=consultant_msg,
                        categorie="CONSULTANT",
                        event="Création BDC",
                        event_id=bdc.id_bdc
                    )
                
                # Notification to ESN
                if ENABLE_BDC_CREATION_ESN_NOTIFICATION and candidature.esn_id:
                    esn_msg = (
                        f"Un nouveau bon de commande ({bdc_number}) a été créé pour le projet <strong>{project_title}</strong> par {client_name}. "
                        f'<a href="/interface-en?menu=Liste-BDC" class="notification-link">Voir les BDC</a>'
                    )
                    send_notification(
                        user_id=appel_offre.client_id,
                        dest_id=candidature.esn_id,
                        message=esn_msg,
                        categorie="ESN",
                        event="Création BDC",
                        event_id=bdc.id_bdc
                    )
                
                # Notification to commercial
                if candidature.commercial_id:
                    commercial_msg = (
                        f"Un nouveau bon de commande ({bdc_number}) a été créé pour le projet <strong>{project_title}</strong> par {client_name}. "
                        f'<a href="/interface-co?menu=Liste-BDC" class="notification-link">Voir les BDC</a>'
                    )
                    send_notification(
                        user_id=appel_offre.client_id,
                        dest_id=candidature.commercial_id,
                        message=commercial_msg,
                        categorie="COMMERCIAL",
                        event="Création BDC",
                        event_id=bdc.id_bdc
                    )
                
                # Notification to all admins
                try:
                    admins = Admin.objects.all()
                    
                    # Get ESN name if available
                    esn_name = "ESN"
                    if candidature.esn_id:
                        try:
                            esn = ESN.objects.get(ID_ESN=candidature.esn_id)
                            esn_name = esn.Raison_sociale
                        except ESN.DoesNotExist:
                            esn_name = f"ESN (ID: {candidature.esn_id})"
                    
                    # Get consultant name if available
                    consultant_info = ""
                    if candidature.id_consultant:
                        try:
                            consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
                            consultant_info = f" - Consultant: {consultant.Nom} {consultant.Prenom}"
                        except Collaborateur.DoesNotExist:
                            pass
                    
                    admin_msg = (
                        f"Nouveau bon de commande créé: {bdc_number} pour le projet \"{project_title}\". "
                        f"Client: {client_name}, ESN: {esn_name}{consultant_info}. "
                        f'<a href="/interface-ad?menu=Liste-BDC" style="color: #1890ff; text-decoration: underline;">Voir les détails</a>'
                    )
                    
                    for admin in admins:
                        send_notification(
                            user_id=appel_offre.client_id,
                            dest_id=admin.ID_Admin,
                            message=admin_msg,
                            categorie="Admin",
                            event="Création BDC",
                            event_id=bdc.id_bdc
                        )
                except Exception as admin_notif_error:
                    print(f"Erreur lors de l'envoi des notifications admin BDC: {str(admin_notif_error)}")
                    
            except Exception as notif_error:
                print(f"Erreur lors de l'envoi des notifications BDC: {str(notif_error)}")

            return JsonResponse({
                "status": True,
                "msg": "Added Successfully!!",
                "errors": col_serializer.errors,
                "id": col_serializer.data["id_bdc"],  # Include the ID of the created Bondecommande
            }, safe=False)
            # Retourne une réponse JSON indiquant que le bon de commande a été ajouté avec succès.

        return JsonResponse({
            "status": False,
            "msg": "Failed to Add",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'PUT':
        # Gère la mise à jour d'un bon de commande existant (opération UPDATE).

        col_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête PUT.

        col = Bondecommande.objects.get(id_bdc=col_data["id_bdc"])
        # Récupère le bon de commande à mettre à jour en fonction de son identifiant.

        col_serializer = BondecommandeSerializer(col, data=col_data)
        # Sérialise les données mises à jour pour les valider.

        if col_serializer.is_valid():
            # Vérifie si les données mises à jour sont valides.

            col_serializer.save()
            # Sauvegarde les modifications dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "updated Successfully!!",
                "errors": col_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que la mise à jour a réussi.

        return JsonResponse({
            "status": False,
            "msg": "Failed to update",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'DELETE':
        # Gère la suppression d'un bon de commande (opération DELETE).

        col = Bondecommande.objects.get(id_bdc=id)
        # Récupère le bon de commande à supprimer en fonction de son identifiant fourni dans l'URL.

        col.delete()
        # Supprime le bon de commande de la base de données.

        return JsonResponse("Deleted Successfully!!", safe=False)
        # Retourne une réponse JSON indiquant que le bon de commande a été supprimé avec succès.

@csrf_exempt
def Contrat_view(request, id=0):
    # Vue permettant de gérer les contrats avec des opérations CRUD (Create, Read, Update, Delete).

    if request.method == 'GET':
        # Gère la récupération des contrats (opération READ).

        # Récupère tous les contrats depuis la base de données.
        colls = Contrat.objects.filter().order_by('-id_contrat')
        # Récupère tous les contrats depuis la base de données en ordre décroissant.

        Collaborateur_serializer = ContratSerializer(colls, many=True)
        # Sérialise les contrats récupérés pour les convertir en JSON.

        data = list(Collaborateur_serializer.data)

            # Ajoute chaque contrat à la liste `data`.

        return JsonResponse({"total": len(data), "data": data}, safe=False)
        # Retourne une réponse JSON contenant le nombre total de contrats et leurs données.

    if request.method == 'POST':
        # Gère la création d'un nouveau contrat (opération CREATE).

        Collaborateur_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête POST.

        col_serializer = ContratSerializer(data=Collaborateur_data)
        # Sérialise les données du contrat pour les valider et les sauvegarder.

        if col_serializer.is_valid():
            # Vérifie si les données sérialisées sont valides.

            col_serializer.save()
            # Sauvegarde le contrat dans la base de données.
            candidature_id = col_serializer.data["candidature_id"]
            esn_id = None
            try:
                candidature = Candidature.objects.get(id_cd=candidature_id)
                esn_id = candidature.esn_id
            except Candidature.DoesNotExist:
                esn_id = None

            return JsonResponse({
                "status": True,
                "msg": "Added Successfully!!",
                "errors": col_serializer.errors,
                "id_contrat": col_serializer.data["id_contrat"],
                "esn_id" : esn_id
            }, safe=False)
            # Retourne une réponse JSON indiquant que le contrat a été ajouté avec succès.

        return JsonResponse({
            "status": False,
            "msg": "Failed to Add",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'PUT':
        # Gère la mise à jour d'un contrat existant (opération UPDATE).

        col_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête PUT.

        col = Contrat.objects.get(id_contrat=col_data["id_contrat"])
        # Récupère le contrat à mettre à jour en fonction de son identifiant.

        col_serializer = ContratSerializer(col, data=col_data)
        # Sérialise les données mises à jour pour les valider.

        if col_serializer.is_valid():
            # Vérifie si les données mises à jour sont valides.

            col_serializer.save()
            # Sauvegarde les modifications dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "updated Successfully!!",
                "errors": col_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que la mise à jour a réussi.

        return JsonResponse({
            "status": False,
            "msg": "Failed to update",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'DELETE':
        # Gère la suppression d'un contrat (opération DELETE).

        col = Contrat.objects.get(id_contrat=id)
        # Récupère le contrat à supprimer en fonction de son identifiant fourni dans l'URL.

        col.delete()
        # Supprime le contrat de la base de données.

        return JsonResponse("Deleted Successfully!!", safe=False)
        # Retourne une réponse JSON indiquant que le contrat a été supprimé avec succès.
    
   
@csrf_exempt
def partenariats_view(request, id=0):
    # Vue permettant de gérer les partenariats avec des opérations CRUD (Create, Read, Update, Delete).

    if request.method == 'GET':
        # Gère la récupération des partenariats (opération READ).

        colls = Partenariat1.objects.filter()
        # Récupère tous les partenariats dans la base de données.

        Collaborateur_serializer = Partenariat1Serializer(colls, many=True)
        # Sérialise les partenariats récupérés pour les convertir en JSON.

        data = []
        # Initialise une liste pour stocker les données des partenariats.

        for col in Collaborateur_serializer.data:
            # Parcourt les partenariats sérialisés.
            data.append(col)
            # Ajoute chaque partenariat à la liste `data`.

        return JsonResponse({"total": len(data), "data": data}, safe=False)
        # Retourne une réponse JSON contenant le nombre total de partenariats et leurs données.

    if request.method == 'POST':
        # Gère la création d'un nouveau partenariat (opération CREATE).

        Collaborateur_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête POST.

        col_serializer = Partenariat1Serializer(data=Collaborateur_data)
        # Sérialise les données du partenariat pour les valider et les sauvegarder.

        if col_serializer.is_valid():
            # Vérifie si les données sérialisées sont valides.

            col_serializer.save()
            # Sauvegarde le partenariat dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "Added Successfully!!",
                "errors": col_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que le partenariat a été ajouté avec succès.

        return JsonResponse({
            "status": False,
            "msg": "Failed to Add",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'PUT':
        # Gère la mise à jour d'un partenariat existant (opération UPDATE).

        col_data = JSONParser().parse(request)
        # Parse les données JSON envoyées dans la requête PUT.

        col = Partenariat1.objects.get(id_part=col_data["id_part"])
        # Récupère le partenariat à mettre à jour en fonction de son identifiant.

        col_serializer = Partenariat1Serializer(col, data=col_data)
        # Sérialise les données mises à jour pour les valider.

        if col_serializer.is_valid():
            # Vérifie si les données mises à jour sont valides.

            col_serializer.save()
            # Sauvegarde les modifications dans la base de données.

            return JsonResponse({
                "status": True,
                "msg": "updated Successfully!!",
                "errors": col_serializer.errors
            }, safe=False)
            # Retourne une réponse JSON indiquant que la mise à jour a réussi.

        return JsonResponse({
            "status": False,
            "msg": "Failed to update",
            "errors": col_serializer.errors
        }, safe=False)
        # Retourne une réponse JSON contenant les erreurs si la validation échoue.

    if request.method == 'DELETE':
        # Gère la suppression d'un partenariat (opération DELETE).

        col = Partenariat1.objects.get(id_part=id)
        # Récupère le partenariat à supprimer en fonction de son identifiant fourni dans l'URL.

        col.delete()
        # Supprime le partenariat de la base de données.

        return JsonResponse("Deleted Successfully!!", safe=False)
        # Retourne une réponse JSON indiquant que le partenariat a été supprimé avec succès.
@csrf_exempt
def Client_by_id(request):
    if request.method == 'GET':
        clientId = request.GET["clientId"]
        client = Client.objects.filter(ID_clt=clientId)
       
        client_serializer = ClientSerializer(client, many=True)
        data = []
        for S in client_serializer.data:
            data.append(S)
        return JsonResponse({"total": len(data),"data": data}, safe=False)
    
@csrf_exempt
def apprlOffre_by_idClient(request):
    if request.method == 'GET':
        clientId = request.GET["clientId"]
        appel = AppelOffre.objects.filter(client_id=clientId)
       
        appelOffre_serializer = AppelOffreSerializer(appel, many=True)
        data = []
        for S in appelOffre_serializer.data:
            data.append(S)
        return JsonResponse({"total": len(data),"data": data}, safe=False)

@csrf_exempt
def get_candidatures_by_esn(request):
    if request.method == 'GET':
        esn_id = request.GET.get("esn_id")
        
        if not esn_id:
            return JsonResponse({"status": False, "message": "esn_id manquant"}, safe=False)

        # Filtrer les candidatures associées à l'ESN
        candidatures = Candidature.objects.filter(esn_id=esn_id)

        if not candidatures.exists():
            return JsonResponse({"status": False, "message": "Aucune candidature trouvée pour cet ESN"}, safe=False)

        # Sérialiser les données des candidatures
        candidature_serializer = CandidatureSerializer(candidatures, many=True)

        return JsonResponse({"status": True, "data": candidature_serializer.data}, safe=False)

    return JsonResponse({"status": False, "message": "Invalid request method"}, safe=False)


@csrf_exempt
def get_collaborateur_by_id(request, collaborateur_id):
    if request.method == 'GET':
        try:
            # Get collaborateur by ID
            collaborateur = Collaborateur.objects.get(ID_collab=collaborateur_id)
            
            # Serialize the collaborateur data
            collaborateur_serializer = CollaborateurSerializer(collaborateur)

            # Fetch related AO data and Candidature data
            ao_data = []
            candidature_data = []
            candidatures = Candidature.objects.filter(id_consultant=collaborateur_id)
            for candidature in candidatures:
                try:
                    # Serialize Candidature data
                    candidature_serializer = CandidatureSerializer(candidature)
                    candidature_data.append(candidature_serializer.data)

                    # Fetch and serialize AO data
                    ao = AppelOffre.objects.get(id=candidature.AO_id)
                    ao_serializer = AppelOffreSerializer(ao)
                    ao_data.append(ao_serializer.data)
                except AppelOffre.DoesNotExist:
                    continue

            return JsonResponse({
                "status": True,
                "data": collaborateur_serializer.data,
                "linked_candidatures": candidature_data,
                "linked_ao": ao_data
            }, safe=False)

        except Collaborateur.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "Collaborateur not found"
            }, safe=False)
        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False)

    return JsonResponse({
        "status": False,
        "message": "Invalid request method"
    }, safe=False)

@csrf_exempt
def get_candidatures_by_client(request):
    if request.method == 'GET':
        client_id = request.GET.get("client_id")
        
        if not client_id:
            return JsonResponse({"status": False, "message": "client_id manquant"}, safe=False)

        # Récupérer les appels d'offre associés au client
        appels_offre = AppelOffre.objects.filter(client_id=client_id)
        if not appels_offre.exists():
            return JsonResponse({"status": False, "message": "Aucun appel d'offre trouvé pour ce client"}, safe=False)

        # Récupérer les candidatures liées à ces appels d'offre
        candidatures = Candidature.objects.filter(AO_id__in=appels_offre.values_list('id', flat=True))
        if not candidatures.exists():
            return JsonResponse({"status": False, "message": "Aucune candidature trouvée pour ce client"}, safe=False)

        # Sérialiser les données des candidatures
        candidature_serializer = CandidatureSerializer(candidatures, many=True)

        return JsonResponse({"status": True, "data": candidature_serializer.data}, safe=False)

    return JsonResponse({"status": False, "message": "Invalid request method"}, safe=False)

@csrf_exempt
def notification_by_type(request):
    if request.method == 'GET':
        notif_type = request.GET.get("type")  # Use `get` to avoid potential `KeyError`
        user_id = request.GET.get("id")

        if not notif_type or not user_id:  # Validate input
            return JsonResponse({"error": "Both 'type' and 'id' are required."}, status=400)

        try:
            dest_id = int(user_id)
        except (TypeError, ValueError):
            return JsonResponse({"error": "'id' must be an integer."}, status=400)

        # Filter notifications by type and destination ID
        notif_queryset = Notification.objects.filter(dest_id=dest_id)
        if notif_type:
            notif_queryset = notif_queryset.filter(categorie__iexact=notif_type)

        notif = notif_queryset.order_by('-id')
        notif_serializer = NotificationSerializer(notif, many=True)
        data = notif_serializer.data  # No need to iterate manually

        return JsonResponse({"total": len(data), "data": data}, safe=False)
    
    # Handle unsupported methods
    return JsonResponse({"error": "Only GET method is allowed."}, status=405)


def _resolve_notification_scope(payload):
    dest_id = (
        payload.get("destId")
        or payload.get("clientId")
        or payload.get("esnId")
        or payload.get("userId")
        or payload.get("id")
    )
    notif_type = payload.get("type") or payload.get("categorie") or payload.get("category")

    if dest_id is None:
        raise ValueError("Destination identifier is required")

    try:
        dest_id = int(dest_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Destination identifier must be an integer") from exc

    return dest_id, notif_type


@csrf_exempt
def mark_notification_as_read(request, notification_id):
    if request.method != 'PUT':
        return JsonResponse({"error": "Only PUT method is allowed."}, status=405)

    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return JsonResponse({"status": False, "message": "Notification not found"}, status=404)

    notification.status = "Read"
    notification.save(update_fields=["status"])
    return JsonResponse({"status": True, "message": "Notification marked as read"}, status=200)


@csrf_exempt
def mark_all_notifications_as_read(request):
    if request.method != 'PUT':
        return JsonResponse({"error": "Only PUT method is allowed."}, status=405)

    try:
        payload = JSONParser().parse(request)
    except Exception:
        payload = {}

    try:
        dest_id, notif_type = _resolve_notification_scope(payload)
    except ValueError as exc:
        return JsonResponse({"status": False, "message": str(exc)}, status=400)

    queryset = Notification.objects.filter(dest_id=dest_id)
    if notif_type:
        queryset = queryset.filter(categorie__iexact=notif_type)

    updated = queryset.update(status="Read")
    return JsonResponse({"status": True, "updated": updated}, status=200)


@csrf_exempt
def clear_all_notifications(request):
    if request.method != 'DELETE':
        return JsonResponse({"error": "Only DELETE method is allowed."}, status=405)

    try:
        payload = JSONParser().parse(request)
    except Exception:
        payload = {}

    try:
        dest_id, notif_type = _resolve_notification_scope(payload)
    except ValueError as exc:
        return JsonResponse({"status": False, "message": str(exc)}, status=400)

    queryset = Notification.objects.filter(dest_id=dest_id)
    if notif_type:
        queryset = queryset.filter(categorie__iexact=notif_type)

    deleted, _ = queryset.delete()
    return JsonResponse({"status": True, "deleted": deleted}, status=200)

@csrf_exempt
def DocumentClient(request):
    if request.method == 'GET':
        ClientId = request.GET["ClientId"]
        doc = Doc_clt.objects.filter(ID_CLT=ClientId)
       
        doc_serializer = DocumentSerializer(doc, many=True)
        data = []
        for S in doc_serializer.data:
            data.append(S)
        return JsonResponse({"total": len(data),"data": data}, safe=False)
    
@csrf_exempt
def DocumentESNs(request):
    if request.method == 'GET':
        esnId = request.GET["esnId"]
        doc = DocumentESN.objects.filter(ID_ESN=esnId)
       
        doc_serializer = DocumentESNSerializer(doc, many=True)
        data = []
        for S in doc_serializer.data:
            data.append(S)
        return JsonResponse({"total": len(data),"data": data}, safe=False)
    
# @csrf_exempt
# def PartenariatESNs(request):
#     if request.method == 'GET':
#         esnId = request.GET["esnId"]
#         parte = Partenariat1.objects.filter(id_esn=esnId)
       
#         part_serializer = Partenariat1Serializer(parte, many=True)
#         data = []
#         for S in part_serializer.data:
#             data.append(S)
#         return JsonResponse({"total": len(data),"data": data}, safe=False)
@csrf_exempt
def get_esn_partenariats(request):
    esn_id = request.GET.get("esn_id")
    
    if not esn_id:
        return JsonResponse({"status": False, "message": "esn_id manquant"}, safe=False, status=400)

    # Filtrer les partenariats associés à l'ESN
    partenariats = Partenariat1.objects.filter(id_esn=esn_id)

    # Sérialiser les données des partenariats
    partenariat_serializer = Partenariat1Serializer(partenariats, many=True)

    return JsonResponse({"status": True, "data": partenariat_serializer.data}, safe=False)

@csrf_exempt
def PartenariatESNs(request):
    if request.method == 'GET':
        try:
            esnId = request.GET["esnId"]
            

            if not esnId:
                return JsonResponse({"status": False, "message": "clientId requis"}, safe=False)
            

            # Filtrer les partenariats pour le client donné et le nom de l'ESN
            partenariats = Partenariat1.objects.filter(id_esn=esnId)

            # Ajouter un filtre supplémentaire pour le nom de l'ESN
            data = []
            for partenariat in partenariats:
                try:
                    clt = Client.objects.get(ID_clt=partenariat.id_client)
                    data.append({
                        "id_part": partenariat.id_part,
                        "id_client": partenariat.id_client,
                        "id_esn": partenariat.id_esn,
                        "client_name": clt.raison_sociale,
                        "date_debut": partenariat.date_debut,
                        "date_fin": partenariat.date_fin,
                        "statut": partenariat.statut,
                        "description": partenariat.description,
                        "categorie": partenariat.categorie,
                    })
                except ESN.DoesNotExist:
                    continue  # Si l'ESN ne correspond pas, passez au suivant

            return JsonResponse({"total": len(data), "data": data}, safe=False)

        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, safe=False)   
        
# @csrf_exempt
# def PartenariatClients(request):
#     if request.method == 'GET':
#         clientId = request.GET["clientId"]
#         parte = Partenariat1.objects.filter(id_client=clientId)
       
#         part_serializer = Partenariat1Serializer(parte, many=True)
#         data = []
#         for S in part_serializer.data:
#             data.append(S)
#         return JsonResponse({"total": len(data),"data": data}, safe=False)
    
@csrf_exempt
def PartenariatClients(request):
    if request.method == 'GET':
        try:
            clientId = request.GET.get("clientId")
         

            if not clientId:
                return JsonResponse({"status": False, "message": "clientId requis"}, safe=False)
           

            # Filtrer les partenariats pour le client donné et le nom de l'ESN
            partenariats = Partenariat1.objects.filter(id_client=clientId)

            # Ajouter un filtre supplémentaire pour le nom de l'ESN
            data = []
            for partenariat in partenariats:
                try:
                    esn = ESN.objects.get(ID_ESN=partenariat.id_esn)
                    data.append({
                        "id_part": partenariat.id_part,
                        "id_client": partenariat.id_client,
                        "id_esn": partenariat.id_esn,
                        "esn_name": esn.Raison_sociale,
                        "date_debut": partenariat.date_debut,
                        "date_fin": partenariat.date_fin,
                        "statut": partenariat.statut,
                        "description": partenariat.description,
                        "categorie": partenariat.categorie,
                    })
                except ESN.DoesNotExist:
                    continue  # Si l'ESN ne correspond pas, passez au suivant

            return JsonResponse({"total": len(data), "data": data}, safe=False)

        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, safe=False)


def get_candidatures_by_project_and_esn(request):
    esn_id = request.GET.get("esn_id")
    project_id = request.GET.get("project_id")
    
    if not esn_id:
        return JsonResponse({"status": False, "message": "esn_id manquant"}, safe=False)
    
    if not project_id:
        return JsonResponse({"status": False, "message": "project_id manquant"}, safe=False)

    # Filtrer les candidatures associées à l'ESN et au projet
    candidatures = Candidature.objects.filter(esn_id=esn_id, AO_id=project_id)
    # Sérialiser les données des candidatures
    candidature_serializer = CandidatureSerializer(candidatures, many=True)

    return JsonResponse({"status": True, "data": candidature_serializer.data}, safe=False)


@csrf_exempt
def get_candidatures_by_project_and_client(request):
    project_id = request.GET.get("project_id")
    client_id = request.GET.get("client_id")
    
    if not project_id:
        return JsonResponse({"status": False, "message": "project_id manquant"}, safe=False)
    
    if not client_id:
        return JsonResponse({"status": False, "message": "client_id manquant"}, safe=False)

    # Filtrer les appels d'offre associés au client et au projet
    appels_offre = AppelOffre.objects.filter(id=project_id, client_id=client_id)

    if not appels_offre.exists():
        return JsonResponse({"status": False, "message": "Aucun appel d'offre trouvé pour ce client et ce projet"}, safe=False)

    # Filtrer les candidatures associées aux appels d'offre trouvés
    candidatures = Candidature.objects.all().filter(AO_id=project_id)

    if not candidatures.exists():
        return JsonResponse({"status": False, "message": "Aucune candidature trouvée pour ce client et ce projet"}, safe=False)

    # Sérialiser les données des candidatures
    candidature_serializer = CandidatureSerializer(candidatures, many=True)
    
    # Enrichir les données avec les CV des collaborateurs
    enriched_data = []
    for candidature in candidature_serializer.data:
        # Récupérer les informations du collaborateur, y compris son CV
        try:
            collaborateur = Collaborateur.objects.get(ID_collab=candidature["id_consultant"])
            collaborateur_serializer = CollaborateurSerializer(collaborateur)
            
            # Créer une copie de la candidature avec les données du collaborateur ajoutées
            candidature_data = dict(candidature)
            candidature_data["collaborateur"] = collaborateur_serializer.data
            
            enriched_data.append(candidature_data)
        except Collaborateur.DoesNotExist:
            # Si le collaborateur n'existe pas, ajouter la candidature sans informations supplémentaires
            enriched_data.append(candidature)

    return JsonResponse({"status": True, "data": enriched_data}, safe=False)

@csrf_exempt
def clients_par_esn(request):
    if request.method == 'GET':
        try:
            # Récupération de l'identifiant de l'ESN
            esn_id = request.GET.get("esn_id")
            if not esn_id:
                return JsonResponse({"status": False, "message": "esn_id manquant"}, safe=False)

            # Filtrer les candidatures associées à l'ESN
            candidatures = Candidature.objects.filter(esn_id=esn_id)
            # if not candidatures.exists():
            #     return JsonResponse({"status": False, "message": "Aucune candidature trouvée pour cet ESN"}, safe=False)

            # Extraire les IDs des appels d'offres associés
            appels_offres_ids = candidatures.values_list('AO_id', flat=True)

            # Filtrer les appels d'offres associés
            appels_offres = AppelOffre.objects.filter(id__in=appels_offres_ids)
            # if not appels_offres.exists():
            #     return JsonResponse({"status": False, "message": "Aucun appel d'offre trouvé"}, safe=False)

            # Extraire les IDs des clients associés
            clients_ids = appels_offres.values_list('client_id', flat=True).distinct()

            # Filtrer les clients associés
            clients = Client.objects.filter(ID_clt__in=clients_ids)

            # Sérialiser les données des clients
            client_serializer = ClientSerializer(clients, many=True)
            return JsonResponse({"total": len(client_serializer.data), "data": client_serializer.data}, safe=False)

        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, safe=False)

    esn_id = request.GET.get("esn_id")
    if not esn_id:
        return JsonResponse({"status": False, "message": "esn_id manquant"}, safe=False)

    # Filtrer les candidatures associées à l'ESN
    candidatures = Candidature.objects.filter(esn_id=esn_id)

    # Sérialiser les données des consultants
    consultant_serializer = CandidatureSerializer(candidatures, many=True)

    return JsonResponse({"status": True, "consultants": consultant_serializer.data}, safe=False)

@csrf_exempt
def consultants_par_client(request):
    if request.method == 'GET':
        try:
            # Récupération de l'identifiant du client
            client_id = request.GET.get("client_id")
            if not client_id:
                return JsonResponse({"status": False, "message": "client_id manquant"}, safe=False)

            # Filtrer les appels d'offres associés au client
            appels_offres = AppelOffre.objects.filter(client_id=client_id)
            if not appels_offres.exists():
                return JsonResponse({"status": False, "message": "Aucun appel d'offre trouvé pour ce client"}, safe=False)

            # Extraire les IDs des appels d'offres
            appels_offres_ids = appels_offres.values_list('id', flat=True)

            # Filtrer les candidatures liées à ces appels d'offres
            candidatures = Candidature.objects.filter(AO_id__in=appels_offres_ids)
            if not candidatures.exists():
                return JsonResponse({"status": False, "message": "Aucune candidature trouvée"}, safe=False)

            # Extraire les IDs des consultants associés
            consultants_ids = candidatures.values_list('id_consultant', flat=True).distinct()

            # Filtrer les consultants associés
            consultants = Collaborateur.objects.filter(ID_collab__in=consultants_ids)

            # Sérialiser les données des consultants
            consultant_serializer = CollaborateurSerializer(consultants, many=True)
            return JsonResponse({"total": len(consultant_serializer.data), "data": consultant_serializer.data}, safe=False)

        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, safe=False)

    
@csrf_exempt
def candidatures_par_client(request):
    if request.method == 'GET':
        try:
            # Récupération de l'identifiant du client
            client_id = request.GET.get("client_id")
            if not client_id:
                return JsonResponse({"status": False, "message": "client_id manquant"}, safe=False)

            # Filtrer les appels d'offres associés au client
            appels_offres = AppelOffre.objects.filter(client_id=client_id)
            if not appels_offres.exists():
                return JsonResponse({"status": False, "message": "Aucun appel d'offre trouvé pour ce client"}, safe=False)

            # Extraire les IDs des appels d'offres
            appels_offres_ids = appels_offres.values_list('id', flat=True)

            # Filtrer les candidatures liées à ces appels d'offres
            candidatures = Candidature.objects.filter(AO_id__in=appels_offres_ids)
            if not candidatures.exists():
                return JsonResponse({"status": False, "message": "Aucune candidature trouvée"}, safe=False)

            # Sérialiser les candidatures
            candidatures_serializer = CandidatureSerializer(candidatures, many=True)
            return JsonResponse({"total": len(candidatures_serializer.data), "data": candidatures_serializer.data}, safe=False)

        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
        
@csrf_exempt
def consultants_par_esn1(request):
    if request.method == 'GET':
            esn_id = request.GET.get("esn_id")
    
            if not esn_id:
                return JsonResponse({"status": False, "message": "esn_id manquant"}, safe=False, status=400)

            # Filtrer les candidatures associées à l'ESN
            candidatures = Collaborateur.objects.filter(ID_ESN=esn_id)

            # Sérialiser les données des candidatures
            candidature_serializer = CollaborateurSerializer(candidatures, many=True)

            return JsonResponse({"status": True, "data": candidature_serializer.data}, safe=False)

@csrf_exempt
def consultants_par_esn_et_projet(request):
    if request.method == 'GET':
        esn_id = request.GET.get("esn_id")
        project_id = request.GET.get("project_id")
        
        if not esn_id:
            return JsonResponse({"status": False, "message": "esn_id manquant"}, safe=False, status=400)
        
        if not project_id:
            return JsonResponse({"status": False, "message": "project_id manquant"}, safe=False, status=400)

        # Obtenir les consultants qui ont déjà soumis une candidature pour ce projet et cet ESN
        submitted_consultants = Candidature.objects.filter(esn_id=esn_id, AO_id=project_id).values_list('id_consultant', flat=True)

        # Obtenir les consultants qui n'ont pas encore soumis de candidature pour ce projet et cet ESN
        consultants = Collaborateur.objects.filter(ID_ESN=esn_id).exclude(ID_collab__in=submitted_consultants)

        # Sérialiser les données des consultants
        consultant_serializer = CollaborateurSerializer(consultants, many=True)

        return JsonResponse({"status": True, "data": consultant_serializer.data}, safe=False)

@csrf_exempt
def candidatures_par_appel_offre(request):
    if request.method == 'GET':
        try:
            # Récupération de l'identifiant de l'appel d'offre depuis les paramètres GET
            AO_id = request.GET.get("AO_id")
            if not AO_id:
                return JsonResponse({"status": False, "message": "AO_id manquant"}, safe=False)

            # Filtrer les candidatures associées à l'appel d'offre
            candidatures = Candidature.objects.filter(AO_id=AO_id)
            if not candidatures.exists():
                return JsonResponse({"status": False, "message": "Aucune candidature trouvée pour cet appel d'offre"}, safe=False)

            # Sérialiser les données des candidatures
            candidatures_serializer = CandidatureSerializer(candidatures, many=True)
            return JsonResponse({"total": len(candidatures_serializer.data), "data": candidatures_serializer.data}, safe=False)

        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
        
@csrf_exempt
def get_candidates(request):
    if request.method == 'GET':
        try:
            # Récupération des paramètres clientId et appelOffreId depuis les paramètres GET
            client_id = request.GET.get("clientId")
            appel_offre_id = request.GET.get("appelOffreId")

            # Vérification des paramètres requis
            if not client_id:
                return JsonResponse({"status": False, "message": "clientId manquant"}, safe=False)
            if not appel_offre_id:
                return JsonResponse({"status": False, "message": "appelOffreId manquant"}, safe=False)

            # Vérification que l'appel d'offre appartient au client
            appel_offre = AppelOffre.objects.filter(client_id=client_id, id=appel_offre_id).first()
            if not appel_offre:
                return JsonResponse({"status": False, "message": "Aucun appel d'offre trouvé pour ce client"}, safe=False)

            # Filtrer les candidatures associées à cet appel d'offre
            candidatures = Candidature.objects.filter(AO_id=appel_offre_id)
            if not candidatures.exists():
                return JsonResponse({"status": False, "message": "Aucune candidature trouvée"}, safe=False)

            # Sérialisation des données des candidatures
            candidatures_serializer = CandidatureSerializer(candidatures, many=True)
            return JsonResponse({"total": len(candidatures_serializer.data), "data": candidatures_serializer.data}, safe=False)

        except Exception as e:
            # Gestion des exceptions générales
            return JsonResponse({"status": False, "message": str(e)}, safe=False)



@csrf_exempt
def get_contract(request):
    if request.method == 'GET':
        try:
            # Récupération des paramètres
            client_id = request.GET.get('clientId')
            esn_id = request.GET.get('esnId')

            # Validation des paramètres
            if not client_id or not esn_id:
                return JsonResponse({"status": False, "message": "clientId et esnId requis"}, safe=False)

            # Rechercher les appels d'offres liés au client
            appels_offres = AppelOffre.objects.filter(client_id=client_id)
            if not appels_offres.exists():
                return JsonResponse({"status": False, "message": "Aucun appel d'offre trouvé pour ce client"}, safe=False)

            # Récupérer les IDs des appels d'offres
            appels_offres_ids = appels_offres.values_list('id', flat=True)

            # Filtrer les candidatures liées à ces appels d'offres et à l'ESN
            candidatures = Candidature.objects.filter(AO_id__in=appels_offres_ids, esn_id=esn_id)
            if not candidatures.exists():
                return JsonResponse({"status": False, "message": "Aucune candidature trouvée pour cette combinaison client et ESN"}, safe=False)

            # Récupérer les IDs des candidatures
            candidatures_ids = candidatures.values_list('id_cd', flat=True)

            # Rechercher les contrats liés à ces candidatures
            contrats = Contrat.objects.filter(candidature_id__in=candidatures_ids)
            if not contrats.exists():
                return JsonResponse({"status": False, "message": "Aucun contrat trouvé pour cette combinaison client et ESN"}, safe=False)

            # Sérialiser les contrats
            contrats = Contrat.objects.filter(candidature_id__in=candidatures.values_list('id_cd', flat=True)).order_by('-id_contrat')
            contrats_serializer = ContratSerializer(contrats, many=True)
            return JsonResponse({"total": len(contrats_serializer.data), "data": contrats_serializer.data}, safe=False)

        except Exception as e:
            # Gestion des erreurs
            return JsonResponse({"status": False, "message": str(e)}, safe=False)

@csrf_exempt
def get_combined_info(request, bon_commande_id):
    if request.method == 'GET':
        try:
            # Get bon de commande
            bon_commande = Bondecommande.objects.get(id_bdc=bon_commande_id)
            bon_commande_data = BondecommandeSerializer(bon_commande).data

            # Get related candidature
            candidature = Candidature.objects.get(id_cd=bon_commande.candidature_id)
            candidature_data = CandidatureSerializer(candidature).data

            # Get related appel offre
            appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
            appel_offre_data = AppelOffreSerializer(appel_offre).data

            # Combine all data
            combined_data = {
                "bon_commande": bon_commande_data,
                "candidature": candidature_data,
                "appel_offre": appel_offre_data
            }

            return JsonResponse({
                "status": True,
                "data": combined_data
            }, safe=False)

        except Bondecommande.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "Bon de commande not found"
            }, safe=False)
        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False)

    return JsonResponse({
        "status": False,
        "message": "Invalid request method"
    }, safe=False)


@csrf_exempt
def check_esn_status(request):
    if request.method == 'GET':
        try:
            # Get ESN ID from request parameters
            esn_id = request.GET.get('esn_id')
            
            # Validate the parameter
            if not esn_id:
                return JsonResponse({
                    "status": False, 
                    "message": "esn_id parameter is required"
                }, safe=False)
                
            # Check if ESN exists
            try:
                esn = ESN.objects.get(ID_ESN=esn_id)
                            # Simple activity check - if ESN has any candidatures, it's considered active
                is_active = esn.Statut.lower() == "actif"
                print(esn.Statut.lower())
                return JsonResponse({
                    "status": True,
                    "is_active": is_active
                }, safe=False)

            except ESN.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": "ESN not found"
                }, safe=False)
            
            
        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False)
    
    return JsonResponse({
        "status": False,
        "message": "Invalid request method"
    }, safe=False)

@csrf_exempt
def get_bon_de_commande_by_client(request):
    if request.method == 'GET':
        try:
            client_id = request.GET.get('client_id')

            if not client_id:
                return JsonResponse({"status": False, "message": "client_id requis"}, safe=False)

            appels_offres = AppelOffre.objects.filter(client_id=client_id)
            if not appels_offres.exists():
                return JsonResponse({"status": False, "message": "Aucun appel d'offre trouvé pour ce client"}, safe=False)

            appels_offres_ids = appels_offres.values_list('id', flat=True)

            candidatures = Candidature.objects.filter(AO_id__in=appels_offres_ids)
            if not candidatures.exists():
                return JsonResponse({"status": False, "message": "Aucune candidature trouvée pour ce client"}, safe=False)

            candidatures_ids = candidatures.values_list('id_cd', flat=True)

            # Add order_by to reverse the order
            bons_de_commande = Bondecommande.objects.filter(
                candidature_id__in=candidatures_ids
            ).order_by('-id_bdc')
            
            if not bons_de_commande.exists():
                return JsonResponse({"status": False, "message": "Aucun bon de commande trouvé pour ce client"}, safe=False)

            serializer = BondecommandeSerializer(bons_de_commande, many=True)
            
            # Enrich BDC data with project and consultant info
            enriched_data = []
            for bdc in serializer.data:
                bdc_copy = dict(bdc)
                try:
                    candidature = Candidature.objects.get(id_cd=bdc['candidature_id'])
                    appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                    collaborateur = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
                    
                    # Add project and consultant info
                    bdc_copy['appel_offre_titre'] = appel_offre.titre
                    bdc_copy['project_description'] = appel_offre.description
                    bdc_copy['collaboratorInfo'] = {
                        'nom': collaborateur.Nom,
                        'prenom': collaborateur.Prenom,
                        'poste': collaborateur.Poste
                    }
                    
                    # Add responsable_compte from candidature
                    bdc_copy['responsable_compte'] = candidature.responsable_compte
                    
                    # Add client and ESN info
                    try:
                        client = Client.objects.get(ID_clt=appel_offre.client_id)
                        bdc_copy['client_name'] = client.raison_sociale
                    except Client.DoesNotExist:
                        bdc_copy['client_name'] = None
                    
                    try:
                        esn = ESN.objects.get(ID_ESN=candidature.esn_id)
                        bdc_copy['esn_name'] = esn.Raison_sociale
                    except ESN.DoesNotExist:
                        bdc_copy['esn_name'] = None
                        
                except Exception as e:
                    # If enrichment fails for this BDC, keep it without extra info
                    pass
                
                enriched_data.append(bdc_copy)
            
            return JsonResponse({"total": len(enriched_data), "data": enriched_data}, safe=False)

        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
@csrf_exempt
def get_bon_de_commande_by_esn(request):
    if request.method == 'GET':
        try:
            # Récupération du esn_id depuis les paramètres de la requête
            esn_id = request.GET.get('esn_id')

            # Validation du paramètre
            if not esn_id:
                return JsonResponse({"status": False, "message": "esn_id requis"}, safe=False)

            # Trouver les candidatures liées à l'ESN
            candidatures = Candidature.objects.filter(esn_id=esn_id)
            if not candidatures.exists():
                return JsonResponse({"status": False, "message": "Aucune candidature trouvée pour cette ESN"}, safe=False)

            # Récupérer les IDs des candidatures
            candidatures_ids = candidatures.values_list('id_cd', flat=True)

            # Trouver les bons de commande associés aux candidatures de l'ESN
            bons_de_commande = Bondecommande.objects.filter(candidature_id__in=candidatures_ids)
            if not bons_de_commande.exists():
                return JsonResponse({"status": False, "message": "Aucun bon de commande trouvé pour cette ESN"}, safe=False)

            # Sérialiser les bons de commande
            serializer = BondecommandeSerializer(bons_de_commande, many=True)
            
            # Enrich BDC data with project and consultant info
            enriched_data = []
            for bdc in serializer.data:
                bdc_copy = dict(bdc)
                # Map statut to status for frontend consistency
                if 'statut' in bdc_copy:
                    bdc_copy['status'] = bdc_copy['statut']
                try:
                    candidature = Candidature.objects.get(id_cd=bdc['candidature_id'])
                    appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                    collaborateur = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
                    
                    # Add project and consultant info
                    bdc_copy['appel_offre_titre'] = appel_offre.titre
                    bdc_copy['project_description'] = appel_offre.description
                    bdc_copy['collaboratorInfo'] = {
                        'nom': collaborateur.Nom,
                        'prenom': collaborateur.Prenom,
                        'poste': collaborateur.Poste
                    }
                    
                    # Add client and ESN info
                    try:
                        client = Client.objects.get(ID_clt=appel_offre.client_id)
                        bdc_copy['client_name'] = client.raison_sociale
                    except Client.DoesNotExist:
                        bdc_copy['client_name'] = None
                    
                    try:
                        esn = ESN.objects.get(ID_ESN=candidature.esn_id)
                        bdc_copy['esn_name'] = esn.Raison_sociale
                    except ESN.DoesNotExist:
                        bdc_copy['esn_name'] = None
                        
                except Exception as e:
                    # If enrichment fails for this BDC, keep it without extra info
                    pass
                
                enriched_data.append(bdc_copy)
            
            return JsonResponse({"total": len(enriched_data), "data": enriched_data}, safe=False)

        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, safe=False)


def send_notification(*, message, categorie, dest_id=None, user_id=None, event=None, event_id=None, status=None):
    """Create and persist a notification with sensible defaults.

    Parameters
    ----------
    message: str
        Notification body (HTML allowed).
    categorie: str
        Logical category / audience (Admin, Client, ESN, Consultant, etc.).
    dest_id: Optional[int]
        Recipient identifier. If omitted, defaults to ``user_id``.
    user_id: Optional[int]
        Actor who triggered the event (used for auditing / filtering).
    event: Optional[str]
        Event code (CRA_VALIDATION, NDF, INVOICE_ACCEPTED, ...). Defaults to ``"GENERAL"``.
    event_id: Optional[int]
        Business identifier tied to the event (CRA id, NDF id, invoice id...). Defaults to ``0``.
    status: Optional[str]
        Explicit status override ("Read" / "Not_read"). Defaults to ``"Not_read"``.
    """

    resolved_dest = dest_id if dest_id is not None else user_id
    if resolved_dest is None:
        raise ValueError("dest_id or user_id must be provided to create a notification")

    notification = Notification(
        user_id=user_id,
        dest_id=resolved_dest,
        message=message,
        status=(status or "Not_read"),
        categorie=categorie.upper() if categorie else None,
        event=(event or "GENERAL"),
        event_id=event_id if event_id is not None else 0,
    )
    notification.save()
    return notification

@csrf_exempt
def notify_appel_offre(request):
    if request.method == 'POST':
        try:
            # Check if AO notifications are disabled
            if not ENABLE_AO_NOTIFICATIONS:
                return JsonResponse({
                    "status": True, 
                    "message": "AO notifications are disabled"
                }, safe=False)
            
            data = JSONParser().parse(request)
            client_id = data.get('client_id')
            appel_offre_id = data.get('appel_offre_id')

            if not client_id or not appel_offre_id:
                return JsonResponse({"status": False, "message": "client_id et appel_offre_id requis"}, safe=False)

            # Get detailed information about the AppelOffre and Client
            try:
                appel_offre = AppelOffre.objects.get(id=appel_offre_id)
                ao_title = appel_offre.titre
                ao_date_limite = appel_offre.date_limite
                
                client = Client.objects.get(ID_clt=client_id)
                client_name = client.raison_sociale
            except (AppelOffre.DoesNotExist, Client.DoesNotExist):
                ao_title = "sans titre"
                ao_date_limite = "inconnue"
                client_name = f"ID={client_id}"
                
            # Get all ESNs
            all_esns = ESN.objects.all()
            if not all_esns.exists():
                return JsonResponse({"status": True, "message": "Aucune ESN trouvée dans le système"}, safe=False)
                
            # Create detail link for client
            ao_detail_link_client = f"/interface-cl/appeldoffre/{appel_offre_id}"
                
            # Create notification for the client with HTML anchor tag
            message_client = (
                f"Votre appel d'offre \"{ao_title}\" (ID: {appel_offre_id}) a été publié avec succès. "
                f"Date limite: {ao_date_limite}. "
                f"Toutes les ESN ont été notifiées et peuvent maintenant soumettre leurs candidatures. "
                f"<a href='{ao_detail_link_client}' class='notification-link'>Cliquez ici pour voir les détails</a>"
            )
            
            send_notification(
                user_id=client_id,
                dest_id=client_id,
                message=message_client,
                categorie="Client",
                event="AO",
                event_id=appel_offre_id
            )
            
            # Create detail link for ESN
            ao_detail_link_esn = f"/interface-en/appeldoffre/{appel_offre_id}"
            
            # Send notifications to all ESNs with HTML anchor tags
            notifications_sent = 0
            for esn in all_esns:
                message_esn = (
                    f"Un nouvel appel d'offre \"{ao_title}\" (ID: {appel_offre_id}) "
                    f"a été publié par {client_name}. "
                    f"Date limite de soumission: {ao_date_limite}. "
                    f"<a href='{ao_detail_link_esn}' class='notification-link'>Consultez les détails et soumettez vos candidatures</a>"
                )
                
                send_notification(
                    user_id=client_id,
                    dest_id=esn.ID_ESN,
                    message=message_esn,
                    categorie="ESN",
                    event="AO",
                    event_id=appel_offre_id
                )
                notifications_sent += 1

            return JsonResponse({
                "status": True, 
                "message": f"Notifications envoyées au client et à {notifications_sent} ESNs."
            }, safe=False)

        except Exception as e:
            print(f"Erreur: {e}")
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
@csrf_exempt
def notify_reponse_appel_offre(request):
    if request.method == 'POST':
        try:
            # Check if AO notifications are disabled
            if not ENABLE_AO_NOTIFICATIONS:
                return JsonResponse({
                    "status": True, 
                    "message": "AO notifications are disabled"
                }, safe=False)
            
            data = JSONParser().parse(request)
            esn_id = data.get('esn_id')
            client_id = data.get('client_id')
            appel_offre_id = data.get('appel_offre_id')

            if not esn_id or not client_id or not appel_offre_id:
                return JsonResponse({"status": False, "message": "esn_id, client_id, et appel_offre_id requis"}, safe=False)

            # Get detailed information
            try:
                appel_offre = AppelOffre.objects.get(id=appel_offre_id)
                ao_title = appel_offre.titre
                
                esn = ESN.objects.get(ID_ESN=esn_id)
                esn_name = esn.Raison_sociale
                
                # Create detail link for client
                ao_detail_link = f"/interface-cl/appeldoffre/{appel_offre_id}"
                
                message = (
                    f"L'ESN {esn_name} a soumis une réponse à votre appel d'offre \"{ao_title}\" (ID: {appel_offre_id}). "
                    f"<a href='{ao_detail_link}' class='notification-link'>Consultez cette candidature et les autres réponses</a>"
                )
            except (AppelOffre.DoesNotExist, ESN.DoesNotExist):
                message = f"L'ESN {esn_id} a soumis une réponse à l'appel d'offre {appel_offre_id}."
            
            send_notification(
                user_id=esn_id, 
                dest_id=client_id, 
                message=message, 
                categorie="Client",
                event="Réponse à l'Appel d'Offre",
                event_id=appel_offre_id
            )

            return JsonResponse({"status": True, "message": "Notification envoyée au client."}, safe=False)

        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False)
@csrf_exempt
def notify_validation_candidature(request):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            client_id = data.get('client_id')
            esn_id = data.get('esn_id')
            candidature_id = data.get('candidature_id')

            if not client_id or not esn_id or not candidature_id:
                return JsonResponse({"status": False, "message": "client_id, esn_id, et candidature_id requis"}, safe=False)

            message = f"Votre candidature {candidature_id} a été validée par le client {client_id}."
            send_notification(user_id=esn_id, message=message, categorie="Validation de Candidature")

            return JsonResponse({"status": True, "message": "Notification envoyée à l'ESN."}, safe=False)

        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
@csrf_exempt
def notify_bon_de_commande(request):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            client_id = data.get('client_id')
            bon_de_commande_id = data.get('bon_de_commande_id')
            esn_id = data.get('esn_id')  # Still need this to get ESN details

            if not client_id or not bon_de_commande_id or not esn_id:
                return JsonResponse({"status": False, "message": "client_id, bon_de_commande_id, et esn_id requis"}, safe=False)

            # Get detailed information for a better notification message
            try:
                # Get client details to retrieve token
                client = Client.objects.get(ID_clt=client_id)
                client_token = client.token  # Get the client token
                
                # Get bon de commande details
                bon_commande = Bondecommande.objects.get(id_bdc=bon_de_commande_id)
                montant = bon_commande.montant_total
                
                # Get candidature details
                candidature = Candidature.objects.get(id_cd=bon_commande.candidature_id)
                
                # Get appel d'offre details
                appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                ao_title = appel_offre.titre
                
                # Get ESN details
                esn = ESN.objects.get(ID_ESN=esn_id)
                esn_name = esn.Raison_sociale
                
                # Create detail link for client
                bdc_detail_link = f"/interface-cl/boncommand/{bon_de_commande_id}"
                
            except (Client.DoesNotExist, Bondecommande.DoesNotExist, Candidature.DoesNotExist, AppelOffre.DoesNotExist, ESN.DoesNotExist):
                # Fallback to simple message if any data is missing
                message_client = f"Vous avez reçu un bon de commande (ID: {bon_de_commande_id}) à accepter."
                client_token = None
                bdc_detail_link = f"/interface-cl/boncommand/{bon_de_commande_id}"
            else:
                # Create detailed message for client only, emphasizing they need to accept it with HTML anchor tag
                message_client = (
                    f"Un bon de commande (ID: {bon_de_commande_id}) d'un montant de {montant}€ "
                    f"a été généré concernant le projet \"{ao_title}\" avec {esn_name}. "
                    f"Vous devez impérativement accepter ce bon de commande dans votre espace. "
                    f"<a href='{bdc_detail_link}' class='notification-link'>Cliquez ici pour voir les détails</a>"
                )

            # Send notification ONLY to client
            send_notification(
                user_id=None,
                dest_id=client_id,
                message=message_client,
                categorie="Client",
                event="Bon de Commande",
                event_id=bon_de_commande_id
            )

            return JsonResponse({
                "status": True, 
                "message": "Notification envoyée uniquement au client pour acceptation du BDC",
                "client_token": client_token  # Return client token in the response
            }, safe=False)

        except Exception as e:
            print(f"Erreur: {e}")  # Pour le débogage
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False)

@csrf_exempt
def notify_esn_new_bon_de_commande(request):
    """
    API endpoint to notify the ESN when they receive a new purchase order (BDC).
    """
    if request.method == 'POST':
        # Check feature flag - if disabled, return success without sending notification
        if not ENABLE_BDC_CREATION_ESN_NOTIFICATION:
            return JsonResponse({
                "status": True,
                "message": "BDC ESN notification disabled via feature flag"
            }, safe=False)
        
        try:
            data = JSONParser().parse(request)
            bon_de_commande_id = data.get('bon_de_commande_id')
            esn_id = data.get('esn_id')
            
            if not bon_de_commande_id or not esn_id:
                return JsonResponse({
                    "status": False, 
                    "message": "bon_de_commande_id et esn_id sont requis"
                }, safe=False)
            
            # Get detailed information about the purchase order
            try:
                # Get bon de commande details
                bon_commande = Bondecommande.objects.get(id_bdc=bon_de_commande_id)
                montant = bon_commande.montant_total
                
                # Get candidature details
                candidature = Candidature.objects.get(id_cd=bon_commande.candidature_id)
                
                # Get appel d'offre details
                appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                ao_title = appel_offre.titre
                client_id = appel_offre.client_id
                
                # Get client details
                client = Client.objects.get(ID_clt=client_id)
                client_name = client.raison_sociale
                
                # Get ESN token for FCM
                esn = ESN.objects.get(ID_ESN=esn_id)
                esn_token = esn.token
                
                # Create ESN BDC detail link
                bdc_detail_link_esn = f"/interface-en?menu=Bon-de-Commande"
                
                # Create detailed message for ESN
                message_esn = (
                    f"Vous avez reçu un nouveau bon de commande (ID: {bon_de_commande_id}) "
                    f"d'un montant de {montant}€ pour le projet \"{ao_title}\" "
                    f"de la part de {client_name}. "
                    f"Ce bon de commande attend votre acceptation. "
                    f"<a href='{bdc_detail_link_esn}' class='notification-link'>Consulter le bon de commande</a>"
                )
                
            except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, 
                   AppelOffre.DoesNotExist, Client.DoesNotExist, ESN.DoesNotExist):
                # Fallback to simple message if any data is missing
                message_esn = f"Vous avez reçu un nouveau bon de commande (ID: {bon_de_commande_id}) à traiter."
                bdc_detail_link_esn = f"/interface-en?menu=Bon-de-Commande"
                esn_token = None
            
            # Send notification to ESN
            send_notification(
                user_id=None,
                dest_id=esn_id,
                message=message_esn,
                categorie="ESN",
                event="Bon de Commande",
                event_id=bon_de_commande_id
            )
            
            return JsonResponse({
                "status": True, 
                "message": "Notification envoyée à l'ESN pour le nouveau BDC",
                "esn_token": esn_token
            }, safe=False)
            
        except Exception as e:
            print(f"Erreur notification ESN BDC: {e}")
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False)

@csrf_exempt
def admin_validate_bdc(request):
    """
    API endpoint pour que l'admin valide un BDC et envoie automatiquement la notification à l'ESN cible
    """
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            bon_de_commande_id = data.get('bon_de_commande_id')
            validation_status = data.get('status', 'accepted')  # 'accepted' ou 'rejected'
            rejection_reason = data.get('rejection_reason', '')
            
            if not bon_de_commande_id:
                return JsonResponse({"status": False, "message": "bon_de_commande_id requis"}, safe=False)
            
            print(f"DEBUG: Admin validation - BDC ID: {bon_de_commande_id}, Status: {validation_status}")
            
            # Mettre à jour le statut du BDC
            try:
                bon_commande = Bondecommande.objects.get(id_bdc=bon_de_commande_id)
                
                if validation_status == 'accepted':
                    bon_commande.statut = 'pending_esn'  # En attente ESN
                    success_message = "BDC validé avec succès - En attente ESN"
                elif validation_status == 'rejected':
                    bon_commande.statut = 'rejected_by_admin'
                    success_message = "BDC rejeté avec succès"
                else:
                    return JsonResponse({"status": False, "message": "Statut invalide"}, safe=False)
                
                bon_commande.save()
                print(f"DEBUG: BDC statut mis à jour vers: {bon_commande.statut}")
                
            except Bondecommande.DoesNotExist:
                return JsonResponse({"status": False, "message": "BDC non trouvé"}, safe=False)
            
            # Appeler la fonction de notification existante
            # Pass the actual BDC status to the notification function
            notification_status = bon_commande.statut if validation_status == 'accepted' else validation_status
            notification_response = notify_admin_verify_bon_de_commande_internal(
                bon_de_commande_id, notification_status, rejection_reason
            )
            
            if notification_response['status']:
                return JsonResponse({
                    "status": True,
                    "message": f"{success_message}. {notification_response['message']}",
                    "bdc_status": bon_commande.statut,
                    "notifications_sent": True
                }, safe=False)
            else:
                return JsonResponse({
                    "status": False,
                    "message": f"BDC mis à jour mais erreur de notification: {notification_response['message']}"
                }, safe=False)
                
        except Exception as e:
            print(f"Erreur admin validation: {e}")
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False)

def notify_admin_verify_bon_de_commande_internal(bon_de_commande_id, status, rejection_reason=""):
    """
    Fonction interne pour envoyer les notifications (réutilisée par les différents endpoints)
    """
    try:
        # Create detail links
        bdc_detail_link_client = f"/interface-cl/boncommand/{bon_de_commande_id}"
        bdc_detail_link_esn = f"/interface-en?menu=Bon-de-Commande"
        
        # Get detailed information about the purchase order
        print(f"DEBUG: Looking for BDC ID: {bon_de_commande_id}")
        
        # Get bon de commande details
        bon_commande = Bondecommande.objects.get(id_bdc=bon_de_commande_id)
        print(f"DEBUG: BDC found - candidature_id: {bon_commande.candidature_id}")
        montant = bon_commande.montant_total
        
        # Get candidature details
        candidature = Candidature.objects.get(id_cd=bon_commande.candidature_id)
        print(f"DEBUG: Candidature found - AO_id: {candidature.AO_id}, esn_id: {candidature.esn_id}")
        
        # Get appel d'offre details
        appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
        print(f"DEBUG: AO found - client_id: {appel_offre.client_id}")
        ao_title = appel_offre.titre
        
        # Get client details - avec fallback si client n'existe pas
        try:
            client = Client.objects.get(ID_clt=appel_offre.client_id)
            print(f"DEBUG: Client found - ID: {client.ID_clt}")
            client_name = client.raison_sociale
            client_id = client.ID_clt
            client_token = client.token
        except Client.DoesNotExist:
            print(f"DEBUG: Client ID {appel_offre.client_id} introuvable - utilisation d'un client par défaut")
            client = Client.objects.first()
            if client:
                client_name = f"Client par défaut ({client.raison_sociale})"
                client_id = client.ID_clt
                client_token = client.token
                print(f"DEBUG: Client fallback utilisé - ID: {client_id}")
            else:
                return {"status": False, "message": "Aucun client disponible dans la base de données"}
        
        # Get ESN details - avec fallback si ESN n'existe pas
        try:
            esn = ESN.objects.get(ID_ESN=candidature.esn_id)
            print(f"DEBUG: ESN found - ID: {esn.ID_ESN}")
            esn_name = esn.Raison_sociale
            esn_id = esn.ID_ESN
            esn_token = esn.token
        except ESN.DoesNotExist:
            print(f"DEBUG: ESN ID {candidature.esn_id} introuvable - utilisation d'une ESN par défaut")
            esn = ESN.objects.first()
            if esn:
                esn_name = f"ESN par défaut ({esn.Raison_sociale})"
                esn_id = esn.ID_ESN
                esn_token = esn.token
                print(f"DEBUG: ESN fallback utilisée - ID: {esn_id}")
            else:
                return {"status": False, "message": "Aucune ESN disponible dans la base de données"}
        
        # Get all admin users
        admins = Admin.objects.all()
        if not admins.exists():
            return {"status": False, "message": "Aucun administrateur trouvé"}
        
        notifications_sent = 0
        
        # Create notification messages based on status
        if status.lower() == "pending_esn":
            message_admin = (
                f"Votre bon de commande pour l'Appel d'Offres \"{ao_title}\" "
                f"avec {client_name} a été accepté. Montant: {montant}€. "
                f"ESN: {esn_name}."
            )
            
            message_client = (
                f"Votre bon de commande pour le projet \"{ao_title}\" "
                f"a été validé par l'administration. Montant: {montant}€. "
                f"ESN assignée: {esn_name}. "
                f'<a href="{bdc_detail_link_client}" style="color: #1890ff; text-decoration: underline;">Voir les détails</a>'
            )
            
            message_esn = (
                f"Votre bon de commande pour le projet \"{ao_title}\" "
                f"avec {client_name} a été validé par l'administration. "
                f"Montant: {montant}€. Vous pouvez maintenant accepter le BDC. "
                f'<a href="{bdc_detail_link_esn}" style="color: #1890ff; text-decoration: underline;">Voir les détails</a>'
            )
        else:
            message_admin = (
                f"Votre bon de commande pour l'Appel d'Offres \"{ao_title}\" "
                f"avec {client_name} a été rejeté. Montant: {montant}€. "
                f"Raison: {rejection_reason}. ESN: {esn_name}."
            )
            
            message_client = (
                f"Votre bon de commande pour le projet \"{ao_title}\" "
                f"a été rejeté par l'administration. Montant: {montant}€. "
                f"Raison: {rejection_reason}. "
                f'<a href="{bdc_detail_link_client}" style="color: #1890ff; text-decoration: underline;">Voir les détails</a>'
            )
            
            message_esn = (
                f"Le bon de commande pour le projet \"{ao_title}\" "
                f"avec {client_name} a été rejeté par l'administration. "
                f"Montant: {montant}€. Raison: {rejection_reason}. "
                f"Veuillez contacter l'administration pour plus d'informations. "
                f'<a href="{bdc_detail_link_esn}" style="color: #1890ff; text-decoration: underline;">Voir les détails</a>'
            )
        
        # Send notifications to admins
        for admin in admins:
            send_notification(
                user_id=None,
                dest_id=admin.ID_Admin,
                message=message_admin,
                categorie="Admin",
                event="Validation BDC",
                event_id=bon_de_commande_id
            )
            notifications_sent += 1
        
        # Send notification to client
        send_notification(
            user_id=None,
            dest_id=client_id,
            message=message_client,
            categorie="Client",
            event="Validation BDC",
            event_id=bon_de_commande_id
        )
        
        # Send notification to ESN
        print(f"DEBUG: Sending notification to ESN {esn_id}")
        print(f"DEBUG: Message: {message_esn[:100]}...")
        
        notification = send_notification(
            user_id=None,
            dest_id=esn_id,
            message=message_esn,
            categorie="ESN",
            event="Validation BDC",
            event_id=bon_de_commande_id
        )
        print(f"DEBUG: Notification created with ID: {notification.id if notification else 'None'}")
        
        status_text = "validé" if status.lower() == "accepted" else "rejeté"
        
        return {
            "status": True,
            "message": f"Bon de commande {status_text}. Notifications envoyées à {notifications_sent} administrateurs, au client et à l'ESN",
            "client_token": client_token,
            "esn_token": esn_token
        }
        
    except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, AppelOffre.DoesNotExist) as e:
        print(f"DEBUG: Erreur détaillée - {type(e).__name__}: {e}")
        return {"status": False, "message": f"Erreur lors de la récupération des données: {type(e).__name__}"}
    except Exception as e:
        print(f"DEBUG: Erreur inattendue - {e}")
        return {"status": False, "message": f"Erreur inattendue: {str(e)}"}

@csrf_exempt
def notify_admin_verify_bon_de_commande(request):
    """
    API endpoint to notify administrators, client and ESN about purchase orders verification results.
    """
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            bon_de_commande_id = data.get('bon_de_commande_id')
            status = data.get('status')  # Default to accepted if not specified
            rejection_reason = data.get('rejection_reason', "Non précisée")  # Optional reason if rejected
            
            if not bon_de_commande_id:
                return JsonResponse({"status": False, "message": "bon_de_commande_id requis"}, safe=False)
            
            # Create detail links
            bdc_detail_link_client = f"/interface-cl/boncommand/{bon_de_commande_id}"
            bdc_detail_link_esn = f"/interface-en?menu=Bon-de-Commande"
            
            # Get detailed information about the purchase order
            try:
                print(f"DEBUG: Looking for BDC ID: {bon_de_commande_id}")
                
                # Get bon de commande details
                bon_commande = Bondecommande.objects.get(id_bdc=bon_de_commande_id)
                print(f"DEBUG: BDC found - candidature_id: {bon_commande.candidature_id}")
                montant = bon_commande.montant_total
                
                # Get candidature details
                candidature = Candidature.objects.get(id_cd=bon_commande.candidature_id)
                print(f"DEBUG: Candidature found - AO_id: {candidature.AO_id}, esn_id: {candidature.esn_id}")
                
                # Get appel d'offre details
                appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                print(f"DEBUG: AO found - client_id: {appel_offre.client_id}")
                ao_title = appel_offre.titre
                
                # Get client details - avec fallback si client n'existe pas
                try:
                    client = Client.objects.get(ID_clt=appel_offre.client_id)
                    print(f"DEBUG: Client found - ID: {client.ID_clt}")
                    client_name = client.raison_sociale
                    client_id = client.ID_clt
                    client_token = client.token
                except Client.DoesNotExist:
                    print(f"DEBUG: Client ID {appel_offre.client_id} introuvable - utilisation d'un client par défaut")
                    # Utiliser le premier client disponible comme fallback
                    client = Client.objects.first()
                    if client:
                        client_name = f"Client par défaut ({client.raison_sociale})"
                        client_id = client.ID_clt
                        client_token = client.token
                        print(f"DEBUG: Client fallback utilisé - ID: {client_id}")
                    else:
                        return JsonResponse({
                            "status": False, 
                            "message": "Aucun client disponible dans la base de données"
                        }, safe=False)
                
                # Get ESN details
                try:
                    esn = ESN.objects.get(ID_ESN=candidature.esn_id)
                    print(f"DEBUG: ESN found - ID: {esn.ID_ESN}")
                except ESN.DoesNotExist:
                    print(f"DEBUG: ESN ID {candidature.esn_id} introuvable - utilisation d'un ESN par défaut")
                    esn = ESN.objects.first()  # Use first available ESN as fallback
                    print(f"DEBUG: ESN fallback utilisé - ID: {esn.ID_ESN}")
                
                esn_name = esn.Raison_sociale
                esn_id = esn.ID_ESN
                esn_token = esn.token
                
            except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, 
                   AppelOffre.DoesNotExist, ESN.DoesNotExist) as e:
                print(f"DEBUG: Erreur détaillée - {type(e).__name__}: {e}")
                return JsonResponse({
                    "status": False, 
                    "message": f"Impossible de récupérer les informations du bon de commande: {type(e).__name__}"
                }, safe=False)
            
            # Get all admin users without filtering by is_staff
            admins = Admin.objects.all()
            if not admins.exists():
                return JsonResponse({"status": False, "message": "Aucun administrateur trouvé"}, safe=False)
            
            notifications_sent = 0
            
            # Create notification messages based on status (accepted or rejected)
            if status.lower() == "pending_esn":
                # ACCEPTED CASE
                
                # Create notification for admins - confirmation of their acceptance
                message_admin = (
                    f"Vous avez validé le bon de commande (ID: {bon_de_commande_id}). "
                    f"Projet: \"{ao_title}\". Client: {client_name}. ESN: {esn_name}. "
                    f"Montant: {montant}€. "
                    f"Les parties concernées ont été notifiées de votre décision. "
                    f"<a href='{bdc_detail_link_client}' class='notification-link'>Voir détails</a>"
                )
                
                # Create notification for client - BDC accepted by admin
                message_client = (
                    f"Votre bon de commande (ID: {bon_de_commande_id}) pour le projet \"{ao_title}\" "
                    f"avec {esn_name} a été vérifié et accepté par l'administration. "
                    f"Montant: {montant}€. "
                    f"Vous pouvez maintenant procéder à l'étape suivante du processus. "
                    f"<a href='{bdc_detail_link_client}' class='notification-link'>Voir les détails</a>"
                )
                
                # Create notification for ESN - BDC accepted by admin, ESN needs to accept
                message_esn = (
                    f"Le bon de commande (ID: {bon_de_commande_id}) pour le projet \"{ao_title}\" "
                    f"avec {client_name} a été vérifié et validé par l'administration. "
                    f"Montant: {montant}€. "
                    f"Vous devez maintenant accepter ce bon de commande dans votre espace ESN "
                    f"pour finaliser le processus et permettre la génération du contrat. "
                    f"<a href='{bdc_detail_link_esn}' class='notification-link'>Voir détails</a>"
                )
                
            else:
                # REJECTED CASE
                
                # Create notification for admins - confirmation of their rejection
                message_admin = (
                    f"Vous avez rejeté le bon de commande (ID: {bon_de_commande_id}). "
                    f"Projet: \"{ao_title}\". Client: {client_name}. ESN: {esn_name}. "
                    f"Montant: {montant}€. Raison: {rejection_reason}. "
                    f"Les parties concernées ont été notifiées de votre décision. "
                    f"<a href='{bdc_detail_link_client}' class='notification-link'>Voir détails</a>"
                )
                
                # Create notification for client - BDC rejected by admin
                message_client = (
                    f"Votre bon de commande (ID: {bon_de_commande_id}) pour le projet \"{ao_title}\" "
                    f"avec {esn_name} a été rejeté par l'administration. "
                    f"Montant: {montant}€. Raison: {rejection_reason}. "
                    f"Veuillez contacter l'administration pour plus d'informations. "
                    f"<a href='{bdc_detail_link_client}' class='notification-link'>Voir détails</a>"
                )
                
                # Create notification for ESN - BDC rejected by admin
                message_esn = (
                    f"Le bon de commande (ID: {bon_de_commande_id}) pour le projet \"{ao_title}\" "
                    f"avec {client_name} a été rejeté par l'administration. "
                    f"Montant: {montant}€. Raison: {rejection_reason}. "
                    f"Veuillez contacter l'administration pour plus d'informations. "
                    f"<a href='{bdc_detail_link_esn}' class='notification-link'>Voir détails</a>"
                )
            
            # Send notifications to admins
            for admin in admins:
                send_notification(
                    user_id=None,
                    dest_id=admin.ID_Admin,
                    message=message_admin,
                    categorie="Admin",
                    event="Vérification Bon de Commande",
                    event_id=bon_de_commande_id
                )
                notifications_sent += 1
            
            # Send notification to client
            send_notification(
                user_id=None,
                dest_id=client_id,
                message=message_client,
                categorie="Client",
                event="Vérification Bon de Commande",
                event_id=bon_de_commande_id
            )
            
            # Send notification to ESN
            print(f"DEBUG: Sending notification to ESN {esn_id}")
            print(f"DEBUG: Message: {message_esn[:100]}...")
            print(f"DEBUG: Categorie: ESN")
            
            notification = send_notification(
                user_id=None,
                dest_id=esn_id,
                message=message_esn,
                categorie="ESN",
                event="Vérification Bon de Commande",
                event_id=bon_de_commande_id
            )
            print(f"DEBUG: Notification created with ID: {notification.id if notification else 'None'}")
            
            # Prepare the appropriate status message
            status_text = "accepté" if status.lower() == "accepted" else "rejeté"
            
            return JsonResponse({
                "status": True,
                "message": f"Bon de commande {status_text}. Notifications envoyées à {notifications_sent} administrateurs, au client et à l'ESN",
                "verification_status": status,
                "client_token": client_token,
                "esn_token": esn_token
            }, safe=False)
            
        except Exception as e:
            print(f"Erreur: {e}")  # Pour le débogage
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False)
@csrf_exempt
def notify_esn_accept_bon_de_commande(request):
    """
    API endpoint to notify the client that the ESN has accepted the purchase order,
    and remind the ESN that the mission is about to start.
    """
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            bon_de_commande_id = data.get('bon_de_commande_id')
            esn_id = data.get('esn_id')
            
            if not bon_de_commande_id or not esn_id:
                return JsonResponse({
                    "status": False, 
                    "message": "bon_de_commande_id et esn_id sont requis"
                }, safe=False)
            
            # Get detailed information about the bon de commande and related entities
            try:
                # Get bon de commande details
                bon_commande = Bondecommande.objects.get(id_bdc=bon_de_commande_id)
                montant = bon_commande.montant_total
                
                # Get candidature details
                candidature = Candidature.objects.get(id_cd=bon_commande.candidature_id)
                
                # Get appel d'offre details
                appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                ao_title = appel_offre.titre
                client_id = appel_offre.client_id
                
                # Get client details
                client = Client.objects.get(ID_clt=client_id)
                client_name = client.raison_sociale
                client_token = client.token
                
                # Get ESN details
                esn = ESN.objects.get(ID_ESN=esn_id)
                esn_name = esn.Raison_sociale
                esn_token = esn.token
                
                # Get consultant details (if available)
                consultant_name = "Non spécifié"
                if candidature.id_consultant:
                    try:
                        consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
                        consultant_name = f"{consultant.Nom} {consultant.Prenom}"
                    except Collaborateur.DoesNotExist:
                        pass
                
            except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, 
                   AppelOffre.DoesNotExist, Client.DoesNotExist, ESN.DoesNotExist):
                return JsonResponse({
                    "status": False, 
                    "message": "Impossible de récupérer les informations du bon de commande"
                }, safe=False)
            
            # Message for the client - inform that ESN has accepted the purchase order
            message_client = (
                f"L'ESN {esn_name} a accepté votre bon de commande (ID: {bon_de_commande_id}) "
                f"pour le projet \"{ao_title}\". Montant: {montant}€. "
                f"Consultant: {consultant_name}. "
                f"La mission pourra bientôt démarrer."
            )
            
            send_notification(
                user_id=esn_id,  # ESN triggered the event
                dest_id=client_id,  # Notification goes to client
                message=message_client,
                categorie="Client",
                event="Bon de Commande",
                event_id=bon_de_commande_id
            )
            
            # Send mission start notification to client
            bdc_link = f"/interface-cl?menu=Liste-BDC"
            client_mission_message = (
                f"Mission démarrée pour le projet \"{ao_title}\". "
                f"L'ESN {esn_name} a confirmé le consultant {consultant_name} pour une mission de {montant}€. "
                f"La prestation peut maintenant commencer. "
                f'<a href="{bdc_link}" style="color: #1890ff; text-decoration: underline;">Suivre la mission</a>'
            )
            
            send_notification(
                user_id=esn_id,  # ESN triggered the mission start
                dest_id=client_id,  # Notification goes to client
                message=client_mission_message,
                categorie="Client",
                event="Démarrage Mission",
                event_id=bon_de_commande_id
            )
            
            # Message for the ESN - confirmation that mission has started
            message_esn = (
                f"Mission démarrée pour le projet \"{ao_title}\". "
                f"Client: {client_name}, Consultant: {consultant_name}, Montant: {montant}€. "
                f"Le consultant peut maintenant commencer la prestation. "
                # f'<a href="/interface-en?menu=Bon-de-Commande" style="color: #1890ff; text-decoration: underline;">Gérer mes missions</a>'
            )
            
            send_notification(
                user_id=esn_id,  # ESN triggered the event
                dest_id=esn_id,  # Notification also goes to ESN as confirmation
                message=message_esn,
                categorie="ESN",
                event="Mission Démarrée",
                event_id=bon_de_commande_id
            )
            
            # Disable the Appel d'Offre when BDC is accepted
            try:
                appel_offre.statut = "inactive"
                appel_offre.save()
                print(f"DEBUG: Appel d'Offre {appel_offre.id} disabled after BDC {bon_de_commande_id} acceptance")
            except Exception as ao_disable_error:
                print(f"WARNING: Could not disable Appel d'Offre {appel_offre.id}: {str(ao_disable_error)}")
                # Don't fail the whole request if AO disable fails
            
            return JsonResponse({
                "status": True, 
                "message": "Notifications envoyées avec succès au client et à l'ESN",
                "client_token": client_token,
                "esn_token": esn_token
            }, safe=False)
            
        except Exception as e:
            print(f"Erreur: {e}")  # Pour le débogage
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False)

@csrf_exempt
def notify_esn_reject_bon_de_commande(request):
    """
    API endpoint to notify the client that the ESN has rejected/not accepted the purchase order.
    """
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            bon_de_commande_id = data.get('bon_de_commande_id')
            esn_id = data.get('esn_id')
            reason = data.get('reason', "Non précisée")  # Optional reason for rejection
            
            if not bon_de_commande_id or not esn_id:
                return JsonResponse({
                    "status": False, 
                    "message": "bon_de_commande_id et esn_id sont requis"
                }, safe=False)
            
            # Get detailed information about the bon de commande and related entities
            try:
                # Get bon de commande details
                bon_commande = Bondecommande.objects.get(id_bdc=bon_de_commande_id)
                montant = bon_commande.montant_total
                
                # Get candidature details
                candidature = Candidature.objects.get(id_cd=bon_commande.candidature_id)
                
                # Get appel d'offre details
                appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                ao_title = appel_offre.titre
                client_id = appel_offre.client_id
                
                # Get client details
                client = Client.objects.get(ID_clt=client_id)
                client_name = client.raison_sociale
                client_token = client.token
                
                # Get ESN details
                esn = ESN.objects.get(ID_ESN=esn_id)
                esn_name = esn.Raison_sociale
                esn_token = esn.token
                
            except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, 
                   AppelOffre.DoesNotExist, Client.DoesNotExist, ESN.DoesNotExist):
                return JsonResponse({
                    "status": False, 
                    "message": "Impossible de récupérer les informations du bon de commande"
                }, safe=False)
            
            # Message for the client - inform that ESN has rejected the purchase order
            message_client = (
                f"L'ESN {esn_name} n'a pas accepté votre bon de commande (ID: {bon_de_commande_id}) "
                f"pour le projet \"{ao_title}\". Montant: {montant}€. "
                f"Raison: {reason}. "
                f"Vous pouvez contacter l'ESN pour plus d'informations ou chercher une solution alternative."
            )
            
            send_notification(
                user_id=esn_id,  # ESN triggered the event
                dest_id=client_id,  # Notification goes to client
                message=message_client,
                categorie="Client",
                event="Bon de Commande",
                event_id=bon_de_commande_id
            )
            
            # Message for the ESN - confirmation of rejection
            message_esn = (
                f"Vous avez décliné le bon de commande (ID: {bon_de_commande_id}) "
                f"pour le projet \"{ao_title}\" avec {client_name}. Montant: {montant}€. "
                f"Raison: {reason}. "
                f"Le client a été informé de votre décision."
            )
            
            send_notification(
                user_id=esn_id,  # ESN triggered the event
                dest_id=esn_id,  # Notification also goes to ESN as confirmation
                message=message_esn,
                categorie="ESN",
                event="Bon de Commande",
                event_id=bon_de_commande_id
            )
            
            # Notify admins about rejection for oversight
            admins = Admin.objects.all()
            for admin in admins:
                message_admin = (
                    f"L'ESN {esn_name} a décliné le bon de commande (ID: {bon_de_commande_id}) "
                    f"pour le projet \"{ao_title}\" du client {client_name}. "
                    f"Montant: {montant}€. Raison: {reason}. "
                    f"Veuillez prendre note de cette situation."
                )
                
                send_notification(
                    user_id=esn_id,
                    dest_id=admin.ID_Admin,
                    message=message_admin,
                    categorie="Admin",
                    event="Bon de Commande",
                    event_id=bon_de_commande_id
                )
            
            return JsonResponse({
                "status": True, 
                "message": "Notifications de refus envoyées avec succès",
                "client_token": client_token,
                "esn_token": esn_token
            }, safe=False)
            
        except Exception as e:
            print(f"Erreur: {e}")  # Pour le débogage
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False)
@csrf_exempt
def notify_validation_bon_de_commande(request):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            client_id = data.get('client_id')
            esn_id = data.get('esn_id')
            bon_de_commande_id = data.get('bon_de_commande_id')

            if not client_id or not esn_id or not bon_de_commande_id:
                return JsonResponse({"status": False, "message": "client_id, esn_id, et bon_de_commande_id requis"}, safe=False)

            # Get detailed information about the bon de commande, client, and ESN
            try:
                # Get bon de commande details
                bon_de_commande = Bondecommande.objects.get(id_bdc=bon_de_commande_id)
                montant = bon_de_commande.montant
                
                # Get candidature details
                candidature = Candidature.objects.get(id_cd=bon_de_commande.candidature_id)
                
                # Get appel d'offre details
                appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                ao_title = appel_offre.titre
                
                # Get client details
                client = Client.objects.get(ID_clt=client_id)
                client_name = client.raison_sociale
                
                # Get ESN details
                esn = ESN.objects.get(ID_ESN=esn_id)
                esn_name = esn.Raison_sociale
                esn_token = esn.token  # Keep token for backward compatibility
                
                # Get consultant details (if available)
                consultant_name = "Non spécifié"
                if candidature.id_consultant:
                    try:
                        consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
                        consultant_name = f"{consultant.Nom} {consultant.Prenom}"
                    except Collaborateur.DoesNotExist:
                        pass
                
            except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, AppelOffre.DoesNotExist, Client.DoesNotExist, ESN.DoesNotExist):
                return JsonResponse({"status": False, "message": "Données associées introuvables"}, safe=False)

            # Create detailed notification for ESN
            message_esn = (
                f"Le bon de commande (ID: {bon_de_commande_id}) pour le projet \"{ao_title}\" "
                f"a été validé par {client_name}. Montant: {montant} €. "
                f"Consultant concerné: {consultant_name}. "
                f"Vous pouvez maintenant procéder à la génération du contrat."
            )
            
            send_notification(
                user_id=client_id,  # Client triggered the event
                dest_id=esn_id,     # Notification goes to ESN
                message=message_esn,
                categorie="ESN",
                event="Bon de Commande",
                event_id=bon_de_commande_id
            )
            
            # Create confirmation notification for client
            message_client = (
                f"Vous avez validé le bon de commande (ID: {bon_de_commande_id}) pour {esn_name}. "
                f"Projet: \"{ao_title}\". Montant: {montant} €. "
                f"Consultant: {consultant_name}. "
                f"L'ESN a été notifiée et pourra procéder à la génération du bon de command."
            )
            
            send_notification(
                user_id=client_id,  # Client triggered the event
                dest_id=client_id,  # Notification also goes to client as confirmation
                message=message_client,
                categorie="Client",
                event="Bon de Commande",
                event_id=bon_de_commande_id
            )

            return JsonResponse({
                "status": True, 
                "message": "Notifications envoyées avec succès à l'ESN et au client",
                "token": esn_token
            }, safe=False)

        except Exception as e:
            print(f"Erreur: {e}")  # Pour le débogage
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False)
@csrf_exempt
def notify_signature_contrat(request):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            client_id = data.get('client_id')
            esn_id = data.get('esn_id')
            contrat_id = data.get('contrat_id')

            if not client_id or not esn_id or not contrat_id:
                return JsonResponse({"status": False, "message": "client_id, esn_id, et contrat_id requis"}, safe=False)

            # Notification pour le client
            message_client = f"Le contrat {contrat_id} a été signé avec l'ESN {esn_id}."
            send_notification(user_id=esn_id, dest_id=esn_id, message=message_client, categorie="Client", event="Contrat", event_id=contrat_id)

            # Notification pour l'ESN
            message_esn = f"Le contrat {contrat_id} a été signé avec le client {client_id}."
            send_notification(user_id=client_id, dest_id=client_id, message=message_esn, categorie="ESN", event="Contrat", event_id=contrat_id)

            return JsonResponse({"status": True, "message": "Notifications envoyées au client et à l'ESN."}, safe=False)

        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, safe=False)

@csrf_exempt
def contrat_by_idClient(request):
    if request.method == 'GET':
        try:
            clientId = request.GET.get("clientId")
            if not clientId:
                return JsonResponse({"status": False, "message": "clientId requis"}, safe=False)

            # Récupérer tous les appels d'offres liés au client
            appels = AppelOffre.objects.filter(client_id=clientId)

            # Récupérer les IDs des appels d'offres
            appel_ids = appels.values_list('id', flat=True)

            # Récupérer toutes les candidatures liées aux appels d'offres
            candidatures = Candidature.objects.filter(AO_id__in=appel_ids)

            # Récupérer tous les contrats liés aux candidatures
            contrats = Contrat.objects.filter().order_by('-id_contrat')
            contrat_serializer = ContratSerializer(contrats, many=True)
            data = contrat_serializer.data

            return JsonResponse({"status": True, "data": data}, safe=False)
        except Exception as e:
                    return JsonResponse({"status": False, "message": str(e)}, safe=False)

    
@csrf_exempt
def contrat_by_idEsn(request):
    if request.method == 'GET':
        try:
            esnId = request.GET.get("esnId")
            if not esnId:
                return JsonResponse({"status": False, "message": "esnId requis"}, safe=False)

                        # Récupérer toutes les candidatures liées à l'ESN
            candidatures = Candidature.objects.filter(esn_id=esnId)

            # Récupérer les IDs des candidatures
            candidature_ids = candidatures.values_list('id_cd', flat=True)

            # Récupérer tous les contrats liés aux candidatures en ordre décroissant
            contrats = Contrat.objects.filter(candidature_id__in=candidature_ids).order_by('-id_contrat')

            # Sérialiser les contrats
            contrat_serializer = ContratSerializer(contrats, many=True)

            return JsonResponse({"status": True, "data": contrat_serializer.data}, safe=False) 
        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, safe=False)

@csrf_exempt 
def download_contract(request, contract_id):
    if request.method == 'GET':
        try:
            # Get contract and related data
            contract = Contrat.objects.get(id_contrat=contract_id)
            candidature = Candidature.objects.get(id_cd=contract.candidature_id)
            esn = ESN.objects.get(ID_ESN=candidature.esn_id)
            appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
            client = Client.objects.get(ID_clt=appel_offre.client_id)

            # Structure contract information
            contract_info = {
                "numero_contrat": contract.numero_contrat,
                "date_signature": contract.date_signature,
                "esn": esn.Raison_sociale,
                "client": client.raison_sociale,
                "date_debut": contract.date_debut,
                "date_fin": contract.date_fin,
                "montant": contract.montant,
                "statut": contract.statut,
                "conditions": contract.conditions or ""
            }

            return JsonResponse({
                "status": True,
                "data": contract_info
            }, safe=False)

        except Contrat.DoesNotExist:
            return JsonResponse({"status": False, "message": "Contract not found"}, safe=False)
        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, safe=False)

    return JsonResponse({"status": False, "message": "Invalid request method"}, safe=False)



@csrf_exempt
def Esn_by_id(request):
    if request.method == 'GET':
        esnId = request.GET["esnId"]
        esn = ESN.objects.filter(ID_ESN=esnId)
       
        esn_serializer = ESNSerializer(esn, many=True)
        data = []
        for S in esn_serializer.data:
            data.append(S)
        return JsonResponse({"total": len(data),"data": data}, safe=False)
    
@csrf_exempt
def notify_new_candidature(request):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            appel_offre_id = data.get('appel_offre_id')
            candidature_id = data.get('condidature_id')
            esn_id = data.get('esn_id')

            print(f"appel_offre_id: {appel_offre_id}, candidature_id: {candidature_id}, esn_id: {esn_id}")
            
            # Get detailed information about the AppelOffre, Client and ESN
            try:
                # Get appel offre details
                appel_offre = AppelOffre.objects.get(id=appel_offre_id)
                ao_title = appel_offre.titre
                client_id = appel_offre.client_id
                
                # Get client details
                client = Client.objects.get(ID_clt=client_id)
                client_name = client.raison_sociale
                
                # Get ESN details
                esn = ESN.objects.get(ID_ESN=esn_id)
                esn_name = esn.Raison_sociale
                
                # Get consultant details (if available)
                consultant_name = "Non spécifié"
                try:
                    candidature = Candidature.objects.get(id_cd=candidature_id)
                    if candidature.id_consultant:
                        consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
                        consultant_name = f"{consultant.Nom} {consultant.Prenom}"
                except (Candidature.DoesNotExist, Collaborateur.DoesNotExist):
                    pass
                    
            except (AppelOffre.DoesNotExist, Client.DoesNotExist, ESN.DoesNotExist):
                return JsonResponse({"status": False, "message": "Données associées introuvables"}, safe=False)

            # Validation des paramètres essentiels
            if not client_id or not appel_offre_id or not candidature_id or not esn_id:
                return JsonResponse({"status": False, "message": "Paramètres manquants (client_id, appel_offre_id, candidature_id, esn_id)"}, safe=False)

            # Préparation du message de notification pour le client - plus détaillé et informatif
            message_client = (
                f"Nouvelle candidature reçue pour votre appel d'offre \"{ao_title}\" ! "
                f"{esn_name} vous propose {consultant_name} pour ce projet. "
                f"Consultez les détails et évaluez cette candidature dès maintenant : "
                f"<a href='/interface-cl?menu=Liste-Candidature&ao_id={appel_offre_id}' style='color: #1890ff; text-decoration: underline;'>Voir la candidature</a>"
            )

            # Envoi de la notification au client
            send_notification(
                user_id=esn_id,  # L'ESN est à l'origine de l'événement
                dest_id=client_id,  # Le destinataire est le client
                message=message_client,
                categorie="Client",
                event="Candidature",
                event_id=candidature_id
            )
            
            # Préparation du message de confirmation pour l'ESN
            message_esn = (
                f"Votre candidature pour l'appel d'offre \"{ao_title}\" "
                f"a été soumise avec succès au client {client_name}. "
                f"Consultant proposé : {consultant_name}. "
                f"Vous serez notifié dès que le client aura examiné votre proposition."
            )
            
            # Envoi d'une notification de confirmation à l'ESN
            send_notification(
                user_id=esn_id,  # L'ESN est à l'origine de l'événement
                dest_id=esn_id,  # Le destinataire est aussi l'ESN (confirmation)
                message=message_esn,
                categorie="ESN",
                event="Candidature",
                event_id=candidature_id
            )

            return JsonResponse({
                "status": True, 
                "message": "Notifications envoyées au client et à l'ESN"
            }, safe=False)

        except Exception as e:
            print(f"Erreur: {e}")  # Pour le débogage
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
@csrf_exempt
def notify_candidature_accepted(request):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            candidature_id = data.get('candidature_id')
            esn_id = data.get('esn_id')

            if not all([candidature_id, esn_id]):
                return JsonResponse({"status": False, "message": "candidature_id et esn_id sont requis."}, safe=False)

            # Get full information about the candidature, consultant, appel d'offre, and client
            try:
                # Get candidature details
                candidature = Candidature.objects.get(id_cd=candidature_id)
                
                # Get appel d'offre details
                appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                ao_title = appel_offre.titre
                client_id = appel_offre.client_id
                
                # Get client details
                client = Client.objects.get(ID_clt=client_id)
                client_name = client.raison_sociale
                
                # Get ESN details
                esn = ESN.objects.get(ID_ESN=esn_id)
                esn_name = esn.Raison_sociale
                esn_token = esn.token
                
                # Get consultant details (if available)
                consultant_name = "Non spécifié"
                if candidature.id_consultant:
                    try:
                        consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
                        consultant_name = f"{consultant.Nom} {consultant.Prenom}"
                    except Collaborateur.DoesNotExist:
                        pass
            except (Candidature.DoesNotExist, AppelOffre.DoesNotExist, Client.DoesNotExist, ESN.DoesNotExist):
                return JsonResponse({"status": False, "message": "Données associées introuvables"}, safe=False)

            # Create detailed notification for ESN with link to BDC process
            bdc_link = f"/interface-en?menu=Bon-de-Commande"  # Link to BDC menu
            message_esn = (
                f"🎉 Félicitations! Votre candidature (ID: {candidature_id}) pour l'appel d'offre \"{ao_title}\" "
                f"a été acceptée par {client_name}. Consultant proposé: {consultant_name}. "
                f"Félicitations pour cette sélection ! "
                f"<a href='{bdc_link}' class='notification-link'>Accédez à la suite du processus avec le BDC</a>"
            )
            
            send_notification(
                user_id=client_id,  # Client triggered the event
                dest_id=esn_id,     # Notification goes to ESN
                event_id=candidature_id,
                event="Candidature",
                message=message_esn,
                categorie="ESN"
            )
            
            # Create confirmation notification for client
            message_client = (
                f"Vous avez accepté la candidature (ID: {candidature_id}) de {esn_name} "
                f"pour votre appel d'offre \"{ao_title}\". Consultant: {consultant_name}. "
                f"Vous pouvez maintenant procéder à la génération du bon de commande"
            )
            
            send_notification(
                user_id=client_id,  # Client triggered the event 
                dest_id=client_id,  # Notification also goes to client as confirmation
                event_id=candidature_id,
                event="Candidature",
                message=message_client,
                categorie="Client"
            )

            return JsonResponse({
                "status": True, 
                "message": "Notifications envoyées avec succès à l'ESN et au client",
                "data": esn_token
            }, safe=False)
            
        except Exception as e:
            print(f"Erreur: {e}")  # For debugging
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
            
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False)   

@csrf_exempt
def notify_expiration_ao(request):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)

            ao_id = data.get('ao_id')
            client_id = data.get('client_id')

            # Get the AppelOffre data to create more informative messages
           # In the notify_expiration_ao function, change:
            try:
                appel_offre = AppelOffre.objects.get(id=ao_id)
                ao_title = appel_offre.titre
                ao_date_fin = appel_offre.date_limite  # Changed from date_fin to date_limite
                
                # Get client name for ESN notifications
                client = Client.objects.get(ID_clt=client_id)
                client_name = client.raison_sociale
            except (AppelOffre.DoesNotExist, Client.DoesNotExist):
                ao_title = "sans titre"
                ao_date_fin = "inconnue"
                client_name = f"ID={client_id}"

            list_esn = []
            # assume we need to get the list from the database base on the client id 
            partenaires = ESN.objects.all()
            for partenaire in partenaires:
                list_esn.append(partenaire.ID_ESN)
            if len(list_esn) == 0:
                return JsonResponse({"status": True, "message": "Non partenaire découvert"}, safe=False)
            
            if not all([ao_id, client_id, list_esn]):
                return JsonResponse({"status": False, "message": "Tous les champs sont requis."}, safe=False)

            # Custom message for client - more formal, acknowledging their own AO has expired
            message_client = (
                f"Votre appel d'offre \"{ao_title}\" (ID: {ao_id}) est arrivé à expiration "
                f"le {ao_date_fin}. Les ESN ne peuvent plus soumettre de candidatures. "
                f"Vous pouvez maintenant procéder à la sélection finale des candidatures reçues "
                f"ou prolonger la date limite si nécessaire."
            )
            
            send_notification(
                user_id=None,
                dest_id=client_id,
                event_id=ao_id,
                event="AO",
                message=message_client,
                categorie="Client"
            )

            # Different message for each ESN - more informative about opportunity closure
            for esn_id in list_esn:
                message_esn = (
                    f"L'appel d'offre \"{ao_title}\" (ID: {ao_id}) du client {client_name} "
                    f"est arrivé à expiration le {ao_date_fin}. "
                    f"Il n'est plus possible de soumettre de nouvelles candidatures pour cette opportunité. "
                    f"Veuillez consulter le statut de vos candidatures déjà soumises."
                )
                
                send_notification(
                    user_id=None,
                    dest_id=esn_id,
                    event_id=ao_id,
                    event="AO",
                    message=message_esn,
                    categorie="ESN"
                )

            return JsonResponse({"status": True, "message": "Notifications personnalisées envoyées aux parties concernées."}, safe=False)

        except Exception as e:
            print(f"Erreur: {e}")  # Déboguer l'erreur
            return JsonResponse({"status": False, "message": str(e)}, safe=False)

@csrf_exempt
def notify_end_of_mission(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        contrat_id = data.get('contrat_id')
        client_id = data.get('client_id')
        esn_id = data.get('esn_id')

        if not all([contrat_id, client_id, esn_id]):
            return JsonResponse({"status": False, "message": "Tous les champs sont requis."}, safe=False)

        message_client = (
            f"La mission liée au contrat ID={contrat_id} est terminée. "
            f'<a href="/interface-cl?menu=Contart" class="notification-link">Voir mes contrats</a>'
        )
        message_esn = (
            f"La mission liée au contrat ID={contrat_id} est terminée. "
            f'<a href="/interface-en?menu=Contart" class="notification-link">Voir mes contrats</a>'
        )

        send_notification(
            user_id=None,
            dest_id=client_id,
            event_id=contrat_id,
            event="Contrat",
            message=message_client,
            categorie="Client"
        )
        send_notification(
            user_id=None,
            dest_id=esn_id,
            event_id=contrat_id,
            event="Contrat",
            message=message_esn,
            categorie="ESN"
        )

        return JsonResponse({"status": True, "message": "Notifications de fin de mission envoyées."}, safe=False)

@csrf_exempt
def notify_cra_validation_admin(request):
    """
    API endpoint to notify administrators when a client validates a CRA and invoices are created.
    Sends detailed notifications to all admins about CRA validation and automatic invoice generation.
    """
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            
            # Extract required fields
            cra_id = data.get('cra_id')
            client_id = data.get('client_id')
            client_name = data.get('client_name', 'Client')
            consultant_name = data.get('consultant_name', 'Consultant')
            esn_name = data.get('esn_name', 'ESN')
            periode = data.get('periode', '')
            montant_total = data.get('montant_total', 0)
            tjm = data.get('tjm', 0)
            jours_travailles = data.get('jours_travailles', 0)
            project_title = data.get('project_title', 'Projet')
            bdc_id = data.get('bdc_id')
            
            if not cra_id or not client_id:
                return JsonResponse({
                    "status": False,
                    "message": "CRA ID and Client ID are required"
                }, safe=False, status=400)
            
            # Get all admins
            admins = Admin.objects.all()
            if not admins.exists():
                print("⚠️ Warning: No admin users found in database")
                return JsonResponse({
                    "status": False,
                    "message": "No admin users found"
                }, safe=False, status=404)
            
            # Get commission percentage from BDC (default to 8% if not found)
            commission_percentage = 8
            if bdc_id:
                try:
                    bdc = Bondecommande.objects.get(id_bdc=bdc_id)
                    if bdc.benefit:
                        # Benefit is stored as "percentage|amount"
                        parts = str(bdc.benefit).split('|')
                        if len(parts) >= 1:
                            commission_percentage = float(parts[0])
                            print(f"✓ Using commission from BDC {bdc_id}: {commission_percentage}%")
                except Bondecommande.DoesNotExist:
                    print(f"⚠️ BDC {bdc_id} not found, using default commission: {commission_percentage}%")
                except (ValueError, IndexError) as e:
                    print(f"⚠️ Error parsing commission from BDC {bdc_id}: {e}, using default: {commission_percentage}%")
            
            montant_prestataire = float(montant_total)
            commission_mitc = montant_prestataire * (commission_percentage / 100)
            montant_client = montant_prestataire + commission_mitc
            
            # Create notification message for admins with clear title and content
            cra_link = "/interface-ad?menu=gestion-cra"
            invoice_link = "/interface-ad?menu=gestion-factures"
            
            admin_message = (
                f"<div style='background: #f0f9ff; padding: 16px; border-left: 4px solid #1890ff; border-radius: 4px;'>"
                f"<h3 style='margin: 0 0 12px 0; color: #0050b3;'>✅ CRA VALIDÉ - FACTURES AUTOMATIQUEMENT CRÉÉES</h3>"
                f"<p style='margin: 8px 0;'><strong>📋 Client:</strong> {client_name}</p>"
                f"<p style='margin: 8px 0;'><strong>👨‍💼 Consultant:</strong> {consultant_name} ({esn_name})</p>"
                f"<p style='margin: 8px 0;'><strong>📅 Période:</strong> {periode}</p>"
                f"<p style='margin: 8px 0;'><strong>📊 Projet:</strong> {project_title}</p>"
                f"</div>"
                f"<div style='margin: 16px 0; padding: 12px; background: #f6ffed; border-radius: 4px;'>"
                f"<p style='margin: 4px 0;'><strong>Détails CRA:</strong></p>"
                f"<ul style='margin: 8px 0; padding-left: 20px;'>"
                f"<li>CRA ID: <strong>{cra_id}</strong></li>"
                f"<li>Jours travaillés: <strong>{jours_travailles} jour(s)</strong></li>"
                f"<li>TJM: <strong>{tjm}€</strong></li>"
                f"<li>Montant base: <strong>{montant_prestataire:.2f}€</strong></li>"
                f"</ul>"
                f"</div>"
                f"<div style='margin: 16px 0; padding: 12px; background: #fff7e6; border-radius: 4px; border-left: 4px solid #faad14;'>"
                f"<p style='margin: 0 0 8px 0;'><strong>💰 FACTURES GÉNÉRÉES AUTOMATIQUEMENT:</strong></p>"
                f"<ol style='margin: 8px 0; padding-left: 20px;'>"
                f"<li><strong>Facture Client → MITC:</strong> {montant_client:.2f}€ "
                f"<span style='color: #52c41a;'>(+{commission_percentage}% commission = {commission_mitc:.2f}€)</span></li>"
                f"<li><strong>Facture MITC → ESN ({esn_name}):</strong> {montant_prestataire - commission_mitc:.2f}€ "
                f"<span style='color: #1890ff;'>(montant prestataire)</span></li>"
                f"</ol>"
                f"</div>"
                f"<div style='margin-top: 16px;'>"
                f"<a href='{cra_link}' style='display: inline-block; margin: 8px 8px 8px 0; padding: 10px 20px; "
                f"background: #1890ff; color: white; text-decoration: none; border-radius: 4px;'>📋 Voir les CRA</a>"
                f"<a href='{invoice_link}' style='display: inline-block; margin: 8px 8px 8px 0; padding: 10px 20px; "
                f"background: #52c41a; color: white; text-decoration: none; border-radius: 4px;'>💰 Gérer les factures</a>"
                f"</div>"
            )
            
            # Send notification to all admins
            notifications_sent = 0
            for admin in admins:
                send_notification(
                    user_id=client_id,  # Client triggered the event
                    dest_id=admin.ID_Admin,  # Notification goes to admin
                    message=admin_message,
                    categorie="Admin",
                    event="CRA Validé - Factures Créées",
                    event_id=cra_id
                )
                notifications_sent += 1
            
            print(f"✅ Sent {notifications_sent} admin notifications for CRA {cra_id}")
            print(f"   Client: {client_name}, Consultant: {consultant_name}, Period: {periode}")
            print(f"   Amount: {montant_total}€ ({jours_travailles} days × {tjm}€)")
            
            return JsonResponse({
                "status": True,
                "message": f"Admin notifications sent successfully to {notifications_sent} admin(s)",
                "details": {
                    "cra_id": cra_id,
                    "notifications_sent": notifications_sent,
                    "montant_client": round(montant_client, 2),
                    "montant_esn": round(montant_prestataire - commission_mitc, 2),
                    "commission": round(commission_mitc, 2)
                }
            }, safe=False)
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ Error in notify_cra_validation_admin: {str(e)}")
            print(error_trace)
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
    
    return JsonResponse({
        "status": False,
        "message": "Only POST method is allowed"
    }, safe=False, status=405)

@csrf_exempt
def get_appel_offre_by_id(request, appel_offre_id):
    """
    API endpoint to retrieve a specific appel d'offre by its ID.
    """
    if request.method == 'GET':
        try:
            # Get the appel d'offre by ID
            appel_offre = AppelOffre.objects.get(id=appel_offre_id)
            
            # Serialize the appel d'offre data
            serializer = AppelOffreSerializer(appel_offre)
            
            # Get client information to enrich the response
            try:
                client = Client.objects.get(ID_clt=appel_offre.client_id)
                client_name = client.raison_sociale
            except Client.DoesNotExist:
                client_name = "Client non trouvé"
                
            # Enhance the response data
            data = serializer.data
            data['client_name'] = client_name
            
            # Count candidatures for this appel d'offre
            candidatures_count = Candidature.objects.filter(AO_id=appel_offre_id).count()
            data['candidatures_count'] = candidatures_count
            
            return JsonResponse({
                "status": True,
                "data": data
            }, safe=False)
            
        except AppelOffre.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "Appel d'offre non trouvé"
            }, safe=False, status=404)
            
        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Seule la méthode GET est autorisée"
    }, safe=False, status=405)

@csrf_exempt
def get_bon_de_commande_by_id(request, bdc_id):
    """
    API endpoint to retrieve a specific bon de commande by its ID.
    """
    if request.method == 'GET':
        try:
            # Get the bon de commande by ID
            bdc = Bondecommande.objects.get(id_bdc=bdc_id)
            
            # Serialize the bon de commande data
            serializer = BondecommandeSerializer(bdc)
            data = serializer.data
            
            # Get related data to enrich the response
            try:
                # Get candidature information
                candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                
                # Get appel d'offre information
                appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                
                # Get client information
                client = Client.objects.get(ID_clt=appel_offre.client_id)
                
                # Get ESN information
                esn = ESN.objects.get(ID_ESN=candidature.esn_id)
                
                # Add related data to response
                data['project_title'] = appel_offre.titre
                data['client_name'] = client.raison_sociale
                data['client_id'] = client.ID_clt
                data['esn_name'] = esn.Raison_sociale
                data['esn_id'] = esn.ID_ESN
                
            except (Candidature.DoesNotExist, AppelOffre.DoesNotExist, Client.DoesNotExist, ESN.DoesNotExist):
                # Continue even if related data is not found
                pass
            
            return JsonResponse({
                "status": True,
                "data": data
            }, safe=False)
            
        except Bondecommande.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "Bon de commande non trouvé"
            }, safe=False, status=404)
            
        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Seule la méthode GET est autorisée"
    }, safe=False, status=405)
    
    
    
@csrf_exempt
def collaborateur_login(request):
    if request.method == "POST":
        data = JSONParser().parse(request)
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return JsonResponse({
                "success": False, 
                "msg": "Email and password are required"
            }, safe=False)

        try:
            collaborateur = Collaborateur.objects.get(email=email)
            
            # Password check with SHA1 hash
            pwd_utf = password.encode()
            pwd_sh = hashlib.sha1(pwd_utf)
            password_crp = pwd_sh.hexdigest()
            
            if collaborateur.password == password_crp:
                # Serialize collaborateur data
                collaborateur_serializer = CollaborateurSerializer(collaborateur)
                
                # Create JWT token
                payload = {
                    'id': collaborateur.ID_collab,
                    'email': collaborateur.email,
                    'role': 'collaborateur'
                }
                token = jwt.encode(payload, 'maghrebIt', algorithm='HS256')
                
                response = JsonResponse({
                    "success": True, 
                    "token": token, 
                    "data": collaborateur_serializer.data
                }, safe=False)
                
                response.set_cookie(key='jwt', value=token, max_age=86400)
                
                return response
            
            return JsonResponse({
                "success": False, 
                "msg": "Invalid password"
            }, safe=False)
        
        except Collaborateur.DoesNotExist:
            return JsonResponse({
                "success": False, 
                "msg": "Collaborateur not found"
            }, safe=False)
    
    return JsonResponse({
        "success": False, 
        "msg": "Only POST method is allowed"
    }, safe=False, status=405)
    
    
    

    """
    API endpoint to authenticate a consultant
    """
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            email = data.get('email')
            password = data.get('password')
            
            if not email or not password:
                return JsonResponse({"status": False, "message": "Email et mot de passe requis"}, safe=False)
            
            # Hash the password
            pwd_utf = password.encode()
            pwd_hash = hashlib.sha1(pwd_utf).hexdigest()
            
            try:
                consultant = Collaborateur.objects.get(email=email, password=pwd_hash)
                
                # Generate a token
                token = jwt.encode({
                    'id': consultant.ID_collab,
                    'email': consultant.email,
                    'role': 'consultant',
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
                }, 'maghrebIt', algorithm='HS256')
                
                # Update the token in the database
                consultant.token = token
                consultant.save()
                
                # Prepare the response
                consultant_data = CollaborateurSerializer(consultant).data
                
                return JsonResponse({
                    "status": True,
                    "message": "Authentification réussie",
                    "token": token,
                    "consultant_id": consultant.ID_collab,
                    "data": consultant_data
                }, safe=False)
                
            except Collaborateur.DoesNotExist:
                return JsonResponse({"status": False, "message": "Email ou mot de passe incorrect"}, safe=False)
                
        except Exception as e:
            print(f"Erreur: {e}")  # Pour le débogage
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False)



@csrf_exempt
def get_consultant_profile(request, consultant_id):
    """
    API endpoint to get or update a consultant's personal information.
    GET: Returns the consultant's profile information
    PUT: Updates the consultant's profile information
    """
    if request.method == 'GET':
        try:
            # Get the consultant by ID
            consultant = Collaborateur.objects.get(ID_collab=consultant_id)
            
            # Serialize the consultant data
            consultant_serializer = CollaborateurSerializer(consultant)
            
            # Get ESN information if available
            esn_data = None
            if consultant.ID_ESN:
                try:
                    esn = ESN.objects.get(ID_ESN=consultant.ID_ESN)
                    esn_data = {
                        "id": esn.ID_ESN,
                        "name": esn.Raison_sociale
                    }
                except ESN.DoesNotExist:
                    pass
            
            return JsonResponse({
                "status": True,
                "data": {
                    **consultant_serializer.data,
                    "esn": esn_data
                }
            }, safe=False)
            
        except Collaborateur.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "Consultant not found"
            }, safe=False, status=404)
            
        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    elif request.method == 'PUT':
        try:
            # Parse the data from the request
            data = JSONParser().parse(request)
            
            # Get the consultant by ID
            consultant = Collaborateur.objects.get(ID_collab=consultant_id)
            
            # If password is in the data, hash it
            if 'password' in data and data['password']:
                pwd_utf = data['password'].encode()
                pwd_sh = hashlib.sha1(pwd_utf)
                password_crp = pwd_sh.hexdigest()
                data['password'] = password_crp
            else:
                # Remove password from data if empty
                data.pop('password', None)
            
            # Update consultant data
            consultant_serializer = CollaborateurSerializer(consultant, data=data, partial=True)
            
            if consultant_serializer.is_valid():
                consultant_serializer.save()
                return JsonResponse({
                    "status": True,
                    "message": "Profile updated successfully",
                    "data": consultant_serializer.data
                }, safe=False)
            
            return JsonResponse({
                "status": False,
                "message": "Failed to update profile",
                "errors": consultant_serializer.errors
            }, safe=False, status=400)
            
        except Collaborateur.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "Consultant not found"
            }, safe=False, status=404)
            
        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def get_consultant_dashboard(request, consultant_id):
    """
    API endpoint to get dashboard data for a consultant, including:
    - Profile information
    - Projects
    - Notifications
    - Statistics
    """
    if request.method == 'GET':
        try:
            # Get the consultant by ID
            consultant = Collaborateur.objects.get(ID_collab=consultant_id)
            
            # Serialize the consultant data
            consultant_serializer = CollaborateurSerializer(consultant)

            # Find the ESN that the consultant belongs to
            esn_id = consultant.ID_ESN
            esn_name = None
            
            try:
                esn = ESN.objects.get(ID_ESN=esn_id)
                esn_name = esn.Raison_sociale
            except ESN.DoesNotExist:
                pass
            
            # Get consultant's projects through candidatures
            candidatures = Candidature.objects.filter(id_consultant=consultant_id)
            
            projects_data = []
            
            # For each candidature, get the associated project (AppelOffre)
            for candidature in candidatures:
                try:
                    project = AppelOffre.objects.get(id=candidature.AO_id)
                    
                    # Get client information
                    client_name = "Unknown Client"
                    try:
                        client = Client.objects.get(ID_clt=project.client_id)
                        client_name = client.raison_sociale
                    except Client.DoesNotExist:
                        pass
                    
                    # Determine project status
                    project_status = candidature.statut
                    if project_status == "Sélectionnée":
                        project_status = "En cours"
                    
                    # Determine if there's a contract
                    has_contract = False
                    contract_data = None
                    
                    try:
                        contract = Contrat.objects.filter(candidature_id=candidature.id_cd).first()
                        if contract:
                            has_contract = True
                            contract_data = {
                                "id": contract.id_contrat,
                                "numero": contract.numero_contrat,
                                "date_debut": contract.date_debut,
                                "date_fin": contract.date_fin,
                                "montant": contract.montant,
                                "statut": contract.statut
                            }
                    except:
                        pass
                    
                    # Create project data structure
                    project_data = {
                        "id": project.id,
                        "name": project.titre,
                        "client": client_name,
                        "client_id": project.client_id,
                        "status": project_status,
                        "deadline": project.date_limite,
                        "start_date": project.date_debut,
                        "progress": 0,  # Would need additional logic to calculate
                        "priority": "Élevé" if candidature.statut == "Sélectionnée" else "Moyen",
                        "description": project.description or "",
                        "technologies": project.profil.split(",") if project.profil else [],
                        "candidature_id": candidature.id_cd,
                        "tjm": float(candidature.tjm),
                        "has_contract": has_contract,
                        "contract": contract_data
                    }
                    
                    projects_data.append(project_data)
                    
                except (AppelOffre.DoesNotExist, Exception) as e:
                    # Skip if project not found or other error
                    print(f"Error getting project data: {str(e)}")
                    continue
            
            # Get notifications for the consultant
            notifications_queryset = Notification.objects.filter(
                dest_id=consultant_id
            ).order_by('-created_at')
            
            # Count unread notifications BEFORE slicing
            unread_count = notifications_queryset.filter(status="Not_read").count()
            
            # Now get the latest 10 notifications
            notifications = notifications_queryset[:10]
            
            notification_serializer = NotificationSerializer(notifications, many=True)
            
            # Create statistics data
            stats = {
                "projectsCount": len(projects_data),
                "activeProjects": len([p for p in projects_data if p["status"] == "En cours"]),
                "completedProjects": len([p for p in projects_data if p["status"] == "Terminé"]),
                "totalTJM": sum(p["tjm"] for p in projects_data),
                "unreadNotifications": unread_count,
            }
            
            # Return the complete dashboard data
            return JsonResponse({
                "status": True,
                "data": {
                    "consultant": {
                        **consultant_serializer.data,
                        "esn_name": esn_name
                    },
                    "projects": projects_data,
                    "notifications": notification_serializer.data,
                    "stats": stats
                }
            }, safe=False)
            
        except Collaborateur.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "Consultant not found"
            }, safe=False, status=404)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    

@csrf_exempt
def cra_imputation_view(request, id=0):
    """
    API endpoint for handling CRA imputation entries (daily work/leave records)
    - GET: Retrieve all imputations or a specific one by ID
    - POST: Create a new imputation entry (auto-creates CRA_CONSULTANT for tracking)
    - PUT: Update an existing imputation
    - DELETE: Remove an imputation
    """
    if request.method == 'GET':
        if id > 0:
            # Get specific imputation
            imputations = CRA_imputation.objects.filter(id_imputation=id)
        else:
            # Get all imputations
            imputations = CRA_imputation.objects.all()
            
        imputation_serializer = CRA_imputationSerializer(imputations, many=True)
        return JsonResponse({"total": len(imputation_serializer.data), "data": imputation_serializer.data}, safe=False)
    
    elif request.method == 'POST':
        imputation_data = JSONParser().parse(request)
        
        # Extract key fields for validation
        consultant_id = imputation_data.get('id_consultan')
        period = imputation_data.get('période')
        bdc_id = imputation_data.get('id_bdc', 0)
        
        if not consultant_id or not period:
            return JsonResponse({
                "status": False,
                "msg": "consultant_id and period are required"
            }, safe=False)
        
        try:
            # Get consultant information to determine ESN
            consultant = Collaborateur.objects.get(ID_collab=consultant_id)
            esn_id = consultant.ID_ESN
            
            # Validate that the ESN exists if provided
            if esn_id:
                try:
                    ESN.objects.get(ID_ESN=esn_id)
                except ESN.DoesNotExist:
                    return JsonResponse({
                        "status": False,
                        "msg": f"ESN with ID {esn_id} does not exist"
                    }, safe=False)
            
            # Initialize client_id as 0 (default for non-project work like leaves)
            client_id = 0
            
            # Only try to get client info if BDC is provided and not 0
            if bdc_id and str(bdc_id).strip() not in ["", "0"]:
                try:
                    bon_de_commande = Bondecommande.objects.get(id_bdc=bdc_id)
                    
                    # Trace through candidature to resolve project/client details
                    candidature = None
                    if bon_de_commande.candidature_id:
                        candidature = Candidature.objects.filter(id_cd=bon_de_commande.candidature_id).first()

                    if candidature and candidature.AO_id:
                        appel_offre = AppelOffre.objects.filter(id=candidature.AO_id).first()

                        if appel_offre and appel_offre.client_id:
                            try:
                                Client.objects.get(ID_clt=appel_offre.client_id)
                                client_id = appel_offre.client_id
                            except Client.DoesNotExist:
                                print(
                                    f"Warning: Client with ID {appel_offre.client_id} does not exist, using default client_id=0"
                                )

                    # Ensure we store the canonical BDC identifier from the database
                    bdc_id = bon_de_commande.id_bdc
                    
                except Bondecommande.DoesNotExist:
                    # BDC doesn't exist - this might be an AppelOffre ID for projects without real BDC
                    # Try to get client info from AppelOffre directly
                    print(f"Info: BDC with ID {bdc_id} not found, treating as AppelOffre ID")
                    try:
                        appel_offre = AppelOffre.objects.get(id=bdc_id)
                        if appel_offre.client_id:
                            try:
                                Client.objects.get(ID_clt=appel_offre.client_id)
                                client_id = appel_offre.client_id
                            except Client.DoesNotExist:
                                print(f"Warning: Client with ID {appel_offre.client_id} does not exist")
                    except AppelOffre.DoesNotExist:
                        # Neither BDC nor AppelOffre exists with this ID, but still save the imputation
                        print(f"Warning: Neither BDC nor AppelOffre found with ID {bdc_id}, saving imputation with provided id_bdc")
            
            # Set the validated values
            imputation_data['id_client'] = client_id
            imputation_data['id_esn'] = esn_id or 0
            imputation_data['id_bdc'] = bdc_id
        
        except Collaborateur.DoesNotExist:
            return JsonResponse({
                "status": False,
                "msg": f"Consultant with ID {consultant_id} does not exist"
            }, safe=False)
        
        try:
            # ENHANCED CRA_CONSULTANT CREATION LOGIC
            # Check for EXACT match: consultant + period + project (id_bdc)
            # This ensures each unique combination gets its own CRA_CONSULTANT record
            
            # Normalize bdc_id for consistent database storage
            normalized_bdc_id = bdc_id if bdc_id != 0 else None
            
            existing_cra_consultant = CRA_CONSULTANT.objects.filter(
                id_consultan=consultant_id,
                période=period,
                id_bdc=normalized_bdc_id
            ).first()
            
            # Create the CRA imputation first
            imputation_serializer = CRA_imputationSerializer(data=imputation_data)
            
            if imputation_serializer.is_valid():
                imputation = imputation_serializer.save()
                
                # Create or update CRA_CONSULTANT based on the EXACT combination (period, consultant, project)
                if not existing_cra_consultant:
                    try:
                        # Create description for different cases
                        if normalized_bdc_id:
                            commentaire = f"CRA créé automatiquement pour le projet {normalized_bdc_id} - période {period} (Consultant: {consultant_id})"
                        else:
                            commentaire = f"CRA créé automatiquement pour activités non-projet - période {period} (Consultant: {consultant_id})"
                        
                        # Count total working days for this EXACT combination (consultant + period + project)
                        # IMPORTANT: Only count 'travail' type entries, not absences/leaves
                        period_imputations = CRA_imputation.objects.filter(
                            id_consultan=consultant_id,
                            période=period,
                            id_bdc=bdc_id,  # Count only for this specific project combination
                            type='travail'  # Only count work days, not absences/leaves
                        )
                        n_jour = period_imputations.count()  # Current count including the just-created imputation
                        
                        # Create CRA_CONSULTANT record for this specific combination
                        cra_consultant = CRA_CONSULTANT.objects.create(
                            id_bdc=normalized_bdc_id,  # Use the normalized project ID or None for non-project
                            n_jour=n_jour,  # Total number of working days for this combination
                            commentaire=commentaire,
                            id_consultan=consultant_id,
                            id_client=client_id if client_id != 0 else None,  # Add client_id
                            id_esn=esn_id,  # Add esn_id
                            période=period,
                            statut='saisi'  # Initial status
                        )
                        
                        # Add CRA_CONSULTANT info to response
                        response_data = {
                            **imputation_serializer.data,
                            "cra_consultant_created": True,
                            "cra_consultant_id": cra_consultant.id_CRA,
                            "cra_status": cra_consultant.statut,
                            "cra_bdc_id": normalized_bdc_id,
                            "cra_n_jour": n_jour,
                            "reason": f"New CRA_CONSULTANT created for unique combination: consultant={consultant_id}, period={period}, project={normalized_bdc_id}"
                        }
                        
                        # Send notification to ESN when CRA is first created
                        if ENABLE_CRA_CREATION_ESN_NOTIFICATION:
                            try:
                                consultant_name = f"{consultant.Nom} {consultant.Prenom}"
                                project_info = f"projet {normalized_bdc_id}" if normalized_bdc_id else "activités non-projet"
                                
                                send_notification(
                                    user_id=consultant_id,
                                    dest_id=esn_id,
                                    message=f"{consultant_name} a créé un CRA pour la période {period} ({project_info}).",
                                    categorie="ESN",
                                    event="Création CRA",
                                    event_id=cra_consultant.id_CRA
                                )
                            except Exception as notif_error:
                                print(f"Warning: Failed to send CRA creation notification: {str(notif_error)}")
                        
                    except Exception as cra_error:
                        # If CRA_CONSULTANT creation fails, log but don't fail the imputation
                        print(f"Failed to create CRA_CONSULTANT: {str(cra_error)}")
                        response_data = {
                            **imputation_serializer.data,
                            "cra_consultant_created": False,
                            "cra_error": str(cra_error)
                        }
                else:
                    # CRA_CONSULTANT already exists for this EXACT combination - update the day count
                    try:
                        # Recount total working days for this EXACT combination
                        # IMPORTANT: Only count 'travail' type entries, not absences/leaves
                        period_imputations = CRA_imputation.objects.filter(
                            id_consultan=consultant_id,
                            période=period,
                            id_bdc=bdc_id,  # Count only for this specific project combination
                            type='travail'  # Only count work days, not absences/leaves
                        )
                        n_jour = period_imputations.count()
                        
                        # Update the existing CRA_CONSULTANT
                        existing_cra_consultant.n_jour = n_jour
                        existing_cra_consultant.save()
                        
                        response_data = {
                            **imputation_serializer.data,
                            "cra_consultant_created": False,
                            "cra_consultant_updated": True,
                            "cra_consultant_id": existing_cra_consultant.id_CRA,
                            "cra_status": existing_cra_consultant.statut,
                            "cra_bdc_id": existing_cra_consultant.id_bdc,
                            "cra_n_jour": n_jour,
                            "reason": f"CRA_CONSULTANT already exists for combination: consultant={consultant_id}, period={period}, project={normalized_bdc_id}, updated day count"
                        }
                    except Exception as update_error:
                        print(f"Failed to update CRA_CONSULTANT: {str(update_error)}")
                        response_data = {
                            **imputation_serializer.data,
                            "cra_consultant_created": False,
                            "cra_consultant_updated": False,
                            "cra_consultant_id": existing_cra_consultant.id_CRA,
                            "cra_status": existing_cra_consultant.statut,
                            "cra_bdc_id": existing_cra_consultant.id_bdc,
                            "reason": f"CRA_CONSULTANT exists for combination: consultant={consultant_id}, period={period}, project={normalized_bdc_id}"
                        }
                
                return JsonResponse({
                    "status": True,
                    "msg": "Added Successfully!",
                    "data": response_data
                }, safe=False)
                
            return JsonResponse({
                "status": False,
                "msg": "Failed to Add",
                "errors": imputation_serializer.errors
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "msg": f"Error creating imputation: {str(e)}"
            }, safe=False, status=500)
    
    elif request.method == 'PUT':
        try:
            imputation_data = JSONParser().parse(request)
            
            # Use the ID from URL parameter instead of requiring it in request body
            if id == 0:
                return JsonResponse({
                    "status": False,
                    "msg": "Imputation ID is required in URL for updating"
                }, safe=False, status=400)
            
            imputation = CRA_imputation.objects.get(id_imputation=id)
            
            # Only update CRA_imputation fields, exclude any CRA_CONSULTANT fields
            allowed_fields = [
                'id_imputation', 'id_consultan', 'période', 'jour', 'type', 
                'Durée', 'id_client', 'id_esn', 'id_bdc', 'commentaire',
                'statut', 'type_imputation'  # Added statut and type_imputation for CRA submission
            ]
            
            # Filter data to only include allowed imputation fields
            filtered_data = {key: value for key, value in imputation_data.items() if key in allowed_fields}
            
            imputation_serializer = CRA_imputationSerializer(imputation, data=filtered_data, partial=True)
            
            if imputation_serializer.is_valid():
                imputation_serializer.save()
                
                return JsonResponse({
                    "status": True,
                    "msg": "Updated Successfully!",
                    "data": imputation_serializer.data
                }, safe=False)
                
            return JsonResponse({
                "status": False,
                "msg": "Failed to Update",
                "errors": imputation_serializer.errors
            }, safe=False)
            
        except CRA_imputation.DoesNotExist:
            return JsonResponse({
                "status": False,
                "msg": "Imputation not found"
            }, safe=False, status=404)
            
        except Exception as e:
            return JsonResponse({
                "status": False,
                "msg": f"Error updating imputation: {str(e)}"
            }, safe=False, status=500)
    
    elif request.method == 'DELETE':
        try:
            # Get the imputation to be deleted
            imputation = CRA_imputation.objects.get(id_imputation=id)
            
            # Store information needed for CRA_CONSULTANT update
            consultant_id = imputation.id_consultan
            period = imputation.période
            bdc_id = imputation.id_bdc
            
            # Delete the imputation
            imputation.delete()
            
            # Update the related CRA_CONSULTANT day count
            try:
                # Normalize bdc_id for consistent database lookup
                normalized_bdc_id = bdc_id if bdc_id != 0 else None
                
                # Find the CRA_CONSULTANT record for this combination
                cra_consultant = CRA_CONSULTANT.objects.filter(
                    id_consultan=consultant_id,
                    période=period,
                    id_bdc=normalized_bdc_id
                ).first()
                
                if cra_consultant:
                    # Recount the remaining imputations for this combination
                    # IMPORTANT: Only count 'travail' type entries, not absences/leaves
                    remaining_imputations = CRA_imputation.objects.filter(
                        id_consultan=consultant_id,
                        période=period,
                        id_bdc=bdc_id,
                        type='travail'  # Only count work days, not absences/leaves
                    )
                    new_count = remaining_imputations.count()
                    
                    if new_count > 0:
                        # Update the day count
                        cra_consultant.n_jour = new_count
                        cra_consultant.save()
                    else:
                        # If no imputations left, optionally delete the CRA_CONSULTANT record
                        # or keep it with 0 days - depending on business requirements
                        cra_consultant.n_jour = 0
                        cra_consultant.save()
                        # cra_consultant.delete()  # Uncomment if you want to delete empty CRA records
                        
            except Exception as cra_update_error:
                print(f"Warning: Failed to update CRA_CONSULTANT after deletion: {str(cra_update_error)}")
                # Don't fail the deletion if CRA update fails
            
            return JsonResponse({
                "status": True,
                "msg": "Deleted Successfully!"
            }, safe=False)
            
        except CRA_imputation.DoesNotExist:
            return JsonResponse({
                "status": False,
                "msg": "Imputation not found"
            }, safe=False, status=404)
            
        except Exception as e:
            return JsonResponse({
                "status": False,
                "msg": f"Error deleting imputation: {str(e)}"
            }, safe=False, status=500)
    
    # If none of the above methods match, return method not allowed
    return JsonResponse({
        "status": False,
        "msg": "Method not allowed"
    }, safe=False, status=405)

def cra_imputations_by_consultant(request, consultant_id):
    """
    Retrieve all CRA imputations for a specific consultant.
    Supports filtering by période, client, or bon de commande.
    """
    if request.method == 'GET':
        # Base query for the consultant
        print(f"Consultant ID: {consultant_id}")
        query = CRA_imputation.objects.filter(id_consultan=consultant_id)
        
        # Apply additional filters if present
        period = request.GET.get('période')
        if period:
            query = query.filter(période=period)
            
        client_id = request.GET.get('id_client')
        if client_id:
            query = query.filter(id_client=client_id)
            
        bdc_id = request.GET.get('id_bdc')
        if bdc_id:
            query = query.filter(id_bdc=bdc_id)
        
        # Order by date (recently added first)
        query = query.order_by('-id_imputation')
        
        imputation_serializer = CRA_imputationSerializer(query, many=True)
        
        return JsonResponse({
            "status": True,
            "total": len(imputation_serializer.data),
            "data": imputation_serializer.data
        }, safe=False)
        
    return JsonResponse({
        "status": False,
        "msg": "Method not allowed"
    }, safe=False, status=405)

def validate_ndf_date_in_bdc_period(periode, jour, id_bdc):
    """
    Validate that the expense report date (periode + jour) falls within the BDC period.
    
    Args:
        periode (str): Period in MM_YYYY format (e.g., "06_2025")
        jour (int): Day of the month (1-31)
        id_bdc (int): BDC ID to check against
        
    Returns:
        tuple: (is_valid, error_message)
    """
    from datetime import datetime
    
    try:
        # Get the BDC record
        try:
            bdc = Bondecommande.objects.get(id_bdc=id_bdc)
        except Bondecommande.DoesNotExist:
            return False, f"Le BDC avec l'ID {id_bdc} n'existe pas."
        
        # Check if BDC has valid date range
        if not bdc.date_debut or not bdc.date_fin:
            return False, f"Le BDC {bdc.numero_bdc or id_bdc} n'a pas de période définie (dates manquantes)."
        
        # Parse the expense report date
        try:
            month, year = periode.split('_')
            month = int(month)
            year = int(year)
            day = int(jour)
            
            # Create the expense date
            expense_date = datetime(year, month, day).date()
            
        except (ValueError, AttributeError):
            return False, f"Format de date invalide: période={periode}, jour={jour}"
        
        # Validate that the expense date is within BDC period
        if expense_date < bdc.date_debut:
            return False, f"La date de la note de frais ({expense_date.strftime('%d/%m/%Y')}) est antérieure au début du BDC ({bdc.date_debut.strftime('%d/%m/%Y')})."
        
        if expense_date > bdc.date_fin:
            return False, f"La date de la note de frais ({expense_date.strftime('%d/%m/%Y')}) est postérieure à la fin du BDC ({bdc.date_fin.strftime('%d/%m/%Y')})."
        
        return True, None
        
    except Exception as e:
        return False, f"Erreur lors de la validation de la date: {str(e)}"

@csrf_exempt
def ndf_consultant_view(request, id=0):
    """
    Handle GET, POST, PUT, DELETE for NDF_CONSULTANT.
    - GET (id=0 optional): Retrieve all or specific record by query params or ID.
      e.g. /ndf-consultant-view/?consultant_id=123 or /ndf-consultant-view/10/
    - POST: Create new NDF_CONSULTANT record.
    - PUT: Update existing record by ID.
    - DELETE: Delete existing record by ID.
    """
    if request.method == 'GET':
        if id > 0:
            # Get single record by ID
            try:
                record = NDF_CONSULTANT.objects.get(pk=id)
                serializer = NDF_CONSULTANTSerializer(record)
                return JsonResponse({"status": True, "data": serializer.data}, safe=False)
            except NDF_CONSULTANT.DoesNotExist:
                return JsonResponse({"status": False, "message": "Record not found"}, safe=False, status=404)
        else:
            # Use filters if provided
            query = NDF_CONSULTANT.objects.all()
            
            consultant_id = request.GET.get('consultant_id')
            if consultant_id:
                query = query.filter(id_consultan=consultant_id)
                
            period = request.GET.get('period')
            if period:
                query = query.filter(période=period)
                
            status = request.GET.get('status')
            if status:
                query = query.filter(statut=status)
                
            esn_id = request.GET.get('esn_id')
            if esn_id:
                query = query.filter(id_esn=esn_id)
                
            client_id = request.GET.get('client_id')
            if client_id:
                query = query.filter(id_client=client_id)
                
            # Filter by responsable_id (commercial manager)
            responsable_id = request.GET.get('responsable_id')
            if responsable_id:
                # Find consultants who have candidatures directly assigned to this commercial
                # (where commercial_id = responsable_id in the same candidature row)
                consultants_for_commercial = Candidature.objects.filter(
                    commercial_id=responsable_id
                ).values_list('id_consultant', flat=True).distinct()
                
                if consultants_for_commercial:
                    # Filter NDFs by these consultants
                    query = query.filter(id_consultan__in=consultants_for_commercial)
                else:
                    # If no candidatures found for this commercial, return empty queryset
                    query = query.none()
                
            # Pagination
            limit = int(request.GET.get('limit', 100))
            offset = int(request.GET.get('offset', 0))
            
            total_count = query.count()
            query = query.order_by('-id_ndf')[offset:offset+limit]
            
            serializer = NDF_CONSULTANTSerializer(query, many=True)
            
            # Enhance with additional information
            enhanced_data = []
            for item in serializer.data:
                record = dict(item)
                
                # Add consultant info
                try:
                    consultant = Collaborateur.objects.get(ID_collab=record['id_consultan'])
                    record['consultant_name'] = f"{consultant.Prenom} {consultant.Nom}"
                except Collaborateur.DoesNotExist:
                    record['consultant_name'] = "Unknown Consultant"
                
                # Add client info
                if record.get('id_client'):
                    try:
                        client = Client.objects.get(ID_clt=record['id_client'])
                        record['client_name'] = client.raison_sociale
                        record['client_responsible'] = getattr(client, 'responsible', '') or ''
                    except Client.DoesNotExist:
                        record['client_name'] = "Unknown Client"
                        record['client_responsible'] = ""
                else:
                    record['client_responsible'] = ""
                
                # Add ESN info
                if record.get('id_esn'):
                    try:
                        esn = ESN.objects.get(ID_ESN=record['id_esn'])
                        record['esn_name'] = esn.Raison_sociale
                        record['esn_responsible'] = getattr(esn, 'responsible', '') or ''
                    except ESN.DoesNotExist:
                        record['esn_name'] = "Unknown ESN"
                        record['esn_responsible'] = ""
                else:
                    record['esn_responsible'] = ""
                
                # Project info through BDC -> Candidature -> AppelOffre chain
                if record.get('id_bdc'):
                    try:
                        bdc = Bondecommande.objects.get(id_bdc=record['id_bdc'])
                        candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                        appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                        record['project_name'] = appel_offre.titre
                        record['project_id'] = appel_offre.id
                        record['bdc_number'] = getattr(bdc, 'numero_bdc', '') or ''
                    except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, AppelOffre.DoesNotExist):
                        record['project_name'] = "Unknown Project"
                        record['project_id'] = None
                        record['bdc_number'] = ""
                else:
                    record['project_name'] = "No Project"
                    record['project_id'] = None
                    record['bdc_number'] = ""
                
                enhanced_data.append(record)
            
            return JsonResponse({
                "status": True,
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "data": enhanced_data
            }, safe=False)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        
        # If id_bdc is provided but id_esn or id_client is missing, try to get them from BDC
        if 'id_bdc' in data and data['id_bdc']:
            # Only fetch if either id_esn or id_client is missing
            if 'id_esn' not in data or 'id_client' not in data:
                try:
                    bdc_id = data['id_bdc']
                    # Get Bondecommande record
                    bdc = Bondecommande.objects.get(id_bdc=bdc_id)
                    
                    # Get Candidature from BDC
                    candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                    
                    # Get ESN ID from Candidature if missing
                    if 'id_esn' not in data and candidature.esn_id:
                        data['id_esn'] = candidature.esn_id
                    
                    # Get client ID from AppelOffre if missing
                    if 'id_client' not in data:
                        try:
                            ao = AppelOffre.objects.get(id=candidature.AO_id)
                            data['id_client'] = ao.client_id
                        except AppelOffre.DoesNotExist:
                            pass
                except (Bondecommande.DoesNotExist, Candidature.DoesNotExist):
                    # If lookup fails, continue with validation (which will fail if required fields are missing)
                    pass
        
        # Auto-calculate montant_ht from montant_ttc and taux_tva if provided
        if 'montant_ttc' in data and data['montant_ttc']:
            montant_ttc = float(data['montant_ttc'])
            taux_tva = float(data.get('taux_tva', 20.00))  # Default to 20% if not provided
            
            # Calculate HT: HT = TTC / (1 + taux_tva/100)
            montant_ht = round(montant_ttc / (1 + taux_tva / 100), 2)
            data['montant_ht'] = montant_ht
            
            # Ensure taux_tva is in the data
            if 'taux_tva' not in data:
                data['taux_tva'] = taux_tva
        
        # Validate that the expense date is within BDC period if BDC is specified
        if 'id_bdc' in data and data['id_bdc'] and 'période' in data and 'jour' in data:
            is_valid, error_message = validate_ndf_date_in_bdc_period(
                data['période'], 
                data['jour'], 
                data['id_bdc']
            )
            if not is_valid:
                return JsonResponse({
                    "status": False, 
                    "message": f"Validation de la période échouée: {error_message}"
                }, safe=False, status=400)
        
        serializer = NDF_CONSULTANTSerializer(data=data)
        if serializer.is_valid():
            ndf = serializer.save()
            
            # Get consultant and ESN information for notification
            try:
                consultant = Collaborateur.objects.get(ID_collab=ndf.id_consultan)
                esn_id = consultant.ID_ESN

                commercial_id = None
                if ndf.id_bdc:
                    try:
                        bdc = Bondecommande.objects.get(id_bdc=ndf.id_bdc)
                        candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                        commercial_id = candidature.commercial_id
                    except (Bondecommande.DoesNotExist, Candidature.DoesNotExist):
                        commercial_id = None

                if not commercial_id:
                    fallback_candidature = (
                        Candidature.objects.filter(id_consultant=ndf.id_consultan)
                        .exclude(commercial_id__isnull=True)
                        .exclude(commercial_id="")
                        .order_by("-id_cd")
                        .first()
                    )
                    if fallback_candidature:
                        commercial_id = fallback_candidature.commercial_id
                
                # Create a notification for the ESN manager
                type_frais = ndf.type_frais.capitalize()
                montant = ndf.montant_ttc
                message = (
                    f"Nouvelle note de frais ({type_frais}, {montant}€) soumise par {consultant.Nom} {consultant.Prenom}. "
                    f'<a href="/interface-en?menu=expense-reports-validation" class="notification-link">Voir les NDF</a>'
                )
                
                send_notification(
                    user_id=consultant.ID_collab,
                    dest_id=esn_id,
                    message=message,
                    categorie="ESN",
                    event="NDF soumise",
                    event_id=ndf.id_ndf
                )

                if commercial_id:
                    send_notification(
                        user_id=consultant.ID_collab,
                        dest_id=commercial_id,
                        message=(
                            f"{consultant.Nom} {consultant.Prenom} a soumis une note de frais ({type_frais}, {montant}€). "
                            f'<a href="/interface-co?menu=expense-reports-validation" class="notification-link">Voir les NDF</a>'
                        ),
                        categorie="COMMERCIAL",
                        event="NDF soumise",
                        event_id=ndf.id_ndf
                    )
                
            except Collaborateur.DoesNotExist:
                pass
            
            return JsonResponse({
                "status": True,
                "msg": "Added Successfully!",
                "data": serializer.data
            }, safe=False, status=201)
        return JsonResponse({"status": False, "errors": serializer.errors}, safe=False, status=400)
        
    elif request.method == 'PUT':
        if id <= 0:
            return JsonResponse({"status": False, "message": "ID parameter is required for update"}, safe=False, status=400)

        data = JSONParser().parse(request)
        try:
            record = NDF_CONSULTANT.objects.get(pk=id)
            
            # Store old status for comparison
            old_status = record.statut
            
            # Auto-calculate montant_ht from montant_ttc and taux_tva if TTC is being updated
            if 'montant_ttc' in data and data['montant_ttc']:
                montant_ttc = float(data['montant_ttc'])
                # Use new taux_tva if provided, otherwise use existing value
                taux_tva = float(data.get('taux_tva', record.taux_tva))
                
                # Calculate HT: HT = TTC / (1 + taux_tva/100)
                montant_ht = round(montant_ttc / (1 + taux_tva / 100), 2)
                data['montant_ht'] = montant_ht
            elif 'taux_tva' in data:
                # If only taux_tva is being updated, recalculate HT with existing TTC
                montant_ttc = float(record.montant_ttc)
                taux_tva = float(data['taux_tva'])
                montant_ht = round(montant_ttc / (1 + taux_tva / 100), 2)
                data['montant_ht'] = montant_ht
            
            # Validate date if updating BDC, période, or jour
            # Use updated values if provided, otherwise use existing values
            periode_to_validate = data.get('période', record.période)
            jour_to_validate = data.get('jour', record.jour)
            bdc_to_validate = data.get('id_bdc', record.id_bdc)
            
            if bdc_to_validate and periode_to_validate and jour_to_validate:
                is_valid, error_message = validate_ndf_date_in_bdc_period(
                    periode_to_validate, 
                    jour_to_validate, 
                    bdc_to_validate
                )
                if not is_valid:
                    return JsonResponse({
                        "status": False, 
                        "message": f"Validation de la période échouée: {error_message}"
                    }, safe=False, status=400)
            
            serializer = NDF_CONSULTANTSerializer(record, data=data, partial=True)
            if serializer.is_valid():
                updated_ndf = serializer.save()
                
                # If status has changed to "validé" or "refusé", notify the consultant
                if 'statut' in data and data['statut'] != old_status:
                    new_status = data['statut']

                    commercial_id = None
                    if updated_ndf.id_bdc:
                        try:
                            bdc = Bondecommande.objects.get(id_bdc=updated_ndf.id_bdc)
                            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                            commercial_id = candidature.commercial_id
                        except (Bondecommande.DoesNotExist, Candidature.DoesNotExist):
                            commercial_id = None
                    
                    if new_status in ['validé', 'refusé', 'remboursé']:
                        try:
                            consultant = Collaborateur.objects.get(ID_collab=updated_ndf.id_consultan)
                            
                            # Create notification message
                            if new_status == 'validé':
                                message = (
                                    f"Votre note de frais de {updated_ndf.montant_ttc}€ ({updated_ndf.type_frais}) a été validée. "
                                    f'<a href="/interface-co?menu=expense-reports-management" class="notification-link">Voir mes NDF</a>'
                                )
                            elif new_status == 'refusé':
                                message = (
                                    f"Votre note de frais de {updated_ndf.montant_ttc}€ ({updated_ndf.type_frais}) a été refusée. "
                                    f'<a href="/interface-co?menu=expense-reports-management" class="notification-link">Voir mes NDF</a>'
                                )
                            else:  # remboursé
                                message = (
                                    f"Votre note de frais de {updated_ndf.montant_ttc}€ ({updated_ndf.type_frais}) a été remboursée. "
                                    f'<a href="/interface-co?menu=expense-reports-management" class="notification-link">Voir mes NDF</a>'
                                )
                            
                            # Send notification to consultant
                            send_notification(
                                user_id=updated_ndf.id_esn,
                                dest_id=consultant.ID_collab,
                                message=message,
                                categorie="Consultant",
                                event="Statut NDF modifié",
                                event_id=updated_ndf.id_ndf
                            )

                            if commercial_id:
                                if new_status == 'validé':
                                    commercial_message = (
                                        f"La note de frais de {consultant.Nom} {consultant.Prenom} ({updated_ndf.montant_ttc}€, {updated_ndf.type_frais}) a été validée. "
                                        f'<a href="/interface-co?menu=expense-reports-validation" class="notification-link">Voir les NDF</a>'
                                    )
                                elif new_status == 'refusé':
                                    commercial_message = (
                                        f"La note de frais de {consultant.Nom} {consultant.Prenom} ({updated_ndf.montant_ttc}€, {updated_ndf.type_frais}) a été refusée. "
                                        f'<a href="/interface-co?menu=expense-reports-validation" class="notification-link">Voir les NDF</a>'
                                    )
                                else:
                                    commercial_message = (
                                        f"La note de frais de {consultant.Nom} {consultant.Prenom} ({updated_ndf.montant_ttc}€, {updated_ndf.type_frais}) a été remboursée. "
                                        f'<a href="/interface-co?menu=expense-reports-validation" class="notification-link">Voir les NDF</a>'
                                    )

                                send_notification(
                                    user_id=updated_ndf.id_esn,
                                    dest_id=commercial_id,
                                    message=commercial_message,
                                    categorie="COMMERCIAL",
                                    event="Statut NDF modifié",
                                    event_id=updated_ndf.id_ndf
                                )
                            
                        except Collaborateur.DoesNotExist:
                            pass
                
                return JsonResponse({
                    "status": True,
                    "msg": "Updated Successfully!",
                    "data": serializer.data
                }, safe=False)
            return JsonResponse({"status": False, "errors": serializer.errors}, safe=False, status=400)
            
        except NDF_CONSULTANT.DoesNotExist:
            return JsonResponse({"status": False, "message": "Record not found"}, safe=False, status=404)
        
    elif request.method == 'DELETE':
        if id <= 0:
            return JsonResponse({"status": False, "message": "ID parameter is required for delete"}, safe=False, status=400)
        try:
            record = NDF_CONSULTANT.objects.get(pk=id)
            record.delete()
            return JsonResponse({"status": True, "message": f"Record {id} deleted."}, safe=False)
        except NDF_CONSULTANT.DoesNotExist:
            return JsonResponse({"status": False, "message": "Record not found"}, safe=False, status=404)
        
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def get_projects_by_consultant(request, consultant_id):
    if request.method == 'GET':
        try:
            # Verify the consultant exists
            consultant = Collaborateur.objects.get(ID_collab=consultant_id)
            
            # Get all candidatures for this consultant
            candidatures = Candidature.objects.filter(id_consultant=consultant_id)
            
            if not candidatures.exists():
                return JsonResponse({
                    "status": True,
                    "data": [],
                    "message": "No projects found for this consultant"
                }, safe=False)
            
            # Get all project IDs from these candidatures
            project_ids = candidatures.values_list('AO_id', flat=True)
            
            # Get all projects with these IDs
            projects = AppelOffre.objects.filter(id__in=project_ids)
            
            # Serialize project data
            project_serializer = AppelOffreSerializer(projects, many=True)
            
            # Enhance project data with additional information
            enhanced_projects = []
            for project in project_serializer.data:
                # Get client information for this project
                try:
                    client = Client.objects.get(ID_clt=project['client_id'])
                    client_name = client.raison_sociale
                except Client.DoesNotExist:
                    client_name = "Unknown Client"
                
                # Get candidature for this project and consultant
                candidature = candidatures.filter(AO_id=project['id']).first()
                candidature_data = None
                bdc_data = None
                
                if candidature:
                    candidature_serializer = CandidatureSerializer(candidature)
                    candidature_data = candidature_serializer.data
                    
                    # Get BDC for this project (AppelOffre)
                    # First try the consultant's own candidature, then look for any BDC linked to this project
                    try:
                        bdc = Bondecommande.objects.filter(candidature_id=candidature.id_cd).first()
                        
                        # If no BDC found for this candidature, look for any BDC linked to this AppelOffre
                        if not bdc:
                            # Find any candidature for this AppelOffre that has a BDC
                            all_project_candidatures = Candidature.objects.filter(AO_id=project['id'])
                            for proj_cand in all_project_candidatures:
                                bdc = Bondecommande.objects.filter(candidature_id=proj_cand.id_cd).first()
                                if bdc:
                                    break
                        
                        if bdc:
                            bdc_serializer = BondecommandeSerializer(bdc)
                            bdc_data = bdc_serializer.data
                    except Exception as bdc_error:
                        print(f"Error fetching BDC: {bdc_error}")
                        bdc_data = None
                
                # Get ESN name
                esn_name = "N/A"
                if candidature_data:
                    try:
                        esn = ESN.objects.get(ID_ESN=candidature_data['esn_id'])
                        esn_name = esn.Raison_sociale
                    except ESN.DoesNotExist:
                        esn_name = f"ESN {candidature_data['esn_id']}"
                
                # Add enhanced data
                enhanced_project = {
                    **project,
                    "client_name": client_name,
                    "candidature": candidature_data,
                    "bdc": bdc_data,
                    "esn_name": esn_name
                }
                
                enhanced_projects.append(enhanced_project)
            
            return JsonResponse({
                "status": True,
                "total": len(enhanced_projects),
                "data": enhanced_projects
            }, safe=False)
            
        except Collaborateur.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "Consultant not found"
            }, safe=False, status=404)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def get_cra_by_period(request):
    """
    Retrieve CRA imputations for a consultant filtered by period.
    Request parameters:
    - consultant_id: ID of the consultant
    - period: The period (format: MM_YYYY)
    """
    if request.method == 'GET':
        consultant_id = request.GET.get('consultant_id')
        period = request.GET.get('period')
        
        if not consultant_id or not period:
            return JsonResponse({
                "status": False,
                "message": "Both consultant_id and period parameters are required"
            }, safe=False, status=400)
            
        try:
            # Filter imputations by consultant and period
            imputations = CRA_imputation.objects.filter(
                id_consultan=consultant_id,
                période=period
            ).order_by('jour')
            
            # Serialize the data
            imputation_serializer = CRA_imputationSerializer(imputations, many=True)
            
            # Group by client and project (BDC)
            grouped_data = {}
            for imp in imputation_serializer.data:
                client_id = imp.get('id_client')
                bdc_id = imp.get('id_bdc')
                
                if client_id not in grouped_data:
                    grouped_data[client_id] = {
                        'client_id': client_id,
                        'projects': {}
                    }
                
                if bdc_id and bdc_id not in grouped_data[client_id]['projects']:
                    grouped_data[client_id]['projects'][bdc_id] = {
                        'bdc_id': bdc_id,
                        'imputations': []
                    }
                
                # Add imputation to appropriate group
                if bdc_id:
                    grouped_data[client_id]['projects'][bdc_id]['imputations'].append(imp)
                else:
                    # Handle non-project imputations (like leaves)
                    if 'other' not in grouped_data[client_id]:
                        grouped_data[client_id]['other'] = []
                    grouped_data[client_id]['other'].append(imp)
            
            # Convert projects dict to list for each client
            for client_id in grouped_data:
                if 'projects' in grouped_data[client_id]:
                    grouped_data[client_id]['projects'] = list(grouped_data[client_id]['projects'].values())
            
            return JsonResponse({
                "status": True,
                "period": period,
                "total": len(imputation_serializer.data),
                "data": imputation_serializer.data,
                "grouped_data": list(grouped_data.values())
            }, safe=False)
            
        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def get_projects_by_consultant_period(request):
    """
    Retrieve projects for a consultant filtered by period.
    Request parameters:
    - consultant_id: ID of the consultant
    - period: The period (format: MM_YYYY)
    """
    if request.method == 'GET':
        consultant_id = request.GET.get('consultant_id')
        period = request.GET.get('period')
        
        if not consultant_id or not period:
            return JsonResponse({
                "status": False,
                "message": "Both consultant_id and period parameters are required"
            }, safe=False, status=400)
            
        try:
            # Parse the period string to get month and year
            month, year = period.split('_')
            month_int = int(month)
            year_int = int(year)
            
            # Format for filtering date ranges (first and last day of month)
            first_day = f"{year}-{month.zfill(2)}-01"
            
            # Determine last day of month (accounting for different month lengths)
            if month_int in [4, 6, 9, 11]:
                last_day = f"{year}-{month.zfill(2)}-30"
            elif month_int == 2:
                # Simple leap year check
                is_leap = (year_int % 4 == 0 and year_int % 100 != 0) or (year_int % 400 == 0)
                last_day = f"{year}-{month.zfill(2)}-29" if is_leap else f"{year}-{month.zfill(2)}-28"
            else:
                last_day = f"{year}-{month.zfill(2)}-31"
            
            # Find all the imputations for this consultant in the specified period
            imputations = CRA_imputation.objects.filter(
                id_consultan=consultant_id,
                période=period,
                type='travail'  # Only consider work imputations, not leaves
            )
            
            # Get unique BDC IDs from these imputations
            bdc_ids_from_imputations = list(imputations.values_list('id_bdc', flat=True).distinct())
            
            # Get ALL candidatures for this consultant (with status Sélectionnée)
            all_candidatures = Candidature.objects.filter(
                id_consultant=consultant_id,
                statut='Sélectionnée'
            )
            
            # Also get candidatures that overlap with this period
            candidatures_in_period = all_candidatures.filter(
                date_disponibilite__lte=last_day
            )
            
            print(f"DEBUG: Consultant {consultant_id}, Period {period}")
            print(f"DEBUG: Found {len(bdc_ids_from_imputations)} BDCs from imputations")
            print(f"DEBUG: Found {candidatures_in_period.count()} candidatures in period")
            
            # Get BDCs for these candidatures (if they exist)
            all_bdcs = []
            for candidature in candidatures_in_period:
                bdcs = Bondecommande.objects.filter(candidature_id=candidature.id_cd)
                all_bdcs.extend(bdcs)
            
            print(f"DEBUG: Found {len(all_bdcs)} BDCs total")
            
            # Get project IDs from candidatures
            project_ids = candidatures_in_period.values_list('AO_id', flat=True).distinct()
            
            # Get the actual projects
            projects = AppelOffre.objects.filter(id__in=project_ids)
            
            # Serialize and enhance project data
            project_serializer = AppelOffreSerializer(projects, many=True)
            enhanced_projects = []
            
            for project in project_serializer.data:
                # Get client information
                try:
                    client = Client.objects.get(ID_clt=project['client_id'])
                    client_name = client.raison_sociale
                except Client.DoesNotExist:
                    client_name = "Unknown Client"
                
                # Get candidature(s) for this project and consultant
                project_candidatures = candidatures_in_period.filter(AO_id=project['id'])
                candidature_data = []
                
                for candidature in project_candidatures:
                    candidature_serializer = CandidatureSerializer(candidature)
                    candidature_data.append(candidature_serializer.data)
                
                # Get BDCs for these candidatures (if they exist)
                bdc_data = []
                
                for candidature in project_candidatures:
                    bdcs = Bondecommande.objects.filter(candidature_id=candidature.id_cd)
                    for bdc in bdcs:
                        bdc_serializer = BondecommandeSerializer(bdc)
                        bdc_data.append(bdc_serializer.data)
                
                # Get imputations for this project in this period
                project_imputations = []
                if bdc_data:
                    bdc_ids = [bdc['id_bdc'] for bdc in bdc_data]
                    for bdc_id in bdc_ids:
                        imp = imputations.filter(id_bdc=bdc_id)
                        project_imputations.extend(imp)
                
                # Calculate total days worked
                total_days = len(project_imputations)
                
                # Sum total hours worked
                total_hours = 0
                for imp in project_imputations:
                    try:
                        total_hours += float(imp.Durée)
                    except (ValueError, TypeError):
                        # Handle case where Durée might not be a valid number
                        pass
                
                # Add enhanced data
                enhanced_project = {
                    **project,
                    "client_name": client_name,
                    "candidatures": candidature_data,
                    "bdcs": bdc_data,
                    "period_data": {
                        "period": period,
                        "period_formatted": f"{month}/{year}",
                        "total_days": total_days,
                        "total_hours": total_hours,
                        "has_imputations": total_days > 0
                    }
                }
                
                enhanced_projects.append(enhanced_project)
            
            return JsonResponse({
                "status": True,
                "period": period,
                "period_formatted": f"{month}/{year}",
                "total": len(enhanced_projects),
                "data": enhanced_projects
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)

@csrf_exempt
def get_cra_by_esn_period(request):
    """
    Retrieve CRA imputations for all consultants of a specific ESN filtered by period.
    Includes consultant profile info and related project details.
    
    Request parameters:
    - esn_id: ID of the ESN
    - period: The period (format: MM_YYYY)
    """
    if request.method == 'GET':
        esn_id = request.GET.get('esn_id')
        period = request.GET.get('period')
        
        if not esn_id or not period:
            return JsonResponse({
                "status": False,
                "message": "Both esn_id and period parameters are required"
            }, safe=False, status=400)
            
        try:
            # Get all consultants for this ESN in a single query to minimize DB hits
            consultants = Collaborateur.objects.filter(ID_ESN=esn_id)
            consultant_dict = {c.ID_collab: c for c in consultants}
            
            if not consultants.exists():
                return JsonResponse({
                    "status": True,
                    "message": "No consultants found for this ESN",
                    "period": period,
                    "esn_id": esn_id,
                    "total": 0,
                    "data": []
                }, safe=False)
            
            consultant_ids = list(consultant_dict.keys())
            
            # Fetch all relevant imputations in a single query
            imputations = CRA_imputation.objects.filter(
                id_consultan__in=consultant_ids,
                période=period
            ).order_by('jour')
            
            # Extract unique AppelOffre IDs from imputations (stored in id_bdc field)
            appel_offre_ids = set(imp.id_bdc for imp in imputations if imp.id_bdc)
            
            # Fetch all AppelOffres in a single query
            appel_offres = {ao.id: ao for ao in AppelOffre.objects.filter(id__in=appel_offre_ids)}
            
            # Get candidature IDs from projects
            candidature_ids = []
            for ao_id in appel_offre_ids:
                if ao_id in appel_offres:
                    # Find candidatures related to this project and consultant
                    project_candidatures = Candidature.objects.filter(
                        AO_id=ao_id, 
                        id_consultant__in=consultant_ids
                    )
                    candidature_ids.extend([c.id_cd for c in project_candidatures])
            
            # Fetch all candidatures in a single query
            candidatures = {c.id_cd: c for c in Candidature.objects.filter(id_cd__in=candidature_ids)}
            
            # Get client IDs from imputations and projects
            client_ids = set(imp.id_client for imp in imputations if imp.id_client)
            client_ids.update(ao.client_id for ao in appel_offres.values() if ao.client_id)
            
            # Fetch all clients in a single query
            clients = {c.ID_clt: c for c in Client.objects.filter(ID_clt__in=client_ids)}
            
            # Process imputations and add related data
            result = []
            for imp in imputations:
                imp_data = CRA_imputationSerializer(imp).data
                
                # Add consultant info
                consultant_info = None
                if imp.id_consultan in consultant_dict:
                    consultant = consultant_dict[imp.id_consultan]
                    consultant_info = {
                        "id": consultant.ID_collab,
                        "nom": consultant.Nom,
                        "prenom": consultant.Prenom,
                        "email": consultant.email,
                        "poste": consultant.Poste
                    }
                
                # Add project and candidature info if available
                project_info = None
                candidature_info = None
                client_info = None
                
                # Add client info
                if imp.id_client and imp.id_client in clients:
                    client = clients[imp.id_client]
                    client_info = {
                        "id": client.ID_clt,
                        "raison_sociale": client.raison_sociale
                    }
                
                # Get project info directly (id_bdc is actually project/AO ID)
                if imp.id_bdc and imp.id_bdc in appel_offres:
                    project = appel_offres[imp.id_bdc]
                    project_info = {
                        "id": project.id,
                        "titre": project.titre,
                        "description": project.description,
                        "date_debut": project.date_debut,
                        "date_limite": project.date_limite
                    }
                    
                    # Find corresponding candidature if exists
                    related_candidatures = [
                        c for c in candidatures.values() 
                        if c.AO_id == imp.id_bdc and c.id_consultant == imp.id_consultan
                    ]
                    
                    if related_candidatures:
                        candidature = related_candidatures[0]
                        candidature_info = {
                            "id": candidature.id_cd,
                            "date_disponibilite": candidature.date_disponibilite,
                            "statut": candidature.statut,
                            "tjm": candidature.tjm
                        }
                
                # Create the enhanced imputation entry
                enhanced_imp = {
                    **imp_data,
                    "consultant": consultant_info,
                    "client": client_info,
                    "candidature": candidature_info,
                    "project": project_info
                }
                
                result.append(enhanced_imp)
            
            return JsonResponse({
                "status": True,
                "total": len(result),
                "period": period,
                "esn_id": esn_id,
                "data": result
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def get_cra_by_client_period(request):
    """
    Retrieve CRA imputations for all consultants working for a specific client filtered by period.
    Includes consultant profile info and related project details.
    Note: id_bdc field actually contains AppelOffre IDs.
    
    Request parameters:
    - client_id: ID of the client
    - period: The period (format: MM_YYYY)
    """
    if request.method == 'GET':
        client_id = request.GET.get('client_id')
        period = request.GET.get('period')
        
        if not client_id or not period:
            return JsonResponse({
                "status": False,
                "message": "Both client_id and period parameters are required"
            }, safe=False, status=400)
            
        try:
            # Get client information
            try:
                client = Client.objects.get(ID_clt=client_id)
                client_info = {
                    "id": client.ID_clt,
                    "name": client.raison_sociale
                }
            except Client.DoesNotExist:
                client_info = {"id": client_id, "name": f"Client {client_id}"}
            
            # Find all imputations for this client in the specified period
            # IMPORTANT: Only return 'travail' type entries for invoice calculation
            imputations = CRA_imputation.objects.filter(
                id_client=client_id,
                période=period,
                type='travail'  # Only work days, not absences/leaves
            ).order_by('jour')
            
            # If no imputations found, return early
            if not imputations.exists():
                return JsonResponse({
                    "status": True,
                    "message": "No imputations found for this client in the specified period",
                    "period": period,
                    "client": client_info,
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Extract consultant IDs and project/BDC IDs from imputations for efficient querying
            consultant_ids = set(imp.id_consultan for imp in imputations)
            bdc_ids = set(imp.id_bdc for imp in imputations if imp.id_bdc)
            
            # Get all consultants in a single query
            consultants = {c.ID_collab: c for c in Collaborateur.objects.filter(ID_collab__in=consultant_ids)}
            
            # Get all AppelOffres in a single query (for direct AppelOffre IDs)
            appel_offres = {ao.id: ao for ao in AppelOffre.objects.filter(id__in=bdc_ids)}
            
            # Find candidatures - handle both direct AppelOffre IDs and BDC IDs
            candidatures = {}
            bdc_to_candidature = {}
            
            if consultant_ids and bdc_ids:
                # First try direct matching with AppelOffre IDs
                direct_candidatures = Candidature.objects.filter(
                    id_consultant__in=consultant_ids,
                    AO_id__in=bdc_ids
                )
                for candidature in direct_candidatures:
                    key = (candidature.id_consultant, candidature.AO_id)
                    candidatures[key] = candidature
                
                # For unmatched BDC IDs, try to find them via BDC -> Candidature mapping
                unmatched_bdc_ids = []
                for bdc_id in bdc_ids:
                    has_direct_match = any(key[1] == bdc_id for key in candidatures.keys())
                    if not has_direct_match:
                        unmatched_bdc_ids.append(bdc_id)
                
                # Look up BDC records to find their associated candidatures
                if unmatched_bdc_ids:
                    bdcs = Bondecommande.objects.filter(id_bdc__in=unmatched_bdc_ids)
                    for bdc in bdcs:
                        if bdc.candidature_id:
                            try:
                                candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                                # Use BDC ID as the key for this mapping
                                key = (candidature.id_consultant, bdc.id_bdc)
                                candidatures[key] = candidature
                                bdc_to_candidature[bdc.id_bdc] = candidature
                            except Candidature.DoesNotExist:
                                continue
            
            # Get ESN IDs from candidatures
            esn_ids = set(c.esn_id for c in candidatures.values() if c.esn_id)
            
            # Get all ESNs in a single query
            esns = {e.ID_ESN: e for e in ESN.objects.filter(ID_ESN__in=esn_ids)}
            
            # Process imputations and add related data
            result = []
            for imp in imputations:
                imp_data = CRA_imputationSerializer(imp).data
                
                # Add consultant info
                consultant_info = None
                if imp.id_consultan in consultants:
                    consultant = consultants[imp.id_consultan]
                    consultant_info = {
                        "id": consultant.ID_collab,
                        "nom": consultant.Nom,
                        "prenom": consultant.Prenom,
                        "email": consultant.email,
                        "poste": consultant.Poste
                    }
                    
                    # Add ESN info if available
                    esn_info = None
                    if consultant.ID_ESN in esns:
                        esn = esns[consultant.ID_ESN]
                        esn_info = {
                            "id": esn.ID_ESN,
                            "name": esn.Raison_sociale
                        }
                    consultant_info["esn"] = esn_info
                
                # Add project and candidature info if available
                project_info = None
                candidature_info = None
                
                # Check if id_bdc is an AppelOffre ID
                if imp.id_bdc and imp.id_bdc in appel_offres:
                    project = appel_offres[imp.id_bdc]
                    project_info = {
                        "id": project.id,
                        "titre": project.titre,
                        "description": project.description,
                        "date_debut": project.date_debut.isoformat() if project.date_debut else None,
                        "date_limite": project.date_limite.isoformat() if project.date_limite else None
                    }
                    
                    # Look for candidature with direct AppelOffre match
                    candidature_key = (imp.id_consultan, imp.id_bdc)
                    if candidature_key in candidatures:
                        candidature = candidatures[candidature_key]
                        candidature_info = {
                            "id": candidature.id_cd,
                            "date_disponibilite": candidature.date_disponibilite.isoformat() if candidature.date_disponibilite else None,
                            "statut": candidature.statut,
                            "tjm": candidature.tjm
                        }
                else:
                    # Check if id_bdc is a BDC ID and we have candidature mapping
                    candidature_key = (imp.id_consultan, imp.id_bdc)
                    if candidature_key in candidatures:
                        candidature = candidatures[candidature_key]
                        candidature_info = {
                            "id": candidature.id_cd,
                            "date_disponibilite": candidature.date_disponibilite.isoformat() if candidature.date_disponibilite else None,
                            "statut": candidature.statut,
                            "tjm": candidature.tjm
                        }
                        
                        # Try to get AppelOffre info through the candidature
                        if candidature.AO_id:
                            try:
                                appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                                project_info = {
                                    "id": appel_offre.id,
                                    "titre": appel_offre.titre,
                                    "description": appel_offre.description,
                                    "date_debut": appel_offre.date_debut.isoformat() if appel_offre.date_debut else None,
                                    "date_limite": appel_offre.date_limite.isoformat() if appel_offre.date_limite else None
                                }
                            except AppelOffre.DoesNotExist:
                                # If no AppelOffre found, create basic project info using BDC data
                                try:
                                    bdc = Bondecommande.objects.get(id_bdc=imp.id_bdc)
                                    project_info = {
                                        "id": imp.id_bdc,
                                        "titre": f"BDC #{bdc.id_bdc}",
                                        "description": f"Montant total: {bdc.montant_total}€",
                                        "date_debut": bdc.date_debut.isoformat() if bdc.date_debut else None,
                                        "date_limite": bdc.date_fin.isoformat() if bdc.date_fin else None
                                    }
                                except Bondecommande.DoesNotExist:
                                    pass
                
                # Create the enhanced imputation entry
                enhanced_imp = {
                    **imp_data,
                    "consultant": consultant_info,
                    "project": project_info,
                    "candidature": candidature_info,
                    # No more BDC info since id_bdc is actually AppelOffre ID
                }
                
                result.append(enhanced_imp)
            
            return JsonResponse({
                "status": True,
                "total": len(result),
                "period": period,
                "client": client_info,
                "data": result
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
@csrf_exempt

@csrf_exempt
def esn_financial_dashboard(request):
    """
    API endpoint that provides financial statistics and data for ESN dashboard.
    
    Request parameters:
    - esn_id: ID of the ESN
    - period: Optional period filter (format: MM_YYYY)
    - year: Optional year filter (format: YYYY)
    """
    if request.method == 'GET':
        esn_id = request.GET.get('esn_id')
        period = request.GET.get('period')  # Optional MM_YYYY filter
        year = request.GET.get('year')      # Optional YYYY filter
        
        if not esn_id:
            return JsonResponse({
                "status": False,
                "message": "esn_id parameter is required"
            }, safe=False, status=400)
            
        try:
            # Get ESN information
            try:
                esn = ESN.objects.get(ID_ESN=esn_id)
                esn_name = esn.Raison_sociale
            except ESN.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": "ESN not found"
                }, safe=False, status=404)
                
            # Get all consultants for this ESN
            consultants = Collaborateur.objects.filter(ID_ESN=esn_id)
            consultant_ids = list(consultants.values_list('ID_collab', flat=True))
            
            # Get candidatures from this ESN
            candidatures = Candidature.objects.filter(esn_id=esn_id)
            active_candidatures = candidatures.filter(statut='Sélectionnée')
            candidature_ids = list(active_candidatures.values_list('id_cd', flat=True))
            
            # Get project IDs from candidatures
            project_ids = list(active_candidatures.values_list('AO_id', flat=True).distinct())
            projects = AppelOffre.objects.filter(id__in=project_ids)
            
            # Get all clients working with this ESN - direct query using project IDs
            client_ids = list(projects.values_list('client_id', flat=True).distinct())
            clients = Client.objects.filter(ID_clt__in=client_ids)
            
            # Get bon de commandes related to these candidatures
            bdcs = Bondecommande.objects.filter(candidature_id__in=candidature_ids)
            
            # Filter BDCs by date if period or year is provided
            if period:
                month, year_val = period.split('_')
                bdcs = bdcs.filter(date_creation__month=int(month), date_creation__year=int(year_val))
            elif year:
                bdcs = bdcs.filter(date_creation__year=int(year))
                
            # Get contracts related to these candidatures
            contracts = Contrat.objects.filter(candidature_id__in=candidature_ids)
            
            # Filter contracts by date if period or year is provided
            if period:
                month, year_val = period.split('_')
                contracts = contracts.filter(date_signature__month=int(month), date_signature__year=int(year_val))
            elif year:
                contracts = contracts.filter(date_signature__year=int(year))
                
            # Calculate total financial statistics
            total_bdc_amount = sum(bdc.montant_total for bdc in bdcs if bdc.montant_total)
            total_contract_amount = sum(contract.montant for contract in contracts if contract.montant)
            
            # Calculate average TJM
            valid_tjms = [float(candidature.tjm) for candidature in active_candidatures if candidature.tjm]
            avg_tjm = sum(valid_tjms) / len(valid_tjms) if valid_tjms else 0
            
            # Calculate revenue per consultant
            revenue_per_consultant = total_bdc_amount / consultants.count() if consultants.count() > 0 else 0
            
            # Calculate imputations/CRA statistics
            imputations_query = CRA_imputation.objects.filter(id_consultan__in=consultant_ids)
            if period:
                imputations_query = imputations_query.filter(période=period)
            elif year:
                imputations_query = imputations_query.filter(période__endswith=f"_{year}")
            
            # Create a list of all imputations for efficient iteration
            all_imputations = list(imputations_query)
                
            # Sum up all work hours
            total_hours = 0
            for imp in all_imputations:
                try:
                    total_hours += float(imp.Durée)
                except (ValueError, TypeError):
                    pass
                    
            # Calculate average utilization rate (billable hours / total potential hours)
            # Assuming 8 working hours per working day (excluding weekends)
            if period:
                month, year_val = period.split('_')
                month_int = int(month)
                year_int = int(year_val)
                
                # Get total working days in the month
                import calendar
                cal = calendar.monthcalendar(year_int, month_int)
                working_days = sum(1 for week in cal for day in range(5) if week[day] != 0)  # Count Mon-Fri
                
                # Potential billable hours
                potential_hours = working_days * 8 * consultants.count()
                utilization_rate = (total_hours / potential_hours) * 100 if potential_hours > 0 else 0
            else:
                utilization_rate = None
                working_days = None
                
            # Calculate expense statistics - Notes de frais
            expense_reports = NDF_CONSULTANT.objects.filter(id_consultan__in=consultant_ids)
            if period:
                expense_reports = expense_reports.filter(période=period)
            elif year:
                expense_reports = expense_reports.filter(période__endswith=f"_{year}")
            
            # Create a list of all expense reports for efficient iteration    
            all_expenses = list(expense_reports)
                
            total_expenses = sum(float(expense.montant_ttc) for expense in all_expenses if expense.montant_ttc)
            
            # Calculate expenses by type
            expenses_by_type = {}
            for expense in all_expenses:
                if expense.type_frais not in expenses_by_type:
                    expenses_by_type[expense.type_frais] = 0
                expenses_by_type[expense.type_frais] += float(expense.montant_ttc) if expense.montant_ttc else 0
            
            # Format expense data for chart
            expense_breakdown = [
                {"type": expense_type, "amount": amount}
                for expense_type, amount in expenses_by_type.items()
            ]
            
            # Create maps for efficient lookups
            client_map = {client.ID_clt: client for client in clients}
            project_map = {project.id: project for project in projects}
            
            # Group imputations by client for efficient client breakdown
            imputations_by_client = {}
            for imp in all_imputations:
                if imp.id_client not in imputations_by_client:
                    imputations_by_client[imp.id_client] = []
                imputations_by_client[imp.id_client].append(imp)
            
            # Client breakdown for this ESN
            client_breakdown = []
            for client in clients:
                client_id = client.ID_clt
                client_projects = projects.filter(client_id=client_id)
                client_project_ids = list(client_projects.values_list('id', flat=True))
                
                client_candidatures = active_candidatures.filter(AO_id__in=client_project_ids)
                client_candidature_ids = list(client_candidatures.values_list('id_cd', flat=True))
                
                # Get BDCs for this client's candidatures
                client_bdcs = bdcs.filter(candidature_id__in=client_candidature_ids)
                client_bdc_amount = sum(bdc.montant_total for bdc in client_bdcs if bdc.montant_total)
                
                # Calculate hours for this client
                client_hours = 0
                client_imputations = imputations_by_client.get(client_id, [])
                for imp in client_imputations:
                    try:
                        client_hours += float(imp.Durée)
                    except (ValueError, TypeError):
                        pass
                
                # Count unique consultants working for this client
                consultant_set = set(candidature.id_consultant for candidature in client_candidatures 
                                    if candidature.id_consultant)
                
                client_breakdown.append({
                    "client_id": client_id,
                    "client_name": client.raison_sociale,
                    "total_amount": client_bdc_amount,
                    "total_hours": client_hours,
                    "consultant_count": len(consultant_set),
                    "project_count": client_projects.count()
                })
            
            # Group imputations by consultant for efficient consultant breakdown
            imputations_by_consultant = {}
            for imp in all_imputations:
                if imp.id_consultan not in imputations_by_consultant:
                    imputations_by_consultant[imp.id_consultan] = []
                imputations_by_consultant[imp.id_consultan].append(imp)
            
            # Consultant breakdown
            consultant_breakdown = []
            for consultant in consultants:
                consultant_id = consultant.ID_collab
                
                # Calculate hours for this consultant
                consultant_hours = 0
                consultant_imputations = imputations_by_consultant.get(consultant_id, [])
                for imp in consultant_imputations:
                    try:
                        consultant_hours += float(imp.Durée)
                    except (ValueError, TypeError):
                        pass
                
                # Get candidatures for this consultant
                consultant_candidatures = active_candidatures.filter(id_consultant=consultant_id)
                consultant_candidature_ids = list(consultant_candidatures.values_list('id_cd', flat=True))
                
                # Get BDCs for this consultant
                consultant_bdcs = bdcs.filter(candidature_id__in=consultant_candidature_ids)
                consultant_bdc_amount = sum(bdc.montant_total for bdc in consultant_bdcs if bdc.montant_total)
                
                # Calculate utilization rate for this consultant
                if period and working_days:
                    consultant_potential_hours = working_days * 8
                    consultant_utilization = (consultant_hours / consultant_potential_hours) * 100 if consultant_potential_hours > 0 else 0
                else:
                    consultant_utilization = None
                
                # Get expense reports for this consultant
                consultant_expenses = [exp for exp in all_expenses if exp.id_consultan == consultant_id]
                consultant_expense_amount = sum(float(expense.montant_ttc) for expense in consultant_expenses if expense.montant_ttc)
                
                # Get project count
                project_count = consultant_candidatures.values('AO_id').distinct().count()
                
                # Get client count - Use a query to get all unique client_ids from projects
                # related to this consultant's candidatures
                ao_ids = list(consultant_candidatures.values_list('AO_id', flat=True).distinct())
                client_count = AppelOffre.objects.filter(id__in=ao_ids).values_list('client_id', flat=True).distinct().count()
                
                consultant_breakdown.append({
                    "consultant_id": consultant_id,
                    "consultant_name": f"{consultant.Prenom} {consultant.Nom}",
                    "poste": consultant.Poste,
                    "total_hours": consultant_hours,
                    "total_amount": consultant_bdc_amount,
                    "utilization_rate": consultant_utilization,
                    "expense_amount": consultant_expense_amount,
                    "project_count": project_count,
                    "client_count": client_count
                })
            
            # Monthly breakdown for time series data
            monthly_data = []
            
            # If year filter is applied, get data for all months in that year
            if year:
                for month in range(1, 13):
                    month_str = f"{month:02d}_{year}"
                    
                    # Get imputations for this month
                    month_imputations = [imp for imp in all_imputations 
                                        if imp.période == month_str]
                    
                    # Calculate hours for this month
                    month_hours = 0
                    for imp in month_imputations:
                        try:
                            month_hours += float(imp.Durée)
                        except (ValueError, TypeError):
                            pass
                    
                    # Get BDCs for this month
                    month_bdcs = bdcs.filter(
                        date_creation__year=int(year),
                        date_creation__month=month
                    )
                    
                    month_amount = sum(bdc.montant_total for bdc in month_bdcs if bdc.montant_total)
                    
                    # Get expense reports for this month
                    month_expenses = [exp for exp in all_expenses 
                                     if exp.période == month_str]
                    month_expense_amount = sum(float(expense.montant_ttc) for expense in month_expenses if expense.montant_ttc)
                    
                    # Calculate profit margin (revenue - expenses)
                    month_profit = month_amount - month_expense_amount
                    month_margin = (month_profit / month_amount * 100) if month_amount > 0 else 0
                    
                    # Count active consultants this month
                    active_consultants = len(set(imp.id_consultan for imp in month_imputations))
                    
                    monthly_data.append({
                        "period": month_str,
                        "period_formatted": f"{month:02d}/{year}",
                        "total_hours": month_hours,
                        "total_amount": month_amount,
                        "total_expenses": month_expense_amount,
                        "profit": month_profit,
                        "margin": month_margin,
                        "active_consultants": active_consultants
                    })
            
            # Calculate profit margin for summary
            profit_margin = ((total_bdc_amount - total_expenses) / total_bdc_amount * 100) if total_bdc_amount > 0 else 0
            
            # Count active consultants (those with imputations)
            active_consultant_count = len(set(imp.id_consultan for imp in all_imputations))
            
            return JsonResponse({
                "status": True,
                "esn": {
                    "id": esn.ID_ESN,
                    "name": esn_name
                },
                "summary": {
                    "total_bdc_amount": total_bdc_amount,
                    "total_contract_amount": total_contract_amount,
                    "total_hours": total_hours,
                    "total_expenses": total_expenses,
                    "profit_margin": profit_margin,
                    "avg_tjm": avg_tjm,
                    "revenue_per_consultant": revenue_per_consultant,
                    "consultant_count": consultants.count(),
                    "active_consultants": active_consultant_count,
                    "utilization_rate": utilization_rate,
                    "client_count": clients.count(),
                    "project_count": projects.count()
                },
                "client_breakdown": client_breakdown,
                "consultant_breakdown": consultant_breakdown,
                "expense_breakdown": expense_breakdown,
                "monthly_data": monthly_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def client_financial_dashboard(request):
    """
    API endpoint that provides financial statistics and data for client dashboard.
    
    Request parameters:
    - client_id: ID of the client
    - period: Optional period filter (format: MM_YYYY)
    - year: Optional year filter (format: YYYY)
    """
    if request.method == 'GET':
        client_id = request.GET.get('client_id')
        period = request.GET.get('period')  # Optional MM_YYYY filter
        year = request.GET.get('year')      # Optional YYYY filter
        
        if not client_id:
            return JsonResponse({
                "status": False,
                "message": "client_id parameter is required"
            }, safe=False, status=400)
            
        try:
            # Get client information
            try:
                client = Client.objects.get(ID_clt=client_id)
                client_name = client.raison_sociale
            except Client.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": "Client not found"
                }, safe=False, status=404)
                
            # Base query for client's projects
            projects = AppelOffre.objects.filter(client_id=client_id)
            project_ids = list(projects.values_list('id', flat=True))
            
            # Get candidatures related to these projects
            candidatures = Candidature.objects.filter(
                AO_id__in=project_ids,
                statut='Sélectionnée'  # Only selected candidatures
            )
            candidature_ids = list(candidatures.values_list('id_cd', flat=True))
            
            # Get bon de commandes related to these candidatures
            bdcs = Bondecommande.objects.filter(candidature_id__in=candidature_ids)
            
            # Filter BDCs by date if period or year is provided
            if period:
                month, year_val = period.split('_')
                bdcs = bdcs.filter(date_creation__month=int(month), date_creation__year=int(year_val))
            elif year:
                bdcs = bdcs.filter(date_creation__year=int(year))
                
            # Get contracts related to these candidatures
            contracts = Contrat.objects.filter(candidature_id__in=candidature_ids)
            
            # Filter contracts by date if period or year is provided
            if period:
                month, year_val = period.split('_')
                contracts = contracts.filter(date_signature__month=int(month), date_signature__year=int(year_val))
            elif year:
                contracts = contracts.filter(date_signature__year=int(year))
                
            # Calculate total financial statistics
            total_bdc_amount = sum(bdc.montant_total for bdc in bdcs if bdc.montant_total)
            total_contract_amount = sum(contract.montant for contract in contracts if contract.montant)
            
            # Calculate imputations/CRA statistics
            imputations_query = CRA_imputation.objects.filter(id_client=client_id)
            if period:
                imputations_query = imputations_query.filter(période=period)
            elif year:
                imputations_query = imputations_query.filter(période__endswith=f"_{year}")
                
            # Create a list of all imputations for efficient iteration
            all_imputations = list(imputations_query)
                
            # Sum up all work hours
            total_hours = 0
            for imp in all_imputations:
                try:
                    total_hours += float(imp.Durée)
                except (ValueError, TypeError):
                    pass
                    
            # Get ESNs working with this client
            esn_ids = set()
            for candidature in candidatures:
                if candidature.esn_id:
                    esn_ids.add(candidature.esn_id)
                    
            esns = ESN.objects.filter(ID_ESN__in=esn_ids)
            esn_count = esns.count()
            
            # Get active consultants for this client
            consultant_ids = set(imp.id_consultan for imp in imputations_query)
            consultants = Collaborateur.objects.filter(ID_collab__in=consultant_ids)
            consultant_count = consultants.count()
            
            # Financial breakdown by ESN
            esn_breakdown = []
            for esn in esns:
                esn_candidatures = candidatures.filter(esn_id=esn.ID_ESN)
                esn_candidature_ids = list(esn_candidatures.values_list('id_cd', flat=True))
                
                esn_bdcs = Bondecommande.objects.filter(candidature_id__in=esn_candidature_ids)
                if period:
                    month, year_val = period.split('_')
                    esn_bdcs = esn_bdcs.filter(
                        date_creation__month=int(month), 
                        date_creation__year=int(year_val)
                    )
                elif year:
                    esn_bdcs = esn_bdcs.filter(date_creation__year=int(year))
                    
                esn_bdc_amount = sum(bdc.montant_total for bdc in esn_bdcs if bdc.montant_total)
                
                esn_imputations = [imp for imp in all_imputations if 
                    imp.id_consultan in Collaborateur.objects.filter(
                        ID_ESN=esn.ID_ESN
                    ).values_list('ID_collab', flat=True)]
                
                esn_hours = 0
                for imp in esn_imputations:
                    try:
                        esn_hours += float(imp.Durée)
                    except (ValueError, TypeError):
                        pass
                
                esn_breakdown.append({
                    "esn_id": esn.ID_ESN,
                    "esn_name": esn.Raison_sociale,
                    "total_amount": esn_bdc_amount,
                    "total_hours": esn_hours,
                    "consultant_count": Collaborateur.objects.filter(
                        ID_ESN=esn.ID_ESN,
                        ID_collab__in=consultant_ids
                    ).count(),
                    "project_count": esn_candidatures.values('AO_id').distinct().count()
                })
            
            # Financial breakdown by project
            project_breakdown = []
            for project in projects:
                project_candidatures = candidatures.filter(AO_id=project.id)
                project_candidature_ids = list(project_candidatures.values_list('id_cd', flat=True))
                
                project_bdcs = Bondecommande.objects.filter(candidature_id__in=project_candidature_ids)
                if period:
                    month, year_val = period.split('_')
                    project_bdcs = project_bdcs.filter(
                        date_creation__month=int(month), 
                        date_creation__year=int(year_val)
                    )
                elif year:
                    project_bdcs = project_bdcs.filter(date_creation__year=int(year))
                    
                project_bdc_amount = sum(bdc.montant_total for bdc in project_bdcs if bdc.montant_total)
                
                project_imputations = [imp for imp in all_imputations if imp.id_bdc == project.id]
                
                project_hours = 0
                for imp in project_imputations:
                    try:
                        project_hours += float(imp.Durée)
                    except (ValueError, TypeError):
                        pass
                
                project_breakdown.append({
                    "project_id": project.id,
                    "project_name": project.titre,
                    "total_amount": project_bdc_amount,
                    "total_hours": project_hours,
                    "consultant_count": len(set(imp.id_consultan for imp in project_imputations)),
                    "esn_count": project_candidatures.values('esn_id').distinct().count()
                })
            
            # Monthly breakdown for time series data
            monthly_data = []
            
            # If year filter is applied, get data for all months in that year
            if year:
                for month in range(1, 13):
                    month_str = f"{month:02d}_{year}"
                    
                    # Get imputations for this month
                    month_imputations = CRA_imputation.objects.filter(
                        id_client=client_id,
                        période=month_str
                    )
                    
                    # Calculate hours for this month
                    month_hours = 0
                    for imp in month_imputations:
                        try:
                            month_hours += float(imp.Durée)
                        except (ValueError, TypeError):
                            pass
                    
                    # Get BDCs for this month
                    month_bdcs = Bondecommande.objects.filter(
                        candidature_id__in=candidature_ids,
                        date_creation__year=int(year),
                        date_creation__month=month
                    )
                    
                    month_amount = sum(bdc.montant_total for bdc in month_bdcs if bdc.montant_total)
                    
                    monthly_data.append({
                        "period": month_str,
                        "period_formatted": f"{month:02d}/{year}",
                        "total_hours": month_hours,
                        "total_amount": month_amount,
                        "consultant_count": len(set(imp.id_consultan for imp in month_imputations))
                    })
            
            return JsonResponse({
                "status": True,
                "client": {
                    "id": client.ID_clt,
                    "name": client_name
                },
                "summary": {
                    "total_bdc_amount": total_bdc_amount,
                    "total_contract_amount": total_contract_amount,
                    "total_hours": total_hours,
                    "project_count": projects.count(),
                    "esn_count": esn_count,
                    "consultant_count": consultant_count,
                    "active_contracts": contracts.filter(statut="Actif").count(),
                },
                "esn_breakdown": esn_breakdown,
                "project_breakdown": project_breakdown,
                "monthly_data": monthly_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    
    
@csrf_exempt
def commercial_login(request):
    """
    API endpoint to authenticate a commercial user.
    
    POST parameters:
    - email: Email of the commercial
    - password: Password of the commercial
    
    Returns JWT token and commercial user data upon successful authentication.
    """
    if request.method == "POST":
        data = JSONParser().parse(request)
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return JsonResponse({
                "success": False, 
                "msg": "Email and password are required"
            }, safe=False)

        try:
            # Find the collaborateur with the provided email
            collaborateur = Collaborateur.objects.get(email=email)
            
            # Check if the collaborateur is a commercial
            if not collaborateur.Commercial:
                return JsonResponse({
                    "success": False,
                    "msg": "This account is not a commercial account"
                }, safe=False)
            
            # Password check with SHA1 hash
            pwd_utf = password.encode()
            pwd_sh = hashlib.sha1(pwd_utf)
            password_crp = pwd_sh.hexdigest()
            
            if collaborateur.password == password_crp:
                # Serialize collaborateur data
                collaborateur_serializer = CollaborateurSerializer(collaborateur)
                
                # Create JWT token
                payload = {
                    'id': collaborateur.ID_collab,
                    'email': collaborateur.email,
                    'role': 'commercial',
                    'esn_id': collaborateur.ID_ESN,
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
                }
                token = jwt.encode(payload, 'maghrebIt', algorithm='HS256')
                
                # Update token in database
                collaborateur.token = token
                collaborateur.save()
                
                response = JsonResponse({
                    "success": True, 
                    "token": token, 
                    "data": collaborateur_serializer.data,
                    "esn_id": collaborateur.ID_ESN
                }, safe=False)
                
                response.set_cookie(key='jwt', value=token, max_age=86400)
                
                return response
            
            return JsonResponse({
                "success": False, 
                "msg": "Invalid password"
            }, safe=False)
        
        except Collaborateur.DoesNotExist:
            return JsonResponse({
                "success": False, 
                "msg": "Commercial account not found"
            }, safe=False)
    
    return JsonResponse({
        "success": False, 
        "msg": "Only POST method is allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def unified_login(request):
    """
    Unified API endpoint to authenticate users based on their Poste (role).
    
    POST parameters:
    - email: Email of the user
    - password: Password of the user
    
    Returns JWT token and user data upon successful authentication with role from Poste field.
    """
    if request.method == "POST":
        data = JSONParser().parse(request)
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return JsonResponse({
                "success": False, 
                "message": "Email and password are required"
            }, safe=False)

        try:
            # Find the collaborateur with the provided email
            collaborateur = Collaborateur.objects.get(email=email)
            
            # Password check with SHA1 hash
            pwd_utf = password.encode()
            pwd_sh = hashlib.sha1(pwd_utf)
            password_crp = pwd_sh.hexdigest()
            
            if collaborateur.password == password_crp:
                # Serialize collaborateur data
                collaborateur_serializer = CollaborateurSerializer(collaborateur)
                
                # Determine user role based on the Poste field
                if collaborateur.Poste:
                    user_role = collaborateur.Poste.lower()  # Convert to lowercase for consistency
                else:
                    # Fallback if Poste is not set
                    user_role = "user"
                
                # Create JWT token with role information
                payload = {
                    'id': collaborateur.ID_collab,
                    'email': collaborateur.email,
                    'role': user_role,
                    'esn_id': collaborateur.ID_ESN,
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
                }
                token = jwt.encode(payload, 'maghrebIt', algorithm='HS256')
                
                # Update token in database
                collaborateur.token = token
                collaborateur.save()
                
                # Return response with role information
                response = JsonResponse({
                    "success": True, 
                    "token": token, 
                    "data": collaborateur_serializer.data,
                    "role": user_role,
                    "esn_id": collaborateur.ID_ESN
                }, safe=False)
                
                response.set_cookie(key='jwt', value=token, max_age=86400)
                
                return response
            
            return JsonResponse({
                "success": False, 
                "message": "Invalid password"
            }, safe=False)
        
        except Collaborateur.DoesNotExist:
            return JsonResponse({
                "success": False, 
                "message": "User not found"
            }, safe=False)
    
    return JsonResponse({
        "success": False, 
        "message": "Only POST method is allowed"
    }, safe=False, status=405)

@csrf_exempt
def get_consultants_by_commercial(request):
    """
    API endpoint to retrieve all consultants associated with a specific commercial.
    
    GET parameters:
    - commercial_id: ID of the commercial/responsable
    - bdc_id: Optional Bon de Commande ID to filter consultants
    
    Returns a list of consultants associated with this commercial.
    """
    if request.method == 'GET':
        commercial_id = request.GET.get('commercial_id')
        bdc_id = request.GET.get('bdc_id')
        bdc_id_int = None
        commercial_id_int = None
        
        if not commercial_id:
            return JsonResponse({
                "status": False,
                "message": "commercial_id parameter is required"
            }, safe=False, status=400)

        try:
            commercial_id_int = int(commercial_id)
        except (TypeError, ValueError):
            return JsonResponse({
                "status": False,
                "message": "commercial_id must be an integer"
            }, safe=False, status=400)
            
        if bdc_id:
            try:
                bdc_id_int = int(bdc_id)
            except ValueError:
                return JsonResponse({
                    "status": False,
                    "message": "bdc_id must be an integer"
                }, safe=False, status=400)

        try:
            # Verify the commercial exists
            try:
                commercial = Collaborateur.objects.get(ID_collab=commercial_id_int)
                
                # Check if user is actually a commercial based on the Poste field
                if commercial.Poste and commercial.Poste.lower() != 'commercial':
                    return JsonResponse({
                        "status": False,
                        "message": f"User is not a commercial (current role: {commercial.Poste})"
                    }, safe=False, status=400)
                    
                # Get the ESN ID for this commercial
                esn_id = commercial.ID_ESN
                
            except Collaborateur.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": "Commercial not found"
                }, safe=False, status=404)
            
            try:
                esn_name = ESN.objects.get(ID_ESN=esn_id).Raison_sociale if esn_id else None
            except ESN.DoesNotExist:
                esn_name = None

            selected_bdc_data = None
            target_bdc = None
            bdc_by_consultant = defaultdict(list)
            associated_consultant_ids = set()

            legacy_identifiers = {
                value
                for value in {
                    f"{commercial.Prenom} {commercial.Nom}".strip(),
                    commercial.Nom,
                    commercial.Prenom,
                    getattr(commercial, "email", None),
                    getattr(commercial, "responsable", None),
                }
                if value
            }

            identifier_filters = (
                Q(commercial_id=commercial_id_int) |
                Q(responsable_compte=str(commercial_id_int))
            )

            if legacy_identifiers:
                identifier_filters |= Q(responsable_compte__in=legacy_identifiers)

            candidatures_for_commercial = Candidature.objects.filter(
                esn_id=esn_id
            ).filter(identifier_filters)

            candidatures_with_consultant = list(
                candidatures_for_commercial.filter(
                    id_consultant__isnull=False
                ).exclude(id_consultant=0)
            )

            consultant_candidatures_map = defaultdict(list)
            candidature_map = {}
            consultant_ids_from_candidatures = set()

            for candidature in candidatures_with_consultant:
                try:
                    consultant_key = int(candidature.id_consultant)
                except (TypeError, ValueError):
                    continue
                consultant_candidatures_map[consultant_key].append(candidature)
                candidature_map[candidature.id_cd] = candidature
                consultant_ids_from_candidatures.add(consultant_key)

            candidature_ids_for_commercial = list(candidature_map.keys())

            appel_map = {}
            client_map = {}

            if candidatures_with_consultant:
                ao_ids = {
                    candidature.AO_id
                    for candidature in candidatures_with_consultant
                    if candidature.AO_id
                }

                if ao_ids:
                    appel_map = {
                        ao.id: ao for ao in AppelOffre.objects.filter(id__in=ao_ids)
                    }

                    client_ids = {
                        ao.client_id for ao in appel_map.values() if ao.client_id
                    }

                    if client_ids:
                        client_map = {
                            client.ID_clt: client
                            for client in Client.objects.filter(ID_clt__in=client_ids)
                        }

            relevant_bdcs = []

            if candidature_ids_for_commercial:
                if bdc_id_int is not None:
                    try:
                        target_bdc = Bondecommande.objects.get(id_bdc=bdc_id_int)
                    except Bondecommande.DoesNotExist:
                        return JsonResponse({
                            "status": False,
                            "message": "Bon de commande not found"
                        }, safe=False, status=404)

                    if target_bdc.candidature_id not in candidature_ids_for_commercial:
                        return JsonResponse({
                            "status": False,
                            "message": "Bon de commande is not associated with this commercial"
                        }, safe=False, status=403)

                    relevant_bdcs = [target_bdc]
                else:
                    relevant_bdcs = list(
                        Bondecommande.objects.filter(candidature_id__in=candidature_ids_for_commercial)
                    )

                if relevant_bdcs:
                    for bdc in relevant_bdcs:
                        candidature = candidature_map.get(bdc.candidature_id)
                        if not candidature or not candidature.id_consultant:
                            continue

                        enriched_bdc = dict(BondecommandeSerializer(bdc).data)
                        enriched_bdc.update({
                            "consultant_id": candidature.id_consultant,
                            "candidature_id": candidature.id_cd,
                            "candidature_status": candidature.statut,
                            "responsable_compte": candidature.responsable_compte,
                            "tjm_candidature": (
                                str(candidature.tjm) if candidature.tjm is not None else None
                            ),
                        })

                        appel_offre = appel_map.get(candidature.AO_id)
                        if appel_offre:
                            enriched_bdc.update({
                                "project_id": appel_offre.id,
                                "project_title": appel_offre.titre,
                                "client_id": appel_offre.client_id,
                            })

                            client = client_map.get(appel_offre.client_id)
                            if client:
                                enriched_bdc["client_name"] = client.raison_sociale

                        try:
                            consultant_key = int(candidature.id_consultant)
                        except (TypeError, ValueError):
                            continue

                        bdc_by_consultant[consultant_key].append(enriched_bdc)

                        if bdc_id_int is not None and bdc.id_bdc == bdc_id_int:
                            selected_bdc_data = enriched_bdc

                    associated_consultant_ids.update(bdc_by_consultant.keys())

            if bdc_id_int is not None and selected_bdc_data is None and target_bdc is not None:
                selected_bdc_data = dict(BondecommandeSerializer(target_bdc).data)

            associated_consultant_ids.update(consultant_ids_from_candidatures)

            consultants = (
                Collaborateur.objects.filter(
                    ID_ESN=esn_id,
                    Poste__iexact='consultant',  # Case-insensitive match for 'consultant'
                    ID_collab__in=associated_consultant_ids
                )
                if associated_consultant_ids
                else Collaborateur.objects.none()
            )

            # Serialize the consultant data
            consultant_serializer = CollaborateurSerializer(consultants, many=True)

            # Get candidatures information for each consultant
            enhanced_consultants = []
            for consultant in consultant_serializer.data:
                consultant_id = int(consultant['ID_collab'])
                
                # Get candidatures for this consultant from cached map
                consultant_candidatures = consultant_candidatures_map.get(consultant_id, [])
                candidature_count = len(consultant_candidatures)

                # Get active projects count (those with "Sélectionnée" status)
                active_projects = sum(
                    1 for candidature in consultant_candidatures
                    if candidature.statut == 'Sélectionnée'
                )

                # Get project and client IDs
                project_ids = {
                    candidature.AO_id
                    for candidature in consultant_candidatures
                    if candidature.AO_id
                }

                client_ids = set()
                for project_id in project_ids:
                    appel_offre = appel_map.get(project_id)
                    if appel_offre and appel_offre.client_id:
                        client_ids.add(appel_offre.client_id)

                # Get bon de commande information linked to this consultant
                linked_bdcs = bdc_by_consultant.get(consultant_id, [])
                
                # Add additional information
                enhanced_consultant = {
                    **consultant,
                    "statistics": {
                        "candidature_count": candidature_count,
                        "active_projects": active_projects,
                        "client_count": len(client_ids),
                        "bdc_count": len(linked_bdcs)
                    },
                    "linked_bdcs": linked_bdcs,
                    "linked_bdc_ids": [bdc["id_bdc"] for bdc in linked_bdcs],
                    "selected_for_bdc": bool(
                        bdc_id_int and any(bdc["id_bdc"] == bdc_id_int for bdc in linked_bdcs)
                    )
                }
                
                enhanced_consultants.append(enhanced_consultant)
            
            return JsonResponse({
                "status": True,
                "commercial": {
                    "id": commercial.ID_collab,
                    "name": f"{commercial.Prenom} {commercial.Nom}",
                    "esn_id": esn_id,
                    "esn_name": esn_name
                },
                "filters": {
                    "bdc_id": bdc_id_int,
                    "selected_bdc": selected_bdc_data
                },
                "total": len(enhanced_consultants),
                "data": enhanced_consultants
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def cra_consultant_view(request, id=0):
    """
    API endpoint for managing CRA_CONSULTANT records (status tracking)
    """
    if request.method == 'GET':
        consultant_id = request.GET.get('consultant_id')
        period = request.GET.get('period')
        
        if consultant_id and period:
            # Get specific CRA for consultant and period
            cra_consultants = CRA_CONSULTANT.objects.filter(
                id_consultan=consultant_id,
                période=period
            )
        elif id > 0:
            # Get specific CRA by ID
            cra_consultants = CRA_CONSULTANT.objects.filter(id_CRA=id)
        else:
            # Get all CRAs
            cra_consultants = CRA_CONSULTANT.objects.all()
            
        cra_serializer = CRA_CONSULTANTSerializer(cra_consultants, many=True)
        return JsonResponse({
            "status": True,
            "total": len(cra_serializer.data),
            "data": cra_serializer.data
        }, safe=False)
    
    elif request.method == 'PUT':
        # Update CRA status
        data = JSONParser().parse(request)
        
        try:
            if id > 0:
                cra_consultant = CRA_CONSULTANT.objects.get(id_CRA=id)
            else:
                consultant_id = data.get('consultant_id')
                period = data.get('period')
                cra_consultant = CRA_CONSULTANT.objects.get(
                    id_consultan=consultant_id,
                    période=period
                )
            
            old_status = cra_consultant.statut
            cra_serializer = CRA_CONSULTANTSerializer(cra_consultant, data=data, partial=True)
            
            if cra_serializer.is_valid():
                updated_cra = cra_serializer.save()
                new_status = updated_cra.statut
                
                # Send notifications when status changes
                if 'statut' in data and old_status != new_status:
                    try:
                        consultant = Collaborateur.objects.get(ID_collab=updated_cra.id_consultan)
                        consultant_name = f"{consultant.Nom} {consultant.Prenom}"
                        period = updated_cra.période
                        
                        # Get project info if available
                        project_name = "N/A"
                        commercial_id = None

                        if updated_cra.id_bdc:
                            try:
                                bdc = Bondecommande.objects.get(id_bdc=updated_cra.id_bdc)
                                candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                                ao = AppelOffre.objects.get(id=candidature.AO_id)
                                project_name = ao.titre
                                commercial_id = candidature.commercial_id
                            except:
                                pass
                        
                        # Notification when consultant submits CRA to commercial (EVP status)
                        if new_status == 'EVP':
                            if commercial_id:
                                message = (
                                    f"Nouveau CRA à valider : {consultant_name} a soumis son compte-rendu d'activité pour la période {period}. "
                                    f"Projet: {project_name}. "
                                    f"Veuillez vérifier et valider ce CRA. "
                                    f'<a href="/interface-co?menu=cra-validation" style="color: #1890ff; text-decoration: underline;">Valider les CRA</a>'
                                )
                                send_notification(
                                    user_id=updated_cra.id_consultan,
                                    dest_id=commercial_id,
                                    message=message,
                                    categorie="COMMERCIAL",
                                    event="CRA à Valider",
                                    event_id=updated_cra.id_CRA
                                )
                        
                        # Notification when commercial validates and sends to client (EVC status)
                        elif new_status == 'EVC':
                            if updated_cra.id_client:
                                message = (
                                    f"Le compte-rendu d'activité de <strong>{consultant_name}</strong> pour la période <strong>{period}</strong> "
                                    f"sur le projet <strong>{project_name}</strong> a été validé par le responsable commercial. "
                                    f"Veuillez examiner et valider ce CRA pour finaliser la facturation de cette période. "
                                    f'<a href="/interface-cl?menu=cra-management" style="color: #1890ff; text-decoration: underline;">Valider le CRA</a>'
                                )
                                send_notification(
                                    user_id=commercial_id if commercial_id else updated_cra.id_esn,
                                    dest_id=updated_cra.id_client,
                                    message=message,
                                    categorie="CLIENT",
                                    event="Validation CRA Client",
                                    event_id=updated_cra.id_CRA
                                )
                        
                        # Notification to consultant when ESN validates
                        elif new_status == 'validé_esn':
                            message = (
                                f"Votre CRA pour la période {period} (Projet: {project_name}) a été validé par l'ESN. "
                                f'<a href="/interface-co?menu=cra-management" class="notification-link">Voir mes CRA</a>'
                            )
                            send_notification(
                                user_id=updated_cra.id_esn,
                                dest_id=updated_cra.id_consultan,
                                message=message,
                                categorie="CONSULTANT",
                                event="Validation CRA",
                                event_id=updated_cra.id_CRA
                            )
                            
                            # Notification to client for validation
                            if updated_cra.id_client:
                                message_client = (
                                    f"CRA de {consultant_name} pour la période {period} (Projet: {project_name}) est en attente de votre validation. "
                                    f'<a href="/interface-cl?menu=cra-validation" class="notification-link">Valider le CRA</a>'
                                )
                                send_notification(
                                    user_id=updated_cra.id_esn,
                                    dest_id=updated_cra.id_client,
                                    message=message_client,
                                    categorie="CLIENT",
                                    event="Validation CRA",
                                    event_id=updated_cra.id_CRA
                                )

                            if commercial_id:
                                send_notification(
                                    user_id=updated_cra.id_esn,
                                    dest_id=commercial_id,
                                    message=(
                                        f"Le CRA de {consultant_name} pour la période {period} (Projet: {project_name}) a été validé par l'ESN et attend la validation du client. "
                                        f'<a href="/interface-co?menu=cra-validation" class="notification-link">Suivre le CRA</a>'
                                    ),
                                    categorie="COMMERCIAL",
                                    event="Validation CRA",
                                    event_id=updated_cra.id_CRA
                                )
                        
                        # Notification to consultant, ESN, and commercial when client validates
                        elif new_status == 'validé_client' or new_status == 'Validé':
                            # Notification to consultant
                            message_consultant = (
                                f"Votre CRA pour la période {period} (Projet: {project_name}) a été validé par le client. "
                                f'<a href="/interface-co?menu=cra-management" class="notification-link">Voir mes CRA</a>'
                            )
                            send_notification(
                                user_id=updated_cra.id_client,
                                dest_id=updated_cra.id_consultan,
                                message=message_consultant,
                                categorie="CONSULTANT",
                                event="Validation client",
                                event_id=updated_cra.id_CRA
                            )
                            
                            # Optional notification to ESN (disabled via flag)
                            if ENABLE_CRA_CLIENT_VALIDATION_ESN_NOTIFICATION and updated_cra.id_esn:
                                message_esn = (
                                    f"Le CRA de {consultant_name} pour la période {period} (Projet: {project_name}) a été validé par le client."
                                )
                                send_notification(
                                    user_id=updated_cra.id_client,
                                    dest_id=updated_cra.id_esn,
                                    message=message_esn,
                                    categorie="ESN",
                                    event="Validation client",
                                    event_id=updated_cra.id_CRA
                                )

                            # Notification to commercial
                            if commercial_id:
                                send_notification(
                                    user_id=updated_cra.id_client,
                                    dest_id=commercial_id,
                                    message=(
                                        f"Le CRA de {consultant_name} pour la période {period} (Projet: {project_name}) a été validé par le client. Vous pouvez lancer la facturation."
                                    ),
                                    categorie="COMMERCIAL",
                                    event="Validation client",
                                    event_id=updated_cra.id_CRA
                                )
                        
                        # Notification when CRA is rejected
                        elif new_status == 'rejeté':
                            message = (
                                f"Votre CRA pour la période {period} a été rejeté. "
                                f"Projet: {project_name}. "
                                f"Veuillez corriger les informations et soumettre à nouveau votre compte-rendu. "
                                f'<a href="/interface-co?menu=cra-management" style="color: #1890ff; text-decoration: underline;">Voir mes CRA</a>'
                            )
                            send_notification(
                                user_id=updated_cra.id_esn if old_status == 'validé_esn' else updated_cra.id_client,
                                dest_id=updated_cra.id_consultan,
                                message=message,
                                categorie="CONSULTANT",
                                event="CRA Rejeté",
                                event_id=updated_cra.id_CRA
                            )

                            if commercial_id:
                                rejection_actor = updated_cra.id_esn if old_status == 'validé_esn' else updated_cra.id_client
                                send_notification(
                                    user_id=rejection_actor,
                                    dest_id=commercial_id,
                                    message=(
                                        f"Le CRA de {consultant_name} pour la période {period} (Projet: {project_name}) a été rejeté. Merci d'accompagner le consultant pour une nouvelle soumission."
                                    ),
                                    categorie="COMMERCIAL",
                                    event="CRA Rejeté",
                                    event_id=updated_cra.id_CRA
                                )
                        
                        # Notification when commercial cancels CRA
                        elif new_status == 'annule':
                            message = (
                                f"Votre CRA pour la période {period} a été annulé par votre responsable commercial. "
                                f"Projet: {project_name}. "
                                f"Veuillez contacter votre responsable pour plus d'informations. "
                                f'<a href="/interface-co?menu=cra-management" style="color: #1890ff; text-decoration: underline;">Voir mes CRA</a>'
                            )
                            send_notification(
                                user_id=commercial_id if commercial_id else updated_cra.id_esn,
                                dest_id=updated_cra.id_consultan,
                                message=message,
                                categorie="CONSULTANT",
                                event="CRA Annulé",
                                event_id=updated_cra.id_CRA
                            )
                    except Exception as notif_error:
                        print(f"Erreur lors de l'envoi de la notification CRA: {str(notif_error)}")
                
                return JsonResponse({
                    "status": True,
                    "msg": "CRA status updated successfully!",
                    "data": cra_serializer.data
                }, safe=False)
                
            return JsonResponse({
                "status": False,
                "msg": "Failed to update CRA",
                "errors": cra_serializer.errors
            }, safe=False)
            
        except CRA_CONSULTANT.DoesNotExist:
            return JsonResponse({
                "status": False,
                "msg": "CRA not found"
            }, safe=False, status=404)
    
    return JsonResponse({
        "status": False,
        "msg": "Method not allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def get_consultants_by_client(request):
    """
    API endpoint to retrieve all consultants associated with a specific client.
    
    GET parameters:
    - client_id: ID of the client
    
    Returns a list of consultants working on this client's projects.
    """
    if request.method == 'GET':
        client_id = request.GET.get('client_id')
        
        if not client_id:
            return JsonResponse({
                "status": False,
                "message": "client_id parameter is required"
            }, safe=False, status=400)
            
        try:
            # Get all projects (AppelOffre) for this client
            projects = AppelOffre.objects.filter(client_id=client_id)
            
            if not projects.exists():
                return JsonResponse({
                    "status": True,
                    "total": 0,
                    "data": [],
                    "message": "No projects found for this client"
                }, safe=False)
            
            # Get all candidatures for these projects
            project_ids = projects.values_list('id', flat=True)
            candidatures = Candidature.objects.filter(AO_id__in=project_ids)
            
            if not candidatures.exists():
                return JsonResponse({
                    "status": True,
                    "total": 0,
                    "data": [],
                    "message": "No consultants assigned to this client's projects"
                }, safe=False)
            
            # Get all consultant IDs from these candidatures
            consultant_ids = candidatures.values_list('id_consultant', flat=True).distinct()
            consultants = Collaborateur.objects.filter(ID_collab__in=consultant_ids)
            
            # Prepare response data with enhanced details
            consultants_data = []
            
            for consultant in consultants:
                # Get the ESN information
                esn_name = "Unknown ESN"
                try:
                    if consultant.ID_ESN:
                        esn = ESN.objects.get(ID_ESN=consultant.ID_ESN)
                        esn_name = esn.Raison_sociale
                except ESN.DoesNotExist:
                    pass
                
                # Get the consultant's candidatures for this client
                consultant_candidatures = candidatures.filter(id_consultant=consultant.ID_collab)
                
                # Get active projects
                active_projects = []
                for candidature in consultant_candidatures:
                    try:
                        project = AppelOffre.objects.get(id=candidature.AO_id)
                        
                        # Check if there's an active contract
                        has_contract = Contrat.objects.filter(
                            candidature_id=candidature.id_cd,
                            statut__in=['actif', 'Actif', 'en cours', 'En cours']
                        ).exists()
                        
                        # Only include active projects with valid contracts
                        if has_contract and candidature.statut in ['Sélectionnée', 'Acceptée']:
                            active_projects.append({
                                "id": project.id,
                                "title": project.titre,
                                "start_date": project.date_debut,
                                "end_date": project.date_limite,
                                "tjm": float(candidature.tjm) if candidature.tjm else 0
                            })
                    except AppelOffre.DoesNotExist:
                        continue
                
                # Build consultant profile
                consultant_data = {
                    "id": consultant.ID_collab,
                    "name": f"{consultant.Nom} {consultant.Prenom}",
                    "email": consultant.email,  # Fixed: changed Mail to email
                    # Removed "phone" since there's no Telephone field in Collaborateur model
                    "esn": esn_name,
                    "esn_id": consultant.ID_ESN,
                    "position": consultant.Poste or "Consultant",
                    "active_projects": active_projects,
                    "project_count": len(active_projects),
                    "profile_photo": consultant.img_path if hasattr(consultant, 'img_path') else None
                }
                
                consultants_data.append(consultant_data)
            
            return JsonResponse({
                "status": True,
                "total": len(consultants_data),
                "data": consultants_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
@csrf_exempt

def get_all_projects(request):
    """
    API endpoint to retrieve a list of all projects with just their IDs and titles.
    Used for populating dropdowns and select lists in the UI.
    
    GET parameters:
    - client_id: Optional - filter projects by client
    - esn_id: Optional - filter projects by ESN (through candidatures)
    - status: Optional - filter by project status
    
    Returns a simplified list of all projects with their IDs and titles.
    """
    if request.method == 'GET':
        try:
            # Start with all projects
            projects_query = AppelOffre.objects.all()
            
            # Apply filters if provided
            client_id = request.GET.get('client_id')
            if client_id:
                projects_query = projects_query.filter(client_id=client_id)
                
            esn_id = request.GET.get('esn_id')
            if esn_id:
                # Filter by ESN through candidatures
                candidature_projects = Candidature.objects.filter(
                    esn_id=esn_id
                ).values_list('AO_id', flat=True).distinct()
                projects_query = projects_query.filter(id__in=candidature_projects)
                
            status = request.GET.get('status')
            if status:
                # Assuming there's a status field in AppelOffre
                projects_query = projects_query.filter(statut=status)
            
            # Order by most recent first
            projects_query = projects_query.order_by('-id')
            
            # Create a simplified list with just ID and title
            projects_list = []
            for project in projects_query:
                # Get client name if available
                client_name = ""
                if project.client_id:
                    try:
                        client = Client.objects.get(ID_clt=project.client_id)
                        client_name = client.raison_sociale
                    except Client.DoesNotExist:
                        pass
                
                projects_list.append({
                    "id": project.id,
                    "title": project.titre,
                    "client_id": project.client_id,
                    "client_name": client_name,
                    "date_debut": project.date_debut,
                    "date_limite": project.date_limite
                })
            
            return JsonResponse({
                "status": True,
                "total": len(projects_list),
                "data": projects_list
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    """
    API endpoint to retrieve all consultants associated with a specific client.
    
    GET parameters:
    - client_id: ID of the client
    
    Returns a list of consultants working on this client's projects.
    """
    if request.method == 'GET':
        client_id = request.GET.get('client_id')
        
        if not client_id:
            return JsonResponse({
                "status": False,
                "message": "client_id parameter is required"
            }, safe=False, status=400)
            
        try:
            # Get all projects (AppelOffre) for this client
            projects = AppelOffre.objects.filter(client_id=client_id)
            
            if not projects.exists():
                return JsonResponse({
                    "status": True,
                    "total": 0,
                    "data": [],
                    "message": "No projects found for this client"
                }, safe=False)
            
            # Get all candidatures for these projects
            project_ids = projects.values_list('id', flat=True)
            candidatures = Candidature.objects.filter(AO_id__in=project_ids)
            
            if not candidatures.exists():
                return JsonResponse({
                    "status": True,
                    "total": 0,
                    "data": [],
                    "message": "No consultants assigned to this client's projects"
                }, safe=False)
            
            # Get all consultant IDs from these candidatures
            consultant_ids = candidatures.values_list('id_consultant', flat=True).distinct()
            consultants = Collaborateur.objects.filter(ID_collab__in=consultant_ids)
            
            # Prepare response data with enhanced details
            consultants_data = []
            
            for consultant in consultants:
                # Get the ESN information
                esn_name = "Unknown ESN"
                try:
                    if consultant.ID_ESN:
                        esn = ESN.objects.get(ID_ESN=consultant.ID_ESN)
                        esn_name = esn.Raison_sociale
                except ESN.DoesNotExist:
                    pass
                
                # Get the consultant's candidatures for this client
                consultant_candidatures = candidatures.filter(id_consultant=consultant.ID_collab)
                
                # Get active projects
                active_projects = []
                for candidature in consultant_candidatures:
                    try:
                        project = AppelOffre.objects.get(id=candidature.AO_id)
                        
                        # Check if there's an active contract
                        has_contract = Contrat.objects.filter(
                            candidature_id=candidature.id_cd,
                            statut__in=['actif', 'Actif', 'en cours', 'En cours']
                        ).exists()
                        
                        # Only include active projects with valid contracts
                        if has_contract and candidature.statut in ['Sélectionnée', 'Acceptée']:
                            active_projects.append({
                                "id": project.id,
                                "title": project.titre,
                                "start_date": project.date_debut,
                                "end_date": project.date_limite,
                                "tjm": float(candidature.tjm) if candidature.tjm else 0
                            })
                    except AppelOffre.DoesNotExist:
                        continue
                
                # Build consultant profile
                consultant_data = {
                    "id": consultant.ID_collab,
                    "name": f"{consultant.Nom} {consultant.Prenom}",
                    "email": consultant.Mail,
                    "phone": consultant.Telephone,
                    "esn": esn_name,
                    "esn_id": consultant.ID_ESN,
                    "position": consultant.Poste or "Consultant",
                    "active_projects": active_projects,
                    "project_count": len(active_projects),
                    "profile_photo": consultant.img_path if consultant.img_path else None
                }
                
                consultants_data.append(consultant_data)
            
            return JsonResponse({
                "status": True,
                "total": len(consultants_data),
                "data": consultants_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)

@csrf_exempt
def get_project_title_by_id(request):
    """
    API endpoint to retrieve just the title of a project by its ID.
    Used for quick lookups and references in UI components.
    
    GET parameters:
    - project_id: ID of the project to fetch (required)
    
    Returns the project ID and title in a simple format.
    """
    if request.method == 'GET':
        project_id = request.GET.get('project_id')
        
        if not project_id:
            return JsonResponse({
                "status": False,
                "message": "project_id parameter is required"
            }, safe=False, status=400)
            
        try:
            # Get the project by ID
            project = AppelOffre.objects.get(id=project_id)
            
            return JsonResponse({
                "status": True,
                "data": {
                    "project_id": project_id,
                    "titre": project.titre
                }
            }, safe=False)
            
        except AppelOffre.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": f"Project with ID {project_id} not found"
            }, safe=False, status=404)
            
        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)

@csrf_exempt
def consultants_cra_commercial(request):
    """
    API endpoint to get CRA data for consultants managed by a commercial.
    
    Query Parameters:
    - commercial_id (required): The commercial user ID
    - period (optional): Format "YYYY-MM" (e.g., "2024-01") - defaults to current month
    - cra_status (optional): Filter by CRA status ("À saisir", "EVP", "EVC", "Validé", "annule")
    - include_periods (optional): Set to "true" to include available periods list
    - include_stats (optional): Set to "true" to include status statistics
    - consultant_id (optional): Get detailed data for specific consultant
    
    Returns detailed CRA information for consultants with optional filtering and statistics.
    """
    if request.method == 'GET':
        # Get required parameters
        commercial_id = request.GET.get('commercial_id')
        
        if not commercial_id:
            return JsonResponse({
                "status": False,
                "message": "commercial_id parameter is required"
            }, safe=False, status=400)
            
        try:
            # First, get the commercial's information
            try:
                commercial = Collaborateur.objects.get(ID_collab=commercial_id)
                
                # Check if user is a commercial
                if commercial.Poste and commercial.Poste.lower() != 'commercial':
                    return JsonResponse({
                        "status": False,
                        "message": f"User is not a commercial (current role: {commercial.Poste})"
                    }, safe=False, status=400)
                    
                # Get ESN ID for finding consultants
                esn_id = commercial.ID_ESN
                
                if not esn_id:
                    return JsonResponse({
                        "status": False,
                        "message": "Commercial is not associated with any ESN"
                    }, safe=False, status=400)
                
            except Collaborateur.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": "Commercial not found"
                }, safe=False, status=404)
            
            # Get optional parameters
            consultant_id = request.GET.get('consultant_id')
            
            # Handle period parameter
            period = request.GET.get('period')
            if not period:
                # Default to current month
                from datetime import datetime
                now = datetime.now()
                period = now.strftime('%Y-%m')
                
            # Parse period to standard format (MM_YYYY)
            year, month = period.split('-')
            standard_period = f"{month}_{year}"
            
            # Get CRA status filter
            cra_status = request.GET.get('cra_status')
            
            # Parse boolean flags
            include_periods = request.GET.get('include_periods', 'false').lower() == 'true'
            include_stats = request.GET.get('include_stats', 'false').lower() == 'true'
            
            # Get consultants in the same ESN as the commercial
            query = Collaborateur.objects.filter(
                ID_ESN=esn_id,
                Poste__icontains='consultant'  # Filter only consultants
            )
            
            # Filter by consultant_id if provided
            if consultant_id:
                query = query.filter(ID_collab=consultant_id)
                
            consultants_data = []
            
            # Process each consultant
            for consultant in query:
                # Get CRA data for this consultant and period
                cra_records = CRA_CONSULTANT.objects.filter(
                    id_consultan=consultant.ID_collab,
                    période=standard_period
                )
                
                # Apply status filter if provided
                if cra_status and cra_records:
                    cra_records = cra_records.filter(statut=cra_status)
                
                # Skip this consultant if no matching CRA records after filtering
                if cra_status and not cra_records.exists():
                    continue
                
                # Get detailed CRA imputations
                cra_imputations = CRA_imputation.objects.filter(
                    id_consultan=consultant.ID_collab,
                    période=standard_period
                )
                
                # Get ESN information
                esn_info = None
                if consultant.ID_ESN:
                    try:
                        esn = ESN.objects.get(ID_ESN=consultant.ID_ESN)
                        esn_info = {
                            "ID_ESN": esn.ID_ESN,
                            "Raison_sociale": esn.Raison_sociale
                        }
                    except ESN.DoesNotExist:
                        pass
                
                # Get current client and mission
                current_client = "N/A"
                current_mission = "N/A"
                
                # Find the most recent active project
                try:
                    candidatures = Candidature.objects.filter(
                        id_consultant=consultant.ID_collab,
                        statut__in=['Sélectionnée', 'Acceptée']
                    ).order_by('-id_cd')
                    
                    if candidatures.exists():
                        candidature = candidatures.first()
                        
                        # Get project information
                        try:
                            project = AppelOffre.objects.get(id=candidature.AO_id)
                            current_mission = project.titre
                            
                            # Get client information
                            try:
                                client = Client.objects.get(ID_clt=project.client_id)
                                current_client = client.raison_sociale
                            except Client.DoesNotExist:
                                pass
                        except AppelOffre.DoesNotExist:
                            pass
                except Exception:
                    pass
                
                # Calculate CRA summary
                cra_summary = {
                    "period": period,
                    "status": "À saisir",
                    "total_days": 0,
                    "submitted_days": 0,
                    "validated_days": 0,
                    "pending_days": 0,
                    "last_update": None
                }
                
                # Update summary from CRA records
                if cra_records.exists():
                    cra = cra_records.first()
                    cra_summary["status"] = cra.statut
                    cra_summary["total_days"] = cra.n_jour or 0
                    
                    # Count days by status
                    if cra.statut == 'Validé':
                        cra_summary["validated_days"] = cra_summary["total_days"]
                    elif cra.statut in ['EVP', 'EVC']:
                        cra_summary["submitted_days"] = cra_summary["total_days"]
                        cra_summary["pending_days"] = cra_summary["total_days"]
                    
                    # Last update - since date_validation doesn't exist, use current date or None
                    from datetime import datetime
                    cra_summary["last_update"] = datetime.now().strftime("%Y-%m-%d")
                
                # Prepare CRA details if consultant_id is specified
                cra_details = []
                if consultant_id:
                    for imputation in cra_imputations:
                        # Get project and client info
                        project_name = "Non spécifié"
                        client_name = "Non spécifié"
                        
                        if imputation.id_bdc:
                            try:
                                project = AppelOffre.objects.get(id=imputation.id_bdc)
                                project_name = project.titre
                                
                                if project.client_id:
                                    try:
                                        client = Client.objects.get(ID_clt=project.client_id)
                                        client_name = client.raison_sociale
                                    except Client.DoesNotExist:
                                        pass
                            except AppelOffre.DoesNotExist:
                                pass
                        
                        # Create detail entry
                        detail = {
                            "date": f"{year}-{month}-{imputation.jour.zfill(2)}",
                            "status": imputation.statut if hasattr(imputation, 'statut') else "N/A",
                            "hours": imputation.Durée or 0,
                            "type": imputation.type,
                            "project": project_name,
                            "client": client_name,
                            "description": imputation.commentaire or ""
                        }
                        
                        cra_details.append(detail)
                
                # Create consultant data structure
                consultant_data = {
                    "ID_collab": consultant.ID_collab,
                    "Nom": consultant.Nom,
                    "Prenom": consultant.Prenom,
                    "email": consultant.email,
                    "current_client": current_client,
                    "current_mission": current_mission,
                    "cra_summary": cra_summary,
                    "esn_info": esn_info
                }
                
                # Add detailed CRA info if requested
                if consultant_id:
                    consultant_data["cra_details"] = cra_details
                
                consultants_data.append(consultant_data)
            
            # Prepare response data
            response_data = {
                "consultants": consultants_data
            }
            
            # Add periods information if requested
            if include_periods:
                periods_data = []
                
                # Get all distinct periods from CRA_CONSULTANT for these consultants
                consultant_ids = query.values_list('ID_collab', flat=True)
                distinct_periods = CRA_CONSULTANT.objects.filter(
                    id_consultan__in=consultant_ids
                ).values_list('période', flat=True).distinct()
                
                for period_str in distinct_periods:
                    # Convert from MM_YYYY to display format
                    try:
                        month, year = period_str.split('_')
                        month_int = int(month)
                        
                        # Get month name
                        import locale
                        try:
                            locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
                        except:
                            pass
                            
                        from datetime import datetime
                        month_name = datetime(int(year), month_int, 1).strftime('%B')
                        
                        # Count consultants and CRAs for this period
                        consultant_count = CRA_CONSULTANT.objects.filter(
                            id_consultan__in=consultant_ids,
                            période=period_str
                        ).values('id_consultan').distinct().count()
                        
                        total_cras = CRA_CONSULTANT.objects.filter(
                            id_consultan__in=consultant_ids,
                            période=period_str
                        ).count()
                        
                        period_data = {
                            "period": f"{year}-{month.zfill(2)}",
                            "display_name": f"{month_name.capitalize()} {year}",
                            "consultant_count": consultant_count,
                            "total_cras": total_cras
                        }
                        
                        periods_data.append(period_data)
                    except:
                        # Skip invalid period formats
                        continue
                
                # Sort periods by date (newest first)
                periods_data.sort(key=lambda x: x["period"], reverse=True)
                response_data["periods"] = periods_data
            
            # Add statistics if requested
            if include_stats:
                # Get status breakdown for current period
                status_counts = {}
                status_options = ['À saisir', 'EVP', 'EVC', 'Validé', 'annule']
                
                for status in status_options:
                    count = CRA_CONSULTANT.objects.filter(
                        id_consultan__in=consultant_ids,
                        période=standard_period,
                        statut=status
                    ).count()
                    status_counts[status] = count
                
                # Calculate completion rate
                total_consultants = query.count()
                completed = status_counts.get('Validé', 0)
                completion_rate = (completed / total_consultants * 100) if total_consultants > 0 else 0
                
                # Get latest update timestamp - don't use date_validation as it doesn't exist
                from datetime import datetime
                last_updated = datetime.now().strftime("%Y-%m-%d")
                
                statistics = {
                    "total_consultants": total_consultants,
                    "status_breakdown": status_counts,
                    "completion_rate": round(completion_rate, 1),
                    "last_updated": last_updated
                }
                
                response_data["statistics"] = statistics
            
            return JsonResponse({
                "status": True,
                "data": response_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def get_all_cra_consultant(request):
    """
    API endpoint to retrieve all CRA_CONSULTANT records with filtering options.
    
    GET parameters:
    - consultant_id: Optional - filter by specific consultant
    - period: Optional - filter by period (format: MM_YYYY)
    - status: Optional - filter by CRA status
    - esn_id: Optional - filter by ESN ID (will find all consultants in the ESN)
    - limit: Optional - limit the number of results (default: 100)
    - offset: Optional - offset for pagination (default: 0)
    
    Returns a list of CRA_CONSULTANT records with related consultant information.
    """
    if request.method == 'GET':
        try:
            # Build the base query
            query = CRA_CONSULTANT.objects.all()
            
            # Apply filters if provided
            consultant_id = request.GET.get('consultant_id')
            if consultant_id:
                query = query.filter(id_consultan=consultant_id)
                
            period = request.GET.get('period')
            if period:
                query = query.filter(période=period)
                
            status = request.GET.get('status')
            if status:
                query = query.filter(statut=status)
            
            esn_id = request.GET.get('esn_id')
            if esn_id:
                # Find all consultants in this ESN
                consultant_ids = Collaborateur.objects.filter(
                    ID_ESN=esn_id
                ).values_list('ID_collab', flat=True)
                
                query = query.filter(id_consultan__in=consultant_ids)
            
            # Pagination
            limit = int(request.GET.get('limit', 100))
            offset = int(request.GET.get('offset', 0))
            
            # Count total records before pagination
            total_count = query.count()
            
            # Apply sorting and pagination
            query = query.order_by('-id_CRA')[offset:offset+limit]
            
            # Serialize the data
            cra_serializer = CRA_CONSULTANTSerializer(query, many=True)
            
            # Enhance data with consultant information
            enhanced_data = []
            for cra in cra_serializer.data:
                consultant_id = cra.get('id_consultan')
                
                # Get consultant information
                consultant_info = None
                if consultant_id:
                    try:
                        consultant = Collaborateur.objects.get(ID_collab=consultant_id)
                        consultant_info = {
                            "id": consultant.ID_collab,
                            "name": f"{consultant.Nom} {consultant.Prenom}",
                            "email": consultant.email,
                            "position": consultant.Poste,
                            "esn_id": consultant.ID_ESN
                        }
                        
                        # Get ESN information if available
                        if consultant.ID_ESN:
                            try:
                                esn = ESN.objects.get(ID_ESN=consultant.ID_ESN)
                                consultant_info["esn_name"] = esn.Raison_sociale
                            except ESN.DoesNotExist:
                                consultant_info["esn_name"] = "Unknown ESN"
                    except Collaborateur.DoesNotExist:
                        consultant_info = {"id": consultant_id, "name": "Unknown Consultant"}
                
                # Get project information if available
                project_info = None
                if cra.get('id_bdc'):
                    try:
                        project = AppelOffre.objects.get(id=cra['id_bdc'])
                        project_info = {
                            "id": project.id,
                            "title": project.titre,
                            "client_id": project.client_id
                        }
                        
                        # Get client information if available
                        if project.client_id:
                            try:
                                client = Client.objects.get(ID_clt=project.client_id)
                                project_info["client_name"] = client.raison_sociale
                            except Client.DoesNotExist:
                                project_info["client_name"] = "Unknown Client"
                    except AppelOffre.DoesNotExist:
                        project_info = {"id": cra['id_bdc'], "title": "Unknown Project"}
                
                # Create enhanced CRA record
                enhanced_cra = {
                    **cra,
                    "consultant": consultant_info,
                    "project": project_info
                }
                
                enhanced_data.append(enhanced_cra)
            
            # Prepare pagination info
            pagination = {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            }
            
            return JsonResponse({
                "status": True,
                "pagination": pagination,
                "data": enhanced_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def get_cra_consultant_by_client_period(request):
    """
    API endpoint to retrieve CRA consultant records for a specific client and period.
    
    GET parameters:
    - client_id: ID of the client (required)
    - period: Period in format MM_YYYY (required)
    - status: Optional filter for CRA status
    
    Returns CRA records with consultant information for the specified client and period.
    """
    if request.method == 'GET':
        client_id = request.GET.get('client_id')
        period = request.GET.get('period')
        status = request.GET.get('status')
        
        if not client_id or not period:
            return JsonResponse({
                "status": False,
                "message": "Both client_id and period parameters are required"
            }, safe=False, status=400)
            
        try:
            # Get client information
            try:
                client = Client.objects.get(ID_clt=client_id)
                client_name = client.raison_sociale
            except Client.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"Client with ID {client_id} not found"
                }, safe=False, status=404)
            
            # Query base: CRA records for this client and period
            cra_query = CRA_CONSULTANT.objects.filter(
                id_client=client_id,
                période=period
            )
            
            # Apply status filter if provided
            if status:
                cra_query = cra_query.filter(statut=status)
            
            # If no records found, return empty result
            if not cra_query.exists():
                return JsonResponse({
                    "status": True,
                    "client": {
                        "id": client_id,
                        "name": client_name
                    },
                    "period": period,
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Get all consultant IDs for efficient querying
            consultant_ids = cra_query.values_list('id_consultan', flat=True).distinct()
            consultants = {
                consultant.ID_collab: consultant 
                for consultant in Collaborateur.objects.filter(ID_collab__in=consultant_ids)
            }
            
            # Get all ESN IDs for efficient querying
            esn_ids = set(consultant.ID_ESN for consultant in consultants.values() if consultant.ID_ESN)
            esns = {
                esn.ID_ESN: esn 
                for esn in ESN.objects.filter(ID_ESN__in=esn_ids)
            }
            
            # Get all project IDs (stored in id_bdc field) for efficient querying
            project_ids = cra_query.values_list('id_bdc', flat=True).distinct()
            projects = {
                project.id: project 
                for project in AppelOffre.objects.filter(id__in=project_ids)
            }
            
            # Get imputations for these CRAs
            imputations = CRA_imputation.objects.filter(
                id_client=client_id,
                période=period,
                id_consultan__in=consultant_ids
            )
            
            # Group imputations by consultant
            imputations_by_consultant = {}
            for imp in imputations:
                if imp.id_consultan not in imputations_by_consultant:
                    imputations_by_consultant[imp.id_consultan] = []
                imputations_by_consultant[imp.id_consultan].append(imp)
            
            # Build enhanced response data
            enhanced_data = []
            for cra in cra_query:
                # Get consultant information
                consultant_info = None
                if cra.id_consultan in consultants:
                    consultant = consultants[cra.id_consultan]
                    consultant_info = {
                        "id": consultant.ID_collab,
                        "name": f"{consultant.Nom} {consultant.Prenom}",
                        "email": consultant.email,
                        "position": consultant.Poste
                    }
                    
                    # Add ESN information if available
                    if consultant.ID_ESN and consultant.ID_ESN in esns:
                        esn = esns[consultant.ID_ESN]
                        consultant_info["esn"] = {
                            "id": esn.ID_ESN,
                            "name": esn.Raison_sociale
                        }
                
                # Get project information
                project_info = None
                if cra.id_bdc and cra.id_bdc in projects:
                    project = projects[cra.id_bdc]
                    project_info = {
                        "id": project.id,
                        "title": project.titre,
                        "description": project.description
                    }
                
                # Get imputations for this consultant
                consultant_imputations = imputations_by_consultant.get(cra.id_consultan, [])
                
                # Calculate metrics
                total_days = len(consultant_imputations)
                total_hours = sum(float(imp.Durée) for imp in consultant_imputations if imp.Durée)
                
                # Create daily breakdown
                daily_breakdown = []
                for imp in consultant_imputations:
                    daily_breakdown.append({
                        "day": imp.jour,
                        "type": imp.type,
                        "hours": float(imp.Durée) if imp.Durée else 0,
                        "status": imp.statut,
                        "comment": imp.commentaire or ""
                    })
                
                # Sort daily breakdown by day
                daily_breakdown.sort(key=lambda x: x["day"])
                
                # Build the enhanced CRA record
                enhanced_cra = {
                    "id": cra.id_CRA,
                    "consultant": consultant_info,
                    "project": project_info,
                    "period": cra.période,
                    "status": cra.statut,
                    "total_days": total_days,
                    "total_hours": total_hours,
                    "comment": cra.commentaire or "",
                    "daily_breakdown": daily_breakdown
                }
                
                enhanced_data.append(enhanced_cra)
            
            # Sort by consultant name
            enhanced_data.sort(key=lambda x: x["consultant"]["name"] if x["consultant"] else "")
            
            return JsonResponse({
                "status": True,
                "client": {
                    "id": client_id,
                    "name": client_name
                },
                "period": period,
                "total": len(enhanced_data),
                "data": enhanced_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def get_cra_consultant_records(request):
    """
    API endpoint to retrieve CRA_CONSULTANT records with basic filtering.
    
    GET parameters:
    - consultant_id: Optional - filter by specific consultant
    - period: Optional - filter by period (format: MM_YYYY)
    - status: Optional - filter by CRA status
    - esn_id: Optional - filter by ESN ID
    - client_id: Optional - filter by client ID
    - limit: Optional - limit the number of results (default: 100)
    - offset: Optional - offset for pagination (default: 0)
    
    Returns data directly from the CRA_CONSULTANT table without joins.
    """
    if request.method == 'GET':
        try:
            # Build the base query
            query = CRA_CONSULTANT.objects.all()
            
            # Apply filters if provided
            consultant_id = request.GET.get('consultant_id')
            if consultant_id:
                query = query.filter(id_consultan=consultant_id)
                
            period = request.GET.get('period')
            if period:
                query = query.filter(période=period)
                
            status = request.GET.get('status')
            if status:
                query = query.filter(statut=status)
            
            esn_id = request.GET.get('esn_id')
            if esn_id:
                query = query.filter(id_esn=esn_id)
                
            client_id = request.GET.get('client_id')
            if client_id:
                query = query.filter(id_client=client_id)
            
            # Pagination
            limit = int(request.GET.get('limit', 100))
            offset = int(request.GET.get('offset', 0))
            
            # Count total records before pagination
            total_count = query.count()
            
            # Apply sorting and pagination
            query = query.order_by('-id_CRA')[offset:offset+limit]
            
            # Serialize the data
            cra_serializer = CRA_CONSULTANTSerializer(query, many=True)
            
            # Prepare pagination info
            pagination = {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            }
            
            return JsonResponse({
                "status": True,
                "pagination": pagination,
                "data": cra_serializer.data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def get_cra_consultant_by_client(request):
    """
    API endpoint to retrieve CRA_CONSULTANT records for a specific client.
    
    GET parameters:
    - client_id: ID of the client (required)
    - period: Optional - filter by period (format: MM_YYYY)
    - status: Optional - filter by CRA status
    
    Returns all CRA_CONSULTANT records for the specified client.
    """
    if request.method == 'GET':
        client_id = request.GET.get('client_id')
        
        if not client_id:
            return JsonResponse({
                "status": False,
                "message": "client_id parameter is required"
            }, safe=False, status=400)
            
        try:
            # Build the base query - filter by client_id
            query = CRA_CONSULTANT.objects.filter(id_client=client_id)
            
            # Apply additional filters if provided
            period = request.GET.get('period')
            if period:
                query = query.filter(période=period)
                
            status = request.GET.get('status')
            if status:
                query = query.filter(statut=status)
            
            # Order by most recent first (assuming id_CRA is auto-incrementing)
            query = query.order_by('-id_CRA')
            
            # If no records found, return empty result
            if not query.exists():
                return JsonResponse({
                    "status": True,
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Serialize the data
            cra_serializer = CRA_CONSULTANTSerializer(query, many=True)
            
            # Enhance data with additional information
            enhanced_data = []
            for cra in cra_serializer.data:
                # Get consultant information
                consultant_info = None
                if cra.get('id_consultan'):
                    try:
                        consultant = Collaborateur.objects.get(ID_collab=cra['id_consultan'])
                        consultant_info = {
                            "id": consultant.ID_collab,
                            "name": f"{consultant.Nom} {consultant.Prenom}",
                            "email": consultant.email
                        }
                    except Collaborateur.DoesNotExist:
                        pass
                
                # Get ESN information
                esn_info = None
                if cra.get('id_esn'):
                    try:
                        esn = ESN.objects.get(ID_ESN=cra['id_esn'])
                        esn_info = {
                            "id": esn.ID_ESN,
                            "name": esn.Raison_sociale
                        }
                    except ESN.DoesNotExist:
                        pass
                
                # Get project/BDC information
                project_info = None
                if cra.get('id_bdc'):
                    try:
                        project = AppelOffre.objects.get(id=cra['id_bdc'])
                        project_info = {
                            "id": project.id,
                            "title": project.titre
                        }
                    except AppelOffre.DoesNotExist:
                        pass
                
                # Build enhanced CRA record
                enhanced_cra = {
                    **cra,
                    "consultant": consultant_info,
                    "esn": esn_info,
                    "project": project_info
                }
                
                enhanced_data.append(enhanced_cra)
            
            return JsonResponse({
                "status": True,
                "total": len(enhanced_data),
                "data": enhanced_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def get_cra_consultants_by_client(request):
    """
    API endpoint to retrieve all CRA_CONSULTANT records for a specific client.
    
    GET parameters:
    - client_id: ID of the client (required)
    - period: Optional - filter by period (format: MM_YYYY)
    - status: Optional - filter by CRA status
    
    Returns a list of CRA_CONSULTANT records for the specified client with AppelOffre title and ESN name.
    """
    if request.method == 'GET':
        client_id = request.GET.get('client_id')
        
        if not client_id:
            return JsonResponse({
                "status": False,
                "message": "client_id parameter is required"
            }, safe=False, status=400)
            
        try:
            # Build query - filter by client_id
            query = CRA_CONSULTANT.objects.filter(id_client=client_id)
            
            # Apply additional filters if provided
            period = request.GET.get('period')
            if period:
                query = query.filter(période=period)
                
            status = request.GET.get('status')
            if status:
                query = query.filter(statut=status)
            
            # Order by most recent first
            query = query.order_by('-id_CRA')
            
            # If no records found, return empty result
            if not query.exists():
                return JsonResponse({
                    "status": True,
                    "message": "No CRA records found for this client",
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Get all unique IDs for efficient querying
            consultant_ids = set(cra.id_consultan for cra in query if cra.id_consultan)
            esn_ids = set(cra.id_esn for cra in query if cra.id_esn)
            bdc_ids = set(cra.id_bdc for cra in query if cra.id_bdc)
            
            # Fetch related data in bulk
            consultants = {c.ID_collab: c for c in Collaborateur.objects.filter(ID_collab__in=consultant_ids)}
            esns = {e.ID_ESN: e for e in ESN.objects.filter(ID_ESN__in=esn_ids)}
            appel_offres = {ao.id: ao for ao in AppelOffre.objects.filter(id__in=bdc_ids)}
            
            # Fetch candidatures to get TJM data - match consultant and project
            # Note: id_bdc can contain either actual BDC IDs or AppelOffre IDs
            candidatures = {}
            bdc_to_ao_mapping = {}  # Map BDC IDs to AppelOffre IDs
            
            if consultant_ids and bdc_ids:
                # First, try direct matching with AppelOffre IDs
                direct_candidatures = Candidature.objects.filter(
                    id_consultant__in=consultant_ids,
                    AO_id__in=bdc_ids
                )
                for candidature in direct_candidatures:
                    key = (candidature.id_consultant, candidature.AO_id)
                    candidatures[key] = candidature
                
                # For BDC IDs that didn't match, try to find them via BDC -> AppelOffre mapping
                unmatched_bdc_ids = []
                for bdc_id in bdc_ids:
                    has_match = any(key[1] == bdc_id for key in candidatures.keys())
                    if not has_match:
                        unmatched_bdc_ids.append(bdc_id)
                
                # Look up BDC records to find their associated AppelOffre IDs
                if unmatched_bdc_ids:
                    from .models import Bondecommande
                    bdcs = Bondecommande.objects.filter(id_bdc__in=unmatched_bdc_ids)
                    for bdc in bdcs:
                        if bdc.candidature_id:
                            try:
                                candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                                bdc_to_ao_mapping[bdc.id_bdc] = candidature.AO_id
                                key = (candidature.id_consultant, bdc.id_bdc)  # Use BDC ID as key
                                candidatures[key] = candidature
                            except Candidature.DoesNotExist:
                                continue
            
            # Convert queryset to list and process
            formatted_data = []
            for cra in query:
                cra_data = {
                    "id_CRA": cra.id_CRA,
                    "id_bdc": cra.id_bdc,
                    "n_jour": cra.n_jour,
                    "commentaire": cra.commentaire or "",
                    "id_esn": cra.id_esn,
                    "id_client": cra.id_client,
                    "id_consultan": cra.id_consultan,
                    "période": cra.période,
                    "statut": cra.statut
                }
                
                # Add consultant information
                if cra.id_consultan in consultants:
                    consultant = consultants[cra.id_consultan]
                    cra_data["consultant_name"] = f"{consultant.Prenom} {consultant.Nom}"
                    cra_data["consultant_email"] = consultant.email
                    cra_data["consultant_position"] = consultant.Poste or "Consultant"
                else:
                    cra_data["consultant_name"] = f"Consultant ID: {cra.id_consultan}"
                    cra_data["consultant_email"] = ""
                    cra_data["consultant_position"] = ""
                
                # Add ESN information
                if cra.id_esn in esns:
                    esn = esns[cra.id_esn]
                    cra_data["esn_name"] = esn.Raison_sociale
                    cra_data["esn_contact"] = esn.mail_Contact
                else:
                    cra_data["esn_name"] = f"ESN ID: {cra.id_esn}"
                    cra_data["esn_contact"] = ""
                
                # Add AppelOffre information (stored in id_bdc field)
                candidature_tjm = None
                candidature_info = None
                
                if cra.id_bdc in appel_offres:
                    appel_offre = appel_offres[cra.id_bdc]
                    cra_data["appel_offre_titre"] = appel_offre.titre
                    cra_data["appel_offre_description"] = appel_offre.description or ""
                    cra_data["appel_offre_profil"] = appel_offre.profil
                    cra_data["appel_offre_statut"] = appel_offre.statut
                    cra_data["appel_offre_date_debut"] = appel_offre.date_debut.isoformat() if appel_offre.date_debut else None
                    cra_data["appel_offre_jours"] = appel_offre.jours
                    
                    # Get TJM from candidature - try direct match first
                    candidature_key = (cra.id_consultan, cra.id_bdc)
                    if candidature_key in candidatures:
                        candidature = candidatures[candidature_key]
                        candidature_tjm = candidature.tjm
                        candidature_info = {
                            "id": candidature.id_cd,
                            "tjm": candidature.tjm,
                            "date_disponibilite": candidature.date_disponibilite.isoformat() if candidature.date_disponibilite else None,
                            "statut": candidature.statut
                        }
                else:
                    # Try to get BDC info and associated candidature
                    try:
                        from .models import Bondecommande
                        bdc = Bondecommande.objects.get(id_bdc=cra.id_bdc)
                        
                        # Try to get the AppelOffre through Candidature
                        if bdc.candidature_id:
                            try:
                                candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                                if candidature.AO_id:
                                    try:
                                        appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                                        cra_data["appel_offre_titre"] = appel_offre.titre
                                        cra_data["appel_offre_description"] = appel_offre.description or ""
                                        cra_data["appel_offre_profil"] = appel_offre.profil
                                        cra_data["appel_offre_statut"] = appel_offre.statut
                                        cra_data["appel_offre_date_debut"] = appel_offre.date_debut.isoformat() if appel_offre.date_debut else None
                                        cra_data["appel_offre_jours"] = appel_offre.jours
                                    except AppelOffre.DoesNotExist:
                                        cra_data["appel_offre_titre"] = f"BDC #{bdc.numero_bdc}"
                                        cra_data["appel_offre_description"] = bdc.description or f"Montant: {bdc.montant_total}€"
                                else:
                                    cra_data["appel_offre_titre"] = f"BDC #{bdc.numero_bdc}"
                                    cra_data["appel_offre_description"] = bdc.description or f"Montant: {bdc.montant_total}€"
                                
                                # Get TJM from candidature
                                candidature_tjm = candidature.tjm
                                candidature_info = {
                                    "id": candidature.id_cd,
                                    "tjm": candidature.tjm,
                                    "date_disponibilite": candidature.date_disponibilite.isoformat() if candidature.date_disponibilite else None,
                                    "statut": candidature.statut
                                }
                            except Candidature.DoesNotExist:
                                cra_data["appel_offre_titre"] = f"BDC #{bdc.numero_bdc}"
                                cra_data["appel_offre_description"] = bdc.description or f"Montant: {bdc.montant_total}€"
                        else:
                            cra_data["appel_offre_titre"] = f"BDC #{bdc.numero_bdc}"
                            cra_data["appel_offre_description"] = bdc.description or f"Montant: {bdc.montant_total}€"
                    except:
                        cra_data["appel_offre_titre"] = f"Projet ID: {cra.id_bdc}"
                        cra_data["appel_offre_description"] = ""
                    
                    # Fill default values if not set
                    if "appel_offre_profil" not in cra_data:
                        cra_data["appel_offre_profil"] = ""
                        cra_data["appel_offre_statut"] = ""
                        cra_data["appel_offre_date_debut"] = None
                        cra_data["appel_offre_jours"] = None
                
                # Add candidature info if found
                if candidature_info:
                    cra_data["candidature"] = candidature_info
                
                # Add TJM directly to the CRA record for easier access
                cra_data["tjm"] = candidature_tjm
                
                formatted_data.append(cra_data)
            
            return JsonResponse({
                "status": True,
                "total": len(formatted_data),
                "data": formatted_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    
@csrf_exempt
def get_cra_consultants_by_commercial(request):
    """
    API endpoint to retrieve all CRA_CONSULTANT records for a specific commercial.
    
    GET parameters:
    - commercial_id: ID of the commercial (required)
    - period: Optional - filter by period (format: MM_YYYY)
    - status: Optional - filter by CRA status
    
    Returns a list of CRA_CONSULTANT records for consultants managed by the specified commercial.
    """
    if request.method == 'GET':
        commercial_id = request.GET.get('commercial_id')
        
        if not commercial_id:
            return JsonResponse({
                "status": False,
                "message": "commercial_id parameter is required"
            }, safe=False, status=400)
            
        try:
            # Verify commercial exists and get their ESN
            try:
                commercial = Collaborateur.objects.get(ID_collab=commercial_id)
                if not commercial.Poste or 'commercial' not in commercial.Poste.lower():
                    return JsonResponse({
                        "status": False,
                        "message": "Specified user is not a commercial"
                    }, safe=False, status=400)
                
                esn_id = commercial.ID_ESN
                if not esn_id:
                    return JsonResponse({
                        "status": False,
                        "message": "Commercial is not associated with any ESN"
                    }, safe=False, status=400)
            except Collaborateur.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": "Commercial not found"
                }, safe=False, status=404)
            
            # Get all consultants belonging to the same ESN as the commercial
            consultants = Collaborateur.objects.filter(
                ID_ESN=esn_id,
                Poste__icontains='consultant'
            )
            consultant_ids = list(consultants.values_list('ID_collab', flat=True))
            
            if not consultant_ids:
                return JsonResponse({
                    "status": True,
                    "message": "No consultants found for this commercial's ESN",
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Build query - filter by consultant IDs
            query = CRA_CONSULTANT.objects.filter(id_consultan__in=consultant_ids)
            
            # Apply additional filters if provided
            period = request.GET.get('period')
            if period:
                query = query.filter(période=period)
                
            status = request.GET.get('status')
            if status:
                query = query.filter(statut=status)
            
            # Order by most recent first
            query = query.order_by('-id_CRA')
            
            # If no records found, return empty result
            if not query.exists():
                return JsonResponse({
                    "status": True,
                    "message": "No CRA records found for consultants managed by this commercial",
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Serialize the data
            from django.core.serializers import serialize
            from json import loads
            
            # Convert queryset to JSON
            serialized_data = loads(serialize('json', query))
            
            # Extract fields from serialized data
            formatted_data = []
            for item in serialized_data:
                # Basic CRA data
                cra_data = {
                    "id_CRA": item['pk'],
                    **item['fields']
                }
                
                # Add consultant information
                try:
                    consultant = Collaborateur.objects.get(ID_collab=cra_data['id_consultan'])
                    cra_data['consultant_name'] = f"{consultant.Prenom} {consultant.Nom}"
                    cra_data['consultant_email'] = consultant.email
                except Collaborateur.DoesNotExist:
                    cra_data['consultant_name'] = "Unknown"
                    cra_data['consultant_email'] = None
                
                # Add client information if available
                if cra_data.get('id_client'):
                    try:
                        client = Client.objects.get(ID_clt=cra_data['id_client'])
                        cra_data['client_name'] = client.raison_sociale
                    except Client.DoesNotExist:
                        cra_data['client_name'] = "Unknown Client"
                
                formatted_data.append(cra_data)
            
            return JsonResponse({
                "status": True,
                "commercial": {
                    "id": commercial.ID_collab,
                    "name": f"{commercial.Prenom} {commercial.Nom}",
                    "esn_id": esn_id
                },
                "total": len(formatted_data),
                "data": formatted_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)

@csrf_exempt
def get_cra_by_commercial_period(request):
    """
    Retrieve CRA imputations for consultants managed by a specific commercial, filtered by period.
    
    Request parameters:
    - commercial_id: ID of the commercial (required)
    - period: The period (format: MM_YYYY) (required)
    - status: Optional filter for CRA status
    
    Returns CRA imputations with consultant information for consultants managed by the specified commercial.
    """
    if request.method == 'GET':
        commercial_id = request.GET.get('commercial_id')
        period = request.GET.get('period')
        status = request.GET.get('status')
        
        if not commercial_id or not period:
            return JsonResponse({
                "status": False,
                "message": "Both commercial_id and period parameters are required"
            }, safe=False, status=400)
            
        try:
            # Get commercial information and verify role
            try:
                commercial = Collaborateur.objects.get(ID_collab=commercial_id)
                if not commercial.Poste or 'commercial' not in commercial.Poste.lower():
                    return JsonResponse({
                        "status": False,
                        "message": "Specified user is not a commercial"
                    }, safe=False, status=400)
                
                esn_id = commercial.ID_ESN
                if not esn_id:
                    return JsonResponse({
                        "status": False,
                        "message": "Commercial is not associated with any ESN"
                    }, safe=False, status=400)
                    
                # Get ESN name
                try:
                    esn = ESN.objects.get(ID_ESN=esn_id)
                    esn_name = esn.Raison_sociale
                except ESN.DoesNotExist:
                    esn_name = f"ESN ID: {esn_id}"
                
            except Collaborateur.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"Commercial with ID {commercial_id} not found"
                }, safe=False, status=404)
            
            # Get all consultants belonging to the same ESN as the commercial
            consultants = Collaborateur.objects.filter(
                ID_ESN=esn_id,
                Poste__icontains='consultant'
            )
            consultant_ids = list(consultants.values_list('ID_collab', flat=True))
            
            if not consultant_ids:
                return JsonResponse({
                    "status": True,
                    "commercial": {
                        "id": commercial_id,
                        "name": f"{commercial.Prenom} {commercial.Nom}",
                        "esn": {
                            "id": esn_id,
                            "name": esn_name
                        }
                    },
                    "period": period,
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Create a lookup dictionary for consultants for efficient access
            consultants_dict = {
                consultant.ID_collab: consultant 
                for consultant in consultants
            }
            
            # Get imputations directly - focus on the imputations, not CRA_CONSULTANT
            imputations = CRA_imputation.objects.filter(
                id_consultan__in=consultant_ids,
                période=period
            )
            
            if not imputations.exists():
                return JsonResponse({
                    "status": True,
                    "commercial": {
                        "id": commercial_id,
                        "name": f"{commercial.Prenom} {commercial.Nom}",
                        "esn": {
                            "id": esn_id,
                            "name": esn_name
                        }
                    },
                    "period": period,
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Get all client IDs for efficient querying
            client_ids = set(imp.id_client for imp in imputations if imp.id_client)
            clients = {
                client.ID_clt: client 
                for client in Client.objects.filter(ID_clt__in=client_ids)
            }
            
            # Get all project IDs for efficient querying
            project_ids = set(imp.id_bdc for imp in imputations if imp.id_bdc)
            projects = {
                project.id: project 
                for project in AppelOffre.objects.filter(id__in=project_ids)
            }
            
            # Group imputations by consultant
            imputations_by_consultant = {}
            for imp in imputations:
                if imp.id_consultan not in imputations_by_consultant:
                    imputations_by_consultant[imp.id_consultan] = []
                imputations_by_consultant[imp.id_consultan].append(imp)
            
            # Get CRA_CONSULTANT records for status info
            cra_consultants = {
                (cra.id_consultan, cra.période): cra 
                for cra in CRA_CONSULTANT.objects.filter(
                    id_consultan__in=consultant_ids,
                    période=period
                )
            }
            if status:
                # Filter by status if specified
                cra_consultants = {
                    k: v for k, v in cra_consultants.items() if v.statut == status
                }
                # Only include consultants with matching status
                consultant_ids = [k[0] for k in cra_consultants.keys()]
                imputations_by_consultant = {
                    k: v for k, v in imputations_by_consultant.items() if k in consultant_ids
                }
            
            # Build enhanced response data
            enhanced_data = []
            for consultant_id, consultant_imputations in imputations_by_consultant.items():
                # Get consultant information
                consultant_info = None
                if consultant_id in consultants_dict:
                    consultant = consultants_dict[consultant_id]
                    consultant_info = {
                        "id": consultant.ID_collab,
                        "name": f"{consultant.Nom} {consultant.Prenom}",
                        "email": consultant.email,
                        "position": consultant.Poste
                    }
                else:
                    # Skip if consultant not found
                    continue
                
                # Get CRA status from CRA_CONSULTANT if available
                cra_status = "À saisir"  # Default status
                cra_comment = ""
                cra_id = None
                if (consultant_id, period) in cra_consultants:
                    cra = cra_consultants[(consultant_id, period)]
                    cra_status = cra.statut
                    cra_comment = cra.commentaire or ""
                    cra_id = cra.id_CRA
                
                # Calculate metrics
                total_days = len(consultant_imputations)
                try:
                    total_hours = sum(float(imp.Durée) for imp in consultant_imputations if imp.Durée)
                except (ValueError, TypeError):
                    total_hours = 0
                
                # Get client and project info for this consultant
                consultant_client_ids = set(imp.id_client for imp in consultant_imputations if imp.id_client)
                consultant_clients = {
                    client_id: clients[client_id] for client_id in consultant_client_ids if client_id in clients
                }
                
                consultant_project_ids = set(imp.id_bdc for imp in consultant_imputations if imp.id_bdc)
                consultant_projects = {
                    project_id: projects[project_id] for project_id in consultant_project_ids if project_id in projects
                }
                
                # Create daily breakdown
                daily_breakdown = []
                for imp in consultant_imputations:
                    day_info = {
                        "day": imp.jour,
                        "type": imp.type,
                        "hours": float(imp.Durée) if imp.Durée else 0,
                    }
                    
                    # Safely check for commentaire attribute
                    try:
                        day_info["comment"] = imp.commentaire if hasattr(imp, 'commentaire') and imp.commentaire else ""
                    except:
                        day_info["comment"] = ""
                    
                    # Safely add status if it exists
                    try:
                        day_info["status"] = imp.statut if hasattr(imp, 'statut') else cra_status
                    except:
                        day_info["status"] = cra_status
                        
                    # Add project and client info if available
                    if imp.id_bdc and imp.id_bdc in projects:
                        day_info["project"] = projects[imp.id_bdc].titre
                    
                    if imp.id_client and imp.id_client in clients:
                        day_info["client"] = clients[imp.id_client].raison_sociale
                        
                    daily_breakdown.append(day_info)
                
                # Sort daily breakdown by day
                daily_breakdown.sort(key=lambda x: int(x["day"]))
                
                # Get primary client and project for this consultant
                primary_client = None
                if consultant_clients:
                    # Find most common client
                    client_counts = {}
                    for imp in consultant_imputations:
                        if imp.id_client in clients:
                            client_counts[imp.id_client] = client_counts.get(imp.id_client, 0) + 1
                    
                    if client_counts:
                        most_common_client_id = max(client_counts, key=client_counts.get)
                        client = clients[most_common_client_id]
                        primary_client = {
                            "id": client.ID_clt,
                            "name": client.raison_sociale
                        }
                
                primary_project = None
                if consultant_projects:
                    # Find most common project
                    project_counts = {}
                    for imp in consultant_imputations:
                        if imp.id_bdc and imp.id_bdc in projects:
                            project_counts[imp.id_bdc] = project_counts.get(imp.id_bdc, 0) + 1
                    
                    if project_counts:
                        most_common_project_id = max(project_counts, key=project_counts.get)
                        project = projects[most_common_project_id]
                        primary_project = {
                            "id": project.id,
                            "title": project.titre,
                            "description": project.description
                        }
                
                # Build the enhanced CRA record
                enhanced_cra = {
                    "id": cra_id,
                    "consultant": consultant_info,
                    "client": primary_client,
                    "project": primary_project,
                    "period": period,
                    "status": cra_status,
                    "total_days": total_days,
                    "total_hours": total_hours,
                    "comment": cra_comment,
                    "daily_breakdown": daily_breakdown
                }
                
                enhanced_data.append(enhanced_cra)
            
            # Sort by consultant name
            enhanced_data.sort(key=lambda x: x["consultant"]["name"] if x["consultant"] else "")
            
            return JsonResponse({
                "status": True,
                "commercial": {
                    "id": commercial_id,
                    "name": f"{commercial.Prenom} {commercial.Nom}",
                    "esn": {
                        "id": esn_id,
                        "name": esn_name
                    }
                },
                "period": period,
                "total": len(enhanced_data),
                "data": enhanced_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    """
    Retrieve CRA imputations for consultants managed by a specific commercial, filtered by period.
    
    Request parameters:
    - commercial_id: ID of the commercial (required)
    - period: The period (format: MM_YYYY) (required)
    - status: Optional filter for CRA status
    
    Returns CRA records with consultant information for consultants managed by the specified commercial.
    """
    if request.method == 'GET':
        commercial_id = request.GET.get('commercial_id')
        period = request.GET.get('period')
        status = request.GET.get('status')
        
        if not commercial_id or not period:
            return JsonResponse({
                "status": False,
                "message": "Both commercial_id and period parameters are required"
            }, safe=False, status=400)
            
        try:
            # Get commercial information and verify role
            try:
                commercial = Collaborateur.objects.get(ID_collab=commercial_id)
                if not commercial.Poste or 'commercial' not in commercial.Poste.lower():
                    return JsonResponse({
                        "status": False,
                        "message": "Specified user is not a commercial"
                    }, safe=False, status=400)
                
                esn_id = commercial.ID_ESN
                if not esn_id:
                    return JsonResponse({
                        "status": False,
                        "message": "Commercial is not associated with any ESN"
                    }, safe=False, status=400)
                    
                # Get ESN name
                try:
                    esn = ESN.objects.get(ID_ESN=esn_id)
                    esn_name = esn.Raison_sociale
                except ESN.DoesNotExist:
                    esn_name = f"ESN ID: {esn_id}"
                
            except Collaborateur.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"Commercial with ID {commercial_id} not found"
                }, safe=False, status=404)
            
            # Get all consultants belonging to the same ESN as the commercial
            consultants = Collaborateur.objects.filter(
                ID_ESN=esn_id,
                Poste__icontains='consultant'
            )
            consultant_ids = list(consultants.values_list('ID_collab', flat=True))
            
            if not consultant_ids:
                return JsonResponse({
                    "status": True,
                    "commercial": {
                        "id": commercial_id,
                        "name": f"{commercial.Prenom} {commercial.Nom}",
                        "esn": {
                            "id": esn_id,
                            "name": esn_name
                        }
                    },
                    "period": period,
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Query base: CRA records for consultants managed by this commercial in this period
            cra_query = CRA_CONSULTANT.objects.filter(
                id_consultan__in=consultant_ids,
                période=period
            )
            
            # Apply status filter if provided
            if status:
                cra_query = cra_query.filter(statut=status)
            
            # If no records found, return empty result
            if not cra_query.exists():
                return JsonResponse({
                    "status": True,
                    "commercial": {
                        "id": commercial_id,
                        "name": f"{commercial.Prenom} {commercial.Nom}",
                        "esn": {
                            "id": esn_id,
                            "name": esn_name
                        }
                    },
                    "period": period,
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Create a lookup dictionary for consultants for efficient access
            consultants_dict = {
                consultant.ID_collab: consultant 
                for consultant in consultants
            }
            
            # Get all client IDs for efficient querying
            client_ids = set(cra.id_client for cra in cra_query if cra.id_client)
            clients = {
                client.ID_clt: client 
                for client in Client.objects.filter(ID_clt__in=client_ids)
            }
            
            # Get all project IDs (stored in id_bdc field) for efficient querying
            project_ids = set(cra.id_bdc for cra in cra_query if cra.id_bdc)
            projects = {
                project.id: project 
                for project in AppelOffre.objects.filter(id__in=project_ids)
            }
            
            # Get imputations for these CRAs
            imputations = CRA_imputation.objects.filter(
                id_consultan__in=consultant_ids,
                période=period
            )
            
            # Group imputations by consultant
            imputations_by_consultant = {}
            for imp in imputations:
                if imp.id_consultan not in imputations_by_consultant:
                    imputations_by_consultant[imp.id_consultan] = []
                imputations_by_consultant[imp.id_consultan].append(imp)
            
            # Build enhanced response data
            enhanced_data = []
            for cra in cra_query:
                # Get consultant information
                consultant_info = None
                if cra.id_consultan in consultants_dict:
                    consultant = consultants_dict[cra.id_consultan]
                    consultant_info = {
                        "id": consultant.ID_collab,
                        "name": f"{consultant.Nom} {consultant.Prenom}",
                        "email": consultant.email,
                        "position": consultant.Poste
                    }
                
                # Get client information
                client_info = None
                if cra.id_client and cra.id_client in clients:
                    client = clients[cra.id_client]
                    client_info = {
                        "id": client.ID_clt,
                        "name": client.raison_sociale
                    }
                
                # Get project information
                project_info = None
                if cra.id_bdc and cra.id_bdc in projects:
                    project = projects[cra.id_bdc]
                    project_info = {
                        "id": project.id,
                        "title": project.titre,
                        "description": project.description
                    }
                
                # Get imputations for this consultant
                consultant_imputations = imputations_by_consultant.get(cra.id_consultan, [])
                
                # Calculate metrics
                total_days = len(consultant_imputations)
                total_hours = sum(float(imp.Durée) for imp in consultant_imputations if imp.Durée)
                
                # Create daily breakdown
                daily_breakdown = []
                for imp in consultant_imputations:
                    day_info = {
                        "day": imp.jour,
                        "type": imp.type,
                        "hours": float(imp.Durée) if imp.Durée else 0,
                    }
                    
                    # Check if commentaire attribute exists before accessing it
                    if hasattr(imp, 'commentaire'):
                        day_info["comment"] = imp.commentaire or ""
                    else:
                        day_info["comment"] = ""  # Provide default empty string
                    
                    # Add status if it exists
                    if hasattr(imp, 'statut'):
                        day_info["status"] = imp.statut
                        
                    # Add project and client info if available
                    if hasattr(imp, 'id_bdc') and imp.id_bdc and imp.id_bdc in projects:
                        day_info["project"] = projects[imp.id_bdc].titre
                    
                    if hasattr(imp, 'id_client') and imp.id_client and imp.id_client in clients:
                        day_info["client"] = clients[imp.id_client].raison_sociale
                        
                    daily_breakdown.append(day_info)
                
                # Sort daily breakdown by day
                daily_breakdown.sort(key=lambda x: x["day"])
                
                # Build the enhanced CRA record
                enhanced_cra = {
                    "id": cra.id_CRA,
                    "consultant": consultant_info,
                    "client": client_info,
                    "project": project_info,
                    "period": cra.période,
                    "status": cra.statut,
                    "total_days": total_days,
                    "total_hours": total_hours,
                    "comment": cra.commentaire or "",
                    "daily_breakdown": daily_breakdown
                }
                
                enhanced_data.append(enhanced_cra)
            
            # Sort by consultant name
            enhanced_data.sort(key=lambda x: x["consultant"]["name"] if x["consultant"] else "")
            
            return JsonResponse({
                "status": True,
                "commercial": {
                    "id": commercial_id,
                    "name": f"{commercial.Prenom} {commercial.Nom}",
                    "esn": {
                        "id": esn_id,
                        "name": esn_name
                    }
                },
                "period": period,
                "total": len(enhanced_data),
                "data": enhanced_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    """
    Retrieve CRA imputations for consultants managed by a specific commercial, filtered by period.
    
    Request parameters:
    - commercial_id: ID of the commercial (required)
    - period: The period (format: MM_YYYY) (required)
    - status: Optional filter for CRA status
    
    Returns CRA records with consultant information for consultants managed by the specified commercial.
    """
    if request.method == 'GET':
        commercial_id = request.GET.get('commercial_id')
        period = request.GET.get('period')
        status = request.GET.get('status')
        
        if not commercial_id or not period:
            return JsonResponse({
                "status": False,
                "message": "Both commercial_id and period parameters are required"
            }, safe=False, status=400)
            
        try:
            # Get commercial information and verify role
            try:
                commercial = Collaborateur.objects.get(ID_collab=commercial_id)
                if not commercial.Poste or 'commercial' not in commercial.Poste.lower():
                    return JsonResponse({
                        "status": False,
                        "message": "Specified user is not a commercial"
                    }, safe=False, status=400)
                
                esn_id = commercial.ID_ESN
                if not esn_id:
                    return JsonResponse({
                        "status": False,
                        "message": "Commercial is not associated with any ESN"
                    }, safe=False, status=400)
                    
                # Get ESN name
                try:
                    esn = ESN.objects.get(ID_ESN=esn_id)
                    esn_name = esn.Raison_sociale
                except ESN.DoesNotExist:
                    esn_name = f"ESN ID: {esn_id}"
                
            except Collaborateur.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"Commercial with ID {commercial_id} not found"
                }, safe=False, status=404)
            
            # Get all consultants belonging to the same ESN as the commercial
            consultants = Collaborateur.objects.filter(
                ID_ESN=esn_id,
                Poste__icontains='consultant'
            )
            consultant_ids = list(consultants.values_list('ID_collab', flat=True))
            
            if not consultant_ids:
                return JsonResponse({
                    "status": True,
                    "commercial": {
                        "id": commercial_id,
                        "name": f"{commercial.Prenom} {commercial.Nom}",
                        "esn": {
                            "id": esn_id,
                            "name": esn_name
                        }
                    },
                    "period": period,
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Query base: CRA records for consultants managed by this commercial in this period
            cra_query = CRA_CONSULTANT.objects.filter(
                id_consultan__in=consultant_ids,
                période=period
            )
            
            # Apply status filter if provided
            if status:
                cra_query = cra_query.filter(statut=status)
            
            # If no records found, return empty result
            if not cra_query.exists():
                return JsonResponse({
                    "status": True,
                    "commercial": {
                        "id": commercial_id,
                        "name": f"{commercial.Prenom} {commercial.Nom}",
                        "esn": {
                            "id": esn_id,
                            "name": esn_name
                        }
                    },
                    "period": period,
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Create a lookup dictionary for consultants for efficient access
            consultants_dict = {
                consultant.ID_collab: consultant 
                for consultant in consultants
            }
            
            # Get all client IDs for efficient querying
            client_ids = set(cra.id_client for cra in cra_query if cra.id_client)
            clients = {
                client.ID_clt: client 
                for client in Client.objects.filter(ID_clt__in=client_ids)
            }
            
            # Get all project IDs (stored in id_bdc field) for efficient querying
            project_ids = set(cra.id_bdc for cra in cra_query if cra.id_bdc)
            projects = {
                project.id: project 
                for project in AppelOffre.objects.filter(id__in=project_ids)
            }
            
            # Get imputations for these CRAs
            imputations = CRA_imputation.objects.filter(
                id_consultan__in=consultant_ids,
                période=period
            )
            
            # Group imputations by consultant
            imputations_by_consultant = {}
            for imp in imputations:
                if imp.id_consultan not in imputations_by_consultant:
                    imputations_by_consultant[imp.id_consultan] = []
                imputations_by_consultant[imp.id_consultan].append(imp)
            
            # Build enhanced response data
            enhanced_data = []
            for cra in cra_query:
                # Get consultant information
                consultant_info = None
                if cra.id_consultan in consultants_dict:
                    consultant = consultants_dict[cra.id_consultan]
                    consultant_info = {
                        "id": consultant.ID_collab,
                        "name": f"{consultant.Nom} {consultant.Prenom}",
                        "email": consultant.email,
                        "position": consultant.Poste
                    }
                
                # Get client information
                client_info = None
                if cra.id_client and cra.id_client in clients:
                    client = clients[cra.id_client]
                    client_info = {
                        "id": client.ID_clt,
                        "name": client.raison_sociale
                    }
                
                # Get project information
                project_info = None
                if cra.id_bdc and cra.id_bdc in projects:
                    project = projects[cra.id_bdc]
                    project_info = {
                        "id": project.id,
                        "title": project.titre,
                        "description": project.description
                    }
                
                # Get imputations for this consultant
                consultant_imputations = imputations_by_consultant.get(cra.id_consultan, [])
                
                # Calculate metrics
                total_days = len(consultant_imputations)
                total_hours = sum(float(imp.Durée) for imp in consultant_imputations if imp.Durée)
                
                # Create daily breakdown
                daily_breakdown = []
                for imp in consultant_imputations:
                    day_info = {
                        "day": imp.jour,
                        "type": imp.type,
                        "hours": float(imp.Durée) if imp.Durée else 0,
                    }
                    
                    # Fix: Check if commentaire attribute exists before accessing it
                    if hasattr(imp, 'commentaire'):
                        day_info["comment"] = imp.commentaire or ""
                    else:
                        day_info["comment"] = ""  # Provide default empty string
                    
                    # Add status if it exists
                    if hasattr(imp, 'statut'):
                        day_info["status"] = imp.statut
                        
                    # Add project and client info if available
                    if imp.id_bdc in projects:
                        day_info["project"] = projects[imp.id_bdc].titre
                    
                    if imp.id_client in clients:
                        day_info["client"] = clients[imp.id_client].raison_sociale
                        
                    daily_breakdown.append(day_info)
                
                # Sort daily breakdown by day
                daily_breakdown.sort(key=lambda x: x["day"])
                
                # Build the enhanced CRA record
                enhanced_cra = {
                    "id": cra.id_CRA,
                    "consultant": consultant_info,
                    "client": client_info,
                    "project": project_info,
                    "period": cra.période,
                    "status": cra.statut,
                    "total_days": total_days,
                    "total_hours": total_hours,
                    "comment": cra.commentaire or "",
                    "daily_breakdown": daily_breakdown
                }
                
                enhanced_data.append(enhanced_cra)
            
            # Sort by consultant name
            enhanced_data.sort(key=lambda x: x["consultant"]["name"] if x["consultant"] else "")
            
            return JsonResponse({
                "status": True,
                "commercial": {
                    "id": commercial_id,
                    "name": f"{commercial.Prenom} {commercial.Nom}",
                    "esn": {
                        "id": esn_id,
                        "name": esn_name
                    }
                },
                "period": period,
                "total": len(enhanced_data),
                "data": enhanced_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    """
    Retrieve CRA imputations for consultants managed by a specific commercial, filtered by period.
    
    Request parameters:
    - commercial_id: ID of the commercial (required)
    - period: The period (format: MM_YYYY) (required)
    - status: Optional filter for CRA status
    
    Returns CRA records with consultant information for consultants managed by the specified commercial.
    """
    if request.method == 'GET':
        commercial_id = request.GET.get('commercial_id')
        period = request.GET.get('period')
        status = request.GET.get('status')
        
        if not commercial_id or not period:
            return JsonResponse({
                "status": False,
                "message": "Both commercial_id and period parameters are required"
            }, safe=False, status=400)
            
        try:
            # Get commercial information and verify role
            try:
                commercial = Collaborateur.objects.get(ID_collab=commercial_id)
                if not commercial.Poste or 'commercial' not in commercial.Poste.lower():
                    return JsonResponse({
                        "status": False,
                        "message": "Specified user is not a commercial"
                    }, safe=False, status=400)
                
                esn_id = commercial.ID_ESN
                if not esn_id:
                    return JsonResponse({
                        "status": False,
                        "message": "Commercial is not associated with any ESN"
                    }, safe=False, status=400)
                    
                # Get ESN name
                try:
                    esn = ESN.objects.get(ID_ESN=esn_id)
                    esn_name = esn.Raison_sociale
                except ESN.DoesNotExist:
                    esn_name = f"ESN ID: {esn_id}"
                
            except Collaborateur.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"Commercial with ID {commercial_id} not found"
                }, safe=False, status=404)
            
            # Get all consultants belonging to the same ESN as the commercial
            consultants = Collaborateur.objects.filter(
                ID_ESN=esn_id,
                Poste__icontains='consultant'
            )
            consultant_ids = list(consultants.values_list('ID_collab', flat=True))
            
            if not consultant_ids:
                return JsonResponse({
                    "status": True,
                    "commercial": {
                        "id": commercial_id,
                        "name": f"{commercial.Prenom} {commercial.Nom}",
                        "esn": {
                            "id": esn_id,
                            "name": esn_name
                        }
                    },
                    "period": period,
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Query base: CRA records for consultants managed by this commercial in this period
            cra_query = CRA_CONSULTANT.objects.filter(
                id_consultan__in=consultant_ids,
                période=period
            )
            
            # Apply status filter if provided
            if status:
                cra_query = cra_query.filter(statut=status)
            
            # If no records found, return empty result
            if not cra_query.exists():
                return JsonResponse({
                    "status": True,
                    "commercial": {
                        "id": commercial_id,
                        "name": f"{commercial.Prenom} {commercial.Nom}",
                        "esn": {
                            "id": esn_id,
                            "name": esn_name
                        }
                    },
                    "period": period,
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Create a lookup dictionary for consultants for efficient access
            consultants_dict = {
                consultant.ID_collab: consultant 
                for consultant in consultants
            }
            
            # Get all client IDs for efficient querying
            client_ids = set(cra.id_client for cra in cra_query if cra.id_client)
            clients = {
                client.ID_clt: client 
                for client in Client.objects.filter(ID_clt__in=client_ids)
            }
            
            # Get all project IDs (stored in id_bdc field) for efficient querying
            project_ids = set(cra.id_bdc for cra in cra_query if cra.id_bdc)
            projects = {
                project.id: project 
                for project in AppelOffre.objects.filter(id__in=project_ids)
            }
            
            # Get imputations for these CRAs
            imputations = CRA_imputation.objects.filter(
                id_consultan__in=consultant_ids,
                période=period
            )
            
            # Group imputations by consultant
            imputations_by_consultant = {}
            for imp in imputations:
                if imp.id_consultan not in imputations_by_consultant:
                    imputations_by_consultant[imp.id_consultan] = []
                imputations_by_consultant[imp.id_consultan].append(imp)
            
            # Build enhanced response data
            enhanced_data = []
            for cra in cra_query:
                # Get consultant information
                consultant_info = None
                if cra.id_consultan in consultants_dict:
                    consultant = consultants_dict[cra.id_consultan]
                    consultant_info = {
                        "id": consultant.ID_collab,
                        "name": f"{consultant.Nom} {consultant.Prenom}",
                        "email": consultant.email,
                        "position": consultant.Poste
                    }
                
                # Get client information
                client_info = None
                if cra.id_client and cra.id_client in clients:
                    client = clients[cra.id_client]
                    client_info = {
                        "id": client.ID_clt,
                        "name": client.raison_sociale
                    }
                
                # Get project information
                project_info = None
                if cra.id_bdc and cra.id_bdc in projects:
                    project = projects[cra.id_bdc]
                    project_info = {
                        "id": project.id,
                        "title": project.titre,
                        "description": project.description
                    }
                
                # Get imputations for this consultant
                consultant_imputations = imputations_by_consultant.get(cra.id_consultan, [])
                
                # Calculate metrics
                total_days = len(consultant_imputations)
                total_hours = sum(float(imp.Durée) for imp in consultant_imputations if imp.Durée)
                
                # Create daily breakdown
                daily_breakdown = []
                for imp in consultant_imputations:
                    day_info = {
                        "day": imp.jour,
                        "type": imp.type,
                        "hours": float(imp.Durée) if imp.Durée else 0,
                        "comment": imp.commentaire or ""
                    }
                    
                    # Add status if it exists
                    if hasattr(imp, 'statut'):
                        day_info["status"] = imp.statut
                        
                    # Add project and client info if available
                    if imp.id_bdc in projects:
                        day_info["project"] = projects[imp.id_bdc].titre
                    
                    if imp.id_client in clients:
                        day_info["client"] = clients[imp.id_client].raison_sociale
                        
                    daily_breakdown.append(day_info)
                
                # Sort daily breakdown by day
                daily_breakdown.sort(key=lambda x: x["day"])
                
                # Build the enhanced CRA record
                enhanced_cra = {
                    "id": cra.id_CRA,
                    "consultant": consultant_info,
                    "client": client_info,
                    "project": project_info,
                    "period": cra.période,
                    "status": cra.statut,
                    "total_days": total_days,
                    "total_hours": total_hours,
                    "comment": cra.commentaire or "",
                    "daily_breakdown": daily_breakdown
                }
                
                enhanced_data.append(enhanced_cra)
            
            # Sort by consultant name
            enhanced_data.sort(key=lambda x: x["consultant"]["name"] if x["consultant"] else "")
            
            return JsonResponse({
                "status": True,
                "commercial": {
                    "id": commercial_id,
                    "name": f"{commercial.Prenom} {commercial.Nom}",
                    "esn": {
                        "id": esn_id,
                        "name": esn_name
                    }
                },
                "period": period,
                "total": len(enhanced_data),
                "data": enhanced_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
@csrf_exempt
def get_ndf_consultants_by_consultant(request):
    """
    GET endpoint to retrieve all NDF_CONSULTANT records by consultant.
    
    Query parameters:
    - consultant_id: ID of the consultant (required)
    - period: Optional filter (format: MM_YYYY)
    - status: Optional filter (e.g. 'validé')
    - esn_id: Optional filter
    - client_id: Optional filter
    - limit: Optional pagination limit (default=100)
    - offset: Optional pagination offset (default=0)
    """
    if request.method == 'GET':
        consultant_id = request.GET.get('consultant_id')
        if not consultant_id:
            return JsonResponse({
                "status": False,
                "message": "consultant_id is required"
            }, safe=False, status=400)
        
        try:
            # Base query
            query = NDF_CONSULTANT.objects.filter(id_consultan=consultant_id)
            
            # Optional filters
            period = request.GET.get('period')
            if period:
                query = query.filter(période=period)
            
            status = request.GET.get('status')
            if status:
                query = query.filter(statut=status)
            
            esn_id = request.GET.get('esn_id')
            if esn_id:
                query = query.filter(id_esn=esn_id)

            client_id = request.GET.get('client_id')
            if client_id:
                query = query.filter(id_client=client_id)

            # Pagination
            limit = int(request.GET.get('limit', 100))
            offset = int(request.GET.get('offset', 0))
            
            total_count = query.count()
            query = query.order_by('-id_ndf')[offset:offset+limit]

            serializer = NDF_CONSULTANTSerializer(query, many=True)
            data = []
            
            # Enhance each record
            for item in serializer.data:
                record = dict(item)
                
                # Consultant info
                try:
                    consultant = Collaborateur.objects.get(ID_collab=record['id_consultan'])
                    record['consultant_name'] = f"{consultant.Prenom} {consultant.Nom}"
                except Collaborateur.DoesNotExist:
                    record['consultant_name'] = "Unknown Consultant"
                
                # Client info
                if record.get('id_client'):
                    try:
                        client = Client.objects.get(ID_clt=record['id_client'])
                        record['client_name'] = client.raison_sociale
                        record['client_responsible'] = getattr(client, 'responsible', '') or ''
                    except Client.DoesNotExist:
                        record['client_name'] = "Unknown Client"
                        record['client_responsible'] = ""
                else:
                    record['client_responsible'] = ""
                
                # ESN info
                if record.get('id_esn'):
                    try:
                        esn = ESN.objects.get(ID_ESN=record['id_esn'])
                        record['esn_name'] = esn.Raison_sociale
                        record['esn_responsible'] = getattr(esn, 'responsible', '') or ''
                    except ESN.DoesNotExist:
                        record['esn_name'] = "Unknown ESN"
                        record['esn_responsible'] = ""
                else:
                    record['esn_responsible'] = ""

                # Project info through BDC -> Candidature -> AppelOffre chain
                if record.get('id_bdc'):
                    try:
                        bdc = Bondecommande.objects.get(id_bdc=record['id_bdc'])
                        candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                        appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                        record['project_name'] = appel_offre.titre
                        record['project_id'] = appel_offre.id
                        record['bdc_number'] = getattr(bdc, 'numero_bdc', '') or ''
                    except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, AppelOffre.DoesNotExist):
                        record['project_name'] = "Unknown Project"
                        record['project_id'] = None
                        record['bdc_number'] = ""
                else:
                    record['project_name'] = "No Project"
                    record['project_id'] = None
                    record['bdc_number'] = ""

                data.append(record)

            return JsonResponse({
                "status": True,
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "data": data
            }, safe=False)
        
        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)

    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)

@csrf_exempt
def ndf_consultant_view(request, id=0):
    """
    Handle GET, POST, PUT, DELETE for NDF_CONSULTANT.
    - GET (id=0 optional): Retrieve all or specific record by query params or ID.
      e.g. /ndf-consultant-view/?consultant_id=123 or /ndf-consultant-view/10/
    - POST: Create new NDF_CONSULTANT record.
    - PUT: Update existing record by ID.
    - DELETE: Delete existing record by ID.
    """
    if request.method == 'GET':
        if id > 0:
            # Get single record by ID
            try:
                record = NDF_CONSULTANT.objects.get(pk=id)
                serializer = NDF_CONSULTANTSerializer(record)
                return JsonResponse({"status": True, "data": serializer.data}, safe=False)
            except NDF_CONSULTANT.DoesNotExist:
                return JsonResponse({"status": False, "message": "Record not found"}, safe=False, status=404)
        else:
            # Use filters if provided
            query = NDF_CONSULTANT.objects.all()
            
            consultant_id = request.GET.get('consultant_id')
            if consultant_id:
                query = query.filter(id_consultan=consultant_id)
                
            period = request.GET.get('period')
            if period:
                query = query.filter(période=period)
                
            status = request.GET.get('status')
            if status:
                query = query.filter(statut=status)
                
            esn_id = request.GET.get('esn_id')
            if esn_id:
                query = query.filter(id_esn=esn_id)
                
            client_id = request.GET.get('client_id')
            if client_id:
                query = query.filter(id_client=client_id)
                
            # Filter by responsable_id (commercial manager)
            responsable_id = request.GET.get('responsable_id')
            if responsable_id:
                # Find consultants who have candidatures directly assigned to this commercial
                # (where commercial_id = responsable_id in the same candidature row)
                consultants_for_commercial = Candidature.objects.filter(
                    commercial_id=responsable_id
                ).values_list('id_consultant', flat=True).distinct()
                
                if consultants_for_commercial:
                    # Filter NDFs by these consultants
                    query = query.filter(id_consultan__in=consultants_for_commercial)
                else:
                    # If no candidatures found for this commercial, return empty queryset
                    query = query.none()
                
            # Pagination
            limit = int(request.GET.get('limit', 100))
            offset = int(request.GET.get('offset', 0))
            
            total_count = query.count()
            query = query.order_by('-id_ndf')[offset:offset+limit]
            
            serializer = NDF_CONSULTANTSerializer(query, many=True)
            
            # Enhance with additional information
            enhanced_data = []
            for item in serializer.data:
                record = dict(item)
                
                # Add consultant info
                try:
                    consultant = Collaborateur.objects.get(ID_collab=record['id_consultan'])
                    record['consultant_name'] = f"{consultant.Prenom} {consultant.Nom}"
                    record['consultant_email'] = consultant.email
                except Collaborateur.DoesNotExist:
                    record['consultant_name'] = "Unknown Consultant"
                    record['consultant_email'] = ""
                
                # Add client info
                if record.get('id_client'):
                    try:
                        client = Client.objects.get(ID_clt=record['id_client'])
                        record['client_name'] = client.raison_sociale
                    except Client.DoesNotExist:
                        record['client_name'] = "Unknown Client"
                
                # Add ESN info
                if record.get('id_esn'):
                    try:
                        esn = ESN.objects.get(ID_ESN=record['id_esn'])
                        record['esn_name'] = esn.Raison_sociale
                    except ESN.DoesNotExist:
                        record['esn_name'] = "Unknown ESN"
                
                # Project info through BDC -> Candidature -> AppelOffre chain
                if record.get('id_bdc'):
                    try:
                        bdc = Bondecommande.objects.get(id_bdc=record['id_bdc'])
                        candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                        appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                        record['project_name'] = appel_offre.titre
                        record['project_id'] = appel_offre.id
                    except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, AppelOffre.DoesNotExist):
                        record['project_name'] = "Unknown Project"
                        record['project_id'] = None
                else:
                    record['project_name'] = "No Project"
                    record['project_id'] = None
                
                enhanced_data.append(record)
            
            return JsonResponse({
                "status": True,
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "data": enhanced_data
            }, safe=False)

    elif request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            
            # Check for consultant_id - this is required
            if 'id_consultan' not in data or not data['id_consultan']:
                return JsonResponse({
                    "status": False, 
                    "message": "id_consultan is required"
                }, safe=False, status=400)
            
            # If id_esn is missing, get it from the consultant's record
            if 'id_esn' not in data or not data['id_esn']:
                try:
                    consultant = Collaborateur.objects.get(ID_collab=data['id_consultan'])
                    if consultant.ID_ESN:
                        data['id_esn'] = consultant.ID_ESN
                        print(f"ESN ID {data['id_esn']} retrieved from consultant record")
                except Collaborateur.DoesNotExist:
                    print(f"Warning: Consultant with ID {data['id_consultan']} not found")
                    pass  # Let serializer validation handle missing id_esn

            # Enhanced client ID resolution from multiple sources
            client_resolved = False
            
            # Method 1: Get client_id from BDC → Candidature → AppelOffre chain (PRIMARY)
            if ('id_client' not in data or not data['id_client']) and 'id_bdc' in data and data['id_bdc']:
                try:
                    # Get BDC record
                    bdc = Bondecommande.objects.get(id_bdc=data['id_bdc'])
                    print(f"Found BDC {data['id_bdc']} with candidature_id: {bdc.candidature_id}")
                    
                    # Get Candidature record
                    candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                    print(f"Found Candidature {bdc.candidature_id} with AO_id: {candidature.AO_id}")
                    
                    # Get AppelOffre record
                    appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                    print(f"Found AppelOffre {candidature.AO_id} with client_id: {appel_offre.client_id}")
                    
                    # Set client_id from AppelOffre
                    data['id_client'] = appel_offre.client_id
                    client_resolved = True
                    print(f"SUCCESS: Client ID {data['id_client']} resolved from BDC {data['id_bdc']} → Candidature {bdc.candidature_id} → AppelOffre {candidature.AO_id}")
                    
                except Bondecommande.DoesNotExist:
                    print(f"ERROR: BDC with ID {data.get('id_bdc')} not found")
                except Candidature.DoesNotExist:
                    print(f"ERROR: Candidature with ID {bdc.candidature_id if 'bdc' in locals() else 'unknown'} not found")
                except AppelOffre.DoesNotExist:
                    print(f"ERROR: AppelOffre with ID {candidature.AO_id if 'candidature' in locals() else 'unknown'} not found")
                except Exception as e:
                    print(f"ERROR: Failed to resolve client from BDC chain: {str(e)}")

            # Method 2: Get client_id directly from candidature_id → AppelOffre (if provided separately)
            if not client_resolved and ('id_client' not in data or not data['id_client']) and 'id_candidature' in data and data['id_candidature']:
                try:
                    candidature = Candidature.objects.get(id_cd=data['id_candidature'])
                    appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                    data['id_client'] = appel_offre.client_id
                    client_resolved = True
                    print(f"SUCCESS: Client ID {data['id_client']} resolved from candidature {data['id_candidature']} → AppelOffre {candidature.AO_id}")
                except (Candidature.DoesNotExist, AppelOffre.DoesNotExist) as e:
                    print(f"ERROR: Failed to resolve client from candidature {data.get('id_candidature')}: {str(e)}")

            # Method 3: Get client_id from consultant's most recent candidature (last resort)
            if not client_resolved and ('id_client' not in data or not data['id_client']):
                try:
                    # Find the most recent candidature for this consultant
                    recent_candidature = Candidature.objects.filter(
                        id_consultant=data['id_consultan']
                    ).order_by('-id_cd').first()
                    
                    if recent_candidature:
                        appel_offre = AppelOffre.objects.get(id=recent_candidature.AO_id)
                        data['id_client'] = appel_offre.client_id
                        client_resolved = True
                        print(f"SUCCESS: Client ID {data['id_client']} resolved from consultant's recent candidature {recent_candidature.id_cd} → AppelOffre {recent_candidature.AO_id}")
                    else:
                        print(f"WARNING: No candidatures found for consultant {data['id_consultan']}")
                except (Candidature.DoesNotExist, AppelOffre.DoesNotExist) as e:
                    print(f"ERROR: Failed to resolve client from consultant's candidatures: {str(e)}")

            # Log final resolution status
            if client_resolved:
                print(f"✅ CLIENT RESOLUTION SUCCESS: client_id = {data['id_client']}")
                
                # Verify client exists
                try:
                    client = Client.objects.get(ID_clt=data['id_client'])
                    print(f"✅ CLIENT VERIFIED: {client.raison_sociale}")
                except Client.DoesNotExist:
                    print(f"⚠️  WARNING: Client with ID {data['id_client']} does not exist in database")
            else:
                print("❌ CLIENT RESOLUTION FAILED: Could not resolve client_id from any source")
                print("Available data fields:", list(data.keys()))
            
            # Auto-resolve commercial ID from BDC → Candidature chain
            commercial_resolved = False
            if ('id_commercial' not in data or not data['id_commercial']) and 'id_bdc' in data and data['id_bdc']:
                try:
                    bdc = Bondecommande.objects.get(id_bdc=data['id_bdc'])
                    candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                    
                    if candidature.commercial_id:
                        data['id_commercial'] = candidature.commercial_id
                        commercial_resolved = True
                        print(f"✅ COMMERCIAL RESOLUTION SUCCESS: commercial_id = {data['id_commercial']} from BDC {data['id_bdc']} → Candidature {bdc.candidature_id}")
                    else:
                        print(f"⚠️  WARNING: No commercial assigned to Candidature {bdc.candidature_id}")
                except (Bondecommande.DoesNotExist, Candidature.DoesNotExist) as e:
                    print(f"ERROR: Failed to resolve commercial from BDC chain: {str(e)}")
            
            # Alternative: Get commercial from consultant's most recent candidature
            if not commercial_resolved and ('id_commercial' not in data or not data['id_commercial']):
                try:
                    recent_candidature = Candidature.objects.filter(
                        id_consultant=data['id_consultan']
                    ).order_by('-id_cd').first()
                    
                    if recent_candidature and recent_candidature.commercial_id:
                        data['id_commercial'] = recent_candidature.commercial_id
                        commercial_resolved = True
                        print(f"✅ COMMERCIAL RESOLUTION SUCCESS: commercial_id = {data['id_commercial']} from consultant's recent candidature {recent_candidature.id_cd}")
                    else:
                        print(f"⚠️  WARNING: No commercial found in consultant's candidatures")
                except Exception as e:
                    print(f"ERROR: Failed to resolve commercial from consultant's candidatures: {str(e)}")
            
            if commercial_resolved:
                print(f"✅ Commercial ID {data['id_commercial']} will receive notification")
            else:
                print(f"⚠️  No commercial assigned - notification will not be sent")
            
            # Set default status if not provided
            if 'statut' not in data or not data['statut']:
                data['statut'] = 'en attente'
                
            # Debug: Print final data before validation
            print("Final data for validation:", {k: v for k, v in data.items() if k != 'password'})
                
            # Validate data before saving
            serializer = NDF_CONSULTANTSerializer(data=data)
            
            if serializer.is_valid():
                ndf = serializer.save()
                print(f"✅ NDF CREATED SUCCESSFULLY: ID = {ndf.id_ndf}")
                
                # Create notification for submission - When consultant submits NDF
                try:
                    consultant = Collaborateur.objects.get(ID_collab=ndf.id_consultan)
                    consultant_name = f"{consultant.Prenom} {consultant.Nom}"
                    
                    # Notify commercial (if assigned)
                    if ndf.id_commercial:
                        send_notification(
                            user_id=ndf.id_consultan,
                            dest_id=ndf.id_commercial,
                            message=(
                                f"Nouvelle note de frais soumise par {consultant_name}. "
                                f"Type: {ndf.type_frais}, Montant: {ndf.montant_ttc} {ndf.devise}, Période: {ndf.période}."
                            ),
                            categorie="COMMERCIAL",
                            event="NDF soumise",
                            event_id=ndf.id_ndf
                        )
                        print(f"📧 Notification sent to Commercial {ndf.id_commercial}")
                    else:
                        print(f"⚠️  No commercial assigned to NDF {ndf.id_ndf}")
                        
                except Exception as e:
                    print(f"❌ Error creating notification: {str(e)}")
                
                return JsonResponse({
                    "status": True,
                    "message": "Note de frais ajoutée avec succès",
                    "data": serializer.data
                }, safe=False, status=201)
                
            else:
                print("❌ VALIDATION FAILED:", serializer.errors)
                return JsonResponse({
                    "status": False, 
                    "errors": serializer.errors,
                    "message": "Validation failed"
                }, safe=False, status=400)
                
        except Exception as e:
            import traceback
            print("❌ EXCEPTION IN POST:")
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
        
    elif request.method == 'PUT':
        if id <= 0:
            return JsonResponse({"status": False, "message": "ID parameter is required for update"}, safe=False, status=400)

        try:
            data = JSONParser().parse(request)
            
            # Get the existing record
            record = NDF_CONSULTANT.objects.get(pk=id)
            
            # Store old status for notifications
            old_status = record.statut
            
            serializer = NDF_CONSULTANTSerializer(record, data=data, partial=True)
            if serializer.is_valid():
                updated_ndf = serializer.save()
                
                # If status has changed, send notifications
                if 'statut' in data and data['statut'] != old_status:
                    try:
                        consultant = Collaborateur.objects.get(ID_collab=updated_ndf.id_consultan)
                        consultant_name = f"{consultant.Prenom} {consultant.Nom}"
                        new_status = data['statut']
                        
                        print(f"🔔 NDF {updated_ndf.id_ndf} status changed: '{old_status}' → '{new_status}'")
                        
                        # When commercial validates NDF
                        # Status codes:
                        # - EVP (En Validation Prestataire) = Submitted by consultant, waiting for commercial validation
                        # - EVC (En Validation Client) = Validated by commercial, waiting for client validation
                        # - Accepted/Approved/Validé = Final validation by client
                        commercial_validated = (
                            # Commercial validation: EVP → EVC (most common)
                            (old_status.upper() == 'EVP' and new_status.upper() == 'EVC') or
                            # OR status contains validation keywords but not client keywords
                            (
                                ('valid' in new_status.lower() or 'approv' in new_status.lower() or new_status.upper() == 'EVC') and
                                'client' not in old_status.lower() and
                                'accept' not in new_status.lower() and
                                'refus' not in new_status.lower() and
                                'reject' not in new_status.lower()
                            )
                        )
                        
                        if commercial_validated:
                            print(f"✅ Detected COMMERCIAL VALIDATION for NDF {updated_ndf.id_ndf}")
                            print(f"   NDF Details: client_id={updated_ndf.id_client}, commercial_id={updated_ndf.id_commercial}, consultant_id={updated_ndf.id_consultan}")
                            
                            # Notify client
                            if updated_ndf.id_client:
                                try:
                                    client = Client.objects.get(ID_clt=updated_ndf.id_client)
                                    print(f"   Client found: {client.raison_sociale} (ID: {client.ID_clt})")
                                    
                                    # Send notification
                                    notification_result = send_notification(
                                        user_id=updated_ndf.id_commercial or updated_ndf.id_consultan,
                                        dest_id=updated_ndf.id_client,
                                        message=(
                                            # f"<strong>Note de frais en attente de validation</strong><br><br>"
                                            f"Le commercial/responsable a validé la note de frais du consultant <strong>{consultant_name}</strong>.<br><br>"
                                            f"<strong>Détails de la note de frais :</strong><br>"
                                            f"• Type de frais : <strong>{updated_ndf.type_frais}</strong><br>"
                                            f"• Montant : <strong>{updated_ndf.montant_ttc} {updated_ndf.devise}</strong><br><br>"
                                            f"Merci de procéder à la validation finale de cette note de frais dans votre espace client. "
                                            f'<a href="/interface-cl?menu=expense-reports-validation" style="color: #1890ff; text-decoration: underline;">Valider la note de frais</a>'
                                        ),
                                        categorie="CLIENT",
                                        event="NDF validée par commercial",
                                        event_id=updated_ndf.id_ndf
                                    )
                                    print(f"📧 Notification sent to Client {updated_ndf.id_client}")
                                    print(f"   Notification result: {notification_result}")
                                    
                                except Client.DoesNotExist:
                                    print(f"❌ ERROR: Client with ID {updated_ndf.id_client} not found in database")
                                except Exception as notif_error:
                                    print(f"❌ ERROR sending notification: {str(notif_error)}")
                                    import traceback
                                    print(traceback.format_exc())
                            else:
                                print(f"❌ ERROR: No client_id for NDF {updated_ndf.id_ndf} - cannot send notification")
                        else:
                            print(f"ℹ️  Status change does not match commercial validation pattern")
                            print(f"   Checking conditions:")
                            print(f"   - Is EVP → EVC transition: {(old_status.upper() == 'EVP' and new_status.upper() == 'EVC')}")
                            print(f"   - Contains validation keywords: {('valid' in new_status.lower() or 'approv' in new_status.lower() or new_status.upper() == 'EVC')}")
                            print(f"   - Old status not client-related: {'client' not in old_status.lower()}")
                            print(f"   - New status not acceptance: {'accept' not in new_status.lower()}")
                            print(f"   - New status not refusal: {'refus' not in new_status.lower()}")
                        
                        # When client validates NDF
                        # Status codes:
                        # - EVC (En Validation Client) → Accepté/Approuvé/Validé (client final validation)
                        # - Or any status containing accept/approuv/validé coming from EVC
                        client_validated = (
                            # Client validation: EVC → Accepté/Approuvé/Validé
                            (old_status.upper() == 'EVC' and new_status.upper() in ['ACCEPTÉ', 'ACCEPTE', 'APPROUVÉ', 'APPROVE', 'VALIDÉ', 'VALIDE']) or
                            # OR status contains client validation keywords
                            ('accept' in new_status.lower() or 'approuv' in new_status.lower() or 'validé par client' in new_status.lower())
                        )
                        
                        print(f"🔍 Client validation check:")
                        print(f"   - Old status: '{old_status}' (upper: '{old_status.upper()}')")
                        print(f"   - New status: '{new_status}' (upper: '{new_status.upper()}')")
                        print(f"   - Is EVC → ACCEPTÉ/VALIDÉ: {(old_status.upper() == 'EVC' and new_status.upper() in ['ACCEPTÉ', 'ACCEPTE', 'APPROUVÉ', 'APPROVE', 'VALIDÉ', 'VALIDE'])}")
                        print(f"   - Contains accept/approuv keywords: {('accept' in new_status.lower() or 'approuv' in new_status.lower() or 'validé par client' in new_status.lower())}")
                        print(f"   - Client validated: {client_validated}")
                        
                        if client_validated:
                            print(f"✅ Detected CLIENT VALIDATION for NDF {updated_ndf.id_ndf}")
                            print(f"   Consultant ID: {updated_ndf.id_consultan}")
                            print(f"   ESN ID: {updated_ndf.id_esn}")
                            print(f"   Commercial ID: {updated_ndf.id_commercial}")
                            # Notify consultant
                            try:
                                send_notification(
                                    user_id=updated_ndf.id_client,
                                    dest_id=updated_ndf.id_consultan,
                                    message=(
                                        f"Votre note de frais a été validée par le client. "
                                        f"Type: {updated_ndf.type_frais}, Montant: {updated_ndf.montant_ttc} {updated_ndf.devise}."
                                    ),
                                    categorie="CONSULTANT",
                                    event="NDF validée par client",
                                    event_id=updated_ndf.id_ndf
                                )
                                print(f"✅ Client validation notification sent to Consultant {updated_ndf.id_consultan}")
                            except Exception as e:
                                print(f"❌ ERROR sending notification to Consultant: {str(e)}")
                            
                            # Notify ESN (optional)
                            if ENABLE_NDF_CLIENT_VALIDATION_ESN_NOTIFICATION and updated_ndf.id_esn:
                                try:
                                    send_notification(
                                        user_id=updated_ndf.id_client,
                                        dest_id=updated_ndf.id_esn,
                                        message=(
                                            f"La note de frais du consultant {consultant_name} a été validée par le client. "
                                            f"Type: {updated_ndf.type_frais}, Montant: {updated_ndf.montant_ttc} {updated_ndf.devise}."
                                        ),
                                        categorie="ESN",
                                        event="NDF validée par client",
                                        event_id=updated_ndf.id_ndf
                                    )
                                    print(f"✅ Client validation notification sent to ESN {updated_ndf.id_esn}")
                                except Exception as e:
                                    print(f"❌ ERROR sending notification to ESN: {str(e)}")
                            else:
                                print(f"⚠️  ESN notification disabled or no ESN ID for NDF {updated_ndf.id_ndf}")
                            
                            # Notify commercial
                            if updated_ndf.id_commercial:
                                try:
                                    send_notification(
                                        user_id=updated_ndf.id_client,
                                        dest_id=updated_ndf.id_commercial,
                                        message=(
                                            f"La note de frais du consultant {consultant_name} a été validée par le client. "
                                            f"Type: {updated_ndf.type_frais}, Montant: {updated_ndf.montant_ttc} {updated_ndf.devise}."
                                        ),
                                        categorie="COMMERCIAL",
                                        event="NDF validée par client",
                                        event_id=updated_ndf.id_ndf
                                    )
                                    print(f"✅ Client validation notification sent to Commercial {updated_ndf.id_commercial}")
                                except Exception as e:
                                    print(f"❌ ERROR sending notification to Commercial: {str(e)}")
                            else:
                                print(f"⚠️  No Commercial ID for NDF {updated_ndf.id_ndf}")
                        
                        # Generic status change notifications disabled to avoid spamming consultants
                        # Consultants only receive meaningful final status notifications (validé, refusé, remboursé)
                        # Intermediate workflow states (EVP, EVC, etc.) are intentionally silent for consultants
                            
                    except Exception as e:
                        print(f"❌ Error creating notification: {str(e)}")
                
                return JsonResponse({
                    "status": True,
                    "message": "Note de frais mise à jour avec succès",
                    "data": serializer.data
                }, safe=False)
                
            return JsonResponse({"status": False, "errors": serializer.errors}, safe=False, status=400)
            
        except NDF_CONSULTANT.DoesNotExist:
            return JsonResponse({"status": False, "message": "Record not found"}, safe=False, status=404)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
        
    elif request.method == 'DELETE':
        if id <= 0:
            return JsonResponse({"status": False, "message": "ID parameter is required for delete"}, safe=False, status=400)
        try:
            record = NDF_CONSULTANT.objects.get(pk=id)
            
            # Optional: Send notification before deletion
            try:
                consultant = Collaborateur.objects.get(ID_collab=record.id_consultan)
                message = f"Votre note de frais ({record.type_frais}) du {record.jour}/{record.période} a été supprimée"
                
                send_notification(
                    user_id=record.id_esn,
                    dest_id=record.id_consultan,
                    message=message,
                    categorie="Consultant",
                    event="NDF supprimée",
                    event_id=record.id_ndf
                )
            except Exception as e:
                print(f"Error creating deletion notification: {str(e)}")
            
            record.delete()
            return JsonResponse({"status": True, "message": f"Note de frais {id} supprimée."}, safe=False)
        except NDF_CONSULTANT.DoesNotExist:
            return JsonResponse({"status": False, "message": "Record not found"}, safe=False, status=404)
        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
        
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
        
@csrf_exempt
def get_esn_list(request):
    """
    GET /esn-list
    Returns a list of all ESNs.
    """
    if request.method == 'GET':
        esn_objects = ESN.objects.all().order_by('Raison_sociale')
        data = [
            {
                "id": esn.ID_ESN,
                "name": esn.Raison_sociale
            }
            for esn in esn_objects
        ]
        return JsonResponse({"status": True, "data": data}, safe=False)
    return JsonResponse({"status": False, "message": "Method not allowed"}, safe=False, status=405)


@csrf_exempt
def get_client_list(request):
    """
    GET /client-list
    Returns a list of all clients with their data.
    """
    if request.method == 'GET':
        client_objects = Client.objects.all().order_by('raison_sociale')
        data = [
            {
                "id": client.ID_clt,
                "name": client.raison_sociale
            }
            for client in client_objects
        ]
        return JsonResponse({"status": True, "data": data}, safe=False)
    return JsonResponse({"status": False, "message": "Method not allowed"}, safe=False, status=405)

@csrf_exempt
def get_bdc_list(request):
    """
    GET endpoint to retrieve CRA_CONSULTANT records for a specific period.
    
    Query parameters:
    - period: Required filter by period (format: MM_YYYY)
    - consultant_id: Optional filter by consultant ID
    
    Returns CRA_CONSULTANT records that match the specified period with AppelOffre titles.
    """
    if request.method == 'GET':
        try:
            period = request.GET.get('period')
            consultant_id = request.GET.get('consultant_id')
            
            if not period:
                return JsonResponse({
                    "status": False,
                    "message": "period parameter is required (format: MM_YYYY)"
                }, safe=False, status=400)
            
            print(f"DEBUG: period={period}, consultant_id={consultant_id}")
            
            # Validate period format
            try:
                month, year = period.split('_')
                month_int = int(month)
                year_int = int(year)
                print(f"DEBUG: Parsed period - month: {month}, year: {year}")
            except (ValueError, IndexError):
                return JsonResponse({
                    "status": False,
                    "message": "Invalid period format. Use MM_YYYY (e.g., 06_2025)"
                }, safe=False, status=400)
            
            # Start with base query for CRA_CONSULTANT records in the specified period
            cra_query = CRA_CONSULTANT.objects.filter(période=period)
            print(f"DEBUG: Total CRA_CONSULTANT records for period {period}: {cra_query.count()}")
            
            # Filter by consultant_id if provided
            if consultant_id:
                cra_query = cra_query.filter(id_consultan=consultant_id)
                print(f"DEBUG: CRA_CONSULTANT records after consultant filter: {cra_query.count()}")
            
            # If no records found, return empty result
            if not cra_query.exists():
                return JsonResponse({
                    "status": True,
                    "total": 0,
                    "data": [],
                    "message": f"No CRA_CONSULTANT records found for period {period}" + 
                              (f" and consultant {consultant_id}" if consultant_id else "")
                }, safe=False)
            
            # Get all related IDs for efficient querying
            consultant_ids = list(cra_query.values_list('id_consultan', flat=True).distinct())
            bdc_ids = list(cra_query.values_list('id_bdc', flat=True).distinct())
            client_ids = list(cra_query.values_list('id_client', flat=True).distinct())
            esn_ids = list(cra_query.values_list('id_esn', flat=True).distinct())
            
            print(f"DEBUG: Found {len(consultant_ids)} consultants, {len(bdc_ids)} BDCs, {len(client_ids)} clients, {len(esn_ids)} ESNs")
            
            # Bulk fetch related data
            consultants = {c.ID_collab: c for c in Collaborateur.objects.filter(ID_collab__in=consultant_ids)}
            clients = {c.ID_clt: c for c in Client.objects.filter(ID_clt__in=client_ids)}
            esns = {e.ID_ESN: e for e in ESN.objects.filter(ID_ESN__in=esn_ids)}
            
            # **KEY CHANGE: Get AppelOffre titles directly (id_bdc contains AppelOffre IDs)**
            appel_offres = {ao.id: ao for ao in AppelOffre.objects.filter(id__in=bdc_ids)}
            
            print(f"DEBUG: Fetched {len(consultants)} consultants, {len(clients)} clients, {len(esns)} ESNs, {len(appel_offres)} projects")
            
            # Build response data
            data = []
            for cra in cra_query:
                # Basic CRA data
                cra_data = {
                    "id_CRA": cra.id_CRA,
                    "id_bdc": cra.id_bdc,
                    "n_jour": cra.n_jour,
                    "commentaire": cra.commentaire or "",
                    "id_esn": cra.id_esn,
                    "id_client": cra.id_client,
                    "id_consultan": cra.id_consultan,
                    "période": cra.période,
                    "statut": cra.statut
                }
                
                # Add consultant information
                if cra.id_consultan in consultants:
                    consultant = consultants[cra.id_consultan]
                    cra_data["consultant_name"] = f"{consultant.Prenom} {consultant.Nom}"
                    cra_data["consultant_email"] = consultant.email
                else:
                    cra_data["consultant_name"] = f"Consultant ID: {cra.id_consultan}"
                    cra_data["consultant_email"] = ""
                
                # Add client information
                if cra.id_client and cra.id_client in clients:
                    client = clients[cra.id_client]
                    cra_data["client_name"] = client.raison_sociale
                else:
                    cra_data["client_name"] = f"Client ID: {cra.id_client}" if cra.id_client else "No Client"
                
                # Add ESN information
                if cra.id_esn and cra.id_esn in esns:
                    esn = esns[cra.id_esn]
                    cra_data["esn_name"] = esn.Raison_sociale
                else:
                    cra_data["esn_name"] = f"ESN ID: {cra.id_esn}" if cra.id_esn else "No ESN"
                
                # **MAIN FOCUS: Add AppelOffre title (stored in id_bdc field)**
                if cra.id_bdc and cra.id_bdc in appel_offres:
                    appel_offre = appel_offres[cra.id_bdc]
                    cra_data["titre"] = appel_offre.titre  # This is the title you want
                    cra_data["project_description"] = appel_offre.description or ""
                    cra_data["project_id"] = appel_offre.id
                    cra_data["project_profil"] = appel_offre.profil
                    cra_data["project_statut"] = appel_offre.statut
                    
                    # Add additional AppelOffre fields if needed
                    if hasattr(appel_offre, 'date_debut') and appel_offre.date_debut:
                        cra_data["project_date_debut"] = appel_offre.date_debut.isoformat()
                    if hasattr(appel_offre, 'date_limite') and appel_offre.date_limite:
                        cra_data["project_date_limite"] = appel_offre.date_limite.isoformat()
                else:
                    cra_data["titre"] = f"Project ID: {cra.id_bdc}" if cra.id_bdc else "No Project"
                    cra_data["project_description"] = ""
                    cra_data["project_id"] = cra.id_bdc
                    cra_data["project_profil"] = ""
                    cra_data["project_statut"] = ""
                
                data.append(cra_data)
            
            print(f"DEBUG: Final data count: {len(data)}")
            
            return JsonResponse({
                "status": True,
                "total": len(data),
                "period": period,
                "data": data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(f"ERROR: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
    
    return JsonResponse({"status": False, "message": "Method not allowed"}, safe=False, status=405)

@csrf_exempt
def get_cra_by_bdc(request):
    """
    GET endpoint to retrieve all CRA_CONSULTANT records for a specific BDC (Bon de Commande).
    
    Query parameters:
    - bdc_id: Required - The ID of the Bon de Commande
    
    Returns all CRA_CONSULTANT records associated with the specified BDC with calculated amounts.
    """
    if request.method == 'GET':
        try:
            bdc_id = request.GET.get('bdc_id')
            
            if not bdc_id:
                return JsonResponse({
                    "status": False,
                    "message": "bdc_id parameter is required"
                }, safe=False, status=400)
            
            print(f"DEBUG: Fetching CRAs for bdc_id={bdc_id}")
            
            # Get the BDC to fetch TJM
            try:
                bdc = Bondecommande.objects.get(id_bdc=bdc_id)
                tjm = bdc.TJM
                print(f"DEBUG: BDC found - TJM: {tjm}")
            except Bondecommande.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"Bon de Commande with id {bdc_id} not found"
                }, safe=False, status=404)
            
            # Query all CRA records for this BDC
            cra_records = CRA_CONSULTANT.objects.filter(id_bdc=bdc_id).order_by('-période', '-id_CRA')
            
            print(f"DEBUG: Found {cra_records.count()} CRA records")
            
            if not cra_records.exists():
                return JsonResponse({
                    "status": True,
                    "total": 0,
                    "data": [],
                    "message": f"No CRA records found for BDC {bdc_id}"
                }, safe=False)
            
            # Build response data
            data = []
            for cra in cra_records:
                # Calculate amounts
                montant_ht = float(cra.n_jour) * float(tjm)
                montant_ttc = montant_ht * 1.20  # Assuming 20% VAT
                
                cra_data = {
                    "id_cra": cra.id_CRA,
                    "periode": cra.période,
                    "jours_travailles": float(cra.n_jour),
                    "montant_ht": round(montant_ht, 2),
                    "montant_ttc": round(montant_ttc, 2),
                    "statut": cra.statut,
                    "date_soumission": None,  # Add if you have a submission date field
                    "commentaire": cra.commentaire or "",
                    "id_consultant": cra.id_consultan,
                    "id_esn": cra.id_esn,
                    "id_client": cra.id_client
                }
                
                data.append(cra_data)
            
            print(f"DEBUG: Returning {len(data)} CRA records")
            
            return JsonResponse({
                "status": True,
                "total": len(data),
                "bdc_id": bdc_id,
                "tjm": float(tjm),
                "data": data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(f"ERROR in get_cra_by_bdc: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
    
    return JsonResponse({"status": False, "message": "Method not allowed"}, safe=False, status=405)

@csrf_exempt
def get_imputation_by_bdc(request):
    """
    GET endpoint to retrieve all CRA_imputation records for a specific BDC (Bon de Commande).
    Groups imputations by period and shows status tracking at the daily imputation level.
    
    Query parameters:
    - bdc_id: Required - The ID of the Bon de Commande
    
    Returns all CRA_imputation records grouped by period with calculated amounts and status breakdown.
    """
    if request.method == 'GET':
        try:
            bdc_id = request.GET.get('bdc_id')
            
            if not bdc_id:
                return JsonResponse({
                    "status": False,
                    "message": "bdc_id parameter is required"
                }, safe=False, status=400)
            
            print(f"DEBUG: Fetching CRA imputations for bdc_id={bdc_id}")
            
            # Get the BDC to fetch TJM
            try:
                bdc = Bondecommande.objects.get(id_bdc=bdc_id)
                tjm = bdc.TJM
                print(f"DEBUG: BDC found - TJM: {tjm}")
            except Bondecommande.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"Bon de Commande with id {bdc_id} not found"
                }, safe=False, status=404)
            
            # Query all imputation records for this BDC (only type='travail')
            imputations = CRA_imputation.objects.filter(
                id_bdc=bdc_id,
                type='travail'
            ).order_by('-période', 'jour')
            
            print(f"DEBUG: Found {imputations.count()} imputation records")
            
            if not imputations.exists():
                return JsonResponse({
                    "status": True,
                    "total": 0,
                    "data": [],
                    "message": f"No imputation records found for BDC {bdc_id}"
                }, safe=False)
            
            # Group imputations by period
            from collections import defaultdict
            period_groups = defaultdict(list)
            
            for imp in imputations:
                period_groups[imp.période].append(imp)
            
            # Build response data grouped by period
            data = []
            for periode, period_imputations in sorted(period_groups.items(), reverse=True):
                # Calculate total days for this period
                total_jours = sum(float(imp.jour) for imp in period_imputations)
                
                # Calculate amounts
                montant_ht = total_jours * float(tjm)
                montant_ttc = montant_ht * 1.20  # 20% VAT
                
                # Determine overall status for the period
                statuses = [imp.statut for imp in period_imputations]
                status_lower = [s.lower() for s in statuses]
                
                # Determine overall status based on all imputations
                if all(s in ['validé', 'valider'] for s in status_lower):
                    overall_status = 'Validé'
                elif any(s in ['refusé', 'refuser'] for s in status_lower):
                    overall_status = 'Refusé'
                elif any(s in ['annulé', 'annuler', 'cancelled'] for s in status_lower):
                    overall_status = 'Annulé'
                else:
                    # Use the most common status
                    overall_status = statuses[0] if statuses else 'En attente'
                
                # Get status breakdown - count each unique status
                from collections import Counter
                status_counts = Counter(statuses)
                status_breakdown = dict(status_counts)
                
                # Build detailed imputation list for this period
                imputation_details = []
                for imp in period_imputations:
                    imputation_details.append({
                        "id_imputation": imp.id_imputation,
                        "jour": float(imp.jour),
                        "duree": imp.Durée,
                        "statut": imp.statut,
                        "type": imp.type
                    })
                
                period_data = {
                    "periode": periode,
                    "jours_travailles": round(total_jours, 2),
                    "montant_ht": round(montant_ht, 2),
                    "montant_ttc": round(montant_ttc, 2),
                    "statut": overall_status,
                    "status_breakdown": status_counts,
                    "total_imputations": len(period_imputations),
                    "imputations": imputation_details,
                    "date_soumission": None  # Add if needed
                }
                
                data.append(period_data)
            
            print(f"DEBUG: Returning {len(data)} period groups")
            
            return JsonResponse({
                "status": True,
                "total": len(data),
                "bdc_id": bdc_id,
                "tjm": float(tjm),
                "data": data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(f"ERROR in get_imputation_by_bdc: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
    
    return JsonResponse({"status": False, "message": "Method not allowed"}, safe=False, status=405)

@csrf_exempt
def get_ndf_by_responsable(request):
    """
    GET endpoint to retrieve all NDF_CONSULTANT records for consultants 
    managed by a specific responsable/commercial.
    
    Query parameters:
    - responsable_id: ID of the commercial/responsable (required)
    - period: Optional filter by period (format: MM_YYYY)
    - status: Optional filter by NDF status
    - limit: Optional pagination limit (default=100)
    - offset: Optional pagination offset (default=0)
    
    Returns all NDFs submitted by consultants belonging to the same ESN 
    as the specified responsable.
    """
    if request.method == 'GET':
        responsable_id = request.GET.get('responsable_id')
        
        if not responsable_id:
            return JsonResponse({
                "status": False,
                "message": "responsable_id parameter is required"
            }, safe=False, status=400)
        
        try:
            # First, verify the responsable exists and get their ESN
            try:
                responsable = Collaborateur.objects.get(ID_collab=responsable_id)
                esn_id = responsable.ID_ESN
                
                if not esn_id:
                    return JsonResponse({
                        "status": False,
                        "message": "Responsable is not associated with any ESN"
                    }, safe=False, status=400)
                    
                # Get ESN name for response
                try:
                    esn = ESN.objects.get(ID_ESN=esn_id)
                    esn_name = esn.Raison_sociale
                except ESN.DoesNotExist:
                    esn_name = f"ESN ID: {esn_id}"
                
            except Collaborateur.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"Responsable with ID {responsable_id} not found"
                }, safe=False, status=404)
            
            # Get all consultants belonging to the same ESN
            consultants = Collaborateur.objects.filter(
                ID_ESN=esn_id,
                Poste__icontains='consultant'
            )
            consultant_ids = list(consultants.values_list('ID_collab', flat=True))
            
            if not consultant_ids:
                return JsonResponse({
                    "status": True,
                    "responsable": {
                        "id": responsable_id,
                        "name": f"{responsable.Prenom} {responsable.Nom}",
                        "esn": {
                            "id": esn_id,
                            "name": esn_name
                        }
                    },
                    "total": 0,
                    "data": []
                }, safe=False)
            
            # Build query for NDFs by these consultants
            query = NDF_CONSULTANT.objects.filter(id_consultan__in=consultant_ids)
            
            # Apply additional filters if provided
            period = request.GET.get('period')
            if period:
                query = query.filter(période=period)
                
            status = request.GET.get('status')
            if status:
                query = query.filter(statut=status)
            
            # Pagination
            limit = int(request.GET.get('limit', 100))
            offset = int(request.GET.get('offset', 0))
            
            # Count total records before pagination
            total_count = query.count()
            
            # Apply sorting and pagination
            query = query.order_by('-id_ndf')[offset:offset+limit]
            
            # Create lookups for efficient data retrieval
            consultants_dict = {c.ID_collab: c for c in consultants}
            
            # Get client IDs for efficient querying
            client_ids = set(ndf.id_client for ndf in query if ndf.id_client)
            clients = {c.ID_clt: c for c in Client.objects.filter(ID_clt__in=client_ids)}
            
            # Get BDC IDs for efficient querying
            bdc_ids = set(ndf.id_bdc for ndf in query if ndf.id_bdc)
            bdcs = {b.id_bdc: b for b in Bondecommande.objects.filter(id_bdc__in=bdc_ids)}
            candidature_ids = {
                bdc.candidature_id for bdc in bdcs.values() if bdc.candidature_id
            }
            candidatures = {
                c.id_cd: c for c in Candidature.objects.filter(id_cd__in=candidature_ids)
            }
            appel_offre_ids = {
                candidature.AO_id
                for candidature in candidatures.values()
                if candidature.AO_id
            }
            appel_offres = {
                ao.id: ao for ao in AppelOffre.objects.filter(id__in=appel_offre_ids)
            }
            
            # Serialize and enhance data
            enhanced_data = []
            for ndf in query:
                # Base NDF data
                ndf_data = {
                    "id_ndf": ndf.id_ndf,
                    "période": ndf.période,
                    "jour": ndf.jour,
                    "type_frais": ndf.type_frais,
                    "montant_ht": float(ndf.montant_ht),
                    "montant_ttc": float(ndf.montant_ttc),
                    "devise": ndf.devise,
                    "statut": ndf.statut,
                    "description": ndf.description,
                    "justificatif": ndf.justificatif
                }
                
                # Add consultant information
                if ndf.id_consultan in consultants_dict:
                    consultant = consultants_dict[ndf.id_consultan]
                    ndf_data["consultant"] = {
                        "id": consultant.ID_collab,
                        "name": f"{consultant.Prenom} {consultant.Nom}",
                        "email": consultant.email,
                        "position": consultant.Poste
                    }
                else:
                    ndf_data["consultant"] = {
                        "id": ndf.id_consultan,
                        "name": "Unknown Consultant"
                    }
                
                # Add client information
                if ndf.id_client in clients:
                    client = clients[ndf.id_client]
                    ndf_data["client"] = {
                        "id": client.ID_clt,
                        "name": client.raison_sociale
                    }
                else:
                    ndf_data["client"] = {
                        "id": ndf.id_client,
                        "name": "Unknown Client"
                    }
                
                # Add BDC information
                bdc_info = {
                    "id": ndf.id_bdc,
                    "number": "Unknown BDC",
                    "title": None,
                    "appel_offre_titre": None,
                    "project_description": None,
                }

                if ndf.id_bdc in bdcs:
                    bdc = bdcs[ndf.id_bdc]
                    bdc_info["id"] = bdc.id_bdc
                    bdc_info["number"] = bdc.numero_bdc or f"BDC-{bdc.id_bdc}"
                    bdc_info["project_description"] = bdc.description

                    candidature = candidatures.get(bdc.candidature_id)
                    if candidature:
                        appel_offre = appel_offres.get(candidature.AO_id)
                        if appel_offre:
                            bdc_info["title"] = appel_offre.titre
                            bdc_info["appel_offre_titre"] = appel_offre.titre
                            if appel_offre.description:
                                bdc_info["project_description"] = (
                                    appel_offre.description
                                )

                fallback_title = (
                    bdc_info["title"]
                    or bdc_info["project_description"]
                    or bdc_info["number"]
                    or (f"BDC #{bdc_info['id']}" if bdc_info["id"] else None)
                )
                bdc_info["title"] = fallback_title
                bdc_info["appel_offre_titre"] = (
                    bdc_info["appel_offre_titre"] or fallback_title
                )

                ndf_data["bdc"] = bdc_info
                ndf_data["project_name"] = fallback_title or "N/A"
                
                enhanced_data.append(ndf_data)
            
            # Return the data
            return JsonResponse({
                "status": True,
                "responsable": {
                    "id": responsable_id,
                    "name": f"{responsable.Prenom} {responsable.Nom}",
                    "esn": {
                        "id": esn_id,
                        "name": esn_name
                    }
                },
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count,
                "data": enhanced_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)

@csrf_exempt
def get_ndf_by_client(request):
    
    """
    GET endpoint to retrieve all NDF_CONSULTANT records for a specific client.
    
    Query parameters:
    - client_id: ID of the client (required)
    - period: Optional filter by period (format: MM_YYYY)
    - status: Optional filter by NDF status
    - limit: Optional pagination limit (default=100)
    - offset: Optional pagination offset (default=0)
    
    Returns all NDFs submitted by consultants for this client.
    """
    if request.method == 'GET':
        client_id = request.GET.get('client_id')
        
        if not client_id:
            return JsonResponse({
                "status": False,
                "message": "client_id parameter is required"
            }, safe=False, status=400)
        
        try:
            # First, verify the client exists
            try:
                client = Client.objects.get(ID_clt=client_id)
                client_name = client.raison_sociale
            except Client.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"Client with ID {client_id} not found"
                }, safe=False, status=404)
            
            # Build query for NDFs by this client - convert to int for proper filtering
            try:
                client_id_int = int(client_id)
                query = NDF_CONSULTANT.objects.filter(id_client=client_id_int)
                
                # Debug query results
                print(f"Found {query.count()} NDF records for client {client_id}")
                
            except ValueError:
                return JsonResponse({
                    "status": False,
                    "message": "Invalid client_id format"
                }, safe=False, status=400)
            
            # Apply additional filters if provided
            period = request.GET.get('period')
            if period:
                query = query.filter(période=period)
                
            status = request.GET.get('status')
            if status:
                query = query.filter(statut=status)
            
            # Pagination
            limit = int(request.GET.get('limit', 100))
            offset = int(request.GET.get('offset', 0))
            
            # Count total records before pagination
            total_count = query.count()
            
            # Apply sorting and pagination
            query = query.order_by('-id_ndf')[offset:offset+limit]
            
            # Get all records in one go to avoid multiple DB hits
            all_records = list(query)
            
            # Get consultant IDs for efficient querying
            consultant_ids = {ndf.id_consultan for ndf in all_records if ndf.id_consultan}
            consultants = {c.ID_collab: c for c in Collaborateur.objects.filter(ID_collab__in=consultant_ids)}
            
            # Get ESN IDs for efficient querying
            esn_ids = {ndf.id_esn for ndf in all_records if ndf.id_esn}
            esns = {e.ID_ESN: e for e in ESN.objects.filter(ID_ESN__in=esn_ids)}
            
            # Get BDC IDs for efficient querying
            bdc_ids = {ndf.id_bdc for ndf in all_records if ndf.id_bdc}
            bdcs = {b.id_bdc: b for b in Bondecommande.objects.filter(id_bdc__in=bdc_ids)}
            candidature_ids = {
                bdc.candidature_id for bdc in bdcs.values() if bdc.candidature_id
            }
            candidatures = {
                c.id_cd: c for c in Candidature.objects.filter(id_cd__in=candidature_ids)
            }
            appel_offre_ids = {
                candidature.AO_id
                for candidature in candidatures.values()
                if candidature.AO_id
            }
            appel_offres = {
                ao.id: ao for ao in AppelOffre.objects.filter(id__in=appel_offre_ids)
            }
            
            # Serialize and enhance data
            enhanced_data = []
            for ndf in all_records:
                # Base NDF data
                ndf_data = {
                    "id_ndf": ndf.id_ndf,
                    "période": ndf.période,
                    "jour": ndf.jour,
                    "type_frais": ndf.type_frais,
                    "montant_ht": float(ndf.montant_ht),
                    "montant_ttc": float(ndf.montant_ttc),
                    "devise": ndf.devise,
                    "statut": ndf.statut,
                    "description": ndf.description,
                    "justificatif": ndf.justificatif
                }
                
                # Add consultant information
                if ndf.id_consultan and ndf.id_consultan in consultants:
                    consultant = consultants[ndf.id_consultan]
                    ndf_data["consultant"] = {
                        "id": consultant.ID_collab,
                        "name": f"{consultant.Prenom} {consultant.Nom}",
                        "email": consultant.email,
                        "position": consultant.Poste
                    }
                else:
                    ndf_data["consultant"] = {
                        "id": ndf.id_consultan,
                        "name": "Unknown Consultant"
                    }
                
                # Add ESN information
                if ndf.id_esn and ndf.id_esn in esns:
                    esn = esns[ndf.id_esn]
                    ndf_data["esn"] = {
                        "id": esn.ID_ESN,
                        "name": esn.Raison_sociale
                    }
                else:
                    ndf_data["esn"] = {
                        "id": ndf.id_esn,
                        "name": "Unknown ESN"
                    }
                
                # Add BDC information
                bdc_info = {
                    "id": ndf.id_bdc,
                    "number": "Unknown BDC",
                    "title": None,
                    "appel_offre_titre": None,
                    "project_description": None,
                }

                if ndf.id_bdc and ndf.id_bdc in bdcs:
                    bdc = bdcs[ndf.id_bdc]
                    bdc_info["id"] = bdc.id_bdc
                    bdc_info["number"] = bdc.numero_bdc or f"BDC-{bdc.id_bdc}"
                    bdc_info["project_description"] = bdc.description

                    candidature = candidatures.get(bdc.candidature_id)
                    if candidature:
                        appel_offre = appel_offres.get(candidature.AO_id)
                        if appel_offre:
                            bdc_info["title"] = appel_offre.titre
                            bdc_info["appel_offre_titre"] = appel_offre.titre
                            if appel_offre.description:
                                bdc_info["project_description"] = (
                                    appel_offre.description
                                )

                fallback_title = (
                    bdc_info["title"]
                    or bdc_info["project_description"]
                    or bdc_info["number"]
                    or (f"BDC #{bdc_info['id']}" if bdc_info["id"] else None)
                )
                bdc_info["title"] = fallback_title
                bdc_info["appel_offre_titre"] = (
                    bdc_info["appel_offre_titre"] or fallback_title
                )

                ndf_data["bdc"] = bdc_info
                ndf_data["project_name"] = fallback_title or "N/A"
                
                enhanced_data.append(ndf_data)
            
            # Return the data
            return JsonResponse({
                "status": True,
                "client": {
                    "id": client_id,
                    "name": client_name
                },
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count,
                "data": enhanced_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            traceback_str = traceback.format_exc()
            print(traceback_str)
            return JsonResponse({
                "status": False,
                "message": f"Error: {str(e)}",
                "traceback": traceback_str
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)
    """
    GET endpoint to retrieve all NDF_CONSULTANT records for a specific client.
    
    Query parameters:
    - client_id: ID of the client (required)
    - period: Optional filter by period (format: MM_YYYY)
    - status: Optional filter by NDF status
    - limit: Optional pagination limit (default=100)
    - offset: Optional pagination offset (default=0)
    
    Returns all NDFs submitted by consultants for this client.
    """
    if request.method == 'GET':
        client_id = request.GET.get('client_id')
        
        if not client_id:
            return JsonResponse({
                "status": False,
                "message": "client_id parameter is required"
            }, safe=False, status=400)
        
        try:
            # First, verify the client exists
            try:
                client = Client.objects.get(ID_clt=client_id)
                client_name = client.raison_sociale
            except Client.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"Client with ID {client_id} not found"
                }, safe=False, status=404)
            
            # Build query for NDFs by this client
            query = NDF_CONSULTANT.objects.filter(id_client=client_id)
            
            # Apply additional filters if provided
            period = request.GET.get('period')
            if period:
                query = query.filter(période=period)
                
            status = request.GET.get('status')
            if status:
                query = query.filter(statut=status)
            
            # Pagination
            limit = int(request.GET.get('limit', 100))
            offset = int(request.GET.get('offset', 0))
            
            # Count total records before pagination
            total_count = query.count()
            
            # Apply sorting and pagination
            query = query.order_by('-id_ndf')[offset:offset+limit]
            
            # Get consultant IDs for efficient querying
            consultant_ids = set(ndf.id_consultan for ndf in query if ndf.id_consultan)
            consultants = {c.ID_collab: c for c in Collaborateur.objects.filter(ID_collab__in=consultant_ids)}
            
            # Get ESN IDs for efficient querying
            esn_ids = set(ndf.id_esn for ndf in query if ndf.id_esn)
            esns = {e.ID_ESN: e for e in ESN.objects.filter(ID_ESN__in=esn_ids)}
            
            # Get BDC IDs for efficient querying
            bdc_ids = set(ndf.id_bdc for ndf in query if ndf.id_bdc)
            bdcs = {b.id_bdc: b for b in Bondecommande.objects.filter(id_bdc__in=bdc_ids)}
            
            # Serialize and enhance data
            enhanced_data = []
            for ndf in query:
                # Base NDF data
                ndf_data = {
                    "id_ndf": ndf.id_ndf,
                    "période": ndf.période,
                    "jour": ndf.jour,
                    "type_frais": ndf.type_frais,
                    "montant_ht": float(ndf.montant_ht),
                    "montant_ttc": float(ndf.montant_ttc),
                    "devise": ndf.devise,
                    "statut": ndf.statut,
                    "description": ndf.description,
                    "justificatif": ndf.justificatif
                }
                
                # Add consultant information
                if ndf.id_consultan in consultants:
                    consultant = consultants[ndf.id_consultan]
                    ndf_data["consultant"] = {
                        "id": consultant.ID_collab,
                        "name": f"{consultant.Prenom} {consultant.Nom}",
                        "email": consultant.email,
                        "position": consultant.Poste
                    }
                else:
                    ndf_data["consultant"] = {
                        "id": ndf.id_consultan,
                        "name": "Unknown Consultant"
                    }
                
                # Add ESN information
                if ndf.id_esn in esns:
                    esn = esns[ndf.id_esn]
                    ndf_data["esn"] = {
                        "id": esn.ID_ESN,
                        "name": esn.Raison_sociale
                    }
                else:
                    ndf_data["esn"] = {
                        "id": ndf.id_esn,
                        "name": "Unknown ESN"
                    }
                
                # Add BDC information
                if ndf.id_bdc in bdcs:
                    bdc = bdcs[ndf.id_bdc]
                    ndf_data["bdc"] = {
                        "id": bdc.id_bdc,
                        "number": bdc.numero_bdc
                    }
                else:
                    ndf_data["bdc"] = {
                        "id": ndf.id_bdc,
                        "number": "Unknown BDC"
                    }
                
                enhanced_data.append(ndf_data)
            
            # Return the data
            return JsonResponse({
                "status": True,
                "client": {
                    "id": client_id,
                    "name": client_name
                },
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count,
                "data": enhanced_data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
            
    return JsonResponse({
        "status": False,
        "message": "Method not allowed"
    }, safe=False, status=405)


def get_short_code(name):
    """
    Extract short code from name (first 3 letters uppercase)
    Example: "AXA Insurance" -> "AXA", "Johnson Services" -> "JOH"
    """
    if not name:
        return "XXX"
    clean_name = name.strip().upper()[:3]
    return clean_name if len(clean_name) >= 3 else clean_name.ljust(3, 'X')


def generate_invoice_numero(facture_type, client_id, esn_id, bdc_id, periode, id_facture=None):
    """
    Generate invoice number based on pattern using id_facture for uniqueness:
    - FC (ESN→MITC): FC_$ClientCode_$ESNCode_$Year_$Periode_$ID
    - FM (MITC→Client): FM_$ClientCode_$ESNCode_$Year_$Periode_$ID
    - NDF: NDF_$ClientCode_$ESNCode_$Year_$Periode_$ID
    
    Example:
    - FC: FC_AXA_Jys_25_10_001
    - FM: FM_AXA_Jys_25_10_001
    - NDF: NDF_AXA_Jys_25_10_001
    
    Using id_facture ensures each invoice has a unique number.
    """
    try:
        # Get client and ESN info
        client = Client.objects.get(ID_clt=client_id)
        esn = ESN.objects.get(ID_ESN=esn_id)
        
        client_code = get_short_code(client.raison_sociale)
        esn_code = get_short_code(esn.Raison_sociale)
        
        # Extract year from periode (MM_YYYY format) - get last 2 digits of year
        if periode and '_' in str(periode):
            parts = str(periode).split('_')
            year = parts[-1][-2:] if len(parts) > 1 else "00"
            month = parts[0] if len(parts) > 0 else "00"
        else:
            from datetime import datetime
            year = datetime.now().strftime('%y')
            month = datetime.now().strftime('%m')
        
        # Define prefix based on facture type
        if facture_type and "ESN_TO_MITC" in facture_type.upper():
            prefix = "FC"
        elif facture_type and "MITC_TO_CLIENT" in facture_type.upper():
            prefix = "FM"
        elif facture_type and "NDF" in facture_type.upper():
            prefix = "NDF"
        else:
            prefix = "FAC"
        
        # Use id_facture for unique increment instead of counting
        # This ensures each invoice gets a unique number
        if id_facture:
            increment = str(id_facture).zfill(3)
        else:
            # Fallback: count if id_facture not provided (shouldn't happen)
            count = Facture.objects.filter(
                id_client=client_id,
                id_esn=esn_id,
                type_facture__contains=prefix,
                periode=periode
            ).count()
            increment = str(count + 1).zfill(3)
        
        # Format: PREFIX_ClientCode_ESNCode_Year_Month_Increment
        numero = f"{prefix}_{client_code}_{esn_code}_{year}_{month}_{increment}"
        
        return numero
        
    except (Client.DoesNotExist, ESN.DoesNotExist) as e:
        # Fallback to simple numbering
        if id_facture:
            return f"FAC_{id_facture}"
        from datetime import datetime
        timestamp = datetime.now().strftime('%y%m%d%H%M%S')
        return f"FAC_{timestamp}"
    except Exception as e:
        print(f"Error generating invoice numero: {str(e)}")
        if id_facture:
            return f"FAC_{id_facture}"
        from datetime import datetime
        timestamp = datetime.now().strftime('%y%m%d%H%M%S')
        return f"FAC_{timestamp}"


def generate_bdc_numero(client_id, esn_id):
    """
    Generate BDC number with pattern: BDC_$ClientCode_$ESNCode_$Year$Increment
    Example: BDC_AXA_Jys_25001
    """
    try:
        from datetime import datetime
        client = Client.objects.get(ID_clt=client_id)
        esn = ESN.objects.get(ID_ESN=esn_id)
        
        client_code = get_short_code(client.raison_sociale)
        esn_code = get_short_code(esn.Raison_sociale)
        year = datetime.now().strftime('%y')
        
        # Count BDCs for this client-esn combo in current year
        current_year_start = datetime.now().replace(month=1, day=1)
        count = Bondecommande.objects.filter(
            candidature_id__in=[c.id_cd for c in Candidature.objects.filter(esn_id=esn_id)],
        ).filter(date_creation__gte=current_year_start).count()
        
        increment = str(count + 1).zfill(3)
        numero = f"BDC_{client_code}_{esn_code}_{year}{increment}"
        
        return numero
    except (Client.DoesNotExist, ESN.DoesNotExist) as e:
        from datetime import datetime
        timestamp = datetime.now().strftime('%y%m%d%H%M%S')
        return f"BDC_{timestamp}"
    except Exception as e:
        print(f"Error generating BDC numero: {str(e)}")
        from datetime import datetime
        timestamp = datetime.now().strftime('%y%m%d%H%M%S')
        return f"BDC_{timestamp}"


@csrf_exempt
def facture_view(request, facture_id=None):  # Add facture_id parameter with default None
    if request.method == 'GET':
        # Use facture_id from URL if provided, otherwise check query parameters
        id_facture = facture_id or request.GET.get('id_facture')
        id_esn = request.GET.get('id_esn')
        id_client = request.GET.get('id_client')

        def enrich_invoice_payload(payload):
            if not payload:
                return payload

            is_list = isinstance(payload, list)
            data_list = payload if is_list else [payload]
            
            print(f"\n{'*'*80}")
            print(f"ENRICH STARTING: Processing {len(data_list)} invoices")
            for idx, inv in enumerate(data_list[:3]):  # Print first 3
                print(f"  Invoice {idx+1}: id={inv.get('id_facture')}, type={inv.get('type_facture')}, HT={inv.get('montant_ht')}, TTC={inv.get('montant_ttc')}, periode={inv.get('periode')}, bdc={inv.get('bdc_id')}")
            print(f"{'*'*80}\n")

            bdc_ids = {
                item.get('bdc_id') for item in data_list if item.get('bdc_id')
            }

            bdcs = {
                bdc.id_bdc: bdc for bdc in Bondecommande.objects.filter(id_bdc__in=bdc_ids)
            } if bdc_ids else {}

            candidature_ids = {
                bdc.candidature_id for bdc in bdcs.values() if bdc.candidature_id
            }
            candidatures = {
                candidature.id_cd: candidature
                for candidature in Candidature.objects.filter(id_cd__in=candidature_ids)
            } if candidature_ids else {}

            appel_offre_ids = {
                candidature.AO_id
                for candidature in candidatures.values()
                if candidature.AO_id
            }
            appel_offres = {
                ao.id: ao for ao in AppelOffre.objects.filter(id__in=appel_offre_ids)
            } if appel_offre_ids else {}

            enriched = []
            for item in data_list:
                invoice = dict(item)
                bdc_id = invoice.get('bdc_id')
                bdc_info = {
                    'id': bdc_id,
                    'number': None,
                    'title': None,
                    'appel_offre_titre': None,
                    'project_description': None,
                }
                
                # Initialize TJM and jours_travailles
                invoice['tjm'] = None
                invoice['jours_travailles'] = None
                invoice['consultant_id'] = None
                invoice['consultant_name'] = None
                invoice['commission_percentage'] = None
                invoice['commission_amount'] = None

                if bdc_id and bdc_id in bdcs:
                    bdc = bdcs[bdc_id]
                    bdc_info['id'] = bdc.id_bdc
                    bdc_info['number'] = bdc.numero_bdc or f"BDC-{bdc.id_bdc}"
                    bdc_info['project_description'] = bdc.description
                    
                    # Get TJM from BDC
                    if bdc.TJM:
                        invoice['tjm'] = float(bdc.TJM)
                    
                    # Get commission from BDC (stored as "percentage|amount")
                    if bdc.benefit:
                        try:
                            if '|' in bdc.benefit:
                                parts = bdc.benefit.split('|')
                                invoice['commission_percentage'] = float(parts[0])
                                invoice['commission_amount'] = float(parts[1])
                            else:
                                # Old format: just the amount
                                invoice['commission_amount'] = float(bdc.benefit)
                                # Calculate percentage if we have montant_total
                                if bdc.montant_total and float(bdc.montant_total) > 0:
                                    invoice['commission_percentage'] = (float(bdc.benefit) / float(bdc.montant_total)) * 100
                        except (ValueError, IndexError) as e:
                            print(f"Warning: Could not parse commission from BDC {bdc.id_bdc}: {str(e)}")

                    candidature = candidatures.get(bdc.candidature_id)
                    if candidature:
                        # Get consultant info
                        invoice['consultant_id'] = candidature.id_consultant
                        try:
                            consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
                            invoice['consultant_name'] = f"{consultant.Prenom} {consultant.Nom}"
                        except Collaborateur.DoesNotExist:
                            pass
                        
                        # Calculate jours_travailles from CRA imputations for this period
                        periode = invoice.get('periode')
                        bdc_id = invoice.get('bdc_id')
                        if periode and candidature.id_consultant:
                            try:
                                # Count only work days (type='travail') for THIS SPECIFIC PERIOD AND BDC
                                filters = {
                                    'id_consultan': candidature.id_consultant,
                                    'période': periode,
                                    'type': 'travail'
                                }
                                
                                # Add BDC filter if available to be more specific
                                if bdc_id:
                                    filters['id_bdc'] = bdc_id
                                
                                work_imputations = CRA_imputation.objects.filter(**filters)
                                # Each imputation entry represents 1 work day
                                # Durée field contains the duration (usually "1" for full day)
                                # Count the number of entries, not sum of jour (jour is day-of-month, not days worked)
                                total_work_days = work_imputations.count()
                                invoice['jours_travailles'] = round(total_work_days, 2)
                                
                                print(f"DEBUG - Invoice {invoice.get('id_facture')}: consultant={candidature.id_consultant}, periode={periode}, bdc={bdc_id}, work_days={total_work_days}, count={work_imputations.count()}")
                            except Exception as e:
                                print(f"Warning: Could not calculate jours_travailles for invoice {invoice.get('id_facture')}: {str(e)}")

                    candidature = candidatures.get(bdc.candidature_id)
                    if candidature:
                        appel_offre = appel_offres.get(candidature.AO_id)
                        if appel_offre:
                            bdc_info['title'] = appel_offre.titre
                            bdc_info['appel_offre_titre'] = appel_offre.titre
                            if appel_offre.description:
                                bdc_info['project_description'] = appel_offre.description

                if not bdc_info['number'] and bdc_info['id']:
                    bdc_info['number'] = f"BDC-{bdc_info['id']}"

                fallback_title = (
                    bdc_info['title']
                    or bdc_info['project_description']
                    or bdc_info['number']
                    or (f"BDC #{bdc_info['id']}" if bdc_info['id'] else None)
                )

                bdc_info['title'] = fallback_title
                bdc_info['appel_offre_titre'] = bdc_info['appel_offre_titre'] or fallback_title

                invoice['bdc'] = bdc_info
                invoice['project_name'] = invoice.get('project_name') or fallback_title or 'N/A'
                if not invoice.get('appel_offre_titre'):
                    invoice['appel_offre_titre'] = bdc_info['appel_offre_titre']
                if not invoice.get('project_description'):
                    invoice['project_description'] = bdc_info['project_description']
                
                # Auto-calculate montant for NDF invoices if it's 0 or missing
                if invoice.get('type_facture') and 'NDF' in invoice.get('type_facture', '').upper():
                    montant_ht = float(invoice.get('montant_ht', 0))
                    montant_ttc = float(invoice.get('montant_ttc', 0))
                    
                    print(f"DEBUG NDF - Invoice {invoice.get('id_facture')}: type={invoice.get('type_facture')}, HT={montant_ht}, TTC={montant_ttc}")
                    
                    if montant_ht == 0 or montant_ttc == 0:
                        try:
                            # Get consultant_id from BDC -> Candidature
                            bdc_id = invoice.get('bdc_id')
                            periode = invoice.get('periode')
                            
                            print(f"DEBUG NDF - Looking for NDF records: bdc_id={bdc_id}, periode={periode}")
                            
                            if bdc_id and periode:
                                # Try to get BDC from prefetched or database
                                bdc = None
                                candidature = None
                                
                                if bdc_id in bdcs:
                                    bdc = bdcs[bdc_id]
                                    candidature = candidatures.get(bdc.candidature_id)
                                else:
                                    # Fetch directly if not in prefetched data
                                    try:
                                        bdc = Bondecommande.objects.get(id_bdc=bdc_id)
                                        candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                                    except:
                                        pass
                                
                                if candidature and candidature.id_consultant:
                                    consultant_id = candidature.id_consultant
                                    
                                    print(f"DEBUG NDF - Consultant ID: {consultant_id}, searching NDF records...")
                                    
                                    # Calculate total from NDF_CONSULTANT records
                                    ndf_records = NDF_CONSULTANT.objects.filter(
                                        id_consultan=consultant_id,
                                        période=periode
                                    )
                                    
                                    print(f"DEBUG NDF - Found {ndf_records.count()} NDF records")
                                    
                                    # Debug: print each NDF record
                                    for idx, ndf in enumerate(ndf_records):
                                        print(f"  NDF {idx+1}: id={ndf.id_ndf}, montant_ht={ndf.montant_ht}, montant_ttc={ndf.montant_ttc}, type={ndf.type_frais}, jour={ndf.jour}")
                                    
                                    # Calculate total - use TTC if HT is 0 (fallback for records with missing HT)
                                    total_ndf_ht = 0
                                    total_ndf_ttc = 0
                                    
                                    for ndf in ndf_records:
                                        ht = float(ndf.montant_ht or 0)
                                        ttc = float(ndf.montant_ttc or 0)
                                        
                                        if ht > 0:
                                            # Use HT if available
                                            total_ndf_ht += ht
                                            total_ndf_ttc += ttc if ttc > 0 else ht * 1.20
                                        elif ttc > 0:
                                            # Calculate HT from TTC if HT is 0 but TTC exists
                                            calculated_ht = round(ttc / 1.20, 2)
                                            total_ndf_ht += calculated_ht
                                            total_ndf_ttc += ttc
                                    
                                    print(f"DEBUG NDF - Total calculated: HT={total_ndf_ht}€, TTC={total_ndf_ttc}€")
                                    
                                    if total_ndf_ht > 0 or total_ndf_ttc > 0:
                                        # Use calculated totals
                                        final_ht = total_ndf_ht
                                        final_ttc = total_ndf_ttc if total_ndf_ttc > 0 else round(total_ndf_ht * 1.20, 2)
                                        
                                        invoice['montant_ht'] = str(final_ht)
                                        invoice['montant_ttc'] = str(final_ttc)
                                        print(f"✅ DEBUG - Recalculated NDF invoice {invoice.get('id_facture')}: HT={final_ht}€, TTC={final_ttc}€")

                                    else:
                                        print(f"⚠️ DEBUG - No NDF amount found for invoice {invoice.get('id_facture')}")
                                else:
                                    print(f"⚠️ DEBUG - Could not find candidature or consultant_id for BDC {bdc_id}")
                        except Exception as e:
                            print(f"❌ ERROR: Could not recalculate NDF amount for invoice {invoice.get('id_facture')}: {str(e)}")
                            import traceback
                            traceback.print_exc()
                
                # Generate numero_facture for display - ALWAYS regenerate to ensure correct format
                try:
                    numero = generate_invoice_numero(
                        facture_type=invoice.get('type_facture'),
                        client_id=invoice.get('id_client'),
                        esn_id=invoice.get('id_esn'),
                        bdc_id=invoice.get('bdc_id'),
                        periode=invoice.get('periode'),
                        id_facture=invoice.get('id_facture')
                    )
                    invoice['numero_facture'] = numero
                except Exception as e:
                    print(f"Warning: Could not generate invoice numero: {str(e)}")
                    invoice['numero_facture'] = f"FAC-{invoice.get('id_facture', 'N/A')}"

                enriched.append(invoice)

            return enriched if is_list else enriched[0]
        
        if id_facture:
            # Get specific facture by id_facture
            try:
                facture = Facture.objects.get(id_facture=id_facture)
                serializer = FactureSerializer(facture)
                enriched_data = enrich_invoice_payload(serializer.data)
                return JsonResponse({'success': True, 'data': enriched_data}, status=200)
            except Facture.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Facture not found'}, status=404)
        
        elif id_esn:
            # Get factures by id_esn
            try:
                factures = Facture.objects.filter(id_esn=id_esn)
                if not factures.exists():
                    return JsonResponse({'success': False, 'message': 'No factures found for this ESN'}, status=404)
                serializer = FactureSerializer(factures, many=True)
                enriched_data = enrich_invoice_payload(serializer.data)
                return JsonResponse({'success': True, 'data': enriched_data}, status=200)
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)}, status=500)
        
        elif id_client:
            # Get factures by id_client
            try:
                factures = Facture.objects.filter(id_client=id_client)
                if not factures.exists():
                    return JsonResponse({'success': True, 'message': 'No factures found for this client'}, status=404)
                serializer = FactureSerializer(factures, many=True)
                print(f"\n{'='*80}")
                print(f"CALLING ENRICH for CLIENT {id_client}: Found {len(serializer.data)} invoices")
                print(f"{'='*80}\n")
                enriched_data = enrich_invoice_payload(serializer.data)
                print(f"\n{'='*80}")
                print(f"ENRICH COMPLETE: Returning {len(enriched_data)} invoices")
                print(f"{'='*80}\n")
                return JsonResponse({'success': True, 'data': enriched_data}, status=200)
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)}, status=500)
        
        else:
            # Get all factures
            factures = Facture.objects.all()
            serializer = FactureSerializer(factures, many=True)
            enriched_data = enrich_invoice_payload(serializer.data)
            return JsonResponse({'success': True, 'data': enriched_data}, status=200)
    
    elif request.method == 'PUT':
        try:
            # Handle request data
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST.dict()
            
            # Use facture_id from URL if provided, otherwise from request data
            target_facture_id = facture_id or data.get('id_facture')
            
            if not target_facture_id:
                return JsonResponse({'success': False, 'message': 'id_facture is required'}, status=400)
            
            facture = Facture.objects.get(id_facture=target_facture_id)
            
            # Auto-collect id_esn and id_client if missing but bdc_id is provided
            if 'bdc_id' in data:
                need_esn = 'id_esn' not in data or not data.get('id_esn')
                need_client = 'id_client' not in data or not data.get('id_client')
                
                if need_esn or need_client:
                    try:
                        bdc = Bondecommande.objects.get(id_bdc=data['bdc_id'])
                        candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                        appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                        
                        if need_esn:
                            data['id_esn'] = candidature.esn_id
                        
                        if need_client:
                            data['id_client'] = appel_offre.client_id
                            
                    except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, AppelOffre.DoesNotExist) as e:
                        return JsonResponse({'success': False, 'message': f'Error auto-collecting data: {str(e)}'}, status=404)
            
            # Auto-recalculate montant_ttc - always override any user-provided value
            if 'montant_ht' in data:
                montant_ht = float(data['montant_ht'])
                taux_tva = float(data.get('taux_tva', facture.taux_tva))
                # Calculate and round to 2 decimal places to fit within 10 digits
                calculated_ttc = round(montant_ht * (1 + taux_tva / 100), 2)
                data['montant_ttc'] = calculated_ttc
            elif 'taux_tva' in data:
                # If only taux_tva is being updated, recalculate with existing montant_ht
                montant_ht = float(facture.montant_ht)
                taux_tva = float(data['taux_tva'])
                calculated_ttc = round(montant_ht * (1 + taux_tva / 100), 2)
                data['montant_ttc'] = calculated_ttc
            
            # Track old status for notification comparison
            old_status = facture.statut
            old_attachment = facture.attachment
            
            serializer = FactureSerializer(facture, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                
                # Send notifications for status changes and document uploads
                new_status = serializer.validated_data.get('statut', old_status)
                new_attachment = serializer.validated_data.get('attachment', old_attachment)
                
                # Get ESN and Client information for notifications
                try:
                    esn = ESN.objects.get(ID_ESN=facture.id_esn)
                    client = Client.objects.get(ID_clt=facture.id_client)

                    # Get project/BDC information
                    project_name = "N/A"
                    commercial_id = None
                    try:
                        bdc = Bondecommande.objects.get(id_bdc=facture.bdc_id)
                        candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                        commercial_id = candidature.commercial_id
                        appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                        project_name = appel_offre.titre
                    except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, AppelOffre.DoesNotExist):
                        project_name = f"BDC-{facture.bdc_id}"
                        commercial_id = None

                    def notify_admins(origin_user_id, message, event_code):
                        for admin in Admin.objects.all():
                            send_notification(
                                user_id=origin_user_id,
                                dest_id=admin.ID_Admin,
                                message=message,
                                categorie="ADMIN",
                                event=event_code,
                                event_id=facture.id_facture,
                            )

                    # Notification when client uploads payment proof (attachment added while in "En attente" status)
                    if new_attachment and new_attachment != old_attachment and old_status == "En attente":
                        admin_message = (
                            f"Le client {client.raison_sociale} a téléchargé un justificatif de paiement pour la facture FAC-{facture.id_facture}."
                        )
                        notify_admins(client.ID_clt, admin_message, "Justificatif de paiement client")

                        # DO NOT notify ESN when client uploads payment proof
                        # ESN will be notified only when admin actually pays them (Clôturée status)

                        # Commercial/responsable payment notifications intentionally disabled

                    # Notification when status changes to "Acceptée"
                    if new_status == "Acceptée" and old_status != "Acceptée":
                        # Get project name and consultant info for better notification
                        try:
                            bdc = Bondecommande.objects.get(id_bdc=facture.bdc_id)
                            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                            ao = AppelOffre.objects.get(id=candidature.AO_id)
                            project_name = ao.titre
                            
                            # Get consultant name
                            consultant_name = "consultant"
                            if candidature.id_consultant:
                                try:
                                    consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
                                    consultant_name = f"{consultant.Prenom} {consultant.Nom}"
                                except Collaborateur.DoesNotExist:
                                    pass
                                    
                            # Check if invoice is for NDF or CRA
                            invoice_type = "CRA"
                            if facture.type_facture and "NDF" in facture.type_facture.upper():
                                invoice_type = "NDF"
                        except Exception:
                            project_name = "projet"
                            consultant_name = "consultant"
                            invoice_type = "CRA"
                        
                        # DO NOT notify ESN when invoice is accepted - only notify when paid (Clôturée)
                        # ESN will be notified only when admin actually pays them
                        
                        # Notification to Client that invoice was accepted by admin
                        send_notification(
                            user_id=None,
                            dest_id=client.ID_clt,
                            message=(
                                f"La facture <strong>FAC-{facture.id_facture}</strong> du projet <strong>{project_name}</strong> "
                                f"pour la période <strong>{facture.periode}</strong> du collaborateur <strong>{consultant_name}</strong> "
                                f"({invoice_type}) a été validée par l'administrateur. "
                                f"Montant à payer: <strong>{facture.montant_ttc}€ TTC</strong>. "
                                f"Veuillez procéder au paiement. "
                                f'<a href="/interface-cl?menu=invoices" class="notification-link">Voir les factures</a>'
                            ),
                            categorie="CLIENT",
                            event="Facture à payer",
                            event_id=facture.id_facture,
                        )

                        if commercial_id:
                            send_notification(
                                user_id=None,
                                dest_id=commercial_id,
                                message=(
                                    f"La facture FAC-{facture.id_facture} liée à votre dossier a été acceptée. Vous pouvez suivre le paiement côté client."),
                                categorie="COMMERCIAL",
                                event="Facture acceptée",
                                event_id=facture.id_facture,
                            )

                    # Notification when status changes to "Rejetée"
                    if new_status == "Rejetée" and old_status != "Rejetée":
                        send_notification(
                            user_id=None,
                            dest_id=esn.ID_ESN,
                            message=(
                                f"Votre facture FAC-{facture.id_facture} a été rejetée. Veuillez vérifier les informations et soumettre un nouveau document."
                            ),
                            categorie="ESN",
                            event="Facture rejetée",
                            event_id=facture.id_facture,
                        )

                        send_notification(
                            user_id=None,
                            dest_id=client.ID_clt,
                            message=f"La facture FAC-{facture.id_facture} a été rejetée.",
                            categorie="CLIENT",
                            event="Facture rejetée",
                            event_id=facture.id_facture,
                        )

                        notify_admins(None, f"La facture FAC-{facture.id_facture} a été rejetée.", "Facture rejetée")

                        if commercial_id:
                            send_notification(
                                user_id=None,
                                dest_id=commercial_id,
                                message=(
                                    f"La facture FAC-{facture.id_facture} a été rejetée. Merci d'accompagner l'ESN pour une nouvelle soumission."),
                                categorie="COMMERCIAL",
                                event="Facture rejetée",
                                event_id=facture.id_facture,
                            )

                    # Notification when status changes to "Payée"
                    if new_status == "Payée" and old_status != "Payée":
                        # Get project name and consultant info for better notification
                        try:
                            bdc = Bondecommande.objects.get(id_bdc=facture.bdc_id)
                            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                            ao = AppelOffre.objects.get(id=candidature.AO_id)
                            project_name = ao.titre
                            
                            # Get consultant name
                            consultant_name = "consultant"
                            if candidature.id_consultant:
                                try:
                                    consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
                                    consultant_name = f"{consultant.Prenom} {consultant.Nom}"
                                except Collaborateur.DoesNotExist:
                                    pass
                        except Exception:
                            project_name = "projet"
                            consultant_name = "consultant"
                        
                        # DO NOT notify ESN when client pays - only notify when admin pays ESN (Clôturée)
                        # ESN will be notified only when they actually receive payment from admin
                        
                        # Notification to Admin when client pays
                        notify_admins(
                            client.ID_clt, 
                            f"Le client <strong>{client.raison_sociale}</strong> a marqué la facture <strong>FAC-{facture.id_facture}</strong> "
                            f"du projet <strong>{project_name}</strong> pour la période <strong>{facture.periode}</strong> "
                            f"comme payée (Montant: {facture.montant_ttc}€). "
                            f"Veuillez procéder au paiement de l'ESN <strong>{esn.Raison_sociale}</strong>. "
                            f'<a href="/interface-ad?menu=invoices" style="color: #1890ff; text-decoration: underline;">Gérer les factures</a>',
                            "Facture payée par client"
                        )

                        # Commercial/responsable payment notifications intentionally disabled

                    # Notification when admin confirme le paiement ESN (statut "Payée" ou "Clôturée" ou justificatif ajouté)
                    payment_statuses = {"Payée", "Clôturée"}
                    attachment_changed = bool(new_attachment) and new_attachment != old_attachment
                    status_triggers_payment = new_status in payment_statuses and old_status != new_status
                    attachment_triggers_payment = new_status in payment_statuses and attachment_changed

                    if status_triggers_payment or attachment_triggers_payment:
                        has_payment_proof = bool(new_attachment)
                        # Get project name and consultant info for better notification
                        payment_project_name = "N/A"
                        payment_invoice_type = "CRA"
                        try:
                            bdc = Bondecommande.objects.get(id_bdc=facture.bdc_id)
                            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                            ao = AppelOffre.objects.get(id=candidature.AO_id)
                            payment_project_name = ao.titre
                            
                            # Check if invoice is for NDF or CRA
                            if facture.type_facture and "NDF" in facture.type_facture.upper():
                                payment_invoice_type = "NDF"
                        except Exception as e:
                            print(f"Warning: Could not retrieve project details for invoice {facture.id_facture}: {str(e)}")
                            payment_project_name = f"BDC-{facture.bdc_id}" if facture.bdc_id else "N/A"
                        
                        # Build payment proof message
                        payment_proof_msg = ""
                        if has_payment_proof:
                            payment_proof_msg = "Un justificatif de paiement a été joint à cette facture.<br><br>"
                        
                        # Enhanced notification to ESN that admin has paid them
                        esn_message = (
                            f"Nous avons le plaisir de vous informer que le paiement de votre facture a été effectué par l'administration MITC.<br><br>"
                            f"<strong>Détails du paiement :</strong><br>"
                            f"<strong>Facture :</strong> FAC-{facture.id_facture}<br>"
                            f"<strong>Projet :</strong> {payment_project_name}<br>"
                            f"<strong>Période :</strong> {facture.periode}<br>"
                            f"<strong>Montant :</strong> {facture.montant_ttc}€ TTC<br>"
                            f"<strong>Type :</strong> {payment_invoice_type}<br>"
                            f"{payment_proof_msg}"
                            f"Merci de vérifier la réception du paiement sur votre compte bancaire et de confirmer.<br>"
                            f'<a href="/interface-en?menu=invoices" style="color: #1890ff; font-weight: bold; text-decoration: underline;">Consulter mes factures</a>'
                        )
                        
                        send_notification(
                            user_id=None,  # System/Admin action
                            dest_id=esn.ID_ESN,
                            message=esn_message,
                            categorie="ESN",
                            event="Paiement ESN effectué",
                            event_id=facture.id_facture,
                        )

                        # Notification to Client that the invoice process is complete (only on status change)
                        if new_status == "Clôturée" and old_status != "Clôturée":
                            send_notification(
                                user_id=None,
                                dest_id=client.ID_clt,
                                message=(
                                    f"La facture <strong>FAC-{facture.id_facture}</strong> du projet <strong>{project_name}</strong> "
                                    f"pour la période <strong>{facture.periode}</strong> ({invoice_type}) "
                                    f"a été entièrement traitée. Le paiement à l'ESN {esn.Raison_sociale} a été effectué par l'administration. "
                                    f"Le dossier est maintenant clôturé. "
                                    f'<a href="/interface-cl?menu=invoices" style="color: #1890ff; text-decoration: underline;">Voir mes factures</a>'
                                ),
                                categorie="CLIENT",
                                event="Facture clôturée",
                                event_id=facture.id_facture,
                            )

                            # Commercial/responsable payment notifications intentionally disabled


                    # Notification when ESN confirms reception (status changes to "Reçue")
                    if new_status == "Reçue" and old_status != "Reçue":
                        try:
                            bdc = Bondecommande.objects.get(id_bdc=facture.bdc_id)
                            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                            ao = AppelOffre.objects.get(id=candidature.AO_id)
                            project_name = ao.titre

                            invoice_type = "CRA"
                            if facture.type_facture and "NDF" in facture.type_facture.upper():
                                invoice_type = "NDF"
                        except Exception:
                            project_name = "projet"
                            invoice_type = "CRA"

                        admin_message = (
                            f"L'ESN <strong>{esn.Raison_sociale}</strong> a confirmé la réception du paiement pour la facture "
                            f"<strong>FAC-{facture.id_facture}</strong> ({invoice_type}) du projet <strong>{project_name}</strong> "
                            f"sur la période <strong>{facture.periode}</strong>."
                            f"<br>Montant confirmé : <strong>{facture.montant_ttc}€ TTC</strong>.<br><br>"
                            f"Le dossier est désormais validé côté ESN."
                            f'<br><a href="/interface-ad?menu=invoices" style="color: #1890ff; text-decoration: underline;">Voir la facture</a>'
                        )

                        notify_admins(
                            esn.ID_ESN,
                            admin_message,
                            "Confirmation paiement ESN",
                        )

                        send_notification(
                            user_id=esn.ID_ESN,
                            dest_id=client.ID_clt,
                            message=(
                                f"L'ESN {esn.Raison_sociale} a confirmé la réception du paiement pour la facture FAC-{facture.id_facture} "
                                f"({invoice_type}) du projet {project_name} ({facture.periode})."
                                f" Merci pour votre règlement."),
                            categorie="CLIENT",
                            event="Paiement confirmé par ESN",
                            event_id=facture.id_facture,
                        )

                        # Commercial/responsable payment notifications intentionally disabled


                    # Notification when ESN confirms payment reception (attachment added after "Payée" status)
                    if new_attachment and new_attachment != old_attachment and old_status == "Payée":
                        try:
                            bdc = Bondecommande.objects.get(id_bdc=facture.bdc_id)
                            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                            ao = AppelOffre.objects.get(id=candidature.AO_id)
                            project_name = ao.titre

                            invoice_type = "CRA"
                            if facture.type_facture and "NDF" in facture.type_facture.upper():
                                invoice_type = "NDF"
                        except Exception:
                            project_name = "projet"
                            invoice_type = "CRA"

                        admin_message = (
                            f"L'ESN <strong>{esn.Raison_sociale}</strong> a confirmé la réception du paiement pour la facture "
                            f"<strong>FAC-{facture.id_facture}</strong> ({invoice_type}) du projet <strong>{project_name}</strong> "
                            f"sur la période <strong>{facture.periode}</strong>.<br>"
                            f"Montant réglé : <strong>{facture.montant_ttc}€ TTC</strong>.<br><br>"
                            f"Le justificatif transmis est disponible dans la fiche facture.<br><br>"
                            f'<a href="/interface-ad?menu=invoices" style="color: #1890ff; text-decoration: underline;">Ouvrir la facture</a>'
                        )

                        notify_admins(
                            esn.ID_ESN,
                            admin_message,
                            "Réception paiement ESN confirmée",
                        )

                        # Commercial/responsable payment notifications intentionally disabled

                except (ESN.DoesNotExist, Client.DoesNotExist) as e:
                    # Log the error but don't fail the invoice update
                    print(f"Warning: Could not send notifications for invoice {facture.id_facture}: {str(e)}")
                
                return JsonResponse({'success': True, 'message': 'Facture updated successfully', 'data': serializer.data}, status=200)
            return JsonResponse({'success': False, 'errors': serializer.errors}, status=400)
            
        except Facture.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Facture not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    elif request.method == 'DELETE':
        try:
            # Use facture_id from URL if provided
            target_facture_id = facture_id
            
            if not target_facture_id:
                # Handle request data for DELETE if no URL parameter
                if request.content_type == 'application/json':
                    data = json.loads(request.body.decode('utf-8'))
                else:
                    data = request.POST.dict()
                target_facture_id = data.get('id_facture')
            
            if not target_facture_id:
                return JsonResponse({'success': False, 'message': 'id_facture is required'}, status=400)
            
            facture = Facture.objects.get(id_facture=target_facture_id)
            facture.delete()
            return JsonResponse({'success': True, 'message': 'Facture deleted successfully'}, status=200)
            
        except Facture.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Facture not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    elif request.method == 'POST':
        # ...existing POST code...
        try:
            # Handle request data
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST.dict()
            
            print(f"DEBUG - Original data: {data}")  # Debug log
            
            # Auto-collect id_esn and id_client if missing but bdc_id is provided
            if 'bdc_id' in data:
                bdc_id = data['bdc_id']
                print(f"DEBUG - Processing BDC ID: {bdc_id}")
                
                # Check if we need to auto-collect
                need_esn = 'id_esn' not in data or not data.get('id_esn') or data.get('id_esn') is None
                need_client = 'id_client' not in data or not data.get('id_client') or data.get('id_client') is None
                
                print(f"DEBUG - need_esn: {need_esn}, need_client: {need_client}")
                print(f"DEBUG - Current id_esn: {data.get('id_esn')}, id_client: {data.get('id_client')}")
                
                if need_esn or need_client:
                    try:
                        # Get the Bondecommande record
                        print(f"DEBUG - Looking for BDC with id: {bdc_id}")
                        bdc = Bondecommande.objects.get(id_bdc=bdc_id)
                        print(f"DEBUG - Found BDC: {bdc}")
                        
                        # Get the Candidature record using candidature_id from BDC
                        print(f"DEBUG - Looking for Candidature with id: {bdc.candidature_id}")
                        candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                        print(f"DEBUG - Found Candidature: {candidature}")
                        print(f"DEBUG - Candidature ESN ID: {candidature.esn_id}")
                        
                        # Get AppelOffre using AO_id from candidature  
                        print(f"DEBUG - Looking for AppelOffre with id: {candidature.AO_id}")
                        appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                        print(f"DEBUG - Found AppelOffre: {appel_offre}")
                        print(f"DEBUG - AppelOffre Client ID: {appel_offre.client_id}")
                        
                        # Auto-fill missing fields based on your model structure
                        if need_esn:
                            data['id_esn'] = candidature.esn_id  # esn_id from Candidature
                            print(f"DEBUG - Set id_esn to: {candidature.esn_id}")
                        
                        if need_client:
                            data['id_client'] = appel_offre.client_id  # client_id from AppelOffre
                            print(f"DEBUG - Set id_client to: {appel_offre.client_id}")
                            
                    except Bondecommande.DoesNotExist:
                        return JsonResponse({'success': False, 'message': f'Bon de commande with id {bdc_id} not found'}, status=404)
                    except Candidature.DoesNotExist:
                        return JsonResponse({'success': False, 'message': f'Candidature not found for BDC {bdc_id}. candidature_id: {bdc.candidature_id if "bdc" in locals() else "N/A"}'}, status=404)
                    except AppelOffre.DoesNotExist:
                        return JsonResponse({'success': False, 'message': f'Appel d\'offre not found for candidature {candidature.AO_id if "candidature" in locals() else "N/A"}'}, status=404)
                    except Exception as e:
                        return JsonResponse({'success': False, 'message': f'Error in auto-collection: {str(e)}'}, status=500)
            
            print(f"DEBUG - Final data before serializer: {data}")  # Debug log
            
            # Validate required fields after auto-collection
            if not data.get('id_esn') or data.get('id_esn') is None:
                return JsonResponse({'success': False, 'message': 'id_esn is required and could not be auto-collected'}, status=400)
            
            if not data.get('id_client') or data.get('id_client') is None:
                return JsonResponse({'success': False, 'message': 'id_client is required and could not be auto-collected'}, status=400)
            
            # Auto-calculate montant_ht for NDF invoices if not provided or is 0
            if data.get('type_facture') and 'NDF' in data.get('type_facture', '').upper():
                if not data.get('montant_ht') or float(data.get('montant_ht', 0)) == 0:
                    print(f"DEBUG - NDF invoice detected with missing/zero montant_ht, calculating from NDF_CONSULTANT records...")
                    try:
                        # Get consultant_id from BDC -> Candidature
                        if data.get('bdc_id'):
                            bdc = Bondecommande.objects.get(id_bdc=data['bdc_id'])
                            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                            consultant_id = candidature.id_consultant
                            periode = data.get('periode')
                            
                            if consultant_id and periode:
                                # Calculate total from NDF_CONSULTANT records for this consultant and period
                                ndf_records = NDF_CONSULTANT.objects.filter(
                                    id_consultan=consultant_id,
                                    période=periode
                                )
                                total_ndf = sum(float(ndf.montant_ht or 0) for ndf in ndf_records)
                                
                                if total_ndf > 0:
                                    data['montant_ht'] = total_ndf
                                    print(f"DEBUG - Calculated NDF montant_ht from records: {total_ndf}€")
                                else:
                                    print(f"DEBUG - No NDF records found or total is 0 for consultant {consultant_id}, period {periode}")
                    except Exception as e:
                        print(f"Warning: Could not auto-calculate NDF amount: {str(e)}")
            
            # Auto-calculate montant_ttc - always override any user-provided value
            if 'montant_ht' in data:
                montant_ht = float(data['montant_ht'])
                taux_tva = float(data.get('taux_tva', 20.00))
                print(f"DEBUG - Input values: montant_ht={montant_ht}, taux_tva={taux_tva}")
                
                # Calculate and round to 2 decimal places to fit within 10 digits
                calculated_ttc = round(montant_ht * (1 + taux_tva / 100), 2)
                data['montant_ttc'] = calculated_ttc
                print(f"DEBUG - Calculated montant_ttc: {calculated_ttc} from montant_ht: {montant_ht} and taux_tva: {taux_tva}")
                print(f"DEBUG - montant_ttc type: {type(calculated_ttc)}, value: {calculated_ttc}")
            elif 'montant_ttc' in data:
                # If user only provides montant_ttc, remove it to prevent validation error
                # We'll require montant_ht instead
                print(f"DEBUG - User provided montant_ttc: {data['montant_ttc']}, removing it")
                del data['montant_ttc']
                if 'montant_ht' not in data:
                    return JsonResponse({'success': False, 'message': 'montant_ht is required for automatic calculation'}, status=400)
            
            # Create new facture
            serializer = FactureSerializer(data=data)
            if serializer.is_valid():
                new_facture = serializer.save()
                
                # Generate invoice number using pattern-based numbering
                try:
                    numero = generate_invoice_numero(
                        facture_type=new_facture.type_facture,
                        client_id=new_facture.id_client,
                        esn_id=new_facture.id_esn,
                        bdc_id=new_facture.bdc_id,
                        periode=new_facture.periode,
                        id_facture=new_facture.id_facture
                    )
                    # Store in a cached field for display (numero_facture derived from pattern)
                    # We'll add this to serializer output
                    new_facture._numero_pattern = numero
                except Exception as e:
                    print(f"Warning: Could not generate invoice numero: {str(e)}")
                    new_facture._numero_pattern = f"FAC-{new_facture.id_facture}"
                
                # Send notifications when invoice is created
                # NOTE: Invoice notifications are sent ONLY to ESN, Admin, and Client
                # Commercials/Responsables do NOT receive invoice notifications
                if ENABLE_INVOICE_CREATION_NOTIFICATIONS:
                    try:
                        # Get ESN and Client information
                        esn = ESN.objects.get(ID_ESN=new_facture.id_esn)
                        client = Client.objects.get(ID_clt=new_facture.id_client)
                        
                        # Get project/BDC information
                        project_name = "N/A"
                        try:
                            bdc = Bondecommande.objects.get(id_bdc=new_facture.bdc_id)
                            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                            appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                            project_name = appel_offre.titre
                        except:
                            project_name = f"BDC-{new_facture.bdc_id}"
                        
                        # Notification to ESN
                        send_notification(
                            user_id=new_facture.id_client,
                            dest_id=new_facture.id_esn,
                            message=(
                                f"Une facture ({new_facture._numero_pattern}) a été créée pour le projet '{project_name}' "
                                f"période {new_facture.periode}. Montant HT: {new_facture.montant_ht}€, TTC: {new_facture.montant_ttc}€. "
                                f'<a href="/interface-en?menu=invoices" class="notification-link">Voir les factures</a>'
                            ),
                            categorie="ESN",
                            event="Facture créée",
                            event_id=new_facture.id_facture
                        )
                        
                        # Notification to all Admins
                        for admin in Admin.objects.all():
                            send_notification(
                                user_id=new_facture.id_client,
                                dest_id=admin.ID_Admin,
                                message=(
                                    f"Une facture ({new_facture._numero_pattern}) a été créée pour le projet '{project_name}' "
                                    f"(Client: {client.raison_sociale}, ESN: {esn.Raison_sociale}). Montant: {new_facture.montant_ttc}€ TTC. "
                                    f'<a href="/interface-ad?menu=invoices" class="notification-link">Voir les factures</a>'
                                ),
                                categorie="ADMIN",
                                event="Facture créée",
                                event_id=new_facture.id_facture
                            )
                        
                        # Notification to Client
                        send_notification(
                            user_id=new_facture.id_client,
                            dest_id=new_facture.id_client,
                            message=(
                                f"Une facture ({new_facture._numero_pattern}) a été créée pour le projet '{project_name}' "
                                f"période {new_facture.periode}. Montant: {new_facture.montant_ttc}€ TTC. Veuillez procéder au paiement. "
                                f'<a href="/interface-cl?menu=invoices" class="notification-link">Voir les factures</a>'
                            ),
                            categorie="Client",
                            event="Facture créée",
                            event_id=new_facture.id_facture
                        )
                        
                        print(f"Notifications sent for newly created invoice FAC-{new_facture.id_facture}")
                        
                    except Exception as notif_error:
                        print(f"Error sending notifications for invoice {new_facture.id_facture}: {str(notif_error)}")
                
                # Include the generated numero in the response
                response_data = dict(serializer.data)
                response_data['numero_facture'] = getattr(new_facture, '_numero_pattern', f"FAC-{new_facture.id_facture}")
                return JsonResponse({'success': True, 'message': 'Facture created successfully', 'data': response_data}, status=201)
            else:
                print(f"DEBUG - Serializer errors: {serializer.errors}")  # Debug log
                return JsonResponse({'success': False, 'errors': serializer.errors}, status=400)
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"DEBUG - Exception: {str(e)}")  # Debug log
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


def get_workflow_step(status):
    """
    Helper function to determine workflow step based on CRA status
    """
    if not status:
        return 0
        
    status_upper = status.upper()
    
    if status_upper in ["A_SAISIR", "À_SAISIR"]:
        return 0
    elif status_upper in ["SAISI"]:
        return 1
    elif status_upper in ["VALIDE_ESN", "VALIDÉ_ESN"]:
        return 2
    elif status_upper in ["VALIDE_CLIENT", "VALIDÉ_CLIENT"]:
        return 3
    elif status_upper in ["FACTURE", "FACTURÉ"]:
        return 4
    elif status_upper in ["REJETE_ESN", "REJETÉ_ESN"]:
        return 1
    elif status_upper in ["REJETE_CLIENT", "REJETÉ_CLIENT"]:
        return 2
    else:
        return 0

@csrf_exempt
def admin_cra_workflow(request):
    """
    API endpoint for admin CRA validation workflow tracking
    Returns comprehensive data about all CRAs and their validation status
    """
    if request.method == 'GET':
        try:
            print("DEBUG: Starting admin_cra_workflow API call")
            
            # Get all CRA_CONSULTANT records with their related data
            cra_consultants = CRA_CONSULTANT.objects.all()
            print(f"DEBUG: Found {len(cra_consultants)} CRA_CONSULTANT records")
            
            workflow_data = []
            
            for cra in cra_consultants:
                print(f"DEBUG: Processing CRA {cra.id_CRA} - Consultant: {cra.id_consultan}, Client: {cra.id_client}, ESN: {cra.id_esn}")
                try:
                    # Get consultant information
                    try:
                        consultant = Collaborateur.objects.get(ID_collab=cra.id_consultan)
                        consultant_name = f"{consultant.Nom} {consultant.Prenom}"
                    except Collaborateur.DoesNotExist:
                        print(f"DEBUG: Collaborateur {cra.id_consultan} not found")
                        consultant_name = f"Consultant {cra.id_consultan}"
                    
                    # Get client information
                    try:
                        client = Client.objects.get(ID_clt=cra.id_client)
                        client_name = client.raison_sociale or f"Client {client.ID_clt}"
                    except Client.DoesNotExist:
                        print(f"DEBUG: Client {cra.id_client} not found")
                        client_name = f"Client {cra.id_client}"
                    
                    # Get ESN information
                    try:
                        esn = ESN.objects.get(ID_ESN=cra.id_esn)
                        esn_name = esn.Raison_sociale or f"ESN {esn.ID_ESN}"
                    except ESN.DoesNotExist:
                        print(f"DEBUG: ESN {cra.id_esn} not found")
                        esn_name = f"ESN {cra.id_esn}"
                    
                    # Get BDC information for project title
                    try:
                        bon_commande = Bondecommande.objects.get(id_bdc=cra.id_bdc)
                        project_title = bon_commande.titre if hasattr(bon_commande, 'titre') else f"Projet BDC-{bon_commande.id_bdc}"
                        tjm = float(bon_commande.TJM) if bon_commande.TJM else 0
                    except Bondecommande.DoesNotExist:
                        print(f"DEBUG: Bondecommande {cra.id_bdc} not found")
                        project_title = f"Projet BDC-{cra.id_bdc}"
                        tjm = 0
                    
                    # Get all imputations for this CRA to calculate totals
                    imputations = CRA_imputation.objects.filter(
                        id_consultan=cra.id_consultan,
                        période=cra.période,
                        id_bdc=cra.id_bdc
                    )
                    
                    # Calculate totals
                    total_days = sum(float(imp.Durée) for imp in imputations if imp.Durée)
                    total_amount = total_days * tjm
                    
                    # Determine workflow dates based on status
                    submitted_date = None
                    esn_validation_date = None
                    client_validation_date = None
                    invoice_date = None
                    
                    # Check if there's a related facture (invoice)
                    try:
                        facture = Facture.objects.filter(
                            bdc_id=cra.id_bdc,
                            periode=cra.période
                        ).first()
                        if facture:
                            invoice_date = facture.date_emission.isoformat()
                    except:
                        pass
                    
                    # Determine dates based on CRA status
                    if cra.statut in ["saisi", "SAISI"]:
                        submitted_date = "2025-09-01"  # Default or get from creation date
                    elif cra.statut in ["valide_esn", "VALIDE_ESN"]:
                        submitted_date = "2025-09-01"
                        esn_validation_date = "2025-09-02"
                    elif cra.statut in ["valide_client", "VALIDE_CLIENT"]:
                        submitted_date = "2025-09-01"
                        esn_validation_date = "2025-09-02"
                        client_validation_date = "2025-09-03"
                    elif cra.statut in ["facture", "FACTURE"]:
                        submitted_date = "2025-09-01"
                        esn_validation_date = "2025-09-02"
                        client_validation_date = "2025-09-03"
                        if not invoice_date:
                            invoice_date = "2025-09-04"
                    
                    workflow_item = {
                        "id": cra.id_CRA,
                        "consultant_name": consultant_name,
                        "client_name": client_name,
                        "esn_name": esn_name,
                        "project_title": project_title,
                        "period": cra.période,
                        "status": cra.statut.upper() if cra.statut else "UNKNOWN",
                        "submitted_date": submitted_date,
                        "esn_validation_date": esn_validation_date,
                        "client_validation_date": client_validation_date,
                        "invoice_date": invoice_date,
                        "total_days": int(total_days),
                        "tjm": int(tjm),
                        "total_amount": int(total_amount),
                        "workflow_step": get_workflow_step(cra.statut),
                        "consultant_id": cra.id_consultan,
                        "client_id": cra.id_client,
                        "esn_id": cra.id_esn,
                        "bdc_id": cra.id_bdc
                    }
                    
                    workflow_data.append(workflow_item)
                    
                except (Collaborateur.DoesNotExist, Client.DoesNotExist, ESN.DoesNotExist, Bondecommande.DoesNotExist) as e:
                    # Skip records with missing related data
                    print(f"Skipping CRA {cra.id_CRA} due to missing related data: {str(e)}")
                    continue
                except Exception as e:
                    print(f"Error processing CRA {cra.id_CRA}: {str(e)}")
                    continue
            
            return JsonResponse({
                "status": True,
                "total": len(workflow_data),
                "data": workflow_data
            }, safe=False)
            
        except Exception as e:
            print(f"Error in admin_cra_workflow: {str(e)}")
            return JsonResponse({
                "status": False,
                "message": f"Error fetching CRA workflow data: {str(e)}",
                "data": []
            }, status=500)
    
    else:
        return JsonResponse({
            "status": False,
            "message": "Method not allowed"
        }, status=405)


@csrf_exempt
def notify_new_client_registration(request):
    """
    API endpoint to notify admins about new client registration requiring document verification
    """
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            client_id = data.get('client_id')
            
            if not client_id:
                return JsonResponse({
                    "status": False, 
                    "message": "client_id est requis"
                }, safe=False)
            
            # Get client details
            try:
                client = Client.objects.get(ID_clt=client_id)
                client_name = client.raison_sociale
                client_email = client.Email_clt
                
            except Client.DoesNotExist:
                return JsonResponse({
                    "status": False, 
                    "message": "Client introuvable"
                }, safe=False)
            
            # Get all admin users
            admins = Admin.objects.all()
            if not admins.exists():
                return JsonResponse({"status": False, "message": "Aucun administrateur trouvé"}, safe=False)
            
            notifications_sent = 0
            
            # Create notification message for admins
            admin_message = (
                f"Un nouveau client \"{client_name}\" (Email: {client_email}) s'est inscrit sur la plateforme. "
                f"Les documents soumis doivent être vérifiés et validés avant activation du compte. "
                f"<a href='/interface-ad/clients/{client_id}' class='notification-link'>Vérifier les documents</a>"
            )
            
            # Send notification to all admins
            for admin in admins:
                send_notification(
                    user_id=client_id,  # Client triggered the event
                    dest_id=admin.ID_Admin,  # Notification goes to admin
                    message=admin_message,
                    categorie="Admin",
                    event="Inscription Client",
                    event_id=client_id
                )
                notifications_sent += 1
            
            return JsonResponse({
                "status": True, 
                "message": f"Notifications envoyées à {notifications_sent} administrateurs pour vérification des documents du nouveau client"
            }, safe=False)
            
        except Exception as e:
            print(f"Erreur: {e}")
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False)


@csrf_exempt  
def notify_client_contract_signature(request):
    """
    API endpoint to notify client that they need to sign a contract
    """
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            client_id = data.get('client_id')
            bon_de_commande_id = data.get('bon_de_commande_id')
            esn_id = data.get('esn_id')
            
            if not client_id or not bon_de_commande_id or not esn_id:
                return JsonResponse({
                    "status": False, 
                    "message": "client_id, bon_de_commande_id et esn_id sont requis"
                }, safe=False)
            
            # Get detailed information about the contract context
            try:
                # Get bon de commande details
                bon_commande = Bondecommande.objects.get(id_bdc=bon_de_commande_id)
                montant = bon_commande.montant_total
                
                # Get candidature details
                candidature = Candidature.objects.get(id_cd=bon_commande.candidature_id)
                
                # Get appel d'offre details
                appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                ao_title = appel_offre.titre
                
                # Get client details
                client = Client.objects.get(ID_clt=client_id)
                client_name = client.raison_sociale
                
                # Get ESN details
                esn = ESN.objects.get(ID_ESN=esn_id)
                esn_name = esn.Raison_sociale
                
                # Get consultant details (if available)
                consultant_name = "Non spécifié"
                if candidature.id_consultant:
                    try:
                        consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
                        consultant_name = f"{consultant.Nom} {consultant.Prenom}"
                    except Collaborateur.DoesNotExist:
                        pass
                
            except (Bondecommande.DoesNotExist, Candidature.DoesNotExist, 
                   AppelOffre.DoesNotExist, Client.DoesNotExist, ESN.DoesNotExist):
                return JsonResponse({
                    "status": False, 
                    "message": "Impossible de récupérer les informations du contrat"
                }, safe=False)
            
            # Create contract signature link for client
            contract_link = f"/interface-cl/contracts/{bon_de_commande_id}"
            
            # Create notification message for client
            client_message = (
                f"La mission pour le projet \"{ao_title}\" avec {esn_name} peut démarrer. "
                f"Bon de commande (ID: {bon_de_commande_id}), Montant: {montant}€, "
                f"Consultant assigné: {consultant_name}. "
            )
            
            # Send notification to client
            send_notification(
                user_id=esn_id,  # ESN triggered the contract signing process
                dest_id=client_id,  # Notification goes to client
                message=client_message,
                categorie="Client",
                event="Démarrage Mission",
                event_id=bon_de_commande_id
            )
            
            return JsonResponse({
                "status": True, 
                "message": "Notification de signature de contrat envoyée au client"
            }, safe=False)
            
        except Exception as e:
            print(f"Erreur: {e}")
            return JsonResponse({"status": False, "message": str(e)}, safe=False)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False)


@csrf_exempt  
def send_client_reminder(request):
    """Envoie un rappel à un client basé sur son statut actuel"""
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            client_id = data.get('client_id')
            
            if not client_id:
                return JsonResponse({"status": False, "message": "ID du client requis"}, safe=False, status=400)
            
            try:
                client = Client.objects.get(ID_clt=client_id)
            except Client.DoesNotExist:
                return JsonResponse({"status": False, "message": "Client non trouvé"}, safe=False, status=404)
            
            # Analyze client profile status and determine reminder type
            profile_link = "/interface-cl?menu=Mon-Profil"
            contracts_link = "/interface-cl?menu=contrats"
            
            # Check client status and create appropriate reminder
            if client.statut == "à signer":
                # Reminder for contract signing
                event = "Rappel - Signature de Contrat"
                client_message = (
                    f"<strong>RAPPEL IMPORTANT</strong><br/><br/>"
                    f"Bonjour {client.raison_sociale}, "
                    f"Votre compte a été validé mais vous n'avez pas encore signé le contrat cadre. "
                    f"<br/><br/><strong>Action requise :</strong> "
                    f"<br/>• Consulter et signer le contrat cadre "
                    f"<br/>• Finaliser votre inscription "
                    f"<br/><br/>"
                    f"<a href='{contracts_link}' style='background-color: #1890ff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;'>Signer le contrat maintenant</a>"
                    f"<br/><br/>L'équipe MAGHREB CONNECT IT"
                )
            elif client.statut == "en attente":
                # Reminder for profile completion
                event = "Rappel - Compléter le Profil"
                client_message = (
                    f"<strong>PROFIL A COMPLETER</strong><br/><br/>"
                    f"Bonjour {client.raison_sociale}, "
                    f"Votre profil client nécessite quelques informations supplémentaires pour être validé par nos équipes. "
                    f"<br/><br/><strong>Documents et informations requis :</strong> "
                    f"<br/>• KBIS de votre entreprise "
                    f"<br/>• RIB pour les paiements "
                    f"<br/>• Informations de contact complètes "
                    f"<br/>• Adresse de facturation "
                    f"<br/><br/>"
                    f"<a href='{profile_link}' style='background-color: #52c41a; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;'>Compléter mon profil</a>"
                    f"<br/><br/>L'équipe MAGHREB CONNECT IT"
                )
            else:
                # General reminder for active clients
                event = "Rappel - Mise à Jour Profil"
                client_message = (
                    f"<strong>MISE A JOUR DE PROFIL</strong><br/><br/>"
                    f"Bonjour {client.raison_sociale}, "
                    f"N'oubliez pas de maintenir vos informations à jour pour une meilleure expérience. "
                    f"<br/><br/><strong>Vérifiez :</strong> "
                    f"<br/>• Vos informations de contact "
                    f"<br/>• Vos documents (expiration, validité) "
                    f"<br/>• Votre profil entreprise "
                    f"<br/><br/>"
                    f"<a href='{profile_link}' style='background-color: #722ed1; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;'>Mettre à jour</a>"
                    f"<br/><br/>L'équipe MAGHREB CONNECT IT"
                )
            
            # Send notification to CLIENT category (not Admin)
            send_notification(
                user_id=1, dest_id=client.ID_clt, message=client_message,
                categorie="Client", event=event, event_id=client.ID_clt
            )
            
            return JsonResponse({"status": True, "message": f"Rappel ({event}) envoyé à {client.raison_sociale}"}, safe=False)
            
        except Exception as e:
            return JsonResponse({"status": False, "message": f"Erreur: {str(e)}"}, safe=False, status=500)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False, status=405)


@csrf_exempt
def send_esn_reminder(request):
    """Envoie un rappel à une ESN basé sur son statut actuel"""  
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            esn_id = data.get('esn_id')
            
            if not esn_id:
                return JsonResponse({"status": False, "message": "ID de l'ESN requis"}, safe=False, status=400)
            
            try:
                esn = ESN.objects.get(ID_ESN=esn_id)
            except ESN.DoesNotExist:
                return JsonResponse({"status": False, "message": "ESN non trouvée"}, safe=False, status=404)
            
            # Analyze ESN profile status and determine reminder type
            profile_link = "/interface-en?menu=Profile"
            contracts_link = "/interface-en?menu=contrats"
            
            # Check ESN status and create appropriate reminder
            if esn.Statut == "à signer":
                # Reminder for contract signing
                event = "Rappel - Signature de Contrat"
                esn_message = (
                    f"<strong>RAPPEL IMPORTANT</strong><br/><br/>"
                    f"Bonjour {esn.Raison_sociale}, "
                    f"Votre compte ESN a été validé mais vous n'avez pas encore signé le contrat de prestation. "
                    f"<br/><br/><strong>Action requise :</strong> "
                    f"<br/>• Consulter et signer le contrat de prestation "
                    f"<br/>• Finaliser votre inscription "
                    f"<br/><br/>"
                    f"<a href='{profile_link}' style='background-color: #1890ff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;'>Signer le contrat maintenant</a>"
                    f"<br/><br/>L'équipe MAGHREB CONNECT IT"
                )
            elif esn.Statut == "en attente":
                # Reminder for profile completion and document upload
                event = "Rappel - Compléter le Profil"
                esn_message = (
                    f"<strong>PROFIL ESN A COMPLETER</strong><br/><br/>"
                    f"Bonjour {esn.Raison_sociale}, "
                    f"Votre profil ESN nécessite quelques informations et documents supplémentaires pour être validé par nos équipes. "
                    f"<br/><br/><strong>Documents et informations requis :</strong> "
                    f"<br/>• KBIS de votre entreprise "
                    f"<br/>• RIB pour les paiements "
                    f"<br/>• Attestations professionnelles "
                    f"<br/>• Informations de contact complètes "
                    f"<br/>• Liste de vos collaborateurs "
                    f"<br/><br/>"
                    f"<a href='{profile_link}' style='background-color: #52c41a; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;'>Compléter mon profil ESN</a>"
                    f"<br/><br/>L'équipe MAGHREB CONNECT IT"
                )
            elif esn.Statut == "validé":
                # Reminder for adding collaborators or updating info
                event = "Rappel - Ajouter des Collaborateurs"
                esn_message = (
                    f"<strong>AJOUTEZ VOS COLLABORATEURS</strong><br/><br/>"
                    f"Bonjour {esn.Raison_sociale}, "
                    f"Votre profil ESN est validé ! Pour maximiser vos opportunités, pensez à : "
                    f"<br/><br/><strong>Actions recommandées :</strong> "
                    f"<br/>• Ajouter vos collaborateurs qualifiés "
                    f"<br/>• Mettre à jour leurs compétences "
                    f"<br/>• Vérifier vos informations de contact "
                    f"<br/>• Consulter les nouveaux appels d'offres "
                    f"<br/><br/>"
                    f"<a href='{profile_link}' style='background-color: #13c2c2; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;'>Gérer mes collaborateurs</a>"
                    f"<br/><br/>L'équipe MAGHREB CONNECT IT"
                )
            else:
                # General reminder for active ESN
                event = "Rappel - Mise à Jour Profil"
                esn_message = (
                    f"<strong>MISE A JOUR DE PROFIL ESN</strong><br/><br/>"
                    f"Bonjour {esn.Raison_sociale}, "
                    f"N'oubliez pas de maintenir vos informations à jour pour de meilleures opportunités. "
                    f"<br/><br/><strong>Vérifiez :</strong> "
                    f"<br/>• Vos informations de contact "
                    f"<br/>• Vos documents (expiration, validité) "
                    f"<br/>• Les profils de vos collaborateurs "
                    f"<br/>• Vos compétences et certifications "
                    f"<br/><br/>"
                    f"<a href='{profile_link}' style='background-color: #722ed1; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;'>Mettre à jour mon profil</a>"
                    f"<br/><br/>L'équipe MAGHREB CONNECT IT"
                )
            
            # Send notification to ESN category (not Admin)
            send_notification(
                user_id=1, dest_id=esn.ID_ESN, message=esn_message,
                categorie="ESN", event=event, event_id=esn.ID_ESN
            )
            
            return JsonResponse({"status": True, "message": f"Rappel ({event}) envoyé à {esn.Raison_sociale}"}, safe=False)
            
        except Exception as e:
            return JsonResponse({"status": False, "message": f"Erreur: {str(e)}"}, safe=False, status=500)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False, status=405)


@csrf_exempt
def send_client_reminder(request):
    """Send custom reminder email to client"""
    if not checkAuth(request):
        return JsonResponse({"status": False, "message": "Non authentifié"}, safe=False, status=401)
    
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            
            # Get required fields
            client_id = data.get('recipient_id')
            subject = data.get('subject', '')
            body = data.get('body', '')
            template_type = data.get('template_type', 'CUSTOM')
            sender = data.get('sender', 'admin')
            
            if not client_id or not subject or not body:
                return JsonResponse({
                    "status": False, 
                    "message": "Champs requis manquants: recipient_id, subject, body"
                }, safe=False, status=400)
            
            # Get client info
            try:
                client = Client.objects.get(pk=client_id)
            except Client.DoesNotExist:
                return JsonResponse({
                    "status": False, 
                    "message": "Client non trouvé"
                }, safe=False, status=404)
            
            # Send email using Django's send_mail
            from django.core.mail import send_mail
            from django.conf import settings
            
            email_sent = send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@maghrebitconnect.com',
                recipient_list=[client.mail_contact],
                fail_silently=False,
            )
            
            if email_sent:
                # Log the reminder in database
                # Translate notification message and event based on template type
                if template_type == "VALIDATION_REQUIRED":
                    notif_message = f"Rappel : veuillez vérifier vos informations pour activer votre compte."
                    event_name = "Rappel - Validation de profil requise"
                else:
                    notif_message = f"Rappel envoyé : {subject}"
                    event_name = f"REMINDER_{template_type}"
                    
                send_notification(
                    user_id=1,  # Admin user
                    dest_id=client.id_client,
                    message=notif_message,
                    categorie="CLIENT",
                    event=event_name,
                    event_id=client.id_client
                )
                
                return JsonResponse({
                    "status": True, 
                    "message": f"Rappel envoyé à {client.nom_client or client.raison_sociale}"
                }, safe=False)
            else:
                return JsonResponse({
                    "status": False, 
                    "message": "Échec de l'envoi de l'email"
                }, safe=False, status=500)
                
        except Exception as e:
            return JsonResponse({
                "status": False, 
                "message": f"Erreur lors de l'envoi du rappel: {str(e)}"
            }, safe=False, status=500)
    
    return JsonResponse({
        "status": False, 
        "message": "Seule la méthode POST est autorisée"
    }, safe=False, status=405)


@csrf_exempt
def send_esn_reminder(request):
    """Send custom reminder email to ESN"""
    if not checkAuth(request):
        return JsonResponse({"status": False, "message": "Non authentifié"}, safe=False, status=401)
    
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            
            # Get required fields
            esn_id = data.get('recipient_id')
            subject = data.get('subject', '')
            body = data.get('body', '')
            template_type = data.get('template_type', 'CUSTOM')
            sender = data.get('sender', 'admin')
            
            if not esn_id or not subject or not body:
                return JsonResponse({
                    "status": False, 
                    "message": "Champs requis manquants: recipient_id, subject, body"
                }, safe=False, status=400)
            
            # Get ESN info
            try:
                esn = ESN.objects.get(pk=esn_id)
            except ESN.DoesNotExist:
                return JsonResponse({
                    "status": False, 
                    "message": "ESN non trouvée"
                }, safe=False, status=404)
            
            # Send email using Django's send_mail
            from django.core.mail import send_mail
            from django.conf import settings
            
            email_sent = send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@maghrebitconnect.com',
                recipient_list=[esn.mail_Contact],
                fail_silently=False,
            )
            
            if email_sent:
                # Log the reminder in database
                # Translate notification message and event based on template type
                if template_type == "VALIDATION_REQUIRED":
                    notif_message = f"Rappel : veuillez vérifier vos informations pour activer votre compte."
                    event_name = "Rappel - Validation de profil requise"
                else:
                    notif_message = f"Rappel envoyé : {subject}"
                    event_name = f"REMINDER_{template_type}"
                    
                send_notification(
                    user_id=1,  # Admin user
                    dest_id=esn.ID_ESN,
                    message=notif_message,
                    categorie="ESN",
                    event=event_name,
                    event_id=esn.ID_ESN
                )
                
                return JsonResponse({
                    "status": True, 
                    "message": f"Rappel envoyé à {esn.Raison_sociale}"
                }, safe=False)
            else:
                return JsonResponse({
                    "status": False, 
                    "message": "Échec de l'envoi de l'email"
                }, safe=False, status=500)
                
        except Exception as e:
            return JsonResponse({
                "status": False, 
                "message": f"Erreur lors de l'envoi du rappel: {str(e)}"
            }, safe=False, status=500)
    
    return JsonResponse({
        "status": False, 
        "message": "Seule la méthode POST est autorisée"
    }, safe=False, status=405)


@csrf_exempt
def send_reminder_email(request):
    """Generic reminder email endpoint for both ESN and clients"""
    import logging
    import traceback
    from django.core.mail import send_mail
    from django.conf import settings
    
    # Set up logging
    logger = logging.getLogger(__name__)
    
    if not checkAuth(request):
        return JsonResponse({"status": False, "message": "Non authentifié"}, safe=False, status=401)
    
    if request.method == 'POST':
        try:
            logger.info("=== REMINDER EMAIL DEBUG START ===")
            
            data = JSONParser().parse(request)
            logger.info(f"Parsed data: {data}")
            
            # Get required fields
            recipient_type = data.get('recipient_type', '').upper()  # ESN or CLIENT
            recipient_id = data.get('recipient_id')
            subject = data.get('subject', '')
            body = data.get('body', '')
            template_type = data.get('template_type', 'CUSTOM')
            sender = data.get('sender', 'admin')
            
            logger.info(f"Recipient type: {recipient_type}, ID: {recipient_id}, Subject: {subject}")
            
            if not recipient_type or not recipient_id or not subject or not body:
                return JsonResponse({
                    "status": False, 
                    "message": "Champs requis manquants: recipient_type, recipient_id, subject, body"
                }, safe=False, status=400)
            
            # Check email configuration
            logger.info(f"Email backend: {getattr(settings, 'EMAIL_BACKEND', 'Not set')}")
            logger.info(f"Default from email: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set')}")
            
            # Handle ESN reminders
            if recipient_type == 'ESN':
                try:
                    esn = ESN.objects.get(pk=recipient_id)
                    logger.info(f"Found ESN: {esn.Raison_sociale}, Email: {esn.mail_Contact}")
                except ESN.DoesNotExist:
                    logger.error(f"ESN with ID {recipient_id} not found")
                    return JsonResponse({
                        "status": False, 
                        "message": "ESN non trouvée"
                    }, safe=False, status=404)
                
                # Validate email address
                if not esn.mail_Contact or '@' not in esn.mail_Contact:
                    logger.error(f"Invalid email address for ESN: {esn.mail_Contact}")
                    return JsonResponse({
                        "status": False, 
                        "message": f"Adresse email invalide pour {esn.Raison_sociale}: {esn.mail_Contact}"
                    }, safe=False, status=400)
                
                logger.info(f"Attempting to send email to: {esn.mail_Contact}")
                
                try:
                    email_sent = send_mail(
                        subject=subject,
                        message=body,
                        from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@maghrebitconnect.com',
                        recipient_list=[esn.mail_Contact],
                        fail_silently=False,
                    )
                    logger.info(f"send_mail returned: {email_sent}")
                    
                    if email_sent:
                        # Log the reminder in database
                        try:
                            # Translate notification message and event based on template type
                            logger.info(f"Template type received: {template_type}")
                            if template_type == "VALIDATION_REQUIRED":
                                notif_message = f"Rappel : veuillez vérifier vos informations pour activer votre compte."
                                event_name = "Rappel - Validation de profil requise"
                                logger.info(f"Using French event name: {event_name}")
                            else:
                                notif_message = f"Rappel envoyé : {subject}"
                                event_name = f"REMINDER_{template_type}"
                                logger.info(f"Using default event name: {event_name}")
                            
                            logger.info(f"About to create notification with event: {event_name}")
                            send_notification(
                                user_id=1,  # Admin user
                                dest_id=esn.ID_ESN,
                                message=notif_message,
                                categorie="ESN",
                                event=event_name,
                                event_id=esn.ID_ESN
                            )
                            logger.info(f"Notification logged successfully with event: {event_name}")
                        except Exception as notif_error:
                            logger.error(f"Failed to log notification: {notif_error}")
                        
                        return JsonResponse({
                            "status": True, 
                            "message": f"Rappel envoyé à {esn.Raison_sociale}"
                        }, safe=False)
                    else:
                        logger.error("send_mail returned 0 (no emails sent)")
                        return JsonResponse({
                            "status": False, 
                            "message": "Échec de l'envoi de l'email - Aucun email envoyé"
                        }, safe=False, status=500)
                        
                except Exception as email_error:
                    logger.error(f"Email sending failed: {email_error}")
                    logger.error(f"Email error traceback: {traceback.format_exc()}")
                    return JsonResponse({
                        "status": False, 
                        "message": f"Erreur d'envoi email: {str(email_error)}"
                    }, safe=False, status=500)
                    
            # Handle CLIENT reminders        
            elif recipient_type == 'CLIENT':
                try:
                    client = Client.objects.get(pk=recipient_id)
                    logger.info(f"Found Client: {client.raison_sociale}, Email: {client.mail_contact}")
                except Client.DoesNotExist:
                    logger.error(f"Client with ID {recipient_id} not found")
                    return JsonResponse({
                        "status": False, 
                        "message": "Client non trouvé"
                    }, safe=False, status=404)
                
                # Validate email address
                if not client.mail_contact or '@' not in client.mail_contact:
                    logger.error(f"Invalid email address for client: {client.mail_contact}")
                    return JsonResponse({
                        "status": False, 
                        "message": f"Adresse email invalide pour {client.raison_sociale}: {client.mail_contact}"
                    }, safe=False, status=400)
                
                logger.info(f"Attempting to send email to: {client.mail_contact}")
                
                try:
                    email_sent = send_mail(
                        subject=subject,
                        message=body,
                        from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@maghrebitconnect.com',
                        recipient_list=[client.mail_contact],
                        fail_silently=False,
                    )
                    logger.info(f"send_mail returned: {email_sent}")
                    
                    if email_sent:
                        # Log the reminder in database
                        try:
                            # Translate notification message and event based on template type
                            logger.info(f"Template type received: {template_type}")
                            if template_type == "VALIDATION_REQUIRED":
                                notif_message = f"Rappel : veuillez vérifier vos informations pour activer votre compte."
                                event_name = "Rappel - Validation de profil requise"
                                logger.info(f"Using French event name: {event_name}")
                            else:
                                notif_message = f"Rappel envoyé : {subject}"
                                event_name = f"REMINDER_{template_type}"
                                logger.info(f"Using default event name: {event_name}")
                            
                            logger.info(f"About to create notification with event: {event_name}")
                            send_notification(
                                user_id=1,  # Admin user
                                dest_id=client.ID_clt,
                                message=notif_message,
                                categorie="CLIENT",
                                event=event_name,
                                event_id=client.ID_clt
                            )
                            logger.info("Notification logged successfully")
                        except Exception as notif_error:
                            logger.error(f"Failed to log notification: {notif_error}")
                        
                        return JsonResponse({
                            "status": True, 
                            "message": f"Rappel envoyé à {client.raison_sociale}"
                        }, safe=False)
                    else:
                        logger.error("send_mail returned 0 (no emails sent)")
                        return JsonResponse({
                            "status": False, 
                            "message": "Échec de l'envoi de l'email - Aucun email envoyé"
                        }, safe=False, status=500)
                        
                except Exception as email_error:
                    logger.error(f"Email sending failed: {email_error}")
                    logger.error(f"Email error traceback: {traceback.format_exc()}")
                    return JsonResponse({
                        "status": False, 
                        "message": f"Erreur d'envoi email: {str(email_error)}"
                    }, safe=False, status=500)
            else:
                return JsonResponse({
                    "status": False, 
                    "message": "recipient_type doit être 'ESN' ou 'CLIENT'"
                }, safe=False, status=400)
                
        except Exception as e:
            logger.error(f"General error in send_reminder_email: {e}")
            logger.error(f"General error traceback: {traceback.format_exc()}")
            return JsonResponse({
                "status": False, 
                "message": f"Erreur lors de l'envoi du rappel: {str(e)}"
            }, safe=False, status=500)
    
    return JsonResponse({
        "status": False, 
        "message": "Seule la méthode POST est autorisée"
    }, safe=False, status=405)


@csrf_exempt
def debug_bdc_relationships(request):
    """Debug endpoint to check BDC relationships"""
    if request.method == 'GET':
        bdc_id = request.GET.get('bdc_id')
        candidature_id = request.GET.get('candidature_id')
        
        try:
            result = {}
            
            if bdc_id:
                # Check specific BDC relationships
                bdc = Bondecommande.objects.get(id_bdc=bdc_id)
                candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                
                result = {
                    'bdc_id': bdc_id,
                    'bdc_candidature_id': bdc.candidature_id,
                    'candidature_esn_id': candidature.esn_id,
                    'candidature_ao_id': candidature.AO_id,
                    'candidature_consultant_id': candidature.id_consultant,
                    'appel_offre_client_id': appel_offre.client_id,
                    'full_chain': f"BDC {bdc_id} -> Candidature {bdc.candidature_id} -> ESN {candidature.esn_id} -> AO {candidature.AO_id} -> Client {appel_offre.client_id}"
                }
            
            elif candidature_id:
                # Check specific candidature
                candidature = Candidature.objects.get(id_cd=candidature_id)
                result = {
                    'candidature_id': candidature_id,
                    'esn_id': candidature.esn_id,
                    'ao_id': candidature.AO_id,
                    'consultant_id': candidature.id_consultant,
                    'date_candidature': str(candidature.date_candidature),
                    'statut': candidature.statut
                }
            
            return JsonResponse({'success': True, 'data': result}, status=200)
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def get_bdc_by_period(request):
    """
    GET endpoint to retrieve BDC contracts filtered by period for NDF interface.
    
    Query parameters:
    - period: Required filter by period (format: MM_YYYY)
    - consultant_id: Optional filter by consultant ID
    
    Returns BDC contracts where the specified period falls within the BDC date range (date_debut to date_fin).
    """
    if request.method == 'GET':
        try:
            period = request.GET.get('period')
            consultant_id = request.GET.get('consultant_id')
            
            if not period:
                return JsonResponse({
                    "status": False,
                    "message": "period parameter is required (format: MM_YYYY)"
                }, safe=False, status=400)
            
            print(f"DEBUG BDC PERIOD FILTER: period={period}, consultant_id={consultant_id}")
            
            # Validate period format
            try:
                month, year = period.split('_')
                month_int = int(month)
                year_int = int(year)
                
                # Create date range for the entire specified month
                from datetime import date
                import calendar
                
                # First day of the month
                month_start = date(year_int, month_int, 1)
                # Last day of the month
                last_day = calendar.monthrange(year_int, month_int)[1]
                month_end = date(year_int, month_int, last_day)
                
                print(f"DEBUG: Period month range: {month_start} to {month_end}")
                
            except (ValueError, IndexError):
                return JsonResponse({
                    "status": False,
                    "message": "Invalid period format. Use MM_YYYY (e.g., 06_2025)"
                }, safe=False, status=400)
            
            # Start with base query for all BDCs
            bdc_query = Bondecommande.objects.filter()
            
            # Filter BDCs where the period month overlaps with the BDC date range
            # There's an overlap if: month_start <= bdc_date_fin AND month_end >= bdc_date_debut
            bdc_query = bdc_query.filter(
                date_debut__isnull=False,
                date_fin__isnull=False,
                date_debut__lte=month_end,    # BDC starts before or during the month
                date_fin__gte=month_start     # BDC ends after or during the month
            )
            
            print(f"DEBUG: BDCs with date overlap for period {period}: {bdc_query.count()}")
            
            # If consultant_id is provided, filter by consultant through candidature relationship
            if consultant_id:
                print(f"DEBUG: Filtering by consultant_id: {consultant_id}")
                
                # First, check if consultant exists
                try:
                    consultant = Collaborateur.objects.get(ID_collab=consultant_id)
                    print(f"DEBUG: Found consultant: {consultant.Prenom} {consultant.Nom}")
                except Collaborateur.DoesNotExist:
                    print(f"DEBUG: Consultant {consultant_id} not found in database")
                    return JsonResponse({
                        "status": False,
                        "message": f"Consultant {consultant_id} not found"
                    }, safe=False, status=404)
                
                # CORRECTED APPROACH: Get candidature IDs for this consultant, then find BDCs
                candidature_ids = list(
                    Candidature.objects.filter(id_consultant=consultant_id)
                    .values_list('id_cd', flat=True)
                )
                
                print(f"DEBUG: Found {len(candidature_ids)} candidatures for consultant {consultant_id}: {candidature_ids}")
                
                if len(candidature_ids) == 0:
                    print(f"DEBUG: No candidatures found for consultant {consultant_id}")
                    return JsonResponse({
                        "status": True,
                        "total": 0,
                        "data": [],
                        "message": f"No candidatures found for consultant {consultant_id}. Consultant may not have applied to any projects."
                    }, safe=False)
                
                # Get ALL BDCs for this consultant (before period filtering)
                consultant_all_bdcs = Bondecommande.objects.filter(candidature_id__in=candidature_ids)
                print(f"DEBUG: Total BDCs for consultant {consultant_id}: {consultant_all_bdcs.count()}")
                
                # Show details of consultant's BDCs for debugging
                for bdc in consultant_all_bdcs:
                    if not bdc.date_debut or not bdc.date_fin:
                        period_match = "No dates"
                    else:
                        # Check if BDC period overlaps with the requested month
                        overlap = (bdc.date_debut <= month_end and bdc.date_fin >= month_start)
                        period_match = f"BDC range [{bdc.date_debut} to {bdc.date_fin}] overlaps with month [{month_start} to {month_end}]? {overlap}"
                    print(f"DEBUG: BDC {bdc.id_bdc}: {period_match}")
                
                # Now apply period filtering to consultant's BDCs
                bdc_query = bdc_query.filter(candidature_id__in=candidature_ids)
                print(f"DEBUG: BDCs after consultant + period filter: {bdc_query.count()}")
                
                # If no BDCs match the period, provide detailed feedback
                if bdc_query.count() == 0:
                    consultant_bdcs_with_dates = consultant_all_bdcs.filter(
                        date_debut__isnull=False, 
                        date_fin__isnull=False
                    )
                    
                    if consultant_bdcs_with_dates.count() == 0:
                        message = f"Consultant {consultant_id} has {consultant_all_bdcs.count()} BDCs, but none have valid date ranges."
                    else:
                        periods_info = []
                        for bdc in consultant_bdcs_with_dates:
                            periods_info.append(f"BDC {bdc.id_bdc}: {bdc.date_debut} to {bdc.date_fin}")
                        
                        message = f"Consultant {consultant_id} has {consultant_all_bdcs.count()} BDCs, but none match period {period}. Available periods: {'; '.join(periods_info)}"
                    
                    return JsonResponse({
                        "status": True,
                        "total": 0,
                        "data": [],
                        "message": message
                    }, safe=False)
                
            else:
                print(f"DEBUG: No consultant filter applied, total BDCs for period: {bdc_query.count()}")
            
            # If no BDCs found, return empty result
            if not bdc_query.exists():
                return JsonResponse({
                    "status": True,
                    "total": 0,
                    "data": [],
                    "message": f"No BDC contracts found for period {period}" + 
                              (f" and consultant {consultant_id}" if consultant_id else "")
                }, safe=False)
            
            # Serialize BDC data with enriched information
            data = []
            for bdc in bdc_query:
                # Base BDC data
                bdc_data = {
                    "id_bdc": bdc.id_bdc,
                    "numero_bdc": bdc.numero_bdc or f"BDC-{bdc.id_bdc}",
                    "date_debut": bdc.date_debut.isoformat() if bdc.date_debut else None,
                    "date_fin": bdc.date_fin.isoformat() if bdc.date_fin else None,
                    "jours": bdc.jours,
                    "TJM": bdc.TJM,
                    "montant_total": bdc.montant_total,
                    "statut": bdc.statut,
                    "description": bdc.description or "",
                    "candidature_id": bdc.candidature_id
                }
                
                # Enrich with related information
                try:
                    candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
                    
                    # Get AppelOffre info
                    try:
                        appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
                        bdc_data["titre"] = appel_offre.titre
                        bdc_data["project_description"] = appel_offre.description or ""
                        
                        # Get Client info
                        try:
                            client = Client.objects.get(ID_clt=appel_offre.client_id)
                            bdc_data["client_name"] = client.raison_sociale
                            bdc_data["id_client"] = client.ID_clt
                        except Client.DoesNotExist:
                            bdc_data["client_name"] = f"Client ID: {appel_offre.client_id}"
                            bdc_data["id_client"] = appel_offre.client_id
                            
                    except AppelOffre.DoesNotExist:
                        bdc_data["titre"] = f"Projet BDC-{bdc.id_bdc}"
                        bdc_data["project_description"] = ""
                        bdc_data["client_name"] = "Client non trouvé"
                        bdc_data["id_client"] = None
                    
                    # Get ESN info
                    try:
                        esn = ESN.objects.get(ID_ESN=candidature.esn_id)
                        bdc_data["esn_name"] = esn.Raison_sociale
                        bdc_data["id_esn"] = esn.ID_ESN
                    except ESN.DoesNotExist:
                        bdc_data["esn_name"] = f"ESN ID: {candidature.esn_id}"
                        bdc_data["id_esn"] = candidature.esn_id
                    
                    # Get Consultant info
                    if candidature.id_consultant:
                        try:
                            consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
                            bdc_data["consultant_name"] = f"{consultant.Prenom} {consultant.Nom}"
                            bdc_data["id_consultan"] = consultant.ID_collab
                        except Collaborateur.DoesNotExist:
                            bdc_data["consultant_name"] = f"Consultant ID: {candidature.id_consultant}"
                            bdc_data["id_consultan"] = candidature.id_consultant
                    else:
                        bdc_data["consultant_name"] = "Non assigné"
                        bdc_data["id_consultan"] = None
                        
                except Candidature.DoesNotExist:
                    bdc_data["titre"] = f"BDC-{bdc.id_bdc}"
                    bdc_data["project_description"] = ""
                    bdc_data["client_name"] = "Candidature non trouvée"
                    bdc_data["esn_name"] = "ESN non trouvée"
                    bdc_data["consultant_name"] = "Consultant non trouvé"
                    bdc_data["id_client"] = None
                    bdc_data["id_esn"] = None
                    bdc_data["id_consultan"] = None
                
                data.append(bdc_data)
            
            print(f"DEBUG: Final BDC data count: {len(data)}")
            
            return JsonResponse({
                "status": True,
                "total": len(data),
                "period": period,
                "data": data
            }, safe=False)
            
        except Exception as e:
            import traceback
            print(f"ERROR in get_bdc_by_period: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, safe=False, status=500)
    
    return JsonResponse({"status": False, "message": "Method not allowed"}, safe=False, status=405)

# Simplified endpoint for ESN to create projects for consultants
@csrf_exempt
def esn_create_project(request):
    """
    Simplified endpoint for ESN to create projects directly for their consultants
    without going through the full candidature workflow
    """
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            
            # Required fields
            esn_id = int(data.get('esn_id')) if data.get('esn_id') else None
            consultant_id = int(data.get('consultant_id')) if data.get('consultant_id') else None
            project_title = data.get('project_title')
            budget = data.get('budget')  # Budget total du projet
            date_debut = data.get('date_debut')
            date_fin = data.get('date_fin')
            
            # Optional fields
            description = data.get('description', '')
            jours = data.get('jours')
            
            # Calculate TJM from budget and days
            if budget and jours and float(jours) > 0:
                tjm = float(budget) / float(jours)
            else:
                tjm = 0
            
            # Validate required fields
            if not all([esn_id, project_title, budget, date_debut, date_fin]):
                return JsonResponse({
                    "status": False,
                    "message": "Missing required fields: esn_id, project_title, budget, date_debut, date_fin"
                }, status=400)
            
            # Verify ESN exists
            try:
                esn = ESN.objects.get(ID_ESN=esn_id)
            except ESN.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"ESN with ID {esn_id} not found"
                }, status=404)
            
            # Verify consultant exists and belongs to this ESN (only if consultant_id is provided)
            consultant = None
            if consultant_id:
                try:
                    consultant = Collaborateur.objects.get(ID_collab=consultant_id)
                    # Convert both to int for comparison
                    consultant_esn_id = int(consultant.ID_ESN)
                    esn_id_int = int(esn_id)
                    if consultant_esn_id != esn_id_int:
                        return JsonResponse({
                            "status": False,
                            "message": f"Consultant does not belong to this ESN (Consultant ESN: {consultant_esn_id}, Requested ESN: {esn_id_int})"
                        }, status=403)
                except Collaborateur.DoesNotExist:
                    return JsonResponse({
                        "status": False,
                        "message": f"Consultant with ID {consultant_id} not found"
                    }, status=404)
            
            # Create a simplified AppelOffre (project) for record keeping
            appel_offre = AppelOffre.objects.create(
                titre=project_title,
                description=description,
                client_id=esn_id,  # Use ESN as client for simplified workflow
                date_publication=datetime.datetime.now().date(),
                date_limite=date_fin,
                date_debut=date_debut,
                statut='En cours',
                profil='Consultant',
                tjm_min=str(tjm),
                tjm_max=str(tjm),
                jours=jours if jours else None
            )
            
            # If no consultant provided, try to get or create a placeholder consultant
            if not consultant_id or not consultant:
                # Try to find existing placeholder consultant for this ESN
                placeholder_consultant = Collaborateur.objects.filter(
                    ID_ESN=esn_id,
                    email='placeholder@project.esn'
                ).first()
                
                if not placeholder_consultant:
                    # Create a placeholder consultant
                    placeholder_consultant = Collaborateur.objects.create(
                        Nom='Non',
                        Prenom='Assigné',
                        email='placeholder@project.esn',
                        password='placeholder',
                        ID_ESN=esn_id,
                        Consultant=True,
                        Commercial=False,
                        Admin=False,
                        Actif=False
                    )
                
                consultant = placeholder_consultant
                consultant_id = placeholder_consultant.ID_collab
            
            # Create candidature to link consultant to project
            candidature = Candidature.objects.create(
                AO_id=appel_offre.id,
                esn_id=esn_id,
                id_consultant=consultant_id,
                date_candidature=datetime.datetime.now().date(),
                statut='Sélectionnée' if consultant.Actif else 'En attente',
                tjm=tjm,
                date_disponibilite=date_debut,
                responsable_compte=f"{consultant.Nom} {consultant.Prenom}",
                commentaire=f"Project created by ESN for {consultant.Nom} {consultant.Prenom}"
            )
            
            # Generate BDC number
            from .views import generate_bdc_numero
            bdc_numero = generate_bdc_numero(esn_id, esn_id)
            
            # Use budget as montant_total
            montant_total = float(budget) if budget else 0
            
            # Create Bondecommande (the actual project/contract)
            bdc = Bondecommande.objects.create(
                candidature_id=candidature.id_cd,
                numero_bdc=bdc_numero,
                montant_total=montant_total,
                statut='actif',
                description=description,
                TJM=tjm,
                date_debut=date_debut,
                date_fin=date_fin,
                jours=jours or 0
            )
            
            consultant_name = f"{consultant.Nom} {consultant.Prenom}" if consultant.Actif else "No consultant assigned"
            
            # Return success response
            return JsonResponse({
                "status": True,
                "message": "Project created successfully",
                "data": {
                    "bdc_id": bdc.id_bdc,
                    "numero_bdc": bdc.numero_bdc,
                    "project_title": project_title,
                    "consultant_name": consultant_name,
                    "date_debut": str(bdc.date_debut),
                    "date_fin": str(bdc.date_fin)
                }
            }, status=201)
            
        except Exception as e:
            import traceback
            print(f"ERROR in esn_create_project: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, status=500)
    
    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)


@csrf_exempt
def esn_update_project_consultants(request, bdc_id):
    """
    Update project information and consultants linked to a project (BDC)
    Allows editing project details and adding or removing consultant assignments
    """
    if request.method == 'PUT':
        try:
            data = JSONParser().parse(request)
            esn_id = int(data.get('esn_id')) if data.get('esn_id') else None
            
            # Validate inputs
            if not esn_id:
                return JsonResponse({
                    "status": False,
                    "message": "Missing required field: esn_id"
                }, status=400)
            
            # Get the BDC
            try:
                bdc = Bondecommande.objects.get(id_bdc=bdc_id)
            except Bondecommande.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"BDC with ID {bdc_id} not found"
                }, status=404)
            
            # Get the candidature linked to this BDC
            try:
                candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
            except Candidature.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"Candidature for BDC {bdc_id} not found"
                }, status=404)
            
            # Verify ESN owns this candidature
            if int(candidature.esn_id) != int(esn_id):
                return JsonResponse({
                    "status": False,
                    "message": "This project does not belong to your ESN"
                }, status=403)
            
            # Get the AppelOffre
            try:
                appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
            except AppelOffre.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": "Project (AppelOffre) not found"
                }, status=404)
            
            # Update project information if provided
            if 'project_title' in data:
                appel_offre.titre = data['project_title']
            if 'description' in data:
                appel_offre.description = data['description']
                bdc.description = data['description']
            if 'budget' in data:
                budget_value = float(data['budget'])
                bdc.montant_total = budget_value
                # Calculate TJM from budget and jours
                jours_value = int(data['jours']) if 'jours' in data else (bdc.jours or 1)
                tjm_value = budget_value / jours_value if jours_value > 0 else 0
                candidature.tjm = tjm_value
                bdc.TJM = tjm_value
                appel_offre.tjm_min = str(tjm_value)
                appel_offre.tjm_max = str(tjm_value)
            if 'date_debut' in data:
                bdc.date_debut = data['date_debut']
                appel_offre.date_debut = data['date_debut']
                candidature.date_disponibilite = data['date_debut']
            if 'date_fin' in data:
                bdc.date_fin = data['date_fin']
                appel_offre.date_limite = data['date_fin']
            if 'jours' in data:
                bdc.jours = int(data['jours'])
                appel_offre.jours = int(data['jours'])
                # Recalculate TJM if budget exists
                if 'budget' in data:
                    budget_value = float(data['budget'])
                    jours_value = int(data['jours'])
                    tjm_value = budget_value / jours_value if jours_value > 0 else 0
                    candidature.tjm = tjm_value
                    bdc.TJM = tjm_value
            if 'status' in data:
                bdc.statut = data['status']
                appel_offre.statut = data['status']  # Fixed: use 'statut' not 'status'
            
            # Update consultant if provided
            consultant_ids = data.get('consultant_ids', [])
            if consultant_ids and len(consultant_ids) > 0:
                # Use the first consultant as the primary consultant for this BDC
                primary_consultant_id = int(consultant_ids[0])
                
                # Verify consultant exists and belongs to this ESN
                try:
                    consultant = Collaborateur.objects.get(ID_collab=primary_consultant_id)
                    if int(consultant.ID_ESN) != int(esn_id):
                        return JsonResponse({
                            "status": False,
                            "message": f"Consultant {primary_consultant_id} does not belong to your ESN"
                        }, status=403)
                except Collaborateur.DoesNotExist:
                    return JsonResponse({
                        "status": False,
                        "message": f"Consultant with ID {primary_consultant_id} not found"
                    }, status=404)
                
                # Update the candidature with the new primary consultant
                candidature.id_consultant = primary_consultant_id
                candidature.responsable_compte = f"{consultant.Nom} {consultant.Prenom}"
            
            # Save all changes
            appel_offre.save()
            candidature.save()
            bdc.save()
            
            return JsonResponse({
                "status": True,
                "message": "Project updated successfully",
                "data": {
                    "bdc_id": bdc.id_bdc,
                    "consultant_id": candidature.id_consultant,
                    "project_title": appel_offre.titre,
                    "tjm": float(bdc.TJM),
                    "montant_total": float(bdc.montant_total)
                }
            }, status=200)
            
        except Exception as e:
            import traceback
            print(f"ERROR in esn_update_project_consultants: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, status=500)
    
    elif request.method == 'GET':
        try:
            # Get the BDC
            try:
                bdc = Bondecommande.objects.get(id_bdc=bdc_id)
            except Bondecommande.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"BDC with ID {bdc_id} not found"
                }, status=404)
            
            # Get the candidature
            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
            
            # Get the AppelOffre
            appel_offre = AppelOffre.objects.get(id=candidature.AO_id)
            
            # Get consultant details
            consultant = Collaborateur.objects.get(ID_collab=candidature.id_consultant)
            
            return JsonResponse({
                "status": True,
                "data": {
                    "id_bdc": bdc.id_bdc,
                    "project_title": appel_offre.titre,
                    "description": bdc.description or appel_offre.description or '',
                    "consultant_id": candidature.id_consultant,
                    "consultant_name": f"{consultant.Nom} {consultant.Prenom}",
                    "tjm": float(bdc.TJM),
                    "budget": float(bdc.montant_total),
                    "date_debut": str(bdc.date_debut) if bdc.date_debut else None,
                    "date_fin": str(bdc.date_fin) if bdc.date_fin else None,
                    "jours": bdc.jours,
                    "montant_total": float(bdc.montant_total),
                    "status": bdc.statut,
                    "esn_id": candidature.esn_id
                }
            }, status=200)
            
        except Exception as e:
            import traceback
            print(f"ERROR in esn_update_project_consultants GET: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, status=500)
    
    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)


@csrf_exempt
def esn_project_consultants(request, bdc_id):
    """
    Manage multiple consultants for a project
    GET: List all consultants assigned to a project
    POST: Add a consultant to a project
    DELETE: Remove a consultant from a project
    """
    if request.method == 'GET':
        try:
            # Get the BDC
            try:
                bdc = Bondecommande.objects.get(id_bdc=bdc_id)
            except Bondecommande.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"BDC with ID {bdc_id} not found"
                }, status=404)
            
            # Get the main candidature
            candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
            ao_id = candidature.AO_id
            esn_id = candidature.esn_id
            
            # Get BDC's default jours and TJM for primary consultant fallback
            bdc_jours = bdc.jours if bdc.jours else None
            bdc_tjm = float(bdc.TJM) if bdc.TJM else None
            
            # Get all candidatures for this AppelOffre from this ESN
            all_candidatures = Candidature.objects.filter(
                AO_id=ao_id,
                esn_id=esn_id
            )
            
            consultants_list = []
            for cand in all_candidatures:
                try:
                    consultant = Collaborateur.objects.get(ID_collab=cand.id_consultant)
                    # Parse role from commentaire field (stored as "role:RoleName" or in comment)
                    role = None
                    jours = None
                    if cand.commentaire:
                        import re
                        # Try to extract role from commentaire
                        role_match = re.search(r'role:([^|]+)', cand.commentaire)
                        if role_match:
                            role = role_match.group(1).strip()
                        # Try to extract jours from commentaire
                        jours_match = re.search(r'jours:(\d+)', cand.commentaire)
                        if jours_match:
                            jours = int(jours_match.group(1))
                    
                    # Check if this is the primary consultant
                    is_primary = cand.id_cd == bdc.candidature_id
                    
                    # Get TJM - from candidature or BDC for primary
                    tjm = float(cand.tjm) if cand.tjm else None
                    if tjm is None and is_primary:
                        tjm = bdc_tjm
                    
                    # Get jours - from commentaire or BDC for primary
                    if jours is None and is_primary:
                        jours = bdc_jours
                    
                    consultants_list.append({
                        'id_consultant': consultant.ID_collab,
                        'nom': consultant.Nom,
                        'prenom': consultant.Prenom,
                        'email': consultant.email,
                        'candidature_id': cand.id_cd,
                        'is_primary': is_primary,
                        'tjm': tjm,
                        'role': role,
                        'jours': jours
                    })
                except Collaborateur.DoesNotExist:
                    continue
            
            return JsonResponse({
                "status": True,
                "data": consultants_list,
                "total": len(consultants_list)
            }, status=200)
            
        except Exception as e:
            import traceback
            print(f"ERROR in esn_project_consultants GET: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, status=500)
    
    elif request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            esn_id = int(data.get('esn_id')) if data.get('esn_id') else None
            consultant_id = int(data.get('consultant_id')) if data.get('consultant_id') else None
            tjm = data.get('tjm')  # TJM specific to this consultant on this project
            role = data.get('role')  # Role on this project
            jours = data.get('jours')  # Number of days allocated
            
            if not esn_id or not consultant_id:
                return JsonResponse({
                    "status": False,
                    "message": "Missing required fields: esn_id, consultant_id"
                }, status=400)
            
            # Get the BDC
            try:
                bdc = Bondecommande.objects.get(id_bdc=bdc_id)
            except Bondecommande.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"BDC with ID {bdc_id} not found"
                }, status=404)
            
            # Get the main candidature and AppelOffre
            main_candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
            
            # Verify ESN owns this project
            if int(main_candidature.esn_id) != int(esn_id):
                return JsonResponse({
                    "status": False,
                    "message": "This project does not belong to your ESN"
                }, status=403)
            
            # Verify consultant exists and belongs to this ESN
            try:
                consultant = Collaborateur.objects.get(ID_collab=consultant_id)
                if int(consultant.ID_ESN) != int(esn_id):
                    return JsonResponse({
                        "status": False,
                        "message": f"Consultant does not belong to your ESN"
                    }, status=403)
            except Collaborateur.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"Consultant with ID {consultant_id} not found"
                }, status=404)
            
            # Check if consultant is already assigned
            existing = Candidature.objects.filter(
                AO_id=main_candidature.AO_id,
                esn_id=esn_id,
                id_consultant=consultant_id
            ).first()
            
            if existing:
                return JsonResponse({
                    "status": False,
                    "message": "Consultant is already assigned to this project"
                }, status=400)
            
            # Create new candidature for this consultant
            # Build commentaire with role and jours info for later retrieval
            commentaire_parts = ["Additional consultant assigned to project"]
            if role:
                commentaire_parts.append(f"role:{role}")
            if jours:
                commentaire_parts.append(f"jours:{jours}")
            
            new_candidature = Candidature.objects.create(
                AO_id=main_candidature.AO_id,
                esn_id=esn_id,
                id_consultant=consultant_id,
                date_candidature=datetime.datetime.now().date(),
                statut='Sélectionnée',
                tjm=tjm if tjm else main_candidature.tjm,
                date_disponibilite=main_candidature.date_disponibilite,
                responsable_compte=f"{consultant.Nom} {consultant.Prenom}",
                commentaire="|".join(commentaire_parts)
            )
            
            return JsonResponse({
                "status": True,
                "message": "Consultant added to project successfully",
                "data": {
                    "candidature_id": new_candidature.id_cd,
                    "consultant_id": consultant_id,
                    "consultant_name": f"{consultant.Nom} {consultant.Prenom}",
                    "tjm": float(new_candidature.tjm) if new_candidature.tjm else None,
                    "role": role,
                    "jours": jours
                }
            }, status=201)
            
        except Exception as e:
            import traceback
            print(f"ERROR in esn_project_consultants POST: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, status=500)
    
    elif request.method == 'DELETE':
        try:
            data = JSONParser().parse(request)
            esn_id = int(data.get('esn_id')) if data.get('esn_id') else None
            consultant_id = int(data.get('consultant_id')) if data.get('consultant_id') else None
            
            if not esn_id or not consultant_id:
                return JsonResponse({
                    "status": False,
                    "message": "Missing required fields: esn_id, consultant_id"
                }, status=400)
            
            # Get the BDC
            try:
                bdc = Bondecommande.objects.get(id_bdc=bdc_id)
            except Bondecommande.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": f"BDC with ID {bdc_id} not found"
                }, status=404)
            
            # Get the main candidature
            main_candidature = Candidature.objects.get(id_cd=bdc.candidature_id)
            
            # Verify ESN owns this project
            if int(main_candidature.esn_id) != int(esn_id):
                return JsonResponse({
                    "status": False,
                    "message": "This project does not belong to your ESN"
                }, status=403)
            
            # Prevent removing the primary consultant
            if int(main_candidature.id_consultant) == int(consultant_id):
                return JsonResponse({
                    "status": False,
                    "message": "Cannot remove the primary consultant. Assign a different primary consultant first."
                }, status=400)
            
            # Find and delete the candidature for this consultant
            candidature_to_delete = Candidature.objects.filter(
                AO_id=main_candidature.AO_id,
                esn_id=esn_id,
                id_consultant=consultant_id
            ).first()
            
            if not candidature_to_delete:
                return JsonResponse({
                    "status": False,
                    "message": "Consultant is not assigned to this project"
                }, status=404)
            
            candidature_to_delete.delete()
            
            return JsonResponse({
                "status": True,
                "message": "Consultant removed from project successfully"
            }, status=200)
            
        except Exception as e:
            import traceback
            print(f"ERROR in esn_project_consultants DELETE: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, status=500)
    
    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)
