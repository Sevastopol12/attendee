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


@app.websocket("/presence")
async def presence(websocket: WebSocket):
    await websocket.accept()
    print("✅ WebSocket connected")

    try:
        while True:
            data = await websocket.receive_text()
            print("📩 Received:", data)
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text("Invalid JSON format")
                continue

            if not all(k in payload for k in ("seat", "name")):
                await websocket.send_text("Missing required keys: seat, name")
                continue

            insert_data(data=payload)

            await websocket.send_text(f"✔ Saved data for seat {payload['seat']}")

    except Exception as e:
        print("⚠ Unexpected error:", e)
        try:
            await websocket.close()
        except Exception:
            pass


@app.websocket("/attend")
async def attended(websocket: WebSocket):
    await websocket.connect()
    try:
        while True:
            attended: List[Dict[str, Any]] = attended_count()
            websocket.send_json(data=attended)
    except Exception as e:
        print("⚠ Unexpected error:", e)
        try:
            await websocket.close()
        except Exception:
            pass
