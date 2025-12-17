# Claude Desktop MCP - Quick Start (2 Minutes)

## What's Happening

Claude connects to your MCP server. Server says "requires auth". Claude opens browser for Google login. User logs in once. Claude stores token. Everything works automatically after that.

## Install & Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the MCP Server
```bash
python mcp_oauth_server.py
```

This starts at `http://localhost:8001`

### 3. Auto-Configure Claude
```bash
python setup_claude_mcp.py
```

This automatically:
- Finds your Claude Desktop config
- Adds the MCP server
- Verifies everything works

### 4. Restart Claude Desktop

Close and reopen Claude Desktop.

### 5. Use It

Ask Claude to use any expense tool:
- "List my expenses"
- "Create a new expense for $50 at Target"
- "Show my mileage logs"

**First time only**: You'll see an "Authenticate" button → Click it → Google login → Done!

## Environment Setup

Make sure your `.env` has:
```bash
GOOGLE_CLIENT_ID=your-id-here
GOOGLE_CLIENT_SECRET=your-secret-here
JWT_SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://...
```

## What Gets Created

✅ Claude config file (if needed)
✅ MCP OAuth endpoints
✅ Google login flow
✅ Token storage
✅ Auto-refresh on expiry

## How It Works (30 seconds)

1. **Claude** → "I need expenses data"
2. **Server** → "401 Unauthorized - go to /oauth/authorize"
3. **Claude** → Opens browser to `/oauth/authorize`
4. **Browser** → Redirects to Google login
5. **User** → Signs in with Google
6. **Server** → Gets JWT token
7. **Claude** → Receives token, stores it
8. **Future requests** → Include token, no more auth needed

## Testing

### Health Check
```bash
curl http://localhost:8001/health
```

### Check Metadata
```bash
curl http://localhost:8001/.well-known/mcp.json
```

### List Tools (need valid JWT)
```bash
TOKEN="your-jwt-token"
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/mcp/tools
```

## Troubleshooting

### MCP server not found in Claude
→ Run `python setup_claude_mcp.py` again
→ Restart Claude Desktop completely
→ Check Claude's console for errors

### Getting auth errors
→ Make sure backend is running (`python main.py`)
→ Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are correct
→ Check JWT_SECRET_KEY is set

### Token not working
→ Re-authenticate (tokens expire after 7 days)
→ Or manually set a new token

## Files Created

- `mcp_oauth_server.py` - Main OAuth server
- `setup_claude_mcp.py` - Auto-configuration script
- `start_mcp_server.sh` - Quick start script
- `CLAUDE_DESKTOP_SETUP.md` - Full documentation

## What Each Endpoint Does

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `/.well-known/mcp.json` | OAuth discovery | None |
| `/oauth/authorize` | Start Google login | None |
| `/oauth/callback` | Handle Google response | None |
| `/oauth/token` | Get access token | OAuth code |
| `/mcp/tools` | List available tools | JWT Token |
| `/mcp/tools/call` | Execute a tool | JWT Token |
| `/health` | Server status | None |

## Security

✅ OAuth 2.0 with PKCE
✅ JWT tokens with 7-day expiry
✅ Google account validation
✅ CORS restricted
✅ Token revocation support
✅ No credentials stored in files

## Deploy to Production

Change these in `.env`:
```bash
MCP_SERVER_URL=https://expenses.arlint.dev/mcp-oauth
BACKEND_URL=https://expenses.arlint.dev
```

Then in Claude config:
```json
{
  "mcpServers": {
    "expenses": {
      "command": "python3",
      "args": ["-m", "fastmcp"],
      "env": {
        "FASTMCP_URL": "https://expenses.arlint.dev/mcp-oauth/mcp",
        "FASTMCP_AUTH_TYPE": "oauth",
        "FASTMCP_METADATA_URI": "https://expenses.arlint.dev/mcp-oauth/.well-known/mcp.json"
      }
    }
  }
}
```

---

**That's it!** You now have a fully OAuth-secured MCP server that integrates seamlessly with Claude Desktop.
