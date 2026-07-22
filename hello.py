"""Simple hello world module."""


def greet(name: str = "World") -> str:
    """Return a greeting string for the given name.

    Args:
        name: Name to greet. Defaults to "World".

    Returns:
        A greeting string.
    """
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(greet())
    print(greet("Alice"))
