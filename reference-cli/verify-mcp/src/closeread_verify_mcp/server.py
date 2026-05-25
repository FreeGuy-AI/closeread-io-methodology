#!/usr/bin/env python3
"""closeread-verify-mcp v0.1 — MCP server for verifying Closeread audit packets.

Standard JSON-RPC over stdio per the Model Context Protocol spec.

Tools exposed:
  - verify_soul(url) -> signature verification result
  - verify_packet_citations(packet_path, repo_path) -> drift report (v0.2)
  - extract_packet_findings(packet_path) -> Finding records
  - compare_packets(packet_a, packet_b) -> diff report

Run:
  python server.py
  # or once published:
  uvx closeread-verify-mcp
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ED25519_MULTICODEC = bytes([0xED, 0x01])
SIG_FENCE_RE = re.compile(r"```signature\n(.*?)\n```", re.DOTALL)
PUBKEY_RE = re.compile(r"\*\*Public key \(Ed25519, multibase\):\*\*\s*`([^`]+)`")
FINGERPRINT_RE = re.compile(r"\*\*Key fingerprint \(SHA-256\):\*\*\s*`([0-9a-f]+)`")


def _b64url_decode(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)


def _verify_soul_text(soul_text: str) -> dict:
    try:
        import base58
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as e:
        return {"valid": False, "error": f"Missing dependency: {e}. Install: pip install base58 cryptography"}

    pubkey_m = PUBKEY_RE.search(soul_text)
    if not pubkey_m:
        return {"valid": False, "error": "No public-key field found in .soul"}
    multibase = pubkey_m.group(1)
    if not multibase.startswith("z"):
        return {"valid": False, "error": f"Public key not z-prefix multibase: {multibase[:10]}"}
    pub_with_prefix = base58.b58decode(multibase[1:])
    if not pub_with_prefix.startswith(ED25519_MULTICODEC):
        return {"valid": False, "error": "Public key not ed25519-pub multicodec"}
    pub_raw = pub_with_prefix[len(ED25519_MULTICODEC):]
    if len(pub_raw) != 32:
        return {"valid": False, "error": f"Public key wrong length: {len(pub_raw)} bytes"}

    fp_m = FINGERPRINT_RE.search(soul_text)
    embedded_fp = fp_m.group(1) if fp_m else None
    actual_fp = hashlib.sha256(pub_raw).hexdigest()
    if embedded_fp and embedded_fp != actual_fp:
        return {"valid": False, "error": "Fingerprint mismatch",
                "embedded_fingerprint": embedded_fp, "computed_fingerprint": actual_fp}

    sig_m = SIG_FENCE_RE.search(soul_text)
    if not sig_m:
        return {"valid": False, "error": "No signature fenced block found"}
    sig_line_m = re.search(r"signature:\s*(\S+)", sig_m.group(1))
    if not sig_line_m:
        return {"valid": False, "error": "No 'signature:' line inside fence"}
    signature_bytes = _b64url_decode(sig_line_m.group(1))

    canonical = SIG_FENCE_RE.sub("", soul_text)
    pub = Ed25519PublicKey.from_public_bytes(pub_raw)
    try:
        pub.verify(signature_bytes, canonical.encode("utf-8"))
    except InvalidSignature:
        return {"valid": False, "error": "Signature verification failed",
                "public_key": multibase, "fingerprint": actual_fp}
    return {"valid": True, "public_key": multibase, "fingerprint": actual_fp}


def tool_verify_soul(url: str) -> dict:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "closeread-verify-mcp/0.1.0 (+https://closeread.io/.soul verifier)",
                "Accept": "text/plain,text/markdown,*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            soul_text = resp.read().decode("utf-8")
    except Exception as e:
        return {"isError": True, "content": [{"type": "text", "text": f"Fetch failed: {e}"}]}

    result = _verify_soul_text(soul_text)
    if result["valid"]:
        text = (
            f"✓ Signature VALID for {url}\n\n"
            f"Public key: {result['public_key']}\n"
            f"Fingerprint: {result['fingerprint']}\n\n"
            f"This .soul file was signed by the holder of the Ed25519 private key "
            f"whose public counterpart is shown above."
        )
    else:
        text = f"✗ Signature INVALID for {url}\n\nError: {result.get('error')}"
        for k, v in result.items():
            if k not in ("valid", "error"):
                text += f"\n{k}: {v}"
    return {"content": [{"type": "text", "text": text}]}


def tool_extract_packet_findings(packet_path: str) -> dict:
    p = Path(packet_path).expanduser()
    if not p.is_file():
        return {"isError": True, "content": [{"type": "text", "text": f"File not found: {packet_path}"}]}
    suffix = p.suffix.lower()
    if suffix == ".md":
        text = p.read_text(encoding="utf-8")
    elif suffix == ".pdf":
        return {"isError": True, "content": [{"type": "text",
            "text": "PDF extraction not yet implemented in v0.1. Use the .md version OR convert via `pdftotext`."}]}
    else:
        return {"isError": True, "content": [{"type": "text", "text": f"Unsupported format: {suffix}"}]}

    finding_pattern = re.compile(r"###\s+(FREE-\d{4})[:\s]+(.+?)(?=\n)", re.MULTILINE)
    matches = finding_pattern.findall(text)
    findings = [{"finding_id": fid, "summary": summary.strip()} for fid, summary in matches]
    return {"content": [{"type": "text", "text":
        f"Extracted {len(findings)} findings from {packet_path}:\n\n"
        + "\n".join(f"- {f['finding_id']}: {f['summary'][:120]}" for f in findings)}]}


def tool_verify_packet_citations(packet_path: str, repo_path: str) -> dict:
    return {"content": [{"type": "text",
        "text": "verify_packet_citations is v0.2 scope; will re-read each cited file:line and confirm code drift status."}]}


def tool_compare_packets(packet_a: str, packet_b: str) -> dict:
    a_result = tool_extract_packet_findings(packet_a)
    b_result = tool_extract_packet_findings(packet_b)
    if a_result.get("isError") or b_result.get("isError"):
        return {"isError": True, "content": [{"type": "text", "text": "compare_packets requires both packets to extract cleanly."}]}
    a_ids = set(re.findall(r"FREE-\d{4}", a_result["content"][0]["text"]))
    b_ids = set(re.findall(r"FREE-\d{4}", b_result["content"][0]["text"]))
    only_a = sorted(a_ids - b_ids)
    only_b = sorted(b_ids - a_ids)
    common = a_ids & b_ids
    text = (
        f"Comparison:\n"
        f"  Packet A: {packet_a} ({len(a_ids)} findings)\n"
        f"  Packet B: {packet_b} ({len(b_ids)} findings)\n"
        f"  Common: {len(common)}\n"
        f"  Only in A: {len(only_a)} {only_a[:5]}{'...' if len(only_a) > 5 else ''}\n"
        f"  Only in B: {len(only_b)} {only_b[:5]}{'...' if len(only_b) > 5 else ''}"
    )
    return {"content": [{"type": "text", "text": text}]}


def handle_initialize(_params: dict) -> dict:
    return {"protocolVersion": "2024-11-05",
            "serverInfo": {"name": "closeread-verify-mcp", "version": "0.1.0"},
            "capabilities": {"tools": {}}}


def handle_tools_list(_params: dict) -> dict:
    return {"tools": [
        {"name": "verify_soul",
         "description": "Fetch a .soul URL and verify its Ed25519 signature.",
         "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
        {"name": "extract_packet_findings",
         "description": "Parse a Closeread audit packet (.md) into structured Finding records.",
         "inputSchema": {"type": "object", "properties": {"packet_path": {"type": "string"}}, "required": ["packet_path"]}},
        {"name": "verify_packet_citations",
         "description": "Re-verify packet citations against the source repo (v0.2).",
         "inputSchema": {"type": "object", "properties": {"packet_path": {"type": "string"}, "repo_path": {"type": "string"}}, "required": ["packet_path", "repo_path"]}},
        {"name": "compare_packets",
         "description": "Diff two Closeread audit packets by finding ID.",
         "inputSchema": {"type": "object", "properties": {"packet_a": {"type": "string"}, "packet_b": {"type": "string"}}, "required": ["packet_a", "packet_b"]}},
    ]}


def handle_tools_call(params: dict) -> dict:
    name = params.get("name", "")
    args = params.get("arguments", {})
    if name == "verify_soul":
        return tool_verify_soul(args.get("url", ""))
    if name == "extract_packet_findings":
        return tool_extract_packet_findings(args.get("packet_path", ""))
    if name == "verify_packet_citations":
        return tool_verify_packet_citations(args.get("packet_path", ""), args.get("repo_path", ""))
    if name == "compare_packets":
        return tool_compare_packets(args.get("packet_a", ""), args.get("packet_b", ""))
    return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {name}"}]}


HANDLERS = {"initialize": handle_initialize, "tools/list": handle_tools_list, "tools/call": handle_tools_call}


def main() -> None:
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
            continue
        handler = HANDLERS.get(method)
        if handler:
            try:
                result = handler(params)
                response = {"jsonrpc": "2.0", "id": req_id, "result": result}
            except Exception as e:
                response = {"jsonrpc": "2.0", "id": req_id,
                            "error": {"code": -32603, "message": f"{type(e).__name__}: {e}"}}
        else:
            response = {"jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"}}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
