import { submitQuery } from "./api.js";
import { renderAnswer, renderCitations } from "./citations.js";

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
const citationsPanel = document.getElementById("citations-panel");
const citationsList = document.getElementById("citations-list");
const suggestedPrompts = document.getElementById("suggested-prompts");

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
    renderAnswer(result.answer, result.metadata, answerText, answerMeta, answerPanel, citationsPanel);
    renderCitations(result.citations, citationsList);
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

renderSuggestedPrompts();
