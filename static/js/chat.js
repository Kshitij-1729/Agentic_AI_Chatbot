/**
 * ═══════════════════════════════════════════════════════════
 *  AGENTIC CHATBOT — Frontend Logic
 * ═══════════════════════════════════════════════════════════
 */

// ─── State ──────────────────────────────────────────────────
const state = {
    currentConversationId: null,
    conversations: [],
    llmProvider: "gemini",
    llmModel: "gemini-2.5-flash",
    toolMode: "auto",
    isLoading: false,
};

// ─── DOM Elements ───────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const DOM = {
    sidebar: $("#sidebar"),
    sidebarToggle: $("#sidebar-toggle"),
    newChatBtn: $("#new-chat-btn"),
    searchInput: $("#search-input"),
    conversationList: $("#conversation-list"),
    welcomeScreen: $("#welcome-screen"),
    chatArea: $("#chat-area"),
    messagesContainer: $("#messages-container"),
    typingIndicator: $("#typing-indicator"),
    messageInput: $("#message-input"),
    sendBtn: $("#send-btn"),
    modelBtn: $("#model-btn"),
    modelLabel: $("#model-label"),
    modelDropdown: $("#model-dropdown"),
    modelSelector: $("#model-selector"),
    toolPopup: $("#tool-popup"),
    toolPopupClose: $("#tool-popup-close"),
    btnTools: $("#btn-tools"),
    contextMenu: $("#context-menu"),
    greetingText: $("#greeting-text"),
};

// ─── Initialize ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", init);

function init() {
    setGreeting();
    loadConversations();
    bindEvents();
    autoResizeTextarea();
    configureMarked();
}

function configureMarked() {
    if (typeof marked !== "undefined") {
        marked.setOptions({
            breaks: true,
            gfm: true,
            highlight: function (code, lang) {
                if (typeof hljs !== "undefined" && lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return code;
            },
        });
    }
}

function setGreeting() {
    const hour = new Date().getHours();
    let greeting;
    if (hour < 12) greeting = "Good morning";
    else if (hour < 17) greeting = "Good afternoon";
    else greeting = "Good evening";
    DOM.greetingText.textContent = greeting;
}

// ═══════════════════════════════════════════════════════════
//  EVENT BINDING
// ═══════════════════════════════════════════════════════════

function bindEvents() {
    // Sidebar
    DOM.sidebarToggle.addEventListener("click", toggleSidebar);
    DOM.newChatBtn.addEventListener("click", newChat);
    DOM.searchInput.addEventListener("input", filterConversations);

    // Send message
    DOM.sendBtn.addEventListener("click", sendMessage);
    DOM.messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    DOM.messageInput.addEventListener("input", () => {
        DOM.sendBtn.disabled = !DOM.messageInput.value.trim();
        autoResizeTextarea();
    });

    // Model selector
    DOM.modelBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleModelDropdown();
    });

    $$(".dropdown-item").forEach((item) => {
        item.addEventListener("click", () => {
            selectModel(item.dataset.provider, item.dataset.model);
        });
    });

    // Tool mode
    DOM.btnTools.addEventListener("click", () => {
        DOM.toolPopup.classList.remove("hidden");
    });
    DOM.toolPopupClose.addEventListener("click", () => {
        DOM.toolPopup.classList.add("hidden");
    });
    DOM.toolPopup.addEventListener("click", (e) => {
        if (e.target === DOM.toolPopup) DOM.toolPopup.classList.add("hidden");
    });

    $$(".tool-option").forEach((opt) => {
        opt.addEventListener("click", () => {
            selectToolMode(opt.dataset.mode);
        });
    });

    // Welcome cards
    $$(".welcome-card").forEach((card) => {
        card.addEventListener("click", () => {
            const prompt = card.dataset.prompt;
            DOM.messageInput.value = prompt;
            DOM.sendBtn.disabled = false;
            sendMessage();
        });
    });

    // Close dropdowns / context menus on outside click
    document.addEventListener("click", (e) => {
        if (!DOM.modelSelector.contains(e.target)) {
            DOM.modelDropdown.classList.add("hidden");
            DOM.modelSelector.classList.remove("open");
        }
        if (!DOM.contextMenu.contains(e.target)) {
            DOM.contextMenu.classList.add("hidden");
        }
    });

    // Escape key closes modals
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            DOM.toolPopup.classList.add("hidden");
            DOM.modelDropdown.classList.add("hidden");
            DOM.contextMenu.classList.add("hidden");
        }
    });
}

