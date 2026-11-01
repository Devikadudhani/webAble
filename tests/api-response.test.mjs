import test from "node:test";
import assert from "node:assert/strict";
import { readApiResponse, runAudit } from "../frontend/src/api.mjs";

test("audits poll pending jobs and return their report", async () => {
  const calls = [];
  const responses = [
    { job_id: "abc" }, { status: "pending" },
    { status: "completed", result: { viewports: [] } },
  ];
  const result = await runAudit({ url: "https://example.com" }, {
    pause: async () => {},
    fetcher: async (url, options) => {
      calls.push({ url, options });
      return Response.json(responses.shift());
    },
  });
  assert.deepEqual(result, { viewports: [] });
  assert.deepEqual(calls.map(call => call.url), ["/captures/jobs", "/captures/jobs/abc", "/captures/jobs/abc"]);
  assert.equal(calls[0].options.method, "POST");
});

test("failed audits surface the server error", async () => {
  const responses = [{ job_id: "abc" }, { status: "failed", error: { detail: "Browser failed" } }];
  await assert.rejects(runAudit({}, {
    pause: async () => {},
    fetcher: async () => Response.json(responses.shift()),
  }), /Browser failed/);
});

test("empty and HTML proxy errors preserve the HTTP status", async () => {
  for (const body of ["", "<html>Bad gateway</html>"]) {
    await assert.rejects(
      readApiResponse(new Response(body, { status: 502 }), "Audit"),
      /Audit failed \(HTTP 502\).*try again/,
    );
  }
});

test("truncated successful JSON is reported clearly", async () => {
  for (const body of ["", '{"viewports":']) {
    await assert.rejects(readApiResponse(new Response(body), "Audit"), /empty or invalid JSON/);
  }
});

test("FastAPI errors retain both supported detail formats", async () => {
  for (const detail of ["Capture failed", { detail: "Capture failed" }]) {
    await assert.rejects(
      readApiResponse(Response.json({ detail }, { status: 400 }), "Audit"),
      /Capture failed/,
    );
  }
});

test("valid reports pass through and invalid payloads are rejected", async () => {
  assert.deepEqual(await readApiResponse(Response.json({ viewports: [] }), "Audit"), { viewports: [] });
  for (const payload of [null, [], "unexpected"]) {
    await assert.rejects(readApiResponse(Response.json(payload), "Audit"), /invalid response/);
  }
});
