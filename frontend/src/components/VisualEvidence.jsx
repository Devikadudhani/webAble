import React, { useCallback, useEffect, useMemo, useState } from "react";
import { comparableFindings, list, readable, screenshotUrl } from "../utils";

const deviceOrder = ["desktop", "tablet", "mobile"];

function annotationBounds(viewport, highlight) {
  const width = Number(viewport?.viewport?.width) || 1;
  const height = Number(viewport?.viewport?.height) || 1;
  const bounds = highlight?.bounds;
  const left = Math.max(0, Number(bounds?.left) || 0);
  const top = Math.max(0, Number(bounds?.top) || 0);
  const right = Math.min(width, (Number(bounds?.left) || 0) + (Number(bounds?.width) || 0));
  const bottom = Math.min(height, (Number(bounds?.top) || 0) + (Number(bounds?.height) || 0));
  return right > left && bottom > top
    ? { x: left, y: top, width: right - left, height: bottom - top }
    : null;
}

function orderedNames(viewports) {
  const names = new Set(list(viewports).map((viewport) => viewport.name));
  return [
    ...deviceOrder.filter((name) => names.has(name)),
    ...[...names].filter((name) => !deviceOrder.includes(name)),
  ];
}

function CapturedImage({ viewport, title, highlight, onEnlarge, onImageStatus }) {
  const [unavailable, setUnavailable] = useState(false);
  const imageUrl = screenshotUrl(viewport?.screenshot_ref);
  useEffect(() => {
    setUnavailable(false);
    if (!imageUrl) onImageStatus?.(viewport?.name, false);
  }, [imageUrl, onImageStatus]);

  if (!imageUrl || unavailable)
    return (
      <div className="visual-empty" role="status">
        <strong>Screenshot unavailable</strong>
        <span>
          {viewport?.screenshot_ref
            ? "The saved capture could not be loaded."
            : "No screenshot was captured for this viewport."}
        </span>
      </div>
    );

  const width = Number(viewport?.viewport?.width) || 1;
  const height = Number(viewport?.viewport?.height) || 1;
  const annotation = annotationBounds(viewport, highlight);

  return (
    <div
      className="screenshot-stage"
      style={{ aspectRatio: `${width} / ${height}` }}
    >
      <img
        src={imageUrl}
        alt={`${readable(viewport.name)} website capture, ${width} by ${height} CSS pixels`}
        onLoad={() => onImageStatus?.(viewport?.name, true)}
        onError={() => {
          setUnavailable(true);
          onImageStatus?.(viewport?.name, false);
        }}
      />
      {annotation && (
        <svg
          className="screenshot-annotations"
          viewBox={`0 0 ${width} ${height}`}
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <rect
            x={annotation.x}
            y={annotation.y}
            width={annotation.width}
            height={annotation.height}
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      )}
      <button
        className="enlarge-screenshot secondary"
        type="button"
        onClick={() => onEnlarge(imageUrl, title, highlight, viewport)}
      >
        Enlarge screenshot
      </button>
    </div>
  );
}

function Snapshot({ title, viewport, highlight, onEnlarge, onImageStatus }) {
  return (
    <article className="capture-panel">
      <div className="capture-panel-heading">
        <div>
          <h4>{title}</h4>
          <span className="metadata">
            {viewport?.viewport?.width && viewport?.viewport?.height
              ? `${viewport.viewport.width} × ${viewport.viewport.height}`
              : "Viewport size unavailable"}
          </span>
        </div>
      </div>
      <CapturedImage
        viewport={viewport}
        title={title}
        highlight={highlight}
        onEnlarge={onEnlarge}
        onImageStatus={onImageStatus}
      />
      {highlight && (
        <p className="annotation-caption">
          Highlighted: {highlight.label}. Coordinates were captured for this
          finding.
        </p>
      )}
    </article>
  );
}

function occurrenceViewports(finding) {
  return list(finding.occurrences).length
    ? list(finding.occurrences)
    : finding.viewport
      ? [{ viewport: finding.viewport, signature: null }]
      : [];
}

