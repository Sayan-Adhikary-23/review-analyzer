from __future__ import annotations

from app.models.schemas import Citation


SYSTEM_PROMPT = """You are a review analysis assistant for a music streaming app.
Answer ONLY using the review excerpts provided below.
Rules:
- Cite evidence inline using [Source: platform | rating | date | id].
- Separate direct observations from reasonable inferences.
- If evidence is insufficient, say so clearly.
- Be concise, structured, and actionable.
"""


def build_messages(question: str, citations: list[Citation]) -> list[dict[str, str]]:
    if not citations:
        context = "No review excerpts were retrieved."
    else:
        blocks = []
        for index, citation in enumerate(citations, start=1):
            rating = citation.rating if citation.rating is not None else "N/A"
            created_at = citation.created_at or "unknown"
            blocks.append(
                f"Excerpt {index} [{citation.source} | {rating} | {created_at} | {citation.id}]:\n"
                f"{citation.excerpt}"
            )
        context = "\n\n".join(blocks)

    user_prompt = f"""Review excerpts:
{context}

Question: {question}

Provide a grounded answer with inline citations."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_retrieval_fallback(
    question: str,
    citations: list[Citation],
    reason: str | None = None,
) -> str:
    if not citations:
        return (
            "I could not find relevant reviews in the database for this question. "
            "Try rephrasing your question."
        )

    reason_note = ""
    if reason:
        if "insufficient_quota" in reason or "exceeded your current quota" in reason:
            reason_note = (
                "OpenAI could not be used because your API key has no remaining quota "
                "(add billing or credits at platform.openai.com). "
            )
        elif "invalid_api_key" in reason or "Incorrect API key" in reason:
            reason_note = "OpenAI could not be used because the API key is invalid. "
        else:
            reason_note = "OpenAI could not be used due to an API error. "

    lines = [
        f"{reason_note}Here is a retrieval-only summary based on the closest matching reviews:",
        "",
        f"Question: {question}",
        "",
    ]
    for index, citation in enumerate(citations[:5], start=1):
        rating = citation.rating if citation.rating is not None else "N/A"
        lines.append(
            f"{index}. [{citation.source} | {rating} | {citation.id}] {citation.excerpt[:240]}..."
        )
    return "\n".join(lines)
