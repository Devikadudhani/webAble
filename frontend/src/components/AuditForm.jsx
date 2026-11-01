import React from "react";
import { Evidence } from "./Common";
import { list, readable } from "../utils";
export function Header({ onNew }) {
  return (
    <header className="site-header">
      <a className="brand" href="/">
        WebAble
      </a>
      <button type="button" className="header-new secondary" onClick={onNew}>+ New audit</button>
    </header>
  );
}
export function OwnerQuestionnaire({
  catalog,
  questions,
  form,
  setForm,
  answers,
  setAnswers,
}) {
  const update = (id, key, value) =>
    setAnswers((old) => ({ ...old, [id]: { ...old[id], [key]: value } }));
  return (
    <details id="website-context" className="context-disclosure">
      <summary>
        Add site context → <span>Optional</span>
      </summary>
      <p>
        Owner context improves evaluation but does not establish WCAG
        conformance. Do not include secrets or personal data.
      </p>
      <section className="panel split-fields">
        {[
          [
            "pages",
            "representative-urls",
            "Representative public pages",
            "One public URL per line",
          ],
          [
            "journeys",
            "journeys",
            "Important user journeys",
            "One journey per line: task name | public URLs separated by commas",
          ],
        ].map(([key, id, label, placeholder]) => (
          <label key={key} className="field-label" htmlFor={id}>
            {label}
            <textarea
              id={id}
              rows="3"
              placeholder={placeholder}
              value={form[key]}
              onChange={(e) =>
                setForm((f) => ({ ...f, [key]: e.target.value }))
              }
            />
            <span className="field-help">
              Public context only. No credentials, query strings or private
              tokens.
            </span>
          </label>
        ))}
      </section>
      <section className="panel">
        <h2>What does this site include?</h2>
        <p>
          Select features you know are present. Browser discovery may identify
          more.
        </p>
        <fieldset className="feature-grid">
          <legend className="visually-hidden">Website features</legend>
          {catalog.map((feature) => (
            <div className="feature-choice" key={feature.feature_id}>
              <span className="feature-name">{feature.label}</span>
              <div
                className="feature-options"
                role="group"
                aria-label={`${feature.label}: owner-reported presence`}
              >
                {[
                  ["yes", "Yes"],
                  ["no", "No"],
                  ["not_sure", "Not sure"],
                ].map(([value, label]) => (
                  <label key={value} className="feature-option">
                    <input
                      type="radio"
                      name={`feature-${feature.feature_id}`}
                      value={value}
                      checked={
                        (form.features[feature.feature_id] == null
                          ? "not_sure"
                          : form.features[feature.feature_id]
                            ? "yes"
                            : "no") === value
                      }
                      onChange={() =>
                        setForm((f) => ({
                          ...f,
                          features: {
                            ...f.features,
                            [feature.feature_id]:
                              value === "not_sure" ? null : value === "yes",
                          },
                        }))
                      }
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          ))}
        </fieldset>
        <label className="check-row">
          <input
            id="features-complete"
            type="checkbox"
            checked={form.complete}
            onChange={(e) =>
              setForm((f) => ({ ...f, complete: e.target.checked }))
            }
          />
          I’ve reviewed the feature list
        </label>
      </section>
      {questions.length > 0 && (
        <section id="questions-panel" className="panel">
          <h2>A few relevant questions</h2>
          <p>
            Questions adapt to your answers and browser discoveries. Previous
            answers stay with this audit.
          </p>
          {questions.map((q) => (
            <fieldset className="question-card" key={q.question_id}>
              <legend>{q.prompt}</legend>
              <div className="answer-options">
                {list(q.answer_options).map((value) => (
                  <label key={value}>
                    <input
                      type="radio"
                      name={`answer-${q.question_id}`}
                      value={value}
                      checked={answers[q.question_id]?.answer === value}
                      onChange={() => update(q.question_id, "answer", value)}
                    />
                    {readable(value)}
                  </label>
                ))}
              </div>
              {q.helper_text && <p>{q.helper_text}</p>}
              {q.answer_interpretation && (
                <Evidence
                  title="How answers are interpreted"
                  data={q.answer_interpretation}
                />
              )}
              <label className="question-label">
                Optional explanation or relevant public page URLs
                <textarea
                  rows="2"
                  maxLength="2000"
                  placeholder="Context only; do not include sensitive information"
                  value={answers[q.question_id]?.explanation || ""}
                  onChange={(e) =>
                    update(q.question_id, "explanation", e.target.value)
                  }
                />
              </label>
              <label className="question-label">
                Related public URLs (optional, one per line)
                <textarea
                  rows="2"
                  maxLength="2000"
                  value={answers[q.question_id]?.pageUrls || ""}
                  onChange={(e) =>
                    update(q.question_id, "pageUrls", e.target.value)
                  }
                />
              </label>
            </fieldset>
          ))}
        </section>
      )}
      <section className="panel optional-panel">
        <label className="field-label" htmlFor="free-text">
          Anything else we should know?
        </label>
        <textarea
          id="free-text"
          rows="3"
          maxLength="2000"
          placeholder="Share non-sensitive context only"
          value={form.context}
          onChange={(e) => setForm((f) => ({ ...f, context: e.target.value }))}
        />
      </section>
    </details>
  );
}
export function AuditForm({
  form,
  setForm,
  loading,
  ready,
  response,
  onSubmit,
  ...props
}) {
  return (
    <form id="audit-form" onSubmit={onSubmit}>
      <section className="panel" aria-label="Start an audit">
        <label className="field-label" htmlFor="audit-url">
          Website URL <span aria-hidden="true">*</span>
        </label>
        <input
          id="audit-url"
          type="url"
          autoComplete="url"
          required
          placeholder="https://example.com"
          value={form.url}
          onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))}
        />
        <div className="url-actions">
          <button id="submit-button" disabled={loading || !ready}>
            {loading
              ? "Running audit…"
              : response
                ? "Save answers & update audit"
                : "Run audit →"}
          </button>
          <span>WCAG 2.2 · axe-core · 3 viewports · Browser tested</span>
        </div>
      </section>
      <OwnerQuestionnaire {...props} form={form} setForm={setForm} />
      <div className="form-actions">
        <p>
          Protected pages can’t be tested without access. Don’t enter passwords
          here; use a public representative page or arrange a separately
          authorized review.
        </p>
      </div>
    </form>
  );
}
export function AuditLoading() {
  return (
    <section id="audit-loading" className="panel" role="status">
      <p className="eyebrow">AUDIT IN PROGRESS</p>
      <h2>Waiting for your audit results</h2>
      <div className="indeterminate" aria-hidden="true" />
      <p>
        Your audit may be queued while other audits finish. Checks run on the
        server and cover desktop, tablet, and mobile, so results can take
        several minutes. A 404 from the website being audited may be recorded
        as a finding; it does not necessarily mean your audit failed.
      </p>
      <ul className="stages">
        {[
          "Opening website",
          "Testing desktop",
          "Testing tablet",
          "Testing mobile",
          "Running accessibility checks",
          "Building evaluation",
        ].map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>
    </section>
  );
}
