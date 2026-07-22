"""
Comprehensive test suite for the longest_common_subsequence function.

Covers:
- Basic functionality
- Edge cases (empty strings, single characters)
- No common subsequence
- Identical strings
- One string is subsequence of another
- Multiple valid LCS answers
- Performance with longer strings
- Type safety
"""

import pytest

from lcs import longest_common_subsequence


class TestBasicFunctionality:
    """Test core LCS functionality with typical inputs."""

    def test_simple_case(self):
        """Standard example: 'ace' is LCS of 'abcde' and 'ace'."""
        assert longest_common_subsequence("abcde", "ace") == "ace"

    def test_reversed_order(self):
        """LCS when characters are in different order."""
        result = longest_common_subsequence("ABC", "ACB")
        assert result == "AB"
        assert len(result) == 2

    def test_partial_overlap(self):
        """Partial character overlap between strings."""
        result = longest_common_subsequence("hello", "world")
        assert result == "lo"

    def test_full_overlap(self):
        """Identical strings should return the entire string."""
        assert longest_common_subsequence("abc", "abc") == "abc"

    def test_completely_different(self):
        """No common characters between strings."""
        assert longest_common_subsequence("abc", "xyz") == ""


class TestEdgeCases:
    """Test boundary conditions and edge cases."""

    def test_empty_first_string(self):
        """Empty first string should return empty."""
        assert longest_common_subsequence("", "anything") == ""

    def test_empty_second_string(self):
        """Empty second string should return empty."""
        assert longest_common_subsequence("anything", "") == ""

    def test_both_empty(self):
        """Both strings empty should return empty."""
        assert longest_common_subsequence("", "") == ""

    def test_single_char_match(self):
        """Single character match."""
        assert longest_common_subsequence("a", "a") == "a"

    def test_single_char_no_match(self):
        """Single character, no match."""
        assert longest_common_subsequence("a", "b") == ""

    def test_one_char_string(self):
        """One character vs multiple characters."""
        result = longest_common_subsequence("a", "abc")
        assert result == "a"

    def test_long_vs_short(self):
        """Very long string vs very short string."""
        long_str = "a" * 1000
        assert longest_common_subsequence(long_str, "a") == "a"


class TestSubsequenceScenarios:
    """Test cases where one string is a subsequence of another."""

    def test_subsequence_at_start(self):
        """Subsequence appears at the beginning."""
        assert longest_common_subsequence("abcdef", "abc") == "abc"

    def test_subsequence_at_end(self):
        """Subsequence appears at the end."""
        assert longest_common_subsequence("abcdef", "def") == "def"

    def test_subsequence_interleaved(self):
        """Subsequence is interleaved throughout."""
        assert longest_common_subsequence("abcdef", "ace") == "ace"

    def test_one_string_is_subsequence(self):
        """One string is entirely a subsequence of the other."""
        assert longest_common_subsequence("abcdef", "aceg") == "ace"


class TestRepeatedCharacters:
    """Test strings with repeated characters."""

    def test_repeated_in_one(self):
        """Repeated characters in first string."""
        result = longest_common_subsequence("aab", "ab")
        assert result == "ab"

    def test_repeated_in_both(self):
        """Repeated characters in both strings."""
        result = longest_common_subsequence("aaa", "aaa")
        assert result == "aaa"

    def test_repeated_mixed(self):
        """Mixed repeated and unique characters."""
        result = longest_common_subsequence("aabbaa", "abab")
        assert len(result) == 3
        # Valid LCS could be "aba" or "bab"
        assert result in ("aba", "bab")


