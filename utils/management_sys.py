import asyncio
from copy import copy
from fastapi import WebSocket
from typing import List, Set, Dict, Any
from database.helper import attended_count
from database.connection import connection
from supabase.client import AsyncClient, acreate_client


class Clients:
    def __init__(self):
        self.background_tasks: Set = set()
        self.active_clients: List[WebSocket] = []
        self.attendees: List[Dict[str, Any]] = []
        self.realtime_channel: AsyncClient = None

    async def establish_connection(self):
        """Establish a real-time connection to Supabase"""
        self.realtime_channel: AsyncClient = await acreate_client(
            supabase_url=connection.project_url, supabase_key=connection.key
        )
        # Subscribe to the channel
        await self.subscribe_channel()

    async def subscribe_channel(self):
        await (
            self.realtime_channel.channel(connection.channel)
            .on_postgres_changes(
                "*",
                schema="attendees",
                table="presence",
                callback=(self.schedule),
            )
            .subscribe()
        )
        
    def schedule(self, payload: Dict[str, Any]):
        """ Wraps & execute schedule_broadcast_action correctly as on_prostgres_changes would yields the payload to its callback"""
        print("Realtime event received:", payload["data"]["type"])
        asyncio.create_task(self.schedule_broadcast_action())

    async def unsubscribe_channel(self):
        await self.realtime_channel.remove_channel(connection.channel)

    async def fetch_db(self):
        """Fetch data on initial"""
        self.attendees = await attended_count()

    async def add_client(self, ws_client: WebSocket):
        """Perform handshake with client then give them the current attendee list"""
        self.active_clients.append(ws_client)
        await ws_client.send_json(self.attendees)

    async def schedule_broadcast_action(self):
        """Schedule broadcast to run in background, listen to database broadcast events"""
        task = asyncio.create_task(self.broadcast_db())
        self.background_tasks.add(task)
        task.add_done_callback(lambda task: self.background_tasks.discard(task))

    async def broadcast_db(self):
        """Broadcast changes across clients"""
        async with asyncio.Lock():
            # Re-fetch
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
