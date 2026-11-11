# WebAble

Accessibility evidence from FastAPI, Playwright and axe-core, with a React dashboard.

## Run locally

From this directory, install the backend and browser:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m playwright install chromium
npm install
python run_server.py
```

In another terminal:

```sh
npm run dev
```

Open http://127.0.0.1:5173/static/. Vite proxies `/accessibility` and `/captures` to FastAPI on port 8000. Enter a public website URL with or without `https://`; WebAble adds HTTPS when omitted. The owner questionnaire is temporarily removed from the dashboard.

## Production

```sh
npm ci
npm run build
python run_server.py
```

Open http://127.0.0.1:8000/. The build writes React assets into `app/static`, which FastAPI already serves. Rebuild after frontend changes. No separate Node server is required in production. Alternatively deploy `app/static` on a static host and reverse-proxy `/accessibility` and `/captures` to FastAPI on the same origin.

## Deploy on Render with Docker

Create a Render Web Service using the repository root as its Docker build context.
The root `Dockerfile` builds the React frontend, installs the Playwright Chromium
runtime, and copies the pinned axe-core script into the location used by the
backend. Leave the build command empty; the Dockerfile handles the build and
starts Uvicorn on Render's assigned port. Deploy the latest commit containing the
Dockerfile. If a capture returns a report without accessibility evidence, check
the viewport's accessibility scan status and details in the report.

You can also create the service using the included `render.yaml` Blueprint.
For an existing service, use the Docker runtime, set the health check path to
`/health`, and set `WEBABLE_MAX_CONCURRENT_CAPTURES=1` to limit simultaneous
Chromium sessions on smaller instances. Keep the Python Playwright pin in
`requirements.txt` aligned with the Docker image version. Deploy this directory
(`webAble` if deploying from its parent) as the Docker build context.

Empty or non-JSON API responses now show a readable error with the HTTP status.
If a capture still returns HTTP 502/503/504 after redeploying, check Render's
runtime logs for a process restart, memory exhaustion, or timeout at that time;
the frontend cannot recover a report from a terminated server process.

## Concurrent audits

The dashboard submits `POST /captures/jobs` and polls `GET /captures/jobs/{id}`
every two seconds. Audits wait for a browser slot without holding a long HTTP
request open. The execution timeout starts after acquiring a slot. The existing
`POST /captures` endpoint remains available for synchronous clients.

`WEBABLE_MAX_CONCURRENT_CAPTURES` defaults to `1` to limit browser memory usage;
increase it only when the host has sufficient CPU and RAM. Up to
`WEBABLE_MAX_PENDING_CAPTURES` audits (default `20`, including running work) are
accepted; a full queue returns HTTP 429. Results expire after 15 minutes and at
most 100 reports are retained.

This queue is in memory: run **one Uvicorn worker and one service instance**.
Restarts discard jobs. Use a persistent shared job queue and result store before
enabling multiple workers, replicas, or serverless hosting. This implementation
is intended for the Docker/Render service above.

The dashboard opens a dedicated `/scan/{scan-id}` page after queueing an audit.
Its progress bar is a time-based estimate, not live server telemetry, and stays
below 100% until the API returns a completed report. Refreshing the same browser
tab resumes polling from session storage. Completed reports are available at
`/report/{scan-id}` and can be restored after refresh in that tab. A server
restart, expired in-memory job, or unavailable browser storage requires a new
scan.

## Screenshot retention

Each successful audit always captures and persists exactly three baseline PNGs:
desktop (1365x768), tablet (768x1024), and mobile (390x844). Text reflow,
orientation, and hover/focus probes still run on all applicable viewports, but
their measurements and findings do not create persisted images during a normal
audit. Set `WEBABLE_PERSIST_SCENARIO_SCREENSHOTS=true` only for an explicitly
requested diagnostic run that needs saved visual evidence of a failing scenario.
This policy is process configuration, so it applies identically to local and
Render Docker runs. Gemini visual review of baseline-state findings uses the
persisted baseline image and a bounded in-memory crop; it does not write a
second crop file. A transformed text-reflow or interaction state has no visual
AI review unless diagnostic scenario capture is explicitly enabled, because a
baseline image would not be valid evidence for that transformed state.

