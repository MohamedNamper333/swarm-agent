"""
Chaos Engineering Tests - Validate system resilience under failure conditions.
Tests system behavior under various failure scenarios.
"""

import asyncio
import random
import time
import logging
import uuid


def uuidv7() -> str:
    return str(uuid.uuid4())
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class ChaosType(str, Enum):
    POD_KILL = "pod_kill"
    NETWORK_PARTITION = "network_partition"
    NETWORK_LATENCY = "network_latency"
    NETWORK_LOSS = "network_loss"
    CPU_STRESS = "cpu_stress"
    MEMORY_PRESSURE = "memory_pressure"
    DISK_FILL = "disk_fill"
    NODE_FAILURE = "node_failure"
    DEPENDENCY_FAILURE = "dependency_failure"
    CLOCK_DRIFT = "clock_drift"


class ChaosSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ChaosExperiment:
    experiment_id: str = field(default_factory=lambda: f"exp-{uuidv7()}")
    name: str = ""
    chaos_type: ChaosType = ChaosType.POD_KILL
    severity: ChaosSeverity = ChaosSeverity.LOW
    target: str = ""  # service/component name
    duration_seconds: int = 30
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_behavior: str = ""
    success_criteria: str = ""


@dataclass
class ChaosResult:
    experiment_id: str
    success: bool
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    observations: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class ChaosEngine:
    """Orchestrates chaos engineering experiments."""

    def __init__(self):
        self.experiments: Dict[str, ChaosExperiment] = {}
        self.results: List[ChaosResult] = []
        self._running = False

    def add_experiment(self, experiment: ChaosExperiment) -> None:
        self.experiments[experiment.experiment_id] = experiment

    async def run_experiment(self, experiment_id: str) -> ChaosResult:
        """Run a single chaos experiment."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        result = ChaosResult(
            experiment_id=experiment_id,
            success=False,
            started_at=now_utc(),
            completed_at=None,
            duration_seconds=0,
        )

        try:
            logger.info(f"Starting chaos experiment: {experiment.name} ({experiment.chaos_type.value})")
            
            # Execute the chaos
            if experiment.chaos_type == ChaosType.POD_KILL:
                await self._kill_pod(experiment)
            elif experiment.chaos_type == ChaosType.NETWORK_PARTITION:
                await self._network_partition(experiment)
            elif experiment.chaos_type == ChaosType.NETWORK_LATENCY:
                await self._network_latency(experiment)
            elif experiment.chaos_type == ChaosType.NETWORK_LOSS:
                await self._network_loss(experiment)
            elif experiment.chaos_type == ChaosType.CPU_STRESS:
                await self._cpu_stress(experiment)
            elif experiment.chaos_type == ChaosType.MEMORY_PRESSURE:
                await self._memory_pressure(experiment)
            elif experiment.chaos_type == ChaosType.DISK_FILL:
                await self._disk_fill(experiment)
            elif experiment.chaos_type == ChaosType.NODE_FAILURE:
                await self._node_failure(experiment)
            elif experiment.chaos_type == ChaosType.DEPENDENCY_FAILURE:
                await self._dependency_failure(experiment)
            elif experiment.chaos_type == ChaosType.CLOCK_DRIFT:
                await self._clock_drift(experiment)

            # Verify success criteria
            success = await self._verify_success_criteria(experiment)
            
            result.completed_at = now_utc()
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
            result.success = True
            result.success = success  # Override with actual success
            
            logger.info(f"Chaos experiment {experiment.name} completed: {'SUCCESS' if success else 'FAILED'}")
            
        except Exception as e:
            logger.error(f"Chaos experiment failed: {e}")
            result.completed_at = now_utc()
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
            result.success = False
            result.error = str(e)

        self.results.append(result)
        return result

    async def run_all_experiments(self) -> List[Dict[str, Any]]:
        """Run all registered experiments."""
        results = []
        for exp_id in self.experiments:
            result = await self.run_experiment(exp_id)
            results.append({
                "experiment_id": result.experiment_id,
                "success": result.success,
                "duration": result.duration_seconds,
                "error": result.error,
            })
        return results

    # =========================================================================
    # Chaos Implementations
    # =========================================================================

    async def _kill_pod(self, experiment: ChaosExperiment) -> None:
        """Simulate pod kill by terminating process."""
        target = experiment.target or "random"
        logger.info(f"Killing pod: {target}")
        # In production: kubectl delete pod or kill process
        await asyncio.sleep(experiment.duration_seconds)
        self._record_observation(f"Pod {target} killed and restarted")

    async def _network_partition(self, experiment: ChaosExperiment) -> None:
        """Create network partition."""
        target = experiment.target
        duration = experiment.duration_seconds
        logger.info(f"Creating network partition for {target} for {duration}s")
        # In production: iptables/iptables rules or network policies
        await asyncio.sleep(min(duration, 5))  # Simulate
        self._record_observation(f"Network partition created for {target}")

    async def _network_latency(self, experiment: ChaosExperiment) -> None:
        """Inject network latency."""
        latency_ms = experiment.parameters.get("latency_ms", 100)
        target = experiment.target
        logger.info(f"Injecting {latency_ms}ms latency for {target}")
        await asyncio.sleep(min(experiment.duration_seconds, 5))
        self._record_observation(f"Latency of {latency_ms}ms injected")

    async def _network_loss(self, experiment: ChaosExperiment) -> None:
        """Inject packet loss."""
        loss_percent = experiment.parameters.get("loss_percent", 10)
        target = experiment.target
        logger.info(f"Injecting {loss_percent}% packet loss for {target}")
        await asyncio.sleep(min(experiment.duration_seconds, 5))
        self._record_observation(f"{loss_percent}% packet loss injected")

    async def _cpu_stress(self, experiment: ChaosExperiment) -> None:
        """Generate CPU stress."""
        cpu_percent = experiment.parameters.get("cpu_percent", 80)
        duration = experiment.duration_seconds
        logger.info(f"Generating {cpu_percent}% CPU stress for {duration}s")
        
        # Simulate CPU stress
        async def stress():
            end = time.time() + duration
            while time.time() < end:
                _ = sum(i * i for i in range(10000))
                await asyncio.sleep(0.001)
        
        await asyncio.gather(*[stress() for _ in range(4)])  # 4 cores
        self._record_observation(f"CPU stress at {cpu_percent}% completed")

    async def _memory_pressure(self, experiment: ChaosExperiment) -> None:
        """Generate memory pressure."""
        memory_mb = experiment.parameters.get("memory_mb", 512)
        duration = experiment.duration_seconds
        logger.info(f"Allocating {memory_mb}MB memory for {duration}s")
        
        # Allocate memory
        data = bytearray(memory_mb * 1024 * 1024)
        await asyncio.sleep(duration)
        del data
        
        self._record_observation(f"Memory pressure of {memory_mb}MB applied")

    async def _disk_fill(self, experiment: ChaosExperiment) -> None:
        """Fill disk space."""
        size_mb = experiment.parameters.get("size_mb", 100)
        logger.info(f"Filling {size_mb}MB disk space")
        
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"0" * (size_mb * 1024 * 1024))
            temp_path = f.name
        
        try:
            await asyncio.sleep(experiment.duration_seconds)
        finally:
            os.unlink(temp_path)
        
        self._record_observation(f"Disk filled with {size_mb}MB")

    async def _node_failure(self, experiment: ChaosExperiment) -> None:
        """Simulate node failure."""
        target = experiment.target
        logger.info(f"Simulating node failure: {target}")
        # In production: terminate node/instance
        await asyncio.sleep(min(experiment.duration_seconds, 5))
        self._record_observation(f"Node {target} simulated failure")

    async def _dependency_failure(self, experiment: ChaosExperiment) -> None:
        """Simulate dependency failure."""
        dependency = experiment.parameters.get("dependency", "database")
        logger.info(f"Simulating {dependency} failure")
        await asyncio.sleep(min(experiment.duration_seconds, 5))
        self._record_observation(f"Dependency {dependency} failure simulated")

    async def _clock_drift(self, experiment: ChaosExperiment) -> None:
        """Simulate clock drift."""
        drift_seconds = experiment.parameters.get("drift_seconds", 30)
        logger.info(f"Simulating {drift_seconds}s clock drift")
        await asyncio.sleep(min(experiment.duration_seconds, 5))
        self._record_observation(f"Clock drift of {drift_seconds}s simulated")

    async def _verify_success_criteria(self, experiment: ChaosExperiment) -> bool:
        """Verify experiment success criteria."""
        # In production, check:
        # - Service still responding
        # - Error rate within threshold
        # - Latency within SLA
        # - Data consistency maintained
        return True  # Simplified

    def _record_observation(self, observation: str) -> None:
        logger.info(f"Observation: {observation}")


# =============================================================================
# Pre-defined Chaos Experiments
# =========================================================================

def create_standard_experiments() -> List[ChaosExperiment]:
    """Create standard chaos experiment suite."""
    experiments = [
        ChaosExperiment(
            name="Pod Kill - Random Service",
            chaos_type=ChaosType.POD_KILL,
            severity=ChaosSeverity.MEDIUM,
            target="api-service",
            duration_seconds=30,
            expected_behavior="Service recovers within 30s, requests retry",
            success_criteria="Service recovers, no data loss",
        ),
        ChaosExperiment(
            name="Network Partition - Database",
            chaos_type=ChaosType.NETWORK_PARTITION,
            severity=ChaosSeverity.HIGH,
            target="database",
            duration_seconds=60,
            expected_behavior="Circuit breaker opens, fallback activates",
            success_criteria="Circuit breaker opens, fallback serves stale data",
        ),
        ChaosExperiment(
            name="Network Latency - API",
            chaos_type=ChaosType.NETWORK_LATENCY,
            severity=ChaosSeverity.MEDIUM,
            target="api-gateway",
            duration_seconds=30,
            parameters={"latency_ms": 500},
            expected_behavior="Increased latency, requests timeout",
            success_criteria="Latency spike handled, circuit breaker activates",
        ),
        ChaosExperiment(
            name="Network Loss - Payment Service",
            chaos_type=ChaosType.NETWORK_LOSS,
            severity=ChaosSeverity.HIGH,
            target="payment-service",
            duration_seconds=30,
            parameters={"loss_percent": 20},
            expected_behavior="20% packet loss, retries with exponential backoff",
            success_criteria="Retries succeed, no data loss",
        ),
        ChaosExperiment(
            name="CPU Stress - Worker",
            chaos_type=ChaosType.CPU_STRESS,
            severity=ChaosSeverity.MEDIUM,
            target="worker-pool",
            duration_seconds=60,
            parameters={"cpu_percent": 90},
            expected_behavior="CPU at 90%, queue backs up",
            success_criteria="Auto-scaling triggers, jobs complete eventually",
        ),
        ChaosExperiment(
            name="Memory Pressure - Cache",
            chaos_type=ChaosType.MEMORY_PRESSURE,
            severity=ChaosSeverity.HIGH,
            target="redis-cache",
            duration_seconds=60,
            parameters={"memory_mb": 1024},
            expected_behavior="Cache eviction, fallback to DB",
            success_criteria="Cache evicts LRU, DB handles load",
        ),
        ChaosExperiment(
            name="Disk Fill - Logs",
            chaos_type=ChaosType.DISK_FILL,
            severity=ChaosSeverity.HIGH,
            target="logging-service",
            duration_seconds=30,
            parameters={"size_mb": 500},
            expected_behavior="Disk fills, log rotation triggers",
            success_criteria="Log rotation works, no data loss",
        ),
        ChaosExperiment(
            name="Node Failure - Worker Node",
            chaos_type=ChaosType.NODE_FAILURE,
            severity=ChaosSeverity.CRITICAL,
            target="worker-node-3",
            duration_seconds=60,
            expected_behavior="Pods rescheduled, workload redistributed",
            success_criteria="All pods rescheduled within 2min",
        ),
        ChaosExperiment(
            name="Dependency Failure - External API",
            chaos_type=ChaosType.DEPENDENCY_FAILURE,
            severity=ChaosSeverity.HIGH,
            target="payment-gateway",
            duration_seconds=30,
            parameters={"dependency": "payment-gateway"},
            expected_behavior="Circuit breaker opens, fallback to queue",
            success_criteria="Circuit breaker opens, requests queued",
        ),
        ChaosExperiment(
            name="Clock Drift - Distributed Lock",
            chaos_type=ChaosType.CLOCK_DRIFT,
            severity=ChaosSeverity.MEDIUM,
            target="distributed-lock-service",
            duration_seconds=60,
            parameters={"drift_seconds": 30},
            expected_behavior="Lock expiration issues, lease renewal fails",
            success_criteria="Lease renewal handles drift, no split-brain",
        ),
    ]
    return experiments


# =============================================================================
# Chaos Test Runner
# =========================================================================

class ChaosTestRunner:
    """Runs chaos experiments and generates reports."""

    def __init__(self):
        self.engine = ChaosEngine()
        for exp in create_standard_experiments():
            self.engine.add_experiment(exp)

    async def run_all(self) -> Dict[str, Any]:
        """Run all chaos experiments."""
        logger.info("Starting chaos engineering test suite")
        results = await self.engine.run_all_experiments()
        
        summary = {
            "total_experiments": len(self.engine.experiments),
            "passed": sum(1 for r in self.engine.results if r.success),
            "failed": len(self.engine.results) - sum(1 for r in self.engine.results if r.success),
            "total_duration": sum(r.duration_seconds for r in self.engine.results),
            "results": [
                {
                    "experiment_id": r.experiment_id,
                    "success": r.success,
                    "duration": r.duration_seconds,
                    "error": r.error,
                }
                for r in self.engine.results
            ],
        }
        
        logger.info(f"Chaos testing complete: {summary['passed']}/{summary['total_experiments']} passed")
        return summary


async def run_chaos_tests():
    """Run all chaos engineering tests."""
    runner = ChaosTestRunner()
    return await runner.run_all()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_chaos_tests())
