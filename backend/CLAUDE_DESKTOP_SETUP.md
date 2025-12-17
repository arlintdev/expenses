# Claude Desktop MCP Setup Guide

This guide walks through setting up the Expenses MCP server with Claude Desktop using OAuth 2.1 authentication.

## What You Get

✅ **One-Click Authentication** - Sign in once, Claude has access forever
✅ **OAuth 2.1 with PKCE** - Enterprise-grade security
✅ **Automatic Token Refresh** - Never deal with expired tokens
✅ **Metadata Discovery** - Claude auto-discovers available tools
✅ **Works Offline** - OAuth tokens cached locally

## Prerequisites

- Claude Desktop (2025 or later)
- Python 3.9+
- Backend running: `python main.py`
- `.env` file configured with:
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
  - `JWT_SECRET_KEY`
  - `DATABASE_URL`

## Quick Setup (2 minutes)

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Run the MCP OAuth Server

In a new terminal:

```bash
python mcp_oauth_server.py
```

This starts the OAuth server on `http://localhost:8001`

### 3. Run the Setup Script

```bash
python setup_claude_mcp.py
```

This will:
- Detect your OS
- Create/update Claude Desktop config
- Add the Expenses MCP server
- Verify everything is working

### 4. Restart Claude Desktop

Close and reopen Claude Desktop. The Expenses MCP server should now be available.

### 5. Authenticate

In Claude, the first time you use an Expenses tool:
1. You'll see an "Authenticate" prompt
2. Click it → Google OAuth login screen appears
3. Sign in with your Google account
4. Claude automatically gets access

That's it! No more copying/pasting tokens.

## Manual Setup (If automatic setup fails)

### Step 1: Find Claude Config File

**macOS:**
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Linux:**
```bash
~/.config/Claude/claude_desktop_config.json
```

### Step 2: Edit Config File

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "expenses": {
      "command": "python3",
      "args": ["-m", "fastmcp"],
      "env": {
        "FASTMCP_URL": "http://localhost:8001/mcp",
        "FASTMCP_AUTH_TYPE": "oauth",
        "FASTMCP_METADATA_URI": "http://localhost:8001/.well-known/mcp.json"
      }
    }
  }
}
```

### Step 3: Restart Claude Desktop

Close and reopen the application.

## Architecture

### OAuth 2.0 Flow

```
1. Claude Desktop connects to MCP Server
   ┌──────────────┐
   │ Claude       │
   │ Desktop      │
   └──────┬───────┘
          │ 1. Connect to http://localhost:8001
          │
          ▼
   ┌──────────────────────────┐
   │ /.well-known/mcp.json    │ ← Metadata discovery
   │ Returns OAuth endpoints  │
   └──────┬───────────────────┘
          │
          │ 2. No token? Requires auth
          │
          ▼
   ┌──────────────────────────┐
   │ /oauth/authorize?        │ ← Claude opens browser
   │ client_id=...            │
   │ redirect_uri=...         │
   │ state=...                │
   └──────┬───────────────────┘
          │ 3. Redirects to Google
          │
          ▼
   ┌──────────────────────────┐
   │ Google OAuth Login       │ ← User sees consent screen
   │ accounts.google.com      │   and logs in
   └──────┬───────────────────┘
          │
          │ 4. Google redirects back
          │
          ▼
   ┌──────────────────────────┐
   │ /oauth/callback          │ ← Backend exchanges code
   │ code=...                 │   for JWT token
   │ auth_id=...              │
   └──────┬───────────────────┘
          │
          │ 5. Redirects to Claude
          │    with token
          │
          ▼
   ┌──────────────────────────┐
   │ Claude Desktop           │ ← Stores token locally
   │ Token saved!             │   Future requests
   └──────────────────────────┘
```

### MCP Server Components

```
mcp_oauth_server.py
├── OAuth Endpoints
│   ├─ /.well-known/mcp.json      (Metadata discovery)
│   ├─ /mcp/oauth/authorize        (OAuth flow initiation)
│   ├─ /mcp/oauth/token            (Token exchange)
│   └─ /mcp/oauth/callback         (OAuth callback)
├── MCP Tools Endpoint
│   ├─ /mcp/tools                  (List available tools)
│   └─ /mcp/tools/call             (Call specific tool)
└── Utilities
    └─ /health                     (Server health check)
