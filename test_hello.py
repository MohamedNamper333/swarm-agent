"""Tests for hello module."""

from hello import greet


def test_greet_default():
    assert greet() == "Hello, World!"


def test_greet_named():
    assert greet("Alice") == "Hello, Alice!"


def test_greet_empty_string():
    assert greet("") == "Hello, !"
