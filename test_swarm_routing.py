#!/usr/bin/env python3
"""
Test Swarm Routing Intelligence
Verifies that each task type routes to the correct worker/model
"""
import asyncio
import json
import sys
import time

# Test data: task type -> expected worker
ROUTING_TABLE = {
    "brainstorm_new_feature": {
        "expected_worker": "innovator",
        "expected_model": "opencode/deepseek-v4-flash-free",
        "task_type": "creative",
        "description": "Brainstorm a new feature"
    },
    "review_code_security": {
        "expected_worker": "critic",
        "expected_model": "opencode/nemotron-3-ultra-free",
        "task_type": "review",
        "description": "Review code for security vulnerabilities"
    },
    "build_api_endpoint": {
        "expected_worker": "architect",
        "expected_model": "opencode/nemotron-3-ultra-free",
        "task_type": "implementation",
        "description": "Build a REST API endpoint"
    },
    "research_competitors": {
        "expected_worker": "explorer",
        "expected_model": "opencode/mimo-v2.5-free",
        "task_type": "research",
        "description": "Research competitor products"
    },
    "review_ux_design": {
        "expected_worker": "reviewer",
        "expected_model": "opencode/nemotron-3-ultra-free",
        "task_type": "design",
        "description": "Review UX design mockups"
    },
    "analyze_logic_puzzle": {
        "expected_worker": "reasoner",
        "expected_model": "opencode/hy3-free",
        "task_type": "logic",
        "description": "Analyze a complex logic problem"
    },
    "vision_coding_task": {
        "expected_worker": "vision-coder",
        "expected_model": "opencode/mimo-v2.5-free",
        "task_type": "multimodal",
        "description": "Process image and write code"
    },
    "run_tests": {
        "expected_worker": "swarm-worker-qa",
        "expected_model": "opencode/nemotron-3-ultra-free",
        "task_type": "qa",
        "description": "Run test suite"
    }
}

def print_routing_table():
    print("\n" + "="*70)
    print("SWARM ROUTING TABLE")
    print("="*70)
    print(f"{'Task Type':<30} {'Worker':<20} {'Model':<35}")
    print("-"*70)
    for task_type, info in ROUTING_TABLE.items():
        print(f"{task_type:<30} {info['expected_worker']:<20} {info['expected_model']:<35}")
    print("="*70)

def test_model_availability():
    """Check if all models are configured"""
    print("\n[TEST] Model Availability")
    
    models = [
        ("opencode/big-pickle", "Coordinator"),
        ("opencode/deepseek-v4-flash-free", "Innovator"),
        ("opencode/nemotron-3-ultra-free", "Critic"),
        ("opencode/nemotron-3-ultra-free", "Architect/Reviewer/QA"),
        ("opencode/mimo-v2.5-free", "Explorer"),
        ("opencode/hy3-free", "Reasoner"),
        ("opencode/mimo-v2.5-free", "Vision-Coder"),
        ("opencode/laguna-s-2-1-free", "General"),
        ("opencode/ling-3-0-flash-free", "Fast")
    ]
    
    results = []
    for model, role in models:
        # Check if model exists in config
        with open("/home/kali/swarm-agent/opencode.json", 'r') as f:
            config = json.load(f)
        
        found = False
        for agent_name, agent_config in config.get("agent", {}).items():
            if agent_config.get("model") == model:
                found = True
                break
        
        status = "✓" if found else "✗"
        results.append((model, role, status))
        print(f"  {status} {model:<35} → {role}")
    
    return results

def test_tool_permissions():
    """Verify each worker has appropriate tools"""
    print("\n[TEST] Tool Permissions")
    
    expected_permissions = {
        "innovator": {"Read": True, "Write": False, "Edit": False, "Bash": False},
        "critic": {"Read": True, "Write": False, "Edit": False, "Bash": False},
        "architect": {"Read": True, "Write": True, "Edit": True, "Bash": True},
        "explorer": {"Read": True, "Write": False, "Edit": False, "Bash": False},
        "reviewer": {"Read": True, "Write": False, "Edit": False, "Bash": False},
        "reasoner": {"Read": True, "Write": False, "Edit": False, "Bash": False},
        "vision-coder": {"Read": True, "Write": True, "Edit": True, "Bash": True},
        "swarm-worker-qa": {"Read": True, "Write": True, "Edit": True, "Bash": True}
    }
    
    with open("/home/kali/swarm-agent/opencode.json", 'r') as f:
        config = json.load(f)
    
    all_ok = True
    for worker, expected in expected_permissions.items():
        agent_config = config.get("agent", {}).get(worker, {})
        actual_tools = agent_config.get("tools", {})
        
        issues = []
        for tool, should_be in expected.items():
            actual = actual_tools.get(tool, False)
            if actual != should_be:
                issues.append(f"{tool}: expected {should_be}, got {actual}")
        
        if issues:
            all_ok = False
            print(f"  ✗ {worker}: {', '.join(issues)}")
        else:
            print(f"  ✓ {worker}: tools OK")
    
    return all_ok

def test_skill_assignment():
    """Verify each worker has correct skills"""
    print("\n[TEST] Skill Assignment")
    
    with open("/home/kali/swarm-agent/opencode.json", 'r') as f:
        config = json.load(f)
    
    required_skills = ["swarm-constitutional-layer", "swarm-scratchpad", "swarm-token-budget", "swarm-worker-enhanced"]
    qa_extra = "swarm-quality-gates"
    
    all_ok = True
    for worker in ["innovator", "critic", "architect", "explorer", "reviewer", "reasoner", "vision-coder", "swarm-worker-qa"]:
        agent_config = config.get("agent", {}).get(worker, {})
        skills = agent_config.get("skills", [])
        
        missing = [s for s in required_skills if s not in skills]
        
        if worker == "swarm-worker-qa":
            if qa_extra not in skills:
                missing.append(qa_extra)
        
        if missing:
            all_ok = False
            print(f"  ✗ {worker}: missing {missing}")
        else:
            print(f"  ✓ {worker}: skills OK")
    
    return all_ok

def test_permission_grants():
    """Verify swarm coordinator can dispatch to all workers"""
    print("\n[TEST] Permission Grants (Swarm → Workers)")
    
    with open("/home/kali/swarm-agent/opencode.json", 'r') as f:
        config = json.load(f)
    
    swarm_permissions = config.get("agent", {}).get("swarm", {}).get("permission", {}).get("task", {})
    
    expected_workers = ["innovator", "critic", "architect", "explorer", "reviewer", "reasoner", "vision-coder", "swarm-worker-qa", "laguna-s-2-1", "ling-3-0-flash"]
    
    all_ok = True
    for worker in expected_workers:
        status = swarm_permissions.get(worker, "NOT FOUND")
        if status == "allow":
            print(f"  ✓ swarm → {worker}: allowed")
        else:
            all_ok = False
            print(f"  ✗ swarm → {worker}: {status} (expected allow)")
    
    return all_ok

def main():
    print("\n" + "="*70)
    print("SWARM INTELLIGENCE VERIFICATION")
    print("="*70)
    
    print_routing_table()
    
    results = []
    
    # Test 1: Model availability
    model_results = test_model_availability()
    results.append(("Model Availability", all(r[2] == "✓" for r in model_results)))
    
    # Test 2: Tool permissions
    results.append(("Tool Permissions", test_tool_permissions()))
    
    # Test 3: Skill assignment
    results.append(("Skill Assignment", test_skill_assignment()))
    
    # Test 4: Permission grants
    results.append(("Permission Grants", test_permission_grants()))
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for test_name, ok in results:
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    print("="*70)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
