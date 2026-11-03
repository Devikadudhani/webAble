export function scorePresentation(scoring) {
  const available = Number.isFinite(scoring.overall_score) && scoring.overall_score >= 0 && scoring.overall_score <= 100;
  const coverage = scoring.overall_coverage;
  const label = !available ? "Score unavailable" : coverage >= 90 ? "High coverage" : coverage >= 70 ? "Provisional" : coverage >= 30 ? "Low evidence" : "Very limited evidence";
  return { available, label };
}
