# IMPOSSIBLE: Self-Improving Code Optimizer

## Concept
Build a system that takes Python functions, analyzes them, generates optimized versions, benchmarks them, and decides whether to keep the improvements — all autonomously.

## Architecture

### 1. `analyzer.py` — Code Analysis
- Takes a Python function (source code string)
- Returns analysis: time complexity class (O(n), O(n²), etc.), potential issues (redundant loops, unnecessary copies, string concatenation in loops), improvement suggestions

### 2. `optimizer.py` — Code Optimization
- Takes original code + analysis
- Generates 1-3 optimized variants using pattern-based transformations:
  - List comprehension → generator (memory)
  - Repeated dict lookup → local variable
  - String concat in loop → join
  - Nested loops → set lookup
  - Redundant function calls → cache
- Returns list of (variant_name, optimized_code, transformation_description)

### 3. `benchmarker.py` — Performance Benchmarking
- Takes original function + optimized variants
- Runs each with timeit (1000+ iterations)
- Returns timing results with statistical summary
- Handles errors gracefully (if optimized code fails, report it)

### 4. `self_improver.py` — The Brain
- Full pipeline: analyze → optimize → benchmark → decide
- Decision logic: keep optimization only if ≥15% speedup AND all tests pass
- Generates a report with before/after comparisons
- Can iterate: take the best version and try to optimize it again (max 3 rounds)
- Tracks improvement history

### 5. `test_self_improver.py` — Tests (15+ tests)
- Analyzer correctly identifies O(n²) patterns
- Analyzer detects string concat in loop
- Optimizer generates valid Python code
- Optimizer handles empty/invalid input
- Benchmarker returns timing data
- Benchmarker handles failing code
- Self-improver keeps genuinely faster code
- Self-improver rejects code that's slower or broken
- Self-improver respects iteration limit
- Full pipeline works end-to-end
- Edge cases: single-line function, recursive function, empty function

## Example Usage
```python
from self_improver import SelfImprover

improver = SelfImprover()

# Define a slow function
slow_code = '''
def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i] == items[j] and items[i] not in duplicates:
                duplicates.append(items[i])
    return duplicates
'''

result = improver.improve(slow_code)
print(result['report'])
# Should find: O(n²) nested loop, suggest set-based approach
# Benchmark: set approach ~10x faster
# Decision: KEEP (≥15% speedup, tests pass)
```

## Files to Create
- `analyzer.py`
- `optimizer.py`
- `benchmarker.py`
- `self_improver.py`
- `test_self_improver.py`

## Verification
```bash
cd /home/kali/.config/opencode/self-improver
python3 test_self_improver.py
```
All 15+ tests must pass.
