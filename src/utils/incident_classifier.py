"""
Intelligent Incident Classifier
Automatically assigns RBAC levels and metadata tags based on incident characteristics.
"""

from typing import Dict, List, Any, Tuple
import re


class IncidentClassifier:
    """Classifies incidents and assigns appropriate RBAC and metadata."""
    
    # Severity to access level mapping
    SEVERITY_ACCESS_MAP = {
        "critical": 1,     # Highest access
        "high": 2,
        "medium": 3,
        "low": 4,
        "info": 5          # Lowest access (most permissive)
    }
    
    # Dollar impact thresholds for classification
    DOLLAR_THRESHOLDS = {
        "critical_finance": 100000,
        "high_finance": 50000,
        "medium_finance": 10000
    }
    
    # Keywords for category classification
    CATEGORY_KEYWORDS = {
        "engineering": [
            "deployment", "server", "infrastructure", "outage", "network",
            "database", "api", "microservice", "container", "kubernetes",
            "performance", "latency", "timeout", "error", "exception",
            "bug", "crash", "memory", "cpu", "disk", "load balancer"
        ],
        "security": [
            "breach", "vulnerability", "attack", "malware", "phishing",
            "unauthorized", "access denied", "firewall", "encryption",
            "authentication", "authorization", "exploit", "intrusion",
            "ddos", "ransomware", "password", "credential"
        ],
        "finance": [
            "payment", "billing", "invoice", "transaction", "revenue",
            "charge", "refund", "subscription", "cost", "budget",
            "pricing", "discount", "credit card", "bank", "financial"
        ],
        "hr": [
            "employee", "onboarding", "offboarding", "leave", "vacation",
            "payroll", "benefits", "performance review", "training",
            "hiring", "termination", "complaint", "hr policy"
        ],
        "compliance": [
            "gdpr", "hipaa", "pci", "sox", "audit", "regulation",
            "compliance", "legal", "privacy", "data protection",
            "retention", "policy violation"
        ],
        "customer": [
            "customer complaint", "service request", "support ticket",
            "user experience", "feedback", "escalation", "sla",
            "customer satisfaction"
        ]
    }
    
    # Platform-specific metadata
    PLATFORM_METADATA = {
        "azure": {
            "cloud_provider": "azure",
            "vendor": "microsoft",
            "category_boost": ["engineering", "infrastructure"]
        },
        "aws": {
            "cloud_provider": "aws",
            "vendor": "amazon",
            "category_boost": ["engineering", "infrastructure"]
        },
        "gcp": {
            "cloud_provider": "gcp",
            "vendor": "google",
            "category_boost": ["engineering", "infrastructure"]
        },
        "on-premise": {
            "cloud_provider": "none",
            "deployment": "on-premise"
        }
    }
    
    def __init__(self):
        """Initialize classifier."""
        pass
    
    def classify_incident(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify incident and return RBAC + metadata.
        
        Args:
            incident: Dictionary with keys:
                - platform: str
                - incident_description: str
                - incident_severity: str
                - resource_type: str
                - l1_triage: str
                - l2_triage: str
                - final_resolution: str
                - impacted_dollar: float/int
        
        Returns:
            Dictionary with:
                - classification: str (primary category)
                - min_access_level: int (1=most restricted, 5=public)
                - metadata_tags: Dict[str, Any]
                - confidence_score: float
        """
        # Extract fields
        platform = str(incident.get("platform", "")).lower()
        description = str(incident.get("incident_description", "")).lower()
        severity = str(incident.get("incident_severity", "")).lower()
        resource_type = str(incident.get("resource_type", "")).lower()
        l1_triage = str(incident.get("l1_triage", "")).lower()
        l2_triage = str(incident.get("l2_triage", "")).lower()
        resolution = str(incident.get("final_resolution", "")).lower()
        impacted_dollar = float(incident.get("impacted_dollar", 0))
        
        # Combine all text for analysis
        full_text = f"{description} {resource_type} {l1_triage} {l2_triage} {resolution}"
        
        # Determine category
        category, category_confidence = self._classify_category(full_text, severity, impacted_dollar)
        
        # Determine access level
        access_level = self._determine_access_level(
            category, severity, impacted_dollar, description
        )
        
        # Generate metadata tags
        metadata_tags = self._generate_metadata_tags(
            incident, category, platform, severity, impacted_dollar
        )
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(
            category_confidence, severity, len(full_text.split())
        )
        
        return {
            "classification": category,
            "min_access_level": access_level,
            "metadata_tags": metadata_tags,
            "confidence_score": confidence,
            "reasoning": self._generate_reasoning(category, access_level, severity, impacted_dollar)
        }
    
    def _classify_category(
        self, 
        text: str, 
        severity: str, 
        dollar_impact: float
    ) -> Tuple[str, float]:
        """Classify primary category based on keywords and context."""
        # Score each category
        category_scores = {}
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword in text:
                    score += 1
                    matched_keywords.append(keyword)
            
            category_scores[category] = {
                "score": score,
                "keywords": matched_keywords
            }
        
        # Boost finance if high dollar impact
        if dollar_impact > self.DOLLAR_THRESHOLDS["medium_finance"]:
            category_scores["finance"]["score"] += 3
        
        # Boost security if critical severity
        if severity == "critical":
            category_scores["security"]["score"] += 2
        
        # Find top category
        if not any(cat["score"] > 0 for cat in category_scores.values()):
            # No matches - default to engineering
            return "engineering", 0.3
        
        top_category = max(category_scores.items(), key=lambda x: x[1]["score"])
        category_name = top_category[0]
        score = top_category[1]["score"]
        
        # Calculate confidence (normalize to 0-1)
        max_possible_score = len(self.CATEGORY_KEYWORDS[category_name])
        confidence = min(score / max(max_possible_score * 0.3, 1), 1.0)
        
        return category_name, confidence
    
    def _determine_access_level(
        self,
        category: str,
        severity: str,
        dollar_impact: float,
        description: str
    ) -> int:
        """Determine minimum access level required."""
        # Start with severity-based access
        base_level = self.SEVERITY_ACCESS_MAP.get(severity, 4)
        
        # Adjust for category
        if category == "security":
            base_level = min(base_level, 1)  # Security always restricted
        elif category == "compliance":
            base_level = min(base_level, 2)
        elif category == "finance" and dollar_impact > self.DOLLAR_THRESHOLDS["high_finance"]:
            base_level = min(base_level, 2)
        elif category == "hr":
            base_level = min(base_level, 3)  # HR usually level 3
        
        # Check for PII/sensitive data keywords
        sensitive_keywords = [
            "ssn", "social security", "credit card", "password",
            "employee id", "salary", "personal information", "pii"
        ]
        
        if any(keyword in description for keyword in sensitive_keywords):
            base_level = min(base_level, 1)  # Highly restricted
        
        return base_level
    
    def _generate_metadata_tags(
        self,
        incident: Dict[str, Any],
        category: str,
        platform: str,
        severity: str,
        dollar_impact: float
    ) -> Dict[str, Any]:
        """Generate comprehensive metadata tags."""
        tags = {
            "category": category,
            "severity": severity,
            "platform": platform,
            "impacted_dollar": dollar_impact,
            "resource_type": incident.get("resource_type", "unknown")
        }
        
        # Add platform-specific metadata
        if platform in self.PLATFORM_METADATA:
            tags.update(self.PLATFORM_METADATA[platform])
        
        # Add severity indicators
        tags["is_critical"] = (severity == "critical")
        tags["is_high_impact"] = (dollar_impact > self.DOLLAR_THRESHOLDS["high_finance"])
        
        # Add triage summary
        if incident.get("l1_triage"):
            tags["has_l1_triage"] = True
        if incident.get("l2_triage"):
            tags["has_l2_triage"] = True
            tags["escalated"] = True
        
        # Add resolution status
        resolution = str(incident.get("final_resolution", "")).lower()
        if resolution:
            tags["resolved"] = True
            tags["resolution_type"] = self._classify_resolution_type(resolution)
        else:
            tags["resolved"] = False
        
        # Add financial classification
        if dollar_impact > 0:
            if dollar_impact > self.DOLLAR_THRESHOLDS["critical_finance"]:
                tags["financial_impact"] = "critical"
            elif dollar_impact > self.DOLLAR_THRESHOLDS["high_finance"]:
                tags["financial_impact"] = "high"
            elif dollar_impact > self.DOLLAR_THRESHOLDS["medium_finance"]:
                tags["financial_impact"] = "medium"
            else:
                tags["financial_impact"] = "low"
        
        # Add searchable tags
        tags["searchable_tags"] = [
            category,
            severity,
            platform,
            f"dollar_{tags.get('financial_impact', 'none')}"
        ]
        
        return tags
    
    def _classify_resolution_type(self, resolution: str) -> str:
        """Classify type of resolution."""
        resolution = resolution.lower()
        
        if any(word in resolution for word in ["reboot", "restart", "reset"]):
            return "restart"
        elif any(word in resolution for word in ["patch", "update", "upgrade"]):
            return "patch"
        elif any(word in resolution for word in ["config", "configuration", "setting"]):
            return "configuration_change"
        elif any(word in resolution for word in ["scale", "capacity", "resource"]):
            return "scaling"
        elif any(word in resolution for word in ["rollback", "revert"]):
            return "rollback"
        elif any(word in resolution for word in ["investigate", "analysis", "root cause"]):
            return "investigation"
        else:
            return "other"
    
    def _calculate_confidence(
        self,
        category_confidence: float,
        severity: str,
        text_length: int
    ) -> float:
        """Calculate overall classification confidence."""
        confidence = category_confidence
        
        # Boost if severity is clear
        if severity in self.SEVERITY_ACCESS_MAP:
            confidence += 0.1
        
        # Boost if sufficient text for analysis
        if text_length > 50:
            confidence += 0.1
        elif text_length < 10:
            confidence -= 0.2
        
        return max(0.0, min(1.0, confidence))
    
    def _generate_reasoning(
        self,
        category: str,
        access_level: int,
        severity: str,
        dollar_impact: float
    ) -> str:
        """Generate human-readable reasoning for classification."""
        reasons = []
        
        reasons.append(f"Category: {category}")
        reasons.append(f"Access Level: {access_level} (1=most restricted)")
        reasons.append(f"Severity: {severity}")
        
        if dollar_impact > 0:
            reasons.append(f"Financial Impact: ${dollar_impact:,.2f}")
        
        # Access level explanation
        level_names = {1: "Executive/Security", 2: "Senior Management", 
                      3: "Department Lead", 4: "Team Member", 5: "All Staff"}
        reasons.append(f"Minimum Role: {level_names.get(access_level, 'Unknown')}")
        
        return " | ".join(reasons)
    
    def validate_access(
        self,
        user_role: str,
        user_level: int,
        doc_classification: str,
        doc_min_level: int
    ) -> Dict[str, Any]:
        """
        Validate if user can access document.
        
        Returns:
            {
                "allowed": bool,
                "reason": str,
                "user_level": int,
                "required_level": int
            }
        """
        allowed = user_level <= doc_min_level
        
        if allowed:
            reason = f"Access GRANTED: {user_role} (level {user_level}) can access {doc_classification} (requires level {doc_min_level})"
        else:
            reason = f"Access DENIED: {user_role} (level {user_level}) cannot access {doc_classification} (requires level {doc_min_level})"
        
        return {
            "allowed": allowed,
            "reason": reason,
            "user_level": user_level,
            "required_level": doc_min_level,
            "classification": doc_classification
        }
    
    def get_role_level(self, role: str) -> int:
        """Map role name to access level."""
        role_map = {
            "admin": 1,
            "security_admin": 1,
            "executive": 1,
            "senior_manager": 2,
            "engineering_lead": 2,
            "manager": 3,
            "hr_manager": 3,
            "team_lead": 3,
            "engineer": 4,
            "employee": 4,
            "contractor": 5,
            "intern": 5,
            "public": 5
        }
        return role_map.get(role.lower(), 5)  # Default to most restrictive access
