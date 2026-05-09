import { useEffect, useState } from "react";
import type { Message } from "./types";

const API_BASE = import.meta.env.DEV ? "http://localhost:8000" : "";

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>("");
  const [isReady, setIsReady] = useState<boolean>(false);
  /** Canonical IDs from the last build/search turn; sent on follow-up so export is not hallucinated. */
  const [lastSpotifyTrackIds, setLastSpotifyTrackIds] = useState<string[]>([]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    if (params.get("auth") === "true") {
      setMessages((prev) => [
        ...prev,
        {
          type: "system",
          text: "Authentication secured. You may now Sync Memory.",
        },
      ]);

      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  function formatMessage(text: string | object) {
    if (typeof text === "object") {
      return (
        <pre style={{ fontFamily: "monospace", fontSize: "0.85rem" }}>
          {JSON.stringify(text, null, 2)}
        </pre>
      );
    }

    const parts = text.split(
      /https:\/\/open\.spotify\.com\/(track|album|playlist)\/([a-zA-Z0-9]+)/g
    );

    if (parts.length === 1) return text;

    const result: React.ReactNode[] = [];

    for (let i = 0; i < parts.length; i++) {
      if (i % 3 === 0) {
        result.push(parts[i]);
      } else if (i % 3 === 1) {
        const type = parts[i];
        const id = parts[i + 1];

        result.push(
          <div key={i}>
            <iframe
              style={{ borderRadius: 12, marginTop: 10, marginBottom: 10 }}
              src={`https://open.spotify.com/embed/${type}/${id}`}
              width="100%"
              height="152"
              frameBorder={0}
              allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
              loading="lazy"
            />
          </div>
        );

        i += 1;
      }
    }

    return result;
  }

  async function handleLogin(): Promise<void> {
    window.location.href = `${API_BASE}/login`;
  }

  async function handleIngest(): Promise<void> {
    setMessages((prev) => [
      ...prev,
      { type: "system", text: "Initializing ingestion sequence..." },
    ]);

    try {
      const res = await fetch(`${API_BASE}/ingest`);
      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          type: "system",
          text: `Ingested ${data.result.ingested} tracks into memory.`,
        },
      ]);

      setIsReady(true);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { type: "system", text: `Error: ${err.message}` },
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
        .filter(m => m.type !== "system")
        .map(m => ({ role: m.type === 'user' ? 'user' : 'assistant', content: m.text }));
      chatHistory.push({ role: 'user', content: q });

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
        agentText = agentText
          ? `${agentText}\n\n${data.spotify_playlist_url}`
          : data.spotify_playlist_url;
      }

      setMessages((prev) => [
        ...prev,
        { type: "agent", text: agentText },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { type: "agent", text: `Error: ${err.message}` },
      ]);
    }
  }

  return (
    <div className="container">
      <header>
        <h1>VibeMap</h1>
        <p>AI Cognitive Playlist Engine</p>
      </header>

      <div className="controls">
        <button className="btn btn-secondary" onClick={handleLogin}>
          Login
        </button>

        <button className="btn btn-secondary" onClick={handleIngest}>
          Ingest Memory
        </button>
      </div>

      <div className="chat-container">
        <div className="chat-history">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.type}-msg`}>
              {formatMessage(msg.text)}
            </div>
          ))}
        </div>

        <div className="input-group">
          <input
            type="text"
            value={input}
            placeholder="Ask your vibe..."
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            disabled={!isReady}
          />

          <button className="btn" onClick={handleSend} disabled={!isReady}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}