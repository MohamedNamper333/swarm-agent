import asyncio
"""
Artifact Signing - cosign/sigstore integration for artifact signing and verification.
Provides keyless signing, SBOM generation, and vulnerability scanning.
"""

import base64
import hashlib
import json
import logging
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, BinaryIO
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Signing Models
# =============================================================================

class SigningAlgorithm(str, Enum):
    ECDSA_P256 = "ECDSA-P256"
    RSA_PSS_2048 = "RSA-PSS-2048"
    ED25519 = "ED25519"


class SignatureFormat(str, Enum):
    COSIGN = "cosign"
    SIGSTORE = "sigstore"
    INTERNAL = "internal"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    FAILED = "failed"
    UNVERIFIED = "unverified"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class SigningKey:
    key_id: str = field(default_factory=lambda: f"key-{uuidv7()}")
    algorithm: SigningAlgorithm = SigningAlgorithm.ECDSA_P256
    private_key: Optional[bytes] = None
    public_key: Optional[bytes] = None
    key_type: str = "cosign"
    status: str = "active"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Signature:
    signature_id: str = field(default_factory=lambda: f"sig-{uuidv7()}")
    artifact_id: str = ""
    key_id: str = ""
    algorithm: SigningAlgorithm = SigningAlgorithm.ECDSA_P256
    signature: bytes = b""
    signed_data_hash: str = ""
    signed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    format: SignatureFormat = SignatureFormat.COSIGN
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    status: VerificationStatus
    signature_id: str
    artifact_id: str
    key_id: str
    verified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: str = ""
    certificate: Optional[Dict[str, Any]] = None
    chain: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SBOM:
    sbom_id: str = field(default_factory=lambda: f"sbom-{uuidv7()}")
    artifact_id: str = ""
    format: str = "spdx"  # spdx, cyclonedx
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    format_version: str = "2.3"


# =============================================================================
# Cosign/Sigstore Integration
# =============================================================================