// ═══════════════════════════════════════════════════════════
//  SIDEBAR
// ═══════════════════════════════════════════════════════════

function toggleSidebar() {
    DOM.sidebar.classList.toggle("collapsed");
    document.body.classList.toggle("sidebar-hidden");
}

async function loadConversations() {
    try {
        const res = await fetch("/api/conversations");
        const data = await res.json();
        state.conversations = data;
        renderConversations(data);
    } catch (e) {
        console.error("Failed to load conversations:", e);
    }
}

function renderConversations(conversations) {
    DOM.conversationList.innerHTML = "";

    if (!conversations.length) {
        DOM.conversationList.innerHTML = `
            <div style="padding: 24px 16px; text-align: center; color: var(--text-tertiary); font-size: 0.82rem;">
                No conversations yet.<br>Start a new chat!
            </div>
        `;
        return;
    }

    // Group by date
    const groups = groupByDate(conversations);

    for (const [label, convs] of Object.entries(groups)) {
        const groupTitle = document.createElement("div");
        groupTitle.className = "conv-group-title";
        groupTitle.textContent = label;
        DOM.conversationList.appendChild(groupTitle);

        for (const conv of convs) {
            const el = createConversationItem(conv);
            DOM.conversationList.appendChild(el);
        }
    }
}

function groupByDate(conversations) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 7);

    const groups = {};

    for (const conv of conversations) {
        const date = new Date(conv.updated_at || conv.created_at);
        let label;
        if (date >= today) label = "Today";
        else if (date >= yesterday) label = "Yesterday";
        else if (date >= weekAgo) label = "Previous 7 Days";
        else label = "Older";

        if (!groups[label]) groups[label] = [];
        groups[label].push(conv);
    }

    return groups;
}

function createConversationItem(conv) {
    const el = document.createElement("div");
    el.className = `conv-item${conv.id === state.currentConversationId ? " active" : ""}`;
    el.dataset.id = conv.id;

    el.innerHTML = `
        <svg class="conv-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
        <span class="conv-item-title">${escapeHtml(conv.title)}</span>
        <div class="conv-item-actions">
            <button class="conv-item-action" data-action="rename" title="Rename">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
            </button>
            <button class="conv-item-action danger" data-action="delete" title="Delete">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
            </button>
        </div>
    `;

    // Click to open
    el.addEventListener("click", (e) => {
        if (e.target.closest(".conv-item-action")) return;
        openConversation(conv.id);
    });

    // Action buttons
    el.querySelector('[data-action="rename"]').addEventListener("click", (e) => {
        e.stopPropagation();
        renameConversation(conv.id, conv.title);
    });

    el.querySelector('[data-action="delete"]').addEventListener("click", (e) => {
        e.stopPropagation();
        deleteConversation(conv.id);
    });

    return el;
}

function filterConversations() {
    const query = DOM.searchInput.value.toLowerCase().trim();
    const filtered = state.conversations.filter((c) =>
        c.title.toLowerCase().includes(query)
    );
    renderConversations(filtered);
}

// ═══════════════════════════════════════════════════════════
//  CONVERSATIONS
// ═══════════════════════════════════════════════════════════

function newChat() {
    state.currentConversationId = null;
    DOM.welcomeScreen.classList.remove("hidden");
    DOM.chatArea.classList.add("hidden");
    DOM.messagesContainer.innerHTML = "";
    DOM.messageInput.value = "";
    DOM.sendBtn.disabled = true;
    DOM.messageInput.focus();

    // Deactivate all sidebar items
    $$(".conv-item.active").forEach((el) => el.classList.remove("active"));
}

