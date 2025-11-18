"""
Enhanced Retrieval Response with Metadata and Faithfulness Tracking
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RetrievalMetadata:
    """Metadata for a single retrieved document."""
    doc_id: str
    source: str
    classification: str
    min_access_level: int
    similarity_score: float
    chunk_id: int
    metadata_tags: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source": self.source,
            "classification": self.classification,
            "min_access_level": self.min_access_level,
            "similarity_score": self.similarity_score,
            "chunk_id": self.chunk_id,
            "metadata_tags": self.metadata_tags,
            "confidence_score": self.confidence_score
        }


@dataclass
class FaithfulnessMetrics:
    """Metrics for answer faithfulness."""
    has_supporting_data: bool
    data_coverage: float  # 0-1: how much of query is covered by data
    source_count: int
    avg_similarity: float
    min_similarity: float
    max_similarity: float
    confidence_level: str  # "high", "medium", "low", "no_data"
    reasoning: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_supporting_data": self.has_supporting_data,
            "data_coverage": self.data_coverage,
            "source_count": self.source_count,
            "avg_similarity": self.avg_similarity,
            "min_similarity": self.min_similarity,
            "max_similarity": self.max_similarity,
            "confidence_level": self.confidence_level,
            "reasoning": self.reasoning
        }


@dataclass
class EnhancedRAGResponse:
    """Enhanced RAG response with full metadata and faithfulness tracking."""
    query: str
    answer: str
    retrieved_docs: List[RetrievalMetadata]
    faithfulness: FaithfulnessMetrics
    timestamp: datetime
    response_time: float
    user_role: Optional[str] = None
    access_violations: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "retrieved_docs": [doc.to_dict() for doc in self.retrieved_docs],
            "faithfulness": self.faithfulness.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "response_time": self.response_time,
            "user_role": self.user_role,
            "access_violations": self.access_violations
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            f"Query: {self.query}",
            f"",
            f"Answer: {self.answer}",
            f"",
            f"Faithfulness:",
            f"  - Confidence: {self.faithfulness.confidence_level.upper()}",
            f"  - Data Coverage: {self.faithfulness.data_coverage:.1%}",
            f"  - Sources Used: {self.faithfulness.source_count}",
            f"  - Avg Similarity: {self.faithfulness.avg_similarity:.3f}",
            f"  - Reasoning: {self.faithfulness.reasoning}",
            f"",
            f"Retrieved Documents: {len(self.retrieved_docs)}",
        ]
        
        for i, doc in enumerate(self.retrieved_docs, 1):
            lines.append(f"  {i}. {doc.source} (similarity: {doc.similarity_score:.3f}, classification: {doc.classification})")
        
        if self.access_violations:
            lines.append(f"")
            lines.append(f"Access Violations: {len(self.access_violations)}")
            for violation in self.access_violations:
                lines.append(f"  - {violation.get('reason', 'Unknown')}")
        
        lines.append(f"")
        lines.append(f"Response Time: {self.response_time:.3f}s")
        
        return "\n".join(lines)


class EnhancedRetriever:
    """Retriever with metadata tracking and faithfulness assessment."""
    
    def __init__(self, db, classifier=None):
        """
        Initialize enhanced retriever.
        
        Args:
            db: RAGDatabase instance
            classifier: IncidentClassifier instance (optional)
        """
        self.db = db
        
        if classifier is None:
            from src.utils.incident_classifier import IncidentClassifier
            classifier = IncidentClassifier()
        
        self.classifier = classifier
    
    def retrieve_with_metadata(
        self,
        query: str,
        user_role: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        check_rbac: bool = True
    ) -> EnhancedRAGResponse:
        """
        Retrieve documents with full metadata and faithfulness tracking.
        
        Args:
            query: User query
            user_role: Role of user making query
            top_k: Number of documents to retrieve
            similarity_threshold: Minimum similarity score
            check_rbac: Whether to enforce RBAC
        
        Returns:
            EnhancedRAGResponse with full metadata
        """
        start_time = datetime.now()
        
        # Get user access level
        user_level = self.classifier.get_role_level(user_role)
        
        # Retrieve documents from database
        all_docs = self.db.get_all_documents()
        
        if not all_docs:
            # No data available
            return self._create_no_data_response(query, user_role, start_time)
        
        # Calculate relevance scores using keyword matching (simple semantic search)
        scored_docs = []
        query_terms = set(query.lower().split())
        
        for doc in all_docs:
            content = doc.get("content", "").lower()
            
            # Calculate simple relevance score based on keyword matching
            matches = sum(1 for term in query_terms if term in content)
            if matches > 0:
                # Normalize score (0-1 range)
                score = min(matches / len(query_terms), 1.0) * 0.9  # Max 0.9 for keyword match
                scored_docs.append((score, doc))
        
        # Sort by score descending
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        # Filter by RBAC if enabled
        retrieved_docs = []
        access_violations = []
        
        for similarity_score, doc in scored_docs:
            if similarity_score < similarity_threshold:
                continue
                
            doc_classification = doc.get("classification", "public")
            doc_min_level = doc.get("min_access_level", 5)
            
            # Check RBAC
            if check_rbac:
                access_result = self.classifier.validate_access(
                    user_role, user_level, doc_classification, doc_min_level
                )
                
                if not access_result["allowed"]:
                    access_violations.append({
                        "doc_id": doc.get("doc_id"),
                        "reason": access_result["reason"],
                        "classification": doc_classification
                    })
                    continue
            
            # Create metadata object
            # Get document metadata from database
            metadata_dict = self.db.get_metadata(doc.get("doc_id", ""))
            
            metadata = RetrievalMetadata(
                doc_id=doc.get("doc_id", "unknown"),
                source=doc.get("source", "unknown"),
                classification=doc_classification,
                min_access_level=doc_min_level,
                similarity_score=similarity_score,
                chunk_id=doc.get("chunk_id", 0),
                metadata_tags=metadata_dict,
                confidence_score=float(metadata_dict.get("confidence_score", 0.8))
            )
            
            retrieved_docs.append(metadata)
            
            if len(retrieved_docs) >= top_k:
                break
        
        # Calculate faithfulness metrics
        faithfulness = self._calculate_faithfulness(query, retrieved_docs)
        
        # Generate answer
        if faithfulness.has_supporting_data:
            answer = self._generate_answer(query, retrieved_docs, faithfulness)
        else:
            answer = (
                f"I don't have sufficient data in my knowledge base to answer: '{query}'. "
                f"The available documents do not contain relevant information on this topic. "
                f"Retrieved {len(retrieved_docs)} documents but data coverage is only "
                f"{faithfulness.data_coverage:.1%}. Please consult additional sources or "
                f"provide more context."
            )
        
        # Calculate response time
        response_time = (datetime.now() - start_time).total_seconds()
        
        return EnhancedRAGResponse(
            query=query,
            answer=answer,
            retrieved_docs=retrieved_docs,
            faithfulness=faithfulness,
            timestamp=start_time,
            response_time=response_time,
            user_role=user_role,
            access_violations=access_violations
        )
    
    def _create_no_data_response(
        self, 
        query: str, 
        user_role: str, 
        start_time: datetime
    ) -> EnhancedRAGResponse:
        """Create response when no data is available."""
        faithfulness = FaithfulnessMetrics(
            has_supporting_data=False,
            data_coverage=0.0,
            source_count=0,
            avg_similarity=0.0,
            min_similarity=0.0,
            max_similarity=0.0,
            confidence_level="no_data",
            reasoning="No documents in knowledge base"
        )
        
        answer = (
            f"I cannot answer this question because there are no documents "
            f"in my knowledge base. Please ingest data before making queries."
        )
        
        response_time = (datetime.now() - start_time).total_seconds()
        
        return EnhancedRAGResponse(
            query=query,
            answer=answer,
            retrieved_docs=[],
            faithfulness=faithfulness,
            timestamp=start_time,
            response_time=response_time,
            user_role=user_role
        )
    
    def _extract_metadata_tags(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant metadata tags from document."""
        tags = {}
        
        # Copy known metadata fields
        for key in ["platform", "severity", "category", "impacted_dollar", 
                   "resource_type", "financial_impact", "is_critical"]:
            if key in doc:
                tags[key] = doc[key]
        
        return tags
    
    def _calculate_faithfulness(
        self,
        query: str,
        retrieved_docs: List[RetrievalMetadata]
    ) -> FaithfulnessMetrics:
        """Calculate faithfulness metrics for retrieved documents."""
        if not retrieved_docs:
            return FaithfulnessMetrics(
                has_supporting_data=False,
                data_coverage=0.0,
                source_count=0,
                avg_similarity=0.0,
                min_similarity=0.0,
                max_similarity=0.0,
                confidence_level="no_data",
                reasoning="No documents retrieved"
            )
        
        # Calculate metrics
        similarities = [doc.similarity_score for doc in retrieved_docs]
        avg_similarity = sum(similarities) / len(similarities)
        min_similarity = min(similarities)
        max_similarity = max(similarities)
        
        # Estimate data coverage (simplified)
        # In real system would analyze query terms vs document content
        query_terms = set(query.lower().split())
        coverage = min(len(retrieved_docs) / 3.0, 1.0)  # Simple heuristic
        
        # Determine confidence level
        if avg_similarity >= 0.8 and len(retrieved_docs) >= 3:
            confidence = "high"
            has_data = True
            reasoning = f"High similarity ({avg_similarity:.3f}) with {len(retrieved_docs)} relevant sources"
        elif avg_similarity >= 0.6 and len(retrieved_docs) >= 2:
            confidence = "medium"
            has_data = True
            reasoning = f"Moderate similarity ({avg_similarity:.3f}) with {len(retrieved_docs)} sources"
        elif avg_similarity >= 0.4:
            confidence = "low"
            has_data = True
            reasoning = f"Low similarity ({avg_similarity:.3f}), answer may be unreliable"
        else:
            confidence = "no_data"
            has_data = False
            reasoning = f"Insufficient similarity ({avg_similarity:.3f}), no reliable data available"
        
        return FaithfulnessMetrics(
            has_supporting_data=has_data,
            data_coverage=coverage,
            source_count=len(retrieved_docs),
            avg_similarity=avg_similarity,
            min_similarity=min_similarity,
            max_similarity=max_similarity,
            confidence_level=confidence,
            reasoning=reasoning
        )
    
    def _generate_answer(
        self,
        query: str,
        retrieved_docs: List[RetrievalMetadata],
        faithfulness: FaithfulnessMetrics
    ) -> str:
        """Generate answer with faithfulness disclaimers."""
        if not retrieved_docs:
            return "No relevant documents found to answer this query."
        
        # Fetch actual document content from database
        doc_contents = []
        for doc_meta in retrieved_docs[:3]:  # Use top 3 documents
            docs = self.db.get_all_documents()
            for doc in docs:
                if doc.get("doc_id") == doc_meta.doc_id:
                    content = doc.get("content", "")
                    # Truncate to first 200 characters
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    doc_contents.append({
                        "source": doc_meta.source,
                        "content": content_preview,
                        "similarity": doc_meta.similarity_score
                    })
                    break
        
        # Build answer
        answer_parts = [
            f"**Answer based on {len(retrieved_docs)} relevant documents:**",
            ""
        ]
        
        # Add document excerpts
        for i, doc in enumerate(doc_contents, 1):
            answer_parts.append(f"**Source {i}** (`{doc['source']}`, similarity: {doc['similarity']:.3f}):")
            answer_parts.append(f"{doc['content']}")
            answer_parts.append("")
        
        # Add confidence information
        answer_parts.append(f"**Confidence Level:** {faithfulness.confidence_level.upper()}")
        answer_parts.append(f"- Data Coverage: {faithfulness.data_coverage:.1%}")
        answer_parts.append(f"- Average Similarity: {faithfulness.avg_similarity:.3f}")
        answer_parts.append(f"- Sources Used: {faithfulness.source_count}")
        
        if faithfulness.confidence_level == "low":
            answer_parts.append("")
            answer_parts.append(
                "⚠️ **CAUTION:** Confidence is low. This answer may not be fully reliable. "
                "Consider requesting more specific information or consulting additional sources."
            )
        
        return "\n".join(answer_parts)
