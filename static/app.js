"use strict";

const TOKEN_KEY = "rag_token";
let currentSessionId = null;
let activeStream = null;

function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

function setToken(value) {
  if (value) {
    localStorage.setItem(TOKEN_KEY, value);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

async function api(path, options = {}) {
  const headers = Object.assign({}, options.headers);
  if (getToken()) headers["Authorization"] = "Bearer " + getToken();
  const response = await fetch(path, Object.assign({}, options, { headers }));
  if (response.status === 401) {
    showLogin();
    throw new Error("未授权");
  }
  if (!response.ok) {
    let detail = "请求失败(" + response.status + ")";
    try {
      const body = await response.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch (e) {
      /* 非 JSON 响应,保留默认提示 */
    }
    throw new Error(detail);
  }
  return response;
}

function showLogin() {
  document.getElementById("login-mask").classList.remove("hidden");
  document.getElementById("app").classList.add("hidden");
  setToken("");
  document.getElementById("login-error").classList.add("hidden");
}

async function tryLogin() {
  const token = document.getElementById("token-input").value.trim();
  if (!token) return;
  setToken(token);
  try {
    await api("/api/sessions");
    document.getElementById("login-mask").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
    await loadSessions();
  } catch (e) {
    showLogin();
    document.getElementById("login-error").classList.remove("hidden");
  }
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderMarkdown(text) {
  let html = escapeHtml(text);
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html
    .split(/\n{2,}/)
    .map(function (block) {
      const lines = block.split("\n");
      const listLines = lines.filter(function (line) {
        return /^\s*[-*]\s+/.test(line);
      });
      if (listLines.length === lines.length && listLines.length > 0) {
        const items = lines
          .map(function (line) {
            return "<li>" + line.replace(/^\s*[-*]\s+/, "") + "</li>";
          })
          .join("");
        return "<ul>" + items + "</ul>";
      }
      if (/^#{1,4}\s/.test(block)) {
        const level = (block.match(/^#+/) || [""])[0].length;
        return "<h" + level + ">" + block.replace(/^#+\s*/, "") + "</h" + level + ">";
      }
      return "<p>" + lines.join("<br>") + "</p>";
    })
    .join("");
  return html;
}

function toast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.classList.remove("hidden");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(function () {
    el.classList.add("hidden");
  }, 3000);
}

function newSession() {
  currentSessionId = null;
  const messages = document.getElementById("messages");
  messages.innerHTML = "";
  renderWelcome();
  document.getElementById("question").focus();
  document.querySelectorAll("#session-list li").forEach(function (li) {
    li.classList.remove("active");
  });
}

function renderWelcome() {
  const messages = document.getElementById("messages");
  const welcome = document.createElement("div");
  welcome.className = "welcome";
  welcome.innerHTML =
    "<h2>你好,我是遥感知识问答助手</h2>" +
    "<p>基于本地知识库回答遥感与地理信息相关问题,并附引用来源。</p>" +
    '<div class="welcome-samples">' +
    "<button>NDVI 的计算公式是什么?</button>" +
    "<button>遥感影像预处理流程有哪些?</button>" +
    "<button>土地覆盖分类体系怎么划分?</button>" +
    "</div>";
  welcome.querySelectorAll("button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      sendQuestion(btn.textContent);
    });
  });
  messages.appendChild(welcome);
}

async function loadSessions() {
  const data = await api("/api/sessions").then(function (r) {
    return r.json();
  });
  const list = document.getElementById("session-list");
  list.innerHTML = "";
  data.forEach(function (session) {
    const li = document.createElement("li");
    li.dataset.id = session.id;
    li.className = session.id === currentSessionId ? "active" : "";

    const title = document.createElement("span");
    title.className = "session-title";
    title.textContent = session.title || "新会话";
    title.title = session.title || "新会话";

    const del = document.createElement("button");
    del.className = "session-del";
    del.textContent = "×";
    del.title = "删除会话";
    del.addEventListener("click", async function (e) {
      e.stopPropagation();
      if (!confirm("删除该会话及其全部消息?")) return;
      await api("/api/sessions/" + session.id, { method: "DELETE" });
      if (currentSessionId === session.id) newSession();
      await loadSessions();
    });

    li.appendChild(title);
    li.appendChild(del);
    li.addEventListener("click", function () {
      selectSession(session.id);
    });
    list.appendChild(li);
  });
}

async function selectSession(sessionId) {
  currentSessionId = sessionId;
  document.querySelectorAll("#session-list li").forEach(function (li) {
    li.classList.toggle("active", li.dataset.id === sessionId);
  });
  const data = await api("/api/sessions/" + sessionId + "/messages").then(function (r) {
    return r.json();
  });
  const messages = document.getElementById("messages");
  messages.innerHTML = "";
  data.forEach(function (message) {
    appendMessage(message.role, message.content, message.sources ? JSON.parse(message.sources) : []);
  });
  scrollToBottom();
}

function appendMessage(role, content, sources) {
  const messages = document.getElementById("messages");
  const welcome = document.querySelector(".welcome");
  if (welcome) welcome.remove();

  if (role === "user") {
    const row = document.createElement("div");
    row.className = "message user";
    row.innerHTML =
      '<div class="bubble"></div><div class="avatar">我</div>';
    row.querySelector(".bubble").textContent = content;
    messages.appendChild(row);
    scrollToBottom();
    return;
  }

  const row = document.createElement("div");
  row.className = "message assistant";
  row.innerHTML = '<div class="avatar">AI</div><div class="bubble pending"></div>';
  messages.appendChild(row);
  const bubble = row.querySelector(".bubble");
  if (content) {
    bubble.classList.remove("pending");
    bubble.innerHTML = renderMarkdown(content);
  }
  if (sources.length) appendSources(row, sources);
  scrollToBottom();
}

function updateAssistantBubble(text) {
  const bubble = document.querySelector("#messages .bubble.pending");
  if (bubble) {
    bubble.innerHTML = renderMarkdown(text);
    scrollToBottom();
  }
}

function clearPendingBubble() {
  const bubble = document.querySelector("#messages .bubble.pending");
  if (bubble) bubble.classList.remove("pending");
}

function appendSources(row, sources) {
  const ref = document.createElement("div");
  ref.className = "sources";
  ref.innerHTML =
    '<span class="sources-label">来源:</span>' +
    sources.map(function (name) {
      return '<span class="source-tag">' + escapeHtml(name) + "</span>";
    }).join("");
  row.appendChild(ref);
}

function showErrorBar(message) {
  const bar = document.createElement("div");
  bar.className = "error-bar";
  bar.textContent = message;
  document.getElementById("messages").appendChild(bar);
  scrollToBottom();
}

function setTyping(on) {
  document.getElementById("typing").classList.toggle("hidden", !on);
  document.getElementById("send-btn").disabled = on;
  document.getElementById("question").disabled = on;
}

function scrollToBottom() {
  const messages = document.getElementById("messages");
  messages.scrollTop = messages.scrollHeight;
}

function parseSSEChunk(chunk, handlers) {
  const event = (chunk.match(/^event:\s*(.+)$/m) || [])[1];
  const data = (chunk.match(/^data:\s*(.+)$/m) || [])[1];
  if (!event || !data || !handlers[event]) return;
  let payload = data;
  try {
    payload = JSON.parse(data);
  } catch (e) {
    /* 保留原始文本 */
  }
  handlers[event](payload);
}

async function sendQuestion(question) {
  question = question.trim();
  if (!question || !getToken() || activeStream) return;

  appendMessage("user", question, []);
  appendMessage("assistant", "", []);
  document.getElementById("question").value = "";
  document.getElementById("question").style.height = "auto";
  setTyping(true);

  let answerText = "";
  let sources = [];

  const handlers = {
    delta: function (event) {
      answerText += event.text;
      updateAssistantBubble(answerText);
    },
    sources: function (event) {
      sources = event.names;
    },
    error: function (event) {
      showErrorBar(event.message);
      clearPendingBubble();
    },
    done: function () {
      const pending = document.querySelector("#messages .bubble.pending");
      if (pending) {
        if (answerText) {
          pending.innerHTML = renderMarkdown(answerText);
          appendSources(pending.parentElement, sources);
        }
        pending.classList.remove("pending");
      }
      setTyping(false);
      loadSessions().catch(function () {});
    },
  };

  try {
    const response = await api("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId, question: question }),
    });
    activeStream = response;
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });
      let index;
      while ((index = buffer.indexOf("\n\n")) >= 0) {
        const eventChunk = buffer.slice(0, index);
        buffer = buffer.slice(index + 2);
        parseSSEChunk(eventChunk, handlers);
      }
    }
  } catch (e) {
    if (e.message !== "未授权") showErrorBar(e.message);
    clearPendingBubble();
  } finally {
    activeStream = null;
    setTyping(false);
  }
}

