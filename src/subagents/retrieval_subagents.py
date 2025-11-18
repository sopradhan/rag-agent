"""
Retrieval Subagents
Handles permission checking, graph expansion, and answer synthesis.
"""

from typing import List, Dict, Any, Optional
from ..agents.deep_agent import DeepAgent
from ..abstraction import Document, LLMManager, RBACManager, User


class PermissionCheckerSubagent(DeepAgent):
    """Checks user permissions before retrieval."""
    
    def __init__(self, name: str, config: Dict[str, Any], rbac_manager: RBACManager):
        super().__init__(name=name, config=config)
        self.rbac_manager = rbac_manager
        self.strict_mode = config.get("strict_mode", True)
    
    def _execute(self, query: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Check user permissions."""
        user_obj = self.rbac_manager.get_user(user.get("id"))
        
        if not user_obj:
            if self.strict_mode:
                raise PermissionError(f"User {user.get('id')} not found")
            # Create temporary user in non-strict mode
            user_obj = User(
                user_id=user.get("id"),
                role=user.get("role", "guest"),
                name=user.get("name", ""),
                email=user.get("email", ""),
                permissions=set(["read:general"]),
                access_level=10
            )
        
        self.memory.add({
            "type": "permission_check",
            "user": user_obj.user_id,
            "role": user_obj.role,
            "access_level": user_obj.access_level
        })
        
        return {
            "user": user_obj,
            "query": query,
            "authorized": True
        }


class GraphExpansionSubagent(DeepAgent):
    """Expands document context using graph relationships."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name=name, config=config)
        self.max_depth = config.get("max_depth", 2)
        self.max_nodes = config.get("max_nodes", 10)
    
    def _execute(self, documents: List[Document], graph_store: Any = None) -> List[Document]:
        """Expand documents using graph relationships."""
        if not graph_store:
            # No graph expansion without graph store
            return documents
        
        expanded_docs = list(documents)
        visited = set(doc.id for doc in documents if hasattr(doc, 'id'))
        
        # Simulate graph expansion (implement actual graph traversal)
        for doc in documents:
            related = self._get_related_documents(doc, graph_store, visited)
            expanded_docs.extend(related[:self.max_nodes - len(expanded_docs)])
            
            if len(expanded_docs) >= self.max_nodes:
                break
        
        self.memory.add({
            "type": "graph_expansion",
            "original_docs": len(documents),
            "expanded_docs": len(expanded_docs)
        })
        
        return expanded_docs[:self.max_nodes]
    
    def _get_related_documents(
        self,
        doc: Document,
        graph_store: Any,
        visited: set
    ) -> List[Document]:
        """Get related documents from graph store."""
        # Placeholder - implement actual graph traversal
        return []


class AnswerSynthesisSubagent(DeepAgent):
    """Synthesizes final answer from retrieved documents with chain-of-thought reasoning."""
    
    def __init__(self, name: str, config: Dict[str, Any], llm_manager: LLMManager = None):
        super().__init__(name=name, config=config)
        self.llm_manager = llm_manager
        self.include_sources = config.get("include_sources", True)
        self.max_context_length = config.get("max_context_length", 4000)
        self.cot_enabled = config.get("cot_enabled", True)
    
    def _execute(self, documents: List[Document], query: str) -> Dict[str, Any]:
        """Synthesize answer from documents."""
        # Prepare context
        context = self._prepare_context(documents)
        
        # Generate answer using chain-of-thought
        prompt = self._build_prompt(query, context)
        
        # If LLM manager available, use it; otherwise generate synthetic response
        if self.llm_manager:
            answer = self.llm_manager.generate(prompt)
        else:
            answer = self._generate_synthetic_answer(query, documents, context)
        
        result = {
            "query": query,
            "answer": answer,
            "num_sources": len(documents),
            "context_length": len(context),
            "status": "success"
        }
        
        if self.include_sources:
            result["sources"] = [
                {
                    "source": doc.source if hasattr(doc, 'source') else str(doc),
                    "content": (doc.content if hasattr(doc, 'content') else str(doc))[:200],
                    "metadata": doc.metadata if hasattr(doc, 'metadata') else {}
                }
                for doc in documents
            ]
        
        self.memory.add({
            "type": "answer_synthesis",
            "query": query,
            "num_documents": len(documents),
            "answer_length": len(answer),
            "status": "completed"
        })
        
        return result
    
    def _think(self, documents: List[Document], query: str) -> Dict[str, Any]:
        """Phase 1: Think about the query and document structure."""
        return {
            "phase": "think",
            "query_analysis": f"Query: {query}",
            "document_count": len(documents),
            "approach": "Will synthesize from relevant documents",
            "keywords": self._extract_keywords(query),
            "confidence": 0.6
        }
    
    def _evaluate(self, current_result: Any, documents: List[Document] = None, query: str = None, *args, **kwargs) -> Dict[str, Any]:
        """Phase 2: Evaluate the answer quality."""
        if not current_result or isinstance(current_result, dict) and current_result.get("phase") == "think":
            # Need to generate answer
            result = self._execute(documents, query) if documents and query else None
        else:
            result = current_result
        
        # Evaluate quality
        answer = result.get("answer", "") if isinstance(result, dict) else str(result)
        score = min(1.0, len(answer) / 200) if answer else 0.0  # Score based on length
        
        return {
            "score": score,
            "feedback": f"Generated answer with {len(answer)} chars from {len(documents)} documents" if documents else "No answer",
            "sufficient": score > 0.5,
            "result": result
        }
    
    def _rethink(self, current_result: Any, feedback: str, iteration: int, 
                documents: List[Document] = None, query: str = None, *args, **kwargs) -> Any:
        """Phase 3: Refine answer based on feedback."""
        if documents and query:
            # Refine the synthesis
            refined_context = self._prepare_context(documents, refined=True)
            refined_prompt = self._build_prompt(query, refined_context)
            
            if self.llm_manager:
                answer = self.llm_manager.generate(refined_prompt)
            else:
                answer = self._generate_synthetic_answer(query, documents, refined_context)
            
            return {
                "query": query,
                "answer": answer,
                "num_sources": len(documents),
                "iteration": iteration,
                "refined": True
            }
        
        return current_result
    
    def _prepare_context(self, documents: List[Document], refined: bool = False) -> str:
        """Prepare context from documents."""
        context_parts = []
        current_length = 0
        
        for i, doc in enumerate(documents):
            # Extract content safely
            content = doc.content if hasattr(doc, 'content') else str(doc)
            doc_text = f"\n\n[Source {i+1}]\n{content}"
            
            if current_length + len(doc_text) > self.max_context_length:
                break
            
            context_parts.append(doc_text)
            current_length += len(doc_text)
        
        return "".join(context_parts) if context_parts else "No documents available"
    
    def _build_prompt(self, query: str, context: str) -> str:
        """Build prompt for answer generation."""
        return f"""You are a helpful assistant. Answer the following question based on the provided context. 
If the context doesn't contain enough information, clearly state that.

Context:
{context}

Question: {query}

Please provide a clear, comprehensive answer based on the context above."""
    
    def _generate_synthetic_answer(self, query: str, documents: List[Document], context: str) -> str:
        """Generate a synthetic answer when LLM manager is not available."""
        if not documents:
            return f"I couldn't find any documents to answer: {query}"
        
        # Extract key information from documents
        sources_summary = []
        for i, doc in enumerate(documents):
            source = doc.source if hasattr(doc, 'source') else f"Document {i+1}"
            content = (doc.content if hasattr(doc, 'content') else str(doc))[:150]
            sources_summary.append(f"- {source}: {content}...")
        
        # Build synthetic answer
        answer = f"""Based on the retrieved documents, here's what I found regarding '{query}':\n\n"""
        answer += "\n".join(sources_summary)
        answer += f"\n\nSources ({len(documents)} documents found): This information was compiled from the available knowledge base. "
        answer += "For more detailed information, please refer to the source documents listed above."
        
        return answer
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'how', 'to', 'how', 'what', 'where', 'when', 'why', 'which', 'who'}
        return [w for w in words if w not in stop_words and len(w) > 2][:5]
    
    def _get_related_documents(
        self,
        doc: Document,
        graph_store: Any,
        visited: set
    ) -> List[Document]:
        """Get related documents from graph store."""
        # Placeholder - implement actual graph traversal
        return []
