from fastapi import WebSocket
from typing import Dict, Set


class CrewConnectionManager:
    def __init__(self):
        # crew_id -> set of (user_id, websocket)
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, crew_id: str, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if crew_id not in self.active_connections:
            self.active_connections[crew_id] = {}
        self.active_connections[crew_id][user_id] = websocket

    def disconnect(self, crew_id: str, user_id: str):
        if crew_id in self.active_connections:
            self.active_connections[crew_id].pop(user_id, None)
            if not self.active_connections[crew_id]:
                self.active_connections.pop(crew_id)

    async def broadcast(self, crew_id: str, message: dict, exclude_user_id: str = None):
        if crew_id in self.active_connections:
            for user_id, ws in self.active_connections[crew_id].items():
                if user_id != exclude_user_id:
                    await ws.send_json(message)


crew_manager = CrewConnectionManager()
