import pytest
from string_utils import reverse_string


def test_reverse_normal():
    assert reverse_string("hello") == "olleh"


def test_reverse_empty():
    assert reverse_string("") == ""


def test_reverse_single():
    assert reverse_string("a") == "a"


def test_reverse_unicode():
    assert reverse_string("مرحبا") == "ابحرم"