## High Impact

  1. **Upgrade EmailQuality to LLM-as-judge**
  The current heuristic grader (4 string checks) is fragile. An LLM judge could
  evaluate tone, completeness, hallucination, and appropriateness more holistically.
  The code comments already note this was planned for Phase 2 but never implemented.
  This is the grader with the most room for sophistication — the current 1.00 score
  might be masking issues a human reviewer would catch (e.g., awkward phrasing, mixed
  language, unnecessary information).

  2. **Add realistic scanned-PDF fixtures**
  All current PDFs are digitally generated with clean text. The OCR layer gets a free
  pass. Adding scanned documents (low DPI, rotation, stamps, noise, handwritten
  annotations) would test the OCR-to-LLM pipeline under realistic conditions. You could
   generate these by applying image degradation (blur, noise, skew) to the rendered
  pages before saving as PDF.

  3. **Fuzzy matching in ExtractionAccuracy**
  The current comparator is normalize(a) == normalize(b) where normalize is just
  lowercase + strip. This is brittle for address comparisons — "c/ industria 45, pol.
  ind. sur, granada" vs "calle industria 45, polígono industrial sur, granada" would
  fail despite being semantically identical. Options:
  - Token-level Jaccard or Levenshtein ratio
  - LLM-as-judge per field
  - Separate thresholds for structured fields (order_id — exact match) vs free-text
  fields (addresses — fuzzy)

  4. **Exploit unused scenario metadata**
  Three fields exist in every scenario but no grader uses them: expected_sheet_update,
  expected_confirmation_email, expected_missing_info_email. A ToolCallCorrectness
  grader could verify these against mock_tools.emails_sent and
  mock_tools.sheet_rows_added. This would close a gap — currently, no grader checks
  whether the correct tools were invoked, only whether the correct data was produced.

##  Medium Impact

  5. **Parallelize eval execution**
  task_threads=1 is a bottleneck. Each scenario requires a real OpenAI API call +
  Tesseract OCR, so 25 sequential scenarios is slow. Fix: give each task its own
  MockToolManager instance instead of sharing one. The build_eval_task closure would
  create a fresh mock per invocation rather than calling reset() on a shared one.

  6. **Add confidence score grading**
  The extract prompt asks the LLM for per-field confidence scores, but no grader
  evaluates them. A ConfidenceCalibration grader could check that high-confidence
  fields are correct and low-confidence fields correlate with actual errors — measuring
   whether the model's self-assessment is calibrated.

  7. **Add regression tracking**
  Currently each eval run is an isolated Opik experiment. There's no automated
  comparison against a baseline. A regression check (e.g., "fail if extraction_accuracy
   drops more than 0.05 from last run") would catch prompt regressions or model
  downgrades early. Could be as simple as storing the last run's scores in a JSON file
  and asserting in CI.

  8. **Expand scenario count for statistical significance**
  5 scenarios per category is useful for development iteration but too few for
  confident metric reporting. At n=5, a single scenario flip changes the score by 0.20.
   Expanding to 15-20 per category (or using scenario generators with parameter
  variation) would give more stable estimates. The malformed_pdf and ambiguous
  categories especially deserve expansion.

##  Lower Impact

  9. **Test error-handling paths**
  No scenario currently tests the error final status. If the LLM returns unparseable
  output, OCR fails completely, or a service throws an exception, the pipeline has
  error guards in every node — but the evals never exercise them. Adding scenarios that
   intentionally trigger failures (corrupted PDF, empty PDF, extremely large PDF) would
   validate the error-handling paths.

  10. **Deterministic date handling in ground truth**
  The ambiguous_no_year_01 scenario expects "2025-03-15T14:00:00" for the date "15 de
  marzo, 14:00". The LLM must infer the year. If this eval runs after 2025, the LLM
  might infer 2026. The ground truth is brittle to temporal drift.

  11. **ExtractionAccuracy datetime normalization**
  Ground truth uses ISO format (2025-01-18T08:00:00) while fixture PDFs use varied
  formats (2025-01-18, 08:00). The grader's _normalize() only does lowercase + strip —
  it doesn't parse datetimes. If the LLM returns "2025-01-18 08:00" instead of
  "2025-01-18T08:00:00", it would count as a mismatch despite being semantically
  identical. A datetime-aware comparison for the delivery_datetime field would be more
  robust.

  12. **Add a latency/cost metric**
  Track per-scenario wall-clock time and token usage. This wouldn't affect pass/fail
  but would catch regressions where a prompt change causes 3x more tokens. Opik tracing
   already captures spans — a LatencyBudget grader could flag scenarios exceeding a
  threshold.