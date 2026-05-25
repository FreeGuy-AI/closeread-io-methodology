# closeread-audit-mcp

A Model Context Protocol server that exposes the Closeread audit methodology
as runnable tools inside Claude Code, Cursor, Continue, and any other
MCP-compatible client.

## Why

The Closeread methodology shipped as markdown is useful for reading. The
methodology shipped as runnable MCP tools is useful for DOING. A founder in
Cursor can ask "audit my repo via closeread" and get a packet back without
leaving their editor.

Per [ADR-0015](https://github.com/closeread-io/methodology/blob/main/lessons/),
the form factor is the distribution wedge.

## What it exposes

| Tool | Inputs | Output |
|---|---|---|
| `audit_repo` | `repo_path: str` (absolute path on local disk) | `AuditPacket` JSON with all artifact reports |
| `audit_artifact` | `repo_path: str`, `artifact_kind: str` | Single `ArtifactReport` for the named artifact |
| `list_artifact_kinds` | (none) | List of available artifact kinds with descriptions |

(A `recompute_health` tool was in the original scaffold and is deferred to v0.2 once the hosted service exposes the same score-recompute primitive for parity.)

## Install

Once published to PyPI (~Day 30):

```bash
uvx closeread-audit-mcp
# or for a persistent install:
pip install closeread-audit-mcp
closeread-audit-mcp
```

The server reads JSON-RPC requests from stdin and writes responses to stdout per the MCP spec. Wire it into any MCP-compatible client by pointing the client at the `closeread-audit-mcp` binary.

## Configure (Claude Desktop example)

```json
{
  "mcpServers": {
    "closeread-audit": {
      "command": "uvx",
      "args": ["closeread-audit-mcp"]
    }
  }
}
```

Same shape for Cursor, Continue, and the rest of the MCP client ecosystem.

This MCP server runs deterministic-only audits. No LLM calls are made from
the open MCP. The hosted service at closeread.io retains the heterogeneous
adversarial reviewer + the packet rendering + the 48-hour SLA + the
signed packet (with `https://closeread.io/.soul` attribution).

## Install

```bash
uvx closeread-audit-mcp
# or
pip install closeread-audit-mcp
closeread-audit-mcp
```

## Configure

For Claude Code (in `~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "closeread-audit": {
      "command": "uvx",
      "args": ["closeread-audit-mcp"]
    }
  }
}
```

For Cursor (in Settings > MCP):

```json
{
  "closeread-audit": {
    "command": "uvx",
    "args": ["closeread-audit-mcp"]
  }
}
```

After restart, the tools appear in your editor and you can ask Claude / Cursor
to audit a repo path.

## What you get from the open MCP vs. the hosted service

| | Open MCP (this server) | Hosted service (closeread.io) |
|---|---|---|
| Deterministic scanners (SCA, credentials, license, stack, architecture, key_person, third_party, security, test_coverage, reliability) | ✓ | ✓ |
| Adversarial reviewer (non-Claude rebuttal per finding) | ✗ | ✓ |
| Brand-styled PDF rendering | ✗ | ✓ |
| 48-hour SLA + email delivery | ✗ | ✓ |
| `closeread.io.soul`-signed packet (carries brand reputational weight in M&A conversations) | ✗ | ✓ |
| Cost | $0 | $500 Founding Alpha (5 seats), $2K-$10K standard |

If you are the founder preparing to sell and you have a weekend to run the
audit yourself, the open MCP is the right tool. If you want it done in 48
hours with the adversarial pass and a signed PDF a buyer can verify, the
hosted service is the right tool.

## License

MIT (same as the parent methodology repository). Brand marks reserved.

## Status

v0.1.0 ships Day 30 (2026-06-15) per ADR-0015. This README is the
pre-launch scaffold. Real implementation lands in `server.py`.
