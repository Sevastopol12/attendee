import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from database.helper import create_schema_and_table, insert_data
from contextlib import asynccontextmanager
from utils.management_sys import connected_clients


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On start-up
    tasks = [
        # Create schem & tables
        asyncio.create_task(create_schema_and_table()),
        # Fetch data on initial
        asyncio.create_task(connected_clients.fetch_db()),
        # Establish real-time connection with Supabase
        asyncio.create_task(connected_clients.establish_connection()),
    ]
    await asyncio.gather(*tasks, return_exceptions=True)

    yield

    # On end
    tasks = [
        # Disconnect from the channel
        asyncio.create_task(connected_clients.unsubscribe_channel()),
        asyncio.create_task(
            connected_clients.remove_client(connected_clients.active_clients)
        ),
    ]

    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(lifespan=lifespan)


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


# Server websocket APIs
@app.websocket("/presence")
async def ws_endpoint(ws_client: WebSocket):
    await ws_client.accept()
    await connected_clients.add_client(ws_client=ws_client)
    print("WebSocket connected")

    while True:
        try:
            attendee_info: str = await ws_client.receive_text()
            print(f"Received: {attendee_info}")
            info_payload = json.loads(attendee_info)

            if not all(k in info_payload for k in ("seat", "name")):
                await ws_client.send_text("Missing required keys: seat, name")
                continue

            # Insert data
            status: bool = await insert_data(payload=info_payload)
            if not status:
                # If already presented, no broadcast needed
                continue

        except (WebSocketDisconnect, Exception) as e:
            print(e)
            await connected_clients.remove_client(ws_client=ws_client)
            print(f"{ws_client} disconnected")
            break
