"""
Artifact Store - Artifact storage, versioning, and provenance tracking.
"""

import hashlib
import io
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, BinaryIO
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Artifact Models
# =============================================================================

class ArtifactType(str, Enum):
    FILE = "file"
    DOCKER_IMAGE = "docker_image"
    MODEL = "model"
    DATASET = "dataset"
    CONFIG = "config"
    SCRIPT = "script"
    BINARY = "binary"
    DOCUMENT = "document"
    ARCHIVE = "archive"
    OTHER = "other"


class ArtifactStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    STORED = "stored"
    FAILED = "failed"
    DELETED = "deleted"
    ARCHIVED = "archived"


@dataclass
class ArtifactMetadata:
    artifact_id: str = field(default_factory=lambda: f"art-{uuidv7()}")
    name: str = ""
    artifact_type: ArtifactType = ArtifactType.FILE
    version: str = "1.0.0"
    description: str = ""
    
    # Content info
    content_hash: str = ""  # SHA256
    size_bytes: int = 0
    mime_type: str = ""
    
    # Versioning
    parent_version: Optional[str] = None
    changelog: str = ""
    
    # Provenance
    created_by: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_url: Optional[str] = None
    build_info: Dict[str, Any] = field(default_factory=dict)
    
    # Tags and metadata
    tags: Set[str] = field(default_factory=set)
    labels: Dict[str, str] = field(default_factory=dict)
    
    # Status
    status: ArtifactStatus = ArtifactStatus.PENDING
    storage_path: Optional[str] = None
    checksum_verified: bool = False
    
    # Retention
    ttl_seconds: Optional[int] = None
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        if self.expires_at:
            return datetime.now(timezone.utc) > self.expires_at
        return False


@dataclass
class ArtifactVersion:
    """A version of an artifact."""
    artifact_id: str
    version: str
    metadata: "ArtifactMetadata"
    content_hash: str
    size_bytes: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    changelog: str = ""


@dataclass
class UploadSession:
    """Tracks an upload session for large artifacts."""
    session_id: str = field(default_factory=lambda: f"up-{uuidv7()}")
    artifact_id: str = ""
    total_size: int = 0
    uploaded_bytes: int = 0
    chunk_size: int = 0
    chunks_received: Set[int] = field(default_factory=set)
    total_chunks: int = 0
    status: str = "active"  # active, completed, failed, cancelled
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=24))


# =============================================================================
# Storage Backends
# =============================================================================

