"""Recursive factorial implementation with input validation."""

from __future__ import annotations


def factorial(n: int) -> int:
    """Calculate the factorial of a non-negative integer using recursion.

    Args:
        n: A non-negative integer whose factorial is to be computed.

    Returns:
        The factorial of ``n`` (i.e. n!).

    Raises:
        TypeError:  If ``n`` is not an integer (or bool).
        ValueError: If ``n`` is negative.

    Examples:
        >>> factorial(0)
        1
        >>> factorial(5)
        120
    """
    # --- input validation ---------------------------------------------------
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"factorial() requires a non-negative integer, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"factorial() is not defined for negative numbers, got {n}")

    # --- recursive base case & step -----------------------------------------
    if n == 0 or n == 1:
        return 1
    return n * factorial(n - 1)
