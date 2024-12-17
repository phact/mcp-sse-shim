import os
import sys
import asyncio
import traceback
import aiohttp
from datetime import datetime

MCP_HOST = os.getenv("MCP_HOST", "http://localhost:7860")
BASE_URL = f"{MCP_HOST}"
BACKEND_URL_SSE = f"{BASE_URL}/api/v1/mcp/sse"
BACKEND_URL_MSG = f"{BASE_URL}/api/v1/mcp/"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Add message queue at the top with other globals
message_queue = []
message_endpoint = None

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def debug(message):
    """Output debug messages to stderr with timestamps."""
    if DEBUG:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"[{timestamp}] {message}", file=sys.stderr)

async def connect_sse_backend():
    """Establish persistent SSE connection to MCP server."""
    global message_endpoint
    try:
        async with aiohttp.ClientSession() as session:
            debug(f"SSE: Connecting to {BACKEND_URL_SSE}")
            async with session.get(BACKEND_URL_SSE) as response:
                if response.status != 200:
                    raise Exception(f"SSE: Connection failed with status {response.status}")

                debug("SSE: Connected successfully")

                # Read and process SSE messages
                async for line in response.content:
                    if line:
                        message = line.decode().strip()
                        debug(f"SSE <<< {message}")
                        
                        if message.startswith("event: endpoint"):
                            continue
                        elif message.startswith("data: ") and message_endpoint is None:
                            endpoint = message[6:]
                            message_endpoint = f"{BASE_URL}{endpoint}"
                            debug(f"SSE: Message endpoint set to: {message_endpoint}")
                            
                            # Process any queued messages
                            if message_queue:
                                debug(f"QUEUE: Processing {len(message_queue)} queued messages")
                                for queued_message in message_queue:
                                    await process_message(session, queued_message)
                                message_queue.clear()
                        elif message.startswith("data: "):
                            response_data = message[6:]
                            debug(f"SSE >>> {response_data}")
                            print(response_data, flush=True)
    except Exception as e:
        debug(f"--- SSE backend disc./error: {str(e)}")
        raise


async def process_message(session, message):
    """Forward received message to the MCP server."""
    if not message_endpoint:
        debug(f"QUEUE: Message queued (no endpoint): {message}")
        message_queue.append(message)
        return
        
    debug(f"MSG >>> {message.strip()}")
    try:
        async with session.post(message_endpoint, data=message, headers={"Content-Type": "application/json"}) as resp:
            debug(f"MSG <<< Status: {resp.status}")
            if resp.status != 202:
                debug(f"MSG <<< Error: Unexpected status {resp.status}")
    except Exception as e:
        debug(f"MSG <<< Error: {e}")
        debug(f"Full exception: {traceback.format_exc()}")

async def run_bridge():
    """Run the bridge."""
    try:
        # Start the SSE connection in a background task
        asyncio.create_task(connect_sse_backend())

        async with aiohttp.ClientSession() as session:
            debug("-- MCP stdio to SSE gw running")

            # Read stdin synchronously using a ThreadPoolExecutor
            loop = asyncio.get_running_loop()

            def read_stdin_sync():
                return sys.stdin.read()

            while True:
                # Read a line synchronously from stdin
                message = await loop.run_in_executor(None, sys.stdin.readline)
                if not message:  # End of input
                    break
                await process_message(session, message.strip())
    except Exception as error:
        debug(f"Fatal error running server: {error}")
        trace = traceback.format_exc()
        debug(f"Traceback: {trace}")
        sys.exit(1)

def app():
    asyncio.run(run_bridge())

if __name__ == "__main__":
    asyncio.run(app())

