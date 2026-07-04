const SOURCE_LABELS = {
  play_store: "Play Store",
  app_store: "App Store",
  reddit: "Reddit",
};

const CITATION_PATTERN =
  /\[(?:Source:\s*)?([a-z_]+)\s*\|\s*([^|\]]+?)(?:\s*\|\s*([^|\]]+?))?(?:\s*\|\s*[^\]]+)?\]/gi;

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatDate(iso) {
  if (!iso || iso === "unknown" || iso === "N/A") return null;
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function platformLabel(source) {
  return SOURCE_LABELS[source] || source.replace(/_/g, " ");
}

function isRating(value) {
  const trimmed = String(value).trim();
  return trimmed === "N/A" || /^[1-5](\.0)?$/.test(trimmed);
}

function buildEvidenceBadge(platform, date) {
  const datePart = date ? ` · ${date}` : "";
  return `<span class="inline-flex items-center gap-1 mx-0.5 px-2 py-0.5 rounded-md bg-indigo-100 text-indigo-800 text-xs font-medium border border-indigo-200">${escapeHtml(platform)}${datePart ? `<span class="text-indigo-600 font-normal">${escapeHtml(date)}</span>` : ""}</span>`;
}

function parseCitationParts(platform, part2, part3) {
  let date = null;
  if (part3 && !isRating(part3)) {
    date = formatDate(part3.trim());
  } else if (part2 && !isRating(part2)) {
    date = formatDate(part2.trim());
  }
  return { platform: platformLabel(platform.trim()), date };
}

export function formatAnswerWithEvidence(answer) {
  return escapeHtml(answer).replace(CITATION_PATTERN, (match, platform, part2, part3) => {
    const { platform: label, date } = parseCitationParts(platform, part2, part3);
    return buildEvidenceBadge(label, date);
  });
}

export function renderEvidenceSummary(citations, container) {
  container.innerHTML = "";
  if (!citations.length) return;

  const seen = new Set();
  const badges = [];

  citations.forEach((citation) => {
    const label = platformLabel(citation.source);
    const date = formatDate(citation.created_at);
    const key = `${label}|${date || ""}`;
    if (seen.has(key)) return;
    seen.add(key);
    badges.push(buildEvidenceBadge(label, date));
  });

  if (!badges.length) return;

  container.innerHTML = `
    <div class="mt-4 pt-4 border-t border-slate-100">
      <p class="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Evidence cited</p>
      <div class="flex flex-wrap gap-2">${badges.join("")}</div>
    </div>
  `;
}

export function renderCitations(citations, container) {
  container.innerHTML = "";

  if (!citations.length) {
    container.innerHTML = `<p class="text-slate-500 text-sm">No sources returned.</p>`;
    return;
  }

  citations.forEach((citation, index) => {
    const card = document.createElement("article");
    card.className = "bg-white border border-slate-200 rounded-xl p-4 shadow-sm";

    const label = platformLabel(citation.source);
    const rating = citation.rating != null ? `${citation.rating}★` : "—";
    const date = formatDate(citation.created_at) || "—";
    const link = citation.url
      ? `<a href="${citation.url}" target="_blank" rel="noopener noreferrer" class="text-indigo-600 hover:text-indigo-500 text-sm">View</a>`
      : "";

    card.innerHTML = `
      <div class="flex items-start justify-between gap-4 mb-2">
        <div>
          <p class="text-xs uppercase tracking-wide text-slate-400">Source ${index + 1}</p>
          <p class="font-medium text-sm text-slate-700 mt-0.5">${label} · ${rating} · ${date}</p>
          <p class="text-xs text-slate-400 mt-0.5 font-mono">${escapeHtml(citation.id)}</p>
        </div>
        ${link}
      </div>
      <p class="text-sm text-slate-600 leading-relaxed">${escapeHtml(citation.excerpt)}</p>
    `;
    container.appendChild(card);
  });
}

export function renderAnswer(
  answer,
  citations,
  metadata,
  answerTextEl,
  answerMetaEl,
  evidenceSummaryEl,
  answerPanel,
  citationsPanel
) {
  answerTextEl.innerHTML = formatAnswerWithEvidence(answer);
  answerMetaEl.textContent = `${metadata.retrieved_count} sources · ${metadata.latency_ms} ms`;
  renderEvidenceSummary(citations, evidenceSummaryEl);
  answerPanel.classList.remove("hidden");
  citationsPanel.classList.remove("hidden");
}
