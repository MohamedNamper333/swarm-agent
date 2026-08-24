#!/usr/bin/env python3
"""CI test script - verifies core components work."""

import asyncio
import sys

sys.path.insert(0, '.')


async def test_sandbox():
    """Test sandbox execution."""
    from swarm.enterprise.core.execution import create_sandbox, Language, ExecutionRequest, ExecutionStatus
    
    sandbox = create_sandbox('local', enable_cgroups=False)
    result = await sandbox.execute(ExecutionRequest(
        code='print("Hello World")',
        language=Language.PYTHON,
        tenant_id='ci-test',
        actor_id='ci-user'
    ))
    assert result.status == ExecutionStatus.COMPLETED, f"Expected COMPLETED, got {result.status}"
    print("✅ Sandbox execution PASSED")


def test_rbac():
    """Test RBAC engine."""
    from swarm.enterprise.core.auth.rbac import create_rbac_engine
    rbac = create_rbac_engine()
    print("✅ RBAC engine PASSED")


def test_oauth2():
    """Test OAuth2 server."""
    from swarm.enterprise.core.auth.oauth2 import create_oauth2_server, JWTManager, MemoryTokenStore
    oauth2 = create_oauth2_server(JWTManager.create_for_testing(), MemoryTokenStore())
    print("✅ OAuth2 server PASSED")


def test_security():
    """Test security modules."""
    from swarm.enterprise.core.security import (
        create_dpop_manager, create_mtls_manager, 
        create_key_rotation_manager, create_audit_log
    )
    
    # DPoP
    dpop = create_dpop_manager()
    proof = dpop.create_proof('https://api.test.com', 'POST')
    assert proof.payload.get('htm') == 'POST'
    print("✅ DPoP PASSED")
    
    # mTLS
    mtls = create_mtls_manager()
    cert = mtls.issue_certificate('test-svc.local')
    assert cert.subject
    print("✅ mTLS PASSED")
    
    # Key Rotation
    rot = create_key_rotation_manager()
    print("✅ Key Rotation PASSED")


async def test_audit_log():
    """Test audit log."""
    from swarm.enterprise.core.security import create_audit_log
    
    audit = create_audit_log('ci-verification')
    event = await audit.append(
        event_type='system_test',
        actor='ci',
        action='verify',
        resource='system',
        resource_id='swarm-ci'
    )
    is_valid, errors = audit.verify_chain()
    assert is_valid, f"Audit chain invalid: {errors}"
    print("✅ Audit Log PASSED")


async def main():
    print("=" * 50)
    print("CI VERIFICATION TEST")
    print("=" * 50)
    
    await test_sandbox()
    test_rbac()
    test_oauth2()
    test_security()
    await test_audit_log()
    
    print("=" * 50)
    print("ALL TESTS PASSED ✅")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
