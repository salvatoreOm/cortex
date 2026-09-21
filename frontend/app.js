const API_BASE = "http://localhost:8000";

const state = {
  apiKey: localStorage.getItem("cortex_api_key"),
  email: localStorage.getItem("cortex_email"),
  documents: [],
  sessions: [],
  currentSessionId: null,
};

// ---------- tiny DOM helpers ----------

const $ = (id) => document.getElementById(id);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// ---------- API helper ----------

class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.status = status;
  }
}

async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (state.apiKey) headers["X-API-Key"] = state.apiKey;

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (resp.status === 401) {
    logout("Your session expired - please sign in again.");
    throw new ApiError(401, "Unauthorized");
  }
  if (!resp.ok) {
    let detail = `Request failed (${resp.status})`;
    try {
      detail = (await resp.json()).detail || detail;
    } catch { /* ignore body parse errors */ }
    throw new ApiError(resp.status, detail);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

// ---------- auth ----------

function showAuthScreen(errorMessage) {
  $("app-screen").classList.add("hidden");
  $("auth-screen").classList.remove("hidden");
  $("auth-error").textContent = errorMessage || "";
}

function showAppScreen() {
  $("auth-screen").classList.add("hidden");
  $("app-screen").classList.remove("hidden");
  $("user-email").textContent = state.email || "";
  loadDocuments();
  loadSessions();
}

function logout(message) {
  localStorage.removeItem("cortex_api_key");
  localStorage.removeItem("cortex_email");
  state.apiKey = null;
  state.email = null;
  state.currentSessionId = null;
  showAuthScreen(message);
}

$("signup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = $("signup-email").value.trim();
  try {
    const user = await apiFetch("/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    state.apiKey = user.api_key;
    state.email = user.email;
    localStorage.setItem("cortex_api_key", state.apiKey);
    localStorage.setItem("cortex_email", state.email);
    showAppScreen();
  } catch (err) {
    $("auth-error").textContent = err.message;
  }
});

$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const key = $("existing-key").value.trim();
  state.apiKey = key;
  try {
    // There's no "whoami" endpoint, so just try an authenticated call -
    // if the key is bad, apiFetch's 401 handling bounces us back here.
    await apiFetch("/documents");
    state.email = "";
    localStorage.setItem("cortex_api_key", key);
    localStorage.setItem("cortex_email", "");
    showAppScreen();
  } catch (err) {
    state.apiKey = null;
    $("auth-error").textContent = "That API key didn't work.";
  }
});

$("logout-btn").addEventListener("click", () => logout());

// ---------- documents ----------

let pollTimer = null;

function statusBadge(status) {
  const badge = el("span", `badge badge-${status}`, status);
  return badge;
}

function renderDocuments() {
  const listEl = $("document-list");
  listEl.innerHTML = "";
  for (const doc of state.documents) {
    const item = el("li", "list-item");
    const title = el("span", "doc-title", doc.title);
    title.title = doc.title;
    item.appendChild(title);

    const right = el("span");
    right.style.display = "flex";
    right.style.alignItems = "center";
    right.style.gap = "6px";
    right.appendChild(statusBadge(doc.status));

    const del = el("button", "delete-btn", "×");
    del.title = "Delete document";
    del.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm(`Delete "${doc.title}"?`)) return;
      await apiFetch(`/documents/${doc.id}`, { method: "DELETE" });
      await loadDocuments();
    });
    right.appendChild(del);
    item.appendChild(right);
    listEl.appendChild(item);
  }

  const stillWorking = state.documents.some(
    (d) => d.status === "pending" || d.status === "processing"
  );
  if (stillWorking && !pollTimer) {
    pollTimer = setInterval(loadDocuments, 2000);
  } else if (!stillWorking && pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function loadDocuments() {
  state.documents = await apiFetch("/documents");
  renderDocuments();
}

$("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = $("file-input");
  const file = fileInput.files[0];
  if (!file) return;

  const statusEl = $("upload-status");
  statusEl.textContent = `Uploading ${file.name}...`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    await apiFetch("/documents/upload", { method: "POST", body: formData });
    statusEl.textContent = "Uploaded - embedding in the background.";
    fileInput.value = "";
    await loadDocuments();
  } catch (err) {
    statusEl.textContent = err.message;
  }
});

