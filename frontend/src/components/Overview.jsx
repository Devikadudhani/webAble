import { scorePresentation } from "../scoringPresentation.mjs";
import React, { Suspense, lazy } from "react";
import { ScoreRing, CoverageBar, Distribution } from "./Visualizations";
import { Badge, Evidence, Paginated } from "./Common";
import { format, implemented, list, readable } from "../utils";
import { PriorityIssues } from "./Issues";
const ReportAnalytics = lazy(() => import("./ReportAnalytics"));
export function SummaryCards({ scoring }) {
  const presentation = scorePresentation(scoring);
  const counts = scoring.status_counts || (Array.isArray(scoring.criteria) ? Object.fromEntries(
    [["passed", "pass"], ["failed", "fail"], ["needs_review", "needs_review"], ["error", "error"], ["unsupported", "unsupported"], ["not_tested", "not_tested"], ["not_applicable", "not_applicable"]]
      .map(([key, status]) => [key, scoring.criteria.filter(c => c.status === status).length])
  ) : null);
  const evaluated = counts ? (counts.passed || 0) + (counts.failed || 0) : null;
  const criteria = Array.isArray(scoring.criteria) ? scoring.criteria : null;
  const statusCounts = counts
    ? [
        ["Passed", counts.passed || 0, "positive"],
        ["Confirmed failures", counts.failed || 0, "danger"],
        ["Needs review", counts.needs_review || 0, "warning"],
        ["Not tested", counts.not_tested || 0, "gray"],
        ["Analyzer errors", counts.error || 0, "gray"],
        ["Unsupported", counts.unsupported || 0, "light"],
        ["Not applicable", counts.not_applicable || 0, "light"],
      ]
    : criteria
      ? [
          ["Passed", criteria.filter(c => c.status === "pass").length, "positive"],
          ["Confirmed failures", criteria.filter(c => c.status === "fail").length, "danger"],
          ["Needs review", criteria.filter(c => c.status === "needs_review").length, "warning"],
        ]
      : null;
  const scoreUnavailableReason = !presentation.available
    ? "A score cannot be calculated: the scan was blocked, no valid conclusive evidence was returned, or the evidence is invalid." : "";
  return <div id="summary-cards" className="audit-summary" aria-label="Executive summary">
    <section className="primary-metrics" aria-label="Primary audit results">
      <div className="failure-metric"><h3>Confirmed failures</h3><strong>{counts ? counts.failed || 0 : "Unavailable"}</strong><p className="field-help">Unique failed criteria · confirmed website issues</p></div>
      <div className="coverage-summary"><CoverageBar value={scoring.overall_coverage} /><p className="field-help">Conclusive evidence within implemented automated checks</p></div>
      <div><h3>Automated checks evaluated</h3><strong>{evaluated ?? "Unavailable"}</strong><p className="field-help">Unique criteria with a pass or fail result</p></div>
    </section>
    <section className="score-summary"><h3>Overall score</h3><div className="score-layout"><ScoreRing value={presentation.available ? scoring.overall_score : null} /><div><p className="score-coverage"><strong>{format(scoring.overall_coverage)}% evidence coverage</strong></p><strong>{presentation.available ? presentation.label : "More conclusive evidence needed"}</strong><p className="field-help">Automated audit evidence; human accessibility evaluation is not included.</p>{scoring.score_weight_basis && <p className="field-help">{scoring.overall_score == null ? "Eligible dimensions cover" : "Based on"} {format(scoring.score_weight_basis.percentage)}% of implemented audit weight ({format(scoring.score_weight_basis.included_weight)} of {format(scoring.score_weight_basis.implemented_weight)}).</p>}{scoreUnavailableReason && <p className="score-explanation" role="note">{scoring.score_unavailable?.reason || scoreUnavailableReason}</p>}</div></div>
      {list(scoring.score_unavailable?.dimensions).length > 0 && (
        <details className="score-gap-details">
          <summary>What evidence is still needed?</summary>
          {scoring.score_unavailable.dimensions.map((dimension) => (
            <section key={dimension.dimension_id}>
              <h4>{dimension.name}</h4>
              <p className="field-help">
                {dimension.conclusive_criteria} conclusive of{" "}
                {dimension.required_conclusive_criteria} currently required;
                {` ${dimension.additional_conclusive_criteria_needed} additional conclusive result(s) needed.`}
                {dimension.coverage_percentage == null
                  ? " Coverage unavailable."
                  : ` Current coverage: ${format(dimension.coverage_percentage)}%.`}
              </p>
              {list(dimension.unresolved_criteria).length > 0 && (
                <ul>
                  {dimension.unresolved_criteria.map((criterion) => (
                    <li key={criterion.criterion_id}>
                      {criterion.name} · {readable(criterion.status)}: {criterion.action}
                      {criterion.diagnostic ? ` ${criterion.diagnostic}` : ""}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
          <p className="field-help">
            Resolving these items does not guarantee an overall score;
            valid conclusive evidence is required.
          </p>
        </details>
      )}
    </section>
    <section className="outcome-summary"><h3>Audit outcomes · unique criteria</h3>{statusCounts ? <Distribution label="Scoring criteria" segments={statusCounts} /> : <p className="field-help">Outcome counts unavailable</p>}</section>
    <p className="analyzer-note" role="note">Analyzer errors: {counts ? counts.error || 0 : "unavailable"}. Execution errors are not accessibility violations and do not count as evaluated checks. Coverage and scores are not WCAG conformance percentages.</p>
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
      {d.score_range && d.score_range.min != null && d.score_range.max != null && (
        <p className="field-help">
          Possible outcome range: {format(d.score_range.min)}–{format(d.score_range.max)} / 100
          <span className="range-note"> · Not a statistical confidence interval</span>
        </p>
      )}
      <dl className="technical-rows">
        <div><dt>{d.score_basis === "conclusive_checks" ? "Score on conclusive checks" : "Score"}</dt><dd>{d.score == null ? "Score unavailable" : `${format(d.score)} / 100`}</dd></div>
        <div><dt>Coverage</dt><dd>{d.coverage_percentage == null ? "Unavailable" : `${format(d.coverage_percentage)}%`}</dd></div>
        <div><dt>Status</dt><dd><Badge value={d.scoring_status} /></dd></div>
        <div><dt>Passed</dt><dd>{d.passed_criteria ?? "—"}</dd></div>
        <div><dt>Confirmed failures</dt><dd>{d.failed_criteria ?? "—"}</dd></div>
        <div><dt>Review</dt><dd>{d.needs_review_criteria ?? "—"}</dd></div>
      </dl>
      {d.score_label && <p className="field-help">
        {readable(d.scoring_status)} · {readable(d.score_label)}
        {d.coverage_percentage != null && d.coverage_percentage < 100
          ? " on conclusive checks only"
          : ""}
      </p>}
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
    <details id="browser-evidence" className="panel contextual-observations">
      <summary>
        <h3>Contextual observations · {features.length + observations.length}</h3>
      </summary>
      <p className="field-help">
        These browser-discovered candidates and bounded observations provide
        context; they are not confirmed defects or criterion conclusions.
      </p>
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
    </details>
  );
}
export default function Overview({ scoring, evaluation, viewports, catalog, aiAnalysis, onShowScreenshot }) {
  const dimensions = list(scoring.dimensions),
    deferred = dimensions.filter((d) => !implemented(d));
  const counts = new Map();
  for (const c of list(evaluation.criteria))
    counts.set(c.status, (counts.get(c.status) || 0) + 1);
  return (
    <>
      <PriorityIssues viewports={viewports} aiAnalysis={aiAnalysis} onShowScreenshot={onShowScreenshot} />
      <h3>Evaluation overview</h3>
      <Suspense fallback={<p className="field-help">Loading audit analytics…</p>}>
        <ReportAnalytics scoring={scoring} />
      </Suspense>
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
