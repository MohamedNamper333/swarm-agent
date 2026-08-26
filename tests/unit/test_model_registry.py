"""
Unit tests for ModelRegistry and HealthMonitor
"""
import pytest
import time
from swarm.core.model_registry import ModelRegistry, ModelConfig, ModelHealth, ModelStatus
from swarm.core.health_monitor import HealthMonitor, CircuitBreaker, CircuitState


class TestModelConfig:
    """Tests for ModelConfig dataclass"""

    def test_model_config_creation(self):
        config = ModelConfig(
            id="test-model",
            provider="opencode",
            model="opencode/test-model-free",
            priority=1,
            capabilities=["coding", "reasoning"]
        )
        assert config.id == "test-model"
        assert config.provider == "opencode"
        assert config.priority == 1
        assert "coding" in config.capabilities


class TestModelRegistry:
    """Tests for ModelRegistry"""

    def setup_method(self):
        self.registry = ModelRegistry()

    def test_default_models_loaded(self):
        """Test that default models are loaded"""
        assert "innovator" in self.registry.models
        assert "critic" in self.registry.models
        assert "architect" in self.registry.models
        assert "explorer" in self.registry.models
        assert "reviewer" in self.registry.models
        assert "reasoner" in self.registry.models
        assert "vision-coder" in self.registry.models
        assert "laguna-s-2-1" in self.registry.models
        assert "nemotron-3.5-lightning" in self.registry.models
        assert "swarm-worker-qa" in self.registry.models

    def test_primary_model_selection(self):
        """Test getting primary model for a worker"""
        primary = self.registry.get_primary_model("innovator")
        assert primary is not None
        assert primary.id == "nemotron-3.5-lightning"
        assert primary.priority == 1

    def test_fallback_chain(self):
        """Test fallback chain for innovator"""
        chain = self.registry.get_fallback_chain("innovator")
        assert len(chain) == 2
        assert chain[0].id == "nemotron-3.5-lightning"
        assert chain[1].id == "tencent-hy3"

    def test_get_models_for_worker(self):
        """Test getting all models for a worker"""
        models = self.registry.get_models_for_worker("critic")
        assert len(models) == 1
        assert models[0].id == "nemotron-ultra"

    def test_health_tracking(self):
        """Test health recording"""
        worker = "innovator"
        model_id = "nemotron-3.5-lightning"
        
        # Initial state should be healthy (default is HEALTHY)
        assert self.registry.is_healthy(worker, model_id) == True
        
        # Record some successes
        self.registry.record_success(worker, model_id, latency=0.5)
        self.registry.record_success(worker, model_id, latency=0.3)
        
        stats = self.registry.get_stats(worker)
        assert stats[model_id]["success_rate"] == 1.0
        assert stats[model_id]["avg_latency"] == 0.3  # last latency

    def test_failure_tracking(self):
        """Test failure tracking and unhealthy detection"""
        worker = "innovator"
        model_id = "nemotron-3.5-lightning"
        
        # Initial state should be healthy
        assert self.registry.is_healthy(worker, model_id) == True
        
        # Record some failures (below threshold of 3)
        self.registry.record_failure(worker, model_id)
        self.registry.record_failure(worker, model_id)
        # Should still be healthy (DEGRADED is still considered healthy for routing)
        assert self.registry.is_healthy(worker, model_id) == True
        
        # Third failure should mark as unhealthy
        self.registry.record_failure(worker, model_id)
        assert self.registry.is_healthy(worker, model_id) == False

    def test_get_stats(self):
        """Test stats retrieval"""
        self.registry.record_success("innovator", "nemotron-3.5-lightning", 0.5)
        self.registry.record_failure("innovator", "nemotron-3.5-lightning")
        
        stats = self.registry.get_stats("innovator")
        assert "nemotron-3.5-lightning" in stats
        assert stats["nemotron-3.5-lightning"]["success_rate"] == 0.5
        assert stats["nemotron-3.5-lightning"]["consecutive_failures"] == 1


