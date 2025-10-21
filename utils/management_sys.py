import asyncio
from copy import copy
from fastapi import WebSocket
from typing import List, Set, Dict, Any
from database.helper import attended_count


class Clients:
    def __init__(self):
        self.background_tasks: Set = set()
        self.active_clients: List[WebSocket] = []
        self.attendees: List[Dict[str, Any]] = []

    async def fetch_db(self):
        """Fetch data on initial"""
        self.attendees = await attended_count()

    async def add_client(self, ws_client: WebSocket):
        """Perform handshake with client then give them the current attendee list"""
        self.active_clients.append(ws_client)
        await ws_client.send_json(self.attendees)

    async def schedule_broadcast_action(self):
        """Schedule broadcast to run in background"""
        task = asyncio.create_task(self.broadcast_db())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    async def broadcast_db(self):
        """Broadcast changes across clients"""
        await self.fetch_db()
        attendee_snapshot = copy(self.attendees)
        
        send_tasks = [
            asyncio.create_task(client.send_json(attendee_snapshot))
            for client in self.active_clients
        ]

        await asyncio.gather(*send_tasks, return_exceptions=True)

    async def remove_client(self, ws_client: WebSocket):
        if ws_client in self.active_clients:
            self.active_clients.remove(ws_client)


connected_clients: Clients = Clients()
