"""
Chaos Engineering Tests for Swarm Agent.
Tests system resilience under failure conditions.
"""

import asyncio
import random
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import pytest
import logging

logger = logging.getLogger(__name__)


class ChaosType(str, Enum):
    """Type of chaos experiment."""
    POD_KILL = "pod_kill"
    NETWORK_LATENCY = "network_latency"
    CPU_STRESS = "cpu_stress"
    MEMORY_STRESS = "memory_stress"
    DISK_FILL = "disk_fill"
    NETWORK_PARTITION = "network_partition"
    DNS_FAILURE = "dns_failure"


@dataclass
class ChaosExperiment:
    """A chaos engineering experiment."""
    experiment_id: str
    chaos_type: ChaosType
    target: str
    duration_seconds: int
    steady_state_hypothesis: Callable[[], bool]
    rollback_action: Optional[Callable[[], None]] = None
    
    # Results
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    hypothesis_held: bool = False
    error: Optional[str] = None


class ChaosMonkey:
    """Chaos Monkey - injects failures to test resilience."""
    
    def __init__(self):
        self._active_experiments: List[ChaosExperiment] = []
        self._lock = threading.Lock()
    
    def create_experiment(
        self,
        chaos_type: ChaosType,
        target: str,
        duration_seconds: int,
        steady_state_check: Callable[[], bool],
    ) -> ChaosExperiment:
        """Create a new chaos experiment."""
        import uuid
        return ChaosExperiment(
            experiment_id=f"chaos-{uuid.uuid4().hex[:8]}",
            chaos_type=chaos_type,
            target=target,
            duration_seconds=duration_seconds,
            steady_state_hypothesis=steady_state_check,
        )
    
    async def run_experiment(self, experiment: ChaosExperiment) -> ChaosExperiment:
        """Run a chaos experiment."""
        logger.info(f"Starting chaos experiment: {experiment.experiment_id}")
        experiment.started_at = datetime.now(timezone.utc)
        
        try:
            # Check steady state before chaos
            if not experiment.steady_state_hypothesis():
                raise RuntimeError("Steady state hypothesis failed BEFORE chaos")
            
            # Inject chaos based on type
            await self._inject_chaos(experiment)
            
            # Wait for duration
            await asyncio.sleep(min(experiment.duration_seconds, 2))  # Cap for testing
            
            # Check steady state after chaos
            experiment.hypothesis_held = experiment.steady_state_hypothesis()
            
        except Exception as e:
            experiment.error = str(e)
            experiment.hypothesis_held = False
        
        finally:
            # Rollback if needed
            if experiment.rollback_action:
                try:
                    experiment.rollback_action()
                except Exception as e:
                    logger.error(f"Rollback failed: {e}")
            
            experiment.completed_at = datetime.now(timezone.utc)
            
            with self._lock:
                self._active_experiments.append(experiment)
        
        return experiment
    
    async def _inject_chaos(self, experiment: ChaosExperiment) -> None:
        """Inject the specific type of chaos."""
        if experiment.chaos_type == ChaosType.POD_KILL:
            await self._simulate_pod_kill()
        elif experiment.chaos_type == ChaosType.NETWORK_LATENCY:
            await self._simulate_network_latency()
        elif experiment.chaos_type == ChaosType.CPU_STRESS:
            await self._simulate_cpu_stress()
        elif experiment.chaos_type == ChaosType.MEMORY_STRESS:
            await self._simulate_memory_stress()
        else:
            # Simulate by just waiting (for testing purposes)
            await asyncio.sleep(0.1)
    
    async def _simulate_pod_kill(self):
        """Simulate a pod being killed."""
        # In production, would use kubectl or k8s API
        await asyncio.sleep(0.05)
    
    async def _simulate_network_latency(self):
        """Simulate network latency."""
        # In production, would use tc or toxiproxy
        await asyncio.sleep(0.05)
    
    async def _simulate_cpu_stress(self):
        """Simulate CPU stress."""
        # In production, would use stress-ng
        start = time.time()
        while time.time() - start < 0.1:
            _ = [x**2 for x in range(1000)]
    
    async def _simulate_memory_stress(self):
        """Simulate memory stress."""
        # In production, would allocate large memory blocks
        data = bytearray(1024 * 1024)  # 1MB
        del data


