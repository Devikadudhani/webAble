(() => {
  "use strict";

  const form = document.querySelector("#audit-form");
  if (!form) return;

  const state = {
    featureCatalog: [],
    questions: [],
    answers: new Map(),
    browserFeatures: new Map(),
    lastResponse: null,
    submitting: false,
  };

  const elements = {
    featureList: document.querySelector("#feature-list"),
    featureComplete: document.querySelector("#features-complete"),
    questionsPanel: document.querySelector("#questions-panel"),
    questionsList: document.querySelector("#questions-list"),
    results: document.querySelector("#results"),
    conflicts: document.querySelector("#conflicts"),
    ownerEvidence: document.querySelector("#owner-evidence"),
    browserEvidence: document.querySelector("#browser-evidence"),
    error: document.querySelector("#form-error"),
    submitButton: document.querySelector("#submit-button"),
  };

  const create = (tagName, className, text) => {
    const node = document.createElement(tagName);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const lines = (value) => value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);

  function renderFeatures() {
    const legend = elements.featureList.querySelector("legend");
    elements.featureList.replaceChildren(legend);
    for (const feature of state.featureCatalog) {
      const wrapper = create("div", "feature-choice");
      wrapper.append(create("span", "feature-name", feature.label));
      const group = create("div", "feature-options");
      group.setAttribute("role", "group");
      group.setAttribute("aria-label", `${feature.label}: owner-reported presence`);
      for (const [value, label] of [
        ["yes", "Yes"],
        ["no", "No"],
        ["not_sure", "Not sure"],
      ]) {
        const id = `feature-${feature.feature_id}-${value}`;
        const option = create("label", "feature-option");
        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = `feature-${feature.feature_id}`;
        radio.value = value;
        radio.id = id;
        radio.checked = value === "not_sure";
        radio.addEventListener("change", renderQuestions);
        option.append(radio, document.createTextNode(label));
        group.append(option);
      }
      wrapper.append(group);
      elements.featureList.append(wrapper);
    }
  }

  function selectedFeatures() {
    const features = {};
    for (const feature of state.featureCatalog) {
      const selected = form.querySelector(
        `input[name="feature-${CSS.escape(feature.feature_id)}"]:checked`,
      );
      if (!selected || selected.value === "not_sure") {
        features[feature.feature_id] = null;
      } else {
        features[feature.feature_id] = selected.value === "yes";
      }
    }
    return features;
  }

  function activeQuestions() {
    const features = selectedFeatures();
    return state.questions.filter((question) => {
      if (!question.feature_id) return false;
      return features[question.feature_id] === true ||
        state.browserFeatures.get(question.feature_id) === true;
    });
  }

  function renderQuestions() {
    const questions = activeQuestions();
    elements.questionsList.replaceChildren();
    elements.questionsPanel.hidden = questions.length === 0;
    for (const question of questions) {
      const card = create("article", "question-card");
      const heading = create("h3", "", question.prompt);
      card.append(heading);

      const current = state.answers.get(question.question_id) || {
        answer: "",
        explanation: "",
        pageUrls: "",
      };
      const options = create("div", "answer-options");
      options.setAttribute("role", "radiogroup");
      options.setAttribute("aria-label", question.prompt);
      const labels = {
        yes: "Yes",
        no: "No",
        not_sure: "Not sure",
        not_applicable: "Not applicable",
      };
      for (const value of question.answer_options) {
        const option = create("label");
        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = `answer-${question.question_id}`;
        radio.value = value;
        radio.checked = current.answer === value;
        radio.addEventListener("change", () => {
          state.answers.set(question.question_id, {
            ...state.answers.get(question.question_id),
            answer: value,
          });
        });
        option.append(radio, document.createTextNode(labels[value] || value));
        options.append(option);
      }
      card.append(options);

      const explanationLabel = create(
        "label",
        "question-label",
        "Optional explanation or relevant public page URLs",
      );
      const explanation = document.createElement("textarea");
      explanation.rows = 2;
      explanation.maxLength = 2000;
      explanation.value = current.explanation || "";
      explanation.placeholder = "Context only; do not include sensitive information";
      explanation.addEventListener("input", () => {
        state.answers.set(question.question_id, {
          ...state.answers.get(question.question_id),
          explanation: explanation.value,
        });
      });
      explanationLabel.append(explanation);
      card.append(explanationLabel);

      const pageLabel = create("label", "question-label", "Related public URLs (optional, one per line)");
      const pageUrls = document.createElement("textarea");
      pageUrls.rows = 2;
      pageUrls.maxLength = 2000;
      pageUrls.value = current.pageUrls || "";
      pageUrls.placeholder = "https://example.com/public-page";
      pageUrls.addEventListener("input", () => {
        state.answers.set(question.question_id, {
          ...state.answers.get(question.question_id),
          pageUrls: pageUrls.value,
        });
      });
      pageLabel.append(pageUrls);
      card.append(pageLabel);
      elements.questionsList.append(card);
    }
  }

  function buildRequest() {
    const features = selectedFeatures();
    const answers = [...state.answers.entries()]
      .filter(([, answer]) => answer.answer)
      .map(([question_id, answer]) => ({
        question_id,
        answer: answer.answer,
        explanation: answer.explanation?.trim() || null,
        page_urls: lines(answer.pageUrls || ""),
      }));
    const journeys = lines(document.querySelector("#journeys").value).map((line) => {
      const [name = "", urls = ""] = line.split("|", 2);
      return {
        name: name.trim().slice(0, 120),
        description: null,
        page_urls: urls.split(",").map((url) => url.trim()).filter(Boolean),
      };
    });
    return {
      url: document.querySelector("#audit-url").value.trim(),
      accessibility_context: {
        representative_page_urls: lines(
          document.querySelector("#representative-urls").value,
        ),
        user_journeys: journeys,
        feature_presence: features,
        feature_inventory_completed: elements.featureComplete.checked,
        answers,
        free_text: document.querySelector("#free-text").value.trim() || null,
      },
    };
  }

  function renderOwnerEvidence(evaluation) {
    elements.ownerEvidence.replaceChildren();
    const answers = evaluation.owner_answers || [];
    const declared = Object.entries(evaluation.declared_features || {})
      .filter(([, present]) => present !== null)
      .map(([feature_id, present]) => ({
        question_id: feature_id,
        answer: present ? "yes" : "no",
        explanation: "Owner-declared feature information; not verified.",
      }));
    if (answers.length === 0 && declared.length === 0) {
      elements.ownerEvidence.append(create("p", "muted", "No structured answers submitted yet."));
      return;
    }
    for (const answer of [...declared, ...answers]) {
      const item = create("article", "evidence-item");
      item.append(create("span", "evidence-kind", "Owner-reported · unverified"));
      item.append(create("p", "", `${answer.question_id}: ${answer.answer.replaceAll("_", " ")}`));
      if (answer.explanation) item.append(create("p", "", answer.explanation));
      elements.ownerEvidence.append(item);
    }
  }

  function renderBrowserEvidence(evaluation) {
    elements.browserEvidence.replaceChildren();
    const detected = new Map();
    for (const viewport of state.lastResponse.viewports || []) {
      for (const feature of viewport.browser_feature_discovery?.features || []) {
        if (!feature.detected) continue;
        const key = `${feature.feature_id}:${feature.viewport}`;
        detected.set(key, feature);
      }
    }
    for (const feature of detected.values()) {
      const catalog = state.featureCatalog.find(
        (item) => item.feature_id === feature.feature_id,
      );
      const item = create("article", "evidence-item");
      item.append(create("span", "evidence-kind browser", "Browser-observed"));
      item.append(create(
        "p",
        "",
        `${catalog?.label || feature.feature_id}: ${feature.count} candidate(s) on ${feature.viewport}.`,
      ));
      for (const evidence of feature.evidence || []) {
        item.append(create("p", "", evidence));
      }
      elements.browserEvidence.append(item);
    }
    const analyzerEvidence = new Map();
    for (const criterion of evaluation.criteria || []) {
      for (const evidence of criterion.browser_observed || []) {
        if (!evidence.analyzer_id) continue;
        const key = `${criterion.criterion_id}:${evidence.analyzer_id}:${evidence.summary}`;
        if (!analyzerEvidence.has(key)) {
          analyzerEvidence.set(key, {
            criterionId: criterion.criterion_id,
            analyzerId: evidence.analyzer_id,
            summary: evidence.summary,
            viewports: new Set(),
          });
        }
        analyzerEvidence.get(key).viewports.add(evidence.viewport);
      }
    }
    for (const evidence of analyzerEvidence.values()) {
      const item = create("article", "evidence-item");
      item.append(create("span", "evidence-kind browser", "Browser-observed · not a criterion conclusion"));
      item.append(create(
        "p",
        "",
        `${evidence.criterionId} · ${evidence.analyzerId} · ${[...evidence.viewports].join(", ")}`,
      ));
      item.append(create("p", "", evidence.summary));
      elements.browserEvidence.append(item);
    }
    if (detected.size === 0 && analyzerEvidence.size === 0) {
      elements.browserEvidence.append(create(
        "p",
        "muted",
        "No feature or criterion-level browser evidence was returned.",
      ));
    }
    if (evaluation.browser_discovery_status !== "available") {
      elements.browserEvidence.append(create(
        "p",
        "muted",
        `Feature discovery status: ${evaluation.browser_discovery_status}.`,
      ));
    }
  }

  function renderConflicts(evaluation) {
    const conflicts = evaluation.conflicts || [];
    elements.conflicts.replaceChildren();
    elements.conflicts.hidden = conflicts.length === 0;
    if (conflicts.length === 0) return;
    elements.conflicts.append(create("h3", "", "Owner and browser information differ"));
    for (const conflict of conflicts) {
      const label = state.featureCatalog.find(
        (feature) => feature.feature_id === conflict.feature_id,
      )?.label || conflict.feature_id;
      elements.conflicts.append(create(
        "p",
        "",
        `${label}: ${conflict.summary || "Your reported scope differs from a browser-detected candidate. Please clarify the feature and relevant public page; this is not a WCAG failure finding."}`,
      ));
    }
  }

  function renderCriterionSummary(evaluation) {
    const target = document.querySelector("#criterion-summary");
    target.replaceChildren();
    const criteria = evaluation.criteria || [];
    if (!criteria.length) {
      target.append(create("p", "muted", "No criterion-level evaluation results were returned."));
      return;
    }
    const statusLabels = {
      owner_reported: "Owner context only",
      browser_observed: "Browser evidence only",
      manual_review_needed: "Owner and browser evidence",
      not_evaluated: "Not evaluated",
    };
    const counts = new Map();
    for (const criterion of criteria) {
      counts.set(criterion.status, (counts.get(criterion.status) || 0) + 1);
    }
    const list = create("ul", "criterion-summary-list");
    for (const [status, label] of Object.entries(statusLabels)) {
      const item = create("li", "");
      item.append(create("strong", "", String(counts.get(status) || 0)));
      item.append(document.createTextNode(` ${label}`));
      list.append(item);
    }
    target.append(list);
    target.append(create("p", "muted", "No criterion is marked passed from owner responses or missing evidence."));
    const notEvaluated = criteria.filter((criterion) => criterion.status === "not_evaluated");
    if (notEvaluated.length) {
      target.append(create("p", "muted", `Not evaluated (not passed): ${notEvaluated.map((criterion) => criterion.criterion_id).join(", ")}`));
    }
  }

  function applyResponse(response) {
    state.lastResponse = response;
    const evaluation = response.hybrid_evaluation || {};
    state.questions = evaluation.questions_to_ask || [];
    state.browserFeatures.clear();
    for (const viewport of response.viewports || []) {
      for (const feature of viewport.browser_feature_discovery?.features || []) {
        if (feature.detected) state.browserFeatures.set(feature.feature_id, true);
      }
    }
    renderQuestions();
    renderOwnerEvidence(evaluation);
    renderBrowserEvidence(evaluation);
    renderConflicts(evaluation);
    renderCriterionSummary(evaluation);
    elements.results.hidden = false;
    document.querySelector("#results-title").focus?.({preventScroll: true});
    elements.results.scrollIntoView({behavior: "smooth", block: "start"});
  }

  async function submit(event) {
    event.preventDefault();
    if (state.submitting) return;
    elements.error.hidden = true;
    elements.error.textContent = "";
    let payload;
    try {
      payload = buildRequest();
    } catch (error) {
      elements.error.textContent = error.message || "Review the questionnaire fields.";
      elements.error.hidden = false;
      return;
    }
    state.submitting = true;
    elements.submitButton.disabled = true;
    elements.submitButton.textContent = "Running audit…";
    try {
      const response = await fetch("/captures", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) {
        const detail = typeof result.detail === "string"
          ? result.detail
          : result.detail?.detail || "The audit request could not be completed.";
        throw new Error(detail);
      }
      applyResponse(result);
      elements.submitButton.textContent = "Save answers & update audit";
    } catch (error) {
      elements.error.textContent = error.message || "The audit request failed.";
      elements.error.hidden = false;
    } finally {
      state.submitting = false;
      elements.submitButton.disabled = false;
      if (!state.lastResponse) elements.submitButton.textContent = "Start accessibility audit";
      else elements.submitButton.textContent = "Save answers & update audit";
    }
  }

  async function initialize() {
    try {
      const response = await fetch("/accessibility/questionnaire");
      if (!response.ok) throw new Error("Could not load the questionnaire.");
      const questionnaire = await response.json();
      state.featureCatalog = questionnaire.features || [];
      state.questions = questionnaire.conditional_questions || [];
      renderFeatures();
      renderQuestions();
    } catch (error) {
      elements.error.textContent = error.message;
      elements.error.hidden = false;
      elements.submitButton.disabled = true;
    }
  }

  form.addEventListener("submit", submit);
  void initialize();
})();