// ---------- chat sessions ----------

function renderSessions() {
  const listEl = $("session-list");
  listEl.innerHTML = "";
  for (const session of state.sessions) {
    const item = el(
      "li",
      "list-item" + (session.id === state.currentSessionId ? " active" : ""),
      session.title || "Untitled chat"
    );
    item.addEventListener("click", () => selectSession(session.id));
    listEl.appendChild(item);
  }
}

async function loadSessions() {
  state.sessions = await apiFetch("/chat/sessions");
  renderSessions();
}

$("new-chat-btn").addEventListener("click", async () => {
  const title = prompt("Name this chat (optional):", "") || null;
  const session = await apiFetch("/chat/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  await loadSessions();
  selectSession(session.id);
});

async function selectSession(sessionId) {
  state.currentSessionId = sessionId;
  renderSessions();
  $("chat-empty").classList.add("hidden");
  $("chat-view").classList.remove("hidden");
  await loadMessages();
}

// ---------- messages ----------

function citationChips(citations) {
  if (!citations || citations.length === 0) return null;
  const wrap = el("div", "citations");
  const seen = new Set();
  for (const c of citations) {
    if (seen.has(c.document_id)) continue;
    seen.add(c.document_id);
    wrap.appendChild(el("span", "citation-chip", c.document_title));
  }
  return wrap;
}

function appendMessage(role, content) {
  const bubble = el("div", `message ${role}`);
  const textNode = el("span", null, content);
  bubble.appendChild(textNode);
  $("messages").appendChild(bubble);
  $("messages").scrollTop = $("messages").scrollHeight;
  return { bubble, textNode };
}

async function loadMessages() {
  const messages = await apiFetch(`/chat/sessions/${state.currentSessionId}/messages`);
  $("messages").innerHTML = "";
  for (const m of messages) {
    const { bubble } = appendMessage(m.role, m.content);
    const chips = citationChips(m.citations);
    if (chips) bubble.appendChild(chips);
  }
}

$("message-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("message-input");
  const content = input.value.trim();
  if (!content || !state.currentSessionId) return;
  input.value = "";
  input.disabled = true;

  appendMessage("user", content);
  const { bubble, textNode } = appendMessage("assistant", "");

  try {
    await streamChat(state.currentSessionId, content, {
      onToken: (delta) => {
        textNode.textContent += delta;
        $("messages").scrollTop = $("messages").scrollHeight;
      },
      onDone: (payload) => {
        const chips = citationChips(payload.citations);
        if (chips) bubble.appendChild(chips);
      },
      onError: (detail) => {
        textNode.textContent = `Error: ${detail}`;
      },
    });
  } catch (err) {
    textNode.textContent = `Error: ${err.message}`;
  } finally {
    input.disabled = false;
    input.focus();
  }
});

/**
 * POSTs a chat message and reads the SSE response manually - the browser's
 * built-in EventSource only supports GET requests, and this endpoint needs a
 * POST body plus an auth header, so we parse the "event: X\ndata: Y\n\n"
 * framing ourselves from the raw response stream.
 */
async function streamChat(sessionId, content, { onToken, onDone, onError }) {
  const resp = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": state.apiKey },
    body: JSON.stringify({ content }),
  });

  if (resp.status === 401) {
    logout("Your session expired - please sign in again.");
    return;
  }
  if (!resp.ok || !resp.body) {
    onError(`Request failed (${resp.status})`);
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sepIndex;
    while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, sepIndex);
      buffer = buffer.slice(sepIndex + 2);

      const eventMatch = rawEvent.match(/^event: (.+)$/m);
      const dataMatch = rawEvent.match(/^data: (.+)$/m);
      if (!dataMatch) continue;

      const eventType = eventMatch ? eventMatch[1] : "message";
      const payload = JSON.parse(dataMatch[1]);

      if (eventType === "token") onToken(payload.delta);
      else if (eventType === "done") onDone(payload);
      else if (eventType === "error") onError(payload.detail);
    }
  }
}

// ---------- boot ----------

if (state.apiKey) {
  showAppScreen();
} else {
  showAuthScreen();
}
