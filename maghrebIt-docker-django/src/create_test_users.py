import os
import django
import hashlib

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maghrebIt_backend.settings')
django.setup()

from maghrebIt.models import ESN, Collaborateur

def hash_password(password):
    """Hash password using SHA1 (legacy system)"""
    return hashlib.sha1(password.encode()).hexdigest()

def create_test_data():
    # Test credentials
    esn_email = "esn@test.com"
    esn_password = "esn123"
    
    consultant_email = "consultant@test.com"
    consultant_password = "consultant123"
    
    # Create or update ESN
    esn, created = ESN.objects.update_or_create(
        mail_Contact=esn_email,
        defaults={
            'Raison_sociale': 'Test ESN Company',
            'password': hash_password(esn_password),
            'Statut': 'actif',
            'Adresse': '123 Test Street',
            'CP': '75001',
            'Ville': 'Paris',
            'Tel_Contact': '+33612345678',
            'Pays': 'France',
            'responsible': 'Manager Test',
        }
    )
    
    if created:
        print(f"✓ Created ESN: {esn_email}")
    else:
        print(f"✓ Updated ESN: {esn_email}")
    
    print(f"  Email: {esn_email}")
    print(f"  Password: {esn_password}")
    print(f"  ESN ID: {esn.ID_ESN}")
    print()
    
    # Create or update Consultant
    consultant, created = Collaborateur.objects.update_or_create(
        email=consultant_email,
        defaults={
            'ID_ESN': esn.ID_ESN,
            'Nom': 'Dupont',
            'Prenom': 'Jean',
            'password': hash_password(consultant_password),
            'Poste': 'Développeur Full Stack',
            'Consultant': True,
            'Commercial': False,
            'Admin': False,
            'Actif': True,
            'Date_naissance': '1990-01-15',
        }
    )
    
    if created:
        print(f"✓ Created Consultant: {consultant_email}")
    else:
        print(f"✓ Updated Consultant: {consultant_email}")
    
    print(f"  Email: {consultant_email}")
    print(f"  Password: {consultant_password}")
    print(f"  Consultant ID: {consultant.ID_collab}")
    print(f"  Linked to ESN ID: {consultant.ID_ESN}")
    print()
    
    print("=" * 50)
    print("Test accounts ready!")
    print("=" * 50)
    print()
    print("Login as ESN:")
    print(f"  URL: http://localhost:5173/login")
    print(f"  Email: {esn_email}")
    print(f"  Password: {esn_password}")
    print()
    print("Login as Consultant:")
    print(f"  URL: http://localhost:5173/login")
    print(f"  Email: {consultant_email}")
    print(f"  Password: {consultant_password}")

if __name__ == '__main__':
    create_test_data()
