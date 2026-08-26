"""Artifact signing package (re-exports the real service module).

2026-08-25: an empty package directory shadowed signing.py — the third
occurrence of the shadowing disease (auth/, placeholder/ before this).
"""
from swarm.enterprise.core.artifact.signing.service import (
    ArtifactSigningService,
    CosignSigner,
    SBOMGenerator,
    VulnerabilityScanner,
    create_cosign_signer,
    create_sbom_generator,
    create_vulnerability_scanner,
    create_artifact_signing_service,
)

__all__ = [
    "ArtifactSigningService",
    "CosignSigner",
    "SBOMGenerator",
    "VulnerabilityScanner",
    "create_cosign_signer",
    "create_sbom_generator",
    "create_vulnerability_scanner",
    "create_artifact_signing_service",
]
