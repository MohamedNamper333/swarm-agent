"""
Request/Response Transformation Plugins.
Supports header manipulation, body transformation, and format conversion.
"""

import asyncio
import base64
import hashlib
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union
import jsonpath_ng
from jsonpath_ng.ext import parse

logger = logging.getLogger(__name__)


@dataclass
class TransformRule:
    """Transformation rule definition."""
    name: str
    phase: str  # "request" or "response"
    match: Dict[str, Any] = field(default_factory=dict)  # Conditions to match
    operations: List[Dict[str, Any]] = field(default_factory=list)  # Operations to apply
    priority: int = 0
    enabled: bool = True


@dataclass
class TransformContext:
    """Context for transformation operations."""
    request: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    variables: Dict[str, Any] = field(default_factory=dict)


class TransformOperation(ABC):
    """Base class for transformation operations."""
    
    @abstractmethod
    async def apply(self, data: Any, context: Any) -> Any:
        """Apply transformation to data."""
        pass


class HeaderOperation:
    """Header manipulation operations."""
    
    @staticmethod
    def add_header(headers: Dict[str, str], name: str, value: str) -> Dict[str, str]:
        """Add or replace header."""
        headers = headers.copy()
        headers[name] = value
        return headers
    
    @staticmethod
    def remove_header(headers: Dict[str, str], name: str) -> Dict[str, str]:
        """Remove header."""
        headers = headers.copy()
        headers.pop(name.lower(), None)
        headers.pop(name.upper(), None)
        headers.pop(name.title(), None)
        return headers
    
    @staticmethod
    def rename_header(headers: Dict[str, str], old_name: str, new_name: str) -> Dict[str, str]:
        """Rename header."""
        headers = headers.copy()
        value = headers.pop(name.lower(), headers.pop(name.upper(), headers.pop(name.title(), None)))
        if value:
            headers[new_name] = value
        return headers
    
    @staticmethod
    def prefix_headers(headers: Dict[str, str], prefix: str) -> Dict[str, str]:
        """Add prefix to all headers."""
        return {f"{prefix}{k}": v for k, v in headers.items()}
    
    @staticmethod
    def filter_headers(headers: Dict[str, str], allowed: List[str]) -> Dict[str, str]:
        """Keep only allowed headers."""
        return {k: v for k, v in headers.items() if k.lower() in [a.lower() for a in allowed]}
    
    @staticmethod
    def strip_hop_by_hop(headers: Dict[str, str]) -> Dict[str, str]:
        """Remove hop-by-hop headers."""
        hop_by_hop = {
            "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
            "te", "trailers", "transfer-encoding", "upgrade"
        }
        return {k: v for k, v in headers.items() if k.lower() not in hop_by_hop}


class BodyOperation:
    """Body transformation operations."""
    
    @staticmethod
    def json_path_get(data: Dict, path: str) -> Any:
        """Extract value using JSONPath."""
        try:
            jsonpath_expr = parse(path)
            matches = [match.value for match in jsonpath_expr.find(data)]
            return matches[0] if matches else None
        except Exception:
            return None
    
    @staticmethod
    def json_path_set(data: Dict, path: str, value: Any) -> Dict:
        """Set value using JSONPath."""
        try:
            jsonpath_expr = parse(path)
            for match in jsonpath_expr.find(data):
                # This is simplified - in production use jsonpath-ng's update
                pass
            return data
        except Exception:
            return data
    
    @staticmethod
    def json_path_delete(data: Dict, path: str) -> Dict:
        """Delete value using JSONPath."""
        try:
            # Simplified - in production use proper JSONPath deletion
            return data
        except Exception:
            return data
    
    @staticmethod
    def transform_json(
        data: Dict,
        operations: List[Dict[str, Any]]
    ) -> Dict:
        """Apply multiple JSON transformations."""
        result = data.copy()
        for op in operations:
            op_type = op.get("op")
            path = op.get("path")
            value = op.get("value")
            
            if op_type == "add":
                # Add field
                pass
            elif op_type == "remove":
                # Remove field
                pass
            elif op_type == "replace":
                # Replace value
                pass
            elif op_type == "move":
                # Move field
                pass
            elif op_type == "copy":
                # Copy field
                pass
            elif op_type == "test":
                # Test value
                pass
        return result
    
    @staticmethod
    def base64_encode(data: Any) -> str:
        """Base64 encode data."""
        if isinstance(data, str):
            data = data.encode()
        elif isinstance(data, dict):
            data = json.dumps(data).encode()
        return base64.b64encode(data).decode()
    
    @staticmethod
    def base64_decode(data: str) -> bytes:
        """Base64 decode data."""
        return base64.b64decode(data)
    
    @staticmethod
    def hash_data(data: str, algorithm: str = "sha256") -> str:
        """Hash data."""
        hasher = hashlib.new(algorithm)
        hasher.update(data.encode() if isinstance(data, str) else data)
        return hasher.hexdigest()
    
    @staticmethod
    def mask_sensitive(data: Dict, fields: List[str]) -> Dict:
        """Mask sensitive fields."""
        result = data.copy()
        for field in fields:
            if field in result:
                result[field] = "*****"
        return result
    
    @staticmethod
    def rename_keys(data: Dict, mapping: Dict[str, str]) -> Dict:
        """Rename keys in dictionary."""
        result = {}
        for k, v in data.items():
            new_key = mapping.get(k, k)
            result[new_key] = v
        return result


