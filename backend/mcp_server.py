from fastmcp import FastMCP
from tools import search_music, find_similar, build_playlist, explain_vibe

# Initialize the FastMCP server
mcp = FastMCP("VibeMap")

@mcp.tool()
def search(query: str) -> list:
    """Find songs by vibe in your Spotify history."""
    return search_music(query)

@mcp.tool()
def similar(track_id: str) -> list:
    """Find songs similar to a specific track ID."""
    return find_similar(track_id)

@mcp.tool()
def playlist(vibe: str) -> list:
    """Build a playlist based on a specific vibe."""
    return build_playlist(vibe)

@mcp.tool()
def explain(tracks: list[str] = None) -> str:
    """Explain why songs match a certain vibe or cluster together."""
    return explain_vibe(tracks or [])

if __name__ == "__main__":
    import sys
    # Example usage: run over stdio for local model clients 
    # Can also be hosted over SSE `mcp.run(transport='sse')`
    mcp.run()
