import test from "node:test";
import assert from "node:assert/strict";
import { readApiResponse } from "../frontend/src/api.mjs";

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
