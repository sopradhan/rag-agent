# RBAC Tags Reference - Company, Department, Role Structure

## CDR Code System Overview

**CDR = Company-Department-Role** (3-digit code)

```
Format: [Company ID][Department ID][Role ID]

Examples:
  113 = Company 1, Department 1, Role 3
  232 = Company 2, Department 3, Role 2
  311 = Company 3, Department 1, Role 1
  131 = Company 1, Department 3, Role 1
```

---

## Your Requirement: Company 1, Department 1, Role 3

### CDR Code: **113**

```
┌─────────────────────────────────────┐
│ CDR CODE: 113                       │
├─────────────────────────────────────┤
│ Company ID: 1                       │
│ Department ID: 1                    │
│ Role ID: 3                          │
│                                     │
│ Human Readable:                     │
│ Company: Acme Corp                  │
│ Department: Engineering             │
│ Role: Engineering Manager           │
│ Access Level: 3 (High)              │
└─────────────────────────────────────┘
```

---

## Complete RBAC Tag Mapping

### Company IDs
```
1 = Acme Corp
2 = TechFlow Inc
3 = Innovation Labs
4 = Enterprise Solutions
...
9 = Custom Company
```

### Department IDs (for Company 1)
```
Department 1: Engineering
  - Role 1: Junior Engineer
  - Role 2: Senior Engineer
  - Role 3: Engineering Manager

Department 2: Product
  - Role 1: Product Associate
  - Role 2: Product Manager
  - Role 3: VP Product

Department 3: HR
  - Role 1: HR Specialist
  - Role 2: HR Manager
  - Role 3: HR Director

Department 4: Finance
  - Role 1: Accountant
  - Role 2: Finance Manager
  - Role 3: CFO
```

### Role IDs (General)
```
1 = Individual Contributor / Staff
2 = Manager / Senior
3 = Director / Lead Manager
4 = VP / Senior Director
5 = C-Level / Executive
```

---

## CDR Code Examples with Tags

### Company 1, Department 1, Role 3 (Your Example)

```
CDR: 113
├─ Company: Acme Corp (ID: 1)
├─ Department: Engineering (ID: 1)
├─ Role: Engineering Manager (ID: 3)
└─ Access Level: 3 (High - can access engineering + related docs)

Database Entry:
INSERT INTO role_mappings 
(company_id, department_id, role_id, cdr_code, company_name, department_name, role_name, access_level)
VALUES (1, 1, 3, '113', 'Acme Corp', 'Engineering', 'Engineering Manager', 3);
```

### Other Examples

#### Example 2: Company 1, Department 3, Role 2
```
CDR: 132
├─ Company: Acme Corp (ID: 1)
├─ Department: HR (ID: 3)
├─ Role: HR Manager (ID: 2)
└─ Access Level: 2 (Medium - HR management privileges)
```

#### Example 3: Company 2, Department 1, Role 1
```
CDR: 211
├─ Company: TechFlow Inc (ID: 2)
├─ Department: Engineering (ID: 1)
├─ Role: Junior Engineer (ID: 1)
└─ Access Level: 1 (Low - junior level access)
```

#### Example 4: Company 1, Department 2, Role 3
```
CDR: 123
├─ Company: Acme Corp (ID: 1)
├─ Department: Product (ID: 2)
├─ Role: VP Product (ID: 3)
└─ Access Level: 3 (High - VP level)
```

---

## How RBAC Tags are Stored in Database

### role_mappings Table

