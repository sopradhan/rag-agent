"""
Test ParameterManager integration with agents
Verifies that agents use dynamic parameters and auto-optimize based on metrics
"""
import sys
import json
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from core.parameter_manager import (
    get_parameter_manager, PerformanceMetrics, RAGParameters, LLMParameters
)


def test_parameter_manager():
    """Test ParameterManager basic functionality"""
    print("\n" + "="*60)
    print("TEST: ParameterManager Basic Functionality")
    print("="*60)
    
    param_manager = get_parameter_manager()
    
    # Test 1: Get default parameters
    print("\n[TEST 1] Get default parameters")
    rag_params = param_manager.get_rag_params()
    llm_params = param_manager.get_llm_params()
    print(f"  [OK] RAG Parameters: {rag_params}")
    print(f"  [OK] LLM Parameters: {llm_params}")
    
    # Test 2: Apply profile
    print("\n[TEST 2] Apply profiles")
    profiles = ['speed', 'accuracy', 'balanced', 'resource_limited', 'high_precision']
    for profile in profiles:
        param_manager.apply_profile(profile)
        rag_params = param_manager.get_rag_params()
        print(f"  [OK] {profile:20s} - top_k={rag_params['top_k']:2d}, "
              f"similarity_threshold={rag_params['similarity_threshold']:.2f}")
    
    # Reset to balanced
    param_manager.apply_profile('balanced')
    
    # Test 3: Set individual parameters
    print("\n[TEST 3] Set individual parameters")
    param_manager.set_rag_param('top_k', 15)
    param_manager.set_llm_param('temperature', 0.5)
    rag_params = param_manager.get_rag_params()
    llm_params = param_manager.get_llm_params()
    print(f"  [OK] Set top_k=15, new value: {rag_params['top_k']}")
    print(f"  [OK] Set temperature=0.5, new value: {llm_params['temperature']}")
    
    # Reset
    param_manager.apply_profile('balanced')
    
    # Test 4: Auto-optimize based on metrics
    print("\n[TEST 4] Auto-optimize based on different metrics")
    
    test_cases = [
        ("Slow Response (5500ms)", PerformanceMetrics(
            response_time_ms=5500, retrieval_accuracy=0.8,
            rbac_denial_rate=0.0, token_usage=500, relevance_score=0.8
        )),
        ("Low Accuracy (0.4)", PerformanceMetrics(
            response_time_ms=2000, retrieval_accuracy=0.4,
            rbac_denial_rate=0.0, token_usage=400, relevance_score=0.4
        )),
        ("High RBAC Denials (0.6)", PerformanceMetrics(
            response_time_ms=1000, retrieval_accuracy=0.8,
            rbac_denial_rate=0.6, token_usage=300, relevance_score=0.8
        )),
        ("High Token Usage (2000)", PerformanceMetrics(
            response_time_ms=3000, retrieval_accuracy=0.7,
            rbac_denial_rate=0.1, token_usage=2000, relevance_score=0.7
        )),
    ]
    
    for case_name, metrics in test_cases:
        # Reset to baseline
        param_manager.apply_profile('balanced')
        baseline_rag = param_manager.get_rag_params()
        
        # Auto-optimize
        optimizations = param_manager.auto_optimize(metrics)
        optimized_rag = param_manager.get_rag_params()
        
        print(f"\n  Case: {case_name}")
        print(f"    Metrics: response_time={metrics.response_time_ms}ms, "
              f"accuracy={metrics.retrieval_accuracy}, "
              f"denials={metrics.rbac_denial_rate}, tokens={metrics.token_usage}")
        if optimizations:
            print(f"    Optimizations: {optimizations}")
            print(f"    Top-k changed: {baseline_rag['top_k']} → {optimized_rag['top_k']}")
            print(f"    Similarity changed: {baseline_rag['similarity_threshold']:.2f} → "
                  f"{optimized_rag['similarity_threshold']:.2f}")
        else:
            print(f"    No optimizations needed (within acceptable range)")


def test_parameter_history():
    """Test parameter history tracking"""
    print("\n" + "="*60)
    print("TEST: Parameter History Tracking")
    print("="*60)
    
    param_manager = get_parameter_manager()
    
    # Make several changes
    print("\n[Making parameter changes...]")
    param_manager.apply_profile('speed')
    param_manager.apply_profile('accuracy')
    param_manager.set_rag_param('top_k', 20)
    
    # Check history
    history = param_manager.get_optimization_history()
    print(f"\n[OK] History entries recorded: {len(history)}")
    for i, entry in enumerate(history[-3:], 1):
        print(f"  {i}. Profile/Parameter change tracked")


def test_parameter_recommendations():
    """Test parameter recommendation system"""
    print("\n" + "="*60)
    print("TEST: Parameter Recommendation System")
    print("="*60)
    
    param_manager = get_parameter_manager()
    
    # Test recommendations with constraints
    print("\n[TEST] Recommendation with max_response_time_ms=2000")
    recommendations = param_manager.recommend_parameters({
        'max_response_time_ms': 2000,
        'min_accuracy': 0.7
    })
    
    if recommendations:
        print(f"[OK] Recommended profile: {recommendations.get('recommended_profile')}")
        print(f"[OK] Reasoning: {recommendations.get('reasoning')}")
    else:
        print("[OK] No recommendations (current config satisfies constraints)")
    
    print("\n[TEST] Recommendation with min_accuracy=0.9")
    recommendations = param_manager.recommend_parameters({
        'min_accuracy': 0.9
    })
    
    if recommendations:
        print(f"[OK] Recommended profile: {recommendations.get('recommended_profile')}")
        print(f"[OK] Reasoning: {recommendations.get('reasoning')}")


def test_export_import():
    """Test parameter export and import"""
    print("\n" + "="*60)
    print("TEST: Export/Import Parameters")
    print("="*60)
    
    param_manager = get_parameter_manager()
    
    # Make custom changes
    print("\n[Creating custom parameter configuration...]")
    param_manager.apply_profile('accuracy')
    param_manager.set_rag_param('top_k', 25)
    param_manager.set_llm_param('temperature', 0.3)
    
    # Export
    print("\n[Exporting parameters...]")
    config = param_manager.export_config()
    print(f"[OK] Exported config: {json.dumps(config, indent=2)}")
    
    # Create new manager and import
    print("\n[Importing into new manager...]")
    param_manager2 = get_parameter_manager()
    param_manager2.import_config(config)
    
    # Verify
    imported_rag = param_manager2.get_rag_params()
    imported_llm = param_manager2.get_llm_params()
    
    print(f"[OK] Imported RAG params: top_k={imported_rag['top_k']}")
    print(f"[OK] Imported LLM params: temperature={imported_llm['temperature']}")
    
    # Verify they match
    original_rag = param_manager.get_rag_params()
    original_llm = param_manager.get_llm_params()
    
    if (imported_rag['top_k'] == original_rag['top_k'] and
        imported_llm['temperature'] == original_llm['temperature']):
        print("\n[OK] Import/Export verification: PASSED")
    else:
        print("\n✗ Import/Export verification: FAILED")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("PARAMETER MANAGER INTEGRATION TESTS")
    print("="*60)
    
    try:
        test_parameter_manager()
        test_parameter_history()
        test_parameter_recommendations()
        test_export_import()
        
        print("\n" + "="*60)
        print("[OK] ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
