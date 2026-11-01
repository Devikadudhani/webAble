import React, { useEffect, useRef, useState } from "react";
import Overview, { SummaryCards } from "./Overview";
import Issues from "./Issues";
import { WCAGView, ResponsiveView, OwnerEvidence } from "./ResultViews";
import { Badge, Evidence, Paginated } from "./Common";
import { limitations, list } from "../utils";
const tabs = [
  ["overview", "Overview"],
  ["issues", "Issues"],
  ["wcag", "WCAG"],
  ["responsive", "Responsive"],
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
export function ResultsHeader({ response, onAgain, onNew, titleRef }) {
  const scoring = response.scoring || {},
    evaluation = response.hybrid_evaluation || {};
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
      <p className="field-help">
        The WebAble score measures evaluated checks. Coverage measures available
        conclusive evidence. Neither is a WCAG conformance percentage.
      </p>
    </>
  );
}
export default function ResultsDashboard({
  response,
  catalog,
  onAgain,
  onNew,
}) {
  const [active, setActive] = useState("overview"),
    title = useRef(null);
  const scoring = response.scoring || {},
    evaluation = response.hybrid_evaluation || {},
    viewports = list(response.viewports);
  useEffect(() => {
    title.current?.focus({ preventScroll: true });
    title.current?.scrollIntoView({ block: "start" });
  }, [response]);
  return (
    <section id="results" className="results" aria-labelledby="results-title">
      <ResultsHeader
        response={response}
        onAgain={onAgain}
        onNew={onNew}
        titleRef={title}
      />
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
      <ResultsTabs active={active} setActive={setActive} />
      {tabs.map(([id]) => (
        <section
          key={id}
          id={`view-${id}`}
          className="result-view"
          role="tabpanel"
          aria-labelledby={`tab-${id}`}
          tabIndex="0"
          hidden={active !== id}
        >
          {id === "overview" ? (
            <Overview
              scoring={scoring}
              evaluation={evaluation}
              viewports={viewports}
              catalog={catalog}
            />
          ) : id === "issues" ? (
            <Issues viewports={viewports} />
          ) : id === "wcag" ? (
            <WCAGView evaluation={evaluation} />
          ) : id === "responsive" ? (
            <ResponsiveView viewports={viewports} />
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
    </section>
  );
}
