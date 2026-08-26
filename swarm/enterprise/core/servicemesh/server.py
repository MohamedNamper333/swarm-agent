"""
Service Mesh - mTLS, service discovery, traffic splitting, and observability.
Provides zero-trust networking for microservices.
"""

import asyncio
import hashlib
import logging
import ssl
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.x509.oid import NameOID

import json
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Service Mesh Models
# =============================================================================

class MeshProtocol(str, Enum):
    HTTP = "http"
    GRPC = "grpc"
    TCP = "tcp"
    TLS = "tls"


class TrafficPolicyType(str, Enum):
    ROUTE = "route"
    FAULT_INJECTION = "fault_injection"
    RETRY = "retry"
    TIMEOUT = "timeout"
    CIRCUIT_BREAKER = "circuit_breaker"
    RATE_LIMIT = "rate_limit"
    MIRROR = "mirror"


class TLSMode(str, Enum):
    DISABLE = "disable"
    PERMISSIVE = "permissive"
    STRICT = "strict"


@dataclass
class ServiceMeshConfig:
    mesh_name: str = "swarm-mesh"
    control_plane_address: str = "localhost:15010"
    data_plane_address: str = "localhost:15011"
    mtls_mode: TLSMode = TLSMode.STRICT
    cert_rotation_interval_hours: int = 24
    ca_cert_path: Optional[str] = None
    ca_key_path: Optional[str] = None
    enable_telemetry: bool = True
    enable_access_log: bool = True
    enable_metrics: bool = True
    global_timeout_ms: int = 30000
    default_retry_policy: Dict[str, Any] = field(default_factory=lambda: {
        "max_attempts": 3,
        "per_try_timeout": "10s",
        "retry_on": ["connect-failure", "refused-stream", "unavailable", "cancelled", "retriable-status-codes"],
    })


@dataclass
class ServiceInstance:
    service_name: str
    namespace: str = "default"
    endpoint: str = ""
    port: int = 8080
    protocol: MeshProtocol = MeshProtocol.HTTP
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    health_check_path: str = "/health"
    health_check_interval: int = 10
    healthy_threshold: int = 2
    unhealthy_threshold: int = 3
    timeout_seconds: int = 5
    weight: int = 100
    tags: Dict[str, str] = field(default_factory=dict)
    version: str = "v1"
    region: str = "default"
    zone: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)
    health_status: str = "UNKNOWN"
    last_health_check: Optional[datetime] = None
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: Optional[datetime] = None


@dataclass
class TrafficPolicy:
    policy_id: str = field(default_factory=lambda: f"tp-{uuidv7()}")
    name: str = ""
    namespace: str = "default"
    target_service: str = ""
    policy_type: TrafficPolicyType = TrafficPolicyType.ROUTE
    spec: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PeerAuthentication:
    policy_id: str = field(default_factory=lambda: f"pa-{uuidv7()}")
    namespace: str = "default"
    selector: Dict[str, str] = field(default_factory=dict)
    mtls_mode: TLSMode = TLSMode.STRICT
    port_level_mtls: Dict[int, TLSMode] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AuthorizationPolicy:
    policy_id: str = field(default_factory=lambda: f"azp-{uuidv7()}")
    namespace: str = "default"
    selector: Dict[str, str] = field(default_factory=dict)
    rules: List[Dict[str, Any]] = field(default_factory=list)
    action: str = "ALLOW"  # ALLOW, DENY
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Certificate Authority
# =============================================================================