class TestSpecialCharacters:
    """Test with special characters, numbers, and unicode."""

    def test_numbers(self):
        """Numeric characters."""
        assert longest_common_subsequence("12345", "246") == "24"

    def test_special_chars(self):
        """Special characters."""
        result = longest_common_subsequence("!@#$%", "@#$")
        assert result == "@#$"

    def test_unicode(self):
        """Unicode characters."""
        result = longest_common_subsequence("αβγδ", "βδ")
        assert result == "βδ"

    def test_mixed_case(self):
        """Case-sensitive matching."""
        result = longest_common_subsequence("ABC", "abc")
        assert result == ""  # Case-sensitive: 'A' != 'a'

    def test_spaces(self):
        """Spaces are valid characters."""
        result = longest_common_subsequence("hello world", "ho ol")
        assert result == "ho ol"


class TestMultipleValidAnswers:
    """Test cases where multiple valid LCS answers exist."""

    def test_multiple_valid_lcs(self):
        """Multiple valid LCS of the same length."""
        result = longest_common_subsequence("ABC", "ACB")
        # Both "AB" and "AC" are valid LCS of length 2
        assert len(result) == 2
        assert result in ("AB", "AC")

    def test_ambiguous_case(self):
        """Ambiguous case with multiple valid answers."""
        result = longest_common_subsequence("abcb", "acbb")
        assert len(result) == 3
        assert result in ("acb", "abb", "abc")


class TestLongerStrings:
    """Test with longer strings to verify correctness."""

    def test_long_identical(self):
        """Long identical strings."""
        s = "a" * 100 + "b" * 100 + "c" * 100
        assert longest_common_subsequence(s, s) == s

    def test_long_no_match(self):
        """Long strings with no common characters."""
        s1 = "a" * 100
        s2 = "b" * 100
        assert longest_common_subsequence(s1, s2) == ""

    def test_long_partial_match(self):
        """Long strings with partial match."""
        s1 = "a" * 50 + "b" * 50
        s2 = "b" * 50 + "a" * 50
        result = longest_common_subsequence(s1, s2)
        assert len(result) == 50  # Either all 'a's or all 'b's


class TestDocstringAndTypeHints:
    """Verify the function has proper documentation."""

    def test_has_docstring(self):
        """Function should have a docstring."""
        assert longest_common_subsequence.__doc__ is not None
        assert "longest common subsequence" in longest_common_subsequence.__doc__.lower()

    def test_type_hints(self):
        """Function should have type annotations."""
        import inspect
        sig = inspect.signature(longest_common_subsequence)
        # Check return annotation
        assert sig.return_annotation is not None
        # Check parameter annotations
        for param in sig.parameters.values():
            assert param.annotation is not None


class TestPerformanceBaseline:
    """Basic performance sanity checks."""

    def test_runs_in_reasonable_time(self):
        """Ensure the function handles reasonable inputs quickly."""
        import time
        s1 = "abcdefghij" * 100
        s2 = "jihgfedcba" * 100
        start = time.perf_counter()
        result = longest_common_subsequence(s1, s2)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"Function took {elapsed:.2f}s for 1000-char strings"
        assert len(result) > 0


class TestRegressionTests:
    """Regression tests for known inputs and expected outputs."""

    @pytest.mark.parametrize(
        "s1, s2, expected_len",
        [
            ("AGGTAB", "GXTXAYB", 4),      # LCS is "GTAB"
            ("ABCBDAB", "BDCAB", 3),         # LCS is "BCAB" or "BDAB"
            ("10010101", "010110", 5),        # Binary strings
            ("abcdgh", "aedfhr", 3),         # LCS is "adh"
            ("abc", "def", 0),                # No common subsequence
            ("abc", "abc", 3),                # Identical
            ("a" * 50 + "b" * 50, "b" * 50 + "a" * 50, 50),
        ],
        ids=[
            "AGGTAB-GXTXAYB",
            "ABCBDAB-BDCAB",
            "binary-strings",
            "abcdgh-aedfhr",
            "no-common",
            "identical",
            "mixed-50-50",
        ],
    )
    def test_parametrized_lcs_length(self, s1: str, s2: str, expected_len: int):
        """Parametrized test verifying LCS length for known cases."""
        result = longest_common_subsequence(s1, s2)
        assert len(result) == expected_len


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