async function openConversation(conversationId) {
    try {
        const res = await fetch(`/api/conversations/${conversationId}`);
        const data = await res.json();

        state.currentConversationId = conversationId;

        // Update sidebar highlight
        $$(".conv-item.active").forEach((el) => el.classList.remove("active"));
        const activeItem = $(`.conv-item[data-id="${conversationId}"]`);
        if (activeItem) activeItem.classList.add("active");

        // Show chat area
        DOM.welcomeScreen.classList.add("hidden");
        DOM.chatArea.classList.remove("hidden");
        DOM.messagesContainer.innerHTML = "";

        // Update model/provider from conversation settings
        if (data.llm_provider) state.llmProvider = data.llm_provider;
        if (data.llm_model) state.llmModel = data.llm_model;
        if (data.tool_mode) state.toolMode = data.tool_mode;
        updateModelLabel();

        // Render messages
        if (data.messages) {
            for (const msg of data.messages) {
                appendMessage(msg.role, msg.content);
            }
        }

        scrollToBottom();
        DOM.messageInput.focus();
    } catch (e) {
        console.error("Failed to open conversation:", e);
    }
}

async function renameConversation(conversationId, currentTitle) {
    const newTitle = prompt("Rename conversation:", currentTitle);
    if (!newTitle || newTitle.trim() === currentTitle) return;

    try {
        await fetch(`/api/conversations/${conversationId}/title`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: newTitle.trim() }),
        });
        loadConversations();
    } catch (e) {
        console.error("Failed to rename:", e);
    }
}

async function deleteConversation(conversationId) {
    if (!confirm("Delete this conversation? This cannot be undone.")) return;

    try {
        await fetch(`/api/conversations/${conversationId}`, {
            method: "DELETE",
        });

        if (state.currentConversationId === conversationId) {
            newChat();
        }
        loadConversations();
    } catch (e) {
        console.error("Failed to delete:", e);
    }
}

// ═══════════════════════════════════════════════════════════
//  MESSAGING
// ═══════════════════════════════════════════════════════════

async function sendMessage() {
    const message = DOM.messageInput.value.trim();
    if (!message || state.isLoading) return;

    state.isLoading = true;
    DOM.sendBtn.disabled = true;

    // Show chat area if on welcome screen
    DOM.welcomeScreen.classList.add("hidden");
    DOM.chatArea.classList.remove("hidden");

    // Render user message
    appendMessage("user", message);
    DOM.messageInput.value = "";
    autoResizeTextarea();
    scrollToBottom();

    // Show typing indicator
    DOM.typingIndicator.classList.remove("hidden");
    scrollToBottom();

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: message,
                conversation_id: state.currentConversationId,
                llm_provider: state.llmProvider,
                llm_model: state.llmModel,
                tool_mode: state.toolMode,
            }),
        });

        const data = await res.json();

        // Hide typing
        DOM.typingIndicator.classList.add("hidden");

        if (data.error && !data.response) {
            appendMessage("assistant", `⚠️ Error: ${data.error}`);
        } else {
            // Update conversation ID if new
            if (data.conversation_id && !state.currentConversationId) {
                state.currentConversationId = data.conversation_id;
            }

            // Show tool calls if any
            if (data.tool_calls && data.tool_calls.length > 0) {
                appendToolCalls(data.tool_calls);
            }

            // Render assistant response
            appendMessage("assistant", data.response);
        }

        // Refresh sidebar
        loadConversations();
    } catch (e) {
        DOM.typingIndicator.classList.add("hidden");
        appendMessage("assistant", "⚠️ Failed to reach the server. Please check if the backend is running.");
        console.error("Send error:", e);
    } finally {
        state.isLoading = false;
        DOM.sendBtn.disabled = !DOM.messageInput.value.trim();
        scrollToBottom();
    }
}

