# Adversarial Reviewer Calibration Study

**Version:** 1.0  
**Date:** 2026-05-24 (Day 10)  
**Status:** READY TO RUN  
**Prerequisite:** ADR-0018 Phase 1 complete (4-backend interface live)  
**Target wall-clock:** 4-6 hours of compute  

---

## Purpose

The adversarial reviewer is load-bearing. If it rejects too little, the pipeline ships fabricated or inflated findings to buyers. If it rejects too much, legitimate findings get suppressed and the audit undervalues the risk the buyer is actually taking on.

This study calibrates the rejection rate of each backend independently, then surfaces per-backend bias and derives a rotation-weighting recommendation. The hypothesis: a well-calibrated reviewer rejects 12-25% of findings across a balanced historical corpus. Below 5% means the reviewer is credulous; above 40% means it is adversarial to the point of uselessness.

The 12-25% band is derived from domain reasoning:

- A mature codebase in a commercial SaaS product will have a real-defect rate in the 15-30% range per methodology artifact category, based on patterns observed in the Day 1-10 audit corpus.
- The adversarial reviewer should surface approximately the same rate of legitimate rejections (findings the primary specialists got wrong) plus a small buffer for findings that are technically correct but overstated in severity.
- A reviewer rejecting fewer than 5% of inputs is not finding the primary scanner's errors. A reviewer rejecting more than 40% is systematically disagreeing with findings that ship correct in production.

This is not a calibration against "ground truth correctness" (that is the REFLECT poisoned-trace QA harness in `tests/reflect_qa/`). This is a calibration against observed behavior at scale -- does the reviewer's rejection rate match what we expect from a balanced audit workload?

---

## Corpus selection

### N = 20 historical audits

Pull the 20 most-recent audits from the pipeline that meet all of the following:

1. Audit is complete (all 10 methodology artifacts produced and signed in the packet).
2. Audit ran through the adversarial reviewer in production (not a dry run).
3. At least one finding was ACCEPT and at least one was REJECT per audit (excludes edge cases where the reviewer returned all-ACCEPT or all-REJECT, which likely indicate a prompt failure rather than a calibration data point).
4. The source repository is still reachable (public GitHub or archived snapshot) so per-backend reruns can access the same file content.

If fewer than 20 audits are in the history at study time, use all available audits and note the N in the report header. The statistical conclusions are weaker at N < 15; flag this as a limitation if it applies.

### Finding-level unit of measurement

Each audit produces a set of finding records. Each finding is the unit of analysis. For N=20 audits at an average of 15 findings per audit, the corpus is approximately 300 finding records. This is the population the per-backend rejection rate is computed over.

Preserve the production verdict for each finding (ACCEPT or REJECT, plus rationale) as the baseline. The reruns in this study run against the same finding inputs but do not see the production verdict, so the study measures per-backend behavior on the same stimuli, not benchmark-contaminated reproduction.

### Stratify by category

The 300 findings should distribute across the 10 methodology artifacts (01-philosophy through 10-key-person). Before running, compute the distribution. If any artifact has fewer than 10 findings in the corpus, note it in the report as a low-sample category. Rejection-rate claims for low-sample categories are directional only.

Target distribution across a 20-audit corpus is approximately:

| Artifact | Expected finding count |
|---|---|
| 03-sca (dependency vulnerabilities) | 60-80 (highest density) |
| 07-credentials | 30-50 |
| 09-test-coverage | 25-40 |
| 02-reliability | 25-40 |
| 04-stack | 20-30 |
| 05-ip-ownership | 15-25 |
| 08-security | 15-25 |
| 06-third-party | 10-20 |
| 10-key-person | 8-15 |
| 01-philosophy | 5-10 |

---

## Rerunning findings through each backend

### Backend list (per ADR-0018)