async function openDocs() {
  document.getElementById("docs-panel").classList.remove("hidden");
  await refreshDocs();
}

async function refreshDocs() {
  const data = await api("/api/documents").then(function (r) {
    return r.json();
  });
  const list = document.getElementById("docs-list");
  list.innerHTML = "";
  if (!data.files.length) {
    const li = document.createElement("li");
    li.className = "docs-empty";
    li.textContent = "暂无文档";
    list.appendChild(li);
    return;
  }
  data.files.forEach(function (file) {
    const li = document.createElement("li");
    li.innerHTML =
      '<span class="doc-name"></span><span class="doc-size"></span>';
    li.querySelector(".doc-name").textContent = file.name;
    li.querySelector(".doc-size").textContent = formatSize(file.size);
    list.appendChild(li);
  });
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1024 / 1024).toFixed(1) + " MB";
}

async function uploadDocument(file) {
  const status = document.getElementById("docs-status");
  status.textContent = "上传并重建知识库中,请稍候…";
  const form = new FormData();
  form.append("file", file);
  try {
    const data = await api("/api/documents", { method: "POST", body: form }).then(function (r) {
      return r.json();
    });
    status.textContent = "已入库 " + data.inserted + " 个文档";
    await refreshDocs();
    toast("知识库更新完成");
  } catch (e) {
    status.textContent = e.message;
  }
}

