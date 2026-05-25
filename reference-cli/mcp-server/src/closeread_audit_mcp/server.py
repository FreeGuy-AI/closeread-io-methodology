#!/usr/bin/env python3
"""closeread-audit-mcp v0.1 — MCP server exposing the Closeread audit methodology.

Standard JSON-RPC over stdio per the Model Context Protocol spec. Compatible
with Claude Code, Cursor, Continue, and any other MCP-compatible client.

Per ADR-0015 + ADR-0013: this server exposes the DETERMINISTIC audit path
only. No LLM calls. The heterogeneous adversarial reviewer, the brand-styled
PDF rendering, and the signed packet are retained by the hosted service at
closeread.io.

Tools exposed:
  - audit_repo(repo_path) -> packet
  - audit_artifact(repo_path, artifact_kind) -> artifact_report
  - list_artifact_kinds() -> list[str]
  (recompute_health was in the original scaffold; deferred to v0.2
   once the hosted service exposes the score-recompute primitive too)

Run:
  python server.py
  # or once published:
  uvx closeread-audit-mcp
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# These imports assume closeread is installed as a sibling package OR via
# `pip install closeread`. The pre-launch scaffold version lives next to the
# closeread source tree; the published version will pip-install closeread
# as a runtime dep.
try:
    from closeread.ingest import ingest as ingest_repo
    from closeread.scanners import (
        architecture,
        credential_inventory,
        key_person,
        license_posture,
        reliability,
        sca,
        security,
        stack_hireability,
        test_coverage,
        third_party,
    )
    from closeread.schema import ArtifactKind, ArtifactReport, AuditPacket
except ImportError:
    print(
        "ERROR: closeread package not installed. Install via 'pip install closeread' "
        "or run from the parent closeread repository.",
        file=sys.stderr,
    )
    sys.exit(1)


SCANNER_REGISTRY = {
    ArtifactKind.SCA: (sca.scan, 1000),
    ArtifactKind.CREDENTIALS: (credential_inventory.scan, 2000),
    ArtifactKind.RELIABILITY: (reliability.scan, 1100),
    ArtifactKind.STACK: (stack_hireability.scan, 4000),
    ArtifactKind.IP_OWNERSHIP: (license_posture.scan, 3000),
    ArtifactKind.ARCHITECTURE: (architecture.scan, 8000),
    ArtifactKind.THIRD_PARTY: (third_party.scan, 7000),
    ArtifactKind.SECURITY: (security.scan, 9000),
    ArtifactKind.TEST_COVERAGE: (test_coverage.scan, 5000),
    ArtifactKind.KEY_PERSON: (key_person.scan, 6000),
}


# ─── MCP protocol handlers ─────────────────────────────────────────────────────

def handle_initialize(_params: dict) -> dict:
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": "closeread-audit-mcp",
            "version": "0.1.0",
        },
        "capabilities": {
            "tools": {},
        },
    }


def handle_tools_list(_params: dict) -> dict:
    return {
        "tools": [
            {
                "name": "audit_repo",
                "description": (
                    "Run the full Closeread audit pipeline against a local "
                    "repository path. Returns a packet JSON with all 10 "
                    "artifact reports + per-finding citations."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo_path": {
                            "type": "string",
                            "description": "Absolute path to a local git repository",
                        },
                        "customer_name": {
                            "type": "string",
                            "description": "Optional display name for the packet",
                        },
                    },
                    "required": ["repo_path"],
                },
            },
            {
                "name": "audit_artifact",
                "description": (
                    "Run a single artifact scanner against a local repository "
                    "path. Returns one ArtifactReport. Useful when you want "
                    "only the license / security / etc. slice."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string"},
                        "artifact_kind": {
                            "type": "string",
                            "enum": [k.value for k in ArtifactKind],
                        },
                    },
                    "required": ["repo_path", "artifact_kind"],
                },
            },
            {
                "name": "list_artifact_kinds",
                "description": (
                    "List the 10 artifact kinds the Closeread methodology "
                    "covers + which buyer DD question each answers."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]
    }


def handle_tools_call(params: dict) -> dict:
    name = params.get("name", "")
    args = params.get("arguments", {})

    if name == "audit_repo":
        return _tool_audit_repo(args)
    if name == "audit_artifact":
        return _tool_audit_artifact(args)
    if name == "list_artifact_kinds":
        return _tool_list_artifact_kinds()
    return _error_content(f"Unknown tool: {name}")


def _tool_audit_repo(args: dict) -> dict:
    repo_path = args.get("repo_path")
    customer_name = args.get("customer_name")
    if not repo_path:
        return _error_content("repo_path is required")
    p = Path(repo_path).expanduser().resolve()
    if not p.is_dir():
        return _error_content(f"Not a directory: {repo_path}")

    ingest_result = ingest_repo(p, name=customer_name)
    reports = []
    for kind, (scan_fn, finding_start) in SCANNER_REGISTRY.items():
        try:
            reports.append(scan_fn(ingest_result, finding_start=finding_start))
        except Exception as e:
            reports.append(
                ArtifactReport(
                    artifact=kind,
                    summary_narrative=f"[ERROR] Scanner failed: {type(e).__name__}: {e}",
                    findings=[],
                    health_score=100,
                )
            )

    overall = min((r.health_score for r in reports), default=100) if reports else 100

    from datetime import datetime, timezone
    import uuid

    packet = AuditPacket(
        packet_id=str(uuid.uuid4())[:8],
        customer_name=customer_name,
        repo=ingest_result.metadata,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        artifacts=reports,
        overall_health_score=overall,
    )
    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Audit complete: {packet.total_findings()} findings across "
                    f"{len(reports)} artifacts. Overall health: {overall}/100.\n\n"
                    f"Packet ID: {packet.packet_id}\n\n"
                    f"```json\n{packet.model_dump_json(indent=2)}\n```"
                ),
            }
        ]
    }


def _tool_audit_artifact(args: dict) -> dict:
    repo_path = args.get("repo_path")
    artifact_kind_str = args.get("artifact_kind")
    if not (repo_path and artifact_kind_str):
        return _error_content("repo_path and artifact_kind are required")

    try:
        kind = ArtifactKind(artifact_kind_str)
    except ValueError:
        return _error_content(f"Unknown artifact_kind: {artifact_kind_str}")

    p = Path(repo_path).expanduser().resolve()
    if not p.is_dir():
        return _error_content(f"Not a directory: {repo_path}")

    scan_fn, finding_start = SCANNER_REGISTRY[kind]
    ingest_result = ingest_repo(p)
    report = scan_fn(ingest_result, finding_start=finding_start)
    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Artifact: {report.artifact.value}\n"
                    f"Findings: {len(report.findings)}\n"
                    f"Health: {report.health_score}/100\n\n"
                    f"```json\n{report.model_dump_json(indent=2)}\n```"
                ),
            }
        ]
    }


def _tool_list_artifact_kinds() -> dict:
    kinds_doc = {
        "reliability": "Q1 — How often does this break, and what does breakage look like?",
        "sca": "Q2 — What dependencies does this carry, and what known vulnerabilities live in them?",
        "stack": "Q3 — What languages and frameworks does this use, and how hard is it to hire for them?",
        "ip_ownership": "Q4 — Who owns this code, under what license, and is there contamination?",
        "architecture": "Q5 — How is the system organized, and where are the single points of failure?",
        "third_party": "Q6 — What external services does this depend on, and what is the vendor risk?",
        "credentials": "Q7 — What secrets exist in the codebase, and what is the rotation posture?",
        "security": "Q8 — What does standard static analysis surface, and what is the pre-pentest signal?",
        "test_coverage": "Q9 — What tests exist, and how much of the code do they actually exercise?",
        "key_person": "Q10 — Who has authored this code, and what is the bus factor?",
    }
    text = "Closeread artifact kinds (each answers one buyer DD question):\n\n"
    for k, doc in kinds_doc.items():
        text += f"- **{k}**: {doc}\n"
    return {"content": [{"type": "text", "text": text}]}


def _error_content(msg: str) -> dict:
    return {
        "isError": True,
        "content": [{"type": "text", "text": f"Error: {msg}"}],
    }


# ─── JSON-RPC over stdio loop ──────────────────────────────────────────────────

HANDLERS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
}


def main() -> None:
    """Read JSON-RPC requests from stdin, write responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = req.get("method", "")
        params = req.get("params", {})
        req_id = req.get("id")

        if method == "notifications/initialized":
            # No response needed for notifications
            continue

        handler = HANDLERS.get(method)
        if handler:
            try:
                result = handler(params)
                response = {"jsonrpc": "2.0", "id": req_id, "result": result}
            except Exception as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32603,
                        "message": f"{type(e).__name__}: {e}",
                    },
                }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
