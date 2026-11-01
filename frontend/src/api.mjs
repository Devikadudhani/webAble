// Proxies can return empty or HTML error responses before FastAPI is reached.
export async function runAudit(payload, { fetcher = fetch, pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms)) } = {}) {
  const submission = await readApiResponse(await fetcher("/captures/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }), "The audit request");
  if (!submission.job_id) throw new Error("The server did not return an audit ID.");
  for (;;) {
    await pause(2000);
    const job = await readApiResponse(await fetcher(`/captures/jobs/${encodeURIComponent(submission.job_id)}`), "Checking the audit");
    if (job.status === "completed") return job.result;
    if (job.status === "failed") throw new Error(job.error?.detail || "The audit failed. Please try again.");
    if (job.status !== "pending") throw new Error("The server returned an unknown audit status.");
  }
}

export async function readApiResponse(response, action) {
  const status = response.status ? ` (HTTP ${response.status})` : "";
  let payload;
  try {
    payload = await response.json();
  } catch (error) {
    if (error.name === "AbortError") throw error;
    if (!response.ok) {
      throw new Error(`${action} failed${status}. The server may be restarting or the request timed out. Please try again.`);
    }
    throw new Error(`${action} returned an empty or invalid JSON response${status}. Please try again.`);
  }
  if (!response.ok) {
    const detail = typeof payload?.detail === "string"
      ? payload.detail
      : payload?.detail?.detail;
    throw new Error(detail || `${action} failed${status}. Please try again.`);
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error(`${action} returned an invalid response${status}. Please try again.`);
  }
  return payload;
}
