import os
import sys
import asyncio
import aiohttp
from datetime import datetime

MCP_HOST = os.getenv("MCP_HOST", "localhost")
MCP_PORT = os.getenv("MCP_PORT", "3000")
BASE_URL = f"http://{MCP_HOST}:{MCP_PORT}"
BACKEND_URL_SSE = f"{BASE_URL}/api/v1/mcp/sse"
BACKEND_URL_MSG = f"{BASE_URL}/api/v1/mcp/"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_FILE = os.getenv("LOG_FILE", "shim.log")

def debug(message):
    """Output debug messages to log file."""
    if DEBUG:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        try:
            with open(LOG_FILE, "a") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"Error writing to log file: {e}", file=sys.stderr)

async def connect_sse_backend():
    """Establish persistent SSE connection to MCP server."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(BACKEND_URL_SSE) as response:
                if response.status != 200:
                    raise Exception(f"SSE connection failed with status {response.status}")

                debug("--- SSE backend connected")

                # Read and process SSE messages
                async for line in response.content:
                    if line:  # Non-empty lines are SSE messages
                        message = line.decode().strip()
                        debug(f"<-- {message}")
                        print(message)  # Forward to Claude Desktop App via stdio
    except Exception as e:
        debug(f"--- SSE backend disc./error: {str(e)}")
        raise

async def process_message(session, message):
    """Forward received message to the MCP server."""
    debug(f"-->{message.strip()}")
    try:
        async with session.post(BACKEND_URL_MSG, data=message, headers={"Content-Type": "application/json"}) as resp:
            if resp.status != 202:
                debug(f"Unexpected response status: {resp.status}")
    except Exception as e:
        debug(f"fetch error: {e}")

async def run_bridge():
    """Run the bridge."""
    try:
        # Start the SSE connection in a background task
        asyncio.create_task(connect_sse_backend())

        async with aiohttp.ClientSession() as session:
            debug("-- MCP stdio to SSE gw running")

            # Listen to stdin and forward messages
            loop = asyncio.get_running_loop()
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            await loop.connect_read_pipe(lambda: protocol, sys.stdin)

            while not reader.at_eof():
                message = await reader.readline()
                if message:
                    await process_message(session, message.decode().strip())
    except Exception as error:
        debug(f"Fatal error running server: {error}")
        sys.exit(1)

def app():
    asyncio.run(run_bridge())

if __name__ == "__main__":
    asyncio.run(app())

