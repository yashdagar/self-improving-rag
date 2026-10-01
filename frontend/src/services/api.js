async function request(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  return response.json();
}

const post = (path, body) => request(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  systemStatus: () => request("/system/status"),
  query: (id) => request(`/query/${id}`),
  paper: (id, includeChunks = false) => request(`/papers/${id}?include_chunks=${includeChunks}`),
  sendFeedback: (feedback) => post("/feedback", feedback),
  metrics: (experimentRun) =>
    request(`/metrics${experimentRun ? `?experiment_run=${encodeURIComponent(experimentRun)}` : ""}`),
  improvementHistory: (limit = 200) => request(`/improvement/history?limit=${limit}`),
};
