const API_BASE = "/api/v1";

export async function submitQuery(question) {
  const response = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, options: { top_k: 8 } }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Query failed");
  }
  return response.json();
}
