
const API_BASE = "http://localhost:8000";

const chatHistory = document.getElementById('chatHistory');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const loginBtn = document.getElementById('loginBtn');
const ingestBtn = document.getElementById('ingestBtn');

window.onload = () => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('auth') === 'true') {
        const sysMsg = document.querySelector('.message.system');
        if (sysMsg) {
            sysMsg.textContent = "Authentication secured. You may now Sync Memory.";
        }
        window.history.replaceState({}, document.title, window.location.pathname);
    }
};

function appendMessage(text, type) {
    const div = document.createElement('div');
    div.className = `message ${type}-msg`;
    
    if (typeof text === 'object') {
        const pre = document.createElement('pre');
        pre.style.fontFamily = "monospace";
        pre.style.fontSize = "0.85rem";
        pre.textContent = JSON.stringify(text, null, 2);
        div.appendChild(pre);
    } else {
        // Parse Spotify open URLs into stunning iFrames and add Share APIs!
        let htmlText = text.replace(
            /https:\/\/open\.spotify\.com\/(track|album|playlist)\/([a-zA-Z0-9]+)/g, 
            `
            <iframe style="border-radius:12px; margin-top: 10px; margin-bottom: 10px;" src="https://open.spotify.com/embed/$1/$2?utm_source=generator" width="100%" height="152" frameBorder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>
            <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                <a href="sms:?&body=Check%20out%20my%20AI%20curated%20Cognitive%20Playlist:%20https://open.spotify.com/$1/$2" class="action-btn">📱 Text Playlist</a>
                <a href="mailto:?subject=VibeMap%20AI%20Playlist&body=Check%20out%20my%20AI%20curated%20Cognitive%20Playlist:%20https://open.spotify.com/$1/$2" class="action-btn">✉️ Email</a>
            </div>
            `
        );
        div.innerHTML = htmlText;
    }
    
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

loginBtn.addEventListener('click', () => {
    window.location.href = `${API_BASE}/login`;
});

ingestBtn.addEventListener('click', async () => {
    appendMessage("Initializing ingestion sequence...", "system");
    console.log("[VibeMap UI] Triggering memory ingestion sync...");
    try {
        const res = await fetch(`${API_BASE}/ingest`);
        const data = await res.json();
        console.log("[VibeMap UI] Ingestion Payload:", data);
        appendMessage(`Ingested ${data.result.ingested} tracks into Qdrant memory.`, "system");
        
        chatInput.disabled = false;
        sendBtn.disabled = false;
    } catch (err) {
        console.error("[VibeMap UI] Ingestion Error:", err);
        appendMessage(`Error: ${err.message}`, "system");
    }
});

sendBtn.addEventListener('click', async () => {
    const q = chatInput.value.trim();
    if (!q) return;
    
    appendMessage(q, "user");
    chatInput.value = "";
    
    console.log(`[VibeMap UI] Transmitting query directly to Agent: "${q}"`);
    try {
        const res = await fetch(`${API_BASE}/chat?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        console.log("[VibeMap UI] Agent raw response payload:", data);
        appendMessage(data.response, "agent");
    } catch (err) {
        console.error("[VibeMap UI] Chat Agent Execution Error:", err);
        appendMessage(`Agent Error: ${err.message}`, "agent");
    }
});

chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendBtn.click();
});