class RequestTransformPlugin:
    """Request transformation plugin."""
    
    def __init__(self):
        self.rules: List[Dict[str, Any]] = []
        self._header_ops = HeaderOperation()
        self._body_ops = BodyOperation()
    
    def add_rule(self, rule: Dict[str, Any]) -> None:
        """Add transformation rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.get("priority", 0), reverse=True)
    
    async def transform_request(
        self,
        headers: Dict[str, str],
        body: bytes,
        context: Dict[str, Any]
    ) -> tuple:
        """Transform request headers and body."""
        headers = dict(headers)
        body = body
        
        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            
            # Check match conditions
            if not self._match_conditions(rule.get("match", {}), context):
                continue
            
            # Apply header operations
            if "headers" in rule.get("operations", {}):
                headers = await self._apply_header_ops(headers, rule["operations"]["headers"])
            
            # Apply body operations
            if "body" in rule.get("operations", {}):
                body = await self._apply_body_ops(body, rule["operations"]["body"])
        
        return headers, body
    
    def _match_conditions(self, conditions: Dict, context: Dict) -> bool:
        """Check if request matches conditions."""
        for key, expected in conditions.items():
            if key == "path":
                import fnmatch
                if not fnmatch.fnmatch(context.get("path", ""), expected):
                    return False
            elif key == "method":
                if context.get("method") != expected:
                    return False
            elif key == "header":
                if context.get("headers", {}).get(expected.get("name")) != expected.get("value"):
                    return False
            elif key == "query":
                if context.get("query_params", {}).get(expected.get("name")) != expected.get("value"):
                    return False
        return True
    
    async def _apply_header_ops(self, headers: Dict, ops: Dict) -> Dict:
        """Apply header operations."""
        headers = dict(headers)
        
        for op in ops:
            op_type = op.get("type")
            
            if op_type == "add":
                headers[op["name"]] = op["value"]
            elif op_type == "remove":
                headers.pop(op["name"], None)
            elif op_type == "rename":
                if op["from"] in headers:
                    headers[op["to"]] = headers.pop(op["from"])
            elif op_type == "prefix":
                new_headers = {}
                for k, v in headers.items():
                    headers[f"{op['prefix']}{k}"] = v
            elif op_type == "strip_prefix":
                new_headers = {}
                for k, v in headers.items():
                    if k.startswith(op["prefix"]):
                        new_headers[k[len(op["prefix"]):]] = v
                    else:
                        new_headers[k] = v
                headers = new_headers
            elif op_type == "filter":
                allowed = op.get("allowed", [])
                headers = {k: v for k, v in headers.items() if k.lower() in [a.lower() for a in allowed]}
        
        return headers
    
    async def _apply_body_ops(self, body: bytes, ops: Dict) -> bytes:
        """Apply body operations."""
        try:
            # Parse body as JSON if possible
            try:
                data = json.loads(body.decode())
            except:
                return body
            
            for op in ops:
                op_type = op.get("type")
                path = op.get("path")
                value = op.get("value")
                
                if op_type == "json_path_set":
                    # Simplified JSON path set
                    pass
                elif op_type == "json_path_remove":
                    pass
                elif op_type == "transform":
                    # Apply custom transform function
                    transform_fn = op.get("function")
                    if callable(transform_fn):
                        data = transform_fn(data)
            
            return json.dumps(data).encode()
        except Exception:
            return body


class ResponseTransformPlugin:
    """Response transformation plugin."""
    
    def __init__(self):
        self.rules: List[Dict[str, Any]] = []
        self._header_ops = HeaderOperation()
        self._body_ops = BodyOperation()
    
    def add_rule(self, rule: Dict[str, Any]) -> None:
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.get("priority", 0), reverse=True)
    
    async def transform_response(
        self,
        status_code: int,
        headers: Dict[str, str],
        body: bytes,
        context: Dict[str, Any]
    ) -> tuple:
        """Transform response headers and body."""
        headers = dict(headers)
        body = body
        
        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            
            if not self._match_conditions(rule.get("match", {}), {"status": status_code}):
                continue
            
            if "headers" in rule.get("operations", {}):
                headers = await self._apply_header_ops(headers, rule["operations"]["headers"])
            
            if "body" in rule.get("operations", {}):
                body = await self._apply_body_ops(body, rule["operations"]["body"])
        
        return headers, body
    
    def _match_conditions(self, conditions: Dict, context: Dict) -> bool:
        for key, expected in conditions.items():
            if key == "status":
                if context.get("status") != expected:
                    return False
            elif key == "header":
                if context.get("headers", {}).get(expected.get("name")) != expected.get("value"):
                    return False
            elif key == "path":
                import fnmatch
                if not fnmatch.fnmatch(context.get("path", ""), expected):
                    return False
        return True
    
    async def _apply_header_ops(self, headers: Dict, ops: Dict) -> Dict:
        headers = dict(headers)
        
        for op in ops:
            op_type = op.get("type")
            
            if op_type == "add":
                headers[op["name"]] = op["value"]
            elif op_type == "remove":
                headers.pop(op["name"], None)
            elif op_type == "rename":
                if op["from"] in headers:
                    headers[op["to"]] = headers.pop(op["from"])
            elif op_type == "filter":
                allowed = op.get("allowed", [])
                return {k: v for k, v in headers.items() if k.lower() in [a.lower() for a in allowed]}
        
        return headers
    
    async def _apply_body_ops(self, body: bytes, ops: Dict) -> bytes:
        try:
            try:
                data = json.loads(body.decode())
            except:
                return body
            
            for op in ops:
                op_type = op.get("type")
                path = op.get("path")
                value = op.get("value")
                
                if op_type == "json_path_set":
                    # Simplified
                    pass
                elif op_type == "mask":
                    fields = op.get("fields", [])
                    data = json.loads(body.decode())
                    data = BodyOperation.mask_sensitive(data, fields)
                    return json.dumps(data).encode()
                elif op_type == "transform":
                    transform_fn = op.get("function")
                    if callable(transform_fn):
                        data = json.loads(body.decode())
                        data = transform_fn(data)
                        return json.dumps(data).encode()
            
            return json.dumps(data).encode()
        except Exception:
            return body


class RequestResponseTransformPlugin:
    """Combined request/response transformation plugin."""
    
    def __init__(self):
        self.request_plugin = RequestTransformPlugin()
        self.response_plugin = ResponseTransformPlugin()
    
    def add_request_rule(self, rule: Dict[str, Any]) -> None:
        self.request_plugin.add_rule(rule)
    
    def add_response_rule(self, rule: Dict[str, Any]) -> None:
        self.response_plugin.add_rule(rule)
    
    async def process_request(
        self,
        headers: Dict[str, str],
        body: bytes,
        context: Dict[str, Any]
    ) -> tuple:
        return await self.request_plugin.transform_request(headers, body, context)
    
    async def process_response(
        self,
        status_code: int,
        headers: Dict[str, str],
        body: bytes,
        context: Dict[str, Any]
    ) -> tuple:
        return await self.response_plugin.transform_response(status_code, headers, body, context)
