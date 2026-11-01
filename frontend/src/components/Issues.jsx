import React, { useMemo, useState } from "react";
import {
  Badge,
  Disclosure,
  Evidence,
  Filter,
  Paginated,
  SafeLink,
} from "./Common";
import { format, groupIssues, list, readable } from "../utils";
export function IssueDetails({ rule, occurrences }) {
  return (
    <div className="issue-inspector">
      <p>{rule.description || "No description returned."}</p>
      {occurrences.map((o, i) => (
        <section key={i}>
          <h4>{readable(o.viewport)}</h4>
          <Badge concept="Axe impact" value={o.rule.impact} />
          <Paginated
            items={list(o.rule.nodes)}
            size={10}
            render={(node) => (
              <article className="finding">
                <p className="field-help">Affected selector</p>
                <pre>
                  {list(node.target)
                    .map((t) => (Array.isArray(t) ? t.join(" → ") : t))
                    .join("\n")}
                </pre>
                {node.html && (
                  <>
                    <p className="field-help">Sanitized HTML · text only</p>
                    <pre>{node.html}</pre>
                  </>
                )}
                {node.failure_summary && <p>{node.failure_summary}</p>}
                {[
                  ...list(node.any_checks),
                  ...list(node.all_checks),
                  ...list(node.none_checks),
                ].map((c, j) => c.message && <p key={j}>{c.message}</p>)}
                <Evidence title="Complete node evidence" data={node} />
              </article>
            )}
          />
        </section>
      ))}
    </div>
  );
}
export function IssueCard({ rule, occurrences }) {
  return (
    <article className="finding issue-row">
      <details><summary>
      <Badge value={rule.impact} />
      <h4>{rule.help || rule.rule_id}</h4>
      <p className="rule-id">{rule.rule_id}</p>
      <p className="field-help">
        {occurrences.map((o) => readable(o.viewport)).join(" · ")} ·{" "}
        {occurrences.reduce((n, o) => n + list(o.rule.nodes).length, 0)}{" "}
        affected element observations
      </p>
      <p className="tags">{list(rule.tags).join(" · ")}</p>
      </summary>
      <IssueDetails rule={rule} occurrences={occurrences} />
      <SafeLink url={rule.help_url}>Rule documentation ↗</SafeLink>
      </details>
    </article>
  );
}
export default function Issues({ viewports }) {
  const [severity, setSeverity] = useState("all"),
    [viewport, setViewport] = useState("all");
  const issues = useMemo(
    () => groupIssues(viewports, severity, viewport),
    [viewports, severity, viewport],
  );
  return (
    <>
      <div className="chart-heading"><h3>Issues</h3><span className="metadata">{issues.length} detected rules</span></div>
      <p>
        Axe violations are grouped by rule. Custom analyzer evidence is listed
        separately below.
      </p>
      <div className="filters">
        <Filter
          label="Axe severity"
          value={severity}
          onChange={setSeverity}
          options={["all", "critical", "serious", "moderate", "minor"].map(
            (x) => [x, readable(x)],
          )}
        />
        <Filter
          label="Viewport"
          value={viewport}
          onChange={setViewport}
          options={[
            ["all", "All"],
            ...viewports.map((v, i) => [v.name || String(i), readable(v.name)]),
          ]}
        />
      </div>
      <div id="issue-list" aria-live="polite">
        <p className="field-help">
          {issues.length} matching axe rules · Counts represent element
          observations across selected viewports.
        </p>
        <Paginated
          key={`${severity}:${viewport}`}
          items={issues}
          render={(item) => <IssueCard {...item} />}
        />
      </div>
      <h3>WebAble analyzer findings</h3>
      {[
        ["Keyboard & Focus", "keyboard_focus_audit"],
        ["Target Size · WCAG 2.5.8", "target_size_audit"],
        ["Reflow / Text", "text_reflow_audit"],
        ["Horizontal Overflow", "element_overflow_diagnosis"],
        ["Functional UX", "functional_ux_audit"],
      ].map(([title, key]) => (
        <section className="panel" key={key}>
          <h4>{title}</h4>
          {key === "element_overflow_diagnosis" && (
            <p className="field-help">
              Overflow priority and evidence correlation describe layout
              evidence, not accessibility severity.
            </p>
          )}
          {viewports
            .filter((v) => viewport === "all" || v.name === viewport)
            .map((v, i) => (
              <Analyzer key={i} viewport={v} auditKey={key} />
            ))}
        </section>
      ))}
    </>
  );
}
function Analyzer({ viewport: v, auditKey }) {
  const audit = v[auditKey];
  const findings =
    auditKey === "element_overflow_diagnosis" &&
    list(v.finding_normalization?.findings).length
      ? v.finding_normalization.findings
      : [
          ...list(audit?.checks),
          ...list(audit?.findings),
          ...list(audit?.inconclusive),
          ...list(audit?.scenarios).flatMap((s) => [
            {
              ...s,
              summary: `${readable(s.scenario_id)} · ${s.condition || s.method || "Reflow scenario"}`,
            },
            ...list(s.findings),
          ]),
        ];
  return (
    <Disclosure
      title={
        <>
          {readable(v.name)} ·{" "}
          <Badge concept="Analyzer" value={audit?.status} />
        </>
      }
    >
      <Paginated
        items={findings}
        render={(f) => (
          <article className="finding analyzer-finding">
            <h4>
              {f.summary ||
                f.accessible_name ||
                f.accessible_label ||
                f.check_id ||
                f.selector ||
                f.element_selector ||
                f.rule_id ||
                "Analyzer observation"}
            </h4>
            {(f.status || f.classification) && (
              <Badge
                concept="Analyzer result"
                value={f.status || f.classification}
              />
            )}
            {(f.selector || f.element_selector) && (
              <pre>{f.selector || f.element_selector}</pre>
            )}
            {f.role && <p>Role: {f.role}</p>}
            {f.width_css_px != null && (
              <p>
                {format(f.width_css_px)} × {format(f.height_css_px)} CSS px ·
                WCAG {f.criterion_id || "2.5.8"}
              </p>
            )}
            {"focus_indicator_detected" in f && (
              <p>
                Focus indicator:{" "}
                {f.focus_indicator_detected == null
                  ? "Unknown"
                  : f.focus_indicator_detected
                    ? "Detected"
                    : "Not detected"}{" "}
                · Obscuration:{" "}
                {f.occlusion_status ||
                  (f.obscured == null
                    ? "Unknown"
                    : f.obscured
                      ? "Obscured"
                      : "Not obscured")}
              </p>
            )}
            {f.overflow_px != null && (
              <p>Overflow: {format(f.overflow_px)} px</p>
            )}
            {f.element_overflow_px != null && (
              <p>
                Element overflow: {format(f.element_overflow_px)} px · Document
                overflow: {format(f.document_overflow_px)} px
              </p>
            )}
            {f.evidence_correlation && (
              <p>Evidence correlation: {readable(f.evidence_correlation)}</p>
            )}
            {f.explanation && <p>{f.explanation}</p>}
            {f.observation && <p>{f.observation}</p>}
            <Evidence title="Supporting evidence and limitations" data={f} />
          </article>
        )}
      />
      <Evidence
        title="Full analyzer evidence"
        data={
          auditKey === "element_overflow_diagnosis"
            ? {
                document_overflow: v.horizontal_overflow,
                analysis_status: v.overflow_analysis_status,
                ...audit,
              }
            : audit || "Analyzer evidence unavailable"
        }
      />
    </Disclosure>
  );
}
