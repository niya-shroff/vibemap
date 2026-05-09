from __future__ import annotations

import json
import re
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

MAX_LLM_ROUNDS = 14
EXPORT_CONTINUATION_NUDGES_MAX = 4

EXPORT_PHYSICAL_NUDGE = """
Follow-up REQUIRED for this SAME request: You already executed build_playlist or search_* and received track rows with spotify_id, but you stopped before export_physical_playlist.
The user message asks you to create or persist a Spotify playlist — finish by exporting.

Immediately call export_physical_playlist using:
• playlist_name: the title/name from the user message (quotes or ‘called …’ / named …).
• spotify_ids: [] (server binds the fresh track ids from the search/build you just ran THIS request.)

Then briefly confirm once; include ONLY the playlist URL returned from that export tool once.
"""


def _last_user_content(user_messages: list) -> str:
    """Most recent chat user text (conversation history excludes system)."""
    for entry in reversed(user_messages):
        if not isinstance(entry, dict):
            continue
        if entry.get("role") != "user":
            continue
        content = entry.get("content") or ""
        return content.strip() if isinstance(content, str) else str(content).strip()
    return ""


def _user_likely_wants_physical_playlist(user_text: str) -> bool:
    """
    Heuristic: user asked to name/save/publish a Spotify playlist (not vibe-only brainstorming).
    Used to retry when the model finished after search/build without export.
    """
    t = user_text.strip().lower()
    if not t:
        return False
    if "playlist" not in t:
        return False
    if re.search(r"\b(do not|don't|dont)\s+.*?\b(save|export|publish|mak|creat)\b.*?playlist", t):
        return False

    persistence = (
        re.search(r"\b(called|named|title\s+[d']\s*|name\s+it)\b", t),
        re.search(r"\b(save|export|publish)\w*\b.*?playlist\b|\bplaylist\b.*?\b(save|export)\w*\b", t),
        re.search(r"\bplaylist\b.*?\b(on|to|into|in)\s+(spotify|my\s+library|library|account)", t),
        re.search(r"\bspotify\b.*?\bplaylist\b|\bplaylist\b.*?\bspotify\b", t),
        re.search(r"\b(build|mak|creat|want|give\s+me)\w*\s+(?:a\s+)?playlist\b", t),
    )
    return any(bool(p) for p in persistence)


SYSTEM_PROMPT = """
You are VibeMap AI, an advanced semantic natural language music cognition system.
Each request contains ONLY this single user message — there is NO prior chat transcript. Never paste or assume URLs from earlier turns (you cannot see them). Every saved playlist must come from tools you run in THIS request.

When the user asks for a vibe based on their library, use `search_vibe` or `build_playlist`.
When a user asks to search for specific new songs, artists, or globally available music outside of their local context, you MUST use `search_spotify_global`.

ONE-SHOT playlist creation (default when they want it saved):
If the user asks you to build, make, or create a playlist AND gives a playlist title or name (e.g. in quotes, or "called X", "named X") OR they ask to save it to Spotify / their account / library, you MUST complete everything in this single assistant turn without asking for confirmation:
1) Call `build_playlist` with a `vibe_description` that matches their request (mood, genre, count like "5 songs", etc.).
2) Immediately call `export_physical_playlist` with `playlist_name` set to the exact title they asked for (or a clear title you infer from their message) and `spotify_ids: []` so the server fills ids from step 1.
Never skip export_physical_playlist when they asked to save or name a playlist in this message.
Do not tell the user to ask again to save, and do not ask them for Spotify track ids.
If they only want suggestions or a draft with no mention of saving or naming a playlist, skip export and only search/build.

CRITICAL — saving to Spotify:
If the user asks to save, create, or export a real playlist, you MUST use `export_physical_playlist`.
You MUST NOT guess, invent, or fabricate Spotify track IDs. Every `spotify_id` in `export_physical_playlist` must be copied EXACTLY from the `spotify_id` field in a tool message you already received from `search_vibe`, `build_playlist`, or `search_spotify_global` in this same HTTP request OR use `spotify_ids: []` when you just invoked build/search earlier in THIS request cycle (preferred after a fresh build).
After you call `build_playlist` or `search_vibe` (or similar) earlier in THIS request cycle, passing `spotify_ids: []` to `export_physical_playlist`; the server applies the IDs from the latest search/build in this request automatically. Prefer copying IDs from JSON when you omit `[]`.

Final reply:
When export succeeded in THIS request, paste ONLY the playlist URL returned from that export tool once as a plain https://open.spotify.com/playlist/... line. Never use an empty markdown link like [title]( ) or [title]( with the URL missing. Do not repeat the same link twice. Keep the message concise.
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
        (
            "Build a playlist from the user's ingested library using a vibe description "
            "(mood, tempo, '5 songs', etc.). If the latest user message asks to SAVE to Spotify "
            "or NAMES the playlist ('called …', quoted title, etc.), you MUST call export_physical_playlist "
            "in the SAME request cycle AFTER this returns. Each distinct playlist name in the message "
            "needs export_physical_playlist after the matching search/build."
        ),
        BuildPlaylistArgs,
    ),
    (
        "export_physical_playlist",
        (
            "Creates ONE new real Spotify playlist on the user's account. Call when this message asks "
            "to save or name a playlist (after build/search in this request). "
            "Use right after search_vibe/build_playlist/search_spotify_global when they want it saved "
            "(spotify_ids may be []; server binds fresh ids from the latest search/build THIS request)."
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
        # Fresh search/build in THIS request must beat stale pins from the UI (previous turn).
        # Pinned ids apply only when this POST did not populate session (e.g. "save that" alone).
        raw = dict(fn_args) if isinstance(fn_args, dict) else {}
        session_ids = state.ids_for_export_fallback()
        if session_ids:
            raw["spotify_ids"] = session_ids
        elif pinned_spotify_track_ids:
            raw["spotify_ids"] = pinned_spotify_track_ids
        args = ExportPhysicalPlaylistArgs.model_validate(raw)
        exported_ids = list(args.spotify_ids)
        if not exported_ids:
            raise ValueError(
                "export_physical_playlist needs Spotify track ids: run search_vibe, build_playlist, "
                "or search_spotify_global earlier in THIS request cycle, send last_spotify_track_ids "
                "from the UI, or pass explicit spotify_ids from tool JSON."
            )
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

    llm_round = 0
    export_reminder_inj = 0
    user_snapshot = _last_user_content(user_messages)

    while True:
        llm_round += 1
        if llm_round > MAX_LLM_ROUNDS:
            raise Exception("Agent exceeded maximum LLM round budget (possible tool loop).")

        payload = {
            "model": "adamo1139/Hermes-3-Llama-3.1-8B-FP8-Dynamic",
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 1024,
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
            if (
                export_reminder_inj < EXPORT_CONTINUATION_NUDGES_MAX
                and session.canonical_track_ids
                and not session.exported_this_request
                and _user_likely_wants_physical_playlist(user_snapshot)
            ):
                messages.append({"role": "system", "content": EXPORT_PHYSICAL_NUDGE})
                export_reminder_inj += 1
                continue
            out = AgentOutput(
                response=message.get("content") or "",
                spotify_track_ids=session.canonical_track_ids,
                spotify_playlist_url=session.spotify_playlist_url,
            )
            return out.model_dump()
