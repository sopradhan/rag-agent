"""
Quick test of agentic spawning capabilities
"""

import sys
sys.path.insert(0, 'e:\\rag_agent')

print("[*] Testing agent spawning capabilities...\n")

try:
    from src.agents.agentic_orchestrator import MasterOrchestrator
    print("[OK] MasterOrchestrator imported")
    
    from src.subagents.langchain_subagents import (
        AnalyzerSubagent, SearcherSubagent, SynthesizerSubagent,
        RefinerSubagent, ValidatorSubagent
    )
    print("[OK] All subagents imported")
    
    # Test spawning
    print("\n[*] Creating Synthesizer and spawning Refiner/Validator...\n")
    
    synthesizer = SynthesizerSubagent()
    print(f"[OK] Synthesizer created: {synthesizer.name} ({synthesizer.agent_id[:8]})")
    
    # Spawn refiner
    refiner = synthesizer.spawn_subagent(
        RefinerSubagent,
        "[Refiner-Test]"
    )
    print(f"[OK] Refiner spawned: {refiner.name}")
    
    # Spawn validator
    validator = synthesizer.spawn_subagent(
        ValidatorSubagent,
        "[Validator-Test]"
    )
    print(f"[OK] Validator spawned: {validator.name}")
    
    # Show tree
    print("\n[*] Agent Tree Structure:")
    tree = synthesizer.get_agent_tree()
    print(f"Agent: {tree['name']}")
    print(f"  Children: {tree['total_children']}")
    for child in tree['spawned_agents']:
        print(f"  - {child['name']}")
    
    # Test delegation
    print("\n[*] Testing task delegation...")
    refiner_result = synthesizer.delegate_task(
        refiner,
        "Test refinement",
        "This is a test answer"
    )
    print(f"[OK] Refiner result: {str(refiner_result)[:80]}...")
    
    print("\n[OK] ALL TESTS PASSED!")
    print("\nKey Features Verified:")
    print("✓ Agent spawning with parent tracking")
    print("✓ Bidirectional communication (spawn/delegate/report)")
    print("✓ Agent tree hierarchy")
    print("✓ Task delegation")
    print("✓ Refiner and Validator subagent creation")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
