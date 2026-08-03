"""String reverse function using slice."""

def reverse_string(s: str) -> str:
    """Return the reversed string."""
    return s[::-1]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python reverse.py <string>")
        sys.exit(1)
    print(reverse_string(sys.argv[1]))
