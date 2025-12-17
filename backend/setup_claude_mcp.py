#!/usr/bin/env python3
"""
Claude Desktop MCP Setup Script

This script configures Claude Desktop to use the Expenses MCP server with automatic OAuth.
Run this once to set up the integration.

Usage:
    python setup_claude_mcp.py
"""

import os
import json
import sys
import platform
from pathlib import Path

def get_config_path():
    """Get the Claude Desktop config file path based on OS."""
    system = platform.system()

    if system == "Darwin":
        return Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    elif system == "Windows":
        return Path(os.getenv("APPDATA")) / "Claude/claude_desktop_config.json"
    elif system == "Linux":
        return Path.home() / ".config/Claude/claude_desktop_config.json"
    else:
        raise Exception(f"Unsupported OS: {system}")

def get_mcp_server_config():
    """Get the MCP server configuration."""
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001")

    return {
        "expenses": {
            "url": f"{mcp_server_url}/mcp"
        }
    }

def setup_claude_mcp():
    """Set up Claude Desktop MCP configuration."""
    config_path = get_config_path()

    print(f"📝 Claude Desktop MCP Configuration Setup")
    print(f"{'='*60}")
    print(f"Platform: {platform.system()}")
    print(f"Config Path: {config_path}")
    print()

    if not config_path.parent.exists():
        print(f"Creating config directory: {config_path.parent}")
        config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        print(f"Found existing config at {config_path}")
        with open(config_path, "r") as f:
            config = json.load(f)
    else:
        print("Creating new Claude Desktop config")
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    mcp_config = get_mcp_server_config()

    print(f"\n📦 Adding MCP Server Configuration")
    print(f"{'='*60}")

    for server_name, server_config in mcp_config.items():
        print(f"\nServer: {server_name}")
        print(f"  URL: {server_config.get('url')}")
        config["mcpServers"][server_name] = server_config

    print(f"\n💾 Saving configuration to {config_path}")

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✅ Configuration saved successfully!")
    print()
    print(f"🎉 Setup Complete!")
    print(f"{'='*60}")
    print()
    print("Next steps:")
    print("1. Restart Claude Desktop")
    print("2. Start the MCP server: python mcp_oauth_server.py")
    print("3. Open Claude Desktop and the Expenses tools will be available")
    print()
    print("Features:")
    print("✓ OAuth 2.1 with PKCE support")
    print("✓ Automatic token management")
    print("✓ One-click authentication in Claude")
    print("✓ Secure access to all expense features")
    print()

def verify_mcp_server():
    """Verify the MCP server is running."""
    import httpx

    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001")

    try:
        response = httpx.get(f"{mcp_server_url}/health", timeout=2)
        if response.status_code == 200:
            print(f"✅ MCP Server is running at {mcp_server_url}")
            return True
    except Exception:
        print(f"⚠️  MCP Server not found at {mcp_server_url}")
        print(f"   Start it with: python mcp_oauth_server.py")
        return False

    return False

if __name__ == "__main__":
    try:
        print()
        setup_claude_mcp()

        print("Checking MCP Server status...")
        verify_mcp_server()

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