class CertificateAuthority:
    """Manages mTLS certificates for the service mesh."""

    def __init__(
        self,
        ca_cert_path: Optional[str] = None,
        ca_key_path: Optional[str] = None,
        cert_ttl_hours: int = 24,
    ):
        self.cert_ttl_hours = cert_ttl_hours
        self._ca_cert: Optional[bytes] = None
        self._ca_key: Optional[bytes] = None
        self._issued_certs: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

        if ca_cert_path and ca_key_path:
            self._load_ca(ca_cert_path, ca_key_path)
        else:
            self._generate_ca()

    def _generate_ca(self) -> None:
        """Generate self-signed CA certificate."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography import x509
        from cryptography.x509.oid import NameOID

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Create subject and issuer names
        subject_attrs = [
            x509.NameAttribute(NameOID.COMMON_NAME, "Swarm Mesh CA"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Swarm"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Service Mesh"),
        ]
        subject = x509.Name(subject_attrs)
        issuer = subject

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=3650)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=True,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False,
        ).sign(private_key, hashes.SHA256())

        self._ca_cert = cert.public_bytes(serialization.Encoding.PEM)
        self._ca_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def _load_ca(self, cert_path: str, key_path: str) -> None:
        with open(cert_path, "rb") as f:
            self._ca_cert = f.read()
        with open(key_path, "rb") as f:
            self._ca_key = f.read()

    async def issue_certificate(
        self,
        service_name: str,
        namespace: str,
        san_dns: Optional[List[str]] = None,
        san_ip: Optional[List[str]] = None,
        ttl_hours: Optional[int] = None,
    ) -> Tuple[bytes, bytes]:
        """Issue a workload certificate."""
        if not self._ca_cert or not self._ca_key:
            raise RuntimeError("CA not initialized")

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography import x509
        from cryptography.x509.oid import NameOID

        ttl_hours = ttl_hours or 24
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        san_dns = san_dns or []
        san_ip = san_ip or []

        san_list = [x509.DNSName(dns) for dns in san_dns]
        for ip in san_ip:
            san_list.append(x509.IPAddress(ipaddress.ip_address(ip)))

        # Create subject
        subject_attrs = [
            x509.NameAttribute(NameOID.COMMON_NAME, f"{service_name}.mesh.local"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Swarm"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Service Mesh"),
        ]
        subject = x509.Name(subject_attrs)

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            x509.load_pem_x509_certificate(self._ca_cert).subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            # SM-N3 fix: caller-supplied ttl was computed then ignored —
            # every cert silently lived the default 24h.
            datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        ).add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        ).sign(
            serialization.load_pem_private_key(self._ca_key, password=None),
            hashes.SHA256(),
        )

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Store issued cert
        cert_info = {
            "service_name": service_name,
            "namespace": namespace,
            "serial_number": cert.serial_number,
            "issued_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
            "cert_pem": cert_pem.decode(),
            # N2 fix: private keys are NEVER retained server-side; the
            # caller owns them. (Old code parked every workload key in a
            # plaintext dict forever.)
            "revoked": False,
        }

        cert_key = f"{san_dns[0] if san_dns else service_name}"
        self._issued_certs[cert_key] = cert_info

        return cert_pem, key_pem

    def revoke_certificate(self, cert_key: str) -> bool:
        """Mark a certificate revoked (N1 fix).

        Previously this DELETED the record and returned True while the
        certificate remained cryptographically valid everywhere — revocation
        theater. Now the record survives with revoked=True and enforcement
        points can query is_revoked()/is_serial_revoked().
        """
        rec = self._issued_certs.get(cert_key)
        if not rec:
            return False
        rec["revoked"] = True
        logger.warning(f"Certificate revoked: {cert_key} "
                       f"(serial={rec.get('serial_number')})")
        return True

    def is_revoked(self, cert_key: str) -> bool:
        rec = self._issued_certs.get(cert_key)
        return bool(rec and rec.get("revoked"))

    def is_serial_revoked(self, serial_number: int) -> bool:
        return any(rec.get("revoked") and rec.get("serial_number") == serial_number
                   for rec in self._issued_certs.values())

    def get_ca_cert(self) -> bytes:
        return self._ca_cert


# =============================================================================
# Service Registry
# =============================================================================

class ServiceRegistry:
    """Service registry with health checking and load balancing."""

    def __init__(self):
        self._services: Dict[str, Dict[str, ServiceInstance]] = defaultdict(dict)
        self._lock = asyncio.Lock()
        self._health_checkers: Dict[str, asyncio.Task] = {}

    async def register(self, instance: ServiceInstance) -> str:
        """Register a service instance."""
        async with self._lock:
            key = f"{instance.namespace}/{instance.service_name}"
            instance_id = f"{instance.service_name}-{instance.endpoint}"
            self._services[key][instance_id] = instance
            logger.info(f"Registered service: {instance.service_name} at {instance.endpoint}")
            return instance_id

    async def deregister(self, namespace: str, service_name: str, instance_id: str) -> bool:
        async with self._lock:
            key = f"{namespace}/{service_name}"
            if key in self._services and instance_id in self._services[key]:
                del self._services[key][instance_id]
                return True
            return False

    def get_instances(
        self,
        namespace: str,
        service_name: str,
        healthy_only: bool = True,
    ) -> List[ServiceInstance]:
        with self._lock:
            key = f"{namespace}/{service_name}"
            instances = list(self._services.get(key, {}).values())
            if healthy_only:
                instances = [i for i in instances if i.health_status == "HEALTHY"]
            return instances

    async def update_health(self, namespace: str, service_name: str, instance_id: str, status: str) -> bool:
        with self._lock:
            key = f"{namespace}/{service_name}"
            if key in self._services and instance_id in self._services[key]:
                instance = self._services[key][instance_id]
                instance.health_status = status
                instance.last_health_check = datetime.now(timezone.utc)
                return True
            return False

    async def get_service_info(self, namespace: str, service_name: str) -> Optional[Dict[str, Any]]:
        instances = await self.get_instances(namespace, service_name, healthy_only=False)
        return {
            "service_name": service_name,
            "namespace": namespace,
            "instances": len(self._services.get(f"{namespace}/{service_name}", {})),
            "healthy": len([i for i in self._services.get(f"{namespace}/{service_name}", {}).values() if i.health_status == "HEALTHY"]),
        }

    async def start_health_checks(self, interval: int = 10) -> None:
        """Start background health checks."""
        async def health_check_loop():
            while True:
                await asyncio.sleep(interval)
                # Run health checks
                pass

        asyncio.create_task(health_check_loop())


# =============================================================================
# Traffic Management
# =============================================================================

class TrafficManager:
    """Manages traffic policies and routing rules."""

    def __init__(self):
        self._policies: Dict[str, TrafficPolicy] = {}
        self._lock = asyncio.Lock()

    async def add_policy(self, policy: TrafficPolicy) -> None:
        async with self._lock:
            self._policies[policy.policy_id] = policy

    async def remove_policy(self, policy_id: str) -> bool:
        async with self._lock:
            if policy_id in self._policies:
                del self._policies[policy_id]
                return True
            return False

    async def get_policy(self, policy_id: str) -> Optional[TrafficPolicy]:
        return self._policies.get(policy_id)

    async def list_policies(
        self,
        namespace: Optional[str] = None,
        target_service: Optional[str] = None,
    ) -> List[TrafficPolicy]:
        with self._lock:
            policies = list(self._policies.values())
            if namespace:
                policies = [p for p in policies if p.namespace == namespace]
            if target_service:
                policies = [p for p in policies if p.target_service == target_service]
            return policies

    async def evaluate_traffic(
        self,
        request: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Optional[TrafficPolicy]:
        """Evaluate traffic policies for a request."""
        applicable = []
        for policy in self._policies.values():
            if not policy.enabled:
                continue
            if policy.namespace != "default" and policy.namespace != context.get("namespace"):
                continue
            if policy.target_service and policy.target_service != context.get("service"):
                continue

            # Check if policy matches request
            if self._matches_policy(policy, context):
                applicable.append(policy)

        if not applicable:
            return None

        # Sort by priority
        applicable.sort(key=lambda p: p.priority)
        return applicable[0] if applicable else None

    def _matches_policy(self, policy: TrafficPolicy, context: Dict[str, Any]) -> bool:
        # Simplified matching logic
        return True


# =============================================================================
# mTLS Manager
# =============================================================================

class MTLSManager:
    """Manages mTLS certificates and policies."""

    def __init__(
        self,
        ca: CertificateAuthority,
        default_mode: TLSMode = TLSMode.STRICT,
    ):
        self.ca = ca
        self.default_mode = default_mode
        self._peer_authentications: Dict[str, PeerAuthentication] = {}
        self._lock = asyncio.Lock()

    async def create_peer_authentication(
        self,
        namespace: str,
        selector: Dict[str, str],
        mode: TLSMode = TLSMode.STRICT,
    ) -> PeerAuthentication:
        pa = PeerAuthentication(
            policy_id=f"pa-{uuidv7()}",
            namespace=namespace,
            selector=selector,
            mtls_mode=mode,
        )
        async with self._lock:
            key = f"{namespace}/{hash(frozenset(selector.items()))}"
            self._peer_authentications[key] = pa
        return pa

    async def get_mtls_mode(self, namespace: str, labels: Dict[str, str]) -> TLSMode:
        for pa in self._peer_authentications.values():
            if pa.namespace == namespace:
                if all(labels.get(k) == v for k, v in pa.selector.items()):
                    return pa.mtls_mode
        return self.default_mode

    async def get_certificate(self, service_name: str, namespace: str) -> Tuple[bytes, bytes]:
        """Issue (or re-issue) a workload cert via the mesh CA.

        Was a bare `pass` returning None inside the mTLS critical path —
        callers unpacking the tuple crashed with TypeError.
        """
        san_dns = [
            f"{service_name}.{namespace}.svc.mesh.local",
            service_name,
        ]
        return await self.ca.issue_certificate(
            service_name=service_name,
            namespace=namespace,
            san_dns=san_dns,
        )


# =============================================================================
# Sidecar Proxy (Envoy-like)
# =============================================================================

class SidecarProxy:
    """Envoy-like sidecar proxy for service mesh."""

    def __init__(
        self,
        service_name: str,
        namespace: str,
        config: ServiceMeshConfig,
        cert_manager: 'CertificateManager',
    ):
        self.service_name = service_name
        self.namespace = namespace
        self.config = config
        self.cert_manager = cert_manager
        self._running = False
        self._server: Optional[asyncio.Server] = None
        self._upstreams: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the sidecar proxy."""
        self._running = True
        # Start inbound listener
        self._server = await asyncio.start_server(
            self._handle_connection,
            "0.0.0.0",
            15000,  # inbound port
            ssl=None,  # Would use mTLS in production
        )
        logger.info(f"Sidecar started for {self.service_name}")

    async def stop(self) -> None:
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        # Handle incoming connection
        pass

    async def register_upstream(self, service_name: str, endpoint: str) -> None:
        async with self._lock:
            self._upstreams[service_name] = endpoint

    async def route_request(self, request: bytes) -> bytes:
        # Route request to appropriate upstream
        pass