function verificationStatus(finding, currentFindings, currentViewports) {
  const current = currentFindings.find((item) => item.key === finding.key);
  if (current) {
    const baselineOccurrences = occurrenceViewports(finding);
    const currentOccurrences = occurrenceViewports(current);
    const sharedViewport = baselineOccurrences.find((item) =>
      currentOccurrences.some((currentItem) => currentItem.viewport === item.viewport),
    );
    if (
      sharedViewport?.signature &&
      currentOccurrences.some(
        (item) =>
          item.viewport === sharedViewport.viewport &&
          item.signature &&
          item.signature !== sharedViewport.signature,
      )
    )
      return "Changed";
    return "Still detected";
  }
  const categoryStatus = {
    axe: (viewport) => viewport.accessibility_scan?.status,
    target_size: (viewport) => viewport.target_size_audit?.status,
    overflow: (viewport) => viewport.finding_normalization?.status,
    functional: (viewport) => viewport.functional_ux_audit?.status,
  }[finding.category];
  const canVerify = occurrenceViewports(finding).every((occurrence) => {
    const viewport = currentViewports.find(
      (item) => item.name === occurrence.viewport,
    );
    return (
      viewport?.capture_outcome === "completed" &&
      categoryStatus?.(viewport) === "available"
    );
  });
  return canVerify ? "Not detected" : "Could not verify";
}

