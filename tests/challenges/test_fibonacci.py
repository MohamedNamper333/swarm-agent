"""Pytest suite for fibonacci function.

Covers edge cases: base cases, negative input, type errors,
sequential correctness, and large values.
"""

import pytest

from fibonacci import fibonacci


# ---------------------------------------------------------------------------
# Base cases
# ---------------------------------------------------------------------------
class TestBaseCases:
    """F(0) = 0, F(1) = 1."""

    def test_fib_zero(self) -> None:
        assert fibonacci(0) == 0

    def test_fib_one(self) -> None:
        assert fibonacci(1) == 1


# ---------------------------------------------------------------------------
# Small known values
# ---------------------------------------------------------------------------
class TestSmallValues:
    """Known Fibonacci numbers for n = 2..20."""

    @pytest.mark.parametrize(
        "n, expected",
        [
            (2, 1),
            (3, 2),
            (4, 3),
            (5, 5),
            (6, 8),
            (7, 13),
            (8, 21),
            (9, 34),
            (10, 55),
            (15, 610),
            (20, 6765),
        ],
    )
    def test_known_values(self, n: int, expected: int) -> None:
        assert fibonacci(n) == expected


# ---------------------------------------------------------------------------
# Negative input
# ---------------------------------------------------------------------------
class TestNegativeInput:
    """Negative indices are undefined — must raise ValueError."""

    def test_negative_one(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            fibonacci(-1)

    def test_large_negative(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            fibonacci(-1000)


# ---------------------------------------------------------------------------
# Type errors
# ---------------------------------------------------------------------------
class TestTypeErrors:
    """Non-integer arguments must raise TypeError."""

    def test_float(self) -> None:
        with pytest.raises(TypeError, match="integer"):
            fibonacci(5.0)  # type: ignore[arg-type]

    def test_string(self) -> None:
        with pytest.raises(TypeError, match="integer"):
            fibonacci("10")  # type: ignore[arg-type]

    def test_none(self) -> None:
        with pytest.raises(TypeError, match="integer"):
            fibonacci(None)  # type: ignore[arg-type]

    def test_list(self) -> None:
        with pytest.raises(TypeError, match="integer"):
            fibonacci([5])  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Large values
# ---------------------------------------------------------------------------
class TestLargeValues:
    """Ensure large inputs return correct results and complete quickly."""

    def test_fib_50(self) -> None:
        assert fibonacci(50) == 12_586_269_025

    def test_fib_100(self) -> None:
        assert fibonacci(100) == 354_224_848_179_261_915_075

    def test_fib_500(self) -> None:
        result = fibonacci(500)
        # Spot-check first 20 digits of F(500)
        assert str(result).startswith("139423224561")


# ---------------------------------------------------------------------------
# Sequential consistency
# ---------------------------------------------------------------------------
class TestSequentialConsistency:
    """F(n) = F(n-1) + F(n-2) must hold for a range of n."""

    @pytest.mark.parametrize("n", range(2, 30))
    def test_recurrence(self, n: int) -> None:
        assert fibonacci(n) == fibonacci(n - 1) + fibonacci(n - 2)