function appendMessage(role, content) {
    const msgEl = document.createElement("div");
    msgEl.className = `message ${role}`;

    const avatarContent =
        role === "user"
            ? "U"
            : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                 <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                 <path d="M2 17l10 5 10-5"/>
                 <path d="M2 12l10 5 10-5"/>
               </svg>`;

    const roleLabel = role === "user" ? "You" : "AgentChat";

    // Render markdown for assistant messages
    let renderedContent;
    if (role === "assistant" && typeof marked !== "undefined") {
        renderedContent = renderMarkdown(content);
    } else {
        renderedContent = escapeHtml(content);
    }

    msgEl.innerHTML = `
        <div class="message-avatar">${avatarContent}</div>
        <div class="message-content">
            <div class="message-role">${roleLabel}</div>
            <div class="message-text">${renderedContent}</div>
        </div>
    `;

    DOM.messagesContainer.appendChild(msgEl);

    // Highlight code blocks
    if (role === "assistant") {
        msgEl.querySelectorAll("pre code").forEach((block) => {
            if (typeof hljs !== "undefined") {
                hljs.highlightElement(block);
            }
        });
        addCopyButtons(msgEl);
    }
}

function appendToolCalls(toolCalls) {
    for (const tc of toolCalls) {
        const el = document.createElement("div");
        el.className = "message assistant";
        el.innerHTML = `
            <div class="message-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
                </svg>
            </div>
            <div class="message-content">
                <div class="tool-call-badge">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"/>
                    </svg>
                    Used tool: <strong>${escapeHtml(tc.name)}</strong>
                    ${tc.execution_time_ms ? `<span style="color:var(--text-tertiary)">(${tc.execution_time_ms}ms)</span>` : ""}
                </div>
            </div>
        `;
        DOM.messagesContainer.appendChild(el);
    }
}

// ─── Markdown Rendering ─────────────────────────────────────

function renderMarkdown(text) {
    if (typeof marked === "undefined") return escapeHtml(text);

    try {
        // Process the markdown
        let html = marked.parse(text);

        // Add code headers with copy button
        html = html.replace(
            /<pre><code class="language-(\w+)">/g,
            '<div class="code-header"><span>$1</span><button class="code-copy-btn" onclick="copyCode(this)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy</button></div><pre><code class="language-$1">'
        );

        return html;
    } catch (e) {
        console.error("Markdown error:", e);
        return escapeHtml(text);
    }
}

function addCopyButtons(msgEl) {
    // Add copy buttons to plain code blocks (without language class)
    msgEl.querySelectorAll("pre").forEach((pre) => {
        if (!pre.previousElementSibling || !pre.previousElementSibling.classList.contains("code-header")) {
            const header = document.createElement("div");
            header.className = "code-header";
            header.innerHTML = `<span>code</span><button class="code-copy-btn" onclick="copyCode(this)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy</button>`;
            pre.parentNode.insertBefore(header, pre);
        }
    });
}

// Global copy function
window.copyCode = function (btn) {
    const codeBlock = btn.closest(".code-header").nextElementSibling;
    const code = codeBlock.querySelector("code");
    if (code) {
        navigator.clipboard.writeText(code.textContent).then(() => {
            btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>Copied!`;
            setTimeout(() => {
                btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy`;
            }, 2000);
        });
    }
};

// ═══════════════════════════════════════════════════════════
//  MODEL SELECTOR
// ═══════════════════════════════════════════════════════════

function toggleModelDropdown() {
    const isHidden = DOM.modelDropdown.classList.contains("hidden");
    DOM.modelDropdown.classList.toggle("hidden");
    DOM.modelSelector.classList.toggle("open", isHidden);

    // Mark current selection
    $$(".dropdown-item").forEach((item) => {
        item.classList.toggle(
            "active",
            item.dataset.provider === state.llmProvider && item.dataset.model === state.llmModel
        );
    });
}

function selectModel(provider, model) {
    state.llmProvider = provider;
    state.llmModel = model;
    updateModelLabel();
    DOM.modelDropdown.classList.add("hidden");
    DOM.modelSelector.classList.remove("open");
}

function updateModelLabel() {
    // Pretty-print the model name
    const labels = {
        "gpt-4o": "GPT-4o",
        "gpt-4o-mini": "GPT-4o Mini",
        "gpt-4-turbo": "GPT-4 Turbo",
        "gpt-3.5-turbo": "GPT-3.5",
        "gemini-2.5-flash": "Gemini 2.5 Flash",
        "gemini-2.5-flash-lite": "Gemini 2.5 Flash-Lite",
    };
    DOM.modelLabel.textContent = labels[state.llmModel] || state.llmModel;
}

// ═══════════════════════════════════════════════════════════
//  TOOL MODE
// ═══════════════════════════════════════════════════════════

function selectToolMode(mode) {
    state.toolMode = mode;

    $$(".tool-option").forEach((opt) => {
        opt.classList.toggle("active", opt.dataset.mode === mode);
    });

    DOM.toolPopup.classList.add("hidden");
}

// ═══════════════════════════════════════════════════════════
//  UTILITIES
// ═══════════════════════════════════════════════════════════

function scrollToBottom() {
    requestAnimationFrame(() => {
        DOM.chatArea.scrollTop = DOM.chatArea.scrollHeight;
    });
}

function autoResizeTextarea() {
    const el = DOM.messageInput;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
