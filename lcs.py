"""
Longest Common Subsequence (LCS) Implementation

This module provides a function to find the longest common subsequence
between two strings using dynamic programming.
"""

from __future__ import annotations


def longest_common_subsequence(s1: str, s2: str) -> str:
    """
    Find the longest common subsequence between two strings.

    A subsequence is a sequence that appears in the same relative order,
    but not necessarily contiguously. For example, "ace" is a subsequence
    of "abcde".

    This implementation uses dynamic programming with O(m*n) time and
    space complexity, where m and n are the lengths of the input strings.

    Args:
        s1: First string to compare.
        s2: Second string to compare.

    Returns:
        The longest common subsequence as a string. If there are multiple
        LCS of the same length, returns one of them (not necessarily unique).

    Examples:
        >>> longest_common_subsequence("abcde", "ace")
        'ace'
        >>> longest_common_subsequence("ABC", "ACB")
        'AB'
        >>> longest_common_subsequence("hello", "world")
        'lo'

    Note:
        - Time complexity: O(m * n)
        - Space complexity: O(m * n)
        - Returns empty string if no common subsequence exists.
    """
    if not s1 or not s2:
        return ""

    m, n = len(s1), len(s2)

    # DP table to store lengths of longest common subsequences
    dp: list[list[int]] = [[0] * (n + 1) for _ in range(m + 1)]

    # Fill the DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # Backtrack to find the actual LCS string
    lcs_chars: list[str] = []
    i, j = m, n

    while i > 0 and j > 0:
        if s1[i - 1] == s2[j - 1]:
            lcs_chars.append(s1[i - 1])
            i -= 1
            j -= 1
        elif dp[i - 1][j] > dp[i][j - 1]:
            i -= 1
        else:
            j -= 1

    # Reverse since we built it backwards
    return "".join(reversed(lcs_chars))


if __name__ == "__main__":
    # Demo with some examples
    test_cases = [
        ("abcde", "ace"),
        ("ABC", "ACB"),
        ("hello", "world"),
        ("", "anything"),
        ("same", "same"),
    ]

    for s1, s2 in test_cases:
        result = longest_common_subsequence(s1, s2)
        print(f'LCS("{s1}", "{s2}") = "{result}"')
