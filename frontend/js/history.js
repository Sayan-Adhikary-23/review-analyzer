const STORAGE_KEY = "review_discovery_history";
const MAX_ENTRIES = 50;

export function loadHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function generateUUID() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function saveHistoryEntry(entry) {
  const history = loadHistory();
  history.unshift({
    id: generateUUID(),
    timestamp: new Date().toISOString(),
    ...entry,
  });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(0, MAX_ENTRIES)));
  return history.slice(0, MAX_ENTRIES);
}

export function clearHistory() {
  localStorage.removeItem(STORAGE_KEY);
}

function formatTimestamp(iso) {
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function truncate(text, max = 80) {
  if (!text || text.length <= max) return text;
  return `${text.slice(0, max).trim()}…`;
}

export function renderHistoryPanel(history, container, onSelect) {
  container.innerHTML = "";

  const header = document.createElement("div");
  header.className = "flex items-center justify-between mb-4 px-1";
  header.innerHTML = `
    <h2 class="text-sm font-semibold text-slate-700 uppercase tracking-wide">History</h2>
    <button type="button" id="clear-history-btn" class="text-xs text-slate-400 hover:text-rose-600 transition">Clear</button>
  `;
  container.appendChild(header);

  const list = document.createElement("div");
  list.className = "space-y-2 overflow-y-auto flex-1 pr-1";
  list.id = "history-list";

  if (!history.length) {
    list.innerHTML = `<p class="text-sm text-slate-400 px-1">No questions yet.</p>`;
  } else {
    history.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className =
        "w-full text-left rounded-xl border border-slate-200 bg-white hover:bg-indigo-50 hover:border-indigo-200 px-3 py-3 transition";
      button.innerHTML = `
        <p class="text-xs text-slate-400 mb-1">${formatTimestamp(item.timestamp)}</p>
        <p class="text-sm font-medium text-slate-800 line-clamp-2">${escapeHtml(item.question)}</p>
        <p class="text-xs text-slate-500 mt-1 line-clamp-2">${escapeHtml(truncate(item.answer, 100))}</p>
      `;
      button.addEventListener("click", () => onSelect(item));
      list.appendChild(button);
    });
  }

  container.appendChild(list);

  const clearBtn = header.querySelector("#clear-history-btn");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (history.length && confirm("Clear all question history?")) {
        clearHistory();
        renderHistoryPanel([], container, onSelect);
      }
    });
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
