#!/usr/bin/env python
"""
Test Script: Verify NDF Filtering Logic for Commercial 58
===================================================
This script tests the filtering logic to understand why consultants 59, 56, 54
are being returned for commercial 58.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maghrebIt_backend.settings')
django.setup()

from maghrebIt.models import Candidature, NDF_CONSULTANT, Collaborateur

print("="*70)
print(" NDF FILTERING LOGIC TEST FOR COMMERCIAL 58")
print("="*70)

commercial_id = 58

# Step 1: Check if commercial exists
print(f"\n[STEP 1] Checking if Commercial {commercial_id} exists...")
try:
    commercial = Collaborateur.objects.get(id_collab=commercial_id)
    print(f"✓ Commercial {commercial_id} exists: {commercial.nom_collab} {commercial.prenom_collab}")
    print(f"  Email: {commercial.email_collab}")
    print(f"  Role: {commercial.role_collab}")
except Collaborateur.DoesNotExist:
    print(f"✗ Commercial {commercial_id} does NOT exist!")
    exit()

# Step 2: Find AO_ids where commercial has candidatures
print(f"\n[STEP 2] Finding AO_ids where commercial {commercial_id} has candidatures...")
ao_ids_for_commercial = list(Candidature.objects.filter(
    commercial_id=commercial_id
).values_list('AO_id', flat=True).distinct())

print(f"AO_ids for commercial {commercial_id}: {ao_ids_for_commercial}")
print(f"Count: {len(ao_ids_for_commercial)}")

if not ao_ids_for_commercial:
    print(f"\n⚠ WARNING: Commercial {commercial_id} has NO candidatures!")
    print("This means the filter should return EMPTY queryset (query.none())")
    
    # Check if ALL candidatures have NULL commercial_id
    print(f"\n[CHECKING] Are ALL candidatures missing commercial_id?")
    total_candidatures = Candidature.objects.count()
    null_commercial_candidatures = Candidature.objects.filter(commercial_id__isnull=True).count()
    print(f"Total candidatures: {total_candidatures}")
    print(f"Candidatures with NULL commercial_id: {null_commercial_candidatures}")
    
    if null_commercial_candidatures == total_candidatures:
        print("\n✗ PROBLEM IDENTIFIED: ALL candidatures have NULL commercial_id!")
        print("This is why the filter returns empty and no consultants should appear.")
    
    # But let's check what consultants 59, 56, 54 have
    print(f"\n[INVESTIGATING] Checking consultants 59, 56, 54...")
    for consultant_id in [59, 56, 54]:
        candidatures = Candidature.objects.filter(id_consultant=consultant_id)
        print(f"\nConsultant {consultant_id}:")
        if candidatures.exists():
            print(f"  Has {candidatures.count()} candidatures")
            for cand in candidatures[:3]:
                print(f"    - Candidature {cand.id_cd}: AO_id={cand.AO_id}, commercial_id={cand.commercial_id}, statut={cand.statut}")
        else:
            print(f"  Has NO candidatures")
    
    # Check the actual NDFs
    print(f"\n[CHECKING] What NDFs exist for these consultants?")
    for consultant_id in [59, 56, 54]:
        ndfs = NDF_CONSULTANT.objects.filter(id_consultan=consultant_id)
        print(f"Consultant {consultant_id}: {ndfs.count()} NDFs")
    
    exit()

# Step 3: Find consultants in same AO_ids
print(f"\n[STEP 3] Finding consultants with candidatures in same AO_ids...")
consultants_in_same_aos = list(Candidature.objects.filter(
    AO_id__in=ao_ids_for_commercial
).values_list('id_consultant', flat=True).distinct())

print(f"Consultants in same AO_ids: {consultants_in_same_aos}")
print(f"Count: {len(consultants_in_same_aos)}")

if not consultants_in_same_aos:
    print(f"\n⚠ WARNING: No consultants found in same AO_ids!")
    print("This means the filter should return EMPTY queryset (query.none())")
    exit()

# Step 4: Check if consultants 59, 56, 54 are in this list
print(f"\n[STEP 4] Checking if consultants 59, 56, 54 are in the filtered list...")
for consultant_id in [59, 56, 54]:
    if consultant_id in consultants_in_same_aos:
        print(f"✓ Consultant {consultant_id} IS in the filtered list (CORRECT)")
        
        # Show which AO_ids they share
        shared_aos = Candidature.objects.filter(
            id_consultant=consultant_id,
            AO_id__in=ao_ids_for_commercial
        ).values_list('AO_id', 'id_cd', 'statut')
        print(f"  Shared AO_ids with commercial {commercial_id}:")
        for ao_id, cand_id, statut in shared_aos:
            print(f"    - AO_id={ao_id}, Candidature={cand_id}, statut={statut}")
    else:
        print(f"✗ Consultant {consultant_id} is NOT in the filtered list (should not appear)")

# Step 5: Filter NDFs
print(f"\n[STEP 5] Filtering NDFs by consultants in same AO_ids...")
filtered_ndfs = NDF_CONSULTANT.objects.filter(id_consultan__in=consultants_in_same_aos)
print(f"Total NDFs after filter: {filtered_ndfs.count()}")

# Show the NDFs from consultants 59, 56, 54
print(f"\nNDFs from consultants 59, 56, 54:")
for consultant_id in [59, 56, 54]:
    ndfs = filtered_ndfs.filter(id_consultan=consultant_id)
    print(f"  Consultant {consultant_id}: {ndfs.count()} NDFs")
    for ndf in ndfs:
        print(f"    - NDF {ndf.id_ndf}: periode={ndf.période}, montant={ndf.montant_ttc}, statut={ndf.statut}")

print("\n" + "="*70)
print("CONCLUSION:")
print("="*70)
if ao_ids_for_commercial:
    if any(c in consultants_in_same_aos for c in [59, 56, 54]):
        print("✓ The filter is working CORRECTLY.")
        print(f"  Commercial {commercial_id} and consultants 59, 56, 54 DO share common AO_ids.")
    else:
        print("✗ The filter has a BUG.")
        print(f"  Commercial {commercial_id} has AO_ids but consultants 59, 56, 54 don't share them.")
else:
    print("✗ DATA ISSUE: Commercial {commercial_id} has NO candidatures assigned.")
    print("  The filter should return EMPTY, but API is showing 7 NDFs.")
    print("  Possible reasons:")
    print("  1. The responsable_id parameter is not being sent correctly")
    print("  2. The if responsable_id: condition is not being entered")
    print("  3. There's a different ndf_consultant_view function being called")

print("="*70)
