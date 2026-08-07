"""
Swarm API Layer - REST, WebSocket, Authentication
Production-grade API for the swarm system.
"""

from .rest_server import app as rest_app
from .websocket_server import create_websocket_app
from .auth import (
    AuthManager,
    APIKey,
    TokenPair,
    AuthStats,
    AuthScope,
    TokenType,
    get_auth_manager,
    get_current_user,
    require_scopes
)

__all__ = [
    # Week 13: REST API + WebSocket + Auth
    "rest_app",
    "create_websocket_app",
    "AuthManager",
    "APIKey",
    "TokenPair",
    "AuthStats",
    "AuthScope",
    "TokenType",
    "get_auth_manager",
    "get_current_user",
    "require_scopes",
]

__version__ = "3.0.0"