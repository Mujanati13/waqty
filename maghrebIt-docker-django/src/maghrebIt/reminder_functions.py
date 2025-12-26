
@csrf_exempt  
def send_client_reminder(request):
    """Envoie un rappel à un client pour compléter ses documents"""
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
            
            # Create reminder message for client
            profile_link = "/interface-cl?menu=Mon-Profil"
            client_message = (
                f"Bonjour {client.nom_entreprise}, "
                f"Nous avons remarqué que votre profil client nécessite quelques informations supplémentaires. "
                f"Pour bénéficier pleinement de nos services, nous vous encourageons à : "
                f"<br/>• Compléter toutes les informations de votre profil "
                f"<br/>• Télécharger les documents requis (KBIS, RIB, etc.) "
                f"<br/>• Vérifier vos informations de contact "
                f"<br/><br/>"
                f"<a href='{profile_link}' style='color: #1890ff; text-decoration: underline;'>Compléter mon profil maintenant</a>"
                f"<br/><br/>L'équipe MAGHREB CONNECT IT"
            )
            
            send_notification(
                user_id=1, dest_id=client.ID_clt, message=client_message,
                categorie="Admin", event="Rappel - Compléter le Profil", event_id=client.ID_clt
            )
            
            return JsonResponse({"status": True, "message": f"Rappel envoyé à {client.nom_entreprise}"}, safe=False)
            
        except Exception as e:
            return JsonResponse({"status": False, "message": f"Erreur: {str(e)}"}, safe=False, status=500)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False, status=405)


@csrf_exempt
def send_esn_reminder(request):
    """Envoie un rappel à une ESN pour compléter ses documents"""  
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
            
            # Create reminder message for ESN
            profile_link = "/interface-en?menu=Profile"
            esn_message = (
                f"Bonjour {esn.Raison_sociale}, "
                f"Nous avons remarqué que votre profil ESN nécessite quelques informations supplémentaires. "
                f"Pour bénéficier pleinement de nos services, nous vous encourageons à : "
                f"<br/>• Compléter toutes les informations de votre profil "
                f"<br/>• Télécharger les documents requis (KBIS, RIB, attestations, etc.) "
                f"<br/>• Vérifier vos informations de contact et bancaires "
                f"<br/>• Ajouter vos collaborateurs si nécessaire "
                f"<br/><br/>"
                f"<a href='{profile_link}' style='color: #1890ff; text-decoration: underline;'>Compléter mon profil maintenant</a>"
                f"<br/><br/>L'équipe MAGHREB CONNECT IT"
            )
            
            send_notification(
                user_id=1, dest_id=esn.ID_ESN, message=esn_message,
                categorie="Admin", event="Rappel - Compléter le Profil", event_id=esn.ID_ESN
            )
            
            return JsonResponse({"status": True, "message": f"Rappel envoyé à {esn.Raison_sociale}"}, safe=False)
            
        except Exception as e:
            return JsonResponse({"status": False, "message": f"Erreur: {str(e)}"}, safe=False, status=500)
    
    return JsonResponse({"status": False, "message": "Seule la méthode POST est autorisée"}, safe=False, status=405)
