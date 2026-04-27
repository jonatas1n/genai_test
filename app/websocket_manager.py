import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, process_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.setdefault(process_id, []).append(websocket)
        logger.info(
            "WebSocket connected for process '%s'. Active connections: %d.",
            process_id,
            len(self.active_connections[process_id]),
        )

    def disconnect(self, process_id: str, websocket: WebSocket) -> None:
        connections = self.active_connections.get(process_id, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self.active_connections.pop(process_id, None)
        logger.info("WebSocket disconnected for process '%s'.", process_id)

    async def broadcast(self, process_id: str, message: dict) -> None:
        targets = self.active_connections.get(process_id, [])
        if not targets:
            return
        logger.debug(
            "Broadcasting to %d connection(s) for process '%s'.",
            len(targets),
            process_id,
        )
        for websocket in targets:
            await websocket.send_json(message)


manager = ConnectionManager()
