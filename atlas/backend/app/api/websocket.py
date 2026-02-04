"""
WebSocket Server
Real-time updates for transactions and alerts
Inspired by Deriv's real-time monitoring systems
"""
import json
import asyncio
from typing import Dict, Set
from datetime import datetime
import logging

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter

from app.services.alert_service import get_alert_service

logger = logging.getLogger(__name__)

# Active WebSocket connections
active_connections: Set[WebSocket] = set()

# Connection manager
class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept and store WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)


# Global connection manager
manager = ConnectionManager()

# WebSocket router
ws_router = APIRouter()


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Clients can subscribe to:
    - transactions: Real-time transaction updates
    - alerts: Real-time alert notifications
    - dashboard: Dashboard statistics updates
    """
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        await manager.send_personal_message({
            "type": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to Atlas-AI real-time updates"
        }, websocket)
        
        # Subscribe to updates
        subscriptions = {"transactions": True, "alerts": True, "dashboard": True}
        
        while True:
            # Receive message from client
            try:
                data = await websocket.receive_json()
                
                # Handle subscription changes
                if data.get("type") == "subscribe":
                    subscriptions = {**subscriptions, **data.get("channels", {})}
                    await manager.send_personal_message({
                        "type": "subscription_updated",
                        "subscriptions": subscriptions
                    }, websocket)
                
                # Handle ping
                elif data.get("type") == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }, websocket)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": str(e)
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def broadcast_transaction(transaction_data: dict):
    """
    Broadcast new transaction to all connected clients.
    
    Args:
        transaction_data: Transaction data dictionary
    """
    message = {
        "type": "transaction",
        "data": transaction_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast(message)


async def broadcast_alert(alert_data: dict):
    """
    Broadcast new alert to all connected clients.
    
    Args:
        alert_data: Alert data dictionary
    """
    message = {
        "type": "alert",
        "data": alert_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast(message)


async def broadcast_dashboard_stats(stats: dict):
    """
    Broadcast dashboard statistics update.
    
    Args:
        stats: Dashboard statistics dictionary
    """
    message = {
        "type": "dashboard_stats",
        "data": stats,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast(message)


def get_connection_count() -> int:
    """Get number of active WebSocket connections."""
    return len(manager.active_connections)
