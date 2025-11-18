"""
RBAC (Role-Based Access Control) Abstraction Layer
Manages user permissions and document access control.
"""

import re
from typing import Dict, Any, List, Optional, Set
import yaml
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
    """Manages role-based access control."""
    
    def __init__(self, config_path: str = "config/rbac_config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.roles = self.config.get("roles", {})
        self.users_config = self.config.get("users", {})
        self.doc_classifications = self.config.get("document_classifications", [])
        self.access_control = self.config.get("access_control", {})
        
        self.enforce_rbac = self.access_control.get("enforce_rbac", True)
        self.log_access = self.access_control.get("log_access_attempts", True)
        self.deny_by_default = self.access_control.get("deny_by_default", True)
        
        # Cache users
        self._user_cache: Dict[str, User] = {}
        self._load_users()
    
    def _load_users(self):
        """Load users from configuration."""
        for user_id, user_data in self.users_config.items():
            role = user_data.get("role")
            if role not in self.roles:
                continue
            
            role_config = self.roles[role]
            self._user_cache[user_id] = User(
                user_id=user_id,
                role=role,
                name=user_data.get("name", ""),
                email=user_data.get("email", ""),
                permissions=set(role_config.get("permissions", [])),
                access_level=role_config.get("access_level", 0)
            )
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._user_cache.get(user_id)
    
    def classify_document(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> DocumentAccess:
        """Classify document and determine access requirements."""
        content_lower = content.lower()
        metadata = metadata or {}
        
        # Check metadata first
        if "classification" in metadata:
            classification = metadata["classification"]
            for rule in self.doc_classifications:
                if classification == rule.get("classification"):
                    return DocumentAccess(
                        classification=classification,
                        min_access_level=rule.get("min_access_level", 0),
                        required_permissions=set([f"read:{classification}"])
                    )
        
        # Pattern-based classification
        for rule in self.doc_classifications:
            pattern = rule.get("pattern", "")
            if pattern and re.search(pattern, content_lower):
                classification = rule.get("classification", "general")
                return DocumentAccess(
                    classification=classification,
                    min_access_level=rule.get("min_access_level", 0),
                    required_permissions=set([f"read:{classification}"])
                )
        
        # Default classification
        return DocumentAccess(
            classification="general",
            min_access_level=10,
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
        """Log access attempt (implement actual logging as needed)."""
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
        """Add a new user."""
        if role not in self.roles:
            raise ValueError(f"Role {role} does not exist")
        
        role_config = self.roles[role]
        user = User(
            user_id=user_id,
            role=role,
            name=name,
            email=email,
            permissions=set(role_config.get("permissions", [])),
            access_level=role_config.get("access_level", 0)
        )
        
        self._user_cache[user_id] = user
        return user
    
    def get_role_info(self, role: str) -> Optional[Dict[str, Any]]:
        """Get role configuration."""
        return self.roles.get(role)
    
    def list_roles(self) -> List[str]:
        """List all available roles."""
        return list(self.roles.keys())
    
    def list_users(self) -> List[User]:
        """List all users."""
        return list(self._user_cache.values())
