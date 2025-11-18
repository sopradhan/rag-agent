"""
Intelligent Retriever with Multi-Step Reasoning
Features:
- Think → Evaluate → Respond → Rethink loop
- Query intent classification
- Department-based RBAC
- Context understanding and attention mechanisms
- Visible reasoning steps in dashboard
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import re


@dataclass
class ReasoningStep:
    """A single step in the reasoning process."""
    step_type: str  # "think", "evaluate", "respond", "rethink", "attention"
    content: str
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_type": self.step_type,
            "content": self.content,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class IntelligentResponse:
    """Response with full reasoning chain."""
    query: str
    final_answer: str
    reasoning_steps: List[ReasoningStep]
    retrieved_docs: List[Any]
    faithfulness: Any
    query_intent: Dict[str, Any]
    department_access: Dict[str, Any]
    response_time: float
    user_context: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "final_answer": self.final_answer,
            "reasoning_steps": [step.to_dict() for step in self.reasoning_steps],
            "retrieved_docs": [doc.to_dict() for doc in self.retrieved_docs],
            "faithfulness": self.faithfulness.to_dict(),
            "query_intent": self.query_intent,
            "department_access": self.department_access,
            "response_time": self.response_time,
            "user_context": self.user_context
        }


class IntelligentRetriever:
    """
    Advanced retriever with multi-step reasoning and department-based access control.
    """
    
    # Department definitions with access levels
    DEPARTMENTS = {
        "engineering": {
            "keywords": ["deployment", "kubernetes", "api", "database", "server", "infrastructure", 
                        "code", "bug", "production", "staging", "docker", "ci/cd"],
            "access_level": 2,
            "allowed_roles": ["admin", "security_admin", "executive", "senior_manager", 
                            "engineering_lead", "engineer", "team_lead"]
        },
        "security": {
            "keywords": ["security", "breach", "unauthorized", "vulnerability", "attack", 
                        "firewall", "encryption", "authentication", "threat", "malware"],
            "access_level": 1,
            "allowed_roles": ["admin", "security_admin", "executive", "senior_manager"]
        },
        "finance": {
            "keywords": ["payment", "revenue", "dollar", "financial", "transaction", 
                        "billing", "charge", "cost", "budget", "invoice"],
            "access_level": 1,
            "allowed_roles": ["admin", "executive", "senior_manager"]
        },
        "hr": {
            "keywords": ["employee", "onboarding", "hiring", "payroll", "benefits", 
                        "training", "recruitment", "termination", "performance"],
            "access_level": 3,
            "allowed_roles": ["admin", "executive", "senior_manager", "hr_manager"]
        },
        "compliance": {
            "keywords": ["gdpr", "compliance", "regulation", "audit", "policy", 
                        "legal", "data retention", "privacy"],
            "access_level": 1,
            "allowed_roles": ["admin", "executive", "senior_manager"]
        },
        "customer": {
            "keywords": ["customer", "client", "portal", "dashboard", "user", 
                        "service", "support", "escalation"],
            "access_level": 4,
            "allowed_roles": ["admin", "executive", "senior_manager", "manager", 
                            "team_lead", "employee"]
        }
    }
    
    def __init__(self, db, classifier=None):
        """Initialize intelligent retriever."""
        self.db = db
        
        if classifier is None:
            from src.utils.incident_classifier import IncidentClassifier
            classifier = IncidentClassifier()
        
        self.classifier = classifier
        self.reasoning_steps = []
    
    def retrieve_with_reasoning(
        self,
        query: str,
        user_role: str,
        user_department: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        check_rbac: bool = True
    ) -> IntelligentResponse:
        """
        Retrieve with full reasoning chain: Think → Evaluate → Respond → Rethink
        """
        start_time = datetime.now()
        self.reasoning_steps = []
        
        # STEP 1: THINK - Analyze query intent
        query_intent = self._think_analyze_query(query, user_role, user_department)
        
        # STEP 2: EVALUATE - Check access and relevance
        department_access = self._evaluate_access(query_intent, user_role, user_department)
        
        # STEP 3: ATTENTION - Focus on relevant aspects
        attention_weights = self._apply_attention(query, query_intent)
        
        # STEP 4: RETRIEVE - Get relevant documents
        retrieved_docs, access_violations = self._retrieve_documents(
            query, query_intent, user_role, department_access, 
            top_k, similarity_threshold, check_rbac
        )
        
        # STEP 5: EVALUATE FAITHFULNESS
        from src.utils.enhanced_retrieval import EnhancedRetriever
        basic_retriever = EnhancedRetriever(self.db, self.classifier)
        faithfulness = basic_retriever._calculate_faithfulness(query, retrieved_docs)
        
        # STEP 6: RESPOND - Generate initial answer
        initial_answer = self._respond_generate_answer(
            query, retrieved_docs, faithfulness, query_intent
        )
        
        # STEP 7: RETHINK - Validate and refine answer
        final_answer = self._rethink_validate_answer(
            query, initial_answer, retrieved_docs, faithfulness, 
            query_intent, department_access
        )
        
        response_time = (datetime.now() - start_time).total_seconds()
        
        return IntelligentResponse(
            query=query,
            final_answer=final_answer,
            reasoning_steps=self.reasoning_steps,
            retrieved_docs=retrieved_docs,
            faithfulness=faithfulness,
            query_intent=query_intent,
            department_access=department_access,
            response_time=response_time,
            user_context={
                "role": user_role,
                "department": user_department,
                "access_level": self.classifier.get_role_level(user_role),
                "access_violations": access_violations
            }
        )
    
    def _think_analyze_query(
        self, 
        query: str, 
        user_role: str, 
        user_department: Optional[str]
    ) -> Dict[str, Any]:
        """STEP 1: Think - Analyze query intent and classify."""
        
        query_lower = query.lower().strip()
        
        # Check for greeting/casual queries
        greetings = ["hi", "hello", "hey", "greetings", "good morning", 
                    "good afternoon", "good evening"]
        is_greeting = any(greeting == query_lower for greeting in greetings)
        
        # Check for help requests
        help_keywords = ["help", "how to", "what is", "explain", "guide"]
        is_help_request = any(keyword in query_lower for keyword in help_keywords)
        
        # Identify relevant departments
        relevant_departments = []
        department_scores = {}
        
        for dept, info in self.DEPARTMENTS.items():
            score = sum(1 for keyword in info["keywords"] if keyword in query_lower)
            if score > 0:
                department_scores[dept] = score
                relevant_departments.append(dept)
        
        # Sort by relevance
        relevant_departments.sort(key=lambda d: department_scores.get(d, 0), reverse=True)
        
        # Determine query type
        if is_greeting:
            query_type = "greeting"
            intent = "User is greeting, not asking for specific information"
        elif is_help_request:
            query_type = "help_request"
            intent = "User needs assistance or explanation"
        elif not relevant_departments:
            query_type = "unclear"
            intent = "Query lacks specific context or keywords"
        elif len(relevant_departments) == 1:
            query_type = "specific"
            intent = f"Query about {relevant_departments[0]} department"
        else:
            query_type = "cross_departmental"
            intent = f"Query spans multiple departments: {', '.join(relevant_departments[:3])}"
        
        result = {
            "query_type": query_type,
            "intent": intent,
            "is_greeting": is_greeting,
            "is_help_request": is_help_request,
            "relevant_departments": relevant_departments,
            "department_scores": department_scores,
            "needs_clarification": query_type in ["unclear", "greeting"]
        }
        
        # Log reasoning step
        confidence = 0.9 if query_type == "specific" else (0.6 if query_type == "cross_departmental" else 0.3)
        self.reasoning_steps.append(ReasoningStep(
            step_type="think",
            content=f"Query Analysis: {intent}. Type: {query_type}. "
                   f"Departments: {', '.join(relevant_departments[:3]) if relevant_departments else 'None identified'}",
            confidence=confidence,
            timestamp=datetime.now(),
            metadata=result
        ))
        
        return result
    
    def _evaluate_access(
        self,
        query_intent: Dict[str, Any],
        user_role: str,
        user_department: Optional[str]
    ) -> Dict[str, Any]:
        """STEP 2: Evaluate - Check if user has access to queried departments."""
        
        user_level = self.classifier.get_role_level(user_role)
        relevant_departments = query_intent.get("relevant_departments", [])
        
        access_results = {}
        allowed_departments = []
        denied_departments = []
        
        for dept in relevant_departments:
            dept_info = self.DEPARTMENTS.get(dept, {})
            required_level = dept_info.get("access_level", 5)
            allowed_roles = dept_info.get("allowed_roles", [])
            
            # Check both level and role
            has_level_access = user_level <= required_level
            has_role_access = user_role in allowed_roles
            
            # If user has department specified, give preference to their department
            is_user_dept = user_department and user_department.lower() == dept.lower()
            
            if has_level_access and has_role_access:
                access_results[dept] = {"allowed": True, "reason": "Sufficient access level and role"}
                allowed_departments.append(dept)
            elif is_user_dept:
                access_results[dept] = {"allowed": True, "reason": "User's own department"}
                allowed_departments.append(dept)
            else:
                reason = f"Requires level {required_level} (you have {user_level}) and role in {allowed_roles}"
                access_results[dept] = {"allowed": False, "reason": reason}
                denied_departments.append(dept)
        
        result = {
            "access_results": access_results,
            "allowed_departments": allowed_departments,
            "denied_departments": denied_departments,
            "has_any_access": len(allowed_departments) > 0,
            "user_department": user_department
        }
        
        # Log reasoning step
        self.reasoning_steps.append(ReasoningStep(
            step_type="evaluate",
            content=f"Access Check: User '{user_role}' (level {user_level}, dept: {user_department}) "
                   f"can access {len(allowed_departments)} of {len(relevant_departments)} departments. "
                   f"Allowed: {', '.join(allowed_departments) if allowed_departments else 'None'}. "
                   f"Denied: {', '.join(denied_departments) if denied_departments else 'None'}",
            confidence=0.95,
            timestamp=datetime.now(),
            metadata=result
        ))
        
        return result
    
    def _apply_attention(
        self,
        query: str,
        query_intent: Dict[str, Any]
    ) -> Dict[str, float]:
        """STEP 3: Apply attention mechanism to focus on important query aspects."""
        
        query_terms = query.lower().split()
        attention_weights = {}
        
        # Weight terms based on department relevance
        for term in query_terms:
            weight = 0.5  # Base weight
            
            # Increase weight for department keywords
            for dept, info in self.DEPARTMENTS.items():
                if term in info["keywords"]:
                    weight += 0.3
                    break
            
            # Increase weight for action words
            action_words = ["show", "get", "find", "list", "what", "how", "why", "when"]
            if term in action_words:
                weight += 0.2
            
            attention_weights[term] = min(weight, 1.0)
        
        # Log reasoning step
        top_terms = sorted(attention_weights.items(), key=lambda x: x[1], reverse=True)[:5]
        self.reasoning_steps.append(ReasoningStep(
            step_type="attention",
            content=f"Attention Focus: Weighted {len(attention_weights)} query terms. "
                   f"Top terms: {', '.join([f'{t}({w:.2f})' for t, w in top_terms])}",
            confidence=0.8,
            timestamp=datetime.now(),
            metadata={"attention_weights": attention_weights}
        ))
        
        return attention_weights
    
    def _retrieve_documents(
        self,
        query: str,
        query_intent: Dict[str, Any],
        user_role: str,
        department_access: Dict[str, Any],
        top_k: int,
        similarity_threshold: float,
        check_rbac: bool
    ) -> Tuple[List[Any], List[Dict[str, Any]]]:
        """STEP 4: Retrieve relevant documents with RBAC."""
        
        from src.utils.enhanced_retrieval import RetrievalMetadata
        
        # Handle special cases
        if query_intent.get("is_greeting"):
            self.reasoning_steps.append(ReasoningStep(
                step_type="retrieve",
                content="No document retrieval needed for greeting. Will provide conversational response.",
                confidence=1.0,
                timestamp=datetime.now(),
                metadata={"skipped": True, "reason": "greeting"}
            ))
            return [], []
        
        if not department_access.get("has_any_access") and check_rbac:
            self.reasoning_steps.append(ReasoningStep(
                step_type="retrieve",
                content=f"No access to any relevant departments. Cannot retrieve documents.",
                confidence=0.9,
                timestamp=datetime.now(),
                metadata={"blocked": True, "reason": "no_access"}
            ))
            return [], []
        
        # Get all documents
        all_docs = self.db.get_all_documents()
        
        if not all_docs:
            self.reasoning_steps.append(ReasoningStep(
                step_type="retrieve",
                content="No documents in database.",
                confidence=1.0,
                timestamp=datetime.now(),
                metadata={"empty_db": True}
            ))
            return [], []
        
        # Score documents
        allowed_departments = department_access.get("allowed_departments", [])
        user_level = self.classifier.get_role_level(user_role)
        
        scored_docs = []
        access_violations = []
        query_terms = set(query.lower().split())
        
        for doc in all_docs:
            content = doc.get("content", "").lower()
            doc_classification = doc.get("classification", "public")
            doc_min_level = doc.get("min_access_level", 5)
            
            # Check RBAC
            if check_rbac:
                # Check if document department is in user's allowed departments
                is_allowed_dept = doc_classification in allowed_departments or doc_classification == "public"
                
                # Also check if user has sufficient access level
                has_level_access = user_level <= doc_min_level
                
                # If user's department matches document department, always allow (own department data)
                user_dept = department_access.get("user_department", "").lower()
                is_own_dept = user_dept and doc_classification.lower() == user_dept
                
                # Allow if: (in allowed departments AND has level access) OR is own department
                if not ((is_allowed_dept and has_level_access) or is_own_dept):
                    reason = f"Document from '{doc_classification}' department"
                    if not is_allowed_dept:
                        reason += f", user can only access: {', '.join(allowed_departments) if allowed_departments else 'none'}"
                    if not has_level_access:
                        reason += f". Requires level {doc_min_level}, user has level {user_level}"
                    
                    access_violations.append({
                        "doc_id": doc.get("doc_id"),
                        "classification": doc_classification,
                        "reason": reason
                    })
                    continue
            
            # Calculate relevance score
            matches = sum(1 for term in query_terms if term in content)
            if matches > 0:
                score = min(matches / len(query_terms), 1.0) * 0.9
                
                # Boost score if document is from user's department
                user_dept = department_access.get("user_department", "").lower()
                if user_dept and doc_classification.lower() == user_dept:
                    score = min(score * 1.2, 1.0)
                
                scored_docs.append((score, doc))
        
        # Sort and filter
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        scored_docs = [(score, doc) for score, doc in scored_docs if score >= similarity_threshold]
        
        # Create metadata objects
        retrieved_docs = []
        for similarity_score, doc in scored_docs[:top_k]:
            metadata_dict = self.db.get_metadata(doc.get("doc_id", ""))
            
            metadata = RetrievalMetadata(
                doc_id=doc.get("doc_id", "unknown"),
                source=doc.get("source", "unknown"),
                classification=doc.get("classification", "public"),
                min_access_level=doc.get("min_access_level", 5),
                similarity_score=similarity_score,
                chunk_id=doc.get("chunk_id", 0),
                metadata_tags=metadata_dict,
                confidence_score=float(metadata_dict.get("confidence_score", 0.8))
            )
            retrieved_docs.append(metadata)
        
        # Log reasoning step
        self.reasoning_steps.append(ReasoningStep(
            step_type="retrieve",
            content=f"Retrieved {len(retrieved_docs)} documents from {len(allowed_departments)} allowed departments. "
                   f"Blocked {len(access_violations)} documents due to access restrictions.",
            confidence=0.85 if retrieved_docs else 0.3,
            timestamp=datetime.now(),
            metadata={
                "retrieved_count": len(retrieved_docs),
                "violations_count": len(access_violations),
                "allowed_departments": allowed_departments
            }
        ))
        
        return retrieved_docs, access_violations
    
    def _respond_generate_answer(
        self,
        query: str,
        retrieved_docs: List[Any],
        faithfulness: Any,
        query_intent: Dict[str, Any]
    ) -> str:
        """STEP 5: Generate initial response."""
        
        # Handle greetings
        if query_intent.get("is_greeting"):
            answer = (
                "Hello! 👋 I'm your RAG assistant. I can help you find information about:\n\n"
                "- 🔒 **Security incidents** (breaches, vulnerabilities, threats)\n"
                "- 💰 **Finance issues** (payments, billing, revenue)\n"
                "- 👨‍💻 **Engineering problems** (deployments, infrastructure, bugs)\n"
                "- 👥 **HR matters** (onboarding, recruitment, policies)\n"
                "- 📋 **Compliance** (GDPR, regulations, audits)\n"
                "- 🎯 **Customer issues** (support, escalations, service)\n\n"
                "What would you like to know? Please ask a specific question!"
            )
            self.reasoning_steps.append(ReasoningStep(
                step_type="respond",
                content="Generated greeting response with available topics.",
                confidence=1.0,
                timestamp=datetime.now(),
                metadata={"response_type": "greeting"}
            ))
            return answer
        
        # No documents case
        if not retrieved_docs:
            if query_intent.get("needs_clarification"):
                answer = (
                    f"I need more context to answer your query: '{query}'\n\n"
                    f"**Suggestions:**\n"
                    f"- Specify which department: engineering, security, finance, HR, compliance, or customer\n"
                    f"- Include relevant keywords like 'incident', 'issue', 'problem', 'error'\n"
                    f"- Be specific about what you're looking for\n\n"
                    f"**Example queries:**\n"
                    f"- 'Show me security incidents in Azure'\n"
                    f"- 'What payment processing issues occurred?'\n"
                    f"- 'List engineering deployment problems'\n"
                )
            else:
                answer = (
                    f"I couldn't find relevant information to answer: '{query}'\n\n"
                    f"This might be because:\n"
                    f"- You don't have access to the {', '.join(query_intent.get('relevant_departments', []))} department(s)\n"
                    f"- No documents match your query in accessible departments\n"
                    f"- The information is not in my knowledge base\n\n"
                    f"Try:\n"
                    f"- Requesting information from departments you have access to\n"
                    f"- Using different keywords\n"
                    f"- Asking your manager for elevated access\n"
                )
            
            self.reasoning_steps.append(ReasoningStep(
                step_type="respond",
                content="No documents available. Provided guidance for better query.",
                confidence=0.7,
                timestamp=datetime.now(),
                metadata={"response_type": "no_data_guidance"}
            ))
            return answer
        
        # Generate answer from documents
        answer_parts = [f"**Found {len(retrieved_docs)} relevant documents:**\n"]
        
        for i, doc in enumerate(retrieved_docs[:3], 1):
            # Get document content
            all_docs = self.db.get_all_documents()
            content_preview = ""
            for d in all_docs:
                if d.get("doc_id") == doc.doc_id:
                    content = d.get("content", "")
                    content_preview = content[:250] + "..." if len(content) > 250 else content
                    break
            
            answer_parts.append(
                f"\n**Document {i}** (`{doc.classification.upper()}` dept, similarity: {doc.similarity_score:.3f}):\n"
                f"{content_preview}\n"
            )
        
        answer = "\n".join(answer_parts)
        
        self.reasoning_steps.append(ReasoningStep(
            step_type="respond",
            content=f"Generated answer from {len(retrieved_docs)} documents with avg similarity {faithfulness.avg_similarity:.3f}",
            confidence=faithfulness.avg_similarity,
            timestamp=datetime.now(),
            metadata={"doc_count": len(retrieved_docs), "faithfulness": faithfulness.confidence_level}
        ))
        
        return answer
    
    def _rethink_validate_answer(
        self,
        query: str,
        initial_answer: str,
        retrieved_docs: List[Any],
        faithfulness: Any,
        query_intent: Dict[str, Any],
        department_access: Dict[str, Any]
    ) -> str:
        """STEP 6: Rethink - Validate and refine the answer."""
        
        # Check if answer is appropriate
        issues = []
        refinements = []
        
        # Check 1: Does answer address the query?
        if query_intent.get("is_greeting"):
            # Greeting is already handled appropriately
            validation_result = "Appropriate greeting response provided"
            confidence = 1.0
        elif not retrieved_docs:
            # Check if guidance was provided
            if "Suggestions:" in initial_answer or "Try:" in initial_answer:
                validation_result = "Provided helpful guidance for unclear/blocked query"
                confidence = 0.8
            else:
                issues.append("Answer lacks actionable guidance")
                confidence = 0.5
        else:
            # Check faithfulness
            if faithfulness.confidence_level == "no_data":
                issues.append("Very low confidence in answer")
                refinements.append("⚠️ **CAUTION:** Data confidence is very low. Verify information independently.")
                confidence = 0.3
            elif faithfulness.confidence_level == "low":
                refinements.append("⚠️ **NOTE:** Moderate confidence. Consider requesting more specific information.")
                confidence = 0.6
            else:
                validation_result = f"Good answer with {faithfulness.confidence_level} confidence"
                confidence = 0.9
        
        # Check 2: Are there access restrictions user should know about?
        denied_depts = department_access.get("denied_departments", [])
        if denied_depts and retrieved_docs:
            refinements.append(
                f"\n📌 **Access Note:** You don't have access to {', '.join(denied_depts)} department(s). "
                f"Some relevant information may be hidden."
            )
        
        # Build final answer
        final_answer = initial_answer
        
        # Add refinements
        if refinements:
            final_answer += "\n\n" + "\n".join(refinements)
        
        # Add metadata footer for document-based answers
        if retrieved_docs:
            final_answer += f"\n\n---\n**Query Analysis:**\n"
            final_answer += f"- **Intent:** {query_intent.get('intent', 'Unknown')}\n"
            final_answer += f"- **Departments:** {', '.join(query_intent.get('relevant_departments', ['None']))}\n"
            final_answer += f"- **Confidence:** {faithfulness.confidence_level.upper()}\n"
            final_answer += f"- **Data Coverage:** {faithfulness.data_coverage:.1%}\n"
            final_answer += f"- **Sources:** {len(retrieved_docs)} documents (avg similarity: {faithfulness.avg_similarity:.3f})\n"
        
        # Log reasoning step
        self.reasoning_steps.append(ReasoningStep(
            step_type="rethink",
            content=f"Validation: {validation_result if 'validation_result' in locals() else 'Completed with ' + str(len(refinements)) + ' refinements'}. "
                   f"Issues: {len(issues)}. Refinements: {len(refinements)}",
            confidence=confidence,
            timestamp=datetime.now(),
            metadata={
                "issues": issues,
                "refinements_count": len(refinements),
                "final_confidence": confidence
            }
        ))
        
        return final_answer
