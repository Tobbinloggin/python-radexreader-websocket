import asyncio
import json
import websockets
from radexreader import RadexReader

PORT = 8765
clients = set()

async def broadcast_data():
    reader = RadexReader()
    prev = None
    while True:
        try:
            measures = reader.read(True)  # Read new radiation data
            if not measures:
                print("[Broadcast] Warning: No data received from RadexReader.")
                continue  # Skip this loop iteration
            
            for timestamp, measure in measures.items():
                if timestamp != prev:
                    data = json.dumps({timestamp: measure})
                    await send_to_all_clients(data)
                    prev = timestamp
        except Exception as e:
            print(f"[Broadcast] Error reading or sending data: {e}")
        await asyncio.sleep(10)

async def send_to_all_clients(data):
    # Create a list of coroutines for sending data to each client
    coroutines = []
    for client in list(clients):
        try:
            coroutines.append(client.send(data))
        except Exception as e:
            print(f"[Send] Error scheduling send for client, removing client: {e}")
            clients.discard(client)
    if coroutines:
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        # Remove clients if sending fails
        for client, result in zip(list(clients), results):
            if isinstance(result, Exception):
                print(f"[Send] Client send error: {result}. Removing client.")
                clients.discard(client)

async def client_handler(websocket):
    print("Client connected.")
    clients.add(websocket)
    try:
        # In a read-only server, we don't expect messages from clients.
        # However, we'll keep the connection open and listen in case of pings or unexpected messages.
        while True:
            try:
                message = await websocket.recv()
                # Optionally log or ignore messages
                print(f"[Client] Received a message (ignored): {message}")
            except websockets.exceptions.ConnectionClosedOK:
                print("Client closed connection gracefully.")
                break
            except websockets.exceptions.ConnectionClosedError as e:
                print(f"Client connection closed with error: {e}")
                break
            except Exception as e:
                print(f"[Client] Error receiving message: {e}")
                break
    except Exception as e:
        print(f"[Client] Unhandled client handler error: {e}")
    finally:
        print("Client disconnected.")
        clients.discard(websocket)

async def main():
    try:
        server = await websockets.serve(
            client_handler, "0.0.0.0", PORT, ping_interval=20, ping_timeout=20
        )
        print(f"WebSocket server running on ws://0.0.0.0:{PORT}")
        await broadcast_data()  # This will run indefinitely
    except Exception as e:
        print(f"[Server] Error starting or during server operation: {e}")
    finally:
        # Attempt to close any open client connections gracefully.
        for client in clients:
            await client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[Fatal] Unhandled exception in main: {e}")
