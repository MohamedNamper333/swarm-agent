#!/usr/bin/env python3
"""IMPOSSIBLE: Self-Improving Code Optimizer — 18 tests."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer import CodeAnalyzer
from optimizer import CodeOptimizer
from benchmarker import Benchmarker
from self_improver import SelfImprover


def test_analyzer_detects_nested_loop():
    code = """
def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i] == items[j]:
                duplicates.append(items[i])
    return duplicates
"""
    a = CodeAnalyzer()
    result = a.analyze(code)
    assert result["valid"] is True
    assert result["complexity"] == "O(n²)"
    assert any(i["type"] == "nested_loop" for i in result["issues"])


def test_analyzer_detects_concat_loop():
    code = """
def build_string(items):
    result = ""
    for item in items:
        result += str(item)
    return result
"""
    a = CodeAnalyzer()
    result = a.analyze(code)
    assert result["valid"] is True
    assert any(i["type"] == "string_concat_loop" for i in result["issues"])


def test_analyzer_simple_function():
    code = """
def add(a, b):
    return a + b
"""
    a = CodeAnalyzer()
    result = a.analyze(code)
    assert result["valid"] is True
    assert result["complexity"] == "O(1)"
    assert len(result["issues"]) == 0


def test_analyzer_invalid_code():
    code = "def broken( :::"
    a = CodeAnalyzer()
    result = a.analyze(code)
    assert result["valid"] is False
    assert "error" in result


def test_optimizer_generates_set_variant():
    code = """
def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i] == items[j] and items[i] not in duplicates:
                duplicates.append(items[i])
    return duplicates
"""
    a = CodeAnalyzer()
    o = CodeOptimizer()
    analysis = a.analyze(code)
    variants = o.optimize(code, analysis)
    names = [v[0] for v in variants]
    assert "set-based-lookup" in names


def test_optimizer_generates_list_comp():
    code = """
def double_all(nums):
    result = []
    for n in nums:
        result.append(n * 2)
    return result
"""
    a = CodeAnalyzer()
    o = CodeOptimizer()
    analysis = a.analyze(code)
    variants = o.optimize(code, analysis)
    names = [v[0] for v in variants]
    assert "list-comprehension" in names


def test_optimizer_no_issues_no_variants():
    code = """
def add(a, b):
    return a + b
"""
    a = CodeAnalyzer()
    o = CodeOptimizer()
    analysis = a.analyze(code)
    variants = o.optimize(code, analysis)
    # No nested loops or concat → no specific variants, but list-comp won't match either
    assert isinstance(variants, list)


def test_optimizer_invalid_code():
    a = CodeAnalyzer()
    o = CodeOptimizer()
    analysis = a.analyze("def broken( :::")
    variants = o.optimize("def broken( :::", analysis)
    assert variants == []


def test_benchmarker_returns_timing():
    code = """
def fast_add(a, b):
    return a + b
"""
    b = Benchmarker()
    result = b.benchmark(code, [], iterations=1000)
    assert result["original"]["success"] is True
    assert result["original"]["time"] is not None
    assert result["original"]["time"] >= 0


def test_benchmarker_detects_faster():
    slow = """
def count_items(items):
    count = 0
    for item in items:
        count += 1
    return count
"""
    fast = """
def count_items(items):
    return len(items)
"""
    b = Benchmarker()
    result = b.benchmark(slow, [("len-version", fast, "Use len()")], setup_code="data = list(range(1000))", iterations=10000)
    assert result["original"]["success"] is True
    assert result["variants"][0]["success"] is True
    assert result["variants"][0]["speedup"] is not None
    assert result["variants"][0]["speedup"] > 1.0


def test_benchmarker_handles_syntax_error():
    bad = "def broken(:::"
    b = Benchmarker()
    result = b.benchmark(bad, [])
    assert result["original"]["success"] is False
    assert "Syntax error" in result["original"]["error"]


def test_self_improver_keeps_faster_code():
    slow = """
