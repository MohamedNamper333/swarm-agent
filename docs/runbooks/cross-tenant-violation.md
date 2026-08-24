# Runbook: Cross-Tenant Access Violation (SECURITY)

## Alert
- **Alert Name**: CrossTenantViolation
- **Severity**: Critical (SECURITY)
- **Trigger Condition**: `swarm_cross_tenant_violations_total > 0`

## Symptoms
- Security alert in monitoring dashboard
- Audit log showing unauthorized access attempt
- Potential data breach

## Diagnosis
1. **DO NOT PANIC** — The isolation enforcer should have BLOCKED the access
2. Check audit log for details:
   ```
   Query: event_type="cross_tenant_access" 
   Look at: actor, resource, resource_id, outcome
   ```
3. Identify:
   - Which tenant attempted access?
   - What resource was targeted?
   - Was the access blocked or did it succeed?
4. Check if this is a false positive (misconfigured tenant_id)

## Resolution
1. If access was BLOCKED (expected behavior):
   - Document the incident
   - Investigate the source of the access attempt
   - Consider rate limiting or blocking the offending principal

2. If access SUCCEEDED (CRITICAL BREACH):
   ```bash
   # 1. IMMEDIATELY isolate affected resources
   kubectl scale deployment/swarm-master --replicas=0 -n swarm-production
   
   # 2. Revoke all tokens for affected tenants
   # Use OAuth2 revocation endpoint
   
   # 3. Preserve evidence
   kubectl get events -n swarm-production > incident_evidence.txt
   kubectl logs deployment/swarm-master -n swarm-production > incident_logs.txt
   
   # 4. Notify security team and compliance officer
   ```

## Escalation
- **IMMEDIATELY** notify Security Lead if access succeeded
- Notify Compliance Officer within 1 hour (regulatory requirement)
- Prepare incident report within 24 hours

## Prevention
- Regular penetration testing (quarterly)
- Tenant isolation tests in CI/CD pipeline
- Monitor `swarm_cross_tenant_violations_total` continuously
