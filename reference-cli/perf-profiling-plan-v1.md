# Audit Pipeline: Performance Instrumentation Plan v1

Status: DRAFT. Day 10 (2026-05-24). Target: merge in one PR.

This document is an implementation contract. A developer with this file and access to the codebase should be able to add all instrumentation in a single pull request without follow-up questions.

---

## Pipeline phases to instrument

The audit pipeline has four measurable phases:

1. **Crawl** -- repository ingestion via `closeread.ingest`. Walks the file tree, extracts metadata, builds the `IngestResult` object the scanners consume.
2. **Specialist-N** -- the 10 scanner calls (`sca.scan`, `credential_inventory.scan`, etc.) in `SCANNER_REGISTRY`. Each scanner is a specialist; they run sequentially today but the shape anticipates parallel fanout.
3. **Adversarial review** -- the LLM reviewer that challenges each finding produced by the specialists. Runs after all specialists complete. Cross-vendor model; separate latency profile from the scanner phase.
4. **Packet render** -- serialization of the `AuditPacket` to JSON, markdown, and PDF. Includes signing if the packet is destined for a customer.

---

## Instrumentation approach

Use OpenTelemetry (OTEL) SDK for Python. Spans go to stdout (OTLP-JSON format) in the reference CLI. The hosted pipeline can wire its own exporter (Honeycomb, Grafana Tempo, or similar) by overriding the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable without touching instrumented code.

Dependencies to add to `pyproject.toml`:

```
opentelemetry-sdk>=1.25.0
opentelemetry-exporter-otlp-proto-json>=1.25.0
```

One tracer instance per process, initialized in `closeread/__init__.py`:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.json.trace_exporter import OTLPSpanExporter

_provider = TracerProvider()
_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(_provider)

tracer = trace.get_tracer("closeread.pipeline", "0.1.0")
```

All spans in this plan use `tracer`. Import it wherever the span is opened.

---

## Spans: one per phase

### Phase 1: Crawl

File: `closeread/ingest.py`, function `ingest(path, name=None)`

Wrap the entire function body in one span:

```python
with tracer.start_as_current_span("pipeline.crawl") as span:
    # existing body
    span.set_attribute("repo.path", str(path))
    span.set_attribute("repo.name", name or path.name)
    span.set_attribute("crawl.file_count", result.file_count)
    span.set_attribute("crawl.total_bytes", result.total_bytes)
    span.set_attribute("crawl.language_count", len(result.languages))
```

Attributes on `span.set_attribute` are searchable in any OTEL-compatible backend. `crawl.file_count` and `crawl.total_bytes` are the primary size signals used to explain crawl latency variance across repositories.

### Phase 2: Specialist-N

File: `closeread_audit_mcp/server.py` (and the equivalent orchestrator in the hosted pipeline), in the loop over `SCANNER_REGISTRY`.

Wrap each scanner call with a child span. The span name encodes the artifact kind so the backend can group by specialist:

```python
for kind, (scan_fn, finding_start) in SCANNER_REGISTRY.items():
    span_name = f"pipeline.specialist.{kind.value}"
    with tracer.start_as_current_span(span_name) as span:
        span.set_attribute("specialist.kind", kind.value)
        span.set_attribute("specialist.finding_start", finding_start)
        try:
            report = scan_fn(ingest_result, finding_start=finding_start)
            span.set_attribute("specialist.finding_count", len(report.findings))
            span.set_attribute("specialist.health_score", report.health_score)
            span.set_attribute("specialist.token_input", report.meta.token_input)
            span.set_attribute("specialist.token_output", report.meta.token_output)
            reports.append(report)
        except Exception as e:
            span.set_status(trace.StatusCode.ERROR, str(e))
            span.record_exception(e)
            # existing error handling
```

`report.meta.token_input` and `report.meta.token_output` require `ArtifactReport.meta` to carry usage data. If the scanner does not currently surface token usage, add a `ScannerMeta` field to `ArtifactReport`:

```python
class ScannerMeta(BaseModel):
    token_input: int = 0
    token_output: int = 0
    model_id: str = ""
