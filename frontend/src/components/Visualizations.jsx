import React from "react";
import { format, list, readable } from "../utils";
const valid = value => typeof value === "number" && Number.isFinite(value);
const percent = value => Math.min(100, Math.max(0, value));
export function ScoreRing({ value }) {
  const available = valid(value), radius = 49, circumference = 2 * Math.PI * radius;
  return <div className="score-ring" role="img" aria-label={`WebAble score: ${available ? `${format(value)} out of 100` : "unavailable"}`}>
    <svg viewBox="0 0 116 116" aria-hidden="true"><circle className="ring-track" cx="58" cy="58" r={radius} /><circle className="ring-value" cx="58" cy="58" r={radius} strokeDasharray={circumference} strokeDashoffset={circumference * (1 - (available ? percent(value) : 0) / 100)} /></svg>
    <div><strong>{available ? format(value) : "—"}</strong><span>{available ? "/ 100" : "Score unavailable"}</span></div>
  </div>;
}
export function CoverageBar({ value }) {
  return <><div className="chart-heading"><h3>Evidence coverage</h3><strong>{valid(value) ? `${format(value)}%` : "Unavailable"}</strong></div><div className="coverage-track" role="img" aria-label={`Evidence coverage: ${valid(value) ? `${format(value)}%` : "unavailable"}`}><span style={{ width: `${valid(value) ? percent(value) : 0}%` }} /></div></>;
}
export function Distribution({ label, segments }) {
  const total = segments.reduce((sum, [, count]) => sum + count, 0);
  return <div className="distribution"><div className="segment-track" role="img" aria-label={`${label}: ${segments.map(([name, count]) => `${name} ${count}`).join(", ")}`}>
    {segments.map(([name, count, tone]) => <span key={name} className={`segment ${tone}`} style={{ width: `${total ? count / total * 100 : 0}%` }} title={`${name}: ${count}`} />)}
  </div><dl className="chart-legend">{segments.map(([name, count, tone]) => <div key={name}><dt><i className={`dot ${tone}`} />{name}</dt><dd>{count}</dd></div>)}</dl>{!total && <p className="field-help">No matching evidence returned.</p>}</div>;
}
export function EvidenceDistribution({ criteria }) {
  // Categories are exclusive: observations take precedence over owner context,
  // then manual review, then criteria without either source.
  const counts = [0, 0, 0, 0];
  for (const c of list(criteria)) counts[list(c.browser_observed).length ? 0 : list(c.owner_reported).length ? 1 : c.manual_review_required ? 2 : 3]++;
  return <section className="evidence-distribution"><h3>WCAG evidence sources</h3><Distribution label="Criteria by available evidence source" segments={[["Browser observed", counts[0], "ink"], ["Owner reported", counts[1], "gray"], ["Manual review", counts[2], "warning"], ["Not evaluated", counts[3], "light"]]} /><p className="field-help">Each criterion counted once: browser evidence, then owner evidence, then manual review. Remaining criteria have no reported source.</p></section>;
}
export function ViewportChart({ viewports }) {
  const values = viewports.map(v => ({ name: readable(v.name), count: Array.isArray(v.accessibility_scan?.violations) ? v.accessibility_scan.violations.length : null }));
  const max = Math.max(1, ...values.map(v => v.count || 0));
  return <section className="viewport-chart"><h4>Detected axe rules by viewport</h4><p className="field-help">Violation rules, not affected elements. Unavailable scans are not counted as zero.</p>{values.map((v, i) => <div className="viewport-bar" key={i}><span>{v.name}</span><div className="coverage-track" aria-hidden="true"><span style={{ width: `${(v.count || 0) / max * 100}%` }} /></div><strong>{v.count ?? "Unavailable"}</strong></div>)}</section>;
}
