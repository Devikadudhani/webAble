import React, { useCallback, useEffect, useRef, useState } from "react";
import { Header, AuditForm, AuditLoading } from "./components/AuditForm";
import ResultsDashboard from "./components/ResultsDashboard";
import ScanProgress from "./components/ScanProgress";
import { buildRequest, getOrCreateVisualBaseline } from "./utils";
import { createAuditJob } from "./api.mjs";

const SCAN_STORAGE_KEY = "webable.activeScan";
function readSavedScan() {
  try {
    const saved = JSON.parse(window.sessionStorage.getItem(SCAN_STORAGE_KEY) || "null");
    return saved && typeof saved === "object" ? saved : null;
  } catch {
    return null;
  }
}

function saveScan(scan) {
  try {
    window.sessionStorage.setItem(SCAN_STORAGE_KEY, JSON.stringify(scan));
    return true;
  } catch {
    return false;
  }
}

function routeId(path, route) {
  const match = path.match(new RegExp(`^/${route}/([^/]+)$`));
  return match ? decodeURIComponent(match[1]) : "";
}
function newScanId() {
  return window.crypto?.randomUUID?.() ||
    `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

const empty = () => ({
  url: "",
  aiOptIn: false,
});
function withoutOwnerContext(payload) {
  const request = { ...payload };
  delete request.accessibility_context;
  return request;
}
export default function App() {
  const [path, setPath] = useState(window.location.pathname),
    [job, setJob] = useState(null);
  const [form, setForm] = useState(empty),
    [loading, setLoading] = useState(false),
    [response, setResponse] = useState(null),
    [error, setError] = useState(""),
    [visualBaseline, setVisualBaseline] = useState(null),
    [currentScanId, setCurrentScanId] = useState(""),
    [baselinePersisted, setBaselinePersisted] = useState(true);
  const pending = useRef(false);
  const navigate = useCallback((nextPath, replace = false) => {
    window.history[replace ? "replaceState" : "pushState"]({}, "", nextPath);
    setPath(nextPath);
  }, []);
  const showReport = useCallback((result, scan) => {
    const savedScan = { ...scan, result };
    const saved = saveScan(savedScan);
    const scanId = scan.scanId || scan.jobId;
    const savedBaseline = getOrCreateVisualBaseline(result, scanId);
    setJob(savedScan);
    setResponse(result);
    setVisualBaseline(savedBaseline.baseline);
    setCurrentScanId(scanId);
    setBaselinePersisted(savedBaseline.persisted);
    setError(
      saved
        ? ""
        : "The report is available, but this browser could not save the scan for refresh recovery.",
    );
    navigate(`/report/${encodeURIComponent(scanId)}`);
  }, [navigate]);

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);
  useEffect(() => {
    const scanId = routeId(path, "scan") || routeId(path, "report");
    if (!scanId) return;
    const saved = readSavedScan();
    if (!saved || (saved.scanId || saved.jobId) !== scanId || !saved.payload) {
      setError("This scan is no longer available in this browser session. Start a new audit.");
      setJob(null);
      setResponse(null);
      return;
    }
    setJob(saved);
    if (routeId(path, "report")) {
      if (saved.result) {
        const baseline = getOrCreateVisualBaseline(saved.result, saved.scanId || saved.jobId);
        setResponse(saved.result);
        setVisualBaseline(baseline.baseline);
        setCurrentScanId(saved.scanId || saved.jobId);
        setBaselinePersisted(baseline.persisted);
      } else {
        navigate(`/scan/${encodeURIComponent(saved.scanId || saved.jobId)}`, true);
      }
    }
  }, [path, navigate]);
  async function startAudit(payload) {
    if (pending.current) return;
    pending.current = true;
    setLoading(true);
    setError("");
    try {
      const submission = await createAuditJob(payload);
      const scan = {
        jobId: submission.job_id,
        scanId: newScanId(),
        payload,
        startedAt: Date.now(),
        result: null,
      };
      const saved = saveScan(scan);
      setJob(scan);
      setResponse(null);
      setError(saved ? "" : "This scan is running, but refresh recovery is unavailable because browser session storage could not be written.");
      navigate(`/scan/${encodeURIComponent(scan.scanId)}`);
    } catch (e) {
      setError(e.message || "The audit request failed.");
    } finally {
      pending.current = false;
      setLoading(false);
    }
  }
  function submit(event) {
    event?.preventDefault();
    if (pending.current) return;
    void startAudit(buildRequest(form));
  }
  const onScanComplete = useCallback(
    (result) => {
      if (job) showReport(result, job);
    },
    [job, showReport],
  );
  const retryScan = useCallback(() => {
    if (job?.payload) void startAudit(withoutOwnerContext(job.payload));
  }, [job]);
  function reset() {
    setForm(empty());
    setResponse(null);
    setVisualBaseline(null);
    setCurrentScanId("");
    setBaselinePersisted(true);
    setError("");
    setJob(null);
    navigate("/");
    document.getElementById("audit-url")?.focus();
  }
  const isScanning = Boolean(routeId(path, "scan") && job && !response);
  return (
    <>
      <a className="skip-link" href={isScanning ? "#scan-title" : "#audit-url"}>
        Skip to audit
      </a>
      <Header onNew={reset} hasResults={Boolean(response && !loading)} />
      <main className={isScanning ? "scan-page" : response ? "has-results" : "landing"}>
        {!isScanning && (
        <section className="intro">
          <p>
            WEBABLE AUDIT · EVIDENCE FOR BETTER DECISIONS
          </p>
          <h1>Find what’s broken.<br />Know what to fix.</h1>
          <p className="hero-line">
            Audit accessibility, responsive layouts, and functional reliability
            with real browser evidence.
          </p>
          <p>Start with a public URL. No account or setup required.</p>
        </section>
        )}
        <AuditForm
          form={form}
          setForm={setForm}
          loading={loading}
          response={response}
          onSubmit={submit}
          hidden={isScanning}
        />
        {!response && !isScanning && (
          <div className="landing-story">
            <section id="products" className="product-intro" aria-label="WebAble products">
              <article>
                <p className="eyebrow">WEBABLE AUDIT</p>
                <h2>Discover what’s broken.</h2>
                <p>
                  Capture desktop, tablet, and mobile views. Review evidence
                  from accessibility, responsive, functional, and technical
                  checks.
                </p>
              </article>
              <article>
                <p className="eyebrow">WEBABLE AGENT</p>
                <h2>Understand and fix why.</h2>
                <p>
                  Codebase connection and proposed code changes are not
                  available in this build. Keep the audit report as your
                  evidence while fixes are made in your usual workflow.
                </p>
              </article>
            </section>
            <section id="how-it-works" className="workflow-intro">
              <h2>Audit → Understand → Fix → Verify</h2>
              <p>
                Save the first scan as a baseline, make changes, then re-scan
                to compare captured views and check which findings remain.
              </p>
            </section>
          </div>
        )}
        {error && (
          <p id="form-error" className="error-message" role="alert">
            {error}
          </p>
        )}
        {loading && <AuditLoading url={form.url} />}
        {isScanning && (
          <ScanProgress
            job={job}
            onComplete={onScanComplete}
            onRetry={retryScan}
            onNew={reset}
          />
        )}
        {response && !loading && (
          <ResultsDashboard
            response={response}
            visualBaseline={visualBaseline}
            currentScanId={currentScanId}
            baselinePersisted={baselinePersisted}
            onAgain={(aiAssistanceOptIn) =>
              void startAudit({
                ...withoutOwnerContext(job?.payload || buildRequest(form)),
                ai_assistance_opt_in: aiAssistanceOptIn,
              })
            }
            onNew={reset}
          />
        )}
        <footer>
          WebAble · Evidence for better decisions. Human review for conformance.
        </footer>
      </main>
    </>
  );
}
