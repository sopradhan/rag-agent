"""
Prompt Template Manager
Centralized management of all LLM prompts for agents.
Supports dynamic prompt generation, COT reasoning, and templating.
"""

import yaml
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path


class PromptTemplate:
    """Represents a single prompt template."""
    
    def __init__(self, name: str, template: str, description: str = "",
                 variables: Optional[List[str]] = None, cot_steps: Optional[List[str]] = None):
        self.name = name
        self.template = template
        self.description = description
        self.variables = variables or []
        self.cot_steps = cot_steps or []
    
    def render(self, **kwargs) -> str:
        """Render prompt with provided variables."""
        result = self.template
        for key, value in kwargs.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        return result
    
    def has_all_variables(self, kwargs: Dict[str, Any]) -> bool:
        """Check if all required variables are provided."""
        return all(var in kwargs for var in self.variables)


class PromptManager:
    """Manages prompt templates for all agents."""
    
    def __init__(self, config_path: str = "config/prompts_config.yaml"):
        self.config_path = config_path
        self.templates: Dict[str, PromptTemplate] = {}
        self.cot_templates: Dict[str, List[str]] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load prompt templates from YAML configuration."""
        if not Path(self.config_path).exists():
            print(f"[WARNING] Prompt config not found: {self.config_path}")
            self._create_default_templates()
            return
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Load classification prompts
            for name, prompt_data in config.get("classification", {}).items():
                self.register_template(
                    name,
                    prompt_data.get("template", ""),
                    prompt_data.get("description", ""),
                    prompt_data.get("variables", []),
                    prompt_data.get("cot_steps", [])
                )
            
            # Load retrieval prompts
            for name, prompt_data in config.get("retrieval", {}).items():
                self.register_template(
                    name,
                    prompt_data.get("template", ""),
                    prompt_data.get("description", ""),
                    prompt_data.get("variables", []),
                    prompt_data.get("cot_steps", [])
                )
            
            # Load synthesis prompts
            for name, prompt_data in config.get("synthesis", {}).items():
                self.register_template(
                    name,
                    prompt_data.get("template", ""),
                    prompt_data.get("description", ""),
                    prompt_data.get("variables", []),
                    prompt_data.get("cot_steps", [])
                )
            
            # Load healing prompts
            for name, prompt_data in config.get("healing", {}).items():
                self.register_template(
                    name,
                    prompt_data.get("template", ""),
                    prompt_data.get("description", ""),
                    prompt_data.get("variables", []),
                    prompt_data.get("cot_steps", [])
                )
            
            print(f"[OK] Loaded {len(self.templates)} prompt templates")
        
        except Exception as e:
            print(f"[ERROR] Failed to load prompts: {e}")
            self._create_default_templates()
    
    def register_template(self, name: str, template: str, description: str = "",
                         variables: Optional[List[str]] = None,
                         cot_steps: Optional[List[str]] = None):
        """Register a new prompt template."""
        self.templates[name] = PromptTemplate(
            name, template, description, variables, cot_steps
        )
        if cot_steps:
            self.cot_templates[name] = cot_steps
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a template by name."""
        return self.templates.get(name)
    
    def render(self, template_name: str, **kwargs) -> str:
        """Render a template with given variables."""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        if not template.has_all_variables(kwargs):
            missing = [v for v in template.variables if v not in kwargs]
            raise ValueError(f"Missing variables: {missing}")
        
        return template.render(**kwargs)
    
    def generate_cot_prompt(self, template_name: str, **kwargs) -> str:
        """Generate a prompt with chain-of-thought reasoning steps."""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Start with main prompt
        prompt = template.render(**kwargs)
        
        # Add COT steps if defined
        if template_name in self.cot_templates:
            cot_steps = self.cot_templates[template_name]
            prompt += "\n\nChain-of-Thought Steps:\n"
            for i, step in enumerate(cot_steps, 1):
                step_rendered = step.format(**kwargs) if '{' in step else step
                prompt += f"{i}. {step_rendered}\n"
        
        return prompt
    
    def _create_default_templates(self):
        """Create default templates for core operations."""
        # Classification template
        self.register_template(
            "classify_document",
            """You are a document classification expert. Analyze this document and classify it.

Document Source: {{source}}
Document Content (first 1000 chars):
{{content}}

Available Departments: {{departments}}

Rule-based classification suggested: {{suggested_classification}} (confidence: {{suggested_confidence}})

Tasks:
1. Classify this document into ONE of the available departments
2. Provide confidence score (0.0 to 1.0)
3. Suggest hierarchical sub-categories
4. Recommend minimum access level (1-5)
5. Explain your reasoning

Respond in JSON format:
{{
    "classification": "department_name",
    "confidence": 0.85,
    "sub_categories": ["subcategory1"],
    "min_access_level": 3,
    "reasoning": "explanation"
}}""",
            "Classify document into departments",
            ["source", "content", "departments", "suggested_classification", "suggested_confidence"],
            ["1. Read and understand the document content",
             "2. Match keywords with available departments",
             "3. Determine hierarchical sub-categories",
             "4. Assess required access level based on sensitivity"]
        )
        
        # Retrieval template
        self.register_template(
            "retrieve_documents",
            """Based on the user query and retrieved documents, provide relevant information.

User Query: {{query}}
Retrieved Documents:
{{documents}}

Requirements:
- Use information from retrieved documents only
- Cite sources
- Maintain accuracy
- Consider user access level: {{access_level}}

Generate a comprehensive answer:""",
            "Generate answer from retrieved documents",
            ["query", "documents", "access_level"],
            ["1. Analyze user query intent",
             "2. Review retrieved documents",
             "3. Extract relevant information",
             "4. Structure coherent response",
             "5. Cite sources"]
        )
        
        # RBAC validation template
        self.register_template(
            "validate_rbac_access",
            """Validate if user can access this document based on RBAC rules.

User Profile:
- Department: {{user_department}}
- Role: {{user_role}}
- Access Level: {{user_access_level}}

Document Classification:
- Department: {{doc_department}}
- Classification: {{doc_classification}}
- Required Access Level: {{doc_access_level}}

Determine if access should be granted based on organizational RBAC hierarchy.""",
            "Validate RBAC permissions",
            ["user_department", "user_role", "user_access_level", "doc_department", "doc_classification", "doc_access_level"]
        )
        
        # Healing template
        self.register_template(
            "analyze_namespace_health",
            """Analyze namespace health and recommend optimizations.

Namespace: {{namespace}}
Document Count: {{doc_count}}
Average Chunk Size: {{avg_chunk_size}}
Distribution: {{distribution}}

Provide recommendations for:
1. Namespace rebalancing
2. Chunk optimization
3. Access pattern optimization""",
            "Analyze namespace health",
            ["namespace", "doc_count", "avg_chunk_size", "distribution"]
        )


class COTReasoner:
    """Generates and manages chain-of-thought reasoning traces."""
    
    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager
        self.reasoning_trace: List[Dict[str, Any]] = []
    
    def add_step(self, step_name: str, thought: str, action: str, observation: str):
        """Add a reasoning step to the trace."""
        self.reasoning_trace.append({
            "timestamp": datetime.now().isoformat(),
            "step": step_name,
            "thought": thought,
            "action": action,
            "observation": observation
        })
    
    def get_trace(self) -> List[Dict[str, Any]]:
        """Get complete reasoning trace."""
        return self.reasoning_trace
    
    def format_trace(self) -> str:
        """Format reasoning trace for logging."""
        output = "Chain-of-Thought Reasoning:\n"
        for i, step in enumerate(self.reasoning_trace, 1):
            output += f"\nStep {i}: {step['step']}\n"
            output += f"  Thought: {step['thought']}\n"
            output += f"  Action: {step['action']}\n"
            output += f"  Observation: {step['observation']}\n"
        return output
    
    def clear(self):
        """Clear reasoning trace."""
        self.reasoning_trace = []
