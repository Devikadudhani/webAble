// Proxies can return empty or HTML error responses before FastAPI is reached.
const POLL_INTERVAL_MS = 2_000;
const REQUEST_TIMEOUT_MS = 30_000;
const MAX_AUDIT_WAIT_MS = 15 * 60 * 1_000;

export async function runAudit(
  payload,
  {
    fetcher = fetch,
    pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
    now = Date.now,
    maxWaitMs = MAX_AUDIT_WAIT_MS,
    requestTimeoutMs = REQUEST_TIMEOUT_MS,
  } = {},
) {
  const startedAt = now();
  const submission = await createAuditJob(payload, { fetcher, requestTimeoutMs });
  while (now() - startedAt < maxWaitMs) {
    await pause(Math.min(POLL_INTERVAL_MS, maxWaitMs - (now() - startedAt)));
    if (now() - startedAt >= maxWaitMs) break;
    const job = await getAuditJob(submission.job_id, { fetcher, requestTimeoutMs });
    if (job.status === "completed") return job.result;
    if (job.status === "failed") throw new Error(job.error?.detail || "The audit failed. Please try again.");
    if (job.status !== "pending") throw new Error("The server returned an unknown audit status.");
  }
  throw new Error(
    "The audit is still pending after 15 minutes. The server may have restarted or be overloaded. Check the Render logs, then try again.",
  );
}

export async function createAuditJob(
  payload,
  { fetcher = fetch, requestTimeoutMs = REQUEST_TIMEOUT_MS } = {},
) {
  const submission = await readApiResponse(
    await fetchWithTimeout(
      fetcher,
      "/captures/jobs",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
      requestTimeoutMs,
    ),
    "The audit request",
  );
  if (!submission.job_id) throw new Error("The server did not return an audit ID.");
  return submission;
}

export async function getAuditJob(
  jobId,
  { fetcher = fetch, requestTimeoutMs = REQUEST_TIMEOUT_MS } = {},
) {
  return readApiResponse(
    await fetchWithTimeout(
      fetcher,
      `/captures/jobs/${encodeURIComponent(jobId)}`,
      {},
      requestTimeoutMs,
    ),
    "Checking the audit",
  );
}

async function fetchWithTimeout(fetcher, url, options, timeoutMs) {
  const controller = new AbortController();
  let timeoutId;
  const timeout = new Promise((_, reject) => {
    timeoutId = setTimeout(() => {
      controller.abort();
      reject(new Error("The server did not respond in time. Please try again."));
    }, timeoutMs);
  });
  try {
    return await Promise.race([
      fetcher(url, { ...options, signal: controller.signal }),
      timeout,
    ]);
  } finally {
    clearTimeout(timeoutId);
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
