#!/usr/bin/env python3
"""Self-improver — the brain that analyzes, optimizes, benchmarks, and decides."""

import json
from datetime import datetime
from analyzer import CodeAnalyzer
from optimizer import CodeOptimizer
from benchmarker import Benchmarker


class SelfImprover:
    """Autonomous code improvement pipeline."""

    def __init__(self, speedup_threshold: float = 0.85, max_iterations: int = 3):
        """
        Args:
            speedup_threshold: Keep optimization if new_time / old_time <= this (0.85 = 15% faster)
            max_iterations: Maximum optimization rounds
        """
        self.analyzer = CodeAnalyzer()
        self.optimizer = CodeOptimizer()
        self.benchmarker = Benchmarker()
        self.speedup_threshold = speedup_threshold
        self.max_iterations = max_iterations
        self.history = []

    def improve(self, source: str, setup_code: str = "", test_code: str = "") -> dict:
        """
        Full improvement pipeline.

        Args:
            source: Original function source code
            setup_code: Setup code for benchmarking (e.g. test data)
            test_code: Test code to validate correctness

        Returns:
            dict with report, best_code, iterations_used, history
        """
        current_best = source
        iterations_used = 0
        full_history = []

        for round_num in range(self.max_iterations):
            # Step 1: Analyze
            analysis = self.analyzer.analyze(current_best)
            if not analysis.get("valid"):
                full_history.append({
                    "round": round_num + 1,
                    "decision": "FAILED",
                    "reason": "Invalid code",
                })
                break

            # Step 2: Optimize
            variants = self.optimizer.optimize(current_best, analysis)
            if not variants:
                full_history.append({
                    "round": round_num + 1,
                    "decision": "NO_OPTIMIZATIONS",
                    "reason": "No optimization opportunities found",
                })
                break

            # Step 3: Benchmark
            bench_results = self.benchmarker.benchmark(current_best, variants, setup_code)

            # Step 4: Decide
            best_variant = None
            best_speedup = None

            for v in bench_results["variants"]:
                if v["success"] and v["speedup"] is not None:
                    if v["speedup"] > 1.0:  # Actually faster
                        if best_speedup is None or v["speedup"] > best_speedup:
                            best_speedup = v["speedup"]
                            best_variant = v

            round_record = {
                "round": round_num + 1,
                "analysis": {
                    "complexity": analysis["complexity"],
                    "issues_found": len(analysis["issues"]),
                },
                "variants_generated": len(variants),
                "variants": [
                    {"name": v["name"], "speedup": v.get("speedup"), "success": v["success"]}
                    for v in bench_results["variants"]
                ],
            }

            if best_variant and best_speedup and best_speedup >= (1.0 / self.speedup_threshold):
                current_best = self._get_variant_code(variants, best_variant["name"])
                round_record["decision"] = "KEEP"
                round_record["chosen"] = best_variant["name"]
                round_record["speedup"] = best_speedup
            else:
                round_record["decision"] = "REJECT"
                round_record["reason"] = "No variant met speedup threshold"

            full_history.append(round_record)
            iterations_used += 1

            # Run tests if provided
            if test_code:
                test_passed = self._run_tests(current_best, test_code, setup_code)
                if not test_passed:
                    # Revert to previous best
                    if len(full_history) > 1:
                        current_best = source  # Original
                    full_history[-1]["tests_passed"] = False
                    full_history[-1]["decision"] = "REVERTED"
                    break
                full_history[-1]["tests_passed"] = True

        self.history = full_history

        return {
            "best_code": current_best,
            "iterations_used": iterations_used,
            "history": full_history,
            "report": self._generate_report(full_history),
        }

    def _get_variant_code(self, variants: list, name: str) -> str:
        for vname, code, desc in variants:
            if vname == name:
                return code
        return ""

    def _run_tests(self, code: str, test_code: str, setup_code: str) -> bool:
        """Run test code with the optimized function."""
        try:
            namespace = {}
            exec(setup_code, namespace) if setup_code else None
            exec(code, namespace)
            exec(test_code, namespace)
            return True
        except Exception:
            return False

    def _generate_report(self, history: list) -> str:
        """Generate human-readable report."""
        lines = ["=" * 50, "SELF-IMPROVEMENT REPORT", "=" * 50]

        for record in history:
            lines.append(f"\n--- Round {record['round']} ---")
            if "analysis" in record:
                lines.append(f"  Complexity: {record['analysis']['complexity']}")
                lines.append(f"  Issues: {record['analysis']['issues_found']}")
            lines.append(f"  Variants: {record.get('variants_generated', 0)}")
            lines.append(f"  Decision: {record['decision']}")
            if record["decision"] == "KEEP":
                lines.append(f"  Chosen: {record.get('chosen')} ({record.get('speedup', '?')}x faster)")
            elif record["decision"] == "REJECT":
                lines.append(f"  Reason: {record.get('reason', 'No variant met threshold')}")
            if "tests_passed" in record:
                lines.append(f"  Tests: {'PASSED' if record['tests_passed'] else 'FAILED'}")

        lines.append(f"\nTotal rounds: {len(history)}")
        lines.append("=" * 50)
        return "\n".join(lines)