```

## Environment Variables

For production deployment, set these:

```bash
# Backend API
BACKEND_URL=https://expenses.arlint.dev
MCP_SERVER_URL=https://expenses.arlint.dev/mcp

# OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
JWT_SECRET_KEY=your-jwt-secret

# Database
DATABASE_URL=postgresql://user:pass@localhost/expenses
```

## Token Management

### Token Storage

Tokens are stored locally:
- **macOS:** `~/Library/Application Support/Claude/mcp-auth.json`
- **Windows:** `%APPDATA%\Claude\mcp-auth.json`
- **Linux:** `~/.config/Claude/mcp-auth.json`

### Token Lifetime

- **Access Token:** 7 days
- **Refresh:** Automatic before expiry
- **Revoke:** Re-authenticate or manually delete local storage

### Token Refresh

The OAuth server supports refresh tokens for long-lived access. Claude Desktop handles this automatically.

## Troubleshooting

### "MCP Server not responding"

1. Verify MCP server is running:
   ```bash
   curl http://localhost:8001/health
   ```

2. Check environment variables:
   ```bash
   echo $GOOGLE_CLIENT_ID
   echo $GOOGLE_CLIENT_SECRET
   ```

3. Check logs:
   ```bash
   # In the terminal where mcp_oauth_server.py is running
   # Look for error messages
   ```

### "Authentication failed"

1. Verify Google OAuth credentials are correct in `.env`
2. Check callback URL matches: `http://localhost:8001/mcp/oauth/callback`
3. Ensure network connectivity to `accounts.google.com`

### "Claude doesn't see the MCP server"

1. Run setup script again:
   ```bash
   python setup_claude_mcp.py
   ```

2. Verify config file exists at the right location
3. Restart Claude Desktop completely (not just switching windows)

### "Token is expired"

Claude will automatically refresh tokens. If issues persist:

1. Sign out and back in (delete cached tokens)
2. Authenticate again

## Production Deployment

### 1. Configure Environment

```bash
export BACKEND_URL=https://expenses.arlint.dev
export MCP_SERVER_URL=https://expenses.arlint.dev/mcp-oauth
export GOOGLE_CLIENT_ID=xxx
export GOOGLE_CLIENT_SECRET=yyy
export JWT_SECRET_KEY=zzz
```

### 2. Run MCP Server

```bash
python mcp_oauth_server.py --host 0.0.0.0 --port 8001
```

### 3. Update Claude Config

For production URLs:
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

### 4. CORS & Security

The MCP server includes:
- CORS headers for Claude.ai and Claude Desktop
- HTTPS enforcement in production
- OAuth 2.1 PKCE protection
- JWT token validation

## Advanced: Using FastMCP CLI

You can also use FastMCP's CLI to test the server:

```bash
# Install FastMCP CLI
pip install fastmcp

# Test connection
fastmcp http://localhost:8001/mcp --auth "your-jwt-token"

# List tools
fastmcp inspect http://localhost:8001/mcp
```

## Support

For issues or questions:
1. Check logs: `python mcp_oauth_server.py` output
2. Test manually: `curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/mcp/tools`
3. Verify OAuth: `curl http://localhost:8001/.well-known/mcp.json`

## Security Best Practices

✅ **Do:**
- Use HTTPS in production
- Keep JWT_SECRET_KEY secure
- Rotate Google OAuth credentials periodically
- Monitor access logs
- Use environment variables for secrets

❌ **Don't:**
- Commit secrets to git
- Share JWT tokens
- Expose OAuth callback URL
- Use the same credentials across environments

## References

- [MCP Protocol Spec](https://modelcontextprotocol.io/)
- [OAuth 2.1 PKCE](https://datatracker.ietf.org/doc/html/rfc7636)
- [Claude Desktop Extensions](https://support.claude.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers)
- [FastMCP Documentation](https://gofastmcp.com/)