| Backend ID | Model family | Mechanism |
|---|---|---|
| `gpt5_codex` | OpenAI GPT-5 | Codex CLI subprocess |
| `gemini_sub` | Google Gemini 2.5 Pro | google-generativeai SDK direct |
| `deepseek_direct` | DeepSeek | HTTPS direct, `DEEPSEEK_API_KEY` |
| `openrouter` | Mixed (fallback path) | OpenRouter HTTP client |

The local Llama 70B backend (ADR-0018 Phase 2) is not included in this study because the M5 Max arrives June 2 / Day 19. Run a supplemental study on the local backend once Phase 2 is complete; use the same protocol below.

### Isolation requirement

Each backend runs in isolation. When rerunning finding F through backend B:

- The prompt is the production reviewer prompt (same template), with the finding fields and surrounding code context as inputs.
- The backend receives NO information about: (a) the production verdict, (b) any other backend's verdict on this finding, (c) any other finding from the same audit. One finding, one backend call, one verdict.
- This isolation is the requirement that makes per-backend bias measurable. If backends share context, their verdicts correlate in ways that are not diagnostic of per-backend bias.

### Input payload per finding

Each rerun call receives the same payload structure the production reviewer receives:

```python
{
    "finding_id": str,          # stable ID from the original audit
    "artifact": str,            # e.g. "03-sca"
    "severity_claimed": str,    # HIGH / MEDIUM / LOW / INFORMATIONAL
    "file_path": str,
    "line_range": [int, int],
    "snippet": str,             # the raw code lines from the repo
    "primary_rationale": str,   # the primary specialist's rationale for this finding
    "context_lines": str,       # 20 lines before and after the snippet, same as production
}
```

The backend returns:

```python
{
    "backend": str,
    "verdict": Literal["ACCEPT", "REJECT"],
    "rejection_reason": str | None,    # None if ACCEPT
    "confidence": Literal["HIGH", "MEDIUM", "LOW"],
    "latency_ms": int,
    "cost_usd": float,
}
```

### Triplicate runs

Each (finding, backend) pair runs three times, matching the REFLECT harness protocol. Record all three verdicts. The study verdict is majority-of-three. A pair where the three verdicts are (ACCEPT, REJECT, ACCEPT) is majority ACCEPT but flagged as a "flicker pair" and analyzed separately in the calibration report.

Flicker pairs reveal prompt instability, not finding quality. High flicker rates on a backend (more than 10% of finding-backend pairs flickering) is itself a calibration signal: that backend's verdicts are unreliable for this finding class.

### Parallelism

All four backends can run in parallel across findings. The constraint is per-backend rate limits:

- GPT-5 via Codex: conservatively 5-10 concurrent subprocess calls. Start at 5; increase if no 429s in the first 50 calls.
- Gemini 2.5 Pro direct: Google's free-tier API allows 60 RPM. At ~4 seconds per call this is the rate-limiter for this backend at scale. Set concurrency to 4.
- DeepSeek direct: generous rate limits on the direct API. Set concurrency to 10.
- OpenRouter: depends on the model routed. Set concurrency to 5 as a safe default.

Estimated wall-clock at N=300 findings, 4 backends, triplicate, with the above concurrency:

- Each finding-backend-triplicate block: ~12-15 seconds (3 calls at ~4 sec each)
- 300 findings x 4 backends = 1,200 finding-backend pairs
- With parallelism across findings per backend, the effective serial depth per backend is 300 / concurrency
  - GPT-5 at 5 concurrent: 60 serial steps x 12 sec = ~12 min
  - Gemini at 4 concurrent: 75 serial steps x 12 sec = ~15 min
  - DeepSeek at 10 concurrent: 30 serial steps x 12 sec = ~6 min
  - OpenRouter at 5 concurrent: 60 serial steps x 12 sec = ~12 min
- All four run in parallel across backends: wall-clock bound by the slowest, ~15 min
- Add setup, corpus loading, report generation: ~20 min total

