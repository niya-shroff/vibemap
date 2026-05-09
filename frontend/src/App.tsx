import { useEffect, useRef, useState } from "react";
import type { Message } from "./types";

const API_BASE = import.meta.env.DEV ? "http://localhost:8000" : "";

/** Remove `[title]()` / broken markdown links with no URL (model glitches). */
function stripEmptyMarkdownLinks(raw: string): string {
  return raw
    .replace(/\[([^\]]+)\]\(\s*\n*\s*\)/g, "$1")
    .replace(/\[([^\]]+)\]\(\s*$/gm, "$1");
}

/** Same playlist/track/album linked twice → keep first URL only. */
function dedupeSpotifyLinksInText(raw: string): string {
  const seen = new Set<string>();
  const re =
    /https:\/\/open\.spotify\.com\/(playlist|track|album)\/([a-zA-Z0-9]+)(?:\?[^\s)\]}>"']*)?/g;
  const collapsed = raw.replace(re, (full, type: string, id: string) => {
    const key = `${type}/${id}`;
    if (seen.has(key)) {
      return "";
    }
    seen.add(key);
    return full;
  });
  return collapsed
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/  +/g, " ")
    .trim();
}

function polishDisplayText(raw: string): string {
  return dedupeSpotifyLinksInText(stripEmptyMarkdownLinks(raw.trim()));
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>("");
  const [isReady, setIsReady] = useState<boolean>(false);
  /** Pinned ids for follow-up turns only; backend prefers fresh build ids in the same request. */
  const [lastSpotifyTrackIds, setLastSpotifyTrackIds] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    if (params.get("auth") === "true") {
      setMessages((prev) => [
        ...prev,
        {
          type: "system",
          text: "Signed in with Spotify. Sync your library to begin.",
        },
      ]);

      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  function formatMessage(text: string | object) {
    if (typeof text === "object") {
      return (
        <pre style={{ fontFamily: "monospace", fontSize: "0.85rem", margin: 0 }}>
          {JSON.stringify(text, null, 2)}
        </pre>
      );
    }

    const normalized = polishDisplayText(text);
    const parts = normalized.split(
      /https:\/\/open\.spotify\.com\/(track|album|playlist)\/([a-zA-Z0-9]+)/g
    );

    if (parts.length === 1) {
      return <span className="msg-body-text">{normalized}</span>;
    }

    const result: React.ReactNode[] = [];
    const seenEmbedKeys = new Set<string>();

    for (let i = 0; i < parts.length; i++) {
      if (i % 3 === 0) {
        if (parts[i]) {
          result.push(
            <span key={`txt-${i}`} className="msg-body-text">
              {parts[i]}
            </span>
          );
        }
      } else if (i % 3 === 1) {
        const type = parts[i];
        const id = parts[i + 1];
        const embedKey = `${type}/${id}`;
        i += 1;

        if (seenEmbedKeys.has(embedKey)) {
          continue;
        }
        seenEmbedKeys.add(embedKey);

        result.push(
          <div key={`${embedKey}-${i}`} className="embed-wrap">
            <iframe
              title={`Spotify ${type}`}
              src={`https://open.spotify.com/embed/${type}/${id}`}
              width="100%"
              height="152"
              style={{ border: 0 }}
              allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
              loading="lazy"
            />
          </div>
        );
      }
    }

    return <>{result}</>;
  }

  async function handleLogin(): Promise<void> {
    window.location.href = `${API_BASE}/login`;
  }

  async function handleIngest(): Promise<void> {
    setMessages((prev) => [
      ...prev,
      { type: "system", text: "Syncing your top tracks and saved music…" },
    ]);

    try {
      const res = await fetch(`${API_BASE}/ingest`);
      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          type: "system",
          text: `Ready — ${data.result.ingested} tracks indexed for vibe search.`,
        },
      ]);

      setIsReady(true);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { type: "system", text: `Sync failed: ${err.message}` },
      ]);
    }
  }

  async function handleSend(): Promise<void> {
    const q: string = input.trim();
    if (!q) return;

    setMessages((prev) => [...prev, { type: "user", text: q }]);
    setInput("");

    try {
      const chatHistory = messages
        .filter((m) => m.type !== "system")
        .map((m) => ({
          role: m.type === "user" ? "user" : "assistant",
          content: typeof m.text === "string" ? m.text : "",
        }));
      chatHistory.push({ role: "user", content: q });

      const payload: Record<string, unknown> = { messages: chatHistory };
      if (lastSpotifyTrackIds.length > 0) {
        payload.last_spotify_track_ids = lastSpotifyTrackIds;
      }

      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (Array.isArray(data.spotify_track_ids) && data.spotify_track_ids.length > 0) {
        setLastSpotifyTrackIds(data.spotify_track_ids);
      }

      let agentText: string = data.response ?? "";
      if (typeof data.spotify_playlist_url === "string" && data.spotify_playlist_url) {
        const url = data.spotify_playlist_url.trim();
        const urlBase = url.replace(/\?.*$/, "");
        if (url && !agentText.includes(urlBase)) {
          agentText = agentText ? `${agentText}\n\n${url}` : url;
        }
      }
      agentText = polishDisplayText(agentText);

      setMessages((prev) => [...prev, { type: "agent", text: agentText }]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { type: "agent", text: `Something went wrong: ${err.message}` },
      ]);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <h1 className="brand-mark">VibeMap</h1>
          <p className="brand-tagline">
            Turn your Spotify library into playlists by vibe — one conversation, real playlists on
            your account.
          </p>
        </div>
      </header>

      <div className="toolbar">
        <button type="button" className="btn btn-ghost" onClick={handleLogin}>
          Connect Spotify
        </button>
        <button type="button" className="btn btn-ghost" onClick={handleIngest}>
          Sync library
        </button>
        <span className={`status-pill ${isReady ? "ready" : ""}`}>
          <span className="status-dot" aria-hidden />
          {isReady ? "Library ready" : "Sync to chat"}
        </span>
      </div>

      <div className="chat-panel">
        <div className="chat-scroll" ref={scrollRef}>
          {messages.map((msg, i) => (
            <div key={i} className={`msg msg-${msg.type}`}>
              {formatMessage(msg.text)}
            </div>
          ))}
        </div>

        <div className="composer">
          <input
            type="text"
            value={input}
            placeholder={
              isReady ? "Describe a mood, a name, or ask for a saved playlist…" : "Sync your library first…"
            }
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            disabled={!isReady}
            aria-label="Message"
          />
          <button type="button" className="btn btn-primary" onClick={handleSend} disabled={!isReady}>
            Send
          </button>
        </div>
      </div>

      <p className="footer-hint">Tip: name a playlist in your message to build and save in one step.</p>
    </div>
  );
}
