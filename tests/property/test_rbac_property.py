"""
Property-Based Tests for RBAC Engine.
Tests RBAC invariants with randomly generated inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, Bundle, rule, initialize

from swarm.enterprise.core.auth.rbac import (
    PolicyEngine, RoleManager, FeatureFlagStore,
    Role, PolicyRule, Policy, Subject, Resource, Action, Environment,
    EvaluationContext, create_rbac_engine, deterministic_hash,
)


# Strategies for generating test data
role_names = st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
permission_names = st.lists(
    st.text(min_size=1, max_size=30),
    min_size=0,
    max_size=20
)
subject_ids = st.text(min_size=1, max_size=50)
percentages = st.floats(min_value=0.0, max_value=100.0)


class TestRBACProperties:
    """Property-based tests for RBAC engine."""

    @given(
        subject_id=subject_ids,
        role_name=role_names,
        permissions=permission_names,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_permission_assignment_is_idempotent(self, subject_id, role_name, permissions):
        """Test that assigning the same role twice doesn't duplicate permissions."""
        manager = RoleManager()
        role = Role(role_id=role_name, name=role_name, permissions=permissions)
        
        import asyncio
        
        async def run():
            await manager.create_role(role)
            await manager.assign_role(subject_id, role.role_id)
            perms1 = await manager.get_effective_permissions(subject_id)
            await manager.assign_role(subject_id, role.role_id)  # Duplicate assignment
            perms2 = await manager.get_effective_permissions(subject_id)
            return perms1 == perms2
        
        assert asyncio.run(run())

    @given(
        flag_id=st.text(min_size=1, max_size=50),
        user_key=st.text(min_size=1, max_size=50),
        percentage=percentages,
    )
    @settings(max_examples=100)
    def test_feature_flag_deterministic(self, flag_id, user_key, percentage):
        """Test that feature flags are deterministic (same input = same output)."""
        from swarm.enterprise.core.auth.rbac import FeatureFlag, deterministic_hash
        
        # Test that hash is deterministic
        hash1 = deterministic_hash(f"{flag_id}:rollout:{user_key}")
        hash2 = deterministic_hash(f"{flag_id}:rollout:{user_key}")
        assert hash1 == hash2

    @given(
        value=st.one_of(st.integers(), st.text(), st.booleans(), st.floats(allow_nan=False)),
    )
    @settings(max_examples=100)
    def test_policy_condition_evaluation_never_crashes(self, value):
        """Test that condition evaluation never crashes regardless of input."""
        evaluator = None  # We'll use the ConditionEvaluator directly
        from swarm.enterprise.core.auth.rbac import ConditionEvaluator, EvaluationContext
        
        conditions = [
            {"attribute": "test_attr", "operator": "eq", "value": value},
            {"attribute": "test_attr", "operator": "ne", "value": value},
        ]
        
        for cond in conditions:
            try:
                result = ConditionEvaluator._compare(value, cond["operator"], value)
                assert isinstance(result, bool)
            except Exception as e:
                pytest.fail(f"Condition evaluation crashed: {e}")


class TestSecurityProperties:
    """Property-based tests for security modules."""

    @given(
        htu=st.text(min_size=1, max_size=200),
        htm=st.sampled_from(["GET", "POST", "PUT", "DELETE", "PATCH"]),
    )
    @settings(max_examples=50)
    def test_dpop_proof_verification_roundtrip(self, htu, htm):
        """Test that DPoP proofs can be created and verified."""
        from swarm.enterprise.core.security import create_dpop_manager
        
        dpop = create_dpop_manager()
        proof = dpop.create_proof(htu, htm)
        
        is_valid, error = dpop.verify_proof(proof, htu, htm)
        assert is_valid, f"DPoP proof verification failed: {error}"

    @given(
        common_name=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=20)
    def test_mtls_certificate_issuance(self, common_name):
        """Test that mTLS certificates can be issued for any name."""
        from swarm.enterprise.core.security import create_mtls_manager
        
        mtls = create_mtls_manager()
        cert = mtls.issue_certificate(common_name)
        assert cert.cert_pem
        assert cert.key_pem

    @given(
        event_type=st.text(min_size=1, max_size=50),
        actor=st.text(min_size=1, max_size=50),
        action=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_audit_log_chain_integrity(self, event_type, actor, action):
        """Test that audit log chain remains intact with random events."""
        from swarm.enterprise.core.security import create_audit_log
        
        audit = create_audit_log('property-test')
        
        import asyncio
        
        async def run():
            for i in range(5):
                await audit.append(
                    event_type=event_type,
                    actor=actor,
                    action=action,
                    resource='test',
                    resource_id=f'test-{i}',
                )
            
            is_valid, errors = audit.verify_chain()
            return is_valid
        
        assert asyncio.run(run())
