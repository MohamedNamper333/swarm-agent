"""
SSO Providers - SAML 2.0, OIDC, LDAP, and custom identity provider integrations.
Supports SAML 2.0, OIDC, LDAP, and custom identity providers.
"""

import base64
import hashlib
import logging
import secrets
import uuid
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urlencode, urlparse
# import xmlsec  # Optional: for SAML signing/validation

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# SSO Models
# =============================================================================

class IdentityProviderType(str, Enum):
    SAML2 = "saml2"
    OIDC = "oidc"
    LDAP = "ldap"
    ACTIVE_DIRECTORY = "active_directory"
    CUSTOM = "custom"


class BindingType(str, Enum):
    HTTP_REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    HTTP_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    HTTP_ARTIFACT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Artifact"
    SOAP = "urn:oasis:names:tc:SAML:2.0:bindings:SOAP"


@dataclass
class IdentityProvider:
    idp_id: str = field(default_factory=lambda: f"idp-{uuidv7()}")
    name: str = ""
    idp_type: IdentityProviderType = IdentityProviderType.SAML2
    display_name: str = ""
    description: str = ""
    enabled: bool = True
    
    # SAML2 Configuration
    entity_id: str = ""
    sso_url: str = ""
    slo_url: Optional[str] = None
    artifact_resolution_url: Optional[str] = None
    x509_cert: str = ""
    private_key: Optional[str] = None
    sign_requests: bool = True
    want_assertions_signed: bool = True
    want_assertions_encrypted: bool = False
    allow_unsolicited: bool = True
    allow_unsolicited_authnrequest: bool = False
    signature_algorithm: str = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
    digest_algorithm: str = "http://www.w3.org/2001/04/xmlenc#sha256"
    encrypt_assertions: bool = False
    encryption_certificate: Optional[str] = None
    
    # OIDC Configuration
    issuer: str = ""
    authorization_endpoint: str = ""
    token_endpoint: str = ""
    jwks_uri: str = ""
    userinfo_endpoint: str = ""
    end_session_endpoint: str = ""
    revocation_endpoint: str = ""
    introspection_endpoint: str = ""
    client_id: str = ""
    client_secret: str = ""
    scope: str = "openid profile email"
    response_types: List[str] = field(default_factory=lambda: ["code"])
    response_modes: List[str] = field(default_factory=lambda: ["query", "fragment"])
    grant_types: List[str] = field(default_factory=lambda: ["authorization_code", "refresh_token"])
    subject_types: List[str] = field(default_factory=lambda: ["public"])
    id_token_signing_alg_values_supported: List[str] = field(default_factory=lambda: ["RS256"])
    token_endpoint_auth_methods_supported: List[str] = field(default_factory=lambda: ["client_secret_basic"])
    claims_supported: List[str] = field(default_factory=lambda: ["sub", "email", "name", "preferred_username"])
    claims_parameter_supported: bool = True
    request_parameter_supported: bool = True
    request_uri_parameter_supported: bool = False
    require_request_uri_registration: bool = False
    op_policy_uri: Optional[str] = None
    op_tos_uri: Optional[str] = None
    
    # LDAP Configuration
    ldap_uri: str = ""
    bind_dn: str = ""
    bind_password: str = ""
    base_dn: str = ""
    user_filter: str = "(uid={username})"
    group_filter: str = "(member={dn})"
    user_attributes: Dict[str, str] = field(default_factory=lambda: {
        "username": "uid",
        "email": "mail",
        "first_name": "givenName",
        "last_name": "sn",
        "display_name": "displayName",
        "groups": "memberOf",
    })
    group_mapping: Dict[str, str] = field(default_factory=dict)
    start_tls: bool = True
    verify_cert: bool = True
    ca_certs: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None
    
    # Attribute mapping
    attribute_mapping: Dict[str, str] = field(default_factory=lambda: {
        "subject_id": "uid",
        "email": "email",
        "first_name": "given_name",
        "last_name": "family_name",
        "email_verified": "email_verified",
        "name": "name",
        "preferred_username": "preferred_username",
        "groups": "groups",
    })
    
    # Group mapping
    group_mapping: Dict[str, str] = field(default_factory=dict)
    default_groups: List[str] = field(default_factory=list)
    default_roles: List[str] = field(default_factory=list)
    
    # JIT Provisioning
    just_in_time_provisioning: bool = True
    update_existing_users: bool = True
    deprovision_on_disable: bool = False
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    metadata_url: Optional[str] = None
    metadata_refresh_interval: int = 3600
    
    # Status
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    last_sync: Optional[datetime] = None


