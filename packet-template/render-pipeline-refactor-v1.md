# Render Pipeline Refactor v1

**Status:** Proposed  
**Author:** Free Guy  
**Date:** 2026-05-25  
**Scope:** `closeread.render.*` + `customer-onboarding/host-receiver/run-audit-server.py`

---

## Problem

The current render path is a one-function monolith. `run_audit_server.py` inlines a `-c` Python string that calls `run_audit()` and immediately pipes the result into `render_pdf()`. That coupling means:

- Every customer gets the same template. No per-customer branding, no partner white-labeling, no light/dark variants.
- Changing the PDF layout requires touching the orchestration logic.
- Testing is binary. You cannot run the data normalization step in isolation, or validate HTML output without generating a PDF.
- The transform (markdown to HTML) carries no brand config. Colors, fonts, and logo paths are hardcoded or absent entirely.

The goal is a four-layer pipeline where each layer has a typed input, a typed output, and no awareness of the layers above or below it.

---

## Architecture

```
AuditPacket (Pydantic)
        |
        v
  [ Data Layer ]
  closeread.render.data
        |
        v  NormalizedPacket
  [ Render Layer ]
  closeread.render.markdown
        |
        v  str (Markdown document)
  [ Transform Layer ]
  closeread.render.html
        |
        v  str (HTML document)
  [ Export Layer ]
  closeread.render.export
        |
        v  bytes (PDF) | Path (file) | bytes (HTML file)
```

Each layer is a Python module. Each module exposes one primary function. Layers communicate through plain Python types. No layer imports from a layer above it.

---

## Layer 1: Data Layer

**Module:** `closeread/render/data.py`

**Purpose:** Accept an `AuditPacket` and return a `NormalizedPacket`. This is the only place that touches the Pydantic schema. Everything downstream works with the normalized shape.

**Primary function:**

```python
def normalize(packet: AuditPacket, variant: PacketVariant) -> NormalizedPacket:
    ...
```

**`NormalizedPacket` schema:**

```python
@dataclass
class NormalizedFinding:
    id: str                  # FREE-NNNN
    zone_number: int         # 1-10
    zone_name: str           # "Reliability"
    severity: str            # critical | high | medium | low | info
    summary: str
    details: str
    recommendation: str
    effort: str              # XS | S | M | L | XL
    confidence: float
    citation_file: str | None
    citation_lines: tuple[int, int] | None
    quoted_code: str | None
    is_sensitive: bool
    redacted: bool           # True when is_sensitive + variant.redact_sensitive


@dataclass
class NormalizedZone:
    number: int
    name: str
    buyer_question: str
    narrative: str
    health_score: int
    findings: list[NormalizedFinding]
    out_of_scope: list[str]


@dataclass
class NormalizedPacket:
    packet_id: str
    customer_name: str
    repo_url: str
    completed_at: str        # ISO-8601, formatted for display
    overall_health_score: int
    total_findings: int
    critical_count: int
    high_count: int
    zones: list[NormalizedZone]
    variant: PacketVariant
    brand: BrandTheme
```

**Responsibilities:**
- Flatten nested Pydantic models into flat dataclasses.
- Apply sensitivity redaction based on `PacketVariant.redact_sensitive`.
- Compute summary counts (`critical_count`, `high_count`, `total_findings`).
- Attach the resolved `BrandTheme` to the packet so downstream layers have no config dependency.

**What it does not do:** render, format, or make any string decisions about layout.

---

## Layer 2: Render Layer

**Module:** `closeread/render/markdown.py`

**Purpose:** Convert a `NormalizedPacket` into a Markdown string. All layout decisions live here. No config is read from disk at this layer; the `NormalizedPacket` already carries the `BrandTheme`.

**Primary function:**

```python
def render_markdown(packet: NormalizedPacket) -> str:
    ...
```

**Implementation pattern:** string templates via Python's `string.Template` or Jinja2. The module contains one template per structural section:

- `_COVER_TEMPLATE` -- cover page: logo alt-text, customer name, packet ID, date, overall score
- `_FINDINGS_OVERVIEW_TEMPLATE` -- the summary table across all zones
- `_ZONE_TEMPLATE` -- one zone: narrative, findings table, per-finding detail blocks, buyer-facing summary, out-of-scope
- `_FINDING_DETAIL_TEMPLATE` -- one finding's detail block with citation

Sensitive findings where `redacted=True` render as: `[REDACTED — available in the confidential annex]`.

**Variant-driven sections:** `PacketVariant.include_buyer_summary` controls whether the "What this means for your buyer" section renders per zone. `PacketVariant.include_technical_annex` controls whether raw quoted code blocks render or collapse.

**What it does not do:** apply CSS, load files from disk, or know anything about HTML or PDF.

---

## Layer 3: Transform Layer

**Module:** `closeread/render/html.py`

