import asyncio
import json
import websockets
from radexreader import RadexReader

PORT = 8765  # WebSocket server port
clients = set()  # Track connected clients

async def broadcast_data():
    """Continuously reads data and broadcasts it to all clients"""
    reader = RadexReader()
    prev = None
    while True:
        measures = reader.read(True)  # Read new radiation data
        for timestamp, measure in measures.items():
            if timestamp != prev:
                data = json.dumps({timestamp: measure})
                await send_to_all_clients(data)  # Send to all connected clients
                prev = timestamp
        await asyncio.sleep(10)  # Delay before reading again

async def send_to_all_clients(data):
    """Sends data to all connected WebSocket clients"""
    if clients:
        await asyncio.gather(*(client.send(data) for client in clients))

async def client_handler(websocket, path):
    """Handles new WebSocket connections"""
    clients.add(websocket)
    try:
        await websocket.wait_closed()  # Keep connection open until closed by client
    finally:
        clients.remove(websocket)  # Remove disconnected clients

async def main():
    """Starts WebSocket server and background data broadcasting"""
    server = await websockets.serve(client_handler, "0.0.0.0", PORT)
    print(f"WebSocket server running on ws://0.0.0.0:{PORT}")

    # Start broadcasting loop
    await broadcast_data()

if __name__ == "__main__":
    asyncio.run(main())
