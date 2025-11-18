"""
Deep Classification Agent - Hybrid Rule-Based + LLM Classification

This agent combines:
1. Rule-based classification (fast, deterministic)
2. LLM-based classification (Ollama, accurate for edge cases)
3. Intelligent chunking (semantic, not character-based)
4. Tree-based namespace assignment
5. RBAC level determination
"""

import json
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import requests

from src.storage import RAGDatabase
from src.utils.config_loader import ConfigLoader


@dataclass
class ChunkMetadata:
    """Metadata for a document chunk"""
    chunk_id: int
    total_chunks: int
    summary: str
    keywords: List[str]
    relationships: List[str]  # Related chunk IDs
    confidence: float


@dataclass
class ClassificationResult:
    """Result of document classification"""
    classification: str  # Department name
    confidence: float  # 0.0 to 1.0
    method: str  # "rule_based", "llm", "hybrid"
    namespace: str  # Hierarchical path
    min_access_level: int  # 1-5
    reasoning: str  # Explanation
    sub_categories: List[str]  # For tree structure
    metadata: Dict[str, Any]


class DeepClassifier:
    """
    Hybrid classification agent combining rule-based and LLM approaches
    """
    
    def __init__(self, use_llm: bool = True, ollama_url: str = "http://localhost:11434"):
        self.db = RAGDatabase()
        self.config = ConfigLoader()
        self.use_llm = use_llm
        self.ollama_url = ollama_url
        
        # Load department configurations
        self.departments = self.config.get_departments()
        
        # Confidence thresholds
        self.RULE_CONFIDENCE_THRESHOLD = 0.7
        self.LLM_FALLBACK_THRESHOLD = 0.5
        
    def classify_document(self, content: str, source: str, 
                         metadata: Optional[Dict] = None) -> ClassificationResult:
        """
        Main classification method - tries rule-based first, falls back to LLM if needed
        
        Args:
            content: Document text content
            source: Document source (filename, URL, etc.)
            metadata: Optional metadata dict
            
        Returns:
            ClassificationResult with classification details
        """
        # Step 1: Try rule-based classification
        rule_result = self._rule_based_classify(content, source)
        
        if rule_result.confidence >= self.RULE_CONFIDENCE_THRESHOLD:
            # High confidence - use rule-based result
            self._store_agent_memory(
                "classification_decision",
                {
                    "method": "rule_based",
                    "confidence": rule_result.confidence,
                    "classification": rule_result.classification
                }
            )
            return rule_result
        
        # Step 2: Low confidence - use LLM for verification/refinement
        if self.use_llm:
            llm_result = self._llm_classify(content, source, rule_result)
            
            if llm_result.confidence > rule_result.confidence:
                # LLM more confident - use its result
                self._store_agent_memory(
                    "classification_decision",
                    {
                        "method": "llm_override",
                        "rule_confidence": rule_result.confidence,
                        "llm_confidence": llm_result.confidence,
                        "classification": llm_result.classification
                    }
                )
                return llm_result
            else:
                # Combine both approaches
                hybrid_result = self._hybrid_classify(rule_result, llm_result)
                self._store_agent_memory(
                    "classification_decision",
                    {
                        "method": "hybrid",
                        "rule_confidence": rule_result.confidence,
                        "llm_confidence": llm_result.confidence,
                        "final_classification": hybrid_result.classification
                    }
                )
                return hybrid_result
        
        # Fallback to rule-based if LLM disabled
        return rule_result
    
    def _rule_based_classify(self, content: str, source: str) -> ClassificationResult:
        """
        Fast rule-based classification using keyword matching
        """
        content_lower = content.lower()
        scores = {}
        
        # Score each department based on keyword matches
        for dept_name, dept_config in self.departments.items():
            keywords = dept_config.get('keywords', [])
            score = sum(1 for keyword in keywords if keyword.lower() in content_lower)
            
            # Boost score if source filename contains department name
            if dept_name.lower() in source.lower():
                score += 5
            
            scores[dept_name] = score
        
        # Get best match
        if not scores or max(scores.values()) == 0:
            # No matches - default to generic
            classification = "general"
            confidence = 0.3
            access_level = 1
            namespace = "general/uncategorized"
        else:
            classification = max(scores, key=scores.get)
            max_score = scores[classification]
            total_keywords = len(self.departments[classification].get('keywords', []))
            
            # Calculate confidence based on match rate
            confidence = min(1.0, max_score / max(total_keywords * 0.5, 1))
            
            # Get access level from config
            access_level = self.departments[classification].get('access_level', 2)
            
            # Build namespace
            namespace = f"{classification}/general"
        
        # Determine sub-categories from content
        sub_categories = self._extract_subcategories(content, classification)
        if sub_categories:
            namespace = f"{classification}/{sub_categories[0]}"
        
        return ClassificationResult(
            classification=classification,
            confidence=confidence,
            method="rule_based",
            namespace=namespace,
            min_access_level=access_level,
            reasoning=f"Matched {scores[classification]} keywords for {classification}",
            sub_categories=sub_categories,
            metadata={"keyword_scores": scores}
        )
    
    def _llm_classify(self, content: str, source: str, 
                     rule_result: ClassificationResult) -> ClassificationResult:
        """
        Use Ollama LLM for intelligent classification
        """
        # Prepare prompt for LLM
        departments_list = ", ".join(self.departments.keys())
        
        prompt = f"""You are a document classification expert. Analyze this document and classify it.

Document Source: {source}

Document Content (first 1000 chars):
{content[:1000]}

Available Departments: {departments_list}

Rule-based classification suggested: {rule_result.classification} (confidence: {rule_result.confidence:.2f})

Tasks:
1. Classify this document into ONE of the available departments
2. Provide confidence score (0.0 to 1.0)
3. Suggest hierarchical sub-categories (e.g., hr/recruitment/policies)
4. Recommend minimum access level (1-5, where 5 is most restricted)
5. Explain your reasoning

Respond in JSON format:
{{
    "classification": "department_name",
    "confidence": 0.85,
    "sub_categories": ["subcategory1", "subcategory2"],
    "min_access_level": 3,
    "reasoning": "explanation here"
}}
"""
        
        try:
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama3.2:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Low temp for consistency
                        "top_p": 0.9
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_output = result.get('response', '{}')
                
                # Parse JSON from LLM response
                # Extract JSON from markdown code blocks if present
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_output, re.DOTALL)
                if json_match:
                    llm_output = json_match.group(1)
                else:
                    # Try to find JSON object
                    json_match = re.search(r'\{.*\}', llm_output, re.DOTALL)
                    if json_match:
                        llm_output = json_match.group(0)
                
                parsed = json.loads(llm_output)
                
                classification = parsed.get('classification', rule_result.classification)
                confidence = float(parsed.get('confidence', 0.5))
                sub_categories = parsed.get('sub_categories', [])
                min_access_level = int(parsed.get('min_access_level', 2))
                reasoning = parsed.get('reasoning', 'LLM classification')
                
                # Validate classification is in allowed departments
                if classification not in self.departments:
                    classification = rule_result.classification
                    confidence *= 0.7  # Reduce confidence for invalid classification
                
                # Build namespace
                namespace = classification
                if sub_categories:
                    namespace = f"{classification}/{'/'.join(sub_categories[:2])}"
                else:
                    namespace = f"{classification}/general"
                
                return ClassificationResult(
                    classification=classification,
                    confidence=confidence,
                    method="llm",
                    namespace=namespace,
                    min_access_level=min_access_level,
                    reasoning=reasoning,
                    sub_categories=sub_categories,
                    metadata={
                        "llm_model": "llama3.2:latest",
                        "llm_raw_output": llm_output[:500]
                    }
                )
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            print(f"LLM classification failed: {e}")
            # Fallback to rule-based
            return ClassificationResult(
                classification=rule_result.classification,
                confidence=rule_result.confidence * 0.8,
                method="llm_fallback",
                namespace=rule_result.namespace,
                min_access_level=rule_result.min_access_level,
                reasoning=f"LLM failed, using rule-based: {str(e)}",
                sub_categories=rule_result.sub_categories,
                metadata={"error": str(e)}
            )
    
    def _hybrid_classify(self, rule_result: ClassificationResult, 
                        llm_result: ClassificationResult) -> ClassificationResult:
        """
        Combine rule-based and LLM results with weighted averaging
        """
        # If both agree, high confidence
        if rule_result.classification == llm_result.classification:
            confidence = (rule_result.confidence + llm_result.confidence) / 2
            confidence = min(1.0, confidence * 1.2)  # Boost for agreement
            
            return ClassificationResult(
                classification=rule_result.classification,
                confidence=confidence,
                method="hybrid_agreement",
                namespace=llm_result.namespace,  # LLM usually better at hierarchy
                min_access_level=max(rule_result.min_access_level, llm_result.min_access_level),
                reasoning=f"Rule-based and LLM agree: {rule_result.classification}",
                sub_categories=llm_result.sub_categories or rule_result.sub_categories,
                metadata={
                    "rule_confidence": rule_result.confidence,
                    "llm_confidence": llm_result.confidence
                }
            )
        else:
            # Disagreement - use higher confidence result
            if llm_result.confidence > rule_result.confidence:
                return ClassificationResult(
                    classification=llm_result.classification,
                    confidence=llm_result.confidence,
                    method="hybrid_llm_preferred",
                    namespace=llm_result.namespace,
                    min_access_level=llm_result.min_access_level,
                    reasoning=f"LLM override: {llm_result.classification} vs rule-based {rule_result.classification}",
                    sub_categories=llm_result.sub_categories,
                    metadata={
                        "rule_suggestion": rule_result.classification,
                        "llm_suggestion": llm_result.classification
                    }
                )
            else:
                return ClassificationResult(
                    classification=rule_result.classification,
                    confidence=rule_result.confidence,
                    method="hybrid_rule_preferred",
                    namespace=rule_result.namespace,
                    min_access_level=rule_result.min_access_level,
                    reasoning=f"Rule-based preferred: {rule_result.classification} vs LLM {llm_result.classification}",
                    sub_categories=rule_result.sub_categories,
                    metadata={
                        "rule_suggestion": rule_result.classification,
                        "llm_suggestion": llm_result.classification
                    }
                )
    
    def _extract_subcategories(self, content: str, department: str) -> List[str]:
        """
        Extract sub-categories from content based on department
        """
        content_lower = content.lower()
        subcategories = []
        
        # Department-specific subcategory patterns
        patterns = {
            'hr': {
                'recruitment': ['hiring', 'interview', 'candidate', 'job posting', 'onboarding'],
                'payroll': ['salary', 'compensation', 'pay', 'wage', 'bonus'],
                'benefits': ['insurance', 'health', '401k', 'retirement', 'pto', 'vacation'],
                'policies': ['policy', 'handbook', 'guidelines', 'code of conduct'],
                'performance': ['review', 'evaluation', 'appraisal', 'feedback']
            },
            'engineering': {
                'infrastructure': ['server', 'cloud', 'aws', 'azure', 'kubernetes', 'docker'],
                'deployment': ['deploy', 'release', 'cicd', 'pipeline', 'build'],
                'documentation': ['api', 'guide', 'tutorial', 'readme', 'specification'],
                'security': ['vulnerability', 'encryption', 'auth', 'ssl', 'certificate'],
                'architecture': ['design', 'diagram', 'component', 'service', 'microservice']
            },
            'finance': {
                'accounting': ['ledger', 'journal', 'balance', 'account', 'bookkeeping'],
                'budgets': ['budget', 'forecast', 'planning', 'allocation', 'expense'],
                'invoicing': ['invoice', 'bill', 'payment', 'receivable', 'payable'],
                'reports': ['financial report', 'quarterly', 'annual', 'statement']
            },
            'security': {
                'incidents': ['breach', 'attack', 'threat', 'vulnerability', 'compromise'],
                'policies': ['security policy', 'compliance', 'standard', 'requirement'],
                'audits': ['audit', 'assessment', 'review', 'compliance check'],
                'access': ['permission', 'access control', 'authentication', 'authorization']
            },
            'customer': {
                'support': ['ticket', 'issue', 'problem', 'help', 'assist'],
                'feedback': ['feedback', 'survey', 'review', 'rating', 'satisfaction'],
                'documentation': ['faq', 'knowledge base', 'help article', 'guide']
            },
            'compliance': {
                'regulations': ['gdpr', 'hipaa', 'sox', 'regulation', 'law'],
                'audits': ['audit', 'inspection', 'review', 'assessment'],
                'policies': ['policy', 'procedure', 'standard', 'requirement']
            }
        }
        
        if department in patterns:
            for subcategory, keywords in patterns[department].items():
                matches = sum(1 for keyword in keywords if keyword in content_lower)
                if matches >= 2:  # At least 2 keyword matches
                    subcategories.append(subcategory)
        
        return subcategories[:3]  # Return top 3
    
    def intelligent_chunk(self, content: str, max_chunk_size: int = 1000) -> List[Tuple[str, ChunkMetadata]]:
        """
        Intelligent semantic chunking using LLM
        
        Args:
            content: Full document content
            max_chunk_size: Maximum characters per chunk
            
        Returns:
            List of (chunk_text, chunk_metadata) tuples
        """
        # Simple approach: Split by paragraphs first
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            if current_size + para_size > max_chunk_size and current_chunk:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(chunk_text)
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        # Add final chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        # Generate metadata for each chunk
        total_chunks = len(chunks)
        result = []
        
        for idx, chunk_text in enumerate(chunks):
            # Extract keywords (simple approach)
            keywords = self._extract_keywords(chunk_text)
            
            # Generate summary (first 100 chars)
            summary = chunk_text[:100].replace('\n', ' ') + "..."
            
            metadata = ChunkMetadata(
                chunk_id=idx + 1,
                total_chunks=total_chunks,
                summary=summary,
                keywords=keywords,
                relationships=[],  # Could be enhanced with similarity
                confidence=0.8  # Default confidence
            )
            
            result.append((chunk_text, metadata))
        
        # Store chunking pattern in agent memory
        self._store_agent_memory(
            "chunking_pattern",
            {
                "total_chunks": total_chunks,
                "avg_chunk_size": sum(len(c) for c in chunks) // total_chunks,
                "method": "paragraph_based"
            }
        )
        
        return result
    
    def _extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract important keywords from text
        """
        # Simple keyword extraction (could be enhanced with TF-IDF)
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        
        # Common stop words
        stop_words = {'that', 'this', 'with', 'from', 'have', 'will', 'been', 'were', 'your', 'their'}
        
        # Filter and count
        word_counts = {}
        for word in words:
            if word not in stop_words:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Get top N
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:top_n]]
    
    def build_tree_index(self, classification: str, namespace: str, doc_id: str):
        """
        Build and maintain hierarchical tree index in agent_memory
        
        Args:
            classification: Department classification
            namespace: Full namespace path (e.g., hr/recruitment/policies)
            doc_id: Document identifier
        """
        # Load existing tree from agent memory
        tree_key = f"tree_index_{classification}"
        existing_tree = self._get_agent_memory(tree_key)
        
        if existing_tree:
            tree = json.loads(existing_tree)
        else:
            tree = {
                "root": classification,
                "nodes": {},
                "document_count": 0,
                "last_updated": datetime.now().isoformat()
            }
        
        # Parse namespace into path components
        path_parts = namespace.split('/')
        
        # Build tree structure
        current_path = ""
        for part in path_parts:
            current_path = f"{current_path}/{part}" if current_path else part
            
            if current_path not in tree["nodes"]:
                tree["nodes"][current_path] = {
                    "name": part,
                    "full_path": current_path,
                    "parent": "/".join(path_parts[:path_parts.index(part)]) if part != classification else None,
                    "children": [],
                    "documents": [],
                    "document_count": 0
                }
            
            # Add document to leaf node
            if current_path == namespace:
                if doc_id not in tree["nodes"][current_path]["documents"]:
                    tree["nodes"][current_path]["documents"].append(doc_id)
                    tree["nodes"][current_path]["document_count"] += 1
            
            # Update parent's children list
            if len(path_parts) > 1 and part != classification:
                parent_path = "/".join(path_parts[:path_parts.index(part)])
                if parent_path and current_path not in tree["nodes"][parent_path]["children"]:
                    tree["nodes"][parent_path]["children"].append(current_path)
        
        tree["document_count"] = sum(node["document_count"] for node in tree["nodes"].values())
        tree["last_updated"] = datetime.now().isoformat()
        
        # Store updated tree
        self._store_agent_memory(tree_key, json.dumps(tree))
        
        return tree
    
    def get_tree_index(self, classification: str) -> Optional[Dict]:
        """
        Retrieve tree index for a classification
        """
        tree_key = f"tree_index_{classification}"
        tree_data = self._get_agent_memory(tree_key)
        
        if tree_data:
            return json.loads(tree_data)
        return None
    
    def _store_agent_memory(self, key: str, value: Any, memory_type: str = "state", 
                           namespace: str = "global", expires_hours: Optional[int] = None):
        """
        Store data in agent_memory table
        """
        # Convert value to JSON if it's a dict
        if isinstance(value, dict):
            value_str = json.dumps(value)
        else:
            value_str = str(value)
        
        # Calculate expiration
        expires_at = None
        if expires_hours:
            from datetime import timedelta
            expires_at = datetime.now() + timedelta(hours=expires_hours)
            expires_at = expires_at.isoformat()
        
        # Insert or update
        self.db.store_agent_memory(
            agent_name="DeepClassifier",
            memory_key=key,
            memory_value=value_str,
            memory_type=memory_type,
            namespace=namespace,
            expires_at=expires_at
        )
    
    def _get_agent_memory(self, key: str) -> Optional[str]:
        """
        Retrieve data from agent_memory table
        """
        results = self.db.select(
            "agent_memory",
            where_conditions={"agent_name": "DeepClassifier", "memory_key": key},
            limit=1
        )
        
        if results:
            return results[0]['memory_value']
        return None
    
    def classify_and_store(self, content: str, source: str, 
                          chunk_intelligently: bool = True) -> List[str]:
        """
        Full pipeline: classify, chunk, and store document
        
        Returns:
            List of doc_ids created
        """
        # Step 1: Classify document
        classification_result = self.classify_document(content, source)
        
        # Step 2: Chunk document
        if chunk_intelligently:
            chunks = self.intelligent_chunk(content)
        else:
            # Simple chunking
            chunks = [(content, ChunkMetadata(
                chunk_id=1,
                total_chunks=1,
                summary=content[:100],
                keywords=[],
                relationships=[],
                confidence=1.0
            ))]
        
        # Step 3: Store each chunk
        doc_ids = []
        parent_doc_id = f"{classification_result.classification}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        for chunk_text, chunk_meta in chunks:
            doc_id = f"{parent_doc_id}_chunk_{chunk_meta.chunk_id}"
            
            # Insert document
            self.db.insert_document(
                doc_id=doc_id,
                source=source,
                content=chunk_text,
                chunk_id=chunk_meta.chunk_id,
                total_chunks=chunk_meta.total_chunks,
                classification=classification_result.classification,
                min_access_level=classification_result.min_access_level,
                namespace=classification_result.namespace,
                parent_doc_id=parent_doc_id if chunk_meta.total_chunks > 1 else None
            )
            
            # Insert metadata
            metadata_entries = {
                "classification_confidence": str(classification_result.confidence),
                "classification_method": classification_result.method,
                "chunk_summary": chunk_meta.summary,
                "keywords": json.dumps(chunk_meta.keywords),
                "sub_categories": json.dumps(classification_result.sub_categories)
            }
            
            for key, value in metadata_entries.items():
                self.db.insert("metadata", {
                    "doc_id": doc_id,
                    "key": key,
                    "value": value,
                    "created_at": datetime.now().isoformat()
                })
            
            doc_ids.append(doc_id)
        
        # Step 4: Build tree index
        self.build_tree_index(
            classification_result.classification,
            classification_result.namespace,
            parent_doc_id
        )
        
        # Step 5: Log operation
        self.db.log_operation(
            operation_type="classification",
            agent_name="DeepClassifier",
            status="success",
            input_data=json.dumps({
                "source": source,
                "content_length": len(content),
                "chunks": len(chunks)
            }),
            output_data=json.dumps({
                "classification": classification_result.classification,
                "confidence": classification_result.confidence,
                "method": classification_result.method,
                "namespace": classification_result.namespace,
                "doc_ids": doc_ids
            })
        )
        
        return doc_ids
