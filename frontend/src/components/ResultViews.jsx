import React, { useState } from "react";
import { EvidenceDistribution, ViewportChart } from "./Visualizations";
import { Badge, Evidence, Filter, Paginated, SafeLink } from "./Common";
import { list, readable } from "../utils";
function evidenceStrengthDescription(strength, status) {
  if (strength === "bounded_probe" && status === "pass")
    return "No issues detected in bounded probe; this does not establish complete behavior.";
  if (strength === "deterministic" && status === "pass")
    return "No issue was recorded by this deterministic check.";
  if (strength === "heuristic")
    return "Candidate detection requiring interpretation or human review.";
  if (strength === "bounded_probe")
    return "Limited automated probe; it does not establish complete behavior.";
  return "Direct, reproducible measurement or observation.";
}

export function CriterionCard({ criterion: c, scoringCriteria = [] }) {
  return (
    <article className="finding">
      <details className="criterion-disclosure"><summary className="criterion-table-row"><code>{c.criterion_id}</code><strong>{c.title || c.name || "WCAG criterion"}</strong><span>{c.level || "—"}</span><Badge value={c.status} /></summary>
      <p>Manual review: {c.manual_review_required == null ? "Unavailable" : c.manual_review_required ? "Required" : "Not required by this evaluation"}</p>
      {scoringCriteria.length > 0 && (
        <section className="related-scoring-evidence">
          <strong>Related scored checks</strong>
          {scoringCriteria.map((item) => (
            <p key={item.criterion_id}>
              {item.criterion_name} · {readable(item.evidence_strength)}:{" "}
              {evidenceStrengthDescription(item.evidence_strength, item.status)}
            </p>
          ))}
        </section>
      )}
      <Evidence title="Criterion intent and evidence" data={c} />
      <SafeLink url={c.criterion_url}>Criterion</SafeLink>
      <SafeLink url={c.understanding_url}>Understanding WCAG</SafeLink>
      </details>
    </article>
  );
}
export function WCAGView({ evaluation, scoring }) {
  const [filter, setFilter] = useState("all");
  const criteria = list(evaluation.criteria).filter(
    (c) =>
      filter === "all" ||
      (filter === "manual"
        ? c.manual_review_required
        : filter === "browser_observed"
          ? list(c.browser_observed).length
          : filter === "owner_reported"
            ? list(c.owner_reported).length
            : c.status === filter),
  );
  const principles = ["Perceivable", "Operable", "Understandable", "Robust"];
  const grouped = principles.map((principle) => [
    principle,
    criteria.filter((criterion) => criterion.principle === principle),
  ]);
  const uncategorized = criteria.filter(
    (criterion) => !principles.includes(criterion.principle),
  );
  if (uncategorized.length) grouped.push(["Other", uncategorized]);
  return (
    <>
      <h3>WCAG 2.2 evidence</h3>
      <EvidenceDistribution criteria={evaluation.criteria} />
      <p>
        Automated evidence alone does not establish WCAG conformance. A missing
        conclusion is not a pass.
      </p>
      <div className="filters">
        <Filter
          label="Evidence filter"
          value={filter}
          onChange={setFilter}
          options={[
            "all",
            "browser_observed",
            "owner_reported",
            "manual",
            "not_evaluated",
          ].map((x) => [x, readable(x)])}
        />
      </div>
      <div id="wcag-list">
        {grouped.map(([principle, items]) => items.length > 0 && (
          <section className="principle-group" key={principle}>
            <h4>{principle}</h4>
            <div className="criterion-table-row table-heading" aria-hidden="true"><span>Criterion</span><span>Name</span><span>Level</span><span>Evidence</span></div>
            <Paginated
              key={`${filter}:${principle}`}
              items={items}
              render={(c) => (
                <CriterionCard
                  criterion={c}
                  scoringCriteria={list(scoring?.criteria).filter((item) =>
                    list(item.wcag_references).includes(c.criterion_id),
                  )}
                />
              )}
            />
          </section>
        ))}
        {!criteria.length && <p className="empty-state">No criteria match this filter.</p>}
      </div>
    </>
  );
}

