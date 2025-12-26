#!/usr/bin/env python3
"""
Script pour explorer la base de données et trouver les vrais IDs
"""

import requests
import json

API_BASE_URL = "http://localhost:8000/api"

def get_bdc_list():
    """Récupère la liste des BDC"""
    try:
        response = requests.get(f"{API_BASE_URL}/Bondecommande/")
        if response.status_code == 200:
            data = response.json()
            bdcs = data.get('data', [])
            print(f"BDC trouvés: {len(bdcs)}")
            
            if bdcs:
                print("\nPremiers BDC:")
                for i, bdc in enumerate(bdcs[:3]):
                    print(f"{i+1}. ID: {bdc.get('id_bdc')}, Statut: {bdc.get('statut')}, Candidature: {bdc.get('candidature_id')}")
                return bdcs
            else:
                print("Aucun BDC trouvé")
                return []
        else:
            print(f"Erreur récupération BDC: {response.status_code}")
            return []
    except Exception as e:
        print(f"Erreur: {e}")
        return []

def get_esn_list():
    """Récupère la liste des ESN"""
    try:
        response = requests.get(f"{API_BASE_URL}/ESN/")
        if response.status_code == 200:
            data = response.json()
            esns = data.get('data', [])
            print(f"\nESN trouvés: {len(esns)}")
            
            if esns:
                print("\nPremiers ESN:")
                for i, esn in enumerate(esns[:3]):
                    print(f"{i+1}. ID: {esn.get('ID_ESN')}, Nom: {esn.get('Raison_sociale')}")
                return esns
            else:
                print("Aucun ESN trouvé")
                return []
        else:
            print(f"Erreur récupération ESN: {response.status_code}")
            return []
    except Exception as e:
        print(f"Erreur: {e}")
        return []

def get_candidatures():
    """Récupère la liste des candidatures"""
    try:
        response = requests.get(f"{API_BASE_URL}/Candidature/")
        if response.status_code == 200:
            data = response.json()
            candidatures = data.get('data', [])
            print(f"\nCandidatures trouvées: {len(candidatures)}")
            
            if candidatures:
                print("\nPremières candidatures:")
                for i, cand in enumerate(candidatures[:3]):
                    print(f"{i+1}. ID: {cand.get('id_cd')}, ESN: {cand.get('esn_id')}, AO: {cand.get('AO_id')}")
                return candidatures
            else:
                print("Aucune candidature trouvée")
                return []
        else:
            print(f"Erreur récupération candidatures: {response.status_code}")
            return []
    except Exception as e:
        print(f"Erreur: {e}")
        return []

def test_with_real_ids():
    """Test avec de vrais IDs"""
    print("\n=== Recherche des vrais IDs ===")
    
    bdcs = get_bdc_list()
    esns = get_esn_list() 
    candidatures = get_candidatures()
    
    if bdcs and esns:
        # Prendre le premier BDC et ESN disponibles
        first_bdc = bdcs[0]
        first_esn = esns[0]
        
        bdc_id = first_bdc.get('id_bdc')
        esn_id = first_esn.get('ID_ESN')
        
        print(f"\n=== Test avec BDC ID: {bdc_id}, ESN ID: {esn_id} ===")
        
        # Test de notification
        try:
            response = requests.post(
                f"{API_BASE_URL}/notify_admin_verify_bon_de_commande/",
                json={
                    "bon_de_commande_id": bdc_id,
                    "status": "pending_esn"
                },
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"Statut notification: {response.status_code}")
            print(f"Réponse: {response.text}")
            
        except Exception as e:
            print(f"Erreur test notification: {e}")
        
        # Test de récupération des notifications pour cet ESN
        try:
            response = requests.get(f"{API_BASE_URL}/getNotifications/?type=ESN&id={esn_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"\nNotifications pour ESN {esn_id}: {data.get('total', 0)}")
                
                notifications = data.get('data', [])
                if notifications:
                    print("Dernières notifications:")
                    for notif in notifications[-3:]:
                        print(f"- {notif.get('event')}: {notif.get('message')[:50]}...")
            else:
                print(f"Erreur récupération notifications: {response.status_code}")
                
        except Exception as e:
            print(f"Erreur récupération notifications: {e}")

if __name__ == "__main__":
    print("=== Exploration de la base de données ===")
    test_with_real_ids()
