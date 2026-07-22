# Calculator — Design Document

## 1. Function Signatures

```python
# Primary unified API
def calculate(operation: str, a: float, b: float) -> float

# Individual operations (exposed for direct use / unit testing)
def add(a: float, b: float) -> float
def subtract(a: float, b: float) -> float
def multiply(a: float, b: float) -> float
def divide(a: float, b: float) -> float
```

### Valid `operation` strings
| String       | Maps to      |
|--------------|--------------|
| `"add"`      | `add(a, b)`  |
| `"subtract"` | `subtract(a, b)` |
| `"multiply"` | `multiply(a, b)` |
| `"divide"`   | `divide(a, b)` |

## 2. Error Handling Strategy

| Error Case               | Exception Type    | Message Pattern                     |
|--------------------------|-------------------|-------------------------------------|
| Division by zero         | `ValueError`      | `"Cannot divide by zero"`           |
| Invalid operation string | `ValueError`      | `"Invalid operation: '{op}'"`       |
| Non-numeric inputs       | `TypeError`       | `"Operands must be numeric"`        |

All errors propagate to the caller — no silent fallbacks. The `calculate` function acts as a single dispatch point, delegating to the individual `add`/`subtract`/`multiply`/`divide` functions which remain independently testable.

## 3. Module Organization

```
calculator/
  __init__.py       # Public API: calculate(), re-exports add/subtract/multiply/divide
  operations.py     # Pure implementations of add, subtract, multiply, divide
  exceptions.py     # Custom exception classes (optional, can use builtins)
```

For a single-file approach (simpler):

```
calculator.py       # All functions + calculate() dispatcher
```

## 4. Edge Cases to Consider

| Category          | Case                                    | Expected Behavior                    |
|-------------------|-----------------------------------------|--------------------------------------|
| Division          | `divide(0, 5)`                          | Returns `0.0`                        |
| Division          | `divide(5, 0)`                          | Raises `ValueError`                  |
| Division          | `divide(0, 0)`                          | Raises `ValueError`                  |
| Division          | `divide(1, 3)`                          | Returns `0.333...` (float precision)  |
| Float precision   | `add(0.1, 0.2)`                         | `0.30000000000000004` (IEEE 754)     |
| Float precision   | `subtract(0.3, 0.1)`                    | `0.19999999999999998`                |
| Negative numbers  | `add(-5, -3)`                           | Returns `-8`                         |
| Negative numbers  | `subtract(-5, -3)`                      | Returns `-2`                         |
| Negative numbers  | `multiply(-3, -4)`                      | Returns `12`                         |
| Negative numbers  | `divide(-10, -2)`                       | Returns `5.0`                        |
| Zero              | `add(0, 0)`                             | Returns `0`                          |
| Zero              | `multiply(0, 5)`                        | Returns `0`                          |
| Large numbers     | `multiply(1e200, 1e200)`                | Returns `inf` (overflow)             |
| Large numbers     | `subtract(1e200, 1e200)`                | Returns `0.0`                        |
| Invalid operation | `calculate("power", 2, 3)`              | Raises `ValueError`                  |
| String input      | `calculate("add", "a", 3)`              | Raises `TypeError`                   |
| None input        | `calculate("add", None, 3)`             | Raises `TypeError`                   |
