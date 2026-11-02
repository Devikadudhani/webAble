import React, { useMemo, useState } from "react";
import { Badge, Evidence, Filter, SafeLink } from "./Common";
import { format, list, readable } from "../utils";

const analyzerSources = [
  ["target_size_audit", "Target size", "target_size"],
  ["finding_normalization", "Responsive", "overflow"],
  ["functional_ux_audit", "Functional", "functional"],
];

function wcagReferences(tags = []) {
  return list(tags)
    .map((tag) => tag.match(/^wcag(\d)(\d)(\d+)$/i))
    .filter(Boolean)
    .map((match) => `${match[1]}.${match[2]}.${match[3]}`);
}

function collectIssues(viewports) {
  const grouped = new Map();
  const add = (issue, viewport, evidence) => {
    const current = grouped.get(issue.key) || { ...issue, occurrences: [] };
    if (!current.occurrences.some((item) => item.viewport === viewport))
      current.occurrences.push({ viewport, evidence });
    grouped.set(issue.key, current);
  };

  for (const viewport of viewports) {
    const name = viewport.name || "unknown";
    for (const rule of list(viewport.accessibility_scan?.violations)) {
      const ruleId = rule.rule_id || rule.id || "axe-rule";
      const refs = wcagReferences(rule.tags);
      const nodes = list(rule.nodes);
      if (!nodes.length) {
        add(
          {
            key: `axe:${ruleId}`,
            category: "Accessibility",
            title: rule.help || ruleId,
            identifier: ruleId,
            impact: rule.impact || "needs_review",
            status: "fail",
            wcag: refs,
            tags: list(rule.tags),
            rule,
            type: "axe",
          },
          name,
          { rule, node: null },
        );
        continue;
      }
      for (const node of nodes) {
        const target = JSON.stringify(node.target || []);
        add(
          {
            key: `axe:${ruleId}:${target}`,
            category: "Accessibility",
            title: rule.help || ruleId,
            identifier: ruleId,
            impact: rule.impact || "needs_review",
            status: "fail",
            wcag: refs,
            tags: list(rule.tags),
            rule,
            type: "axe",
          },
          name,
          { rule, node },
        );
      }
    }

    for (const [auditKey, category, keyPrefix] of analyzerSources) {
      const findings =
        auditKey === "finding_normalization"
          ? list(viewport.finding_normalization?.findings)
          : list(viewport[auditKey]?.findings);
      for (const finding of findings) {
        const selector =
          finding.selector ||
          finding.element_selector ||
          finding.finding_id ||
          finding.rule_id ||
          finding.check_id;
        if (!selector) continue;
        const status =
          finding.status === "observed_failure" ||
          finding.classification === "violation"
            ? "fail"
            : "needs_review";
        const identity =
          auditKey === "functional_ux_audit"
            ? `${finding.rule_id}:${selector}:${finding.destination_url || ""}`
            : selector;
        add(
          {
            key: `${keyPrefix}:${identity}`,
            category,
            title:
              finding.accessible_name ||
              finding.accessible_label ||
              finding.summary ||
              selector,
            identifier: selector,
            status,
            impact: status,
            wcag: finding.criterion_id ? [finding.criterion_id] : [],
            type: "analyzer",
            auditKey,
          },
          name,
          finding,
        );
      }
      if (auditKey === "functional_ux_audit") {
        for (const finding of list(viewport.functional_ux_audit?.inconclusive)) {
          const selector = finding.element_selector || finding.rule_id;
          if (!selector) continue;
          add(
            {
              key: `functional:${finding.rule_id}:${selector}:${finding.destination_url || ""}`,
              category,
              title: finding.accessible_label || selector,
              identifier: selector,
              status: "needs_review",
              impact: "needs_review",
              wcag: [],
              type: "analyzer",
              auditKey,
            },
            name,
            finding,
          );
        }
      }
    }

    for (const check of list(viewport.keyboard_focus_audit?.checks)) {
      if (check.status === "pass") continue;
      add(
        {
          key: `keyboard:${check.check_id}`,
          category: "Keyboard & focus",
          title: check.summary || readable(check.check_id),
          identifier: check.check_id,
          status: check.status === "fail" ? "fail" : "needs_review",
          impact: check.status === "fail" ? "serious" : "needs_review",
          wcag: list(check.criterion_ids),
          type: "analyzer",
          auditKey: "keyboard_focus_audit",
        },
        name,
        check,
      );
    }

    for (const scenario of list(viewport.text_reflow_audit?.scenarios)) {
      for (const finding of list(scenario.findings)) {
        const selector = finding.selector || finding.criterion_id;
        if (!selector) continue;
        add(
          {
            key: `reflow:${scenario.scenario_id}:${selector}`,
            category: "Reflow & text",
            title: finding.observation || scenario.condition || selector,
            identifier: selector,
            status: finding.classification === "violation" ? "fail" : "needs_review",
            impact: finding.classification === "violation" ? "serious" : "needs_review",
            wcag: [finding.criterion_id].filter(Boolean),
            type: "analyzer",
            auditKey: "text_reflow_audit",
          },
          name,
          { ...finding, scenario },
        );
      }
    }
  }
  return [...grouped.values()];
}

