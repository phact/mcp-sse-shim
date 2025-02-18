# mcp-sse-shim

Allows you to connect to an sse mcp server via stdio

Run:

    uvx mcp-sse-shim

Optionally set these env vars:

```
MCP_HOST = os.getenv("MCP_HOST", "http://localhost:7860")
BASE_URL = f"{MCP_HOST}"
BACKEND_URL_SSE = f"{BASE_URL}/api/v1/mcp/sse"
BACKEND_URL_MSG = f"{BASE_URL}/api/v1/mcp/"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
```
