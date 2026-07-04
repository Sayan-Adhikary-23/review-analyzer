import { submitQuery } from "./api.js";
import { renderAnswer, renderCitations } from "./citations.js";
import { loadHistory, saveHistoryEntry, renderHistoryPanel } from "./history.js";

const SUGGESTED_PROMPTS = [
  "Why do users struggle to discover new music?",
  "What are the most common frustrations with recommendations?",
  "What causes users to repeatedly listen to the same content?",
  "What unmet needs emerge consistently across reviews?",
];

const questionEl = document.getElementById("question");
const askBtn = document.getElementById("ask-btn");
const statusText = document.getElementById("status-text");
const answerPanel = document.getElementById("answer-panel");
const answerText = document.getElementById("answer-text");
const answerMeta = document.getElementById("answer-meta");
const evidenceSummary = document.getElementById("evidence-summary");
const citationsPanel = document.getElementById("citations-panel");
const citationsList = document.getElementById("citations-list");
const suggestedPrompts = document.getElementById("suggested-prompts");
const historyPanel = document.getElementById("history-panel");
const historyPanelMobile = document.getElementById("history-panel-mobile");
const historyDrawer = document.getElementById("history-drawer");
const historyToggle = document.getElementById("history-toggle");
const historyClose = document.getElementById("history-close");
const historyBackdrop = document.getElementById("history-backdrop");

function setStatus(message, isError = false) {
  statusText.textContent = message;
  statusText.className = isError ? "text-sm text-rose-600" : "text-sm text-slate-500";
}

function renderSuggestedPrompts() {
  suggestedPrompts.innerHTML = "";
  SUGGESTED_PROMPTS.forEach((prompt) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className =
      "text-xs px-3 py-1.5 rounded-full bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-600 transition";
    button.textContent = prompt;
    button.addEventListener("click", () => {
      questionEl.value = prompt;
    });
    suggestedPrompts.appendChild(button);
  });
}

function displayResult(result) {
  renderAnswer(
    result.answer,
    result.citations,
    result.metadata,
    answerText,
    answerMeta,
    evidenceSummary,
    answerPanel,
    citationsPanel
  );
  renderCitations(result.citations, citationsList);
}

function handleHistorySelect(item) {
  questionEl.value = item.question;
  displayResult({
    answer: item.answer,
    citations: item.citations || [],
    metadata: item.metadata || { retrieved_count: 0, latency_ms: 0 },
  });
  closeHistoryDrawer();
  answerPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function refreshHistoryPanels() {
  const history = loadHistory();
  renderHistoryPanel(history, historyPanel, handleHistorySelect);
  renderHistoryPanel(history, historyPanelMobile, handleHistorySelect);
}

function openHistoryDrawer() {
  historyDrawer.classList.remove("hidden");
  refreshHistoryPanels();
}

function closeHistoryDrawer() {
  historyDrawer.classList.add("hidden");
}

async function handleAsk() {
  const question = questionEl.value.trim();
  if (!question) {
    setStatus("Enter a question first.", true);
    return;
  }

  askBtn.disabled = true;
  setStatus("Analyzing reviews...");

  try {
    const result = await submitQuery(question);
    displayResult(result);
    saveHistoryEntry({
      question,
      answer: result.answer,
      citations: result.citations,
      metadata: result.metadata,
    });
    refreshHistoryPanels();
    setStatus("");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    askBtn.disabled = false;
  }
}

askBtn.addEventListener("click", handleAsk);
questionEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    handleAsk();
  }
});

historyToggle?.addEventListener("click", openHistoryDrawer);
historyClose?.addEventListener("click", closeHistoryDrawer);
historyBackdrop?.addEventListener("click", closeHistoryDrawer);

renderSuggestedPrompts();
refreshHistoryPanels();