The overall score is shown only when conclusive evidence reaches the
configured minimum coverage (currently 40%). Lower coverage displays a reason
instead of converting unavailable evidence into a zero score. Neither score
nor coverage represents WCAG conformance. WCAG findings that require human
review remain in the report but are excluded from score coverage.

WebAble scans public HTTP(S) pages that its browser can reach. It does not
bypass authentication, CAPTCHA, bot protection, or network restrictions, and
blocks requests to private/internal network destinations.

## Download a report

Open a completed audit and select **Download PDF**. The report opens the
browser's print dialog; choose **Save as PDF** as the destination. The PDF uses
a white page background and includes all report tabs, even if they are not
currently selected. It also includes the saved baseline captures for each
viewport and, on follow-up scans, the latest captures alongside them. Browser
print settings may still control page size, margins, and headers/footers.

## Optional AI assistance

AI enrichment is off by default. A user must check the consent box for each
audit (and separately for each rescan) before grouped findings can be sent to
Groq or eligible screenshot crops to Gemini. The service sends finding
messages, up to three selectors per rule/category group, a short sanitized HTML sample,
and only screenshots cropped around findings with measured element bounds.
The requested page URL and owner context are not included as
fields, though sanitized snippets may retain public host/path references. AI
output is advisory and never changes analyzer findings, severity, scoring, or
WCAG conclusions. The report includes a separate audit overview and structured
finding explanations with observed behavior, potential user impact, inspection
steps, remediation direction, confidence, and evidence limitations. Any code
sample is optional and illustrative. Missing scores are stated as unavailable,
not inferred. Visual opinions remain separate from analyzer verdicts.
Provider diagnostics expose only provider/model, status, latency, reported
token counts, and error type; they do not include credentials or raw exception messages. Identical
opted-in AI requests can reuse a bounded in-memory cache keyed by evidence,
prompt version, and configured model; cached text is not persisted to disk.

Set `GROQ_API_KEY` and/or `GEMINI_API_KEY` in the server environment (Render's
Environment settings in production). Optional model overrides are
`GROQ_MODEL` and `GEMINI_MODEL`. For local development, create an ignored `.env`
file using `.env.example` as a template. Never commit or paste live keys. When
no provider is configured or a provider fails, the audit still completes and
the report shows local rule-based fallback text.

## Verify

```sh
npm run build
.venv/bin/python -m pytest tests/test_questionnaire_frontend.py tests/test_scoring.py
```

## Test categories

Pytest uses `C:\tmp\webable-pytest` as its base temporary directory on the
supported Windows setup. This avoids both the user-profile Temp directory,
which may be managed or denied, and this OneDrive-synced checkout, whose files
may be briefly locked during pytest cleanup.

```powershell
# Deterministic classification tests: no Chromium or internet.
python -m pytest -m unit

# Browser integration: Chromium plus local HTML fixtures only.
python -m pytest -m browser_integration

# Existing full local suite. It may include browser tests, but no public-site test.
python -m pytest

# One external Chromium preflight. It stops immediately when the environment
# blocks external networking; add --benchmark only after a successful preflight.
python scripts/external_compatibility.py
python scripts/external_compatibility.py --benchmark
```

External results use `passed`, `blocked_by_test_environment`,
`blocked_by_target`, or `inconclusive`. A test-environment block is not an
application failure. Render must be verified separately against its deployed
service and logs; local results do not establish Render compatibility.

Frontend sources live in `frontend/src`; generated assets live in `app/static`. The browser tests exercise the production build, public URL entry, evidence safety, filters, keyboard tabs, mobile layout, partial data and unavailable dimensions. They use contract fixtures, never fallback results in the application. Backend and capture documentation remains in `docs/`.
