import re

# Read the file
with open('maghrebIt/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Old filtering logic (wrong - finds all consultants in same AO_ids)
old_pattern = re.compile(
    r'# Filter by responsable_id \(commercial manager\)\s+'
    r'responsable_id = request\.GET\.get\(\'responsable_id\'\)\s+'
    r'if responsable_id:\s+'
    r'# Step 1: Find all AO_ids \(Appel d\'Offres\) where this commercial has candidatures\s+'
    r'ao_ids_for_commercial = Candidature\.objects\.filter\(\s+'
    r'commercial_id=responsable_id\s+'
    r'\)\.values_list\(\'AO_id\', flat=True\)\.distinct\(\)\s+'
    r'\s+'
    r'if ao_ids_for_commercial:\s+'
    r'# Step 2: Find all consultants who have candidatures for these same AO_ids\s+'
    r'consultants_in_same_aos = Candidature\.objects\.filter\(\s+'
    r'AO_id__in=ao_ids_for_commercial\s+'
    r'\)\.values_list\(\'id_consultant\', flat=True\)\.distinct\(\)\s+'
    r'\s+'
    r'if consultants_in_same_aos:\s+'
    r'# Step 3: Filter NDFs by these consultants\s+'
    r'query = query\.filter\(id_consultan__in=consultants_in_same_aos\)\s+'
    r'else:\s+'
    r'query = query\.none\(\)\s+'
    r'else:\s+'
    r'# If no candidatures found for this commercial, return empty queryset\s+'
    r'query = query\.none\(\)',
    re.MULTILINE
)

# New filtering logic (correct - only consultants with direct commercial_id assignment)
new_text = '''# Filter by responsable_id (commercial manager)
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
                    query = query.none()'''

# Replace all occurrences
new_content, count = old_pattern.subn(new_text, content)

print(f"Replacements made: {count}")

if count > 0:
    # Write back
    with open('maghrebIt/views.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("✓ File updated successfully!")
else:
    print("✗ Pattern not found. Trying simpler pattern...")