The 4-6 hour estimate in the header is conservative. 15-20 minutes is the expected runtime. The buffer exists for rate-limit backoffs, retries on transient failures, and the report-generation pass.

---

## Measuring per-backend bias

For each backend B, compute the following over the full corpus of finding-backend pairs:

### Primary metric: rejection rate

```
rejection_rate(B) = count(verdict == REJECT for backend B) / total_findings
```

Compare against the target band: 12-25% healthy, less than 5% too credulous, more than 40% too adversarial.

### Secondary metric: severity-stratified rejection rate

The reviewer should be more likely to reject HIGH and CRITICAL findings (because the stakes of a false positive are higher in a buyer packet) and more lenient on INFORMATIONAL findings. A backend that rejects INFORMATIONAL findings at the same rate as HIGH findings is miscalibrated toward indiscriminate rejection.

```
rejection_rate(B, severity=HIGH) vs rejection_rate(B, severity=LOW)
```

A well-calibrated backend should show: HIGH rejection rate >= LOW rejection rate, with the gap >= 5 percentage points. A backend where LOW rejection rate > HIGH rejection rate is inverting the risk hierarchy and is a hard disqualifier for the primary rotation.

### Tertiary metric: artifact-stratified rejection rate

Some artifacts (03-sca, 07-credentials) have more mechanical, verifiable findings than others (01-philosophy, 10-key-person). The reviewer should have a higher rejection rate on the philosophical artifacts (because LLM reasoning about philosophy is less grounded) and a lower rejection rate on mechanical artifacts (because the evidence is in the file or it is not).

Flag any backend where the rejection rate on mechanical artifacts (03-sca, 07-credentials, 04-stack) is higher than the rejection rate on judgment artifacts (01-philosophy, 10-key-person). That pattern indicates the backend is rejecting based on argument style rather than evidence.

### Flicker rate per backend

```
flicker_rate(B) = count(finding-backend pairs where votes are (ACCEPT, REJECT, ACCEPT) or (REJECT, ACCEPT, REJECT)) / total_pairs
```

Flicker rate above 10% on a backend disqualifies it from the primary rotation and moves it to the OpenRouter-fallback tier. A flicker on any specific finding-backend pair is logged separately; a systematic high-flicker backend is a prompt or model stability problem, not a finding-quality signal.

### Agreement rate across backends

For each finding F, compute the inter-backend agreement:

```
consensus(F) = number of backends with majority-ACCEPT or majority-REJECT that agree with each other / 4
```

A finding where 3 of 4 backends agree is a high-confidence finding regardless of the direction. A finding where the backends split 2:2 is ambiguous. A finding where one backend disagrees while the other three agree is a "lone-rejection" case; log these separately.

Aggregate across all findings:

```
strong_consensus_rate = count(findings where >= 3 of 4 backends agree) / total_findings
```

Target: strong_consensus_rate >= 70%. Below 50% indicates the reviewer is unstable as a layer, not just a single-backend problem.

---

## Detecting consensus vs lone-rejection cases

For each finding F, after computing the majority verdict per backend:

**Classify the finding as one of:**

1. **Unanimous ACCEPT (4-of-4):** All four backends accept the finding. High-confidence pass. No further action.

2. **Unanimous REJECT (4-of-4):** All four backends reject the finding. High-confidence rejection. The finding should be reviewed manually and, if the rejection is correct, added as a fixture to the REFLECT corpus (per corpus-growth doctrine in `reflect-qa-harness-spec.md`).

3. **Strong consensus ACCEPT (3-of-4):** Three backends accept, one rejects. The lone-rejection backend is identified and logged. If the same backend is the lone-rejector in more than 15% of strong-consensus ACCEPT cases, that backend is running systematically adversarial. Flag for downward weighting.

4. **Strong consensus REJECT (3-of-4):** Three backends reject, one accepts. Same lone-actor analysis applies in reverse. A backend that lone-accepts in more than 15% of strong-consensus REJECT cases is running systematically credulous. Flag for downward weighting.