```

Scanners that call an LLM (architecture, security) populate this from the API response. Deterministic scanners (sca, credentials) leave it at 0. This lets the backend separate LLM cost from static-analysis cost per specialist without hardcoding which scanners are LLM-backed.

### Phase 3: Adversarial review

File: wherever `reviewer.review(report)` is called (hosted pipeline; not in the reference CLI per ADR-0015).

One parent span for the review phase, one child span per finding reviewed:

```python
with tracer.start_as_current_span("pipeline.adversarial_review") as parent:
    parent.set_attribute("review.finding_count", total_findings)
    parent.set_attribute("review.model_id", reviewer_model_id)

    for finding in all_findings:
        with tracer.start_as_current_span("pipeline.adversarial_review.finding") as child:
            child.set_attribute("review.finding_id", finding.id)
            child.set_attribute("review.artifact", finding.artifact.value)
            child.set_attribute("review.claimed_severity", finding.severity)
            verdict = reviewer.review(finding)
            child.set_attribute("review.verdict", verdict.action)  # PASS | REJECT
            child.set_attribute("review.token_input", verdict.meta.token_input)
            child.set_attribute("review.token_output", verdict.meta.token_output)
            child.set_attribute("review.rejection_reason", verdict.reason or "")
```

The `review.verdict` attribute is the key counter feed for the rejection rate metric described below.

### Phase 4: Packet render

File: wherever the `AuditPacket` is serialized and signed.

```python
with tracer.start_as_current_span("pipeline.render") as span:
    span.set_attribute("render.format", output_format)  # "json" | "markdown" | "pdf"
    span.set_attribute("render.signed", packet.signed)
    span.set_attribute("render.finding_count", packet.total_findings())
    span.set_attribute("render.overall_health", packet.overall_health_score)
```

---

## Counters to track (OTEL Metrics)

Add these to `closeread/metrics.py` (new file). Initialize one `MeterProvider` alongside the tracer in `closeread/__init__.py`.

```python
from opentelemetry import metrics

meter = metrics.get_meter("closeread.pipeline", "0.1.0")

specialist_token_counter = meter.create_counter(
    name="closeread.specialist.tokens_total",
    unit="tokens",
    description="Total tokens consumed by specialist scanners, by specialist kind.",
)

reviewer_rejection_counter = meter.create_counter(
    name="closeread.reviewer.rejections_total",
    unit="findings",
    description="Total findings rejected by the adversarial reviewer.",
)

reviewer_pass_counter = meter.create_counter(
    name="closeread.reviewer.passes_total",
    unit="findings",
    description="Total findings accepted by the adversarial reviewer.",
)

fanout_depth_gauge = meter.create_up_down_counter(
    name="closeread.pipeline.fanout_depth",
    unit="specialists",
    description="Number of specialist scanners running concurrently in the current audit.",
)

audit_counter = meter.create_counter(
    name="closeread.pipeline.audits_total",
    unit="audits",
    description="Total completed audits.",
)
```

Call sites:

- After each specialist span closes: `specialist_token_counter.add(tokens, {"specialist": kind.value})`
- After each reviewer verdict: increment `reviewer_rejection_counter` or `reviewer_pass_counter` with `{"artifact": finding.artifact.value}`
- At the start of the specialist loop if running parallel: `fanout_depth_gauge.add(N)`, subtract N when done
- After packet is written: `audit_counter.add(1, {"status": "complete"})`

---

## Percentiles to track

All latency distributions use OTEL histogram with these explicit boundaries (in milliseconds):

```
[50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000]
```

Create one histogram per phase in `closeread/metrics.py`:

```python
crawl_latency = meter.create_histogram(
    name="closeread.phase.crawl.duration_ms",
    unit="ms",
    description="Wall-clock duration of the repository crawl phase.",
)

specialist_latency = meter.create_histogram(
    name="closeread.phase.specialist.duration_ms",
    unit="ms",
    description="Wall-clock duration per specialist scanner call.",
)

review_latency = meter.create_histogram(
    name="closeread.phase.review.duration_ms",
    unit="ms",
    description="Wall-clock duration of the adversarial review phase per finding.",
)

