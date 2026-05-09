from __future__ import annotations

import json
import requests
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError

from core.config import *
from tools.registry import TOOLS

from agent.schemas import (
    AgentOutput,
    BuildPlaylistArgs,
    ExplainVibeArgs,
    ExportPhysicalPlaylistArgs,
    SearchSpotifyGlobalArgs,
    SearchVibeArgs,
    tool_schema_parameters,
)
from agent.session_state import PlaylistAgentState

SYSTEM_PROMPT = """
You are VibeMap AI, an advanced semantic natural language music cognition system.
When the user asks for a vibe based on their library, use `search_vibe` or `build_playlist`.
When a user asks to search for specific new songs, artists, or globally available music outside of their local context, you MUST use `search_spotify_global`.

CRITICAL — saving to Spotify:
If the user asks to save, create, or export a real playlist, you MUST use `export_physical_playlist`.
You MUST NOT guess, invent, or fabricate Spotify track IDs. Every `spotify_id` in `export_physical_playlist` must be copied EXACTLY from the `spotify_id` field in a tool message you already received from `search_vibe`, `build_playlist`, or `search_spotify_global` in this same conversation.
If you do not have those tool results in context, call `search_vibe` or `build_playlist` (or `search_spotify_global`) again first, then export using only IDs from that fresh result.
After you call `build_playlist` or `search_vibe` in the same turn, you may pass `spotify_ids: []` to `export_physical_playlist`; the server applies the IDs from that search automatically. Prefer copying the IDs from the tool JSON when you can.
"""

_TOOL_SPECS: List[tuple[str, str, Type[BaseModel]]] = [
    (
        "search_vibe",
        "Find similar songs in the user's vector space by a text description.",
        SearchVibeArgs,
    ),
    (
        "search_spotify_global",
        "Search Spotify's global catalog directly by query like 'lofi hip hop' or 'drake'.",
        SearchSpotifyGlobalArgs,
    ),
    (
        "build_playlist",
        "Build a playlist from the user's ingested library using a vibe description.",
        BuildPlaylistArgs,
    ),
    (
        "export_physical_playlist",
        (
            "Creates a real Spotify playlist on the user's account. spotify_ids must be the exact "
            "spotify_id strings from a prior search_vibe, build_playlist, or search_spotify_global "
            "tool result in this chat — never placeholder or invented IDs."
        ),
        ExportPhysicalPlaylistArgs,
    ),
    (
        "explain_vibe",
        "Explain why the user likes these songs.",
        ExplainVibeArgs,
    ),
]


def _openai_tools() -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": tool_schema_parameters(model),
            },
        }
        for name, desc, model in _TOOL_SPECS
    ]


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


def _run_tool(
    fn_name: str,
    fn_args: Dict[str, Any],
    pinned_spotify_track_ids: Optional[List[str]],
    state: PlaylistAgentState,
) -> Any:
    if fn_name == "search_vibe":
        args = SearchVibeArgs.model_validate(fn_args)
        return search_vibe(**args.model_dump())

    if fn_name == "search_spotify_global":
        args = SearchSpotifyGlobalArgs.model_validate(fn_args)
        return search_spotify_global(**args.model_dump())

    if fn_name == "build_playlist":
        args = BuildPlaylistArgs.model_validate(fn_args)
        return build_playlist(**args.model_dump())

    if fn_name == "export_physical_playlist":
        # Pinned ids (multi-turn UI) > LLM args > ids from a prior search/build in this chat (same
        # request batch or earlier assistant tool step). The model often omits spotify_ids or sends [].
        raw = dict(fn_args) if isinstance(fn_args, dict) else {}
        if pinned_spotify_track_ids:
            raw = {**raw, "spotify_ids": pinned_spotify_track_ids}
        else:
            ids = raw.get("spotify_ids")
            fallback = state.ids_for_export_fallback()
            if not ids and fallback:
                raw = {**raw, "spotify_ids": fallback}
        args = ExportPhysicalPlaylistArgs.model_validate(raw)
        exported_ids = list(args.spotify_ids)
        out = export_physical_playlist(args.playlist_name, exported_ids)
        state.absorb_export_success(out, exported_ids)
        return out

    if fn_name == "explain_vibe":
        ExplainVibeArgs.model_validate(fn_args if isinstance(fn_args, dict) else {})
        return explain_vibe()

    return f"Unknown tool: {fn_name}"


def agent(
    user_messages: list,
    pinned_spotify_track_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    print(f"[Agent] Processing conversation with history length {len(user_messages)}...")
    session = PlaylistAgentState()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if pinned_spotify_track_ids:
        messages.append(
            {
                "role": "system",
                "content": (
                    "The user already ran a library or Spotify search in the UI; the canonical Spotify track IDs for that "
                    "result are listed below. When calling export_physical_playlist, you MUST use this exact list and order — "
                    "do not invent, alter, or substitute any character: "
                    + json.dumps(pinned_spotify_track_ids)
                ),
            }
        )
    messages.extend(user_messages)

    url = "https://hermes.ai.unturf.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer choose-any-value",
    }

    tools = _openai_tools()

    while True:
        payload = {
            "model": "adamo1139/Hermes-3-Llama-3.1-8B-FP8-Dynamic",
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 500,
            "tools": tools,
            "tool_choice": "auto",
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
                raw_args = tool_call["function"].get("arguments") or "{}"
                try:
                    fn_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError as e:
                    print(f"[Agent] Tool JSON decode error: {e}")
                    result = json.dumps(
                        {
                            "error": "invalid_tool_arguments_json",
                            "message": str(e),
                            "raw": raw_args[:500],
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": fn_name,
                            "content": result,
                        }
                    )
                    continue

                print(f"[Agent] AI mathematically deduced signature: {fn_name}({fn_args})")

                try:
                    result = _run_tool(
                        fn_name,
                        fn_args,
                        pinned_spotify_track_ids,
                        session,
                    )
                except ValidationError as e:
                    print(f"[Agent] Tool validation error: {e}")
                    result = json.dumps(
                        {
                            "error": "invalid_tool_arguments",
                            "tool": fn_name,
                            "detail": e.errors(),
                        }
                    )
                except Exception as e:
                    print(f"[Agent] Tool Error: {e}")
                    result = str(e)

                session.absorb_search_tool(fn_name, result)

                serializable = result
                if not isinstance(result, str):
                    serializable = json.dumps(result)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": fn_name,
                        "content": serializable,
                    }
                )
        else:
            out = AgentOutput(
                response=message.get("content") or "",
                spotify_track_ids=session.canonical_track_ids,
                spotify_playlist_url=session.spotify_playlist_url,
            )
            return out.model_dump()
