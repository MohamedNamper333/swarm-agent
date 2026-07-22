"""String reverse function."""

def reverse_string(s: str) -> str:
    """Reverse a string using slice notation."""
    return s[::-1]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(reverse_string(sys.argv[1]))
    else:
        print("Usage: python reverse_string.py <string>")
