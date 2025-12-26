import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maghrebIt_backend.settings')
django.setup()

from maghrebIt.models import Candidature, NDF_CONSULTANT

print("\n" + "="*70)
print("TESTING NEW FILTER LOGIC FOR COMMERCIAL 58")
print("="*70)

commercial_id = 58

# New correct logic
consultants_for_commercial = list(Candidature.objects.filter(
    commercial_id=commercial_id
).values_list('id_consultant', flat=True).distinct())

print(f"\nConsultants with candidatures where commercial_id={commercial_id}:")
print(f"Result: {consultants_for_commercial}")

# Count NDFs for these consultants
if consultants_for_commercial:
    ndfs = NDF_CONSULTANT.objects.filter(id_consultan__in=consultants_for_commercial)
    print(f"\nTotal NDFs for these consultants: {ndfs.count()}")
    
    for consultant_id in consultants_for_commercial:
        consultant_ndfs = ndfs.filter(id_consultan=consultant_id)
        print(f"  Consultant {consultant_id}: {consultant_ndfs.count()} NDFs")
        for ndf in consultant_ndfs[:3]:
            print(f"    - NDF {ndf.id_ndf}: periode={ndf.période}, statut={ndf.statut}")
else:
    print("\n⚠ No consultants found for this commercial")

print("\n" + "="*70)
print("EXPECTED RESULT:")
print("="*70)
print("Only consultant 59 should appear (2 NDFs)")
print("Consultants 54 and 56 should NOT appear")
print("="*70)
