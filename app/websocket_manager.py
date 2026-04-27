from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, process_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.setdefault(process_id, []).append(websocket)

    def disconnect(self, process_id: str, websocket: WebSocket) -> None:
        connections = self.active_connections.get(process_id, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self.active_connections.pop(process_id, None)

    async def broadcast(self, process_id: str, message: dict) -> None:
        for websocket in self.active_connections.get(process_id, []):
            await websocket.send_json(message)


manager = ConnectionManager()
