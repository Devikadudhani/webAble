import test from "node:test";
import assert from "node:assert/strict";
import { scorePresentation } from "../frontend/src/scoringPresentation.mjs";

for (const [coverage, score, label] of [[47.06, 31.25, "Low evidence"], [20, 35.71, "Very limited evidence"], [5, 0, "Very limited evidence"], [70, 100, "Provisional"], [100, 100, "High coverage"]]) {
  test(`${coverage}% coverage preserves score ${score} and its evidence label`, () => {
    const result = scorePresentation({overall_score: score, overall_coverage: coverage});
    assert.equal(result.available, true);
    assert.equal(result.label, label);
  });
}
for (const score of [null, undefined, NaN, Infinity, -1, 101]) {
  test(`unavailable or invalid score ${score} does not produce a provisional score`, () => {
    assert.deepEqual(scorePresentation({overall_score: score, overall_coverage: 0}), {
      available: false, label: "Score unavailable",
    });
  });
}