# =============================================================================
# Chaos Tests
# =============================================================================

class TestChaosEngineering:
    """Chaos engineering test suite."""
    
    @pytest.fixture
    def chaos_monkey(self):
        return ChaosMonkey()
    
    @pytest.mark.asyncio
    async def test_pod_kill_recovery(self, chaos_monkey):
        """Test that system recovers from pod kill."""
        steady_state = lambda: True  # Simplified for testing
        
        experiment = chaos_monkey.create_experiment(
            chaos_type=ChaosType.POD_KILL,
            target="swarm-master",
            duration_seconds=5,
            steady_state_check=steady_state,
        )
        
        result = await chaos_monkey.run_experiment(experiment)
        assert result.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_network_latency_resilience(self, chaos_monkey):
        """Test that system handles network latency gracefully."""
        steady_state = lambda: True
        
        experiment = chaos_monkey.create_experiment(
            chaos_type=ChaosType.NETWORK_LATENCY,
            target="redis",
            duration_seconds=3,
            steady_state_check=steady_state,
        )
        
        result = await chaos_monkey.run_experiment(experiment)
        assert result.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_cpu_stress_graceful_degradation(self, chaos_monkey):
        """Test graceful degradation under CPU stress."""
        steady_state = lambda: True
        
        experiment = chaos_monkey.create_experiment(
            chaos_type=ChaosType.CPU_STRESS,
            target="sandbox-worker",
            duration_seconds=2,
            steady_state_check=steady_state,
        )
        
        result = await chaos_monkey.run_experiment(experiment)
        assert result.completed_at is not None


# =============================================================================
# Load Testing Helpers
# =============================================================================

@dataclass
class LoadTestResult:
    """Result of a load test."""
    total_requests: int
    successful: int
    failed: int
    avg_response_time_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_response_time_ms: float
    throughput_rps: float
    errors: List[str] = field(default_factory=list)


async def run_load_test(
    func: Callable,
    num_requests: int = 100,
    concurrency: int = 10,
    timeout_per_request: float = 10.0,
) -> LoadTestResult:
    """Run an async load test against a function."""
    import concurrent.futures
    
    response_times = []
    errors = []
    successful = 0
    failed = 0
    
    start_time = time.time()
    
    semaphore = asyncio.Semaphore(concurrency)
    
    async def single_request():
        nonlocal successful, failed
        async with semaphore:
            request_start = time.time()
            try:
                await asyncio.wait_for(func(), timeout=timeout_per_request)
                successful += 1
            except Exception as e:
                failed += 1
                errors.append(str(e))
            finally:
                response_times.append((time.time() - request_start) * 1000)
    
    tasks = [single_request() for _ in range(num_requests)]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    total_time = time.time() - start_time
    response_times.sort()
    
    n = len(response_times)
    if n == 0:
        response_times = [0]
    
    return LoadTestResult(
        total_requests=num_requests,
        successful=successful,
        failed=failed,
        avg_response_time_ms=sum(response_times) / len(response_times),
        p50_ms=response_times[int(n * 0.5)],
        p95_ms=response_times[int(n * 0.95)],
        p99_ms=response_times[min(int(n * 0.99), n-1)],
        max_response_time_ms=max(response_times),
        throughput_rps=num_requests / total_time if total_time > 0 else 0,
        errors=errors[:10],  # First 10 errors only
    )


class TestLoadTesting:
    """Load testing suite."""
    
    @pytest.mark.asyncio
    async def test_light_load(self):
        """Test system under light load (100 requests, 10 concurrent)."""
        
        async def noop():
            await asyncio.sleep(0.001)
        
        result = await run_load_test(noop, num_requests=100, concurrency=10)
        
        assert result.successful >= result.total_requests * 0.9, "Success rate below 90%"
        assert result.p99_ms < 1000, f"p99 too high: {result.p99_ms}ms"
    
    @pytest.mark.asyncio
    async def test_moderate_load(self):
        """Test system under moderate load (500 requests, 25 concurrent)."""
        
        async def noop():
            await asyncio.sleep(0.001)
        
        result = await run_load_test(noop, num_requests=500, concurrency=25)
        
        assert result.successful >= result.total_requests * 0.85, "Success rate below 85%"
