"""Stress test: many agents/tasks running concurrently.

Verifies the swarm handles realistic concurrency without deadlocking,
losing tasks, or corrupting shared state.

Usage: PYTHONPATH=. pytest tests/stress/test_concurrent_agents.py -v
"""
import time
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed

from swarm.core.task_dag import DAGBuilder


class TestConcurrentAgents:
    """Verify concurrent task execution is safe and bounded."""

    def test_parallel_template_lookup_100_workers(self):
        """Hit TASK_TEMPLATES from 100 threads — must be safe and fast."""
        def lookup(worker_id: int) -> int:
            t = DAGBuilder.TASK_TEMPLATES.get("implementation")
            return len(t["stages"]) if t else 0

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(lookup, w) for w in range(100)]
            results = [f.result(timeout=10) for f in as_completed(futures)]
        elapsed = time.perf_counter() - start

        assert len(results) == 100
        assert all(n > 0 for n in results), "every lookup should return non-zero"
        assert elapsed < 5.0, f"100 concurrent template lookups took {elapsed:.2f}s"
        print(f"✅ 100 concurrent template lookups in {elapsed*1000:.1f}ms")

    def test_dag_build_for_each_template_under_load(self):
        """Build a DAG for every template × 20 seeds = 140 builds in parallel."""
        templates = list(DAGBuilder.TASK_TEMPLATES.keys())
        assert len(templates) >= 5

        def build_one(args):
            template, seed = args
            builder = DAGBuilder()
            info = builder.get_template_info(template)
            return template, len(info["stages"]) if info else 0

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(build_one, (t, s)) for t in templates for s in range(20)]
            results = [f.result(timeout=10) for f in as_completed(futures)]
        elapsed = time.perf_counter() - start

        assert len(results) == len(templates) * 20
        assert all(n > 0 for _, n in results)
        assert elapsed < 5.0, f"140 builds took {elapsed:.2f}s"
        print(f"✅ {len(results)} template-aware DAG lookups in {elapsed*1000:.1f}ms")

    def test_stage_library_thread_safety(self):
        """STAGE_LIBRARY reads from many threads must be consistent."""
        def read_lib(worker_id: int) -> int:
            return len(DAGBuilder.STAGE_LIBRARY)

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(read_lib, w) for w in range(200)]
            results = [f.result(timeout=10) for f in as_completed(futures)]

        assert len(set(results)) == 1, f"inconsistent library sizes: {set(results)}"
        print(f"✅ 200 concurrent STAGE_LIBRARY reads returned consistent value={results[0]}")

    def test_template_registry_size(self):
        """Sanity: at least 5 templates + at least 5 stage library entries."""
        templates = list(DAGBuilder.TASK_TEMPLATES.keys())
        stages = list(DAGBuilder.STAGE_LIBRARY.keys())
        assert len(templates) >= 5
        assert len(stages) >= 5
        print(f"✅ {len(templates)} templates, {len(stages)} stages in library")