function verificationStatus(issue, baseline, isFollowUp) {
  if (
    !isFollowUp ||
    !baseline ||
    !Array.isArray(baseline.findings)
  )
    return "Could not verify";
  const sameFinding = baseline.findings.some((finding) => {
    if (finding.key === issue.key) return true;
    return (
      issue.type === "axe" &&
      finding.category === "axe" &&
      typeof finding.key === "string" &&
      finding.key.startsWith(`axe:${issue.identifier}:`)
    );
  });
  return sameFinding ? "Still detected" : "Needs review";
}

function evidenceBounds(evidence) {
  if (evidence?.target_rect) return evidence.target_rect;
  if (
    Number.isFinite(evidence?.left_css_px) &&
    Number.isFinite(evidence?.top_css_px) &&
    Number.isFinite(evidence?.width_css_px) &&
    Number.isFinite(evidence?.height_css_px)
  ) {
    return {
      left: evidence.left_css_px,
      top: evidence.top_css_px,
      width: evidence.width_css_px,
      height: evidence.height_css_px,
    };
  }
  return null;
}

function IssueDetails({ issue, onShowScreenshot }) {
  return (
    <div className="issue-detail-content">
      {issue.type === "axe" && (
        <>
          <p>{issue.rule.description || "No description returned."}</p>
          <p className="rule-id">{issue.identifier}</p>
          {list(issue.tags).length > 0 && (
            <p className="tags">{list(issue.tags).join(" · ")}</p>
          )}
          <SafeLink url={issue.rule.help_url}>Rule documentation ↗</SafeLink>
        </>
      )}
      {issue.occurrences.map(({ viewport, evidence }, index) => {
        const rule = evidence.rule;
        const node = evidence.node;
        return (
          <section className="issue-occurrence" key={`${viewport}:${index}`}>
            <div className="issue-occurrence-heading">
              <h4>{readable(viewport)}</h4>
              {rule && <Badge concept="Axe impact" value={rule.impact} />}
              {issue.type === "analyzer" && (
                <Badge concept="Check" value={issue.status} />
              )}
            </div>
            <button
              type="button"
              className="text-action"
              onClick={() =>
                onShowScreenshot?.(
                  viewport,
                  node?.bounds || evidenceBounds(evidence),
                  issue.title,
                )
              }
            >
              View {readable(viewport)} capture
            </button>
            {node ? (
              <article className="finding">
                <p className="field-help">Affected selector</p>
                <pre>
                  {list(node.target)
                    .map((target) =>
                      Array.isArray(target) ? target.join(" → ") : target,
                    )
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
                ].map((check, checkIndex) =>
                  check.message ? <p key={checkIndex}>{check.message}</p> : null,
                )}
                <Evidence title="Complete node evidence" data={node} />
              </article>
            ) : issue.type === "analyzer" ? (
              <article className="finding">
                {(evidence.selector || evidence.element_selector) && (
                  <pre>{evidence.selector || evidence.element_selector}</pre>
                )}
                {evidence.width_css_px != null && (
                  <p>
                    {format(evidence.width_css_px)} ×{" "}
                    {format(evidence.height_css_px)} CSS px
                  </p>
                )}
                {evidence.observation && <p>{evidence.observation}</p>}
                {evidence.explanation && <p>{evidence.explanation}</p>}
                <Evidence title="Supporting evidence" data={evidence} />
              </article>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}

export default function Issues({
  viewports,
  baseline,
  isFollowUp,
  onShowScreenshot,
}) {
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("all");
  const [category, setCategory] = useState("all");
  const [criterion, setCriterion] = useState("all");
  const [viewport, setViewport] = useState("all");
  const [status, setStatus] = useState("all");
  const [verification, setVerification] = useState("all");
  const [selectedKey, setSelectedKey] = useState("");
  const [mobileDetailOpen, setMobileDetailOpen] = useState(false);
  const issues = useMemo(() => collectIssues(viewports), [viewports]);
  const categories = [...new Set(issues.map((issue) => issue.category))].sort();
  const criteria = [...new Set(issues.flatMap((issue) => issue.wcag))].sort();
  const viewportIssues = issues.flatMap((issue) => {
    const occurrences =
      viewport === "all"
        ? issue.occurrences
        : issue.occurrences.filter((item) => item.viewport === viewport);
    return occurrences.length ? [{ ...issue, occurrences }] : [];
  });
  const filteredIssues = viewportIssues.filter((issue) => {
    const searchText = [
      issue.title,
      issue.identifier,
      issue.category,
      ...issue.wcag,
      ...list(issue.tags),
      ...issue.occurrences.map(({ evidence }) =>
        evidence.node?.failure_summary || evidence.observation || "",
      ),
    ]
      .join(" ")
      .toLowerCase();
    return (
      (!query || searchText.includes(query.toLowerCase())) &&
      (severity === "all" || issue.impact === severity) &&
      (category === "all" || issue.category === category) &&
      (criterion === "all" || issue.wcag.includes(criterion)) &&
      (status === "all" || issue.status === status) &&
      (verification === "all" ||
        verificationStatus(issue, baseline, isFollowUp) === verification)
    );
  });
  const selectedIssue =
    filteredIssues.find((issue) => issue.key === selectedKey) ||
    filteredIssues[0] ||
    null;

  function selectIssue(issue) {
    setSelectedKey(issue.key);
    setMobileDetailOpen(true);
  }

  return (
    <section className="issues-workspace" aria-labelledby="issues-heading">
      <div className="chart-heading">
        <div>
          <h3 id="issues-heading">Issues</h3>
          <p className="field-help">
            Findings are grouped across viewports. Select a row to inspect
            evidence and open its capture.
          </p>
        </div>
        <span className="metadata">{filteredIssues.length} findings</span>
      </div>
      <div className="issues-filters" aria-label="Issue filters">
        <label className="issue-search">
          Search findings
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search title, selector, or WCAG criterion"
          />
        </label>
        <Filter
          label="Severity"
          value={severity}
          onChange={setSeverity}
          options={[
            ["all", "All severities"],
            ["critical", "Critical"],
            ["serious", "Serious"],
            ["moderate", "Moderate"],
            ["minor", "Minor"],
            ["needs_review", "Needs review"],
          ]}
        />
        <Filter
          label="Category"
          value={category}
          onChange={setCategory}
          options={[
            ["all", "All categories"],
            ...categories.map((value) => [value, value]),
          ]}
        />
        <Filter
          label="WCAG criterion"
          value={criterion}
          onChange={setCriterion}
          options={[
            ["all", "All criteria"],
            ...criteria.map((value) => [value, value]),
          ]}
        />
        <Filter
          label="Viewport"
          value={viewport}
          onChange={setViewport}
          options={[
            ["all", "All viewports"],
            ...viewports.map((item) => [item.name, readable(item.name)]),
          ]}
        />
        <Filter
          label="Status"
          value={status}
          onChange={setStatus}
          options={[
            ["all", "All statuses"],
            ["fail", "Failed"],
            ["needs_review", "Needs review"],
          ]}
        />
        <Filter
          label="Verification"
          value={verification}
          onChange={setVerification}
          options={[
            ["all", "All verification"],
            ["Still detected", "Still detected"],
            ["Needs review", "Needs review"],
            ["Could not verify", "Could not verify"],
          ]}
        />
      </div>
      <div
        className={`issues-split${mobileDetailOpen ? " is-detail-open" : ""}`}
      >
        <div className="issue-list-pane">
          <div className="issue-list-heading">
            <h4>Finding groups</h4>
            <span className="metadata">{filteredIssues.length} results</span>
          </div>
          <ul id="issue-list" className="issue-list" aria-label="Finding groups">
            {filteredIssues.map((issue) => {
              const verificationResult = verificationStatus(issue, baseline, isFollowUp);
              return (
                <li key={issue.key}>
                  <button
                    type="button"
                    className={`issue-list-item${selectedIssue?.key === issue.key ? " is-selected" : ""}`}
                    aria-pressed={selectedIssue?.key === issue.key}
                    onClick={() => selectIssue(issue)}
                  >
                    <span className="issue-list-item-heading">
                      <strong>{issue.title}</strong>
                      <Badge value={issue.impact} />
                    </span>
                    <span className="issue-list-meta">
                      {issue.category}
                      {issue.wcag.length > 0
                        ? ` · WCAG ${issue.wcag.join(", ")}`
                        : ""}
                    </span>
                    <span className="issue-list-meta">
                      {issue.occurrences.map((item) => readable(item.viewport)).join(" · ")}
                      {" · "}
                      {issue.occurrences.reduce(
                        (count, item) =>
                          count +
                          (item.evidence.node
                            ? 1
                            : item.evidence.rule
                              ? list(item.evidence.rule.nodes).length
                              : 1),
                        0,
                      )}{" "}
                      occurrence(s)
                    </span>
                    <span className="issue-list-status">
                      <Badge concept="Status" value={issue.status} />
                      <Badge concept="Verification" value={verificationResult} />
                    </span>
                  </button>
                </li>
              );
            })}
            {!filteredIssues.length && (
              <li className="issue-list-empty">
                <p className="empty-state">No findings match these filters.</p>
              </li>
            )}
          </ul>
        </div>
        <aside
          className="issue-detail-pane"
          aria-label="Selected finding details"
          aria-live="polite"
        >
          {selectedIssue ? (
            <>
              <div className="issue-detail-heading">
                <button
                  type="button"
                  className="secondary issue-back"
                  onClick={() => setMobileDetailOpen(false)}
                >
                  Back to findings
                </button>
                <p className="eyebrow">{selectedIssue.category}</p>
                <h4>{selectedIssue.title}</h4>
                <div className="issue-detail-badges">
                  <Badge value={selectedIssue.status} />
                  <Badge
                    concept="Verification"
                    value={verificationStatus(selectedIssue, baseline, isFollowUp)}
                  />
                </div>
                {selectedIssue.wcag.length > 0 && (
                  <p className="field-help">
                    WCAG {selectedIssue.wcag.join(", ")}
                  </p>
                )}
              </div>
              <IssueDetails
                issue={selectedIssue}
                onShowScreenshot={onShowScreenshot}
              />
              <p className="field-help">
                A finding missing from a later scan is not, by itself, proof
                that a specific change resolved it.
              </p>
            </>
          ) : (
            <p className="empty-state">
              No issue details are available for this selection.
            </p>
          )}
        </aside>
      </div>
    </section>
  );
}
