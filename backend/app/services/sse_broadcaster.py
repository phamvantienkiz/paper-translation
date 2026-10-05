import asyncio
import json
from typing import AsyncGenerator, Dict, Set
from app.core.logging import logger


class SSEBroadcaster:
    """In-memory event hub for Server-Sent Events (SSE)."""

    def __init__(self):
        # session_id -> Set of asyncio.Queue
        self._listeners: Dict[str, Set[asyncio.Queue]] = {}

    def add_listener(self, session_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        if session_id not in self._listeners:
            self._listeners[session_id] = set()
        self._listeners[session_id].add(q)
        return q

    def remove_listener(self, session_id: str, q: asyncio.Queue) -> None:
        if session_id in self._listeners:
            self._listeners[session_id].discard(q)
            if not self._listeners[session_id]:
                del self._listeners[session_id]

    async def emit(self, session_id: str, event: str, data: dict) -> None:
        if session_id in self._listeners:
            payload = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            for q in list(self._listeners[session_id]):
                await q.put(payload)

    async def subscribe(self, session_id: str) -> AsyncGenerator[str, None]:
        q = self.add_listener(session_id)
        try:
            # Yield initial connection confirmation
            initial_msg = f"event: connected\ndata: {json.dumps({'session_id': session_id, 'status': 'connected'})}\n\n"
            yield initial_msg

            while True:
                payload = await q.get()
                yield payload
        except asyncio.CancelledError:
            pass
        finally:
            self.remove_listener(session_id, q)


broadcaster = SSEBroadcaster()
