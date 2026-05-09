"""
In-request agent memory for Spotify track ids and exported playlist URLs.

Replaces ad-hoc variables so export fallbacks and /chat JSON stay aligned without LangChain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

_SEARCH_TOOLS = frozenset({"build_playlist", "search_vibe", "search_spotify_global"})


def extract_track_ids_from_search_result(fn_name: str, result: Any) -> Optional[List[str]]:
    """Parse spotify_id list from a search_vibe / build_playlist / search_spotify_global tool result."""
    if fn_name not in _SEARCH_TOOLS:
        return None
    if not isinstance(result, list):
        return None
    out: List[str] = []
    for item in result:
        if isinstance(item, dict) and item.get("spotify_id"):
            out.append(str(item["spotify_id"]))
    return out or None


@dataclass
class PlaylistAgentState:
    """
    Canonical ids from the latest successful library/global search in this HTTP request.
    After a successful export, ids match what was sent to Spotify and ``spotify_playlist_url`` is set.
    """

    canonical_track_ids: Optional[List[str]] = field(default=None)
    spotify_playlist_url: Optional[str] = field(default=None)

    def absorb_search_tool(self, fn_name: str, result: Any) -> None:
        ids = extract_track_ids_from_search_result(fn_name, result)
        if ids:
            self.canonical_track_ids = ids

    def absorb_export_success(self, tool_return: Any, exported_track_ids: List[str]) -> None:
        """Call after export_physical_playlist returns successfully."""
        self.canonical_track_ids = list(exported_track_ids)
        if isinstance(tool_return, str) and tool_return.startswith("https://open.spotify.com/playlist/"):
            self.spotify_playlist_url = tool_return

    def ids_for_export_fallback(self) -> Optional[List[str]]:
        return self.canonical_track_ids
