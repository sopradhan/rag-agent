"""
Test Agentic RAG System - Demonstrates agent spawning and delegation
Shows how agents autonomously spawn subagents and communicate
"""

import sys
sys.path.insert(0, 'e:\\rag_agent')

from src.agents.agentic_orchestrator import MasterOrchestrator


def demo_agentic_rag():
    """Demonstrate agentic RAG with spawning and delegation"""
    
    print("\n" + "="*80)
    print("AGENTIC RAG SYSTEM - AGENT SPAWNING & DELEGATION DEMO")
    print("="*80)
    
    # Initialize orchestrator
    orchestrator = MasterOrchestrator()
    
    print("\n[*] Processing query with full agent spawning...")
    
    # Process query
    result = orchestrator.process_query(
        query="What are the engineering safety protocols?",
        user_id="user_001",
        user_role="engineer",
        access_level=3
    )
    
    print(f"\n{'='*80}")
    print("RESULT")
    print(f"{'='*80}")
    print(f"Status: {result.get('status')}")
    print(f"Answer: {result.get('results', {}).get('answer', 'N/A')[:200]}...")
    
    print(f"\n{'='*80}")
    print("AGENT SPAWNING HIERARCHY")
    print(f"{'='*80}")
    
    # Show agent tree
    agent_tree = orchestrator.get_agent_tree()
    
    def print_tree(node, indent=0):
        prefix = "  " * indent
        children = node.get('spawned_agents', [])
        total = node.get('total_children', 0)
        
        print(f"{prefix}[AGENT] {node['name']}")
        if total > 0:
            print(f"{prefix}  ├─ Spawned: {total} subagent(s)")
        
        for child in children:
            print_tree(child, indent + 1)
    
    print("\nPipeline Structure:")
    for pipeline_agent in agent_tree.get('pipeline', []):
        print_tree(pipeline_agent)
    
    print(f"\n{'='*80}")
    print("DYNAMICALLY SPAWNED AGENTS")
    print(f"{'='*80}")
    
    spawned = orchestrator.get_all_spawned_agents()
    if spawned:
        print(f"\nTotal spawned agents: {len(spawned)}\n")
        for agent in spawned:
            print(f"[{agent['type']}] {agent['name']}")
            print(f"  ID: {agent['agent_id'][:8]}...")
            print(f"  Parent: {agent['parent']}")
            print()
    else:
        print("\nNo agents spawned in this execution")
    
    print(f"{'='*80}")
    print("AGENT COMMUNICATION FLOW")
    print(f"{'='*80}")
    
    print("""
DELEGATION PATTERN:

Synthesizer Agent
├─ Spawn [Refiner-xxxx] subagent
│  └─ Delegate: "Refine and improve answer"
│     └─ Refiner thinks (5 iterations COT)
│        └─ Refiner reports back to Synthesizer
│
├─ Spawn [Validator-xxxx] subagent
│  └─ Delegate: "Validate answer quality"
│     └─ Validator thinks (5 iterations COT)
│        └─ Validator reports back to Synthesizer
│
└─ Synthesizer reports final answer to parent (Ranker)

CHAIN-OF-THOUGHT IN EACH AGENT:

Each agent executes 5 iterations of:
  1. THINK - Analyze the task
  2. EVALUATE - Assess approach
  3. RETHINK - Refine if needed

This creates deep reasoning at every step!
    """)
    
    print(f"\n{'='*80}")
    print("KEY FEATURES DEMONSTRATED")
    print(f"{'='*80}")
    
    features = [
        "✓ Hierarchical agent spawning (Master → Pipeline → Helpers)",
        "✓ Dynamic subagent creation (Refiner, Validator spawned on-demand)",
        "✓ Task delegation with results aggregation",
        "✓ Parent-child agent relationships",
        "✓ Chain-of-thought reasoning in each agent (5 iterations)",
        "✓ Agent tree tracking and reporting",
        "✓ Bidirectional communication (delegate down, report up)",
        "✓ Execution history and results tracking"
    ]
    
    for feature in features:
        print(feature)
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    demo_agentic_rag()