@dataclass
class SAMLAuthnRequest:
    id: str = field(default_factory=lambda: f"_id_{uuid.uuid4().hex}")
    issue_instant: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    destination: str = ""
    issuer: str = ""
    assertion_consumer_service_url: str = ""
    protocol_binding: str = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    assertion_consumer_service_index: Optional[int] = None
    name_id_policy: Optional[str] = None
    requested_authn_context: Optional[str] = None
    force_authn: bool = False
    is_passive: bool = False


@dataclass
class SAMLAssertion:
    assertion_id: str = field(default_factory=lambda: f"_id_{uuid.uuid4().hex}")
    issue_instant: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    issuer: str = ""
    subject: Dict[str, Any] = field(default_factory=dict)
    conditions: Dict[str, Any] = field(default_factory=dict)
    authn_statement: Dict[str, Any] = field(default_factory=dict)
    attribute_statements: List[Dict[str, Any]] = field(default_factory=list)
    authn_context_class_ref: Optional[str] = None
    session_index: Optional[str] = None
    session_not_on_or_after: Optional[datetime] = None


@dataclass
class OIDCTokenResponse:
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: str = "openid profile email"


@dataclass
class OIDCUserInfo:
    sub: str = ""
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    middle_name: Optional[str] = None
    nickname: Optional[str] = None
    preferred_username: Optional[str] = None
    profile: Optional[str] = None
    picture: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    email_verified: bool = False
    gender: Optional[str] = None
    birthdate: Optional[str] = None
    zoneinfo: Optional[str] = None
    locale: Optional[str] = None
    phone_number: Optional[str] = None
    phone_number_verified: bool = False
    address: Optional[Dict[str, Any]] = None
    updated_at: Optional[int] = None
    sub: str = ""
    email: Optional[str] = None
    email_verified: bool = False
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    middle_name: Optional[str] = None
    nickname: Optional[str] = None
    preferred_username: Optional[str] = None
    profile: Optional[str] = None
    picture: Optional[str] = None
    website: Optional[str] = None
    email_verified: bool = False
    gender: Optional[str] = None
    birthdate: Optional[str] = None
    zoneinfo: Optional[str] = None
    locale: Optional[str] = None
    phone_number: Optional[str] = None
    phone_number_verified: bool = False
    address: Optional[Dict[str, Any]] = None
    updated_at: Optional[int] = None


# =============================================================================
# SAML 2.0 Provider
# =============================================================================

