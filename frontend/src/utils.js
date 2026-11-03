export const list = (value) => (Array.isArray(value) ? value : []);
export const readable = (value) =>
  ({ valid_high_coverage: "High coverage", valid_moderate_coverage: "Provisional", provisional: "Provisional", low_evidence: "Low evidence", very_limited_evidence: "Very limited evidence", insufficient_evidence: "Score unavailable" }[value] || String(value ?? "Unavailable").replaceAll("_", " "));
export const format = (value) =>
  typeof value === "number" && Number.isFinite(value)
    ? String(Math.round(value * 10) / 10)
    : "Unavailable";
export const lines = (value) =>
  value
    .split(/\r?\n/)
    .map((v) => v.trim())
    .filter(Boolean);
export const implemented = (d) =>
  d.implemented !== false && d.scoring_status !== "not_implemented";
export function buildRequest(form, answers) {
  return {
    url: form.url.trim(),
    ai_assistance_opt_in: Boolean(form.aiOptIn),
    accessibility_context: {
      representative_page_urls: lines(form.pages),
      user_journeys: lines(form.journeys).map((line) => {
        const [name = "", urls = ""] = line.split("|", 2);
        return {
          name: name.trim().slice(0, 120),
          description: null,
          page_urls: urls
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        };
      }),
      feature_presence: form.features,
      feature_inventory_completed: form.complete,
      answers: Object.entries(answers)
        .filter(([, a]) => a.answer)
        .map(([question_id, a]) => ({
          question_id,
          answer: a.answer,
          explanation: a.explanation?.trim() || null,
          page_urls: lines(a.pageUrls || ""),
        })),
      free_text: form.context.trim() || null,
    },
  };
}
export function groupIssues(viewports, severity, viewport) {
  const grouped = new Map();
  for (const v of viewports)
    for (const rule of list(v.accessibility_scan?.violations)) {
      if (
        (viewport !== "all" && v.name !== viewport) ||
        (severity !== "all" && rule.impact !== severity)
      )
        continue;
      const id = rule.rule_id || rule.id;
      if (!grouped.has(id)) grouped.set(id, { rule, occurrences: [] });
      grouped.get(id).occurrences.push({ viewport: v.name, rule });
    }
  return [...grouped.values()];
}

const BASELINE_STORAGE_PREFIX = "webable.visual-baseline.v1:";
const MAX_BASELINE_FINDINGS = 1_000;

export function screenshotUrl(reference) {
  if (typeof reference !== "string") return null;
  const filename = reference.split("/").pop();
  if (
    !/^(?:[a-f0-9]{32}|scenario_[A-Za-z0-9_-]+_[A-Za-z0-9_-]+_[A-Za-z0-9_-]+_[0-9]+x[0-9]+)\.png$/i.test(
      filename || "",
    )
  )
    return null;
  return `/captures/screenshots/${encodeURIComponent(filename)}`;
}

function baselineKey(url) {
  try {
    const parsed = new URL(url);
    return `${BASELINE_STORAGE_PREFIX}${encodeURIComponent(parsed.href)}`;
  } catch {
    return null;
  }
}

function collectComparableFindings(response) {
  const findings = new Map();
  const add = (
    viewport,
    category,
    label,
    identifier,
    bounds = null,
    signature = null,
  ) => {
    if (!identifier) return;
    const key = `${category}:${identifier}`;
    const finding = findings.get(key) || {
      key,
      category,
      label,
      occurrences: [],
    };
    const occurrence = { viewport, bounds, signature };
    if (
      !finding.occurrences.some(
        (existing) =>
          existing.viewport === viewport &&
          existing.signature === signature &&
          JSON.stringify(existing.bounds) === JSON.stringify(bounds),
      )
    )
      finding.occurrences.push(occurrence);
    findings.set(key, finding);
  };

  for (const viewport of list(response?.viewports)) {
    const name = viewport.name || "unknown";
    for (const rule of list(viewport.accessibility_scan?.violations)) {
      const ruleId = rule.rule_id || rule.id || "axe-rule";
      for (const node of list(rule.nodes)) {
        const target = JSON.stringify(node.target || []);
        add(
          name,
          "axe",
          rule.help || ruleId,
          `${ruleId}:${target}`,
          null,
          JSON.stringify({
            html: node.html || null,
            impact: node.impact || null,
            failure_summary: node.failure_summary || null,
          }),
        );
      }
    }
    for (const finding of list(viewport.target_size_audit?.findings)) {
      add(
        name,
        "target_size",
        finding.accessible_name || finding.selector || "Target-size finding",
        finding.selector,
        {
          left: finding.left_css_px,
          top: finding.top_css_px,
          width: finding.width_css_px,
          height: finding.height_css_px,
        },
        JSON.stringify({
          left: finding.left_css_px,
          top: finding.top_css_px,
          width: finding.width_css_px,
          height: finding.height_css_px,
        }),
      );
    }
    for (const finding of list(viewport.finding_normalization?.findings)) {
      add(
        name,
        "overflow",
        finding.selector || "Horizontal overflow finding",
        finding.selector,
        null,
        JSON.stringify(finding),
      );
    }
    for (const finding of list(viewport.functional_ux_audit?.findings)) {
      add(
        name,
        "functional",
        finding.accessible_label || finding.rule_id || "Functional finding",
        `${finding.rule_id}:${finding.element_selector}:${finding.destination_url || ""}`,
        null,
        JSON.stringify({
          failure_category: finding.failure_category,
          evidence: finding.evidence,
        }),
      );
    }
  }
  return [...findings.values()];
}

