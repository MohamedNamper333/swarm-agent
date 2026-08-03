"""Tests for factorial function."""

import pytest
from factorial import factorial


class TestFactorial:
    def test_factorial_zero(self):
        assert factorial(0) == 1

    def test_factorial_one(self):
        assert factorial(1) == 1

    def test_factorial_five(self):
        assert factorial(5) == 120

    def test_factorial_ten(self):
        assert factorial(10) == 3628800

    def test_factorial_negative(self):
        with pytest.raises(ValueError):
            factorial(-1)

    def test_factorial_large(self):
        assert factorial(20) == 2432902008176640000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
