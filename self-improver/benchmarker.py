#!/usr/bin/env python3
"""Benchmarker — times code execution and compares variants."""

import timeit
import re


class Benchmarker:
    """Benchmarks original and optimized code variants."""

    def benchmark(self, original: str, variants: list, setup_code: str = "", iterations: int = 1000, call_args: str = "") -> dict:
        """
        Benchmark original and variants.

        Args:
            call_args: Arguments to pass to the function (e.g. "data" or "data, 5")
        """
        results = {"original": None, "variants": [], "iterations": iterations}

        orig_result = self._time_code(original, setup_code, iterations, call_args)
        results["original"] = orig_result

        for name, code, desc in variants:
            var_result = self._time_code(code, setup_code, iterations, call_args)
            var_result["name"] = name
            var_result["description"] = desc
            if orig_result["success"] and var_result["success"] and orig_result["time"] and orig_result["time"] > 0:
                speedup = orig_result["time"] / var_result["time"]
                var_result["speedup"] = round(speedup, 2)
            else:
                var_result["speedup"] = None
            results["variants"].append(var_result)

        return results

    def _time_code(self, code: str, setup: str, iterations: int, call_args: str = "") -> dict:
        """Time a single code block."""
        try:
            compile(code, "<bench>", "exec")
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error: {e}", "time": None}

        # Find function name
        func_match = re.search(r'def\s+(\w+)\s*\(', code)
        if not func_match:
            # Not a function — just verify it compiles
            return {"success": True, "time": 0.0, "error": None}

        func_name = func_match.group(1)

        # Check if function has parameters
        params_match = re.search(r'def\s+\w+\s*\(([^)]*)\)', code)
        params = [p.strip() for p in params_match.group(1).split(",") if p.strip()] if params_match else []

        # Determine how to call the function
        if call_args:
            call_expr = f"{func_name}({call_args})"
        elif params:
            # Try to use setup_code variable names
            # Look for variable assignments in setup_code
            var_names = re.findall(r'(\w+)\s*=\s*', setup)
            if var_names and len(var_names) >= len(params):
                args = ", ".join(var_names[:len(params)])
                call_expr = f"{func_name}({args})"
            elif not params:
                call_expr = f"{func_name}()"
            else:
                # Can't determine args — just compile check
                return {"success": True, "time": 0.0, "error": None}
        else:
            call_expr = f"{func_name}()"

        full_setup = (setup + "\n" if setup else "") + code

        try:
            timer = timeit.Timer(call_expr, setup=full_setup, globals={})
            times = timer.repeat(repeat=3, number=iterations)
            avg_time = sum(times) / len(times)
            return {
                "success": True,
                "time": avg_time,
                "min": min(times),
                "max": max(times),
                "error": None,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "time": None}

    def quick_bench(self, code: str, setup: str = "", iterations: int = 10000, call_args: str = "") -> dict:
        """Quick single-code benchmark."""
        return self._time_code(code, setup, iterations, call_args)