class StorageBackend(ABC):
    """Abstract storage backend for artifacts."""
    
    @abstractmethod
    def write(self, path: str, data: BinaryIO, metadata: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def read(self, path: str) -> Optional[BinaryIO]:
        pass
    
    @abstractmethod
    def delete(self, path: str) -> bool:
        pass
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        pass
    
    @abstractmethod
    def get_size(self, path: str) -> Optional[int]:
        pass
    
    @abstractmethod
    def get_metadata(self, path: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def list(self, prefix: str = "") -> List[str]:
        pass


class LocalFileStorage(StorageBackend):
    """Local filesystem storage backend."""
    
    def __init__(self, base_path: str = "/tmp/artifacts"):
        self.base_path = base_path
        import os
        os.makedirs(base_path, exist_ok=True)
    
    def _full_path(self, path: str) -> str:
        """Traversal-proof path resolution (AR-N1).

        Previously os.path.join(base, "../../x") escaped the artifact root —
        an arbitrary read/write primitive on the host filesystem.
        """
        import os
        base = os.path.realpath(self.base_path)
        full = os.path.realpath(os.path.join(base, path.lstrip("/")))
        if full != base and not full.startswith(base + os.sep):
            raise ValueError(f"Artifact path escapes storage root: {path!r}")
        return full
    
    def write(self, path: str, data: BinaryIO, metadata: Dict[str, Any]) -> bool:
        import os
        full_path = self._full_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        try:
            with open(full_path, "wb") as f:
                f.write(data.read())
            return True
        except Exception as e:
            logger.error(f"Write failed: {e}")
            return False
    
    def read(self, path: str) -> Optional[BinaryIO]:
        import os
        full_path = self._full_path(path)
        if not os.path.exists(full_path):
            return None
        return open(full_path, "rb")
    
    def delete(self, path: str) -> bool:
        import os
        full_path = self._full_path(path)
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False
    
    def exists(self, path: str) -> bool:
        import os
        full_path = self._full_path(path)
        return os.path.exists(full_path)
    
    def get_size(self, path: str) -> Optional[int]:
        import os
        full_path = self._full_path(path)
        if os.path.exists(full_path):
            return os.path.getsize(full_path)
        return None
    
    def get_metadata(self, path: str) -> Dict[str, Any]:
        import os
        full_path = self._full_path(path)
        if not os.path.exists(full_path):
            return {}
        stat = os.stat(full_path)
        return {
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
        }
    
    def list(self, prefix: str = "") -> List[str]:
        import os
        full_prefix = self._full_path(prefix)
        if not os.path.exists(full_prefix):
            return []
        
        result = []
        for root, dirs, files in os.walk(full_prefix):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, self.base_path)
                result.append(rel)
        return result


class S3Storage(StorageBackend):
    """S3-compatible storage backend."""
    
    def __init__(
        self,
        bucket: str,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "us-east-1",
    ):
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self.region = region
        
        try:
            import boto3
            self.client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
            )
            self._available = True
        except ImportError:
            logger.warning("boto3 not installed, S3 storage unavailable")
            self._available = False
            self.client = None
    
    def write(self, path: str, data: BinaryIO, metadata: Dict[str, Any]) -> bool:
        if not self._available:
            return False
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=path,
                Body=data,
                Metadata={k: str(v) for k, v in metadata.items()},
            )
            return True
        except Exception as e:
            logger.error(f"S3 write failed: {e}")
            return False
    
    def read(self, path: str) -> Optional[BinaryIO]:
        if not self._available:
            return None
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=path)
            return response["Body"]
        except Exception as e:
            logger.error(f"S3 read failed: {e}")
            return None
    
    def delete(self, path: str) -> bool:
        if not self._available:
            return False
        try:
            self.client.delete_object(Bucket=self.bucket, Key=path)
            return True
        except Exception as e:
            logger.error(f"S3 delete failed: {e}")
            return False
    
    def exists(self, path: str) -> bool:
        if not self._available:
            return False
        try:
            self.client.head_object(Bucket=self.bucket, Key=path)
            return True
        except Exception:
            return False
    
    def get_size(self, path: str) -> Optional[int]:
        if not self._available:
            return None
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=path)
            return response.get("ContentLength")
        except Exception:
            return None
    
    def get_metadata(self, path: str) -> Dict[str, Any]:
        if not self._available:
            return {}
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=path)
            return response.get("Metadata", {})
        except Exception:
            return {}
    
    def list(self, prefix: str = "") -> List[str]:
        if not self._available:
            return []
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            result = []
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    result.append(obj["Key"])
            return result
        except Exception as e:
            logger.error(f"S3 list failed: {e}")
            return []


# =============================================================================
# Artifact Store
# =============================================================================