function setupEvents() {
  document.getElementById("login-btn").addEventListener("click", tryLogin);
  document.getElementById("token-input").addEventListener("keydown", function (e) {
    if (e.key === "Enter") tryLogin();
  });

  document.getElementById("new-session-btn").addEventListener("click", newSession);

  const form = document.getElementById("chat-form");
  const textarea = document.getElementById("question");
  textarea.addEventListener("input", function () {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 160) + "px";
    document.getElementById("send-btn").disabled = !textarea.value.trim();
  });
  textarea.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!document.getElementById("send-btn").disabled) form.requestSubmit();
    }
  });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    sendQuestion(textarea.value);
  });

  document.getElementById("docs-btn").addEventListener("click", openDocs);
  document.getElementById("docs-close").addEventListener("click", function () {
    document.getElementById("docs-panel").classList.add("hidden");
  });
  document.getElementById("docs-upload").addEventListener("change", function (e) {
    if (e.target.files.length) uploadDocument(e.target.files[0]);
    e.target.value = "";
  });
  document.getElementById("docs-rebuild").addEventListener("click", async function () {
    const status = document.getElementById("docs-status");
    status.textContent = "重建中,请稍候…";
    try {
      const data = await api("/api/rebuild", { method: "POST" }).then(function (r) {
        return r.json();
      });
      status.textContent = "重建完成,共 " + data.inserted + " 个文档";
    } catch (e) {
      status.textContent = e.message;
    }
  });
}

function init() {
  setupEvents();
  renderWelcome();
  if (getToken()) {
    loadSessions()
      .then(function () {
        document.getElementById("app").classList.remove("hidden");
        document.getElementById("login-mask").classList.add("hidden");
      })
      .catch(function () {
        showLogin();
      });
  } else {
    showLogin();
  }
}

init();
