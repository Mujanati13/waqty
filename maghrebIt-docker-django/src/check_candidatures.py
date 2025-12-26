import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maghrebIt_backend.settings')
django.setup()

from maghrebIt.models import Candidature

print("\n" + "="*70)
print("CANDIDATURES FOR CONSULTANTS 54, 56, 59")
print("="*70)

candidatures = Candidature.objects.filter(id_consultant__in=[54, 56, 59]).order_by('id_consultant', 'AO_id')

for c in candidatures:
    print(f"Candidature {c.id_cd}: AO_id={c.AO_id}, commercial_id={c.commercial_id}, consultant={c.id_consultant}, statut={c.statut}")

print("\n" + "="*70)
print("CANDIDATURES WHERE COMMERCIAL_ID = 58")
print("="*70)

candidatures_58 = Candidature.objects.filter(commercial_id=58)
print(f"Total: {candidatures_58.count()}")
for c in candidatures_58:
    print(f"Candidature {c.id_cd}: AO_id={c.AO_id}, commercial_id={c.commercial_id}, consultant={c.id_consultant}, statut={c.statut}")

print("\n" + "="*70)
print("THE CORRECT FILTER SHOULD BE:")
print("="*70)
print("Show consultants who have candidatures where:")
print("  - commercial_id = 58 (same row)")
print("  - id_consultant = X (same row)")
print("\nNOT:")
print("  - Find AO_ids where commercial_id=58")
print("  - Then find all consultants in those AO_ids")

correct_consultants = list(Candidature.objects.filter(
    commercial_id=58
).values_list('id_consultant', flat=True).distinct())

print(f"\nCorrect consultant list for commercial 58: {correct_consultants}")
