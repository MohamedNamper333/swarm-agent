#!/usr/bin/env python3
"""Code optimizer — generates optimized variants based on analysis."""

import ast
import re
import textwrap


class CodeOptimizer:
    """Generates optimized code variants based on analysis results."""

    def optimize(self, source: str, analysis: dict) -> list:
        """Return list of (name, code, description) tuples."""
        source = textwrap.dedent(source).strip()
        variants = []

        if not analysis.get("valid"):
            return []

        try:
            ast.parse(source)
        except SyntaxError:
            return []

        for issue in analysis.get("issues", []):
            if issue["type"] == "nested_loop":
                variant = self._optimize_nested_loop(source)
                if variant:
                    variants.append(variant)

            elif issue["type"] == "string_concat_loop":
                variant = self._optimize_concat(source)
                if variant:
                    variants.append(variant)

        # Always try general optimizations
        variant = self._optimize_list_comp(source)
        if variant:
            variants.append(variant)

        # Deduplicate by code content
        seen = set()
        unique = []
        for v in variants:
            if v[1] not in seen:
                seen.add(v[1])
                unique.append(v)

        return unique

    def _optimize_nested_loop(self, source: str) -> tuple | None:
        """Convert nested loop pattern to set-based approach."""
        tree = ast.parse(source)
        for func_node in ast.walk(tree):
            if not isinstance(func_node, ast.FunctionDef):
                continue
            for node in ast.walk(func_node):
                if not isinstance(node, ast.For):
                    continue
                if not isinstance(node.body, list) or len(node.body) < 1:
                    continue
                inner = node.body[0]
                if not isinstance(inner, ast.For):
                    continue
                # Found nested for — check if it's the duplicate-finding pattern
                if not inner.body or not isinstance(inner.body[0], ast.If):
                    continue

                func_name = func_node.name
                params = [a.arg for a in func_node.args.args]

                # Generate optimized version
                param_str = ", ".join(params)
                optimized = f"""def {func_name}({param_str}):
    seen = set()
    result = []
    for item in {params[0] if params else 'items'}:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result"""
                return ("set-based-lookup", optimized, "Replaced O(n²) nested loop with O(n) set lookup")
        return None

    def _optimize_concat(self, source: str) -> tuple | None:
        """Convert string concatenation in loop to join()."""
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            # Look for pattern: var = "" then loop with var += x
            # First find string initialization
            string_vars = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    if isinstance(child.value, ast.Constant) and isinstance(child.value.value, str) and child.value.value == "":
                        for target in child.targets:
                            if isinstance(target, ast.Name):
                                string_vars.add(target.id)

            for child in ast.walk(node):
                if isinstance(child, ast.AugAssign) and isinstance(child.op, ast.Add):
                    if isinstance(child.target, ast.Name) and child.target.id in string_vars:
                        var_name = child.target.id
                        param_str = ", ".join(a.arg for a in node.args.args)
                        optimized = f"""def {node.name}({param_str}):
    _parts = []
    for item in {node.args.args[0].arg if node.args.args else 'items'}:
        _parts.append(str(item))
    return "".join(_parts)"""
                        return ("join-pattern", optimized, "Replaced string concatenation with list append + join()")
        return None

    def _optimize_list_comp(self, source: str) -> tuple | None:
        """Convert simple for-loop-append to list comprehension."""
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            body = node.body
            if len(body) < 3:
                continue
            # Pattern: result = [] / for x in y: / result.append(expr) / return result
            if not isinstance(body[0], ast.Assign):
                continue
            if not isinstance(body[-1], ast.Return):
                continue

            # Check the for loop
            for_node = body[1] if len(body) >= 3 else None
            if not isinstance(for_node, ast.For):
                continue

            # Check append in for body
            if not for_node.body or not isinstance(for_node.body[0], ast.Expr):
                continue
            call = for_node.body[0].value
            if not isinstance(call, ast.Call):
                continue
            if not isinstance(call.func, ast.Attribute):
                continue
            if call.func.attr != "append":
                continue

            # Extract info
            target = ast.dump(call.args[0]) if call.args else None
            iter_var = for_node.target.id if isinstance(for_node.target, ast.Name) else None
            iterable = ast.dump(for_node.iter) if for_node.iter else None

            if not iter_var or not iterable:
                continue

            # Reconstruct the expression source
            try:
                expr_src = ast.unparse(call.args[0])
            except:
                continue

            param_str = ", ".join(a.arg for a in node.args.args)
            optimized = f"""def {node.name}({param_str}):
    return [{expr_src} for {iter_var} in {ast.unparse(for_node.iter)}]"""
            return ("list-comprehension", optimized, "Replaced for-loop-append with list comprehension")
        return None