class TestCircuitBreaker:
    """Tests for CircuitBreaker"""

    def test_initial_state(self):
        cb = CircuitBreaker("test:model")
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_failure_threshold(self):
        cb = CircuitBreaker("test:model", failure_threshold=3)
        
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 1
        
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 2
        
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    def test_success_resets_failures(self):
        cb = CircuitBreaker("test:model", failure_threshold=3)
        
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2
        
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_circuit_open_blocks_execution(self):
        cb = CircuitBreaker("test:model", failure_threshold=2)
        
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        
        assert cb.can_execute() == False

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker("test:model", failure_threshold=2, recovery_timeout=1)
        
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(1.1)
        # Trigger state transition
        cb.can_execute()
        
        # Should transition to half-open and allow execution
        assert cb.can_execute() == True
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker("test:model", failure_threshold=2, recovery_timeout=1)
        
        cb.record_failure()
        cb.record_failure()
        time.sleep(1.1)
        # Trigger state transition
        cb.can_execute()
        assert cb.state == CircuitState.HALF_OPEN
        
        # Failure in half-open should reopen to OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN


class TestHealthMonitor:
    """Tests for HealthMonitor"""

    def setup_method(self):
        self.registry = ModelRegistry()
        self.monitor = HealthMonitor(self.registry, check_interval=1)

    def teardown_method(self):
        self.monitor.stop()

    def test_initialization(self):
        assert self.monitor.check_interval == 1
        assert self.monitor._running == False

    def test_can_execute(self):
        assert self.monitor.can_execute("innovator", "nemotron-3.5-lightning") == True

    def test_record_success_and_failure(self):
        self.monitor.record_success("innovator", "nemotron-3.5-lightning", 0.1)
        self.monitor.record_failure("innovator", "nemotron-3.5-lightning")
        
        stats = self.monitor.get_stats()
        # Should track the operations
        circuit_status = self.monitor.get_all_circuit_status()
        assert "innovator:nemotron-3.5-lightning" in circuit_status

    def test_circuit_breaker_integration(self):
        """Test circuit breaker opens after threshold failures"""
        for _ in range(3):
            self.monitor.record_failure("innovator", "nemotron-3.5-lightning")
        
        # Circuit should be open
        assert self.monitor.can_execute("innovator", "nemotron-3.5-lightning") == False
        
        # Get circuit status
        status = self.monitor.get_circuit_status("innovator", "nemotron-3.5-lightning")
        assert status["state"] == "open"

    def test_health_check_runs(self):
        """Test that health checks can run"""
        self.monitor.run_health_checks()
        stats = self.monitor.get_stats()
        assert stats["total_checks"] >= 1

    def test_circuit_recovery(self):
        """Test circuit breaker recovery after timeout"""
        monitor = HealthMonitor(self.registry, check_interval=1)
        monitor.circuit_breaker_threshold = 2
        monitor.circuit_breaker_timeout = 1  # 1 second for testing
        
        # First, open the circuit by recording failures
        monitor.record_failure("innovator", "nemotron-3.5-lightning")
        monitor.record_failure("innovator", "nemotron-3.5-lightning")
        assert monitor.can_execute("innovator", "nemotron-3.5-lightning") == False
        
        # Wait for recovery timeout
        time.sleep(1.2)
        
        # Should transition to half-open and allow execution
        assert monitor.can_execute("innovator", "nemotron-3.5-lightning") == True
        
        monitor.stop()


class TestIntegration:
    """Integration tests between ModelRegistry and HealthMonitor"""

    def test_registry_and_monitor_integration(self):
        registry = ModelRegistry()
        monitor = HealthMonitor(registry, check_interval=1)
        
        # Test that monitor can access registry models
        models = registry.get_models_for_worker("architect")
        assert len(models) > 0
        
        # Test that monitor can track health
        monitor.record_success("architect", "nemotron-ultra")
        monitor.record_failure("architect", "nemotron-ultra")
        
        stats = registry.get_stats("architect")
        assert "nemotron-ultra" in stats
        
        monitor.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
