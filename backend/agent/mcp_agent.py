import json
import requests
from core.config import *
from tools.registry import TOOLS

SYSTEM_PROMPT = """
You are VibeMap AI, an advanced semantic natural language music cognition system.
When the user asks for a vibe based on their library, use `search_vibe` or `build_playlist`.
When a user asks to search for specific new songs, artists, or globally available music outside of their local context, you MUST use `search_spotify_global`.

CRITICAL: If the user explicitly asks to "save", "create", or "make it a real playlist", you MUST use the `export_physical_playlist` tool.
First, run a search to retrieve the data IDs. Take the resulting `spotify_id`s and pass them into `export_physical_playlist` with a creative name to write it permanently into their Spotify account.
"""

def search_vibe(vibe_description: str) -> list:
    """Find similar songs in the user's vector space by a text description."""
    return TOOLS["search_vibe"](vibe_description)

def search_spotify_global(query: str) -> list:
    """Search Spotify's global catalog directly by query like 'lofi hip hop' or 'drake'."""
    return TOOLS["search_spotify_global"](query)

def build_playlist(vibe_description: str) -> list:
    """Build a playlist."""
    return TOOLS["build_playlist"](vibe_description)

def export_physical_playlist(playlist_name: str, spotify_ids: list) -> str:
    """Creates a real Spotify playlist. Pass a name and a list of Spotify IDs."""
    cleaned = []
    for item in spotify_ids:
        if isinstance(item, dict):
            cleaned.append(item.get("spotify_id") or item.get("id", ""))
        else:
            cleaned.append(str(item))
            
    cleaned = [c for c in cleaned if c]
    return TOOLS["export_physical_playlist"](playlist_name, cleaned)

def explain_vibe() -> str:
    """Explain why the user likes these songs."""
    return TOOLS["explain_vibe"]([])

def agent(user_messages: list):
    print(f"[Agent] Processing conversation with history length {len(user_messages)}...")
    
    url = "https://hermes.ai.unturf.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer choose-any-value"
    }
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_vibe",
                "description": "Find similar songs in the user's vector space by a text description.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "vibe_description": {"type": "string"}
                    },
                    "required": ["vibe_description"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_spotify_global",
                "description": "Search Spotify's global catalog directly by query like 'lofi hip hop' or 'drake'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "build_playlist",
                "description": "Build a playlist.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "vibe_description": {"type": "string"}
                    },
                    "required": ["vibe_description"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "export_physical_playlist",
                "description": "Creates a real Spotify playlist. Pass a name and a list of Spotify IDs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "playlist_name": {"type": "string"},
                        "spotify_ids": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["playlist_name", "spotify_ids"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "explain_vibe",
                "description": "Explain why the user likes these songs.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_messages
    
    while True:
        payload = {
            "model": "adamo1139/Hermes-3-Llama-3.1-8B-FP8-Dynamic",
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 500,
            "tools": tools,
            "tool_choice": "auto"
        }
        
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"Failed to communicate with LLM: {response.text}")
            
        data = response.json()
        message = data["choices"][0]["message"]
        
        if message.get("tool_calls"):
            messages.append(message)
            for tool_call in message["tool_calls"]:
                fn_name = tool_call["function"]["name"]
                fn_args = json.loads(tool_call["function"]["arguments"])
                print(f"[Agent] AI mathematically deduced signature: {fn_name}({fn_args})")
                
                result = None
                try:
                    if fn_name == "search_vibe":
                        result = search_vibe(**fn_args)
                    elif fn_name == "search_spotify_global":
                        result = search_spotify_global(**fn_args)
                    elif fn_name == "build_playlist":
                        result = build_playlist(**fn_args)
                    elif fn_name == "export_physical_playlist":
                        result = export_physical_playlist(**fn_args)
                    elif fn_name == "explain_vibe":
                        result = explain_vibe()
                    else:
                        result = f"Unknown tool: {fn_name}"
                except Exception as e:
                    print(f"[Agent] Tool Error: {e}")
                    result = str(e)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": fn_name,
                    "content": json.dumps(result)
                })
        else:
            return message.get("content", "")
