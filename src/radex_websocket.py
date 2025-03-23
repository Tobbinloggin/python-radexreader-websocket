import os
import asyncio
import json
import datetime
import websockets
from radexreader import RadexReader
from influxdb_client import InfluxDBClient, Point, WriteOptions

PORT = 8765
clients = set()

# InfluxDB Configuration
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "your-influxdb-token")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "your-org")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "bucket-name")

# Initialize InfluxDB client
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api(write_options=WriteOptions(batch_size=1))

async def save_to_influxdb(timestamp, measure):
    """Save radiation data to InfluxDB."""
    try:
        point = Point("radiation") \
            .time(datetime.datetime.fromtimestamp(timestamp, datetime.UTC)) \
            .field("pct", measure["pct"]) \
            .field("min", measure["min"]) \
            .field("val", measure["val"]) \
            .field("max", measure["max"]) \
            .field("acc", measure["acc"]) \
            .field("cpm", measure["cpm"])

        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
        print(f"[InfluxDB] Saved data: {timestamp} -> {measure}")

    except Exception as e:
        print(f"[InfluxDB] Error writing to database: {e}")

async def broadcast_data():
    reader = RadexReader()
    prev = None
    while True:
        try:
            measures = reader.read(True)  # Read new radiation data
            for timestamp, measure in measures.items():
                if timestamp != prev:
                    data = json.dumps({timestamp: measure})
                    
                    # Create and track tasks for error handling
                    send_task = asyncio.create_task(send_to_all_clients(data))
                    influx_task = asyncio.create_task(save_to_influxdb(timestamp, measure))

                    # Monitor task completion to catch failures
                    send_task.add_done_callback(handle_task_error)
                    influx_task.add_done_callback(handle_task_error)
                    
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

def handle_task_error(task):
    """Callback to handle failed tasks created with asyncio.create_task."""
    try:
        result = task.result()  # This will raise an exception if the task failed
    except Exception as e:
        print(f"[Task Error] Task failed: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[Fatal] Unhandled exception in main: {e}")
