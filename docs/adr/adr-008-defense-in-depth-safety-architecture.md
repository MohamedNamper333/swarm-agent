# ADR-008: Defense-in-Depth Safety Architecture

**Status:** accepted
**Author:** system
**Date:** 2026-08-14
**Updated:** 2026-08-14

## Context
Single-layer regex safety is insufficient for production.

## Decision
Implement defense-in-depth: Normalization -> Deterministic Rules -> Safety Classifier -> Policy Engine -> Tool Authorization -> Output Safety. Tool permissions controlled by policy, not just safety approval.

## Consequences
- Multiple independent safety layers
- Tool authorization separate from content safety
- Fail-closed at each layer

## Alternatives Considered
- Single LLM-based safety classifier
- Regex-only with allowlist