function normalizeBaselineFindings(findings) {
  const grouped = new Map();
  for (const finding of list(findings)) {
    if (Array.isArray(finding.occurrences)) {
      const current = grouped.get(finding.key) || {
        ...finding,
        occurrences: [],
      };
      for (const occurrence of finding.occurrences) {
        if (
          !current.occurrences.some(
            (item) =>
              item.viewport === occurrence.viewport &&
              item.signature === occurrence.signature &&
              JSON.stringify(item.bounds) === JSON.stringify(occurrence.bounds),
          )
        )
          current.occurrences.push(occurrence);
      }
      grouped.set(finding.key, current);
      continue;
    }

    const [category, , ...identityParts] = String(finding.key || "").split(":");
    const identity = identityParts.join(":");
    if (!category || !identity || !finding.viewport) continue;
    const key = `${category}:${identity}`;
    const current = grouped.get(key) || {
      key,
      category: finding.category || category,
      label: finding.label,
      occurrences: [],
    };
    current.occurrences.push({
      viewport: finding.viewport,
      bounds: finding.bounds || null,
      signature: null,
    });
    grouped.set(key, current);
  }
  return [...grouped.values()];
}

export function createVisualBaseline(response, scanId) {
  const findings = collectComparableFindings(response);
  return {
    version: 1,
    scan_id: scanId,
    requested_url: response.requested_url,
    captured_at: new Date().toISOString(),
    scoring_configuration_version:
      response.scoring?.scoring_configuration_version || null,
    viewports: list(response.viewports).map((viewport) => ({
      name: viewport.name,
      viewport: viewport.viewport,
      screenshot_ref: viewport.screenshot_ref || null,
      capture_outcome: viewport.capture_outcome,
    })),
    findings: findings.slice(0, MAX_BASELINE_FINDINGS),
    findings_truncated: findings.length > MAX_BASELINE_FINDINGS,
  };
}

export function getOrCreateVisualBaseline(response, scanId) {
  const created = createVisualBaseline(response, scanId);
  const key = baselineKey(response.requested_url);
  if (!key || typeof window === "undefined")
    return { baseline: created, persisted: false };

  try {
    const saved = window.localStorage.getItem(key);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (
        parsed?.version === 1 &&
        parsed.requested_url === response.requested_url &&
        Array.isArray(parsed.viewports) &&
        Array.isArray(parsed.findings)
      )
        return {
          baseline: {
            ...parsed,
            findings: normalizeBaselineFindings(parsed.findings),
          },
          persisted: true,
        };
    }
    window.localStorage.setItem(key, JSON.stringify(created));
    return { baseline: created, persisted: true };
  } catch {
    return { baseline: created, persisted: false };
  }
}

export function comparableFindings(response) {
  return collectComparableFindings(response).slice(0, MAX_BASELINE_FINDINGS);
}

export function limitations(response) {
  const scoring = response.scoring || {},
    evaluation = response.hybrid_evaluation || {};
  const result = new Set([
    ...list(scoring.limitations),
    ...list(evaluation.limitations),
    ...list(evaluation.details),
  ]);
  for (const v of list(response.viewports)) {
    if (v.capture_outcome !== "completed")
      result.add(`${readable(v.name)} capture: ${readable(v.capture_outcome)}`);
    for (const [key, audit] of Object.entries(v))
      if (audit && typeof audit === "object" && !Array.isArray(audit)) {
        if (
          /partial|error|unavailable|unsupported|not_tested/.test(
            audit.status || "",
          )
        )
          result.add(
            `${readable(v.name)} · ${readable(key)}: ${readable(audit.status)}`,
          );
        for (const text of [
          ...list(audit.details),
          ...list(audit.limitations),
          ...list(audit.candidate_limitations),
        ])
          result.add(`${readable(v.name)} · ${text}`);
      }
    for (const text of list(v.details))
      result.add(`${readable(v.name)} · ${text}`);
  }
  if (list(evaluation.criteria).some((c) => c.manual_review_required))
    result.add("Manual review is required for criteria in this evaluation.");
  return [...result];
}
