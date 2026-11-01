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

Open http://127.0.0.1:5173/static/. Vite proxies `/accessibility` and `/captures` to FastAPI on port 8000. The backend API contracts and audit pipeline are unchanged.

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

## Verify

```sh
npm run build
.venv/bin/python -m pytest tests/test_questionnaire_frontend.py
```

Frontend sources live in `frontend/src`; generated assets live in `app/static`. The browser tests exercise the production build, adaptive questionnaire payloads, evidence safety, filters, keyboard tabs, mobile layout, partial data and unavailable dimensions. They use contract fixtures, never fallback results in the application. Backend and capture documentation remains in `docs/`.
