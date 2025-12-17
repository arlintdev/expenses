from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.responses import JSONResponse
import json
import structlog
from typing import Optional
from auth import get_current_user
from models import User

logger = structlog.get_logger(__name__)

class MCPIntegration:
    def __init__(self, app: FastAPI):
        self.app = app
        self.setup_mcp_routes()

    def setup_mcp_routes(self):
        @self.app.post("/mcp/message")
        async def mcp_message_handler(
            payload: dict,
            current_user: User = Depends(get_current_user)
        ):
            try:
                from mcp_server import UserContext, server

                user_context = UserContext(
                    user_id=current_user.id,
                    email=current_user.email
                )

                request = payload.get("request", {})
                method = request.get("method")

                if method == "tools/list":
                    tools = await server.list_tools()
                    return {
                        "result": {
                            "tools": tools
                        }
                    }

                elif method == "tools/call":
                    tool_name = request.get("params", {}).get("name")
                    arguments = request.get("params", {}).get("arguments", {})

                    result = await server.handle_tool_call(
                        tool_name,
                        arguments,
                        user_context
                    )

                    return {
                        "result": json.loads(result) if isinstance(result, str) else result
                    }

                else:
                    return {
                        "error": f"Unknown MCP method: {method}"
                    }

            except Exception as e:
                logger.error("mcp_handler_error", error=str(e), exc_info=True)
                return {
                    "error": f"MCP handler error: {str(e)}"
                }

        @self.app.get("/mcp/tools")
        async def get_mcp_tools(current_user: User = Depends(get_current_user)):
            try:
                from mcp_server import server
                tools = await server.list_tools()
                return {"tools": tools}
            except Exception as e:
                logger.error("get_mcp_tools_error", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )

        @self.app.post("/mcp/tools/{tool_name}")
        async def call_mcp_tool(
            tool_name: str,
            arguments: dict,
            current_user: User = Depends(get_current_user)
        ):
            try:
                from mcp_server import UserContext, server

                user_context = UserContext(
                    user_id=current_user.id,
                    email=current_user.email
                )

                result = await server.handle_tool_call(
                    tool_name,
                    arguments,
                    user_context
                )

                return json.loads(result) if isinstance(result, str) else result

            except Exception as e:
                logger.error("call_mcp_tool_error", tool=tool_name, error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
