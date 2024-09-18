"""Simple broadcaster for websockets on webserver backend"""

import logging
from typing import Any
from fastapi import WebSocket


class WSPubManager:
    """Implementation of websocket data publication manager"""

    def __init__(self):
        logging.info("Init WebSocket Pub Manager instance")
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Connects new client to the manager"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info("WSPubManager new client. (Total: %s)", self.nclients)
        return

    def disconnect(self, websocket: WebSocket):
        """Turns off a client from the manager"""
        self.active_connections.remove(websocket)
        logging.info("WSPubManager drop client. (Total: %s)", self.nclients)
        return

    async def broadcast(self, msg_json: Any):
        """Broadcasts the json message to all clients"""
        if self.nclients > 0:
            logging.info("WSPubManager broadcast message (%s)", self.nclients)
        for connection in self.active_connections:
            await connection.send_json(msg_json)
        return

    @property
    def nclients(self):
        """Returns a number of connected clients"""
        return len(self.active_connections)
