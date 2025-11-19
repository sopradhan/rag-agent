"""
Run All Agent Tests
Complete test suite for REFRAG system
"""
import subprocess
import sys

def run_test(script_name, description):
    print("\n" + "=" * 100)
    print(f"RUNNING: {description}")
    print("=" * 100)
    
    result = subprocess.run([sys.executable, script_name], capture_output=False)
    
    if result.returncode == 0:
        print(f"\n✓ {description} - PASSED")
        return True
    else:
        print(f"\n✗ {description} - FAILED")
        return False

def main():
    print("\n" + "=" * 100)
    print("REFRAG SYSTEM - COMPLETE TEST SUITE")
    print("=" * 100)
    print("\nTesting all agents with DeepAgents features:")
    print("  • write_todos (planning)")
    print("  • task (subagent spawning)")
    print("  • File system tools (context management)")
    print("  • Custom agent tools")
    print("\n" + "=" * 100)
    
    tests = [
        ("test_ingestion_agent.py", "IngestionAgent - Document Processing"),
        ("test_retrieval_agent.py", "RetrievalAgent - Query with RBAC"),
        ("test_healing_agent.py", "HealingAgent - REFRAG Self-Healing"),
        ("test_orchestrator.py", "MasterOrchestrator - Agent Coordination"),
    ]
    
    results = []
    for script, desc in tests:
        passed = run_test(script, desc)
        results.append((desc, passed))
        
        if not passed:
            print(f"\n⚠️  Test failed. Continue? (y/n): ", end="")
            choice = input().lower()
            if choice != 'y':
                break
    
    # Summary
    print("\n" + "=" * 100)
    print("TEST SUMMARY")
    print("=" * 100)
    
    for desc, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status} - {desc}")
    
    total = len(results)
    passed_count = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed_count}/{total} tests passed")
    
    if passed_count == total:
        print("\n🎉 ALL TESTS PASSED! REFRAG system is fully operational.")
    else:
        print(f"\n⚠️  {total - passed_count} test(s) failed.")
    
    print("=" * 100)

if __name__ == "__main__":
    main()
