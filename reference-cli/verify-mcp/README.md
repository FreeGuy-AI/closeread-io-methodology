# closeread-verify-mcp

A Model Context Protocol server for VERIFYING Closeread audit packets you've
received. This is the buyer-side companion to `closeread-audit-mcp`.

## Why

If a seller hands you a Closeread audit packet during diligence, you want to
verify what they sent you without taking it on faith. This MCP exposes that
verification as runnable tools inside Claude Code, Cursor, Continue, and any
other MCP-compatible client.

## What it exposes

| Tool | Inputs | Output |
|---|---|---|
| `verify_soul` | `url: str` (a `.soul` URL like `https://closeread.io/.soul`) | Verification result: signature valid, public key, fingerprint, signing date |
| `verify_packet_citations` | `packet_path: str`, `repo_path: str` | For each finding in the packet, re-checks that the cited code still exists at the cited location. Reports drift. |
| `extract_packet_findings` | `pdf_path: str` OR `md_path: str` | Parses a Closeread packet back into structured Finding objects. Useful for filtering, grouping, or comparing against a buyer's own scan. |
| `compare_packets` | `packet_a: str`, `packet_b: str` | Diff two packets (e.g. one from the seller, one you generated yourself). Surfaces what each finding the seller surfaced that you didn't, and vice versa. |

This MCP server runs locally; no data leaves your machine. The `verify_soul`
tool makes one HTTP fetch to the URL you supply.

## Install

```bash
uvx closeread-verify-mcp
# or
pip install closeread-verify-mcp
closeread-verify-mcp
```

## Configure (Claude Code example)

```json
{
  "mcpServers": {
    "closeread-verify": {
      "command": "uvx",
      "args": ["closeread-verify-mcp"]
    }
  }
}
```

## Use case (buyer side)

1. Seller hands you a Closeread audit packet PDF + access to the repo
2. In Claude Code, ask: "verify this Closeread packet's citations against the repo at /tmp/seller-repo"
3. Claude calls `extract_packet_findings` then `verify_packet_citations`
4. You get a report: 95 of 97 citations match exactly, 2 citations point at code that's drifted since the audit ran. You ask the seller to either re-run the audit or explain the drift.
5. Optionally: run `closeread-audit-mcp` against the same repo yourself and call `compare_packets` to see what the seller's packet missed (or what you missed that they caught).

## Use case (Closeread methodology verification)

1. You see a `.soul` URL on closeread.io or in a packet's signature block
2. In Claude Code, ask: "verify the Closeread .soul"
3. Claude calls `verify_soul("https://closeread.io/.soul")`
4. You get: signature valid, public key z6Mkqb..., fingerprint 6b4ff4a0...
5. This is the same verification a buyer's M&A counsel would do to confirm the packet came from the entity it claims to come from.

## License

MIT (same as the parent methodology repository). Brand marks reserved.

## Status

v0.1.0 ships ~Day 45-60 (subsequent monthly release after the Day 30 audit-mcp
ship). This README is the pre-launch scaffold. Real implementation lands in
`server.py`.