**Purpose:** Convert a Markdown string into a styled HTML document. Brand CSS is injected at this layer.

**Primary function:**

```python
def render_html(markdown_content: str, brand: BrandTheme) -> str:
    ...
```

**Dependencies:** `mistune` (or `markdown-it-py`) for Markdown to HTML conversion. No heavyweight dependency; the converter must handle tables, fenced code blocks, and definition lists.

**Brand injection:** the function wraps converted HTML in a full `<!DOCTYPE html>` document and injects:
- `<style>` block built from `BrandTheme` fields (see Config Schema below)
- Logo `<img>` in the header if `brand.logo_path` is set
- Cover page CSS class toggled by `brand.packet_variant_css_class`

The HTML structure is fixed. CSS variables drive all visual customization:

```html
<style>
  :root {
    --color-primary: {{ brand.primary_color }};
    --color-secondary: {{ brand.secondary_color }};
    --color-accent: {{ brand.accent_color }};
    --font-body: {{ brand.font_body }};
    --font-heading: {{ brand.font_heading }};
    --logo-max-height: 48px;
  }
  /* base.css inlined here */
</style>
```

`base.css` (checked into `closeread/render/assets/base.css`) provides structural rules that reference CSS variables. It is never brand-specific and is safe to publish in the OSS repo.

**What it does not do:** generate PDFs, read config from disk, or know anything about the packet schema.

---

## Layer 4: Export Layer

**Module:** `closeread/render/export.py`

**Purpose:** Convert an HTML string into the requested output formats. Currently PDF via Playwright; future formats (DOCX, interactive HTML bundle) are added here without touching other layers.

**Primary function:**

```python
async def export(
    html_content: str,
    output_path: Path,
    formats: list[OutputFormat],
    export_config: ExportConfig,
) -> ExportResult:
    ...
```

**`OutputFormat` enum:** `PDF | HTML | BOTH`

**`ExportConfig`:**

```python
@dataclass
class ExportConfig:
    pdf_page_size: str = "A4"          # "A4" | "Letter"
    pdf_margin_mm: int = 15
    pdf_print_background: bool = True
    playwright_timeout_ms: int = 30000
    chromium_args: list[str] = field(default_factory=list)
```

**Implementation:**

```python
async with async_playwright() as p:
    browser = await p.chromium.launch(args=export_config.chromium_args)
    page = await browser.new_page()
    await page.set_content(html_content, wait_until="networkidle")
    if OutputFormat.PDF in formats:
        await page.pdf(
            path=str(pdf_path),
            format=export_config.pdf_page_size,
            margin={"top": ..., "bottom": ..., "left": ..., "right": ...},
            print_background=export_config.pdf_print_background,
        )
    if OutputFormat.HTML in formats:
        html_path.write_text(html_content, encoding="utf-8")
    await browser.close()
```

**`ExportResult`:**

```python
@dataclass
class ExportResult:
    pdf_path: Path | None
    html_path: Path | None
    elapsed_seconds: float
```

**What it does not do:** parse Markdown, apply styles, or read any packet data.

---

## Config Schema

### `BrandTheme`

Loaded once at the callsite (typically `run_audit_server.py` or the CLI). Passed through the pipeline as a field on `NormalizedPacket`.

```python
@dataclass
class BrandTheme:
    # Colors (CSS hex or rgb())
    primary_color: str = "#0F172A"
    secondary_color: str = "#1E40AF"
    accent_color: str = "#3B82F6"
    background_color: str = "#FFFFFF"
    text_color: str = "#111827"
    muted_color: str = "#6B7280"

    # Typography (Google Fonts name or system-safe fallback)
    font_body: str = "Inter, system-ui, sans-serif"
    font_heading: str = "Inter, system-ui, sans-serif"
    font_mono: str = "JetBrains Mono, monospace"

    # Branding
    logo_path: Path | None = None        # absolute path to PNG/SVG
    logo_alt: str = "Closeread"
    company_name: str = "Closeread"
    packet_variant_css_class: str = "standard"

    @classmethod
    def from_toml(cls, path: Path) -> "BrandTheme":
        ...

    @classmethod
    def closeread_default(cls) -> "BrandTheme":
        return cls()

    @classmethod
    def white_label(cls, path: Path) -> "BrandTheme":
        """Load a partner's brand theme from a TOML file."""
        return cls.from_toml(path)
```

