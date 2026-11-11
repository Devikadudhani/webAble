import React from "react";
export function Header({ onNew, hasResults = false }) {
  return (
    <header className="site-header">
      <a className="brand" href="/">
        WebAble
      </a>
      <nav className="site-nav" aria-label="Main navigation">
        {hasResults ? (
          <>
            <a href="#baseline-website">Captured views</a>
            <a href="#results">Report</a>
          </>
        ) : (
          <>
            <a href="#how-it-works">How it works</a>
            <a href="#audit-form">Audit</a>
            <span className="agent-unavailable">Agent · unavailable</span>
          </>
        )}
      </nav>
      {hasResults && (
        <button type="button" className="header-new secondary" onClick={onNew}>
          + New audit
        </button>
      )}
    </header>
  );
}
export function AuditForm({
  form,
  setForm,
  loading,
  response,
  onSubmit,
  hidden = false,
}) {
  return (
    <form id="audit-form" onSubmit={onSubmit} hidden={hidden}>
      <section className="panel" aria-label="Start an audit">
        <label className="field-label" htmlFor="audit-url">
          Website URL <span aria-hidden="true">*</span>
        </label>
        <input
          id="audit-url"
          type="text"
          inputMode="url"
          autoComplete="url"
          required
          placeholder="example.com"
          value={form.url}
          onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))}
        />
        <label className="check-row ai-opt-in">
          <input
            id="ai-assistance-opt-in"
            type="checkbox"
            checked={Boolean(form.aiOptIn)}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                aiOptIn: event.target.checked,
              }))
            }
          />
          <span>
            <strong>Optional AI explanations and visual review</strong>
            <span className="field-help">
              If selected, grouped findings, selectors, short markup snippets,
              and eligible cropped screenshots may be sent to Groq and Gemini.
              AI output is advisory and does not change audit findings. Leave
              unchecked to keep all audit evidence within WebAble.
            </span>
          </span>
        </label>
        <div className="url-actions">
          <button id="submit-button" disabled={loading}>
            {loading
              ? "Auditing website…"
              : response
                ? "Re-scan website →"
                : "Audit website →"}
          </button>
          <span>Public websites · axe-core · 3 viewports · Browser tested</span>
        </div>
      </section>
      <div className="form-actions">
        <p>
          Enter a public website URL. HTTPS is added if you omit the scheme.
          Protected pages and sites that block automated access can’t be tested.
        </p>
      </div>
    </form>
  );
}
export function AuditLoading({ url }) {
  return (
    <section id="audit-loading" className="panel" role="status">
      <p className="eyebrow">WEBABLE AUDIT · IN PROGRESS</p>
      <h2>Auditing website</h2>
      <p className="audit-target">{url}</p>
      <div className="indeterminate" aria-hidden="true" />
      <p>
        The server does not report detailed stage progress, so this indicator
        is intentionally indeterminate. The audit captures desktop, tablet,
        and mobile before returning its evidence.
      </p>
      <ul className="stages">
        {[
          "Capture browser views",
          "Analyze accessibility and responsive evidence",
          "Consolidate findings and verification context",
        ].map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>
      <p>
        A 404 from the website being audited may be recorded as a finding; it
        does not necessarily mean your audit request failed.
      </p>
    </section>
  );
}
