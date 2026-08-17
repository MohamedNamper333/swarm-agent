"""Tests for Workflow Engine Stage 2 P1 fixes.

- 2.1: Iterative topological sort handles deep chains + detects cycles
- 2.2: WorkflowStep raises on missing required keys
- 2.3: Compensation timeout enforcement cancels hanging step
"""
import time
import pytest

from swarm.enterprise.core.job.compensation import (
    CompensationEngine,
    WorkflowExecution,
    WorkflowStep,
    WorkflowStepStatus,
    CompensationPolicy,
    StepTimeoutError,
    _run_with_timeout,
    create_compensable_workflow,
)


# ============================================================
# 2.1: Iterative topological sort
# ============================================================

class TestTopologicalSort:
    def _make_engine_with_linear_chain(self, length: int) -> CompensationEngine:
        """Build a workflow where step_i depends on step_{i-1}."""
        engine = CompensationEngine()
        workflow = WorkflowExecution(
            workflow_id=f"chain-{length}",
            workflow_type="chain",
        )
        for i in range(length):
            step = WorkflowStep(
                step_id=f"step-{i}",
                name=f"Step {i}",
                execute_fn=lambda inputs: inputs,
                depends_on=[f"step-{i-1}"] if i > 0 else [],
                provides=[f"out-{i}"],
                requires=[f"out-{i-1}"] if i > 0 else [],
            )
            workflow.steps[step.step_id] = step
        engine.register_workflow(workflow)
        return engine

    def test_topological_sort_handles_deep_chain(self):
        """A chain of 1000 steps should sort without RecursionError."""
        length = 1000
        engine = self._make_engine_with_linear_chain(length)
        workflow = engine.get_workflow(f"chain-{length}")
        order = engine._topological_sort(workflow)
        assert len(order) == length
        # Verify chain order preserved
        assert order[0] == "step-0"
        assert order[-1] == f"step-{length-1}"

    def test_topological_sort_handles_diamond(self):
        """Diamond: A -> B,C -> D."""
        engine = CompensationEngine()
        workflow = WorkflowExecution(workflow_id="diamond", workflow_type="diamond")
        workflow.steps = {
            "a": WorkflowStep(step_id="a", name="A", execute_fn=lambda i: i),
            "b": WorkflowStep(
                step_id="b", name="B", execute_fn=lambda i: i,
                depends_on=["a"], provides=["b_out"], requires=["a_out"],
            ),
            "c": WorkflowStep(
                step_id="c", name="C", execute_fn=lambda i: i,
                depends_on=["a"], provides=["c_out"], requires=["a_out"],
            ),
            "d": WorkflowStep(
                step_id="d", name="D", execute_fn=lambda i: i,
                depends_on=["b", "c"], requires=["b_out", "c_out"],
            ),
        }
        engine.register_workflow(workflow)
        order = engine._topological_sort(workflow)
        assert order[0] == "a"
        assert order[-1] == "d"
        # b and c can be in any order but must be between a and d
        assert order.index("a") < order.index("b") < order.index("d")
        assert order.index("a") < order.index("c") < order.index("d")

    def test_topological_sort_detects_cycle(self):
        """A -> B -> A should raise ValueError."""
        engine = CompensationEngine()
        workflow = WorkflowExecution(workflow_id="cycle", workflow_type="cycle")
        workflow.steps = {
            "a": WorkflowStep(
                step_id="a", name="A", execute_fn=lambda i: i,
                depends_on=["b"], requires=["b_out"],
            ),
            "b": WorkflowStep(
                step_id="b", name="B", execute_fn=lambda i: i,
                depends_on=["a"], provides=["b_out"], requires=["a_out"],
            ),
        }
        with pytest.raises(ValueError, match="[Cc]ycle"):
            engine._topological_sort(workflow)

    def test_topological_sort_rejects_unknown_dependency(self):
        """Step depending on non-existent step should raise ValueError."""
        engine = CompensationEngine()
        workflow = WorkflowExecution(workflow_id="bad", workflow_type="bad")
        workflow.steps = {
            "x": WorkflowStep(
                step_id="x", name="X", execute_fn=lambda i: i,
                depends_on=["nonexistent"],
            ),
        }
        with pytest.raises(ValueError, match="unknown step"):
            engine._topological_sort(workflow)


# ============================================================
# 2.2: Raise on missing required keys
# ============================================================

