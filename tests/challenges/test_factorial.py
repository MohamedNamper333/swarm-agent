"""Unit tests for factorial."""

import pytest

from factorial import factorial


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------
class TestFactorialHappyPath:
    """Verify correct results for valid inputs."""

    def test_zero(self) -> None:
        assert factorial(0) == 1

    def test_one(self) -> None:
        assert factorial(1) == 1

    def test_small_number(self) -> None:
        assert factorial(5) == 120

    def test_larger_number(self) -> None:
        assert factorial(10) == 3_628_800

    def test_result_grows_correctly(self) -> None:
        for i in range(2, 12):
            assert factorial(i) == factorial(i - 1) * i


# ---------------------------------------------------------------------------
# Boundary tests
# ---------------------------------------------------------------------------
class TestFactorialBoundary:
    """Edge cases around the valid/invalid boundary."""

    def test_two_returns_two(self) -> None:
        assert factorial(2) == 2

    def test_twenty(self) -> None:
        assert factorial(20) == 2_432_902_008_176_640_000


# ---------------------------------------------------------------------------
# Negative-input tests
# ---------------------------------------------------------------------------
class TestFactorialNegativeInput:
    """Negative integers must raise ValueError."""

    @pytest.mark.parametrize("n", [-1, -10, -100])
    def test_negative_raises_value_error(self, n: int) -> None:
        with pytest.raises(ValueError, match="not defined for negative"):
            factorial(n)


# ---------------------------------------------------------------------------
# Non-integer-input tests
# ---------------------------------------------------------------------------
class TestFactorialNonIntegerInput:
    """Non-integer types must raise TypeError."""

    @pytest.mark.parametrize("n", [1.5, 3.14, "5", [1], None, object()])
    def test_non_integer_raises_type_error(self, n: object) -> None:
        with pytest.raises(TypeError, match="requires a non-negative integer"):
            factorial(n)

    def test_bool_is_rejected(self) -> None:
        """bool is a subclass of int but should still be rejected."""
        with pytest.raises(TypeError, match="requires a non-negative integer"):
            factorial(True)
