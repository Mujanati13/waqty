# Test Script for Commercial NDF Filtering API
# This script helps verify that the API correctly filters NDFs based on Candidature table

"""
Test the commercial NDF filtering endpoint:
http://localhost:8000/api/ndf-consultant-view/?responsable_id=58&view_type=validation&_t=1759322483297&limit=10&offset=0&period=10_2025
"""

# Run this in Django shell: python manage.py shell

from maghrebIt.models import Candidature, NDF_CONSULTANT, Collaborateur

# Set your commercial ID
commercial_id = 58

print("=" * 80)
print(f"TESTING COMMERCIAL NDF FILTERING FOR COMMERCIAL ID: {commercial_id}")
print("=" * 80)

# Step 1: Check if the commercial exists
print(f"\n1. Checking if commercial ID {commercial_id} exists...")
try:
    commercial = Collaborateur.objects.get(ID_collab=commercial_id)
    print(f"   ✅ Found: {commercial.Prenom} {commercial.Nom}")
    print(f"   - Email: {commercial.email}")
    print(f"   - ESN ID: {commercial.ID_ESN}")
    print(f"   - Is Commercial: {commercial.Commercial}")
except Collaborateur.DoesNotExist:
    print(f"   ❌ Commercial with ID {commercial_id} not found!")
    exit()

# Step 2: Find candidatures for this commercial
print(f"\n2. Finding candidatures for commercial ID {commercial_id}...")
candidatures_commercial = Candidature.objects.filter(commercial_id=commercial_id)
print(f"   Found {candidatures_commercial.count()} candidature(s) where this commercial is assigned")

if candidatures_commercial.count() == 0:
    print(f"   ⚠️  WARNING: No candidatures found with commercial_id={commercial_id}")
    print(f"   This means the API will return 0 NDFs for this commercial")
    print(f"\n   To fix this, you need to:")
    print(f"   1. Assign this commercial to candidatures in the Candidature table")
    print(f"   2. Run: Candidature.objects.filter(id_cd=<candidature_id>).update(commercial_id={commercial_id})")
else:
    for i, cand in enumerate(candidatures_commercial[:5], 1):  # Show first 5
        print(f"   {i}. Candidature ID: {cand.id_cd}, AO_id: {cand.AO_id}")
        print(f"      - Consultant ID: {cand.id_consultant}")
        print(f"      - ESN ID: {cand.esn_id}")
        print(f"      - Status: {cand.statut}")

# Step 3: Get AO_ids for this commercial
print(f"\n3. Getting Appel d'Offres (AO) IDs where commercial is assigned...")
ao_ids = list(Candidature.objects.filter(
    commercial_id=commercial_id
).values_list('AO_id', flat=True).distinct())
print(f"   Found {len(ao_ids)} unique AO_id(s): {ao_ids}")

# Step 4: Find ALL consultants in these same AO_ids
print(f"\n4. Finding ALL consultants who have candidatures in these same AO_ids...")
if ao_ids:
    all_candidatures_in_aos = Candidature.objects.filter(AO_id__in=ao_ids)
    print(f"   Total candidatures in these AOs: {all_candidatures_in_aos.count()}")
    
    consultant_ids = list(all_candidatures_in_aos.values_list('id_consultant', flat=True).distinct())
    print(f"   Unique consultants in these AOs: {len(consultant_ids)}")
    print(f"   Consultant IDs: {consultant_ids}")
else:
    consultant_ids = []
    print(f"   No AO_ids found, so no consultants to show")

print(f"   Found {len(consultant_ids)} unique consultant(s): {consultant_ids}")

# Step 4: Check each consultant
if consultant_ids:
    print(f"\n4. Consultant details:")
    for cons_id in consultant_ids:
        try:
            consultant = Collaborateur.objects.get(ID_collab=cons_id)
            print(f"   - ID {cons_id}: {consultant.Prenom} {consultant.Nom} ({consultant.email})")
        except Collaborateur.DoesNotExist:
            print(f"   - ID {cons_id}: ❌ Consultant not found in Collaborateur table!")

