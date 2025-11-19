"""
Debug RBAC issues - check users, roles, documents, and access levels.
"""

from src.storage import RAGDatabase
from src.abstraction import RBACManager, DatabaseManager

print("=" * 80)
print("RBAC DEBUGGING SCRIPT")
print("=" * 80)

# Initialize database
db = RAGDatabase()
db_manager = DatabaseManager()
rbac_manager = RBACManager(db_manager=db_manager)

# 1. Check available roles
print("\n[1] AVAILABLE ROLES IN DATABASE:")
print("-" * 80)
try:
    roles_result = db.conn.execute("SELECT id, name, grade FROM role").fetchall()
    for role in roles_result:
        print(f"  Role ID: {role[0]}, Name: {role[1]}, Grade: {role[2]}")
except Exception as e:
    print(f"  Error: {e}")

# 2. Check available users
print("\n[2] AVAILABLE USERS IN DATABASE:")
print("-" * 80)
try:
    users_result = db.conn.execute("""
        SELECT u.id, u.username, u.email, r.name as role_name, r.grade 
        FROM users u 
        LEFT JOIN role r ON u.role_id = r.id
    """).fetchall()
    for user in users_result:
        print(f"  User ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {user[3]}, Grade: {user[4]}")
except Exception as e:
    print(f"  Error: {e}")

# 3. Check document classifications
print("\n[3] DOCUMENTS IN VECTOR STORE:")
print("-" * 80)
try:
    # Get all documents from the vector store
    collection = db.vector_store.collection
    if collection:
        all_docs = collection.get()
        print(f"  Total documents in collection: {len(all_docs['ids'])}")
        for i, (doc_id, metadata) in enumerate(zip(all_docs['ids'], all_docs.get('metadatas', [{}] * len(all_docs['ids'])))):
            classification = metadata.get('classification', 'unknown')
            min_level = metadata.get('min_access_level', 1)
            print(f"  Doc {i+1}: ID={doc_id}, Classification={classification}, Min Level={min_level}")
    else:
        print("  No collection found")
except Exception as e:
    print(f"  Error: {e}")

# 4. Check documents in SQLite
print("\n[4] DOCUMENTS IN SQLITE DATABASE:")
print("-" * 80)
try:
    docs_result = db.conn.execute("""
        SELECT id, title, classification, min_access_level 
        FROM documents 
        LIMIT 10
    """).fetchall()
    print(f"  Total documents: {docs_result[0][0] if docs_result else 0}")
    for doc in docs_result[:5]:
        print(f"  Doc: ID={doc[0]}, Title={doc[1]}, Class={doc[2]}, MinLevel={doc[3]}")
except Exception as e:
    print(f"  Error: {e}")

# 5. Test RBAC filtering with a specific user
print("\n[5] TEST RBAC FILTERING:")
print("-" * 80)
try:
    # Get first user
    user_result = db.conn.execute("SELECT id, username FROM users LIMIT 1").fetchone()
    if user_result:
        user_id = user_result[0]
        username = user_result[1]
        print(f"  Testing with User: {username} (ID: {user_id})")
        
        # Get user object via RBACManager
        user = rbac_manager.get_user(user_id)
        if user:
            print(f"    - Access Level: {user.access_level}")
            print(f"    - Role: {user.role}")
            print(f"    - Permissions: {user.permissions}")
        else:
            print(f"    - User not found in RBAC manager")
    else:
        print("  No users in database")
except Exception as e:
    print(f"  Error: {e}")

# 6. Show RBAC classification examples
print("\n[6] RBAC CLASSIFICATION LOGIC:")
print("-" * 80)
test_content = "This is about database rollback and transaction management"
doc_access = rbac_manager.classify_document(test_content)
print(f"  Test content: '{test_content}'")
print(f"  Classification: {doc_access.classification}")
print(f"  Min Access Level: {doc_access.min_access_level}")
print(f"  Required Permissions: {doc_access.required_permissions}")

print("\n[7] ACCESS LEVEL MAPPING:")
print("-" * 80)
test_grades = ["intern", "junior l1", "senior l3", "lead l4", "director", "executive"]
for grade in test_grades:
    level = rbac_manager._get_access_level_for_role(grade)
    print(f"  Grade '{grade}' -> Level {level}")

print("\n" + "=" * 80)
print("DEBUG COMPLETE")
print("=" * 80)
