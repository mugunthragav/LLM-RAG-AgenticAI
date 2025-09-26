import asyncio
import websockets
import json

async def receive_notifications():
    """
    Connects to the WebSocket server and continuously listens for incoming messages.
    Prints raw and parsed JSON messages to the console.
    """
    uri = "ws://127.0.0.1:8000/ws/notifications" # The WebSocket URI of your FastAPI server
    print(f"Attempting to connect to WebSocket at {uri}...")

    try:
        # Establish a persistent WebSocket connection
        async with websockets.connect(uri) as websocket:
            print("Successfully connected to WebSocket.")
            
            try:
                # Loop indefinitely to receive messages
                while True:
                    message = await websocket.recv() # Wait for the next message from the server
                    print(f"\n--- New Message ---")
                    print(f"Raw message received: {message}")
                    
                    try:
                        # Attempt to parse the message as JSON
                        parsed_message = json.loads(message)
                        print("Parsed JSON message:")
                        print(json.dumps(parsed_message, indent=2)) # Pretty print JSON
                    except json.JSONDecodeError:
                        print("Received non-JSON message (could not parse as JSON).")
                    except Exception as parse_error:
                        print(f"An unexpected error occurred during JSON parsing: {parse_error}")

            except websockets.exceptions.ConnectionClosedOK:
                print("WebSocket connection closed normally by the server.")
            except websockets.exceptions.ConnectionClosedError as e:
                print(f"WebSocket connection closed with an error: Code={e.code}, Reason={e.reason}")
            except Exception as e:
                print(f"An unexpected error occurred while receiving messages: {e}")

    except ConnectionRefusedError:
        print("Connection refused. Is the FastAPI server running and accessible at 127.0.0.1:8000?")
        print("Please ensure your FastAPI server is running in a separate terminal: uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
    except Exception as e:
        print(f"Could not establish WebSocket connection: {e}")

if __name__ == "__main__":
    print("Starting Python WebSocket client...")
    # Run the asynchronous receive_notifications function
    asyncio.run(receive_notifications())