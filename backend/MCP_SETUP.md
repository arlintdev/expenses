# MCP (Model Context Protocol) Integration Setup

## Overview

This expenses application now includes MCP server integration, allowing AI agents (like Claude) to interact with your expense tracking system through the Model Context Protocol.

## What is MCP?

The Model Context Protocol (MCP) is a standardized way for AI models to securely interact with applications and data sources. This integration allows Claude and other AI assistants to:
- List and search your expenses
- Create new expenses
- Delete expenses
- Manage mileage logs and vehicle records
- Work with tags and categories
- Get financial summaries and deductions

## Installation

1. **FastMCP Dependency**
   The `fastmcp>=2.0.0` library has been added to `requirements.txt`. Install it:
   ```bash
   pip install -r requirements.txt
   ```

## MCP Components

### Files Created

1. **`mcp_server.py`** - Core MCP server implementation
   - Defines all available MCP tools
   - Implements tool handlers with async/await
   - Manages database queries and operations
   - Handles authentication context

2. **`mcp_integration.py`** - FastAPI MCP route integration
   - Exposes MCP endpoints in FastAPI
   - Handles user authentication via JWT
   - Routes MCP requests to the server

### Main Integration

Modified `main.py` to:
- Import `MCPIntegration`
- Initialize MCP routes on app startup

## Available MCP Tools

### Expense Management
- **`list_expenses`** - List all user expenses with optional date filtering
- **`create_expense`** - Create a new expense record
- **`delete_expense`** - Delete an expense by ID

### Vehicle & Mileage
- **`list_vehicles`** - List registered vehicles
- **`create_vehicle`** - Register a new vehicle
- **`list_mileage_logs`** - List business mileage trips
- **`create_mileage_log`** - Log a new business trip
- **`delete_mileage_log`** - Delete a mileage log

### Tags & Organization
- **`list_tags`** - List all custom tags
- **`create_tag`** - Create a new tag

### Analytics
- **`get_expense_summary`** - Get expense statistics (total, count, average)
- **`get_mileage_deduction`** - Calculate tax deductible mileage amounts

## API Endpoints

The MCP integration exposes the following REST endpoints:

### List Available Tools
```
GET /mcp/tools
Authorization: Bearer <jwt_token>
```

Response:
```json
{
  "tools": [
    {
      "name": "list_expenses",
      "description": "...",
      "inputSchema": { ... }
    },
    ...
  ]
}
```

### Call a Tool
```
POST /mcp/tools/{tool_name}
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "argument1": "value1",
  "argument2": "value2"
}
```

### Generic MCP Message Handler
```
POST /mcp/message
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "request": {
    "method": "tools/list" | "tools/call",
    "params": {
      "name": "tool_name",
      "arguments": { ... }
    }
  }
}
```

## Authentication

All MCP endpoints require authentication via JWT Bearer token:

1. Get JWT token from `/api/auth/google` endpoint
2. Include in all MCP requests: `Authorization: Bearer <token>`
3. User context is automatically extracted and used for data filtering

## Usage Examples

### Using with Claude
Claude can automatically discover and use these MCP tools when configured properly. The tools will:
- Only show data for the authenticated user
- Enforce proper authorization
- Handle errors gracefully

### Using cURL
```bash
# Get tools list
curl -H "Authorization: Bearer $TOKEN" \
  https://expenses.arlint.dev/mcp/tools

# Create an expense
curl -X POST https://expenses.arlint.dev/mcp/tools/create_expense \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Office supplies",
    "recipient": "Staples",
    "amount": 45.99,
    "tags": ["office"]
  }'
```

## Security Considerations

1. **User Isolation**: All operations are scoped to the authenticated user
2. **JWT Validation**: Every request validates the JWT token
3. **Google OAuth**: Leverages existing Google OAuth security
4. **Rate Limiting**: Not yet implemented (can be added via middleware)
5. **Input Validation**: Pydantic schemas validate all inputs

## Error Handling

MCP tools return JSON responses with error information:

```json
{
  "error": "Descriptive error message"
}
```

## Logging

All MCP operations are logged using structlog:
- Tool invocations are tracked
- Database operations are timed
- Errors include full context

## Deployment

### Production Deployment

1. Ensure FastMCP is installed in production environment
2. MCP endpoints are available at `/mcp/*` paths
3. Keep JWT_SECRET_KEY and GOOGLE_CLIENT_ID secure
4. Monitor logs for MCP errors and usage

### Domain Setup

The application is hosted at `expenses.arlint.dev`. MCP endpoints are available at:
- `https://expenses.arlint.dev/mcp/tools`
- `https://expenses.arlint.dev/mcp/tools/{tool_name}`
- `https://expenses.arlint.dev/mcp/message`

## Future Enhancements

Potential improvements to the MCP integration:

1. **Rate Limiting** - Add per-user request rate limits
2. **Tool Pagination** - Support pagination for large result sets
3. **Caching** - Cache frequently accessed data
4. **Advanced Filtering** - More sophisticated query options
5. **Streaming Responses** - Stream large result sets
6. **Webhooks** - Real-time notifications for changes
7. **Batch Operations** - Bulk create/update/delete
8. **Advanced Analytics** - More detailed financial reports

## Troubleshooting

### FastMCP Import Error
If you get "ModuleNotFoundError: No module named 'fastmcp'":
```bash
pip install fastmcp>=2.0.0
```

### Authentication Failed
- Verify JWT token is valid
- Check token not expired (7-day lifetime)
- Ensure Authorization header format: `Bearer <token>`

### Tool Not Found
- Verify tool name matches exactly (case-sensitive)
- Check `/mcp/tools` endpoint to see available tools

### Database Connection Issues
- Verify DATABASE_URL is set correctly
- Check PostgreSQL/SQLite availability
- Review logs for connection errors

## Documentation References

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://gofastmcp.com/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Pydantic Validation](https://docs.pydantic.dev/latest/)