**TOML format** (`brand.toml` in the partner's config directory):

```toml
[colors]
primary = "#1A1A2E"
secondary = "#16213E"
accent = "#0F3460"

[typography]
body = "Roboto, sans-serif"
heading = "Roboto Slab, serif"
mono = "Fira Code, monospace"

[branding]
logo_path = "/etc/closeread/partner-logo.png"
logo_alt = "Acme Due Diligence"
company_name = "Acme DD"
```

### `PacketVariant`

Controls which sections render and whether sensitive data is visible.

```python
@dataclass
class PacketVariant:
    name: str                          # "standard" | "executive" | "technical"
    redact_sensitive: bool = True      # hide credential citations in rendered output
    include_buyer_summary: bool = True # "What this means for your buyer" sections
    include_technical_annex: bool = True  # quoted code blocks
    include_out_of_scope: bool = True
    watermark: str | None = None       # "DRAFT" | "CONFIDENTIAL" | None

    @classmethod
    def standard(cls) -> "PacketVariant":
        return cls(name="standard")

    @classmethod
    def executive(cls) -> "PacketVariant":
        return cls(
            name="executive",
            include_technical_annex=False,
            watermark=None,
        )

    @classmethod
    def draft(cls) -> "PacketVariant":
        return cls(name="draft", watermark="DRAFT")
```

---

## Public Entry Point

A single coordinator function in `closeread/render/__init__.py` wires the four layers. This is what `run_audit_server.py` calls.

```python
# closeread/render/__init__.py

import asyncio
from pathlib import Path

from .data import normalize
from .markdown import render_markdown
from .html import render_html
from .export import export, ExportConfig, OutputFormat
from .config import BrandTheme, PacketVariant


def render_packet(
    packet: AuditPacket,
    output_dir: Path,
    brand: BrandTheme | None = None,
    variant: PacketVariant | None = None,
    formats: list[OutputFormat] | None = None,
    export_config: ExportConfig | None = None,
) -> ExportResult:
    brand = brand or BrandTheme.closeread_default()
    variant = variant or PacketVariant.standard()
    formats = formats or [OutputFormat.PDF]
    export_config = export_config or ExportConfig()

    normalized = normalize(packet, variant)
    normalized.brand = brand

    md = render_markdown(normalized)
    html = render_html(md, brand)

    stem = f"closeread-audit-{packet.packet_id}"
    return asyncio.run(
        export(html, output_dir / stem, formats, export_config)
    )
```

Callers never import from sub-modules directly unless they need fine-grained control.

---

## File Boundaries

```
closeread/
  render/
    __init__.py       <- render_packet() coordinator
    config.py         <- BrandTheme, PacketVariant, ExportConfig, OutputFormat
    data.py           <- normalize() + NormalizedPacket dataclasses
    markdown.py       <- render_markdown() + section templates
    html.py           <- render_html() + CSS variable injection
    export.py         <- export() via Playwright
    assets/
      base.css        <- structural CSS, no brand colors
      cover.html.j2   <- optional Jinja2 cover page override
```

The `AuditPacket` Pydantic model stays in `closeread/schema.py`, which is not in the render package. The render package imports from `schema`; `schema` never imports from `render`.

---

## Migration Path from Current Monolith

The current render call in `run_audit_server.py`:

```python
from closeread.render.pdf import render_pdf
render_pdf(packet, str(pdf_path))
```

Becomes:

```python
from closeread.render import render_packet, OutputFormat
from closeread.render.config import BrandTheme, PacketVariant

result = render_packet(
    packet,
    output_dir=VAULT_EXAMPLES,
    brand=BrandTheme.closeread_default(),
    variant=PacketVariant.standard(),
    formats=[OutputFormat.PDF, OutputFormat.HTML],
)
pdf_path = result.pdf_path
```

The old `closeread/render/pdf.py` can be kept as a thin compatibility shim that calls `render_packet()` until all callers are migrated.

---

## Success Criteria

1. Running `render_packet(packet, brand=BrandTheme.white_label(path))` produces a PDF and HTML file styled with the partner's colors and logo. The data layer, render layer, and export layer are unchanged.

2. Each layer can be tested independently:
   - `normalize(packet, PacketVariant.standard())` returns a `NormalizedPacket` with correct counts.
   - `render_markdown(normalized)` returns a valid Markdown string. Spot-check: every finding ID appears exactly once.
   - `render_html(md, brand)` returns a string containing `var(--color-primary)` and the logo `<img>` when `brand.logo_path` is set.
   - `export(html, path, [OutputFormat.PDF], ExportConfig())` writes a non-zero PDF file.

3. The `executive` variant suppresses quoted code blocks and the technical annex. The `draft` variant renders a "DRAFT" watermark. Both are selected by passing a `PacketVariant` to `render_packet()` with no changes to any other layer.

4. A `brand.toml` roundtrip: `BrandTheme.from_toml(path).to_toml(path2)` produces an identical file.

5. The `run_audit_server.py` migration requires touching exactly two lines (the import and the function call) with no behavioral change on the default code path.

---

## Out of Scope for v1

- DOCX output (planned for v2 via `python-docx`)
- Interactive HTML bundle with collapsible findings
- Per-zone brand overrides (e.g., different accent color for critical vs. info findings)
- Server-side font subsetting for offline PDF generation
- Streaming progress events from the export layer to the orchestrator