class TestMissingRequiredKeys:
    def test_missing_required_key_raises(self):
        """Step with requires=['foo'] must raise ValueError if 'foo' missing."""
        engine = CompensationEngine()
        workflow = WorkflowExecution(workflow_id="miss", workflow_type="miss")
        workflow.steps = {
            "step1": WorkflowStep(
                step_id="step1", name="Step 1",
                execute_fn=lambda i: {"out1": "value"},
                provides=["out1"],
            ),
            "step2": WorkflowStep(
                step_id="step2", name="Step 2",
                execute_fn=lambda i: {"out2": "ok"},
                requires=["missing_key"],
                depends_on=["step1"],
            ),
        }
        engine.register_workflow(workflow)

        with pytest.raises(ValueError, match="missing_key"):
            engine.execute("miss")

    def test_present_required_key_passes(self):
        """Sanity: when upstream step provides the key, no error."""
        engine = CompensationEngine()
        workflow = WorkflowExecution(workflow_id="ok", workflow_type="ok")
        workflow.steps = {
            "step1": WorkflowStep(
                step_id="step1", name="Step 1",
                execute_fn=lambda i: {"out1": "hello"},
                provides=["out1"],
            ),
            "step2": WorkflowStep(
                step_id="step2", name="Step 2",
                execute_fn=lambda i: {"out2": i["out1"] + "_world"},
                requires=["out1"],
                depends_on=["step1"],
                provides=["out2"],
            ),
        }
        engine.register_workflow(workflow)
        result = engine.execute("ok")
        assert result.status == "succeeded"
        assert result.steps["step2"].result["out2"] == "hello_world"

    def test_missing_keys_error_lists_available(self):
        """Error message should list available context keys for debugging."""
        engine = CompensationEngine()
        workflow = WorkflowExecution(workflow_id="debug", workflow_type="debug")
        workflow.steps = {
            "step1": WorkflowStep(
                step_id="step1", name="Step 1",
                execute_fn=lambda i: {},
            ),
            "step2": WorkflowStep(
                step_id="step2", name="Step 2",
                execute_fn=lambda i: {},
                requires=["needed"],
                depends_on=["step1"],
            ),
        }
        engine.register_workflow(workflow)
        with pytest.raises(ValueError) as exc_info:
            engine.execute("debug")
        msg = str(exc_info.value)
        assert "needed" in msg
        assert "step2" in msg


# ============================================================
# 2.3: Compensation timeout enforcement
# ============================================================

class TestTimeoutEnforcement:
    def test_run_with_timeout_cancels_hanging_step(self):
        """_run_with_timeout must raise StepTimeoutError on hanging callable."""
        def hang_forever(inputs):
            time.sleep(10)
            return inputs

        start = time.time()
        with pytest.raises(StepTimeoutError) as exc_info:
            _run_with_timeout(hang_forever, ({"k": 1},), timeout_ms=100)
        elapsed_ms = (time.time() - start) * 1000

        assert exc_info.value.timeout_ms == 100
        assert exc_info.value.phase == "execute"
        # Should cancel within reasonable time, not wait the full 10s
        assert elapsed_ms < 5000

    def test_run_with_timeout_returns_result_on_success(self):
        """Normal completion must return the result."""
        def fast_fn(inputs):
            return {"computed": inputs["x"] * 2}

        result = _run_with_timeout(fast_fn, ({"x": 5},), timeout_ms=1000)
        assert result == {"computed": 10}

    def test_workflow_step_timeout_triggers_compensation(self):
        """A step that hangs past its timeout should trigger compensation."""
        engine = CompensationEngine()

        completed_steps = []

        def slow_step(inputs):
            time.sleep(5)  # Hangs well past timeout
            return {"out": "never"}

        def fast_step(inputs):
            return {"out": "fast"}

        def compensate_first(context, result):
            completed_steps.append("first")

        def compensate_second(context, result):
            completed_steps.append("second")

        workflow = WorkflowExecution(workflow_id="timeout-wf", workflow_type="timeout")
        workflow.steps = {
            "first": WorkflowStep(
                step_id="first", name="First",
                execute_fn=fast_step,
                compensate_fn=compensate_first,
                provides=["out"],
                compensation_policy=CompensationPolicy(compensation_timeout_ms=2000),
            ),
            "slow": WorkflowStep(
                step_id="slow", name="Slow",
                execute_fn=slow_step,
                provides=["out2"], requires=["out"],
                depends_on=["first"],
                compensation_policy=CompensationPolicy(compensation_timeout_ms=500),
            ),
        }
        engine.register_workflow(workflow)

        start = time.time()
        with pytest.raises(StepTimeoutError):
            engine.execute("timeout-wf")
        elapsed = time.time() - start

        # Must not wait the full 5s — timeout should fire at ~500ms
        assert elapsed < 4.0
        # First step succeeded and was compensated
        assert "first" in completed_steps
        # Slow step is FAILED with timeout reason
        assert workflow.steps["slow"].status == WorkflowStepStatus.FAILED
        assert "timeout" in (workflow.steps["slow"].error or "")