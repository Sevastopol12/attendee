import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from database.helper import insert_data, attended_count
from typing import List, Dict, Any

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


class Clients:
    def __init__(self):
        self.active_clients: List[WebSocket] = []

    async def add_client(self, websocket: WebSocket):
        self.active_clients.append(websocket)
        attended: List[Dict[str, Any]] = attended_count()
        await websocket.send_json(attended)

    async def broadcast_db(self):
        attended: List[Dict[str, Any]] = attended_count()
        async for client in self.active_clients:
            await client.send_json(attended)

    async def update_db(self, payload: json):
        """Insert new record to DB and broadcast changes"""
        await insert_data(data=payload)
        await self.broadcast_db()

    def remove_client(self, websocket: WebSocket):
        if websocket in self.active_clients:
            self.active_clients.remove(websocket)


connected_clients = Clients()


@app.websocket("/presence")
async def presence(websocket: WebSocket):
    await websocket.accept()
    await connected_clients.add_client(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Validate data format
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text("Invalid JSON format")
                continue

            if not all(k in payload for k in ("seat", "name")):
                await websocket.send_text("Missing required keys: seat, name")
                continue

            await connected_clients.update_db(payload=payload)

    except WebSocketDisconnect:
        connected_clients.remove_client(websocket)

    except Exception:
        connected_clients.remove_client(websocket)
        try:
            await websocket.close()
        except Exception:
            pass