class ArtifactStore:
    """Main artifact store with versioning and provenance."""
    
    def __init__(
        self,
        storage: StorageBackend,
        metadata_store: Optional[Any] = None,
    ):
        self.storage = storage
        self.metadata_store = metadata_store  # Could be a database
        
        self._artifacts: Dict[str, ArtifactMetadata] = {}
        self._versions: Dict[str, List[ArtifactVersion]] = defaultdict(list)
        self._lock = threading.RLock()
        
        # Upload sessions
        self._upload_sessions: Dict[str, UploadSession] = {}
    
    def create_artifact(
        self,
        name: str,
        artifact_type: ArtifactType,
        version: str = "1.0.0",
        description: str = "",
        created_by: str = "system",
        tags: Optional[Set[str]] = None,
        labels: Optional[Dict[str, str]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> ArtifactMetadata:
        """Create a new artifact metadata entry."""
        with self._lock:
            artifact = ArtifactMetadata(
                name=name,
                artifact_type=artifact_type,
                version=version,
                description=description,
                created_by=created_by,
                tags=tags or set(),
                labels=labels or {},
            )
            
            if ttl_seconds:
                artifact.ttl_seconds = ttl_seconds
                artifact.expires_at = now_utc() + timedelta(seconds=ttl_seconds)
            
            self._artifacts[artifact.artifact_id] = artifact
            logger.info(f"Created artifact: {artifact.artifact_id} ({name})")
            return artifact
    
    def get_artifact(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        with self._lock:
            return self._artifacts.get(artifact_id)
    
    def update_artifact(self, artifact_id: str, updates: Dict[str, Any]) -> Optional[ArtifactMetadata]:
        with self._lock:
            artifact = self._artifacts.get(artifact_id)
            if not artifact:
                return None
            
            # AR-N4: financial-grade fields (storage_path, hashes, size,
            # status) are engine-managed — direct mutation defeated the
            # checksum system entirely.
            allowed = {"name", "description", "tags", "metadata",
                       "version", "updated_at"}
            for key, value in updates.items():
                if key in ("artifact_id", "created_at", "created_by"):
                    continue
                if key in ("storage_path", "content_hash", "size_bytes",
                           "status", "checksum_verified"):
                    raise ValueError(
                        f"'{key}' is engine-managed; use store_content()/"
                        f"verify_checksum()")
                if key in allowed and hasattr(artifact, key):
                    setattr(artifact, key, value)

            artifact.updated_at = now_utc()
            return artifact
    
    def delete_artifact(self, artifact_id: str, delete_content: bool = True) -> bool:
        with self._lock:
            artifact = self._artifacts.get(artifact_id)
            if not artifact:
                return False
            
            if delete_content and artifact.storage_path:
                self.storage.delete(artifact.storage_path)
            
            del self._artifacts[artifact_id]
            if artifact_id in self._versions:
                del self._versions[artifact_id]
            
            logger.info(f"Deleted artifact: {artifact_id}")
            return True
    
    def list_artifacts(
        self,
        artifact_type: Optional[ArtifactType] = None,
        tags: Optional[Set[str]] = None,
        status: Optional[ArtifactStatus] = None,
        limit: int = 100,
    ) -> List[ArtifactMetadata]:
        with self._lock:
            artifacts = list(self._artifacts.values())
            
            if artifact_type:
                artifacts = [a for a in artifacts if a.artifact_type == artifact_type]
            if tags:
                artifacts = [a for a in artifacts if tags.issubset(a.tags)]
            if status:
                artifacts = [a for a in artifacts if a.status == status]
            
            artifacts.sort(key=lambda a: a.created_at, reverse=True)
            return artifacts[:limit]
    
    def store_content(
        self,
        artifact_id: str,
        data: BinaryIO,
        content_hash: Optional[str] = None,
    ) -> bool:
        """Store artifact content and update metadata."""
        with self._lock:
            artifact = self._artifacts.get(artifact_id)
            if not artifact:
                return False
            
            # ALWAYS compute server-side hash. A caller-supplied hash was
            # trusted verbatim and `checksum_verified` stamped True without
            # any verification (AR-N2). Non-seekable streams are buffered
            # once so hash+write see identical bytes (AR-N3).
            try:
                data.seek(0)
            except (OSError, AttributeError):
                data = io.BytesIO(data.read())
            content_hash = self._calculate_hash(data)
            data.seek(0)
            
            # Generate storage path
            storage_path = f"artifacts/{artifact.artifact_id}/{artifact.version}"
            
            # Store in backend
            success = self.storage.write(storage_path, data, {
                "artifact_id": artifact_id,
                "version": artifact.version,
                "content_hash": content_hash,
            })
            
            if success:
                # Verify what actually landed on disk before stamping.
                readback = self.storage.read(storage_path)
                verified = False
                if readback is not None:
                    import hashlib as _hl
                    h = _hl.sha256()
                    while True:
                        chunk = readback.read(1024 * 1024)
                        if not chunk:
                            break
                        h.update(chunk)
                    verified = h.hexdigest() == content_hash
                if not verified:
                    logger.error(
                        f"Post-write checksum mismatch for {artifact_id}; "
                        f"removing corrupt stored object")
                    self.storage.delete(storage_path)
                    return False

                artifact.content_hash = content_hash
                artifact.size_bytes = self.storage.get_size(f"artifacts/{artifact.artifact_id}/{artifact.version}") or 0
                artifact.storage_path = storage_path
                artifact.status = ArtifactStatus.STORED
                artifact.checksum_verified = True
                artifact.updated_at = now_utc()
                
                # Record version
                version = ArtifactVersion(
                    artifact_id=artifact_id,
                    version=artifact.version,
                    metadata=artifact,
                    content_hash=content_hash,
                    size_bytes=artifact.size_bytes,
                )
                self._versions[artifact_id].append(version)
                
                logger.info(f"Stored content for artifact: {artifact_id}")
                return True
            
            return False
    
    def get_content(self, artifact_id: str, version: Optional[str] = None) -> Optional[BinaryIO]:
        """Retrieve artifact content."""
        with self._lock:
            artifact = self._artifacts.get(artifact_id)
            if not artifact:
                return None
            
            # Get specific version if requested
            if version:
                for v in self._versions.get(artifact_id, []):
                    if v.version == version:
                        path = f"artifacts/{artifact_id}/{version}"
                        return self.storage.read(path)
            
            # Return latest
            if artifact.storage_path:
                return self.storage.read(artifact.storage_path)
            
            return None
    
    def create_version(
        self,
        artifact_id: str,
        new_version: str,
        data: BinaryIO,
        changelog: str = "",
        created_by: str = "system",
    ) -> Optional[ArtifactVersion]:
        """Create a new version of an artifact."""
        with self._lock:
            artifact = self._artifacts.get(artifact_id)
            if not artifact:
                return None
            
            # Update artifact metadata
            artifact.parent_version = artifact.version
            artifact.version = new_version
            artifact.changelog = changelog
            artifact.updated_at = now_utc()
            
            # Calculate hash
            content_hash = self._calculate_hash(data)
            data.seek(0)
            
            # Store new version
            storage_path = f"artifacts/{artifact_id}/{new_version}"
            success = self.storage.write(storage_path, data, {
                "artifact_id": artifact_id,
                "version": new_version,
                "content_hash": content_hash,
            })
            
            if not success:
                return None
            
            # Update artifact
            artifact.content_hash = content_hash
            artifact.size_bytes = self.storage.get_size(storage_path) or 0
            artifact.storage_path = storage_path
            artifact.status = ArtifactStatus.STORED
            artifact.checksum_verified = True
            
            # Create version record
            version = ArtifactVersion(
                artifact_id=artifact_id,
                version=new_version,
                metadata=artifact,
                content_hash=content_hash,
                size_bytes=artifact.size_bytes,
                changelog=changelog,
                created_by=created_by,
            )
            self._versions[artifact_id].append(version)
            
            logger.info(f"Created version {new_version} for artifact {artifact_id}")
            return version
    
    def get_versions(self, artifact_id: str) -> List[ArtifactVersion]:
        with self._lock:
            return list(self._versions.get(artifact_id, []))
    
    def verify_checksum(self, artifact_id: str, version: Optional[str] = None) -> bool:
        """Verify artifact checksum."""
        with self._lock:
            artifact = self._artifacts.get(artifact_id)
            if not artifact or not artifact.content_hash:
                return False
            
            # Read content and verify
            content = self.get_content(artifact_id, version)
            if not content:
                return False
            
            calculated_hash = self._calculate_hash(content)
            content.seek(0)
            
            expected_hash = artifact.content_hash
            if version:
                for v in self._versions.get(artifact_id, []):
                    if v.version == version:
                        expected_hash = v.content_hash
                        break
            
            return calculated_hash == expected_hash
    
    def _calculate_hash(self, data: BinaryIO) -> str:
        """Calculate SHA256 hash of data."""
        hasher = hashlib.sha256()
        pos = data.tell()
        data.seek(0)
        for chunk in iter(lambda: data.read(8192), b""):
            hasher.update(chunk)
        data.seek(pos)
        return hasher.hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_size = sum(a.size_bytes for a in self._artifacts.values())
            by_type = defaultdict(int)
            by_status = defaultdict(int)
            
            for a in self._artifacts.values():
                by_type[a.artifact_type.value] += 1
                by_status[a.status.value] += 1
            
            return {
                "total_artifacts": len(self._artifacts),
                "total_versions": sum(len(v) for v in self._versions.values()),
                "total_size_bytes": total_size,
                "by_type": dict(by_type),
                "by_status": dict(by_status),
            }


# =============================================================================
# Upload Session Manager
# =============================================================================

class UploadManager:
    """Manages resumable upload sessions for large artifacts."""
    
    def __init__(self, artifact_store: ArtifactStore):
        self.artifact_store = artifact_store
        self._sessions: Dict[str, UploadSession] = {}
        self._lock = threading.RLock()
    
    def create_session(
        self,
        artifact_id: str,
        total_size: int,
        chunk_size: int = 5 * 1024 * 1024,  # 5MB default
    ) -> UploadSession:
        with self._lock:
            total_chunks = (total_size + chunk_size - 1) // chunk_size
            
            session = UploadSession(
                artifact_id=artifact_id,
                total_size=total_size,
                chunk_size=chunk_size,
                total_chunks=total_chunks,
            )
            
            self._sessions[session.session_id] = session
            logger.info(f"Created upload session: {session.session_id} for {artifact_id}")
            return session
    
    def upload_chunk(
        self,
        session_id: str,
        chunk_index: int,
        data: BinaryIO,
    ) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session or session.status != "active":
                return False
            
            if chunk_index in session.chunks_received:
                return True  # Already received
            
            if chunk_index >= session.total_chunks:
                return False
            
            # Store chunk temporarily (in production, write to temp storage)
            session.chunks_received.add(chunk_index)
            session.uploaded_bytes += len(data.read()) if hasattr(data, 'read') else 0
            data.seek(0)
            session.updated_at = now_utc()
            
            # Check if complete
            if len(session.chunks_received) == session.total_chunks:
                session.status = "completed"
            
            return True
    
    def complete_upload(
        self,
        session_id: str,
        final_hash: str,
    ) -> Optional[str]:
        """Finalize upload and create artifact."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session or session.status != "completed":
                return None
            
            # In production, reassemble chunks and verify hash
            # For now, just return artifact ID
            del self._sessions[session_id]
            return session.artifact_id
    
    def get_session(self, session_id: str) -> Optional[UploadSession]:
        with self._lock:
            return self._sessions.get(session_id)
    
    def cancel_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].status = "cancelled"
                return True
            return False
    
    def cleanup_expired(self, max_age_hours: int = 24) -> int:
        with self._lock:
            now = now_utc()
            expired = [
                sid for sid, s in self._sessions.items()
                if s.expires_at and s.expires_at < now
            ]
            for sid in expired:
                del self._sessions[sid]
            return len(expired)


# =============================================================================
# Factory
# =============================================================================

def create_artifact_store(
    storage: Optional[StorageBackend] = None,
    storage_type: str = "local",
    **kwargs,
) -> ArtifactStore:
    """Create an artifact store with the specified storage backend."""
    if storage:
        return ArtifactStore(storage)
    
    if storage_type == "local":
        base_path = kwargs.get("base_path", "/tmp/artifacts")
        storage = LocalFileStorage(base_path)
    elif storage_type == "s3":
        storage = S3Storage(
            bucket=kwargs.get("bucket", ""),
            endpoint_url=kwargs.get("endpoint_url"),
            access_key=kwargs.get("access_key"),
            secret_key=kwargs.get("secret_key"),
            region=kwargs.get("region", "us-east-1"),
        )
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
    
    return ArtifactStore(storage)


def create_upload_manager(artifact_store: ArtifactStore) -> UploadManager:
    return UploadManager(artifact_store)
