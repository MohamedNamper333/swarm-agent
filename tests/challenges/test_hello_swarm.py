"""Unit tests for hello_swarm.py."""

from hello_swarm import main


def test_main_prints_hello(capsys):
    """main() should print the Swarm v2.0 greeting."""
    main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello from Swarm v2.0!"
