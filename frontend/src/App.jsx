import React, { useEffect, useMemo, useRef, useState } from "react";
import { Header, AuditForm, AuditLoading } from "./components/AuditForm";
import ResultsDashboard from "./components/ResultsDashboard";
import { buildRequest, list } from "./utils";
import { readApiResponse, runAudit } from "./api.mjs";
const empty = () => ({
  url: "",
  pages: "",
  journeys: "",
  context: "",
  features: {},
  complete: false,
});
export default function App() {
  const [form, setForm] = useState(empty),
    [answers, setAnswers] = useState({}),
    [catalog, setCatalog] = useState([]),
    [questions, setQuestions] = useState([]),
    [ready, setReady] = useState(false),
    [loading, setLoading] = useState(false),
    [response, setResponse] = useState(null),
    [error, setError] = useState("");
  const pending = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/accessibility/questionnaire", { signal: controller.signal })
      .then((r) => readApiResponse(r, "Loading the questionnaire"))
      .then((q) => {
        setCatalog(list(q.features));
        setQuestions(list(q.conditional_questions));
        setForm((f) => ({
          ...f,
          features: Object.fromEntries(
            list(q.features).map((x) => [x.feature_id, null]),
          ),
        }));
        setReady(true);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, []);
  const activeQuestions = useMemo(() => {
    const detected = new Set(
      list(response?.viewports).flatMap((v) =>
        list(v.browser_feature_discovery?.features)
          .filter((f) => f.detected)
          .map((f) => f.feature_id),
      ),
    );
    return questions.filter(
      (q) =>
        q.feature_id &&
        (form.features[q.feature_id] === true || detected.has(q.feature_id)),
    );
  }, [questions, form.features, response]);
  async function submit(event) {
    event?.preventDefault();
    if (pending.current || !ready) return;
    pending.current = true;
    setLoading(true);
    setError("");
    try {
      const result = await runAudit(buildRequest(form, answers));
      setResponse(result);
      setQuestions((old) => [
        ...new Map(
          [
            ...old,
            ...list(result.hybrid_evaluation?.questions_to_ask).map((q) => ({
              ...old.find((x) => x.question_id === q.question_id),
              ...q,
            })),
          ].map((q) => [q.question_id, q]),
        ).values(),
      ]);
    } catch (e) {
      setError(e.message || "The audit request failed.");
    } finally {
      pending.current = false;
      setLoading(false);
    }
  }
  function reset() {
    setForm({
      ...empty(),
      features: Object.fromEntries(catalog.map((f) => [f.feature_id, null])),
    });
    setAnswers({});
    setResponse(null);
    setError("");
    document.getElementById("audit-url")?.focus();
  }
  return (
    <>
      <a className="skip-link" href="#audit-url">
        Skip to audit
      </a>
      <Header onNew={reset} />
      <main className={response ? "has-results" : "landing"}>
        <section className="intro">
          <p className="eyebrow">WEB ACCESSIBILITY · WCAG 2.2</p>
          <h1>Accessibility,<br />measured properly.</h1>
          <p className="hero-line">
            Browser-based accessibility and WCAG evidence
          </p>
          <p>
            Across desktop, tablet and mobile.
          </p>
        </section>
        <AuditForm
          form={form}
          setForm={setForm}
          answers={answers}
          setAnswers={setAnswers}
          catalog={catalog}
          questions={activeQuestions}
          ready={ready}
          loading={loading}
          response={response}
          onSubmit={submit}
        />
        {error && (
          <p id="form-error" className="error-message" role="alert">
            {error}
          </p>
        )}
        {loading && <AuditLoading />}
        {response && !loading && (
          <ResultsDashboard
            response={response}
            catalog={catalog}
            onAgain={() =>
              document.getElementById("audit-form").requestSubmit()
            }
            onNew={reset}
          />
        )}
        <footer>
          WebAble · Evidence for better decisions. Human review for conformance.
        </footer>
      </main>
    </>
  );
}