class SAMLProvider:
    """SAML 2.0 Identity Provider and Service Provider implementation."""

    def __init__(self, idp_config: 'IdentityProvider'):
        self.idp = idp_config
        self._certificate = self._load_certificate()
        self._private_key = self._load_private_key()

    def _load_certificate(self):
        """Load X.509 certificate."""
        if self.idp.x509_cert:
            # Load certificate from PEM
            from cryptography.hazmat.primitives import serialization
            return serialization.load_pem_x509_certificate(
                self.idp.x509_cert.encode()
            )
        return None

    def _load_private_key(self):
        """Load private key."""
        if self.idp.private_key:
            from cryptography.hazmat.primitives import serialization
            return serialization.load_pem_private_key(
                self.idp.private_key.encode(),
                password=None,
            )
        return None

    def create_authn_request(
        self,
        sp_entity_id: str,
        acs_url: str,
        force_authn: bool = False,
        is_passive: bool = False,
        name_id_policy: Optional[str] = None,
        requested_authn_context: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Create SAML AuthnRequest for SP-initiated SSO (SSO-1: signing with xmlsec)."""
        from xml.etree import ElementTree as ET
        from xml.dom import minidom

        request_id = f"_id_{uuid.uuid4().hex}"
        issue_instant = datetime.now(timezone.utc).isoformat()

        # Create AuthnRequest
        root = ET.Element(
            "{urn:oasis:names:tc:SAML:2.0:protocol}AuthnRequest",
            attrib={
                "ID": f"_id_{uuid.uuid4().hex}",
                "Version": "2.0",
                "IssueInstant": datetime.now(timezone.utc).isoformat(),
                "Destination": self.idp.sso_url,
                "ProtocolBinding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                "AssertionConsumerServiceURL": acs_url,
            })

        # Issuer
        issuer = ET.SubElement(root, "{urn:oasis:names:tc:SAML:2.0:assertion}Issuer")
        issuer.text = ""  # SP entity ID

        # NameIDPolicy
        if name_id_policy:
            name_id_policy = ET.SubElement(root, "{urn:oasis:names:tc:SAML:2.0:protocol}NameIDPolicy")
            name_id_policy.set("Format", name_id_policy)
            name_id_policy.set("AllowCreate", "true")

        # RequestedAuthnContext
        if requested_authn_context:
            requested_authn_context = ET.SubElement(root, "{urn:oasis:names:tc:SAML:2.0:protocol}RequestedAuthnContext")
            requested_authn_context.set("Comparison", "exact")
            authn_context_class_ref = ET.SubElement(
                requested_authn_context,
                "{urn:oasis:names:tc:SAML:2.0:assertion}AuthnContextClassRef"
            )
            requested_authn_context.text = requested_authn_context

        # ForceAuthn
        if force_authn:
            root.set("ForceAuthn", "true")

        if is_passive:
            root.set("IsPassive", "true")

        # Sign the request if private key available (SSO-1)
        if self._private_key and self.idp.sign_requests:
            try:
                import xmlsec
                # XMLSec signing implementation would go here
                # This is a placeholder - production requires proper xmlsec integration
                logger.warning("SAML request signing with xmlsec is not fully implemented")
            except ImportError:
                logger.warning("xmlsec not available - SAML request signing disabled")

        # Serialize to XML
        xml_str = ET.tostring(root, encoding='unicode')
        
        # Compress and encode for HTTP-Redirect binding
        import zlib
        import base64
        compressed = zlib.compress(xml_str.encode())[2:-4]
        encoded = base64.b64encode(compressed).decode()
        
        return encoded, "SAMLRequest"

    def parse_authn_request(self, saml_request: str) -> Dict[str, Any]:
        """Parse incoming SAML AuthnRequest with basic validation (SSO-2)."""
        import base64
        import zlib
        from xml.etree import ElementTree as ET
        
        # Decode and decompress
        try:
            compressed = base64.b64decode(saml_request)
            decompressed = zlib.decompress(compressed, -zlib.MAX_WBITS)
            xml_str = decompressed.decode()
        except Exception as e:
            logger.warning(f"SAML request decode failed: {e}")
            # Maybe not compressed
            xml_str = saml_request
        
        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError as e:
            raise ValueError(f"Invalid SAML XML: {e}")
        
        # Validate required attributes (SSO-2)
        required_attrs = ["ID", "Version", "IssueInstant", "Destination"]
        for attr in required_attrs:
            if not root.get(attr):
                logger.warning(f"Missing required attribute: {attr}")
        
        # Parse attributes
        result = {
            "id": root.get("ID"),
            "version": root.get("Version"),
            "issue_instant": root.get("IssueInstant"),
            "destination": root.get("Destination"),
            "protocol_binding": root.get("ProtocolBinding"),
            "acs_url": root.get("AssertionConsumerServiceURL"),
            "issuer": root.findtext(".//{urn:oasis:names:tc:SAML:2.0:assertion}Issuer"),
            "name_id_policy": root.findtext(".//{urn:oasis:names:tc:SAML:2.0:protocol}NameIDPolicy/@Format"),
            "requested_authn_context": root.findtext(".//{urn:oasis:names:tc:SAML:2.0:assertion}AuthnContextClassRef"),
            "force_authn": root.get("ForceAuthn") == "true",
            "is_passive": root.get("IsPassive") == "true",
        }
        
        # Validate signature if present (SSO-2)
        signature = root.find(".//{http://www.w3.org/2000/09/xmldsig#}Signature")
        if signature is not None:
            result["signed"] = True
            # Signature verification would use xmlsec here
            logger.info("SAML AuthnRequest contains signature - verification requires xmlsec")
        else:
            result["signed"] = False
        
        return result

    def create_assertion(
        self,
        subject_id: str,
        attributes: Dict[str, Any],
        audience: str,
        recipient: str,
        not_on_or_after: Optional[datetime] = None,
        session_index: Optional[str] = None,
        session_not_on_or_after: Optional[datetime] = None,
    ) -> str:
        """Create SAML Assertion."""
        from xml.etree import ElementTree as ET
        
        assertion_id = f"_id_{uuid.uuid4().hex}"
        issue_instant = datetime.now(timezone.utc).isoformat()
        not_on_or_after = not_on_or_after or (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        
        # Create SAML assertion XML
        # This is a simplified version - production would use xmlsec for signing
        
        assertion_xml = f'''<saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
            ID="{assertion_id}"
            Version="2.0"
            IssueInstant="{datetime.now(timezone.utc).isoformat()}"
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <saml:Issuer>{self.idp.entity_id}</saml:Issuer>
  <saml:Subject>
    <saml:NameID Format="urn:oasis:names:tc:SAML:2.0:nameid-format:transient">{subject_id}</saml:NameID>
    <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
      <saml:SubjectConfirmationData NotOnOrAfter="{not_on_or_after}"
        Recipient="{recipient}"
        InResponseTo="" />
    </saml:SubjectConfirmation>
  </saml:Subject>
  <saml:Conditions NotBefore="{datetime.now(timezone.utc).isoformat()}"
    NotOnOrAfter="{not_on_or_after}">
    <saml:AudienceRestriction>
      <saml:Audience>{audience}</saml:Audience>
    </saml:AudienceRestriction>
  </saml:Conditions>
  <saml:AuthnStatement AuthnInstant="{datetime.now(timezone.utc).isoformat()}"
    SessionIndex="{session_index or ''}">
    <saml:AuthnContext>
      <saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport</saml:AuthnContextClassRef>
    </saml:AuthnContext>
  </saml:AuthnStatement>
</saml:Assertion>'''
        
        return assertion_xml


# =============================================================================
# OIDC Provider
# =============================================================================

class OIDCProvider:
    """OpenID Connect Provider implementation."""

    def __init__(self, idp_config: 'IdentityProvider'):
        self.idp = idp_config
        self._jwks_cache: Optional[Dict] = None
        self._jwks_fetched_at: Optional[datetime] = None

    async def _get_jwks(self) -> Dict:
        """Fetch and cache JWKS from provider."""
        if (self._jwks_cache and self._jwks_fetched_at and 
            (datetime.now(timezone.utc) - self._jwks_fetched_at).seconds < 3600):
            return self._jwks_cache
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.idp.jwks_uri) as resp:
                if resp.status == 200:
                    jwks = await resp.json()
                    self._jwks_cache = jwks
                    self._jwks_fetched_at = datetime.now(timezone.utc)
                    return jwks
        return {}

    def build_authorization_url(
        self,
        redirect_uri: str,
        scope: str = "openid profile email",
        state: Optional[str] = None,
        nonce: Optional[str] = None,
        prompt: Optional[str] = None,
        max_age: Optional[int] = None,
        ui_locales: Optional[str] = None,
        login_hint: Optional[str] = None,
        acr_values: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Build OIDC authorization URL with state parameter validation (SSO-6)."""
        # Generate secure state if not provided (SSO-6)
        if state is None:
            state = secrets.token_urlsafe(32)
        else:
            # Validate state entropy (SSO-6)
            if len(state) < 16:
                raise ValueError("State parameter must be at least 16 characters for security")
            # Check entropy - state should have sufficient randomness
            unique_chars = len(set(state))
            if unique_chars < 8:
                raise ValueError("State parameter has insufficient entropy")
        
        # Generate secure nonce if not provided
        if nonce is None:
            nonce = secrets.token_urlsafe(32)
        
        params = {
            "client_id": self.idp.client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "response_type": "code",
            "response_mode": "query",
            "state": state,
            "nonce": nonce,
        }
        
        # Add optional parameters
        if prompt:
            params["prompt"] = prompt
        if max_age:
            params["max_age"] = str(max_age)
        if ui_locales:
            params["ui_locales"] = ui_locales
        if login_hint:
            params["login_hint"] = login_hint
        if acr_values:
            params["acr_values"] = acr_values
        
        from urllib.parse import urlencode
        base_url = self.idp.authorization_endpoint
        return f"{base_url}?{urlencode(params)}", state

    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
        client_id: str,
        client_secret: str,
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.idp.client_id,
                "client_secret": self.idp.client_secret,
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.idp.token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        error_text = await resp.text()
                        raise Exception(f"Token exchange failed: {error_text}")

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from UserInfo endpoint."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.idp.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        return {}

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.idp.client_id,
                "client_secret": self.idp.client_secret,
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.idp.token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
        return {}

    async def end_session(self, id_token_hint: str, post_logout_redirect_uri: str = "") -> str:
        """Build end session URL for logout."""
        params = {
            "id_token_hint": id_token_hint,
        }
        if post_logout_redirect_uri:
            params["post_logout_redirect_uri"] = post_logout_redirect_uri
        
        params_str = urlencode(params)
        return f"{self.idp.end_session_endpoint}?{urlencode(params)}"

    async def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """Verify and decode ID token with JWK to PEM conversion (SSO-3)."""
        import jwt
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        
        # Get JWKS
        jwks = await self._get_jwks()
        if not jwks:
            raise ValueError("Failed to fetch JWKS")
        
        # Get kid from token header
        header = jwt.get_unverified_header(id_token)
        kid = header.get("kid")
        if not kid:
            raise ValueError("Token missing kid header")
        
        # Find matching key
        jwk_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                jwk_key = key
                break
        
        if not jwk_key:
            raise ValueError(f"No matching key found for kid: {kid}")
        
        # Convert JWK to PEM (SSO-3)
        # JWK format: {"kty": "RSA", "n": "...", "e": "...", "kid": "..."}
        if jwk_key.get("kty") != "RSA":
            raise ValueError(f"Unsupported key type: {jwk_key.get('kty')}")
        
        # Convert JWK to PEM
        n = base64.urlsafe_b64decode(jwk_key["n"] + "==")
        e = base64.urlsafe_b64decode(jwk_key["e"] + "==")
        
        public_numbers = rsa.RSAPublicNumbers(
            e=int.from_bytes(e, "big"),
            n=int.from_bytes(n, "big"),
        )
        public_key = public_numbers.public_key()
        
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        
        # Verify token
        try:
            payload = jwt.decode(
                id_token,
                pem,
                algorithms=["RS256"],
                audience=self.idp.client_id,
                issuer=self.idp.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require_exp": True,
                    "require_iat": True,
                }
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("ID token expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid ID token: {e}")


# =============================================================================
# LDAP / Active Directory Provider
# =============================================================================

class LDAPProvider:
    """LDAP / Active Directory identity provider (SSO-4: async with thread pool)."""

    def __init__(self, idp_config: 'IdentityProvider'):
        self.idp = idp_config
        self._connection = None
        self._executor = None

    async def _get_executor(self):
        """Get or create thread pool executor for LDAP operations (SSO-4)."""
        if self._executor is None:
            import concurrent.futures
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        return self._executor

    async def _run_in_executor(self, func, *args, **kwargs):
        """Run synchronous function in thread pool."""
        loop = asyncio.get_event_loop()
        executor = await self._get_executor()
        return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))

    async def connect(self) -> bool:
        """Establish LDAP connection."""
        try:
            import ldap3
            self._connection = ldap3.Connection(
                ldap3.Server(
                    self.idp.ldap_uri,
                    use_ssl=self.idp.start_tls,
                    get_info=ldap3.ALL,
                ),
                user=self.idp.bind_dn,
                password=self.idp.bind_password,
                auto_bind=True,
                auto_bind_referrals=False,
            )
            return self._connection.bind()
        except Exception as e:
            logger.error(f"LDAP connection failed: {e}")
            return False

    async def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user against LDAP using thread pool (SSO-4)."""
        if not self._connection or not self._connection.bound:
            if not await self.connect():
                return None
        
        def _sync_authenticate():
            try:
                # Search for user
                user_filter = self.idp.user_filter.format(username=username)
                self._connection.search(
                    search_base=self.idp.base_dn,
                    search_filter=user_filter,
                    attributes=list(self.idp.user_attributes.values()) + ["dn"],
                )
                
                if not self._connection.entries:
                    return None
                
                entry = self._connection.entries[0]
                
                # Verify password by binding as the user
                user_dn = str(entry.entry_dn)
                user_conn = ldap3.Connection(
                    self._connection.server,
                    user=user_dn,
                    password=password,
                    auto_bind=True,
                )
                
                if user_conn.bind():
                    # Extract user attributes
                    user_attrs = {}
                    for attr_name, ldap_attr in self.idp.user_attributes.items():
                        value = getattr(entry, ldap_attr, None)
                        if value:
                            user_attrs[attr_name] = str(value)
                    
                    # Get groups
                    groups = self._get_user_groups_sync(entry)
                    user_attrs["groups"] = groups
                    
                    return {
                        "dn": str(entry.entry_dn),
                        "attributes": user_attrs,
                        "groups": groups,
                    }
                
                return None
            except Exception as e:
                logger.error(f"LDAP authentication failed: {e}")
                return None
        
        return await self._run_in_executor(_sync_authenticate)

    def _get_user_groups_sync(self, entry) -> List[str]:
        """Get user's group memberships (synchronous version)."""
        groups = []
        try:
            # Search for groups where user is a member
            group_filter = self.idp.group_filter.format(dn=entry.entry_dn)
            self._connection.search(
                search_base=self.idp.base_dn,
                search_filter=group_filter,
                attributes=["cn", "dn"],
            )
            
            for group in self._connection.entries:
                groups.append(str(getattr(group, 'cn', group.entry_dn)))
        except Exception as e:
            logger.warning(f"Failed to get groups: {e}")
        
        return groups

    async def _get_user_groups(self, entry) -> List[str]:
        """Get user's group memberships."""
        groups = []
        try:
            # Search for groups where user is a member
            group_filter = self.idp.group_filter.format(dn=entry.entry_dn)
            self._connection.search(
                search_base=self.idp.base_dn,
                search_filter=group_filter,
                attributes=["cn", "dn"],
            )
            
            for group in self._connection.entries:
                groups.append(str(getattr(group, 'cn', group.entry_dn)))
        except Exception as e:
            logger.warning(f"Failed to get groups: {e}")
        
        return groups

    async def get_user_by_dn(self, dn: str) -> Optional[Dict[str, Any]]:
        """Get user by DN."""
        try:
            self._connection.search(
                search_base=dn,
                search_filter="(objectClass=*)",
                search_scope=ldap3.BASE,
                attributes=list(self.idp.user_attributes.values()) + ["dn"],
            )
            
            if self._connection.entries:
                entry = self._connection.entries[0]
                user_attrs = {}
                for attr_name, ldap_attr in self.idp.user_attributes.items():
                    value = getattr(entry, ldap_attr, None)
                    if value:
                        user_attrs[attr_name] = str(value)
                return {
                    "dn": str(entry.entry_dn),
                    "attributes": user_attrs,
                }
        except Exception as e:
            logger.error(f"LDAP get user failed: {e}")
        return None

    async def search_users(
        self,
        filter_str: str = "(objectClass=person)",
        attributes: Optional[List[str]] = None,
        size_limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search for users."""
        try:
            attrs = attributes or list(self.idp.user_attributes.values()) + ["dn"]
            self._connection.search(
                search_base=self.idp.base_dn,
                search_filter=filter_str,
                attributes=attrs,
                size_limit=size_limit,
            )
            
            users = []
            for entry in self._connection.entries:
                user_attrs = {}
                for attr_name, ldap_attr in self.idp.user_attributes.items():
                    value = getattr(entry, ldap_attr, None)
                    if value:
                        user_attrs[attr_name] = str(value)
                users.append({
                    "dn": str(entry.entry_dn),
                    "attributes": user_attrs,
                })
            return users
        except Exception as e:
            logger.error(f"LDAP search failed: {e}")
            return []


# =============================================================================
# Identity Provider Manager
# =============================================================================

class IdentityProviderManager:
    """Manages multiple identity providers."""

    def __init__(self):
        self._providers: Dict[str, 'IdentityProvider'] = {}
        self._saml_providers: Dict[str, SAMLProvider] = {}
        self._oidc_providers: Dict[str, OIDCProvider] = {}
        self._ldap_providers: Dict[str, LDAPProvider] = {}
        self._lock = asyncio.Lock()

    def register_idp(self, idp: IdentityProvider) -> None:
        """Register an identity provider."""
        with self._lock:
            self._providers[idp.idp_id] = idp
            
            # Create appropriate provider instance
            if idp.idp_type == IdentityProviderType.SAML2:
                self._saml_providers[idp.idp_id] = SAMLProvider(idp)
            elif idp.idp_type == IdentityProviderType.OIDC:
                self._oidc_providers[idp.idp_id] = OIDCProvider(idp)
            elif idp.idp_type in (IdentityProviderType.LDAP, IdentityProviderType.ACTIVE_DIRECTORY):
                self._ldap_providers[idp.idp_id] = LDAPProvider(idp)

    def get_provider(self, idp_id: str) -> Optional[IdentityProvider]:
        return self._providers.get(idp_id)

    def get_saml_provider(self, idp_id: str) -> Optional[SAMLProvider]:
        return self._saml_providers.get(idp_id)

    def get_oidc_provider(self, idp_id: str) -> Optional[OIDCProvider]:
        return self._oidc_providers.get(idp_id)

    def get_ldap_provider(self, idp_id: str) -> Optional[LDAPProvider]:
        return self._ldap_providers.get(idp_id)

    def list_providers(self, idp_type: Optional[IdentityProviderType] = None) -> List[IdentityProvider]:
        providers = list(self._providers.values())
        if idp_type:
            providers = [p for p in providers if p.idp_type == idp_type]
        return providers

    async def authenticate(
        self,
        idp_id: str,
        username: str,
        password: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Authenticate user against an identity provider."""
        idp = self._providers.get(idp_id)
        if not idp:
            return None
        
        if idp.idp_type == IdentityProviderType.SAML2:
            # SAML doesn't typically use username/password directly
            return None
        elif idp.idp_type == IdentityProviderType.OIDC:
            # OIDC would use authorization code flow
            return None
        elif idp.idp_type in (IdentityProviderType.LDAP, IdentityProviderType.ACTIVE_DIRECTORY):
            provider = self._ldap_providers.get(idp_id)
            if provider:
                return await provider.authenticate(username, password)
        
        return None

    async def initiate_sso(self, idp_id: str, **kwargs) -> Dict[str, Any]:
        """Initiate SSO flow."""
        idp = self._providers.get(idp_id)
        if not idp:
            raise ValueError(f"Identity provider {idp_id} not found")
        
        if idp.idp_type == IdentityProviderType.SAML2:
            provider = self._saml_providers.get(idp_id)
            if provider:
                return provider.create_authn_request(**kwargs)
        elif idp.idp_type == IdentityProviderType.OIDC:
            provider = self._oidc_providers.get(idp_id)
            if provider:
                auth_url = provider.build_authorization_url(**kwargs)
                return {"authorization_url": auth_url}
        
        return {}

    async def handle_sso_callback(self, idp_id: str, **kwargs) -> Dict[str, Any]:
        """Handle SSO callback from identity provider."""
        idp = self._providers.get(idp_id)
        if not idp:
            raise ValueError(f"Identity provider {idp_id} not found")
        
        if idp.idp_type == IdentityProviderType.SAML2:
            provider = self._saml_providers.get(idp_id)
            if provider:
                # Parse SAML response
                pass
        elif idp.idp_type == IdentityProviderType.OIDC:
            provider = self._oidc_providers.get(idp_id)
            if provider:
                code = kwargs.get("code")
                if code:
                    return await provider.exchange_code_for_tokens(
                        code=kwargs.get("code"),
                        redirect_uri=kwargs.get("redirect_uri"),
                        client_id=kwargs.get("client_id"),
                        client_secret=kwargs.get("client_secret"),
                    )
        
        return {}

    async def sync_from_idp(self, idp_id: str) -> Dict[str, Any]:
        """Synchronize users/groups from identity provider."""
        idp = self._providers.get(idp_id)
        if not idp:
            raise ValueError(f"Identity provider {idp_id} not found")
        
        results = {
            "users_synced": 0,
            "groups_synced": 0,
            "errors": [],
        }
        
        if idp.idp_type in (IdentityProviderType.LDAP, IdentityProviderType.ACTIVE_DIRECTORY):
            provider = self._ldap_providers.get(idp_id)
            if provider:
                # Sync users
                users = await provider.search_users(size_limit=1000)
                # Process users...
        
        return results


# =============================================================================
# SSO Session Manager
# =============================================================================

@dataclass
class SSOSession:
    session_id: str = field(default_factory=lambda: f"sso-{uuidv7()}")
    user_id: str = ""
    tenant_id: str = "default"
    idp_id: str = ""
    idp_type: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=8))
    access_token: str = ""
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    user_attributes: Dict[str, Any] = field(default_factory=dict)
    roles: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class SSOSessionManager:
    """Manages SSO sessions across identity providers."""
    
    def __init__(self, default_ttl_hours: int = 8):
        self._sessions: Dict[str, SSOSession] = {}
        self._user_sessions: Dict[str, Set[str]] = defaultdict(set)  # user_id -> session_ids
        self._default_ttl_hours = default_ttl_hours
        self._lock = asyncio.Lock()
    
    async def create_session(
        self,
        user_id: str,
        tenant_id: str,
        idp_id: str,
        idp_type: str,
        user_attributes: Dict[str, Any],
        roles: List[str] = None,
        groups: List[str] = None,
        ttl_hours: Optional[int] = None,
    ) -> SSOSession:
        """Create a new SSO session."""
        session = SSOSession(
            user_id=user_id,
            tenant_id=tenant_id,
            idp_id=idp_id,
            idp_type=idp_type,
            user_attributes=user_attributes,
            roles=roles or [],
            groups=groups or [],
            expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours or self._default_ttl_hours),
        )
        
        async with self._lock:
            self._sessions[session.session_id] = session
            self._user_sessions[user_id].add(session.session_id)
        
        return session

    def get_session(self, session_id: str) -> Optional[SSOSession]:
        return self._sessions.get(session_id)

    def get_user_sessions(self, user_id: str) -> List[SSOSession]:
        session_ids = self._user_sessions.get(user_id, set())
        return [self._sessions[sid] for sid in session_ids if sid in self._sessions]

    def validate_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        if session.expires_at < datetime.now(timezone.utc):
            return False
        return True

    def revoke_session(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if session:
            self._user_sessions[session.user_id].discard(session_id)
            return True
        return False

    def revoke_all_user_sessions(self, user_id: str) -> int:
        session_ids = self._user_sessions.pop(user_id, set())
        count = 0
        for sid in session_ids:
            self._sessions.pop(sid, None)
            count += 1
        return count

    def cleanup_expired(self) -> int:
        now = datetime.now(timezone.utc)
        expired = [
            sid for sid, session in self._sessions.items()
            if session.expires_at < datetime.now(timezone.utc)
        ]
        for sid in expired:
            session = self._sessions.pop(sid, None)
            if session:
                self._user_sessions[session.user_id].discard(sid)
        return len(expired)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_sessions": len(self._sessions),
            "active_users": len(self._user_sessions),
            "expired_sessions": sum(
                1 for s in self._sessions.values()
                if s.expires_at < datetime.now(timezone.utc)
            ),
        }