render_latency = meter.create_histogram(
    name="closeread.phase.render.duration_ms",
    unit="ms",
    description="Wall-clock duration of the packet render phase.",
)
```

Record at the close of each span:

```python
elapsed_ms = (end_time - start_time).total_seconds() * 1000
specialist_latency.record(elapsed_ms, {"specialist": kind.value})
```

The OTEL SDK computes p50, p95, p99 from histogram data. The backend (Grafana, Honeycomb, or CLI summary) queries these at whatever aggregation window is appropriate. For the reference CLI a local Prometheus scrape endpoint is sufficient at launch.

---

## 6-metric dashboard: text sketch

The dashboard has two rows. Row 1 is latency; row 2 is correctness and cost.

```
+------------------------------------------------------------------+
|  AUDIT PIPELINE HEALTH                         Last 24h          |
+------------------------------------------------------------------+
|                                                                  |
|  [1] CRAWL LATENCY (p50/p95/p99)    [2] SPECIALIST LATENCY      |
|                                          (p50/p95/p99, by kind)  |
|  p50:  1.2s                                                      |
|  p95:  4.8s                          sca        p95:  0.8s       |
|  p99: 11.3s                          security   p95: 18.2s       |
|                                      credentials p95: 0.3s       |
|  Bars: histogram buckets 50ms-60s    architecture p95: 21.4s     |
|        one bar per boundary          (others collapsed)          |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  [3] REVIEW LATENCY (p50/p95/p99)   [4] REVIEWER REJECTION RATE |
|      per-finding wall clock                                      |
|                                      Rate = rejections /         |
|  p50:  4.1s                               (rejections + passes)  |
|  p95: 12.8s                                                      |
|  p99: 28.4s                         Overall: 23.4%              |
|                                     By artifact:                 |
|  Bars: histogram buckets 1s-120s      credentials  38.1%         |
|                                       sca          19.7%         |
|                                       license      11.2%         |
|                                       (others...)                |
|                                                                  |
+------------------------------------------------------------------+
|  [5] SPECIALIST TOKENS (total/audit, [6] PARALLEL FANOUT DEPTH  |
|      by specialist kind, 24h total)      (active specialists     |
|                                           at sample time)        |
|  security      ~12,400 tok/audit                                 |
|  architecture  ~10,800 tok/audit     Current: 1 (sequential)    |
|  sca              ~800 tok/audit     Max observed: 1             |
|  credentials      ~200 tok/audit                                 |
|  (others...)                         Target (v2): 10             |
|                                       (all parallel)             |
|  Token cost est: $0.08/audit                                     |
|  (at current OpenRouter pricing)                                 |
+------------------------------------------------------------------+
```

Metric 1 surfaces crawl bottlenecks on large repos. Metric 2 pinpoints which specialist is the scheduling bottleneck without aggregating across all 10. Metric 3 tracks reviewer cost; a p99 above 30s indicates model timeout risk. Metric 4 is the correctness signal: a rejection rate that drops suddenly means the reviewer is becoming a rubber-stamp, not that the code got cleaner. Metric 5 drives pricing: it is the raw input to the $/audit cost-transparency metric Free Guy publishes publicly. Metric 6 tracks progress toward parallel fanout (currently sequential; the counter will show 1 until the scheduler is changed).

---

## What "done" looks like for the PR author

The PR is mergeable when all of the following are true:

1. `pip install -e ".[dev]"` installs `opentelemetry-sdk` and `opentelemetry-exporter-otlp-proto-json` without error.
2. Running `closeread audit /path/to/repo` with `OTEL_SDK_DISABLED=false` (the default) emits JSON spans to stdout with span names matching the four phase names in this spec exactly: `pipeline.crawl`, `pipeline.specialist.<kind>`, `pipeline.adversarial_review`, `pipeline.render`.
3. Running with `OTEL_SDK_DISABLED=true` produces no span output and no performance overhead (the OTEL no-op tracer handles this automatically; no conditional logic needed in the instrumented code).
4. `pytest tests/ -m "not reflect"` still passes (instrumentation adds no breaking changes).
5. A manual smoke run shows `specialist.token_input` is non-zero for at least one LLM-backed scanner (confirm `security` or `architecture` populates it).
6. The `closeread.phase.specialist.duration_ms` histogram records a data point for each of the 10 specialists in a full audit run.

No dashboard wiring is required in this PR. The dashboard sketch above is a reference for whoever wires the OTEL backend. The PR is scope-complete when spans exist and can be confirmed in a local OTLP collector (e.g. `otel-collector` Docker image or `otelcol-contrib` binary with a debug exporter).

---

## What this plan does NOT cover

- **Async concurrency spans.** The current pipeline is sequential. When parallel fanout lands, add `asyncio` context propagation (`context.attach`/`context.detach`) to each specialist task. That is a separate PR.
- **REFLECT QA harness instrumentation.** The poisoned-trace harness (`tests/reflect_qa/`) has its own latency and cost profile. Instrument it separately; its numbers should not contaminate production audit metrics.
- **Billing-grade token attribution.** This plan tracks tokens per specialist for cost visibility. Billing-grade attribution (per-customer, per-audit, exportable to Stripe usage records) is an ops concern above this layer.
- **Prompt-injection detection.** Security spans on the review input are out of scope here. ADR-0009 covers that surface.

---

*Created by Free Guy, Day 10 (2026-05-24). Part of the Day 30 OSS launch instrumentation work.*
