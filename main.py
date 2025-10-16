import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from database.helper import insert_data, attended_count, create_schema_and_table
from typing import List, Dict, Any


create_schema_and_table()


app = FastAPI()

# Allow both frontend URLs
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://9000-firebase-attendance-1760419902082.cluster-yylgzpipxrar4v4a72liastuqy.cloudworkstations.dev",
        "https://attendance-7t4e.onrender.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Management system
class Clients:
    def __init__(self):
        self.active_clients: List[WebSocket] = []
        self.attendees: List[Dict[str, Any]] = attended_count()

    async def add_client(self, ws_client: WebSocket):
        """Perform handshake with client then give them the current attendee list"""
        self.active_clients.append(ws_client)
        await ws_client.send_json(self.attendees)

    async def broadcast_db(self):
        """Broadcast changes"""
        self.attendees = attended_count()
        for client in self.active_clients:
            await client.send_json(self.attendees)

    async def remove_client(self, ws_client: WebSocket):
        if ws_client in self.active_clients:
            self.active_clients.remove(ws_client)


connected_clients: Clients = Clients()


# Server websocket APIs
@app.websocket("/presence")
async def ws_endpoint(ws_client: WebSocket):
    await ws_client.accept()
    await connected_clients.add_client(ws_client=ws_client)
    print("WebSocket connected")

    while True:
        try:
            attendee_info: json = await ws_client.receive_text()
            print(f"Received: {attendee_info}")
            info_payload = json.loads(attendee_info)

            if not all(k in info_payload for k in ("seat", "name")):
                await ws_client.send_text("Missing required keys: seat, name")
                continue

            # Insert data
            status: bool = insert_data(data=info_payload)
            if not status:
                # If already presented, no broadcast needed
                continue

            await connected_clients.broadcast_db()

        except (WebSocketDisconnect, Exception) as e:
            print(e)
            await connected_clients.remove_client(ws_client=ws_client)
            print(f"{ws_client} disconnected")
            break