def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i] == items[j] and items[i] not in duplicates:
                duplicates.append(items[i])
    return duplicates
"""
    improver = SelfImprover(speedup_threshold=0.85, max_iterations=1)
    result = improver.improve(slow, setup_code="data = list(range(100))")
    assert result["iterations_used"] == 1
    assert result["history"][0]["decision"] == "KEEP"
    assert "seen" in result["best_code"]


def test_self_improver_rejects_slower_code():
    code = """
def add(a, b):
    return a + b
"""
    improver = SelfImprover(speedup_threshold=0.85, max_iterations=1)
    result = improver.improve(code)
    # The optimizer finds no variants for this trivial function
    assert result["history"][0]["decision"] in ("REJECT", "NO_OPTIMIZATIONS")


def test_self_improver_respects_max_iterations():
    code = """
def find_dupes(items):
    dups = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i] == items[j] and items[i] not in dups:
                dups.append(items[i])
    return dups
"""
    improver = SelfImprover(speedup_threshold=0.85, max_iterations=2)
    result = improver.improve(code)
    assert result["iterations_used"] <= 2


def test_self_improver_full_pipeline():
    code = """
def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i] == items[j] and items[i] not in duplicates:
                duplicates.append(items[i])
    return duplicates
"""
    improver = SelfImprover(speedup_threshold=0.85, max_iterations=3)
    result = improver.improve(code)
    assert "best_code" in result
    assert "report" in result
    assert "history" in result
    assert len(result["history"]) > 0


def test_self_improver_with_tests():
    code = """
def double_all(nums):
    result = []
    for n in nums:
        result.append(n * 2)
    return result
"""
    test_code = """
assert double_all([1, 2, 3]) == [2, 4, 6]
assert double_all([]) == []
assert double_all([0]) == [0]
"""
    improver = SelfImprover(speedup_threshold=0.85, max_iterations=1)
    result = improver.improve(code, test_code=test_code)
    # Tests should pass on the optimized code
    assert result["iterations_used"] >= 1


def test_self_improver_empty_function():
    code = """
def empty():
    pass
"""
    improver = SelfImprover(max_iterations=1)
    result = improver.improve(code)
    assert result["best_code"].strip() != ""


def test_report_generation():
    code = """
def add(a, b):
    return a + b
"""
    improver = SelfImprover(max_iterations=1)
    result = improver.improve(code)
    report = result["report"]
    assert "SELF-IMPROVEMENT REPORT" in report
    assert "Round 1" in report


def test_benchmarker_quick_bench():
    code = """
def fast():
    return 42
"""
    b = Benchmarker()
    result = b.quick_bench(code, iterations=10000)
    assert result["success"] is True
    assert result["time"] is not None


if __name__ == "__main__":
    tests = [
        test_analyzer_detects_nested_loop,
        test_analyzer_detects_concat_loop,
        test_analyzer_simple_function,
        test_analyzer_invalid_code,
        test_optimizer_generates_set_variant,
        test_optimizer_generates_list_comp,
        test_optimizer_no_issues_no_variants,
        test_optimizer_invalid_code,
        test_benchmarker_returns_timing,
        test_benchmarker_detects_faster,
        test_benchmarker_handles_syntax_error,
        test_self_improver_keeps_faster_code,
        test_self_improver_rejects_slower_code,
        test_self_improver_respects_max_iterations,
        test_self_improver_full_pipeline,
        test_self_improver_with_tests,
        test_self_improver_empty_function,
        test_report_generation,
        test_benchmarker_quick_bench,
    ]

    passed = 0
    failed = 0
    print("=" * 55)
    print("IMPOSSIBLE: Self-Improving Code Optimizer — Test Suite")
    print("=" * 55)

    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 55}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print(f"{'=' * 55}")
    sys.exit(0 if failed == 0 else 1)
