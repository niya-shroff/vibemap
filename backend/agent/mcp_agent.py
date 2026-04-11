from google import genai
from google.genai import types
from core.config import *
from tools.registry import TOOLS

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-2.5-flash"

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

def export_physical_playlist(playlist_name: str, spotify_ids: list[str]) -> str:
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

def agent(user_input: str):
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[search_vibe, search_spotify_global, build_playlist, export_physical_playlist, explain_vibe],
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode="AUTO"
            )
        )
    )

    chat = client.chats.create(model=MODEL_ID, config=config)
    
    print(f"[Agent] Converting user query into acoustic floats...")
    response = chat.send_message(user_input)
    
    while response.function_calls:
        # We handle tool calls one batch at a time
        parts = []
        for fn_call in response.function_calls:
            fn_name = fn_call.name
            fn_args = {k: v for k, v in fn_call.args.items()} if fn_call.args else {}
            
            print(f"[Agent] AI mathematically deduced signature: {fn_name}({fn_args})")
            
            if fn_name in TOOLS:
                try:
                    # Execute tool
                    result = TOOLS[fn_name](**fn_args)
                    print(f"[Agent] Retrieved tracks: {len(result) if type(result) == list else 'metadata'}")
                    
                    parts.append(
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"result": result}
                        )
                    )
                except Exception as e:
                    print(f"[Agent] Tool Error: {e}")
                    parts.append(
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"error": str(e)}
                        )
                    )
        
        if parts:
            # Send all tool responses back in one message
            response = chat.send_message(parts)
        else:
            break

    return response.text
