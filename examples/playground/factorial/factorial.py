"""Factorial calculator using recursion."""

import sys

def factorial(n: int) -> int:
    """Calculate factorial of n using recursion.
    
    Args:
        n: Non-negative integer
        
    Returns:
        Factorial of n
        
    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    return n * factorial(n - 1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python factorial.py <number>")
        sys.exit(1)
    
    try:
        n = int(sys.argv[1])
        result = factorial(n)
        print(f"{n}! = {result}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
