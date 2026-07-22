#!/usr/bin/env python3
"""Code analyzer — detects complexity class and optimization opportunities."""

import ast
import textwrap


class CodeAnalyzer:
    """Analyzes Python code for complexity and optimization opportunities."""

    def analyze(self, source: str) -> dict:
        source = textwrap.dedent(source).strip()
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return {"valid": False, "error": str(e), "issues": [], "complexity": "unknown"}

        issues = []
        complexity = "O(1)"
        func_count = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_count += 1

            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, ast.For) and child is not node:
                        issues.append({
                            "type": "nested_loop",
                            "severity": "high",
                            "message": "Nested for-loop detected (O(n²) → consider set/dict lookup)",
                            "line": getattr(child, "lineno", 0),
                        })
                        complexity = "O(n²)"

            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, ast.AugAssign) and isinstance(child.op, ast.Add):
                        if isinstance(child.target, ast.Name):
                            issues.append({
                                "type": "string_concat_loop",
                                "severity": "medium",
                                "message": f"Concatenation in loop (variable '{child.target.id}') — use join()/append()",
                                "line": getattr(child, "lineno", 0),
                            })

            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Attribute):
                    issues.append({
                        "type": "repeated_attr",
                        "severity": "low",
                        "message": "Repeated attribute access — consider local variable",
                        "line": getattr(node, "lineno", 0),
                    })

        return {
            "valid": True,
            "complexity": complexity,
            "issues": issues,
            "function_count": func_count,
            "line_count": len(source.splitlines()),
        }