```sql
SELECT * FROM role_mappings WHERE company_id = 1 ORDER BY department_id, role_id;

Results:
┌──────────┬───────────┬─────────┬──────────┬──────────────┬────────────────┬──────────────────┬──────────────┐
│company_id│department │role_id  │cdr_code  │company_name  │department_name │role_name         │access_level  │
├──────────┼───────────┼─────────┼──────────┼──────────────┼────────────────┼──────────────────┼──────────────┤
│1         │1          │1        │"111"     │Acme Corp     │Engineering     │Junior Engineer   │1             │
│1         │1          │2        │"112"     │Acme Corp     │Engineering     │Senior Engineer   │2             │
│1         │1          │3        │"113"     │Acme Corp     │Engineering     │Engineering Mgr   │3             │
│1         │2          │1        │"121"     │Acme Corp     │Product         │Product Associate │1             │
│1         │2          │2        │"122"     │Acme Corp     │Product         │Product Manager   │2             │
│1         │2          │3        │"123"     │Acme Corp     │Product         │VP Product        │3             │
│1         │3          │1        │"131"     │Acme Corp     │HR              │HR Specialist     │1             │
│1         │3          │2        │"132"     │Acme Corp     │HR              │HR Manager        │2             │
│1         │3          │3        │"133"     │Acme Corp     │HR              │HR Director       │3             │
│2         │1          │1        │"211"     │TechFlow Inc  │Engineering     │Junior Engineer   │1             │
│2         │1          │2        │"212"     │TechFlow Inc  │Engineering     │Senior Engineer   │2             │
│2         │1          │3        │"213"     │TechFlow Inc  │Engineering     │Engineering Mgr   │3             │
└──────────┴───────────┴─────────┴──────────┴──────────────┴────────────────┴──────────────────┴──────────────┘
```

---

## How Document Access is Controlled with RBAC Tags

### Scenario: HR Document with Tag Restrictions

```
Document: Employee Handbook
Tags/CDR Codes Required: 131, 132, 133

┌─ Document stored with RBAC rules:
│
├─ CDR 131 (HR Specialist) ✅ Can access
│   └─ Company 1, HR Department, Role 1
│
├─ CDR 132 (HR Manager) ✅ Can access
│   └─ Company 1, HR Department, Role 2
│
├─ CDR 133 (HR Director) ✅ Can access
│   └─ Company 1, HR Department, Role 3
│
├─ CDR 113 (Engineering Manager) ❌ Cannot access
│   └─ Company 1, Engineering Department, Role 3
│       (Different department, no HR access)
│
└─ CDR 211 (TechFlow Junior Engineer) ❌ Cannot access
    └─ Company 2, Engineering, Role 1
        (Different company, no access to Acme docs)
```

### SQL Query to Check Access

```sql
-- User has role 113 (Acme Corp, Engineering, Manager)
-- Check if can access document ID 1 (Employee Handbook)

SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM document_permissions 
            WHERE doc_id = 1 AND cdr_code = '113'
        ) THEN 'GRANTED'
        ELSE 'DENIED'
    END as access_result;

Result: DENIED (because 113 is not in required CDR codes)

-- Now check user with role 131 (Acme Corp, HR, Specialist)
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM document_permissions 
            WHERE doc_id = 1 AND cdr_code = '131'
        ) THEN 'GRANTED'
        ELSE 'DENIED'
    END as access_result;

Result: GRANTED (because 131 is in required CDR codes)
```

---

## Tag Hierarchy

```
COMPANY LEVEL (First Digit: 1-9)
  │
  ├─ Company 1 (Acme Corp)
  │   │
  │   ├─ DEPARTMENT (Second Digit: 1-9)
  │   │   │
  │   │   ├─ Department 1: Engineering
  │   │   │   ├─ ROLE (Third Digit: 1-9)
  │   │   │   ├─ Role 1: Junior Engineer (111)
  │   │   │   ├─ Role 2: Senior Engineer (112)
  │   │   │   └─ Role 3: Engineering Manager (113) ← YOUR EXAMPLE
  │   │   │
  │   │   ├─ Department 2: Product
  │   │   │   ├─ Role 1: Product Associate (121)
  │   │   │   ├─ Role 2: Product Manager (122)
  │   │   │   └─ Role 3: VP Product (123)
  │   │   │
  │   │   └─ Department 3: HR
  │   │       ├─ Role 1: HR Specialist (131)
  │   │       ├─ Role 2: HR Manager (132)
  │   │       └─ Role 3: HR Director (133)
  │   │
  │   └─ Company 2 (TechFlow Inc)
  │       └─ ...all departments & roles...
  │
  └─ Company 3 (Innovation Labs)
      └─ ...all departments & roles...
```

