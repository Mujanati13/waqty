# SQL Query Explanation - Commercial NDF Filtering
# =================================================

## What the API does when Commercial ID 58 requests their NDF list:

### Step 1: Find AO_ids where Commercial 58 has candidatures
```sql
SELECT DISTINCT AO_id 
FROM candidature 
WHERE commercial_id = 58;

-- Example Result:
-- AO_id
-- ------
-- 10
-- 25
-- 33
```

### Step 2: Find ALL consultants who have candidatures in these same AO_ids
```sql
SELECT DISTINCT id_consultant 
FROM candidature 
WHERE AO_id IN (10, 25, 33);

-- Example Result:
-- id_consultant
-- -------------
-- 45
-- 67
-- 89
-- 102
-- 115
```

**Important:** This query gets consultants regardless of their `commercial_id` value!
- It can be NULL
- It can be 58 (same commercial)
- It can be a different commercial ID

What matters: They have a candidature record for the SAME Appel d'Offre (AO_id)

### Step 3: Get NDFs for these consultants
```sql
SELECT * 
FROM ndf_consultant 
WHERE id_consultan IN (45, 67, 89, 102, 115)
  AND période = '10_2025'
ORDER BY id_ndf DESC
LIMIT 10 OFFSET 0;

-- Returns all NDFs from consultants working on the same projects as Commercial 58
```

## Full Combined Query (equivalent to what Django ORM does):

```sql
-- Get NDFs for consultants who have candidatures in the same AO_ids as Commercial 58

SELECT ndf.* 
FROM ndf_consultant ndf
WHERE ndf.id_consultan IN (
    -- Get all consultants in the same AO_ids as the commercial
    SELECT DISTINCT c2.id_consultant
    FROM candidature c2
    WHERE c2.AO_id IN (
        -- Get AO_ids where commercial 58 has candidatures
        SELECT DISTINCT c1.AO_id
        FROM candidature c1
        WHERE c1.commercial_id = 58
    )
)
AND ndf.période = '10_2025'
ORDER BY ndf.id_ndf DESC
LIMIT 10 OFFSET 0;
```

## Relationship Diagram:

```
Commercial (ID: 58)
        |
        | (has candidatures in)
        v
    AO_ids [10, 25, 33]  ← Appel d'Offres (Projects)
        |
        | (other candidatures in same AO_ids)
        v
    Consultants [45, 67, 89, 102, 115]
        |
        | (created)
        v
    NDFs [id_ndf: 1, 2, 3, 4, 5]
        |
        | (displayed to)
        v
    Commercial (ID: 58) in Validation Interface
```

## Key Concept:

**COMMON CANDIDATURES = SHARED PROJECTS (AO_ids)**

- Commercial and Consultants must have candidatures in the SAME Appel d'Offre (AO_id)
- This creates the relationship: "We work on the same project"
- Commercial sees all expense reports from consultants on their projects

## Verification Query:

To check if the filtering is working correctly:

```sql
-- For Commercial ID 58, show which consultants they should see

SELECT 
    c.id_consultant,
    col.Nom,
    col.Prenom,
    c.AO_id,
    COUNT(ndf.id_ndf) as ndf_count
FROM candidature c
INNER JOIN collaboration col ON col.ID_collab = c.id_consultant
LEFT JOIN ndf_consultant ndf ON ndf.id_consultan = c.id_consultant 
    AND ndf.période = '10_2025'
WHERE c.AO_id IN (
    SELECT DISTINCT AO_id 
    FROM candidature 
    WHERE commercial_id = 58
)
GROUP BY c.id_consultant, col.Nom, col.Prenom, c.AO_id
ORDER BY c.AO_id, col.Nom;
```

This shows:
- Which consultants share AO_ids with Commercial 58
- How many NDFs each consultant has for the period
- Which project (AO_id) links them together

## Test Cases:

### Test Case 1: Commercial with 3 projects
```sql
-- Commercial 58 manages AO_ids: 10, 25, 33
-- Should see consultants from all 3 projects
```

### Test Case 2: Consultant on multiple projects
```sql
-- Consultant 45 has candidatures for AO_ids: 10, 50
-- Commercial 58 (manages 10, 25, 33) → WILL see Consultant 45 (common AO_id: 10)
-- Commercial 99 (manages 50, 60) → WILL see Consultant 45 (common AO_id: 50)
```

### Test Case 3: No common projects
```sql
-- Commercial 58 manages AO_ids: 10, 25, 33
-- Consultant 200 only has candidatures for AO_id: 50
-- Commercial 58 → WILL NOT see Consultant 200 (no common AO_ids)
```

## API Response Structure:

When calling:
```
GET /api/ndf-consultant-view/?responsable_id=58&period=10_2025
```

Expected response includes NDFs from consultants who share AO_ids with Commercial 58:
```json
{
  "status": true,
  "data": [
    {
      "id_ndf": 5,
      "id_consultan": 115,
      "consultant_name": "Frank Martin",
      "période": "10_2025",
      "jour": 15,
      "montant_ttc": 1900.00,
      "statut": "EVP",
      "description": "Client meeting expenses"
    },
    // ... more NDFs from consultants [45, 67, 89, 102, 115]
  ],
  "total": 25
}
```