class CosignSigner:
    """Cosign-based artifact signer with keyless and key-based signing."""

    def __init__(
        self,
        cosign_path: str = "cosign",
        fulcio_url: str = "https://fulcio.sigstore.dev",
        rekor_url: str = "https://rekor.sigstore.dev",
        oidc_issuer: str = "https://oauth2.sigstore.dev/auth",
    ):
        self.cosign_path = cosign_path
        self.fulcio_url = fulcio_url
        self.rekor_url = rekor_url
        self.oidc_issuer = oidc_issuer
        self._verify_cosign()

    def _verify_cosign(self) -> None:
        """Verify cosign is installed and working (lazy)."""
        if hasattr(self, '_cosign_verified'):
            return
        try:
            result = subprocess.run(
                [self.cosign_path, "version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(f"cosign not available: {result.stderr}")
            logger.info(f"Cosign version: {result.stdout.strip()}")
            self._cosign_verified = True
        except FileNotFoundError:
            logger.warning(f"cosign not found at {self.cosign_path}. Install: https://docs.sigstore.dev/cosign/installation/")
            # Don't raise - allow lazy verification
        except Exception as e:
            logger.warning(f"Cosign verification failed: {e}")

    def _ensure_cosign(self):
        """Ensure cosign is available before use."""
        if not hasattr(self, '_cosign_verified'):
            self._verify_cosign()
        if not getattr(self, '_cosign_verified', False):
            raise RuntimeError("cosign not available. Install: https://docs.sigstore.dev/cosign/installation/")

    def _ensure_cosign(self):
        if not hasattr(self, "_cosign_verified"):
            self._verify_cosign()
        if not getattr(self, "_cosign_verified", False):
            raise RuntimeError("cosign not available. Install: https://docs.sigstore.dev/cosign/installation/")

    def sign_artifact(
        self,
        artifact_path: str,
        key_path: Optional[str] = None,
        keyless: bool = True,
        annotations: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Sign an artifact using cosign."""
        cmd = [
            self.cosign_path,
            "sign",
            "--yes",
        ]

        if keyless:
            cmd.extend(["--keyless"])
        elif key_path:
            cmd.extend(["--key", key_path])
        else:
            raise ValueError("Either keyless=True or key_path must be provided")

        if annotations:
            for k, v in annotations.items():
                cmd.extend(["--annotation", f"{k}={v}"])

        cmd.append(artifact_path)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ, "COSIGN_EXPERIMENTAL": "1"},
            )
            if result.returncode != 0:
                raise RuntimeError(f"Cosign sign failed: {result.stderr}")

            # Parse output for signature info
            return {
                "success": True,
                "artifact_path": artifact_path,
                "output": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            raise RuntimeError("Cosign sign timed out")
        except Exception as e:
            raise RuntimeError(f"Cosign sign failed: {e}")

    def _ensure_cosign(self):
        if not hasattr(self, "_cosign_verified"):
            self._verify_cosign()
        if not getattr(self, "_cosign_verified", False):
            raise RuntimeError("cosign not available. Install: https://docs.sigstore.dev/cosign/installation/")

    def verify_signature(
        self,
        artifact_path: str,
        signature_path: Optional[str] = None,
        keyless: bool = True,
        public_key_path: Optional[str] = None,
        certificate_path: Optional[str] = None,
        certificate_identity: Optional[str] = None,
        certificate_oidc_issuer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verify an artifact signature using cosign."""
        cmd = [
            self.cosign_path,
            "verify",
            artifact_path,
        ]

        if keyless:
            cmd.append("--keyless")
        elif public_key_path:
            cmd.extend(["--key", public_key_path])

        if certificate_path:
            cmd.extend(["--certificate", certificate_path])

        if certificate_identity:
            cmd.extend(["--certificate-identity", certificate_identity])

        if certificate_oidc_issuer:
            cmd.extend(["--certificate-oidc-issuer", certificate_oidc_issuer])

        if signature_path:
            cmd.extend(["--signature", signature_path])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            return {
                "verified": result.returncode == 0,
                "output": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            raise RuntimeError("Cosign verify timed out")
        except Exception as e:
            raise RuntimeError(f"Cosign verify failed: {e}")

    def generate_sbom(
        self,
        artifact_path: str,
        output_path: str,
        format: str = "spdx",
    ) -> Dict[str, Any]:
        """Generate SBOM for an artifact using syft (via cosign)."""
        cmd = [
            self.cosign_path,
            "sbom",
            artifact_path,
            "--format", format,
            "--output", output_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(f"SBOM generation failed: {result.stderr}")

            return {
                "success": True,
                "output_path": output_path,
                "format": format,
                "output": result.stdout,
            }

        except subprocess.TimeoutExpired:
            raise RuntimeError("SBOM generation timed out")
        except Exception as e:
            raise RuntimeError(f"SBOM generation failed: {e}")

    def sign_blob(
        self,
        blob_path: str,
        output_path: str,
        key_path: Optional[str] = None,
        keyless: bool = True,
    ) -> Dict[str, Any]:
        """Sign a blob file."""
        cmd = [
            self.cosign_path,
            "sign-blob",
            "--yes",
            "--output", output_path,
        ]

        if keyless:
            cmd.append("--keyless")
        elif key_path:
            cmd.extend(["--key", key_path])

        cmd.append(blob_path)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Blob sign failed: {result.stderr}")

            return {
                "success": True,
                "output_path": output_path,
                "output": result.stdout,
            }

        except Exception as e:
            raise RuntimeError(f"Blob sign failed: {e}")

    def verify_blob(
        self,
        blob_path: str,
        signature_path: str,
        public_key_path: Optional[str] = None,
        keyless: bool = True,
    ) -> Dict[str, Any]:
        """Verify a blob signature."""
        cmd = [
            self.cosign_path,
            "verify-blob",
            blob_path,
            "--signature", signature_path,
        ]

        if keyless:
            cmd.append("--keyless")
        elif public_key_path:
            cmd.extend(["--key", public_key_path])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            return {
                "verified": result.returncode == 0,
                "output": result.stdout,
                "stderr": result.stderr,
            }

        except Exception as e:
            raise RuntimeError(f"Blob verify failed: {e}")


# =============================================================================
# Sigstore Keyless Signer (Fulcio + Rekor)
# =============================================================================

class SigstoreSigner:
    """Sigstore keyless signing using Fulcio (certificates) and Rekor (transparency log)."""

    def __init__(
        self,
        fulcio_url: str = "https://fulcio.sigstore.dev",
        rekor_url: str = "https://rekor.sigstore.dev",
        oidc_issuer: str = "https://oauth2.sigstore.dev/auth",
        cosign_path: str = "cosign",
    ):
        self.fulcio_url = fulcio_url
        self.rekor_url = rekor_url
        self.oidc_issuer = oidc_issuer
        self.cosign_path = cosign_path

    def sign_keyless(
        self,
        artifact_path: str,
        identity_token: Optional[str] = None,
        annotations: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Sign using keyless Sigstore (OIDC identity)."""
        # This would use sigstore-python library in production
        # Simplified implementation using cosign
        cosign = CosignSigner(cosign_path=self.cosign_path)
        return cosign.sign_artifact(
            artifact_path=artifact_path,
            keyless=True,
            annotations=annotations,
        )

    def verify_keyless(
        self,
        artifact_path: str,
        certificate_identity: str,
        certificate_oidc_issuer: str = "https://oauth2.sigstore.dev/auth",
    ) -> Dict[str, Any]:
        """Verify keyless signature."""
        cosign = CosignSigner()
        return cosign.verify_signature(
            artifact_path=artifact_path,
            keyless=True,
            certificate_identity=certificate_identity,
            certificate_oidc_issuer=certificate_oidc_issuer,
        )


# =============================================================================
# SBOM Generator
# =============================================================================

class SBOMGenerator:
    """Generate Software Bill of Materials (SBOM) in SPDX or CycloneDX format."""

    def __init__(
        self,
        syft_path: str = "syft",
        format: str = "spdx",
    ):
        self.syft_path = syft_path
        self.default_format = format
        self._verify_syft()

    def _verify_syft(self) -> None:
        if hasattr(self, '_syft_verified'):
            return
        try:
            result = subprocess.run(
                [self.syft_path, "version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(f"syft not available: {result.stderr}")
            logger.info(f"Syft version: {result.stdout.strip()}")
            self._syft_verified = True
        except FileNotFoundError:
            logger.warning(f"syft not found at {self.syft_path}. Install: https://github.com/anchore/syft")
        except Exception as e:
            logger.warning(f"Syft verification failed: {e}")

    def _ensure_syft(self):
        if not hasattr(self, '_syft_verified'):
            self._verify_syft()
        if not getattr(self, '_syft_verified', False):
            raise RuntimeError("syft not available. Install: https://github.com/anchore/syft")

    def generate_sbom(
        self,
        artifact_path: str,
        output_path: str,
        format: Optional[str] = None,
        sbom_id: Optional[str] = None,
    ) -> SBOM:
        self._ensure_syft()
        """Generate SBOM for an artifact."""
        fmt = format or self.default_format
        sbom_id = sbom_id or f"sbom-{uuidv7()}"

        cmd = [
            self.syft_path,
            "scan",
            artifact_path,
            "-o", f"{format}={output_path}",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode != 0:
                raise RuntimeError(f"SBOM generation failed: {result.stderr}")

            # Parse generated SBOM to extract metadata
            with open(output_path, 'r') as f:
                sbom_data = json.load(f)

            return SBOM(
                sbom_id=sbom_id,
                artifact_id="",  # To be filled by caller
                format=fmt,
                data=sbom_data,
                created_by="syft",
            )

        except subprocess.TimeoutExpired:
            raise RuntimeError("SBOM generation timed out")
        except Exception as e:
            raise RuntimeError(f"SBOM generation failed: {e}")

    def generate_sbom_for_directory(
        self,
        directory_path: str,
        output_path: str,
        format: Optional[str] = None,
    ) -> SBOM:
        """Generate SBOM for a directory (source code)."""
        return self.generate_sbom(directory_path, output_path, format)


# =============================================================================
# Vulnerability Scanner
# =============================================================================

class VulnerabilityScanner:
    """Scan artifacts for vulnerabilities using Grype/Trivy."""

    def __init__(
        self,
        grype_path: str = "grype",
        trivy_path: str = "trivy",
    ):
        self.grype_path = grype_path
        self.trivy_path = trivy_path
        self._verify_tools()

    def _verify_tools(self) -> None:
        for tool, path in [("grype", self.grype_path), ("trivy", self.trivy_path)]:
            try:
                result = subprocess.run(
                    [path, "version"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode != 0:
                    logger.warning(f"{tool} not available: {result.stderr}")
                else:
                    logger.info(f"{tool} version: {result.stdout.strip()}")
            except FileNotFoundError:
                logger.warning(f"{tool} not found at {path}")

    def _ensure_tools(self):
        if not hasattr(self, '_tools_verified'):
            self._verify_tools()

    def scan_with_grype(
        self,
        artifact_path: str,
        output_path: Optional[str] = None,
        format: str = "json",
        fail_on_severity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Scan artifact for vulnerabilities using Grype."""
        self._ensure_tools()
        cmd = [
            self.grype_path,
            artifact_path,
            "-o", format,
        ]

        if output_path:
            cmd.extend(["-o", f"{format}={output_path}"])

        if fail_on_severity:
            cmd.extend(["--fail-on", fail_on_severity])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if output_path:
                with open(output_path, 'r') as f:
                    return json.load(f)

            return json.loads(result.stdout) if result.returncode == 0 else {}

        except Exception as e:
            raise RuntimeError(f"Grype scan failed: {e}")

    def scan_with_trivy(
        self,
        artifact_path: str,
        output_path: Optional[str] = None,
        format: str = "json",
        severity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Scan artifact for vulnerabilities using Trivy."""
        self._ensure_tools()
        cmd = [
            self.trivy_path,
            "fs",
            "--format", format,
        ]

        if output_path:
            cmd.extend(["-o", output_path])

        if severity:
            cmd.extend(["--severity", severity])

        cmd.append(artifact_path)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if output_path:
                with open(output_path, 'r') as f:
                    return json.load(f)

            return json.loads(result.stdout) if result.returncode == 0 else {}

        except Exception as e:
            raise RuntimeError(f"Trivy scan failed: {e}")


# =============================================================================
# Artifact Signing Service (High-level API)
# =============================================================================

class ArtifactSigningService:
    """High-level artifact signing service combining all signing capabilities."""

    def __init__(
        self,
        cosign_path: str = "cosign",
        syft_path: str = "syft",
        grype_path: str = "grype",
        trivy_path: str = "trivy",
    ):
        self.cosign = CosignSigner(cosign_path=cosign_path)
        self.sbom_generator = SBOMGenerator(syft_path=syft_path)
        self.vuln_scanner = VulnerabilityScanner(grype_path=grype_path)
        self._signatures: Dict[str, Signature] = {}
        self._lock = asyncio.Lock()

    async def _ensure_cosign(self):
        if not hasattr(self, "_cosign_verified"):
            self._verify_cosign()
        if not getattr(self, "_cosign_verified", False):
            raise RuntimeError("cosign not available. Install: https://docs.sigstore.dev/cosign/installation/")

    def sign_artifact(
        self,
        artifact_path: str,
        keyless: bool = True,
        key_path: Optional[str] = None,
        annotations: Optional[Dict[str, str]] = None,
        generate_sbom: bool = True,
        scan_vulnerabilities: bool = True,
    ) -> Dict[str, Any]:
        """Complete artifact signing pipeline."""
        results = {
            "artifact_path": artifact_path,
            "signed": False,
            "sbom_generated": False,
            "vulnerabilities_scanned": False,
            "errors": [],
        }

        try:
            # 1. Sign artifact
            sign_result = self.cosign.sign_artifact(
                artifact_path=artifact_path,
                keyless=keyless,
                key_path=None if keyless else key_path,
            )
            results["signed"] = sign_result.get("success", False)
            results["signature_info"] = sign_result

            # 2. Generate SBOM
            if generate_sbom:
                sbom_path = f"{artifact_path}.sbom.json"
                sbom_result = self.sbom_generator.generate_sbom(
                    artifact_path=artifact_path,
                    output_path=sbom_path,
                )
                results["sbom_generated"] = True
                results["sbom_path"] = sbom_path

            # 3. Scan vulnerabilities
            if scan_vulnerabilities:
                vuln_path = f"{artifact_path}.vuln.json"
                vuln_result = self.vuln_scanner.scan_with_grype(
                    artifact_path=artifact_path,
                    output_path=vuln_path,
                )
                results["vulnerabilities_scanned"] = True
                results["vulnerability_report"] = vuln_result

        except Exception as e:
            results["errors"].append(str(e))
            logger.error(f"Artifact signing pipeline failed: {e}")

        return results

    async def verify_artifact(
        self,
        artifact_path: str,
        keyless: bool = True,
        certificate_identity: Optional[str] = None,
        certificate_oidc_issuer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verify artifact signature."""
        return self.cosign.verify_signature(
            artifact_path=artifact_path,
            keyless=keyless,
            certificate_identity=certificate_identity,
        )

    async def sign_and_attest(
        self,
        artifact_path: str,
        attestation_type: str = "sbom",
        keyless: bool = True,
    ) -> Dict[str, Any]:
        """Sign artifact and create in-toto attestation."""
        # Simplified - in production would use in-toto
        sign_result = await self.sign_artifact(
            artifact_path=artifact_path,
            keyless=keyless,
        )

        if attestation_type == "sbom":
            sbom_path = f"{artifact_path}.sbom.json"
            sbom_result = self.sbom_generator.generate_sbom(
                artifact_path=artifact_path,
                output_path=sbom_path,
            )
            sign_result["sbom"] = sbom_result

        return sign_result


# =============================================================================
# Factory
# =============================================================================

def create_cosign_signer(
    cosign_path: str = "cosign",
    fulcio_url: str = "https://fulcio.sigstore.dev",
    rekor_url: str = "https://rekor.sigstore.dev",
) -> CosignSigner:
    return CosignSigner(cosign_path, fulcio_url, rekor_url)


def create_sbom_generator(
    syft_path: str = "syft",
    format: str = "spdx",
) -> SBOMGenerator:
    return SBOMGenerator(syft_path, format)


def create_vulnerability_scanner(
    grype_path: str = "grype",
    trivy_path: str = "trivy",
) -> VulnerabilityScanner:
    return VulnerabilityScanner(grype_path, trivy_path)


def create_artifact_signing_service(
    cosign_path: str = "cosign",
    syft_path: str = "syft",
    grype_path: str = "grype",
) -> ArtifactSigningService:
    return ArtifactSigningService(cosign_path, syft_path, grype_path)
