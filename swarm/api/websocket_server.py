"""
WebSocket Server Module - Real-time Updates for Swarm
Provides WebSocket endpoints for real-time task/agent updates.
"""
import asyncio
import json
import logging
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends


# Module-level app instance so uvicorn can find it:
#   uvicorn swarm.api.websocket_server:app
app = None


def get_app() -> FastAPI:
    """Lazy-build the WS FastAPI app from create_websocket_app()."""
    global app
    if app is None:
        app = create_websocket_app()
    return app
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types"""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    AGENT_STATE_CHANGED = "agent_state_changed"
    MODEL_HEALTH_CHANGED = "model_health_changed"
    CONSTITUTIONAL_VIOLATION = "constitutional_violation"
    ALERT_FIRED = "alert_fired"
    ALERT_RESOLVED = "alert_resolved"
    SNAPSHOT_CREATED = "snapshot_created"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_COMPLETED = "recovery_completed"
    SYSTEM_STATUS = "system_status"
    METRICS_UPDATE = "metrics_update"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


@dataclass
class WSMessage:
    """WebSocket message"""
    type: str
    timestamp: str
    payload: Dict[str, Any]
    request_id: Optional[str] = None


class ConnectionManager:
    """Manages WebSocket connections and subscriptions"""
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_subscriptions: Dict[str, Set[str]] = {}
        self.topic_subscribers: Dict[str, Set[str]] = {}
        self.connection_metadata: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept and register a new connection"""
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket
            self.client_subscriptions[client_id] = set()
            self.connection_metadata[client_id] = {
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "last_heartbeat": datetime.now(timezone.utc).isoformat()
            }
            logger.info(f"Client {client_id} connected. Total: {len(self.active_connections)}")
    
    async def disconnect(self, client_id: str) -> None:
        """Remove a connection"""
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            if client_id in self.client_subscriptions:
                # Remove from topic subscribers
                for topic in self.client_subscriptions[client_id]:
                    if topic in self.topic_subscribers:
                        self.topic_subscribers[topic].discard(client_id)
                        if not self.topic_subscribers[topic]:
                            del self.topic_subscribers[topic]
                del self.client_subscriptions[client_id]
            if client_id in self.connection_metadata:
                del self.connection_metadata[client_id]
            logger.info(f"Client {client_id} disconnected. Total: {len(self.active_connections)}")
    
    async def subscribe(self, client_id: str, topic: str) -> bool:
        """Subscribe a client to a topic"""
        async with self._lock:
            if client_id not in self.active_connections:
                return False
            if topic not in self.topic_subscribers:
                self.topic_subscribers[topic] = set()
            self.topic_subscribers[topic].add(client_id)
            self.client_subscriptions[client_id].add(topic)
            return True
    
    async def unsubscribe(self, client_id: str, topic: str) -> bool:
        """Unsubscribe a client from a topic"""
        async with self._lock:
            if client_id not in self.client_subscriptions:
                return False
            self.client_subscriptions[client_id].discard(topic)
            if topic in self.topic_subscribers:
                self.topic_subscribers[topic].discard(client_id)
                if not self.topic_subscribers[topic]:
                    del self.topic_subscribers[topic]
            return True
    
    async def broadcast(self, topic: str, message: Dict[str, Any], exclude: Optional[str] = None) -> int:
        """Broadcast a message to all subscribers of a topic"""
        sent = 0
        async with self._lock:
            if topic not in self.topic_subscribers:
                return 0
            
            subscribers = list(self.topic_subscribers[topic])
        
        for client_id in subscribers:
            if client_id == topic:  # Don't send to self if topic is client_id
                continue
            try:
                websocket = self.active_connections.get(client_id)
                if websocket:
                    await websocket.send_text(json.dumps(message))
                    sent += 1
            except Exception as e:
                logger.warning(f"Failed to send to {client_id}: {e}")
        
        return sent
    
    async def send_personal(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to a specific client"""
        async with self._lock:
            websocket = self.active_connections.get(client_id)
            if not websocket:
                return False
        
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning(f"Failed to send to {client_id}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "topics": {k: len(v) for k, v in self.topic_subscribers.items()},
            "clients": list(self.active_connections.keys())
        }


# Global manager
_connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    return _connection_manager


async def websocket_endpoint(websocket: WebSocket, client_id: Optional[str] = None):
    """Main WebSocket endpoint"""
    if client_id is None:
        client_id = f"client-{uuid.uuid4().hex[:8]}"
    
    await _connection_manager.connect(websocket, client_id)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"client_id": client_id}
        })
        
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_message(client_id, message)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {"error": "Invalid JSON"}
                })
            except Exception as e:
                logger.error(f"Error handling message: {e}")
    
    except WebSocketDisconnect:
        await _connection_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        await _connection_manager.disconnect(client_id)


async def handle_message(client_id: str, message: Dict[str, Any]):
    """Handle incoming WebSocket message"""
    msg_type = message.get("type")
    
    if msg_type == MessageType.SUBSCRIBE.value:
        topics = message.get("topics", [])
        for topic in topics:
            await _connection_manager.subscribe(client_id, topic)
        await _connection_manager.send_personal(client_id, {
            "type": "subscribed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"topics": topics}
        })
    
    elif msg_type == MessageType.UNSUBSCRIBE.value:
        topics = message.get("topics", [])
        for topic in topics:
            await _connection_manager.unsubscribe(client_id, topic)
        await _connection_manager.send_personal(client_id, {
            "type": "unsubscribed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"topics": topics}
        })
    
    elif msg_type == MessageType.HEARTBEAT.value:
        await _connection_manager.send_personal(client_id, {
            "type": "heartbeat_ack",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"server_time": datetime.now(timezone.utc).isoformat()}
        })
    
    else:
        await _connection_manager.send_personal(client_id, {
            "type": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"error": f"Unknown message type: {msg_type}"}
        })


def broadcast_task_event(event_type: str, task_data: Dict[str, Any]):
    """Broadcast task event to subscribers"""
    asyncio.create_task(_connection_manager.broadcast("tasks", {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": task_data
    }))


def broadcast_agent_event(event_type: str, agent_data: Dict[str, Any]):
    """Broadcast agent event to subscribers"""
    asyncio.create_task(_connection_manager.broadcast("agents", {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": agent_data
    }))


def broadcast_alert(alert_data: Dict[str, Any]):
    """Broadcast alert to subscribers"""
    asyncio.create_task(_connection_manager.broadcast("alerts", {
        "type": "alert_fired",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": alert_data
    }))


def broadcast_metrics(metrics: Dict[str, Any]):
    """Broadcast metrics update"""
    asyncio.create_task(_connection_manager.broadcast("metrics", {
        "type": "metrics_update",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": metrics
    }))


def broadcast_system_status(status: Dict[str, Any]):
    """Broadcast system status"""
    asyncio.create_task(_connection_manager.broadcast("system", {
        "type": "system_status",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": status
    }))


def create_websocket_app() -> FastAPI:
    """Create FastAPI app with WebSocket endpoints"""
    app = FastAPI(
        title="Swarm WebSocket API",
        description="Real-time WebSocket API for Swarm",
        version="3.0.0"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.websocket("/ws")
    async def websocket_route(websocket: WebSocket, client_id: Optional[str] = None):
        await websocket_endpoint(websocket, client_id)
    
    @app.get("/ws/stats")
    async def ws_stats():
        return _connection_manager.get_stats()
    
    return app


if __name__ == "__main__":
    import uvicorn
    app = create_websocket_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)