export default function VisualEvidence({
  baseline,
  response,
  scanId,
  persisted,
  evidenceRequest,
  onEvidenceRequest,
}) {
  const [selectedName, setSelectedName] = useState("");
  const [mode, setMode] = useState("before");
  const [highlight, setHighlight] = useState(null);
  const [zoom, setZoom] = useState(null);
  const [baselineImageAvailability, setBaselineImageAvailability] = useState({});
  const printAll =
    typeof document !== "undefined" &&
    document.body.classList.contains("printing-report");
  const names = orderedNames(baseline?.viewports);
  const isFollowUp = Boolean(baseline?.scan_id && scanId !== baseline.scan_id);
  const baselineScoringVersion = baseline?.scoring_configuration_version;
  const currentScoringVersion = response?.scoring?.scoring_configuration_version;
  const scoringVersionsMatch =
    Boolean(baselineScoringVersion) &&
    Boolean(currentScoringVersion) &&
    baselineScoringVersion === currentScoringVersion;
  const currentViewports = list(response?.viewports);
  const baselineViewport = list(baseline?.viewports).find(
    (viewport) => viewport.name === selectedName,
  );
  const baselineScreenshotAvailable =
    Boolean(screenshotUrl(baselineViewport?.screenshot_ref)) &&
    baselineImageAvailability[selectedName] !== false;
  const currentViewport = currentViewports.find(
    (viewport) => viewport.name === selectedName,
  );
  const allCurrentNames = orderedNames(currentViewports);
  const availableNames = [...new Set([...names, ...allCurrentNames])];
  const currentFindings = useMemo(
    () => comparableFindings(response),
    [response],
  );
  const currentViewportFindings = currentFindings.filter(
    (finding) =>
      occurrenceViewports(finding).some(
        (occurrence) => occurrence.viewport === selectedName,
      ),
  );
  const coordinateFindings = currentViewportFindings.filter(
    (finding) => {
      const occurrence = occurrenceViewports(finding).find(
        (item) => item.viewport === selectedName,
      );
      return (
        finding.category === "target_size" &&
        occurrence?.bounds &&
        [
          occurrence.bounds.left,
          occurrence.bounds.top,
          occurrence.bounds.width,
          occurrence.bounds.height,
        ]
        .every((value) => Number.isFinite(value)),
      );
    },
  );
  const updateBaselineImageAvailability = useCallback((name, available) => {
    setBaselineImageAvailability((previous) => ({
      ...previous,
      [name]: available,
    }));
  }, []);

  useEffect(() => {
    if (!availableNames.includes(selectedName))
      setSelectedName(availableNames[0] || "");
  }, [availableNames.join("|"), selectedName]);

  useEffect(() => {
    if (!isFollowUp) setMode("before");
    else if (!baselineScreenshotAvailable) setMode("after");
    else setMode("side-by-side");
  }, [baselineScreenshotAvailable, isFollowUp]);

  useEffect(() => {
    if (!evidenceRequest?.name) return;
    setSelectedName(evidenceRequest.name);
    setMode("after");
    setHighlight(
      evidenceRequest.bounds
        ? {
            bounds: evidenceRequest.bounds,
            label: evidenceRequest.label || "Selected finding",
          }
        : null,
    );
  }, [evidenceRequest?.key]);

  useEffect(() => {
    if (!zoom) return undefined;
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setZoom(null);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [zoom]);

  function requestEvidence(name, bounds, label) {
    setSelectedName(name);
    setMode("after");
    setHighlight(bounds ? { bounds, label } : null);
    onEvidenceRequest?.(name, bounds, label);
  }

  const baselineFindingStates = list(baseline?.findings).map((finding) => ({
    ...finding,
    status: verificationStatus(
      finding,
      currentFindings,
      currentViewports,
    ),
  }));
  const confirmedFindingStates = baselineFindingStates.filter(
    (finding) => finding.category === "axe" || finding.category === "functional",
  );
  const contextualFindingStates = baselineFindingStates.filter(
    (finding) =>
      finding.category === "target_size" || finding.category === "overflow",
  );
  const newFindings = currentFindings.filter(
    (finding) =>
      !list(baseline?.findings).some((baselineFinding) => baselineFinding.key === finding.key),
  );

  return (
    <section
      id="baseline-website"
      className="visual-evidence"
      aria-labelledby="visual-evidence-title"
    >
      <div className="visual-evidence-heading">
        <div>
          <p className="eyebrow">VISUAL EVIDENCE</p>
          <h3 id="visual-evidence-title">Baseline Website</h3>
          <p>
            The first saved scan is kept as the before view. Re-scan after
            changes to compare it with the latest captured website. Run the
            first scan before editing the site to establish a true pre-change
            baseline.
          </p>
        </div>
        {isFollowUp && (
          <div className="comparison-controls" role="group" aria-label="Screenshot comparison">
            {[
              ["before", "Before"],
              ["after", "After"],
              ["side-by-side", "Side by side"],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={mode === value ? "comparison-option selected" : "comparison-option"}
                aria-pressed={mode === value}
                disabled={
                  (value === "before" || value === "side-by-side") &&
                  !baselineScreenshotAvailable
                }
                onClick={() => {
                  setMode(value);
                  setHighlight(null);
                }}
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      {availableNames.length > 0 ? (
        <>
          <div className="viewport-selector" role="group" aria-label="Captured viewport">
            {availableNames.map((name) => (
              <button
                key={name}
                type="button"
                aria-pressed={selectedName === name}
                onClick={() => {
                  setSelectedName(name);
                  setHighlight(null);
                }}
              >
                {readable(name)}
              </button>
            ))}
          </div>

          <div className={`visual-captures ${mode === "side-by-side" && isFollowUp && baselineScreenshotAvailable ? "is-comparison" : ""}`}>
            {isFollowUp &&
              baselineScreenshotAvailable &&
              (mode === "before" || mode === "side-by-side") && (
              <Snapshot
                title="Before · First saved scan"
                viewport={baselineViewport}
                highlight={mode === "before" ? highlight : null}
                onImageStatus={updateBaselineImageAvailability}
                onEnlarge={(src, title, selected, viewport) => setZoom({ src, title, highlight: selected, viewport })}
              />
            )}
            {(mode === "after" || mode === "side-by-side") && isFollowUp && (
              <Snapshot
                title="After · Latest scan"
                viewport={currentViewport}
                highlight={highlight}
                onEnlarge={(src, title, selected, viewport) => setZoom({ src, title, highlight: selected, viewport })}
              />
            )}
            {isFollowUp &&
              !baselineScreenshotAvailable && (
                <div className="visual-empty" role="status">
                  <strong>Baseline screenshot unavailable</strong>
                  <span>
                    A before/after comparison cannot be shown for this viewport.
                    The latest capture is still available.
                  </span>
                </div>
              )}
            {!isFollowUp && baselineScreenshotAvailable && (
              <Snapshot
                title="First saved scan"
                viewport={baselineViewport}
                highlight={highlight}
                onImageStatus={updateBaselineImageAvailability}
                onEnlarge={(src, title, selected, viewport) => setZoom({ src, title, highlight: selected, viewport })}
              />
            )}
            {!isFollowUp && !baselineScreenshotAvailable && (
              <div className="visual-empty" role="status">
                <strong>Baseline screenshot unavailable</strong>
                <span>No usable saved screenshot exists for this viewport.</span>
              </div>
            )}
          </div>
          {printAll && (
            <div className="print-all-captures">
              {availableNames.map((name) => {
                const before = list(baseline?.viewports).find(
                  (viewport) => viewport.name === name,
                );
                const after = currentViewports.find(
                  (viewport) => viewport.name === name,
                );
                const initialCapture = before || (!isFollowUp ? after : null);
                return (
                  <section className="print-viewport-captures" key={name}>
                    <h4>{readable(name)} captured views</h4>
                    {isFollowUp ? (
                      <Snapshot
                        title="Before · First saved scan"
                        viewport={before}
                        onEnlarge={() => {}}
                      />
                    ) : (
                      <Snapshot
                        title="First saved scan"
                        viewport={initialCapture}
                        onEnlarge={() => {}}
                      />
                    )}
                    {isFollowUp && after && (
                      <Snapshot
                        title="After · Latest scan"
                        viewport={after}
                        onEnlarge={() => {}}
                      />
                    )}
                  </section>
                );
              })}
            </div>
          )}
          {isFollowUp && (
            <p className="verification-note">
              A re-scan shows what the automated checks observed; it does not
              prove that a code change caused the result or establish WCAG
              conformance.
              {!scoringVersionsMatch && (
                <> Score history is not compared because the baseline scoring
                  configuration ({baselineScoringVersion || "unknown"}) differs
                  from the current configuration ({currentScoringVersion || "unknown"}).</>
              )}
            </p>
          )}

          <details className="visual-finding-links">
            <summary>
              Contextual observations · {readable(selectedName)} ·{" "}
              {coordinateFindings.length} coordinate-backed candidate(s)
            </summary>
            <p className="field-help">
              These heuristic candidates are context for review, not confirmed
              defects. Confirmed findings and criteria needing review appear in
              the audit sections.
            </p>
            {coordinateFindings.length > 0 ? (
              <ul>
                {coordinateFindings.map((finding) => {
                  const occurrence = occurrenceViewports(finding).find(
                    (item) => item.viewport === selectedName,
                  );
                  return (
                  <li key={finding.key}>
                    <button
                      type="button"
                      className="text-action"
                      onClick={() =>
                        requestEvidence(
                          selectedName,
                          occurrence.bounds,
                          finding.label,
                        )
                      }
                    >
                      Highlight {finding.label}
                    </button>
                  </li>
                  );
                })}
              </ul>
            ) : (
              <p className="field-help">
                No findings with reliable element coordinates are available for
                this viewport. Issue details can still link to its capture.
              </p>
            )}
          </details>

          {isFollowUp && (
            <section className="verification-summary" aria-label="Re-scan verification status">
              <div className="chart-heading">
                <h4>Verification status</h4>
                <span className="metadata">
                  {baselineFindingStates.length} baseline findings compared
                </span>
              </div>
              {confirmedFindingStates.length ? (
                <ul className="verification-list">
                  {confirmedFindingStates.slice(0, 30).map((finding) => (
                    <li key={finding.key}>
                      <span>
                        {occurrenceViewports(finding)
                          .map((item) => readable(item.viewport))
                          .join(", ")}{" "}
                        · {finding.label}
                      </span>
                      <strong className={`verification-${finding.status.toLowerCase().replaceAll(" ", "-")}`}>
                        {finding.status}
                      </strong>
                      <button
                        type="button"
                        className="text-action"
                        onClick={() => {
                          const occurrence = occurrenceViewports(finding)[0];
                          requestEvidence(
                            occurrence?.viewport,
                            occurrence?.bounds,
                            finding.label,
                          );
                        }}
                      >
                        View capture
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="empty-state">
                  The baseline has no comparable confirmed axe or functional
                  findings.
                </p>
              )}
              {confirmedFindingStates.length > 30 && (
                <p className="field-help">
                  Showing 30 of {confirmedFindingStates.length} confirmed
                  findings.
                </p>
              )}
              {contextualFindingStates.length > 0 && (
                <details className="contextual-verification">
                  <summary>
                    Contextual observations · {contextualFindingStates.length}
                  </summary>
                  <p className="field-help">
                    These are candidate observations, not confirmed issues.
                    Missing candidates are not treated as proof of resolution.
                  </p>
                  <ul className="verification-list">
                    {contextualFindingStates.slice(0, 30).map((finding) => (
                      <li key={finding.key}>
                        <span>
                          {occurrenceViewports(finding)
                            .map((item) => readable(item.viewport))
                            .join(", ")}{" "}
                          · {finding.label}
                        </span>
                        <strong className={`verification-${finding.status.toLowerCase().replaceAll(" ", "-")}`}>
                          {finding.status}
                        </strong>
                      </li>
                    ))}
                  </ul>
                  {contextualFindingStates.length > 30 && (
                    <p className="field-help">
                      Showing 30 of {contextualFindingStates.length} contextual
                      observations.
                    </p>
                  )}
                </details>
              )}
              <p className="verification-note">
                “Not detected” means absent from the comparable completed
                checks; it does not prove that a change resolved the finding.
              </p>
              {newFindings.length > 0 && (
                <p className="field-help">
                  {newFindings.length} finding identity/identities were not
                  present in the comparable baseline evidence.
                </p>
              )}
              {baseline.findings_truncated && (
                <p className="field-help">
                  Baseline finding comparison was capped at 1,000 observations.
                </p>
              )}
            </section>
          )}
        </>
      ) : (
        <div className="visual-empty" role="status">
          <strong>No captured views</strong>
          <span>
            This report has no desktop, tablet, or mobile screenshots to display.
          </span>
        </div>
      )}
      {!persisted && (
        <p className="storage-warning" role="status">
          This baseline is available for this report, but browser storage is
          unavailable, so it may not be retained after leaving this page.
        </p>
      )}

      {zoom && (
        <div
          className="screenshot-modal-backdrop"
          role="presentation"
          onClick={(event) => {
            if (event.target === event.currentTarget) setZoom(null);
          }}
        >
          <section
            className="screenshot-modal"
            role="dialog"
            aria-modal="true"
            aria-label={`Enlarged ${zoom.title}`}
          >
            <div className="screenshot-modal-heading">
              <h3>{zoom.title}</h3>
              <button
                type="button"
                className="secondary"
                autoFocus
                onClick={() => setZoom(null)}
              >
                Close
              </button>
            </div>
            <div
              className="screenshot-modal-stage"
              style={{
                aspectRatio: `${zoom.viewport?.viewport?.width || 1} / ${zoom.viewport?.viewport?.height || 1}`,
              }}
            >
              <img src={zoom.src} alt={`Enlarged ${zoom.title}`} />
              {annotationBounds(zoom.viewport, zoom.highlight) && (
                <svg
                  className="screenshot-annotations"
                  viewBox={`0 0 ${zoom.viewport.viewport.width} ${zoom.viewport.viewport.height}`}
                  preserveAspectRatio="none"
                  aria-hidden="true"
                >
                  <rect
                    {...annotationBounds(zoom.viewport, zoom.highlight)}
                    vectorEffect="non-scaling-stroke"
                  />
                </svg>
              )}
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