5. **Evenly split (2:2):** Two backends ACCEPT, two REJECT. This is the calibration failure case. Record the artifact category, severity level, and the rationale from each backend for manual review. A high rate of 2:2 splits (more than 10% of findings) is a systemic prompt problem. The two-backends-per-side pattern with no clear consensus is what the rotation-weighting is designed to avoid.

**Lone-rejection registry:** produce a table of all findings that produced a 3:1 verdict with the dissenting backend named. This table is the primary artifact for rotation-weighting decisions. Pattern: if backend X is the lone dissenter in more than 20% of the 3:1 cases, X carries a systematic bias that weighting should correct.

---

## Outputs

### Per-backend calibration table

| Backend | Rejection rate | HIGH rejection | LOW rejection | Flicker rate | Lone-rejection rate | Status |
|---|---|---|---|---|---|---|
| gpt5_codex | XX% | XX% | XX% | XX% | XX% | IN_BAND / HIGH / LOW / FLICKER |
| gemini_sub | XX% | XX% | XX% | XX% | XX% | IN_BAND / HIGH / LOW / FLICKER |
| deepseek_direct | XX% | XX% | XX% | XX% | XX% | IN_BAND / HIGH / LOW / FLICKER |
| openrouter | XX% | XX% | XX% | XX% | XX% | IN_BAND / HIGH / LOW / FLICKER |

Status definitions:
- **IN_BAND:** Rejection rate 12-25%, severity ordering correct, flicker rate under 10%, lone-rejection rate under 20%.
- **HIGH:** Rejection rate above 40%. Adversarial. Weight down.
- **LOW:** Rejection rate below 5%. Credulous. Weight down or remove from primary rotation.
- **FLICKER:** Flicker rate above 10%. Unstable. Remove from primary rotation pending prompt review.
- **INVERTED:** HIGH rejection rate on LOW severity findings, or vice versa. Disqualify from primary rotation.

### Rotation-weighting recommendation

Based on the calibration table, produce a rotation weight for each backend. Weights sum to 1.0. Apply in the `select_backend(strategy="weighted_by_health")` call in the orchestrator.

Weighting formula:

```
weight(B) = score(B) / sum(score(all in-band backends))
```

Where:

```
score(B) = 1.0
  - 0.3 * max(0, (rejection_rate(B) - 0.25) / 0.75)     # penalty for high rejection
  - 0.3 * max(0, (0.12 - rejection_rate(B)) / 0.12)     # penalty for low rejection
  - 0.2 * (flicker_rate(B) / 0.10)                       # penalty for flicker (normalized at 10%)
  - 0.2 * (lone_rejection_rate(B) / 0.20)                # penalty for lone-dissent (normalized at 20%)
```

A backend with rejection_rate = 18%, flicker_rate = 3%, lone_rejection_rate = 8% scores approximately 1.0 - 0 - 0 - 0.06 - 0.08 = 0.86. A backend with rejection_rate = 35%, flicker_rate = 12%, lone_rejection_rate = 22% scores approximately 1.0 - 0.13 - 0 - 0.24 - 0.22 = 0.41. The weighting naturally dilutes unstable backends without fully removing them, preserving rotation diversity.

Backends with status HIGH, LOW, FLICKER, or INVERTED receive weight = 0.0 in the primary rotation and are routed to OpenRouter fallback tier. Do not remove them from the backend interface; a disqualified backend can re-qualify on the next monthly calibration run.

### Artifact: calibration-report-{YYYY-MM-DD}.md

Write the report to:

```
methodology/calibration-results/calibration-report-{run-date}.md
```

Schema:

