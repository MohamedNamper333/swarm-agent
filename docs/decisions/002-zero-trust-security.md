# ADR-002: Zero-Trust Security (DPoP + mTLS + HSM)

## Status
**Accepted** — 2025-08-24

## Context
The platform handles multi-tenant code execution with sensitive data. Traditional perimeter-based security is insufficient because:
- Tokens can be stolen and replayed
- Service-to-service communication needs mutual authentication
- Key material must never leave hardware security modules
- Certificates issued for our domains must be monitored

## Decision
Implement defense-in-depth with 5 security layers:

1. **Transport**: mTLS (RFC 8705) with certificate-based service identity
2. **Token Binding**: DPoP (RFC 9449) - proof-of-possession for all tokens
3. **Key Management**: HSM integration (PKCS#11) - keys never leave hardware
4. **Audit**: Immutable SHA-256 chained audit log
5. **CT Monitoring**: Certificate Transparency monitoring via crt.sh

### Implementation Files
- `core/security/dpop.py` — DPoP Manager (proof creation + verification)
- `core/security/mtls.py` — mTLS Manager (certificate issuance + token binding)
- `core/security/hsm.py` — HSM Manager (key generation, signing, verification)
- `core/security/audit_log.py` — Immutable Audit Log (SHA-256 chaining)
- `core/security/ct_monitor.py` — CT Monitor (crt.sh integration)

## Consequences

### Positive
- Stolen tokens are useless without the private key (DPoP)
- Service identity is cryptographically verified (mTLS)
- Key material never exposed in memory dumps (HSM)
- Tampering detected immediately (audit chaining)
- Unauthorized certificates detected within 6 hours (CT monitoring)

### Negative
- Higher latency due to cryptographic operations (~5ms per request)
- HSM dependency adds operational complexity
- DPoP requires client-side key management
- CT monitoring requires network access to crt.sh

### Neutral
- MockHSM available for development; production MUST use real HSM
- Audit log anchoring supports RFC 3161 timestamping for external verification