# Step 5: Find NDFs for these consultants
print(f"\n5. Finding NDFs for these consultants...")
if consultant_ids:
    ndfs = NDF_CONSULTANT.objects.filter(id_consultan__in=consultant_ids)
    print(f"   Total NDFs found: {ndfs.count()}")
    
    # Filter by period if needed
    period = "10_2025"
    ndfs_period = ndfs.filter(période=period)
    print(f"   NDFs for period {period}: {ndfs_period.count()}")
    
    # Show some examples
    if ndfs_period.exists():
        print(f"\n   Example NDFs:")
        for i, ndf in enumerate(ndfs_period[:5], 1):
            consultant = Collaborateur.objects.get(ID_collab=ndf.id_consultan)
            print(f"   {i}. NDF ID: {ndf.id_ndf}")
            print(f"      - Consultant: {consultant.Prenom} {consultant.Nom} (ID: {ndf.id_consultan})")
            print(f"      - Period: {ndf.période}, Day: {ndf.jour}")
            print(f"      - Amount TTC: {ndf.montant_ttc} {ndf.devise}")
            print(f"      - Status: {ndf.statut}")
            print(f"      - Description: {ndf.description[:50]}..." if len(ndf.description or '') > 50 else f"      - Description: {ndf.description}")
    else:
        print(f"   ⚠️  No NDFs found for period {period}")
        print(f"   But {ndfs.count()} NDFs exist for other periods")
else:
    print(f"   ⚠️  No consultant IDs found, so no NDFs to show")

# Step 6: Summary
print(f"\n" + "=" * 80)
print(f"SUMMARY")
print("=" * 80)
print(f"Commercial ID: {commercial_id}")
print(f"Candidatures for commercial: {candidatures_commercial.count()}")
print(f"AO_ids where commercial is involved: {len(ao_ids)}")
print(f"Total consultants in these AO_ids: {len(consultant_ids)}")
if consultant_ids:
    total_ndfs = NDF_CONSULTANT.objects.filter(id_consultan__in=consultant_ids).count()
    period_ndfs = NDF_CONSULTANT.objects.filter(id_consultan__in=consultant_ids, période="10_2025").count()
    print(f"Total NDFs (all periods): {total_ndfs}")
    print(f"NDFs for October 2025: {period_ndfs}")
else:
    print(f"Total NDFs: 0 (no consultants assigned)")

print(f"\n" + "=" * 80)
print(f"API ENDPOINT TEST")
print("=" * 80)
print(f"URL: http://localhost:8000/api/ndf-consultant-view/?responsable_id={commercial_id}&view_type=validation&limit=10&offset=0&period=10_2025")
print(f"\nExpected result:")
if consultant_ids:
    period_count = NDF_CONSULTANT.objects.filter(id_consultan__in=consultant_ids, période="10_2025").count()
    print(f"   - Should return {period_count} NDF(s) for October 2025")
    print(f"   - Consultants: {consultant_ids}")
else:
    print(f"   - Should return 0 NDFs (no candidatures with this commercial)")

print("\n" + "=" * 80)

# Additional: Check if there are candidatures without commercial_id
print(f"\nBONUS: Checking for candidatures without commercial_id...")
no_commercial = Candidature.objects.filter(commercial_id__isnull=True)
print(f"Found {no_commercial.count()} candidature(s) without commercial_id")
if no_commercial.count() > 0:
    print(f"⚠️  These candidatures need to be assigned to a commercial:")
    for cand in no_commercial[:10]:  # Show first 10
        try:
            consultant = Collaborateur.objects.get(ID_collab=cand.id_consultant)
            print(f"   - Candidature {cand.id_cd}: Consultant {consultant.Prenom} {consultant.Nom} (ID: {cand.id_consultant})")
        except:
            print(f"   - Candidature {cand.id_cd}: Consultant ID {cand.id_consultant}")
