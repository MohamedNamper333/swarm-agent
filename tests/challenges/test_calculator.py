import pytest
from calculator import add, subtract, multiply, divide


class TestAdd:
    def test_add_positive_numbers(self):
        assert add(2, 3) == 5
        assert add(10, 20) == 30

    def test_add_negative_numbers(self):
        assert add(-5, -3) == -8
        assert add(-10, -20) == -30

    def test_add_mixed_signs(self):
        assert add(5, -3) == 2
        assert add(-5, 3) == -2

    def test_add_zero(self):
        assert add(0, 5) == 5
        assert add(5, 0) == 5
        assert add(0, 0) == 0

    def test_add_large_numbers(self):
        assert add(10**10, 10**10) == 2 * 10**10
        assert add(999999999, 1) == 1000000000


class TestSubtract:
    def test_subtract_positive_numbers(self):
        assert subtract(10, 3) == 7
        assert subtract(20, 10) == 10

    def test_subtract_negative_numbers(self):
        assert subtract(-5, -3) == -2
        assert subtract(-10, -20) == 10

    def test_subtract_mixed_signs(self):
        assert subtract(5, -3) == 8
        assert subtract(-5, 3) == -8

    def test_subtract_zero(self):
        assert subtract(0, 5) == -5
        assert subtract(5, 0) == 5
        assert subtract(0, 0) == 0

    def test_subtract_large_numbers(self):
        assert subtract(10**10, 10**5) == 9999900000
        assert subtract(1000000000, 1) == 999999999


class TestMultiply:
    def test_multiply_positive_numbers(self):
        assert multiply(3, 4) == 12
        assert multiply(10, 20) == 200

    def test_multiply_negative_numbers(self):
        assert multiply(-3, -4) == 12
        assert multiply(-10, -20) == 200

    def test_multiply_mixed_signs(self):
        assert multiply(5, -3) == -15
        assert multiply(-5, 3) == -15

    def test_multiply_by_zero(self):
        assert multiply(0, 5) == 0
        assert multiply(5, 0) == 0
        assert multiply(0, 0) == 0

    def test_multiply_by_one(self):
        assert multiply(1, 5) == 5
        assert multiply(5, 1) == 5
        assert multiply(-1, 5) == -5

    def test_multiply_large_numbers(self):
        assert multiply(10**5, 10**5) == 10**10
        assert multiply(99999, 99999) == 9999800001


class TestDivide:
    def test_divide_positive_numbers(self):
        assert divide(10, 2) == 5
        assert divide(20, 4) == 5

    def test_divide_negative_numbers(self):
        assert divide(-10, -2) == 5
        assert divide(-20, -4) == 5

    def test_divide_mixed_signs(self):
        assert divide(10, -2) == -5
        assert divide(-10, 2) == -5

    def test_divide_by_zero_raises_error(self):
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(10, 0)
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(-10, 0)
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(0, 0)

    def test_divide_zero_by_number(self):
        assert divide(0, 5) == 0
        assert divide(0, -5) == 0

    def test_divide_large_numbers(self):
        assert divide(10**10, 10**5) == 10**5
        assert divide(1000000000, 1000) == 1000000

    def test_divide_returns_float(self):
        assert divide(7, 2) == 3.5
        assert divide(10, 4) == 2.5


class TestCalculatorEdgeCases:
    def test_very_large_numbers(self):
        large = 10**100
        assert add(large, large) == 2 * large
        assert subtract(large, large) == 0
        assert multiply(large, 2) == 2 * large
        assert divide(large, 2) == large / 2

    def test_very_small_numbers(self):
        small = 1e-10
        assert add(small, small) == 2e-10
        assert subtract(small, small) == 0
        assert multiply(small, 2) == 2e-10
        assert divide(small, 2) == 5e-11


if __name__ == "__main__":
    pytest.main([__file__, "-v"])