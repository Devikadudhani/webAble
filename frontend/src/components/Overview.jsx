import React from "react";
import { ScoreRing, CoverageBar, Distribution } from "./Visualizations";
import { Badge, Evidence, Paginated } from "./Common";
import { format, implemented, list, readable } from "../utils";
export function SummaryCards({ scoring }) {
  const criteria = Array.isArray(scoring.criteria) ? scoring.criteria : null;
  return <div id="summary-cards" className="audit-summary">
    <section className="score-summary"><h3>WebAble score</h3><div className="score-layout"><ScoreRing value={scoring.overall_score} /><div><strong>{scoring.overall_score_label ? readable(scoring.overall_score_label) : "Evaluated checks"}</strong><p className="field-help">{readable(scoring.overall_scoring_status)}</p><p className="field-help">Evidence-based assessment, with human review.</p></div></div></section>
    <section className="outcome-summary"><h3>Audit outcomes</h3>{criteria ? <Distribution label="Scoring criteria" segments={[["Passed", criteria.filter(c => c.status === "pass").length, "positive"], ["Failed", criteria.filter(c => c.status === "fail").length, "danger"], ["Needs review", criteria.filter(c => c.status === "needs_review").length, "warning"]]} /> : <p className="field-help">Outcome counts unavailable</p>}</section>
    <section className="coverage-summary"><CoverageBar value={scoring.overall_coverage} /><p className="field-help">Conclusive evidence available · distinct from score</p></section>
  </div>;
}
export function DimensionCard({ dimension: d }) {
  if (!implemented(d))
    return (
      <article className="not-evaluated">
        <h4>{d.name}</h4>
        <p>Not currently evaluated</p>
        {d.description && <p className="field-help">{d.description}</p>}
      </article>
    );
  return (
    <article className="panel dimension">
      <h4>{d.name}</h4>
      <dl className="technical-rows">
        <div><dt>Score</dt><dd>{d.score == null ? "—" : `${format(d.score)} / 100`}</dd></div>
        <div><dt>Coverage</dt><dd>{d.coverage_percentage == null ? "Unavailable" : `${format(d.coverage_percentage)}%`}</dd></div>
        <div><dt>Status</dt><dd><Badge value={d.scoring_status} /></dd></div>
        <div><dt>Passed</dt><dd>{d.passed_criteria ?? "—"}</dd></div>
        <div><dt>Failed</dt><dd>{d.failed_criteria ?? "—"}</dd></div>
        <div><dt>Review</dt><dd>{d.needs_review_criteria ?? "—"}</dd></div>
      </dl>
      {d.score_label && <p className="field-help">{readable(d.score_label)}</p>}
      {d.coverage_label && <p className="field-help">{readable(d.coverage_label)}</p>}
      {d.description && <p className="field-help">{d.description}</p>}
    </article>
  );
}
export function BrowserEvidence({ evaluation, viewports, catalog }) {
  const features = viewports.flatMap((v) =>
    list(v.browser_feature_discovery?.features).filter((f) => f.detected),
  );
  const observations = list(evaluation.criteria).flatMap((c) =>
    list(c.browser_observed)
      .filter((e) => e.analyzer_id)
      .map((e) => ({ ...e, criterion_id: c.criterion_id })),
  );
  return (
    <section id="browser-evidence" className="panel">
      <h3>Browser evidence</h3>
      <Paginated
        items={[...features, ...observations]}
        render={(e) => (
          <article className="evidence-item">
            <span className="evidence-kind browser">
              Browser-observed
              {e.analyzer_id ? " · not a criterion conclusion" : ""}
            </span>
            {e.feature_id ? (
              <>
                <p>
                  {catalog.find((f) => f.feature_id === e.feature_id)?.label ||
                    e.feature_id}
                  : {e.count ?? "Unknown"} candidate(s) on{" "}
                  {readable(e.viewport)}.
                </p>
                {list(e.evidence).map((s, i) => (
                  <p key={i}>{s}</p>
                ))}
              </>
            ) : (
              <>
                <p>
                  {e.criterion_id} · {e.analyzer_id} · {readable(e.viewport)}
                </p>
                <p>
                  {readable(e.result_status)}: {e.summary}
                </p>
              </>
            )}
          </article>
        )}
      />
    </section>
  );
}
export default function Overview({ scoring, evaluation, viewports, catalog }) {
  const dimensions = list(scoring.dimensions),
    deferred = dimensions.filter((d) => !implemented(d));
  const counts = new Map();
  for (const c of list(evaluation.criteria))
    counts.set(c.status, (counts.get(c.status) || 0) + 1);
  return (
    <>
      <h3>Evaluation overview</h3>
      <div className="dimension-grid">
        <Paginated
          items={dimensions.filter(implemented)}
          render={(d) => <DimensionCard dimension={d} />}
        />
      </div>
      {deferred.length > 0 && (
        <section aria-label="Dimensions not currently evaluated">
          <h3>Not currently evaluated</h3>
          <div className="dimension-grid">
            {deferred.map((d, i) => (
              <DimensionCard key={i} dimension={d} />
            ))}
          </div>
        </section>
      )}
      {list(scoring.excluded_dimensions).length > 0 && (
        <Evidence
          title="Excluded dimensions"
          data={scoring.excluded_dimensions}
        />
      )}
      <section id="criterion-summary" className="panel">
        <h3>Evidence at a glance</h3>
        {counts.size ? (
          <ul className="criterion-summary-list">
            {[...counts].map(([status, count]) => (
              <li key={status}>
                <strong>{count}</strong> {readable(status)}
              </li>
            ))}
          </ul>
        ) : (
          <p>No criterion-level evaluation results were returned.</p>
        )}
        <p className="field-help">
          No criterion is marked passed from owner responses or missing
          evidence.
        </p>
      </section>
      <BrowserEvidence
        evaluation={evaluation}
        viewports={viewports}
        catalog={catalog}
      />
    </>
  );
}