---

## Tag Filtering Examples

### Find All Managers (Role ID = 3) in Company 1

```sql
SELECT cdr_code, company_name, department_name, role_name
FROM role_mappings
WHERE company_id = 1 AND role_id = 3;

Results:
- 113: Acme Corp, Engineering, Engineering Manager
- 123: Acme Corp, Product, VP Product
- 133: Acme Corp, HR, HR Director
```

### Find All HR Department (Department ID = 3) Roles

```sql
SELECT cdr_code, company_name, role_name, access_level
FROM role_mappings
WHERE department_id = 3
ORDER BY company_id, role_id;

Results:
- 131: Acme Corp, HR Specialist, Level 1
- 132: Acme Corp, HR Manager, Level 2
- 133: Acme Corp, HR Director, Level 3
- 231: TechFlow Inc, HR Specialist, Level 1
- 232: TechFlow Inc, HR Manager, Level 2
- 231: Innovation Labs, HR Specialist, Level 1
```

### Find All Engineering (Department 1) Access Levels

```sql
SELECT cdr_code, company_name, role_name, access_level
FROM role_mappings
WHERE department_id = 1
ORDER BY access_level DESC;

Results:
- 113: Acme Corp, Engineering Manager, Level 3
- 213: TechFlow Inc, Engineering Manager, Level 3
- 112: Acme Corp, Senior Engineer, Level 2
- 212: TechFlow Inc, Senior Engineer, Level 2
- 111: Acme Corp, Junior Engineer, Level 1
- 211: TechFlow Inc, Junior Engineer, Level 1
```

---

## How to Use Tags in Queries

### Python - Check User Permission by Tag

```python
from core.services.database_service import DatabaseService

db = DatabaseService('data/rag_system.db')

# User has tag: Company 1, Department 1, Role 3
user_cdr_code = "113"

# Check if user can access document
can_access = db.check_permission(
    user_id="john.doe@acme.com",
    doc_id="1"  # Employee Handbook
)

# Behind the scenes:
# 1. Get user roles: ["113"]
# 2. Get document required roles: ["131", "132", "133"]
# 3. Check intersection: "113" not in ["131", "132", "133"]
# 4. Result: False (cannot access)
```

### Python - Query by Tag

```python
# Get CDR code from tag
tag = {"company_id": 1, "department_id": 3, "role_id": 2}
# CDR = "132"

# Find all HR (dept 3) documents accessible to HR Manager (role 2)
results = chromadb.collection.query(
    query_embeddings=[query_vector],
    where={"cdr_codes": {"$contains": "132"}},
    n_results=10
)
```

---

## Summary Table

| Tag Component | Example | Range | Purpose |
|---------------|---------|-------|---------|
| **Company** | 1 (Acme Corp) | 1-9 | Organization |
| **Department** | 1 (Engineering) | 1-9 | Function/Team |
| **Role** | 3 (Manager) | 1-9 | Position Level |
| **CDR Code** | 113 | 111-999 | Access Control |
| **Access Level** | 3 | 1-10 | Permission Level |
| **Name Tags** | "Engineering Manager" | Any | Human Readable |

---

## Your Configuration Ready

```
✅ Company 1
✅ Department 1  
✅ Role 3
✅ CDR Code: 113
✅ Access Level: 3
✅ Ready to assign to users and documents!
```

To add this to the system:

```sql
INSERT INTO role_mappings 
(company_id, department_id, role_id, cdr_code, company_name, department_name, role_name, access_level)
VALUES (1, 1, 3, '113', 'Acme Corp', 'Engineering', 'Engineering Manager', 3);

-- Then assign to users
INSERT INTO user_roles (user_id, cdr_code, company_id, department_id, role_id)
VALUES ('manager1@acme.com', '113', 1, 1, 3);

-- Then assign to documents
INSERT INTO document_permissions (doc_id, cdr_code, sensitivity, subject, assigned_by)
VALUES (1, '113', 'confidential', 'engineering', 'system_admin');
```
