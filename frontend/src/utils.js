export const list = (value) => (Array.isArray(value) ? value : []);
export const readable = (value) =>
  String(value ?? "Unavailable").replaceAll("_", " ");
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
