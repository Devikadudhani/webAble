// Proxies can return empty or HTML error responses before FastAPI is reached.
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
