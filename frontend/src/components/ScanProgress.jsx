import React, { useEffect, useRef, useState } from "react";
import { getAuditJob } from "../api.mjs";
import { readable } from "../utils";

const MAX_WAIT_MS = 15 * 60 * 1_000;
const POLL_INTERVAL_MS = 2_000;

function estimatedProgress(elapsedMs) {
  const elapsedMinutes = Math.max(0, elapsedMs) / 60_000;
  return Math.min(92, Math.round(94 * (1 - Math.exp(-elapsedMinutes / 3.2))));
}

function estimatedStage(progress) {
  if (progress < 20) return "Starting browser capture";
  if (progress < 48) return "Capturing desktop, tablet, and mobile";
  if (progress < 74) return "Checking accessibility and interactions";
  if (progress < 90) return "Analyzing responsive and technical evidence";
  return "Preparing the evidence report";
}

export default function ScanProgress({ job, onComplete, onRetry, onNew }) {
  const [now, setNow] = useState(Date.now());
  const [error, setError] = useState("");
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;
  const elapsedMs = now - job.startedAt;
  const progress = estimatedProgress(elapsedMs);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1_000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let active = true;
    let timer;
    async function poll() {
      try {
        while (active) {
          if (Date.now() - job.startedAt >= MAX_WAIT_MS) {
            throw new Error(
              "This scan has not completed after 15 minutes. The server may be overloaded or may have restarted.",
            );
          }
          const status = await getAuditJob(job.jobId);
          if (!active) return;
          if (status.status === "completed") {
            onCompleteRef.current(status.result);
            return;
          }
          if (status.status === "failed") {
            throw new Error(
              status.error?.detail || "The scan failed. You can try it again.",
            );
          }
          if (status.status !== "pending") {
            throw new Error("The server returned an unknown scan status.");
          }
          await new Promise((resolve) => {
            timer = window.setTimeout(resolve, POLL_INTERVAL_MS);
          });
        }
      } catch (pollError) {
        if (active) setError(pollError.message || "Unable to check scan status.");
      }
    }
    poll();
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [job.jobId, job.startedAt]);

  return (
    <section className="scan-progress panel" aria-labelledby="scan-title">
      <p className="eyebrow">WEBABLE AUDIT · IN PROGRESS</p>
      <h1 id="scan-title">Building your evidence report</h1>
      <p className="audit-target">{job.payload.url}</p>
      {error ? (
        <div id="form-error" className="scan-error" role="alert">
          <p>{error}</p>
          <div className="result-actions">
            <button type="button" onClick={onRetry}>Try again</button>
            <button type="button" className="secondary" onClick={onNew}>New audit</button>
          </div>
        </div>
      ) : (
        <>
          <div
            className="scan-progress-track"
            role="progressbar"
            aria-label="Estimated scan progress"
            aria-valuemin="0"
            aria-valuemax="100"
            aria-valuenow={progress}
          >
            <span style={{ width: `${progress}%` }} />
          </div>
          <div className="scan-progress-labels">
            <strong>{estimatedStage(progress)}</strong>
            <span>{progress}% estimated</span>
          </div>
          <p className="field-help">
            This is a time-based estimate, not live stage telemetry. It will
            remain below 100% until the server confirms the report is complete.
          </p>
          <ol className="stages">
            {[
              "Capture browser views",
              "Analyze accessibility, responsive, functional, and technical evidence",
              "Prepare report and baseline screenshots",
            ].map((stage) => <li key={stage}>{stage}</li>)}
          </ol>
          <p className="metadata">
            Scan ID · {readable(job.jobId)} · Refreshing this page will resume
            status checks.
          </p>
        </>
      )}
    </section>
  );
}