```markdown
# Reviewer Calibration Report

Run date: {ISO date}
Corpus: N={audits} audits, {findings} findings
Backends: gpt5_codex | gemini_sub | deepseek_direct | openrouter

## Summary

[Per-backend calibration table]

## Rotation weights (effective {date})

gpt5_codex: {weight}
gemini_sub: {weight}
deepseek_direct: {weight}
openrouter: {weight}

## Consensus analysis

Strong consensus rate: {pct}%
Unanimous ACCEPT: {count} findings ({pct}%)
Unanimous REJECT: {count} findings ({pct}%)
Strong consensus ACCEPT (3:1): {count} findings ({pct}%)
Strong consensus REJECT (3:1): {count} findings ({pct}%)
Evenly split (2:2): {count} findings ({pct}%)

## Lone-rejection registry

[Table of 3:1 splits with lone-dissenter backend and finding ID]

## Flags

[Any backend-level flags raised: HIGH / LOW / FLICKER / INVERTED]

## Next calibration

Scheduled: {date 30 days from run date}
Trigger conditions for ad-hoc rerun: (a) any ADR-0018 backend change, (b) prompt template change that touches the reviewer system prompt, (c) finding rate from production shifts more than 5 percentage points from the rate at last calibration.
```

---

## Running the study

The study runner lives at `tests/calibration/run_calibration.py`. Invoke:

```bash
uv run python tests/calibration/run_calibration.py \
  --corpus-size 20 \
  --triplicate \
  --output methodology/calibration-results/calibration-report-$(date +%Y-%m-%d).md
```

Flags:

- `--corpus-size N`: pull the N most recent qualifying audits. Default 20.
- `--triplicate`: run each finding-backend pair three times (default). `--no-triplicate` runs once for a fast smoke check.
- `--backends gpt5_codex,gemini_sub,deepseek_direct,openrouter`: comma-separated list to limit the run to specific backends (useful for re-qualifying one disqualified backend without rerunning all).
- `--dry-run`: load corpus, validate payloads, print per-finding stats, do not make any API calls. Validates the corpus extraction logic before spending compute.

Expected log output:

```
[CALIBRATION] Corpus: 20 audits, 312 findings
[CALIBRATION] Backend: gpt5_codex -- 312 findings x 3 runs = 936 calls
[CALIBRATION] Backend: gemini_sub -- rate limit: 4 concurrent
[CALIBRATION] Backend: deepseek_direct -- concurrency: 10
[CALIBRATION] Backend: openrouter -- concurrency: 5
[CALIBRATION] Progress: 100/312 findings complete across all backends
...
[CALIBRATION] Done. Report written to methodology/calibration-results/calibration-report-2026-05-28.md
```

---

## Ongoing calibration schedule

Run this study monthly and any time one of the following is true:

1. A new backend is added (Phase 2 local Llama backend on June 2 / Day 19 triggers a supplemental run).
2. The reviewer system prompt is modified.
3. A model version change on any backend (GPT-5 minor version, Gemini 2.5 Pro update, DeepSeek model revision).
4. Production rejection rate deviates more than 5 percentage points from the rate recorded at the last calibration.

Store all calibration reports in `methodology/calibration-results/` as a historical record. The trend across reports (rejection rates moving over time per backend) is a model-drift signal before it becomes visible in production audit quality.

---

## Related artifacts

- `methodology/reflect-qa-harness-spec.md`: the complementary QA layer that verifies the reviewer catches planted lies. This study measures rejection rate; the REFLECT harness verifies the reviewer correctly identifies *why* a finding is wrong.
- `decisions/0018-multi-backend-adversarial-reviewer-and-local-inference.md`: the backend architecture this study exercises.
- `decisions/0016-cost-aware-audit-pricing-publish-dollar-per-audit.md`: the cost-transparency claim this study's per-backend cost data feeds.
- `decisions/0017-pre-empt-acquirecom-embed-and-defensive-positioning-against-vibeeval.md`: the strategic context (Move 4) for why reviewer quality is publicly defensible.
