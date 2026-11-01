import React, { useState } from "react";
import { readable } from "../utils";
export function Badge({ value, concept }) {
  const tone = /^(fail|critical|serious|error|capture_failed|violation)$/.test(
    value,
  )
    ? "danger"
    : /^(pass|completed)$/.test(value)
      ? "positive"
      : /review|partial|provisional|insufficient|concern|timeout/.test(
            value || "",
          )
        ? "warning"
        : "neutral";
  return (
    <span className={`badge ${tone}`}>
      {concept && `${concept}: `}
      {readable(value)}
    </span>
  );
}
export function SafeLink({ url, children }) {
  try {
    const u = new URL(url);
    if (!["https:", "http:"].includes(u.protocol)) return null;
    return (
      <a
        className="documentation"
        href={u.href}
        target="_blank"
        rel="noopener noreferrer"
      >
        {children}
      </a>
    );
  } catch {
    return null;
  }
}
export function Paginated({ items, render, size = 15 }) {
  const [count, setCount] = useState(size);
  if (!items.length)
    return (
      <p className="empty-state">No evidence returned for this selection.</p>
    );
  return (
    <>
      {items.slice(0, count).map((item, i) => (
        <React.Fragment key={i}>{render(item, i)}</React.Fragment>
      ))}
      {count < items.length && (
        <button
          type="button"
          className="secondary show-more"
          onClick={() => setCount((n) => n + size)}
        >
          Show more ({items.length - count} remaining)
        </button>
      )}
    </>
  );
}
export function Disclosure({ title, children }) {
  const [open, setOpen] = useState(false);
  return (
    <details
      className="evidence-detail"
      open={open}
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>{title}</summary>
      {open && children}
    </details>
  );
}
export function Evidence({ title = "Supporting evidence", data }) {
  return (
    <Disclosure title={title}>
      <EvidenceValues data={data} />
    </Disclosure>
  );
}
function EvidenceValues({ data }) {
  const entries = Array.isArray(data)
    ? data.map((v, i) => [String(i + 1), v])
    : data && typeof data === "object"
      ? Object.entries(data)
      : [["Evidence", data]];
  return (
    <Paginated
      items={entries}
      render={([key, value]) => (
        <div className="evidence-row">
          {value && typeof value === "object" ? (
            <Evidence title={readable(key)} data={value} />
          ) : (
            <>
              <strong>{readable(key)}</strong>
              {/html|selector/.test(key) ? (
                <pre>{String(value ?? "Not provided")}</pre>
              ) : (
                <p>{String(value ?? "Not provided")}</p>
              )}
            </>
          )}
        </div>
      )}
    />
  );
}
export function Filter({ label, value, onChange, options }) {
  return (
    <label className="filter-label">
      {label}
      <select aria-label={label} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map(([v, t]) => (
          <option key={v} value={v}>
            {t}
          </option>
        ))}
      </select>
    </label>
  );
}
