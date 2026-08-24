#!/usr/bin/env python3
from typing import Any, Dict, List, Optional
"""
Load Test for Swarm Agent Enterprise.
Python alternative to k6 for environments without k6 installed.

Run: python3 tests/load/load_test.py [--vus 100] [--duration 60]
"""

import asyncio
import time
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, List, Optional
import argparse


@dataclass
class LoadTestConfig:
    """Configuration for load test."""
    vus: int = 100                    # Virtual users (concurrency)
    duration_seconds: int = 30        # Test duration
    ramp_up_seconds: int = 5         # Ramp-up period
    target_rps: int = 0              # 0 = unlimited
    base_url: str = "http://localhost:8080"
    scenario: str = "sandbox"         # sandbox, auth, memory, mixed


@dataclass
class LoadTestResult:
    """Results of a load test run."""
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    
    # Latency metrics (ms)
    latencies_ms: List[float] = field(default_factory=list)
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def duration_s(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0
    
    @property
    def throughput_rps(self) -> float:
        if self.duration_s > 0:
            return self.total_requests / self.duration_s
        return 0
    
    @property
    def error_rate(self) -> float:
        if self.total_requests > 0:
            return self.failed / self.total_requests
        return 0
    
    def percentile(self, p: float) -> float:
        """Get latency percentile in ms."""
        if not self.latencies_ms:
            return 0
        sorted_latencies = sorted(self.latencies_ms)
        idx = min(int(len(sorted_latencies) * p / 100), len(sorted_latencies) - 1)
        return sorted_latencies[idx]
    
    @property
    def p50(self) -> float:
        return self.percentile(50)
    
    @property
    def p95(self) -> float:
        return self.percentile(95)
    
    @property
    def p99(self) -> float:
        return self.percentile(99)
    
    @property
    def max_latency(self) -> float:
        return max(self.latencies_ms) if self.latencies_ms else 0
    
    def summary(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful": self.successful,
            "failed": self.failed,
            "error_rate": f"{self.error_rate:.2%}",
            "duration_s": round(self.duration_s, 1),
            "throughput_rps": round(self.throughput_rps, 1),
            "latency_p50_ms": round(self.p50, 1),
            "latency_p95_ms": round(self.p95, 1),
            "latency_p99_ms": round(self.p99, 1),
            "latency_max_ms": round(self.max_latency, 1),
        }


async def run_load_test(config: LoadTestConfig) -> LoadTestResult:
    """Run the load test with the given configuration."""
    
    result = LoadTestResult(
        started_at=datetime.now(timezone.utc),
    )
    
    print(f"╔═══════════════════════════════════════════╗")
    print(f"║   LOAD TEST                               ║")
    print(f"╠═══════════════════════════════════════════╣")
    print(f"║   VUs: {config.vus:<4} Duration: {config.duration_seconds}s          ║")
    print(f"║   Scenario: {config.scenario:<25} ║")
    print(f"╚═══════════════════════════════════════════╝")
    print()
    
    semaphore = asyncio.Semaphore(config.vus)
    running = True
    
    async def worker(worker_id: int):
        """Individual virtual user."""
        nonlocal result
        
        while running:
            async with semaphore:
                request_start = time.time()
                
                try:
                    await _execute_scenario(config.scenario)
                    result.successful += 1
                except Exception as e:
                    result.failed += 1
                
                latency_ms = (time.time() - request_start) * 1000
                result.latencies_ms.append(latency_ms)
                result.total_requests += 1
            
            # Small delay between requests
            await asyncio.sleep(0.01)
    
    async def _execute_scenario(scenario: str):
        """Execute a single request based on scenario."""
        from swarm.enterprise.core.execution import (
            create_sandbox, Language, ExecutionRequest, ExecutionStatus
        )
        
        if scenario == "sandbox":
            sandbox = create_sandbox('local', enable_cgroups=False)
            res = await sandbox.execute(ExecutionRequest(
                code='x = sum(i**2 for i in range(100)); print(x)',
                language=Language.PYTHON,
                tenant_id='load-test',
                actor_id=f'load-user-{random.randint(1, 100)}',
            ))
            assert res.status == ExecutionStatus.COMPLETED
        
        elif scenario == "auth":
            from swarm.enterprise.core.auth.rbac import create_rbac_engine
            rbac = create_rbac_engine()
        
        elif scenario == "security":
            from swarm.enterprise.core.security import create_dpop_manager
            dpop = create_dpop_manager()
            proof = dpop.create_proof('https://api.load-test.com', 'POST')
        
        else:
            # Default: sandbox execution
            sandbox = create_sandbox('local', enable_cgroups=False)
            res = await sandbox.execute(ExecutionRequest(
                code='print("load test")',
                language=Language.PYTHON,
                tenant_id='load-test',
            ))
    
    # Start workers
    tasks = []
    for i in range(config.vus):
        task = asyncio.create_task(worker(i))
        tasks.append(task)
    
    # Run for specified duration
    await asyncio.sleep(config.duration_seconds)
    running = False
    
    # Wait for workers to finish current requests
    await asyncio.sleep(1)
    
    # Cancel remaining tasks
    for task in tasks:
        task.cancel()
    
    result.completed_at = datetime.now(timezone.utc)
    return result


def print_results(result: LoadTestResult):
    """Print formatted load test results."""
    s = result.summary()
    
    print("\n╔═══════════════════════════════════════════╗")
    print("║   LOAD TEST RESULTS                       ║")
    print("╠═══════════════════════════════════════════╣")
    print(f"║   Total Requests:  {s['total_requests']:>8}           ║")
    print(f"║   Successful:      {s['successful']:>8}           ║")
    print(f"║   Failed:          {s['failed']:>8}           ║")
    print(f"║   Error Rate:      {s['error_rate']:>8}           ║")
    print(f"║   ─────────────────────────────────────────║")
    print(f"║   Duration:        {s['duration_s']:>7}s           ║")
    print(f"║   Throughput:      {s['throughput_rps']:>7} rps       ║")
    print(f"║   ─────────────────────────────────────────║")
    print(f"║   Latency p50:     {s['latency_p50_ms']:>7}ms          ║")
    print(f"║   Latency p95:     {s['latency_p95_ms']:>7}ms          ║")
    print(f"║   Latency p99:     {s['latency_p99_ms']:>7}ms          ║")
    print(f"║   Latency Max:     {s['latency_max_ms']:>7}ms          ║")
    print(f"╚═══════════════════════════════════════════╝")
    
    # SLA checks
    sla_pass = True
    
    if s['latency_p99_ms'] > 500:
        print("⚠️  SLA MISS: p99 latency > 500ms")
        sla_pass = False
    
    if result.error_rate > 0.01:
        print("⚠️  SLA MISS: Error rate > 1%")
        sla_pass = False
    
    if sla_pass:
        print("\n✅ ALL SLA TARGETS MET")
    else:
        print("\n❌ SLA VIOLATIONS DETECTED")


async def main():
    parser = argparse.ArgumentParser(description="Swarm Agent Load Test")
    parser.add_argument('--vus', type=int, default=10, help='Virtual users')
    parser.add_argument('--duration', type=int, default=10, help='Duration in seconds')
    parser.add_argument('--scenario', type=str, default='sandbox', 
                        choices=['sandbox', 'auth', 'security'],
                        help='Test scenario')
    
    args = parser.parse_args()
    
    config = LoadTestConfig(
        vus=args.vus,
        duration_seconds=args.duration,
        scenario=args.scenario,
    )
    
    result = await run_load_test(config)
    print_results(result)
    
    # Save report
    report = result.summary()
    report["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    with open("load_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("\n📄 Report saved to load_test_report.json")


if __name__ == "__main__":
    import random
    asyncio.run(main())