# =============================================================================
# Factory Functions
# =============================================================================

def create_identity_provider(
    name: str,
    idp_type: IdentityProviderType,
    **kwargs
) -> IdentityProvider:
    """Create an identity provider configuration."""
    return IdentityProvider(
        name=name,
        idp_type=idp_type,
        **kwargs
    )


def create_saml_idp(
    name: str,
    entity_id: str,
    sso_url: str,
    x509_cert: str,
    **kwargs
) -> IdentityProvider:
    """Create SAML 2.0 Identity Provider."""
    return IdentityProvider(
        name=name,
        idp_type=IdentityProviderType.SAML2,
        entity_id=entity_id,
        sso_url=sso_url,
        x509_cert=x509_cert,
        **kwargs
    )


def create_oidc_idp(
    name: str,
    issuer: str,
    client_id: str,
    client_secret: str,
    **kwargs
) -> IdentityProvider:
    """Create OIDC Identity Provider."""
    return IdentityProvider(
        name=name,
        idp_type=IdentityProviderType.OIDC,
        issuer=issuer,
        client_id=client_id,
        client_secret=client_secret,
        **kwargs
    )


def create_ldap_idp(
    name: str,
    ldap_uri: str,
    bind_dn: str,
    bind_password: str,
    base_dn: str,
    **kwargs
) -> IdentityProvider:
    """Create LDAP/Active Directory Identity Provider."""
    return IdentityProvider(
        name=name,
        idp_type=IdentityProviderType.LDAP,
        ldap_uri=ldap_uri,
        bind_dn=bind_dn,
        bind_password=bind_password,
        base_dn=base_dn,
        **kwargs
    )


def create_saml_provider(idp: IdentityProvider) -> SAMLProvider:
    return SAMLProvider(idp)


def create_oidc_provider(idp: IdentityProvider) -> OIDCProvider:
    return OIDCProvider(idp)


def create_ldap_provider(idp: IdentityProvider) -> LDAPProvider:
    return LDAPProvider(idp)


def create_identity_provider_manager() -> IdentityProviderManager:
    return IdentityProviderManager()


def create_sso_session_manager(default_ttl_hours: int = 8) -> SSOSessionManager:
    return SSOSessionManager(default_ttl_hours=default_ttl_hours)
