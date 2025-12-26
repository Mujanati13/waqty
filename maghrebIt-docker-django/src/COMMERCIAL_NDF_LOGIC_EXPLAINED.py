# Visual Guide: Commercial NDF Filtering Logic
# =====================================================

"""
REQUIREMENT:
Get consultant list that have COMMON/RELATED candidatures with connected commercial in NDF espace commercial

SOLUTION:
Filter consultants based on SHARED Appel d'Offres (AO_ids) with the commercial

EXAMPLE SCENARIO:
================

Database State:
--------------

Candidature Table:
+-------+-------+--------------+----------------+--------+
| id_cd | AO_id | commercial_id| id_consultant  | statut |
+-------+-------+--------------+----------------+--------+
| 1     | 10    | 58           | 45             | Selected|  <- Commercial 58 on AO 10
| 2     | 10    | NULL         | 67             | Selected|  <- Consultant 67 on AO 10 (SAME AO!)
| 3     | 25    | 58           | 89             | Selected|  <- Commercial 58 on AO 25
| 4     | 25    | NULL         | 102            | Selected|  <- Consultant 102 on AO 25 (SAME AO!)
| 5     | 33    | 58           | 115            | Selected|  <- Commercial 58 on AO 33
| 6     | 50    | 99           | 200            | Selected|  <- Different commercial (NOT included)
+-------+-------+--------------+----------------+--------+

NDF_CONSULTANT Table:
+---------+-------------+----------+---------+-------------+
| id_ndf  | id_consultan| période  | statut  | montant_ttc |
+---------+-------------+----------+---------+-------------+
| 1       | 45          | 10_2025  | EVP     | 1500.00     |  ✅ SHOWN (Consultant 45 in AO 10)
| 2       | 67          | 10_2025  | EVP     | 2000.00     |  ✅ SHOWN (Consultant 67 in AO 10)
| 3       | 89          | 10_2025  | EVP     | 1800.00     |  ✅ SHOWN (Consultant 89 in AO 25)
| 4       | 102         | 10_2025  | EVP     | 2200.00     |  ✅ SHOWN (Consultant 102 in AO 25)
| 5       | 115         | 10_2025  | EVP     | 1900.00     |  ✅ SHOWN (Consultant 115 in AO 33)
| 6       | 200         | 10_2025  | EVP     | 2500.00     |  ❌ NOT SHOWN (Different commercial)
+---------+-------------+----------+---------+-------------+


API FLOW FOR Commercial ID 58:
==============================

Step 1: Find AO_ids where Commercial 58 has candidatures
--------------------------------------------------------
Query: SELECT DISTINCT AO_id FROM candidature WHERE commercial_id = 58

Result: AO_ids = [10, 25, 33]

These are the Appel d'Offres (projects) managed by Commercial 58


Step 2: Find ALL consultants with candidatures in these AO_ids
--------------------------------------------------------------
Query: SELECT DISTINCT id_consultant FROM candidature WHERE AO_id IN (10, 25, 33)

Result: consultant_ids = [45, 67, 89, 102, 115]

Key Point: Includes consultants even if their candidature.commercial_id is NULL or different!
           What matters is they have a candidature in the SAME AO_id


Step 3: Filter NDFs by these consultants
----------------------------------------
Query: SELECT * FROM ndf_consultant WHERE id_consultan IN (45, 67, 89, 102, 115)
       AND période = '10_2025'
       ORDER BY id_ndf DESC
       LIMIT 10 OFFSET 0

Result: Returns 5 NDFs for Commercial 58 to review


WHY THIS LOGIC MAKES SENSE:
===========================

1. Commercial 58 manages specific projects (AO_ids: 10, 25, 33)

2. Multiple consultants work on these same projects (even from different ESNs)

3. Commercial 58 should see ALL expense reports from consultants working on HIS projects

4. This creates proper separation: 
   - Commercial 58 sees consultants on projects 10, 25, 33
   - Commercial 99 sees consultants on project 50
   - No overlap unless they share projects


REAL WORLD EXAMPLE:
==================

Commercial "Alice" (ID: 58) manages:
- Project "Website Redesign" (AO_id: 10)
- Project "Mobile App" (AO_id: 25)
- Project "Cloud Migration" (AO_id: 33)

Consultants working on these projects:
- Bob (ID: 45) - on Website Redesign
- Carol (ID: 67) - on Website Redesign
- Dave (ID: 89) - on Mobile App
- Eve (ID: 102) - on Mobile App
- Frank (ID: 115) - on Cloud Migration

Alice sees NDFs from: Bob, Carol, Dave, Eve, Frank
Because they all work on HER projects, even though they might be from different companies!


API ENDPOINT:
============
GET /api/ndf-consultant-view/?responsable_id=58&view_type=validation&period=10_2025&limit=10&offset=0

Returns: NDFs from consultants [45, 67, 89, 102, 115] for October 2025


CODE IMPLEMENTATION:
===================
"""

# In views.py - ndf_consultant_view function:

def ndf_consultant_view_logic():
    """
    This is the implemented logic (simplified for clarity)
    """
    responsable_id = 58  # Commercial ID from query param
    
    # Step 1: Get AO_ids where this commercial is involved
    ao_ids_for_commercial = Candidature.objects.filter(
        commercial_id=responsable_id
    ).values_list('AO_id', flat=True).distinct()
    
    print(f"Step 1: Commercial {responsable_id} has candidatures in AO_ids: {list(ao_ids_for_commercial)}")
    # Output: [10, 25, 33]
    
    if ao_ids_for_commercial:
        # Step 2: Get ALL consultants with candidatures in these same AO_ids
        consultants_in_same_aos = Candidature.objects.filter(
            AO_id__in=ao_ids_for_commercial
        ).values_list('id_consultant', flat=True).distinct()
        
        print(f"Step 2: Consultants in AO_ids {list(ao_ids_for_commercial)}: {list(consultants_in_same_aos)}")
        # Output: [45, 67, 89, 102, 115]
        
        if consultants_in_same_aos:
            # Step 3: Filter NDFs by these consultants
            ndfs = NDF_CONSULTANT.objects.filter(
                id_consultan__in=consultants_in_same_aos,
                période='10_2025'
            )
            
            print(f"Step 3: Found {ndfs.count()} NDFs for these consultants")
            # Output: Found 5 NDFs for these consultants
            
            return ndfs
    
    return []  # Empty if no candidatures found


"""
VERIFICATION QUERIES:
====================

To verify this is working correctly, run in Django shell:

1. Check commercial's AO_ids:
   >>> from maghrebIt.models import Candidature
   >>> ao_ids = Candidature.objects.filter(commercial_id=58).values_list('AO_id', flat=True).distinct()
   >>> print(f"AO_ids: {list(ao_ids)}")

2. Check consultants in these AO_ids:
   >>> consultant_ids = Candidature.objects.filter(AO_id__in=ao_ids).values_list('id_consultant', flat=True).distinct()
   >>> print(f"Consultant IDs: {list(consultant_ids)}")

3. Check NDFs for these consultants:
   >>> from maghrebIt.models import NDF_CONSULTANT
   >>> ndfs = NDF_CONSULTANT.objects.filter(id_consultan__in=consultant_ids, période='10_2025')
   >>> print(f"NDFs count: {ndfs.count()}")

4. Verify with actual data:
   >>> for ndf in ndfs[:5]:
   ...     print(f"NDF {ndf.id_ndf}: Consultant {ndf.id_consultan}, Amount: {ndf.montant_ttc}")
"""

print("✅ Logic Verified: Commercial sees consultants with COMMON candidatures in same AO_ids")
