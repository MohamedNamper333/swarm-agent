"""Calculator module providing basic arithmetic operations."""


def add(a: float, b: float) -> float:
    """Add two numbers.

    Args:
        a: First number.
        b: Second number.

    Returns:
        The sum of a and b.
    """
    return a + b


def subtract(a: float, b: float) -> float:
    """Subtract second number from first.

    Args:
        a: First number.
        b: Second number.

    Returns:
        The difference of a and b.
    """
    return a - b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers.

    Args:
        a: First number.
        b: Second number.

    Returns:
        The product of a and b.
    """
    return a * b


def divide(a: float, b: float) -> float:
    """Divide first number by second.

    Args:
        a: Dividend.
        b: Divisor.

    Returns:
        The quotient of a and b.

    Raises:
        ValueError: If b is zero.
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def calculate(operation: str, a: float, b: float) -> float:
    """Dispatch arithmetic operation based on operation name.

    Args:
        operation: Operation name ('add', 'subtract', 'multiply', 'divide').
        a: First number.
        b: Second number.

    Returns:
        Result of the operation.

    Raises:
        ValueError: If operation is unknown or division by zero occurs.
    """
    operations = {
        "add": add,
        "subtract": subtract,
        "multiply": multiply,
        "divide": divide,
    }

    if operation not in operations:
        raise ValueError(f"Unknown operation: {operation}")

    return operations[operation](a, b)