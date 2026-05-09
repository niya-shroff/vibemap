"""
Structured types for the LLM tool layer and /chat API.

Tool argument models validate JSON the model emits before any Spotify or vector calls.
"""

from __future__ import annotations

from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


SpotifyTrackId = Annotated[
    str,
    Field(
        min_length=22,
        max_length=22,
        pattern=r"^[0-9A-Za-z]{22}$",
        description="Exact Spotify track id from a prior tool result (22 base62 chars).",
    ),
]


class SearchVibeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    vibe_description: str = Field(..., min_length=1, max_length=2000)


class SearchSpotifyGlobalArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(..., min_length=1, max_length=500)


class BuildPlaylistArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    vibe_description: str = Field(..., min_length=1, max_length=2000)


class ExportPhysicalPlaylistArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    playlist_name: str = Field(..., min_length=1, max_length=300)
    spotify_ids: List[SpotifyTrackId] = Field(
        default_factory=list,
        max_length=100,
        description=(
            "Spotify ids from the latest search_vibe/build_playlist/search_spotify_global tool payload in THIS "
            "request, or [] so the server fills them from that search for you."
        ),
    )


class ExplainVibeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


def tool_schema_parameters(model: type[BaseModel]) -> dict:
    """JSON Schema object for OpenAI-style `function.parameters` (no wrapper)."""
    schema = model.model_json_schema()
    schema.pop("title", None)
    return schema


class AgentOutput(BaseModel):
    """Structured agent completion for one /chat invocation."""

    response: str = Field(..., description="Assistant text shown in the UI.")
    spotify_track_ids: Optional[List[str]] = Field(
        default=None,
        description="Canonical ids from the last search/build (or last successful export) in this request.",
    )
    spotify_playlist_url: Optional[str] = Field(
        default=None,
        description="Set when export_physical_playlist succeeded in this request.",
    )


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    role: Literal["user", "assistant", "system"]
    content: str = Field(default="", max_length=50000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    messages: List[ChatMessage] = Field(..., min_length=1)
    last_spotify_track_ids: Optional[List[SpotifyTrackId]] = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    response: str
    spotify_track_ids: Optional[List[str]] = None
    spotify_playlist_url: Optional[str] = None
