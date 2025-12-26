"""
DEBUG SCRIPT: Check why consultants 59, 56, 54 appear for commercial 58
Run this in Django shell: python manage.py shell < debug_commercial_58.py
"""

from maghrebIt.models import Candidature, Collaborateur, NDF_CONSULTANT

commercial_id = 58
consultant_ids_in_response = [59, 56, 54]

print("=" * 80)
print(f"DEBUGGING COMMERCIAL {commercial_id} NDF FILTERING")
print("=" * 80)

# Step 1: Check if commercial 58 exists and has candidatures
print(f"\n1. Checking Commercial ID {commercial_id}...")
try:
    commercial = Collaborateur.objects.get(ID_collab=commercial_id)
    print(f"   ✅ Found: {commercial.Prenom} {commercial.Nom} ({commercial.email})")
    print(f"   - Is Commercial: {commercial.Commercial}")
except Collaborateur.DoesNotExist:
    print(f"   ❌ Commercial not found!")

# Step 2: Check candidatures for commercial 58
print(f"\n2. Candidatures WHERE commercial_id = {commercial_id}:")
candidatures_commercial = Candidature.objects.filter(commercial_id=commercial_id)
print(f"   Found: {candidatures_commercial.count()} candidature(s)")

if candidatures_commercial.count() > 0:
    print(f"   Details:")
    for cand in candidatures_commercial:
        print(f"   - Candidature {cand.id_cd}: AO_id={cand.AO_id}, Consultant={cand.id_consultant}, Status={cand.statut}")
else:
    print(f"   ⚠️  NO CANDIDATURES with commercial_id={commercial_id}")
    print(f"   This is the problem! Commercial has no assigned candidatures.")

# Step 3: Get AO_ids for commercial 58
print(f"\n3. AO_ids from commercial's candidatures:")
ao_ids = list(Candidature.objects.filter(commercial_id=commercial_id).values_list('AO_id', flat=True).distinct())
print(f"   AO_ids: {ao_ids}")

# Step 4: Check consultants in these AO_ids
print(f"\n4. Consultants in AO_ids {ao_ids}:")
if ao_ids:
    consultants_in_aos = list(Candidature.objects.filter(AO_id__in=ao_ids).values_list('id_consultant', flat=True).distinct())
    print(f"   Consultant IDs: {consultants_in_aos}")
    
    print(f"\n   Consultant details:")
    for cons_id in consultants_in_aos:
        try:
            consultant = Collaborateur.objects.get(ID_collab=cons_id)
            print(f"   - ID {cons_id}: {consultant.Prenom} {consultant.Nom} ({consultant.email})")
        except:
            print(f"   - ID {cons_id}: Not found")
else:
    print(f"   No AO_ids, so no consultants")

# Step 5: Check the consultants that ARE appearing (59, 56, 54)
print(f"\n5. ACTUAL CONSULTANTS IN API RESPONSE: {consultant_ids_in_response}")
print(f"   Checking their candidatures:")

for cons_id in consultant_ids_in_response:
    print(f"\n   Consultant ID {cons_id}:")
    try:
        consultant = Collaborateur.objects.get(ID_collab=cons_id)
        print(f"   - Name: {consultant.Prenom} {consultant.Nom}")
        print(f"   - Email: {consultant.email}")
    except:
        print(f"   - Not found in Collaborateur table")
    
    # Check their candidatures
    candidatures = Candidature.objects.filter(id_consultant=cons_id)
    print(f"   - Has {candidatures.count()} candidature(s):")
    for cand in candidatures:
        print(f"     * Candidature {cand.id_cd}: AO_id={cand.AO_id}, commercial_id={cand.commercial_id}, Status={cand.statut}")

# Step 6: Check if there's ANY overlap
print(f"\n6. CHECKING FOR OVERLAP:")
print(f"   Commercial {commercial_id} AO_ids: {ao_ids}")

if ao_ids:
    for cons_id in consultant_ids_in_response:
        consultant_ao_ids = list(Candidature.objects.filter(id_consultant=cons_id).values_list('AO_id', flat=True))
        overlap = set(ao_ids) & set(consultant_ao_ids)
        print(f"   Consultant {cons_id} AO_ids: {consultant_ao_ids}")
        print(f"   Overlap with commercial: {list(overlap) if overlap else 'NONE'}")
        if not overlap:
            print(f"   ⚠️  WARNING: Consultant {cons_id} has NO common AO_ids with commercial!")

# Step 7: Check ALL candidatures (maybe commercial_id is NULL or wrong)
print(f"\n7. ALL CANDIDATURES IN DATABASE:")
all_candidatures = Candidature.objects.all()
print(f"   Total candidatures: {all_candidatures.count()}")

commercial_assigned = Candidature.objects.filter(commercial_id__isnull=False).count()
commercial_null = Candidature.objects.filter(commercial_id__isnull=True).count()

print(f"   - With commercial_id assigned: {commercial_assigned}")
print(f"   - With commercial_id NULL: {commercial_null}")

# Check if commercial 58 appears anywhere
candidatures_58 = Candidature.objects.filter(commercial_id=58)
print(f"   - Candidatures with commercial_id=58: {candidatures_58.count()}")

# Step 8: HYPOTHESIS - Maybe ALL candidatures have NULL commercial_id
print(f"\n8. HYPOTHESIS CHECK:")
if commercial_null == all_candidatures.count():
    print(f"   ⚠️  ALL candidatures have NULL commercial_id!")
    print(f"   This means the filtering is NOT working because:")
    print(f"   1. Query for commercial_id=58 returns 0 AO_ids")
    print(f"   2. Filter with empty AO_id list should return nothing")
    print(f"   3. But API is returning data anyway!")
    print(f"\n   🔍 POSSIBLE BUG: Check if the API is actually applying the filter")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)

if not ao_ids:
    print("❌ Problem: Commercial 58 has NO candidatures assigned")
    print("Solution: Run this to assign candidatures to commercial 58:")
    print("")
    print("   # Find relevant candidatures and assign them")
    print("   Candidature.objects.filter(id_cd__in=[<ids>]).update(commercial_id=58)")
    print("")
else:
    expected_consultants = list(Candidature.objects.filter(AO_id__in=ao_ids).values_list('id_consultant', flat=True).distinct())
    if set(expected_consultants) == set(consultant_ids_in_response):
        print("✅ Filtering is working correctly!")
    else:
        print(f"❌ Mismatch!")
        print(f"   Expected consultants: {expected_consultants}")
        print(f"   Actual consultants: {consultant_ids_in_response}")