export function ScoringDimensionView({ scoring, dimensionId }) {
  const dimensions = list(scoring.dimensions);
  const dimension = dimensions.find((item) => item.dimension_id === dimensionId);
  const criteria = list(scoring.criteria).filter((item) => item.dimension === dimensionId);
  return (
    <>
      <h3>{dimension?.name || readable(dimensionId)}</h3>
      {dimension?.description && <p>{dimension.description}</p>}
      {criteria.length ? (
        <div className="dimension-grid">
          <Paginated
            items={criteria}
            render={(criterion) => (
              <article className="panel">
                <h4>{criterion.criterion_name}</h4>
                <Badge value={criterion.status} />
                {criterion.score_exclusion_reason && (
                  <p className="field-help">
                    Excluded from score: {criterion.score_exclusion_reason}
                  </p>
                )}
                <p className="field-help">
                  Evidence strength · {readable(criterion.evidence_strength)} ·{" "}
                  {evidenceStrengthDescription(criterion.evidence_strength, criterion.status)}
                </p>
                {list(criterion.wcag_references).length > 0 && (
                  <p className="field-help">
                    WCAG {criterion.level} · {criterion.principle} ·{" "}
                    {list(criterion.wcag_references).join(", ")}
                  </p>
                )}
                <p>{criterion.description}</p>
                {list(criterion.viewport_results).length > 0 && (
                  <ul className="criterion-summary-list">
                    {criterion.viewport_results.map((result) => (
                      <li key={result.viewport}>
                        <strong>{readable(result.viewport)}</strong> · {readable(result.status)}
                        {result.details ? ` — ${result.details}` : ""}
                      </li>
                    ))}
                  </ul>
                )}
                {list(criterion.limitations).length > 0 && (
                  <p className="field-help">Limitations: {list(criterion.limitations).join(" ")}</p>
                )}
                <Evidence title="Supporting evidence" data={criterion.evidence} />
              </article>
            )}
          />
        </div>
      ) : (
        <p className="empty-state">No {readable(dimensionId)} evidence was returned.</p>
      )}
    </>
  );
}
export function ViewportCard({ viewport: v }) {
  return (
    <article className="panel">
      <h4>{readable(v.name)}</h4>
      <Badge concept="Capture" value={v.capture_outcome} />
      <Badge concept="Website access" value={v.technical_evidence?.access_status || "unavailable"} />
      <Badge concept="Analyzer execution" value={v.analyzer_execution_status || "not_run"} />
      {[
        ["Axe violations", v.accessibility_scan?.violations?.length],
        ["Axe review rules", v.accessibility_scan?.incomplete?.length],
        ["Keyboard", v.keyboard_focus_audit?.status],
        ["Target-size findings", v.target_size_audit?.findings?.length],
        ["Overflow", v.overflow_analysis_status],
        ["Reflow", v.text_reflow_audit?.status],
      ].map(([label, value]) => (
        <p key={label}>
          {label}: {readable(value)}
        </p>
      ))}
      <Evidence
        title="Capture details"
        data={{
          capture_outcome: v.capture_outcome,
          analyzer_execution_status: v.analyzer_execution_status || "not_run",
          details: v.details,
          technical_evidence: v.technical_evidence,
        }}
      />
    </article>
  );
}
export function ResponsiveView({ viewports }) {
  return (
    <>
      <h3>Responsive analysis</h3>
      <div id="responsive-cards">
        <div className="viewport-identities">{viewports.map((v, i) => <div key={i}><strong>{readable(v.name)}</strong><span>{v.viewport?.width ?? "—"} × {v.viewport?.height ?? "—"}</span></div>)}</div>
        <ViewportChart viewports={viewports} />
        <div className="dimension-grid"><Paginated items={viewports} render={(v) => <ViewportCard viewport={v} />} /></div>
      </div>
    </>
  );
}
export function OwnerEvidence({ evaluation }) {
  const declared = Object.entries(evaluation.declared_features || {})
    .filter(([, v]) => v != null)
    .map(([id, v]) => ({
      question_id: id,
      answer: v ? "yes" : "no",
      explanation: "Owner-declared feature information; not verified.",
    }));
  return (
    <>
      <h3>Owner Evidence</h3>
      <p>
        Owner responses provide contextual evidence and do not independently
        establish WCAG conformance.
      </p>
      <div id="owner-assessments">
        <Paginated
          items={list(evaluation.criteria).filter(
            (c) =>
              c.owner_self_assessment &&
              c.owner_self_assessment.status !== "not_provided",
          )}
          render={(c) => (
            <article className="finding">
              <h4>
                {c.criterion_id} · {c.title || "Owner assessment"}
              </h4>
              <Badge
                concept="Owner outcome"
                value={c.owner_self_assessment.reported_outcome}
              />
              <p>
                {{
                  supports: "Support",
                  indicates_concern: "Concern",
                  inconclusive: "Uncertain",
                  context_only: "Context",
                }[c.owner_self_assessment.reported_outcome] ||
                  readable(c.owner_self_assessment.reported_outcome)}
              </p>
              <dl className="technical-rows"><div><dt>Browser</dt><dd>{list(c.browser_observed).length ? `${list(c.browser_observed).length} observations` : "No observations"}</dd></div><div><dt>Status</dt><dd>{list(c.conflicts).length || list(evaluation.conflicts).some(x => x.criterion_id === c.criterion_id) ? <Badge value="needs_review" concept="Conflict" /> : readable(c.status)}</dd></div></dl>
              <Evidence
                title="Owner responses and interpretation"
                data={c.owner_self_assessment}
              />
            </article>
          )}
        />
      </div>
      <section className="panel">
        <Paginated
          items={[...declared, ...list(evaluation.owner_answers)]}
          render={(a) => (
            <article className="evidence-item">
              <span className="evidence-kind">Owner-reported · unverified</span>
              <p>
                {a.question_id || "Owner response"}: {readable(a.answer)}
              </p>
              {a.explanation && <p>{a.explanation}</p>}
              <Evidence title="Owner answer evidence" data={a} />
            </article>
          )}
        />
      </section>
    </>
  );
}