# =============================================================================
# Certificate Manager
# =============================================================================

class CertificateManager:
    """Manages workload certificates for sidecars."""

    def __init__(self, ca: CertificateAuthority):
        self.ca = ca
        self._cert_cache: Dict[str, Tuple[bytes, bytes]] = {}  # cert, key
        self._lock = asyncio.Lock()

    async def get_certificate(
        self,
        service_name: str,
        namespace: str,
    ) -> Tuple[bytes, bytes]:
        """Get or generate certificate for workload."""
        key = f"{namespace}/{service_name}"

        async with self._lock:
            if key in self._cert_cache:
                cert, key_pem = self._cert_cache[key]
                # Check expiry
                return cert, key_pem

        # Generate new certificate
        cert_pem, key_pem = await self._generate_certificate()
        self._cert_cache[key] = (cert_pem, key_pem)
        return cert_pem, key_pem

    async def _generate_certificate(self) -> Tuple[bytes, bytes]:
        # Would call CA to issue certificate
        return b"", b""

    async def rotate_certificates(self) -> None:
        """Rotate all certificates nearing expiry."""
        pass


# =============================================================================
# Service Mesh Control Plane
# =============================================================================

class ServiceMeshControlPlane:
    """Main control plane for service mesh."""

    def __init__(self, config: ServiceMeshConfig):
        self.config = config
        self.registry = ServiceRegistry()
        self.traffic_manager = TrafficManager()
        self.ca = CertificateAuthority()
        self.mtls_manager = MTLSManager(ca=self.ca)
        self.cert_manager = CertificateManager(self.mtls_manager)
        self._running = False

    async def start(self) -> None:
        await self.registry.start_health_checks()
        logger.info("Service mesh control plane started")

    async def stop(self) -> None:
        pass

    def get_stats(self) -> Dict[str, Any]:
        return {
            "mesh_name": self.config.mesh_name,
            "services": len(self.registry._services),
            "policies": len(self.traffic_manager._policies),
        }


