import React, { useEffect, useRef, useState } from "react";
import Overview, { SummaryCards } from "./Overview";
import Issues from "./Issues";
import {
  WCAGView,
  ResponsiveView,
  OwnerEvidence,
  ScoringDimensionView,
} from "./ResultViews";
import { Badge, Evidence, Paginated } from "./Common";
import { limitations, list, readable } from "../utils";
import VisualEvidence from "./VisualEvidence";
const tabs = [
  ["overview", "Overview"],
  ["issues", "Issues"],
  ["wcag", "WCAG"],
  ["responsive", "Responsive"],
  ["functional", "Functional"],
  ["technical", "Technical"],
  ["owner", "Owner Evidence"],
];
export function ResultsTabs({ active, setActive }) {
  const refs = useRef([]);
  function keydown(e, index) {
    let next;
    if (e.key === "ArrowRight") next = (index + 1) % tabs.length;
    else if (e.key === "ArrowLeft")
      next = (index + tabs.length - 1) % tabs.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabs.length - 1;
    else return;
    e.preventDefault();
    setActive(tabs[next][0]);
    refs.current[next]?.focus();
  }
  return (
    <div className="result-nav" role="tablist" aria-label="Audit views">
      {tabs.map(([id, label], i) => (
        <button
          key={id}
          ref={(el) => {
            refs.current[i] = el;
          }}
          id={`tab-${id}`}
          type="button"
          className="nav-button"
          role="tab"
          aria-selected={active === id}
          aria-controls={`view-${id}`}
          tabIndex={active === id ? 0 : -1}
          onClick={() => setActive(id)}
          onKeyDown={(e) => keydown(e, i)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function AIReportOverview({ analysis }) {
  const summary = analysis?.audit_summary;
  if (!summary) return null;
  const sections = [
    ["Key strengths", summary.key_strengths],
    ["Major concerns", summary.major_concerns],
    ["Recommended next steps", summary.recommended_actions],
    ["Evidence limitations", summary.limitations],
  ].filter(([, items]) => Array.isArray(items) && items.length > 0);
  return (
    <section className="ai-report-overview" aria-labelledby="ai-report-title">
      <div className="ai-report-heading">
        <div>
          <p className="eyebrow">OPTIONAL AI INTERPRETATION</p>
          <h3 id="ai-report-title">Audit overview</h3>
        </div>
        <span className="metadata">
          Advisory · {summary.source === "template" ? "local fallback" : summary.source}
        </span>
      </div>
      <p className="ai-report-lead">{summary.overall_summary}</p>
      <p>{summary.health_assessment}</p>
      {sections.length > 0 && (
        <div className="ai-report-sections">
          {sections.map(([title, items]) => (
            <section key={title}>
              <h4>{title}</h4>
              <ul>
                {items.map((item, index) => (
                  <li key={`${title}:${index}`}>{item}</li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
      <p className="field-help">
        This interpretation is based on the captured evidence and does not
        change analyzer findings, severity, scores, or conformance conclusions.
      </p>
      <div className="ai-status-row">
        <span>Explanations · {readable(analysis.explanation_status)}</span>
        <span>Visual review · {readable(analysis.visual_status)}</span>
        <span>{analysis.stats?.issue_groups ?? 0} issue groups</span>
        <span>{analysis.stats?.vision_succeeded ?? 0} visual checks completed</span>
        <span>
          Provider tokens · {Number.isFinite(analysis.stats?.total_tokens)
            ? analysis.stats.total_tokens
            : "not reported"}
        </span>
        <span>
          Provider time · {Number.isFinite(analysis.stats?.provider_latency_ms)
            ? `${analysis.stats.provider_latency_ms} ms`
            : "not reported"}
        </span>
      </div>
      {list(analysis.provider_diagnostics).length > 0 && (
        <details className="ai-processing-details">
          <summary>AI provider diagnostics</summary>
          <ul>
            {list(analysis.provider_diagnostics).map((item, index) => (
              <li key={`${item.provider}:${item.status}:${index}`}>
                {readable(item.provider)} · {readable(item.status)}
                {item.model ? ` · ${item.model}` : ""}
                {Number.isFinite(item.latency_ms)
                  ? ` · ${item.latency_ms} ms`
                  : ""}
                {item.error_type ? ` · ${readable(item.error_type)}` : ""}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

export function ResultsHeader({
  response,
  onDownloadPdf,
  onAgain,
  onNew,
  titleRef,
  aiRescanOptIn,
  setAiRescanOptIn,
}) {
  const scoring = response.scoring || {},
    evaluation = response.hybrid_evaluation || {};
  const blockedViewport = list(response.viewports).find(
    (viewport) => viewport.technical_evidence?.access_status === "restricted",
  );
  let hostname = response.requested_url || "Target unavailable";
  try { hostname = new URL(response.requested_url).hostname; } catch { /* Partial responses may omit the URL. */ }
  return (
    <>
      <div className="results-heading">
        <div>
          <p className="eyebrow">AUDIT REPORT</p>
          <h2 id="results-title" ref={titleRef} tabIndex="-1">
            Accessibility audit
          </h2>
          <p id="requested-url" title={response.requested_url}>{hostname}</p>
        </div>
        <div className="result-actions">
          <button type="button" className="secondary" onClick={onDownloadPdf}>
            Download PDF
          </button>
          <label className="rescan-ai-opt-in">
            <input
              type="checkbox"
              checked={aiRescanOptIn}
              onChange={(event) => setAiRescanOptIn(event.target.checked)}
            />
            Send this rescan’s evidence for optional AI analysis
          </label>
          <button id="run-again" type="button" onClick={onAgain}>
            Run again
          </button>
          <button
            id="new-audit"
            type="button"
            className="secondary"
            onClick={onNew}
          >
            New Audit
          </button>
        </div>
      </div>
      <div id="audit-status">
        <Badge
          concept="Evaluation"
          value={
            evaluation.status || evaluation.evaluation_status || "not_provided"
          }
        />
        <Badge concept="Scoring" value={scoring.overall_scoring_status} />
        <Badge concept="Score type" value={scoring.overall_score_type} />
        <span className="metadata">{list(response.viewports).length} viewports</span>
      </div>
      {blockedViewport && (
        <aside className="access-warning" role="status">
          <h3>Website access was blocked</h3>
          <p>
            {blockedViewport.technical_evidence?.access_restriction_provider
              ? `${blockedViewport.technical_evidence.access_restriction_provider} denied this scan. `
              : "The website returned an access restriction. "}
            WebAble captured the denial page, so this report does not evaluate the actual website.
            {blockedViewport.technical_evidence?.access_restriction_reference
              ? ` Reference: ${blockedViewport.technical_evidence.access_restriction_reference}.`
              : ""}
          </p>
          <p>If you administer the site, ask its CDN/site operator to allow the scan, or run WebAble against an authorized staging copy.</p>
        </aside>
      )}
      <p className="field-help">
        The WebAble score measures evaluated checks. Coverage measures available
        conclusive evidence. Neither is a WCAG conformance percentage.
      </p>
    </>
  );
}
export default function ResultsDashboard({
  response,
  visualBaseline,
  currentScanId,
  baselinePersisted,
  catalog,
  onAgain,
  onNew,
}) {
  const [active, setActive] = useState("overview"),
    [isPrinting, setIsPrinting] = useState(false),
    [evidenceRequest, setEvidenceRequest] = useState(null),
    [aiRescanOptIn, setAiRescanOptIn] = useState(false),
    title = useRef(null);
  const scoring = response.scoring || {},
    evaluation = response.hybrid_evaluation || {},
    viewports = list(response.viewports);
  function downloadPdf() {
    const previousTitle = document.title;
    let hostname = "website";
    try {
      hostname = new URL(response.requested_url).hostname;
    } catch {
      // Partial reports may not include a valid requested URL.
    }
    const safeHostname = hostname.replace(/[^a-z0-9.-]/gi, "-");
    const date = new Date().toISOString().slice(0, 10);
    document.title = `WebAble-audit-${safeHostname}-${date}`;
    document.body.classList.add("printing-report");
    setIsPrinting(true);
    window.requestAnimationFrame(() => {
      try {
        window.print();
      } finally {
        document.title = previousTitle;
        document.body.classList.remove("printing-report");
        setIsPrinting(false);
      }
    });
  }
  function showScreenshot(name, bounds, label) {
    setEvidenceRequest({
      name,
      bounds: bounds || null,
      label: label || "",
      key: `${Date.now()}-${Math.random()}`,
    });
    const section = document.getElementById("baseline-website");
    section?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  useEffect(() => {
    title.current?.focus({ preventScroll: true });
    title.current?.scrollIntoView({ block: "start" });
  }, [response]);
  return (
    <section
      id="results"
      className={`results${isPrinting ? " is-printing" : ""}`}
      aria-labelledby="results-title"
    >
      <ResultsHeader
        response={response}
        onDownloadPdf={downloadPdf}
        onAgain={() => {
          onAgain(aiRescanOptIn);
          setAiRescanOptIn(false);
        }}
        onNew={onNew}
        titleRef={title}
        aiRescanOptIn={aiRescanOptIn}
        setAiRescanOptIn={setAiRescanOptIn}
      />
      <AIReportOverview analysis={response.ai_analysis} />
      <SummaryCards scoring={scoring} />
      {list(evaluation.conflicts).length > 0 && (
        <aside id="conflicts" className="conflicts">
          <h3>Owner and browser information differ</h3>
          <p>
            Owner-reported context differs from browser-observed evidence.
            Review these differences.
          </p>
          <Evidence title="Conflict evidence" data={evaluation.conflicts} />
        </aside>
      )}
      <VisualEvidence
        baseline={visualBaseline}
        response={response}
        scanId={currentScanId}
        persisted={baselinePersisted}
        evidenceRequest={evidenceRequest}
        onEvidenceRequest={showScreenshot}
      />
      <ResultsTabs active={active} setActive={setActive} />
      {tabs.map(([id]) => (
        <section
          key={id}
          id={`view-${id}`}
          className="result-view"
          role="tabpanel"
          aria-labelledby={`tab-${id}`}
          tabIndex="0"
          hidden={active !== id && !isPrinting}
        >
          {id === "overview" ? (
            <Overview
              scoring={scoring}
              evaluation={evaluation}
              viewports={viewports}
              catalog={catalog}
            />
          ) : id === "issues" ? (
            <Issues
              viewports={viewports}
              baseline={visualBaseline}
              aiAnalysis={response.ai_analysis}
              isFollowUp={Boolean(
                visualBaseline?.scan_id &&
                  currentScanId !== visualBaseline.scan_id,
              )}
              onShowScreenshot={showScreenshot}
            />
          ) : id === "wcag" ? (
            <WCAGView evaluation={evaluation} scoring={scoring} />
          ) : id === "responsive" ? (
            <ResponsiveView viewports={viewports} />
          ) : id === "functional" ? (
            <ScoringDimensionView scoring={scoring} dimensionId="functional_reliability" />
          ) : id === "technical" ? (
            <ScoringDimensionView scoring={scoring} dimensionId="technical_reliability" />
          ) : (
            <OwnerEvidence evaluation={evaluation} />
          )}
        </section>
      ))}
      <details className="panel">
        <summary>Audit limitations</summary>
        <Paginated
          items={limitations(response)}
          render={(text) => <p>{String(text)}</p>}
        />
      </details>
      <details className="panel raw-evidence">
        <summary>Raw audit response · advanced evidence</summary>
        <p className="field-help">
          Includes the returned scanner evidence and diagnostic details. Review
        </p>
        <Evidence title="Full response" data={response} />
      </details>
    </section>
  );
}
