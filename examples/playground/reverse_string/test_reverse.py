"""Tests for reverse_string function."""

import pytest
from reverse import reverse_string


class TestReverseString:
    def test_empty(self):
        assert reverse_string("") == ""

    def test_single_char(self):
        assert reverse_string("a") == "a"

    def test_simple(self):
        assert reverse_string("hello") == "olleh"

    def test_palindrome(self):
        assert reverse_string("racecar") == "racecar"

    def test_unicode(self):
        assert reverse_string("مرحبا") == "ابحرم"

    def test_spaces(self):
        assert reverse_string("a b c") == "c b a"