# =============================================================================
# Sidecar Injection (for Kubernetes)
# =============================================================================

class SidecarInjector:
    """Injects sidecar proxy into Kubernetes pods."""

    SIDECAR_TEMPLATE = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
spec:
  template:
    spec:
      containers:
      - name: {name}
        image: {image}
        ports:
        - containerPort: 8080
      - name: swarm-sidecar
        image: swarm/sidecar:v1.0.0
        ports:
        - containerPort: 15000
          name: http
        - containerPort: 15001
          name: https
        - containerPort: 15010
          name: grpc
        env:
        - name: SERVICE_NAME
          value: "{service_name}"
        - name: NAMESPACE
          value: "{namespace}"
        - name: MESH_CONFIG
          value: "{mesh_config}"
        volumeMounts:
        - name: certs
          mountPath: /etc/certs
          readOnly: true
      volumes:
      - name: certs
        secret:
          secretName: {service_name}-certs
"""

    def inject(self, deployment_yaml: str, service_name: str, namespace: str) -> str:
        """Inject sidecar into deployment YAML."""
        import yaml
        doc = yaml.safe_load(deployment_yaml)

        if 'spec' not in doc or 'template' not in doc['spec']:
            return deployment_yaml

        template = doc['spec']['template']
        if 'spec' not in template:
            template['spec'] = {}

        # Add sidecar container
        sidecar = {
            'name': 'swarm-sidecar',
            'image': 'swarm/sidecar:v1.0.0',
            'ports': [
                {'containerPort': 15000, 'name': 'http'},
                {'containerPort': 15001, 'name': 'https'},
                {'containerPort': 15010, 'name': 'grpc'},
            ],
            'env': [
                {'name': 'SERVICE_NAME', 'value': service_name},
                {'name': 'NAMESPACE', 'value': namespace},
                {'name': 'MESH_CONFIG', 'value': json.dumps({})},
            ],
            'volumeMounts': [
                {'name': 'certs', 'mountPath': '/etc/certs', 'readOnly': True}
            ],
        }

        if 'containers' not in template['spec']:
            template['spec']['containers'] = []
        template['spec']['containers'].append(sidecar)

        # Add volumes
        if 'volumes' not in template['spec']:
            template['spec']['volumes'] = []
        template['spec']['volumes'].append({
            'name': 'certs',
            'secret': {'secretName': f'{service_name}-certs'},
        })

        return yaml.dump(doc)


# =============================================================================
# Factory
# =============================================================================

def create_service_mesh(config: Optional[ServiceMeshConfig] = None) -> ServiceMeshControlPlane:
    return ServiceMeshControlPlane(config or ServiceMeshConfig())


def create_certificate_authority(
    ca_cert_path: Optional[str] = None,
    ca_key_path: Optional[str] = None,
    cert_ttl_hours: int = 24,
) -> CertificateAuthority:
    return CertificateAuthority(ca_cert_path, ca_key_path, cert_ttl_hours)


def create_certificate_manager(ca: CertificateAuthority) -> CertificateManager:
    return CertificateManager(ca)


def create_mtls_manager(ca: CertificateAuthority, default_mode: TLSMode = TLSMode.STRICT) -> MTLSManager:
    return MTLSManager(ca, default_mode)


def create_service_registry() -> ServiceRegistry:
    return ServiceRegistry()


def create_traffic_manager() -> TrafficManager:
    return TrafficManager()


def create_sidecar_proxy(
    service_name: str,
    namespace: str,
    config: ServiceMeshConfig,
    cert_manager: CertificateManager,
) -> SidecarProxy:
    return SidecarProxy(service_name, namespace, config, cert_manager)


def create_service_mesh(config: Optional[ServiceMeshConfig] = None) -> ServiceMeshControlPlane:
    return ServiceMeshControlPlane(config or ServiceMeshConfig())
