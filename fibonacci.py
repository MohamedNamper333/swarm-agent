"""Fibonacci number calculation using dynamic programming.

Provides an iterative bottom-up approach with O(n) time complexity
and O(1) space complexity by tracking only the two preceding values.
"""

from __future__ import annotations


def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number using dynamic programming.

    Uses an iterative bottom-up approach that tracks only the two
    most recent values, achieving O(n) time and O(1) space.

    The Fibonacci sequence is defined as:
        F(0) = 0
        F(1) = 1
        F(n) = F(n-1) + F(n-2) for n >= 2

    Args:
        n: The index in the Fibonacci sequence (non-negative integer).

    Returns:
        The nth Fibonacci number.

    Raises:
        ValueError: If n is negative.

    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(10)
        55
        >>> fibonacci(50)
        12586269025
    """
    if not isinstance(n, int):
        raise TypeError(f"n must be an integer, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    if n <= 1:
        return n

    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr
    return curr
