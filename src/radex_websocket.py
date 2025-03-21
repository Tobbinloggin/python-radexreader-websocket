import asyncio
import json
import time
import datetime
import websockets
from radexreader import RadexReader

PORT = 8765  # WebSocket server port

async def broadcast_data(websocket, path):
    reader = RadexReader()
    prev = None
    while True:
        measures = reader.read(True)  # Read new radiation data
        for timestamp, measure in measures.items():
            if timestamp != prev:
                data = json.dumps({timestamp: measure})
                await websocket.send(data)  # Send to connected clients
                prev = timestamp
        await asyncio.sleep(10)  # Delay before reading again

async def main():
    server = websockets.serve(broadcast_data, "0.0.0.0", PORT)

    print(f"WebSocket server running on ws://0.0.0.0:{PORT}")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
