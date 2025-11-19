"""
RBAC (Role-Based Access Control) Abstraction Layer
Manages user permissions and document access control.
Uses SQLite hierarchical RBAC instead of static config.
"""

import re
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass


@dataclass
class User:
    """User representation."""
    user_id: str
    role: str
    name: str
    email: str
    permissions: Set[str]
    access_level: int


@dataclass
class DocumentAccess:
    """Document access metadata."""
    classification: str
    min_access_level: int
    required_permissions: Set[str]


class RBACManager:
    """Manages role-based access control using SQLite hierarchy."""
    
    def __init__(self, db_manager=None):
        """Initialize RBAC Manager with database backend.
        
        Args:
            db_manager: DatabaseManager instance (lazy loaded if None)
        """
        self.db_manager = db_manager
        self.enforce_rbac = True
        self.log_access = True
        self.deny_by_default = True
        
        # Cache for users
        self._user_cache: Dict[str, User] = {}
        self._role_cache: Dict[str, Dict[str, Any]] = {}
        self._load_hierarchy()
    
    def _get_db(self):
        """Lazy load database manager if not provided."""
        if self.db_manager is None:
            from .database_abstraction import DatabaseManager
            self.db_manager = DatabaseManager()
        return self.db_manager
    
    def _load_hierarchy(self):
        """Load RBAC hierarchy from SQLite database."""
        try:
            db = self._get_db()
            
            # Load companies, departments, roles from database
            # Cache is built on-demand in get_user, etc.
            print("[OK] RBAC Manager initialized with SQLite backend")
        except Exception as e:
            print(f"[WARNING] Could not load RBAC hierarchy: {e}")
    
    def get_user(self, user_id) -> Optional[User]:
        """Get user from database by ID."""
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        
        try:
            db = self._get_db()
            user_data = db.get_user(user_id)
            
            if not user_data:
                return None
            
            # Get access level from role
            role_name = user_data.get("role_name", "unknown")
            access_level = self._get_access_level_for_role(user_data.get("grade"))
            
            user = User(
                user_id=str(user_id),
                role=role_name,
                name=user_data.get("username", ""),
                email=user_data.get("email", ""),
                permissions=set(self._get_permissions_for_role(role_name)),
                access_level=access_level
            )
            
            self._user_cache[user_id] = user
            return user
        except Exception as e:
            print(f"[WARNING] Error loading user {user_id}: {e}")
            return None
    
    def _get_access_level_for_role(self, grade: Optional[str]) -> int:
        """Map role grade to access level (1-5 scale)."""
        if not grade:
            return 1
        
        grade_lower = grade.lower()
        
        # Map grades to levels
        if "intern" in grade_lower:
            return 1
        elif any(x in grade_lower for x in ["junior", "l1", "l2"]):
            return 2
        elif any(x in grade_lower for x in ["senior", "l3"]):
            return 3
        elif any(x in grade_lower for x in ["lead", "manager", "l4"]):
            return 4
        elif any(x in grade_lower for x in ["director", "executive", "c-level", "l5"]):
            return 5
        
        return 2  # Default to level 2
    
    def _get_permissions_for_role(self, role_name: str) -> List[str]:
        """Get permissions for a role."""
        if not role_name:
            return ["read:general"]
        
        role_lower = role_name.lower()
        
        # Default permissions based on role
        if "admin" in role_lower or "director" in role_lower:
            return ["read:all", "write:all", "delete:all"]
        elif "manager" in role_lower or "lead" in role_lower:
            return ["read:all", "write:department"]
        elif "engineer" in role_lower or "developer" in role_lower:
            return ["read:technical", "read:engineering", "write:technical"]
        elif "hr" in role_lower or "recruiter" in role_lower:
            return ["read:policy", "read:hr", "write:hr"]
        else:
            return ["read:general"]
    
    def classify_document(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> DocumentAccess:
        """Classify document and determine access requirements."""
        content_lower = content.lower()
        metadata = metadata or {}
        
        # Check metadata first
        if "classification" in metadata:
            classification = metadata["classification"]
            min_level = metadata.get("min_access_level", 2)
            return DocumentAccess(
                classification=classification,
                min_access_level=min_level,
                required_permissions=set([f"read:{classification}"])
            )
        
        # Pattern-based classification
        classifications = {
            "technical": (r"(database|api|schema|algorithm|architecture|code)", 2),  # Lowered from 3 to 2
            "engineering": (r"(engineering|development|deployment|infrastructure)", 2),
            "hr": (r"(employee|hr|policy|handbook|payroll|benefits)", 2),
            "policy": (r"(policy|compliance|security|audit|legal)", 2),  # Lowered from 3 to 2
            "incident": (r"(incident|issue|problem|error|failure|root cause)", 1),  # Lowered from 2 to 1
        }
        
        for classification, (pattern, min_level) in classifications.items():
            if re.search(pattern, content_lower):
                return DocumentAccess(
                    classification=classification,
                    min_access_level=min_level,
                    required_permissions=set([f"read:{classification}"])
                )
        
        # Default classification
        return DocumentAccess(
            classification="general",
            min_access_level=1,
            required_permissions=set(["read:general"])
        )
    
    def check_permission(self, user: User, permission: str) -> bool:
        """Check if user has specific permission."""
        if not self.enforce_rbac:
            return True
        
        # Admin has all permissions
        if "read:all" in user.permissions or "write:all" in user.permissions:
            return True
        
        return permission in user.permissions
    
    def check_access_level(self, user: User, required_level: int) -> bool:
        """Check if user meets required access level."""
        if not self.enforce_rbac:
            return True
        
        return user.access_level >= required_level
    
    def can_access_document(
        self,
        user: User,
        document_access: DocumentAccess,
        operation: str = "read"
    ) -> bool:
        """Check if user can access document."""
        if not self.enforce_rbac:
            return True
        
        # Check access level
        if not self.check_access_level(user, document_access.min_access_level):
            if self.log_access:
                self._log_access_attempt(user, document_access, operation, False, "Insufficient access level")
            return False
        
        # Check permissions
        required_perm = f"{operation}:{document_access.classification}"
        if not self.check_permission(user, required_perm):
            # Check for wildcard permissions
            wildcard_perm = f"{operation}:all"
            if not self.check_permission(user, wildcard_perm):
                if self.log_access:
                    self._log_access_attempt(user, document_access, operation, False, "Missing permission")
                return False
        
        if self.log_access:
            self._log_access_attempt(user, document_access, operation, True, "Access granted")
        
        return True
    
    def filter_documents_by_access(
        self,
        user: User,
        documents: List[Any],
        operation: str = "read"
    ) -> List[Any]:
        """Filter documents based on user access rights."""
        if not self.enforce_rbac:
            return documents
        
        accessible_docs = []
        for doc in documents:
            # Assume documents have document_access attribute or metadata
            doc_access = getattr(doc, "document_access", None)
            if not doc_access and hasattr(doc, "metadata"):
                # Try to classify from metadata
                doc_access = self.classify_document(
                    getattr(doc, "content", ""),
                    doc.metadata
                )
            
            if doc_access and self.can_access_document(user, doc_access, operation):
                accessible_docs.append(doc)
        
        return accessible_docs
    
    def _log_access_attempt(
        self,
        user: User,
        document_access: DocumentAccess,
        operation: str,
        granted: bool,
        reason: str
    ):
        """Log access attempt."""
        status = "GRANTED" if granted else "DENIED"
        print(f"[RBAC {status}] User: {user.user_id} ({user.role}), "
              f"Operation: {operation}, Classification: {document_access.classification}, "
              f"Reason: {reason}")
    
    def add_user(
        self,
        user_id: str,
        role: str,
        name: str,
        email: str
    ) -> User:
        """Add a new user (cached representation)."""
        user = User(
            user_id=user_id,
            role=role,
            name=name,
            email=email,
            permissions=set(self._get_permissions_for_role(role)),
            access_level=self._get_access_level_for_role(role)
        )
        
        self._user_cache[user_id] = user
        return user
    
    def get_role_info(self, role: str) -> Optional[Dict[str, Any]]:
        """Get role information."""
        return {
            "name": role,
            "permissions": self._get_permissions_for_role(role),
            "access_level": self._get_access_level_for_role(role)
        }
    
    def list_roles(self) -> List[str]:
        """List all available roles."""
        try:
            db = self._get_db()
            # In a real implementation, query all roles from database
            # For now return common roles
            return ["engineer", "hr", "manager", "admin", "analyst"]
        except:
            return ["engineer", "hr", "manager", "admin"]
    
    def list_users(self) -> List[User]:
        """List all cached users."""
        return list(self._user_cache.values())
