/* === chat.js — Streaming chat logic === */

const modelSelect = document.getElementById("modelSelect");
const messages = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const promptInput = document.getElementById("prompt");
const streamToggle = document.getElementById("streamToggle");
const bindTools = document.getElementById("bindTools");
const sendBtn = document.getElementById("sendBtn");

const history = [];

function addMessage(role, content) {
  const el = document.createElement("div");
  el.className = "message " + role;
  el.textContent = content;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
  return el;
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const content = promptInput.value.trim();
  if (!content) return;
  promptInput.value = "";
  history.push({ role: "user", content });
  addMessage("user", content);

  const payload = {
    messages: history,
    model_id: modelSelect.value ? Number(modelSelect.value) : null,
    bind_tools: bindTools.checked,
  };

  sendBtn.disabled = true;
  try {
    if (streamToggle.checked) {
      await handleStream(payload);
    } else {
      await handleNonStream(payload);
    }
  } catch (err) {
    addMessage("assistant", "Error: " + err.message);
  }
  sendBtn.disabled = false;
});

async function handleNonStream(payload) {
  const data = await api("POST", "/chat/completions", payload);
  const text = String(data.content ?? "");
  addMessage("assistant", text);
  history.push({ role: "assistant", content: text });
}

async function handleStream(payload) {
  const res = await fetch("/api/chat/completions/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  const node = addMessage("assistant", "");
  node.classList.add("streaming");
  let full = "";
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop();
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const chunk = line.slice(6);
      if (chunk === "[DONE]") break;
      try {
        const obj = JSON.parse(chunk);
        const delta = obj.delta || obj.content || "";
        full += delta;
        node.textContent = full;
      } catch { /* skip */ }
    }
    messages.scrollTop = messages.scrollHeight;
  }
  node.classList.remove("streaming");
  if (!full && buf) {
    try {
      const obj = JSON.parse(buf.replace(/^data: /, ""));
      full = obj.content || "";
      node.textContent = full;
    } catch { /* skip */ }
  }
  history.push({ role: "assistant", content: full });
}
