"""Strix-style AI security scanner — recon, findings, and live-site probing."""

from __future__ import annotations

import ipaddress
import re
import socket
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

import requests

from ..core.helpers import extract_json_object
from ..core.provider import Provider, call_ai

MAX_TARGET_CHARS = 140_000

_SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

_SCAN_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# (path, severity-if-exposed, description)
SECURITY_PROBE_PATHS: list[tuple[str, str, str]] = [
    ("/.env", "Critical", "Exposed .env file"),
    ("/.git/HEAD", "High", "Git repository exposed"),
    ("/.git/config", "High", "Git config exposed"),
    ("/wp-config.php", "High", "wp-config.php exposed"),
    ("/wp-config.php.bak", "High", "wp-config backup exposed"),
    ("/phpinfo.php", "High", "phpinfo() page exposed"),
    ("/backup.zip", "High", "Backup archive exposed"),
    ("/backup.sql", "High", "Database backup exposed"),
    ("/server-status", "High", "Apache server-status exposed"),
    ("/admin", "Medium", "Admin panel reachable"),
    ("/wp-admin", "Medium", "WordPress admin reachable"),
    ("/api-docs", "Medium", "API documentation exposed"),
    ("/swagger-ui", "Medium", "Swagger UI exposed"),
    ("/robots.txt", "Info", "robots.txt present"),
    ("/.well-known/security.txt", "Info", "security.txt present"),
]

RECON_PROMPT = (
    "You are ReconAgent, the reconnaissance module of Strix, an expert AI "
    "penetration-testing team that works like real ethical hackers.\n\n"
    "Map the attack surface of the code/target below. Actually read the code "
    "and report only real observations.\n\n"
    "Return ONLY a JSON object inside a fenced ```json block with this exact "
    "structure:\n"
    "{\n"
    '  "technologies": ["languages, frameworks, libraries detected"],\n'
    '  "entry_points": ["user-controlled inputs: endpoints, functions, forms"],\n'
    '  "attack_surface": "one short paragraph describing the attack surface",\n'
    '  "potential_vectors": ["likely attack vectors"]\n'
    "}\n"
    "Keep each field concise. Do not invent facts or add any text outside the "
    "JSON block.\n\n"
    "TARGET:\n{target}"
)

SCAN_PROMPT = (
    "You are Strix, an autonomous AI penetration tester who works exactly like "
    "a real hacker: recon -> exploit -> validate with a proof-of-concept -> "
    "report the fix.\n\n"
    "{recon_context}Analyze the TARGET below and find ONLY realistic, "
    "exploitable security vulnerabilities the code actually exhibits.\n\n"
    "Hunt for (but keep an open mind):\n"
    "- Injection: SQL/NoSQL, OS command, template (SSTI), broken deserialization\n"
    "- Broken authentication / authorization, hard-coded credentials, committed "
    "secrets and API keys\n"
    "- Path traversal, arbitrary file read/write, SSRF, unsafe file uploads\n"
    "- XSS (reflected/stored/DOM), insecure HTML insertion, client-side injection\n"
    "- Sensitive data exposure, insecure CORS, missing security headers, "
    "insecure cookies\n"
    "- Unsafe eval/exec, pickle.loads on untrusted data, regex DoS, debug "
    "backdoors, suspicious crypto\n\n"
    "Rules:\n"
    "- Report only vulnerabilities with a concrete location inside the target.\n"
    "- Provide a working copy-paste proof-of-concept (curl command, raw HTTP "
    "request, or code snippet).\n"
    "- No vague advice - every finding must be actionable.\n"
    "- Explain summary/description/remediation/attack_scenario in plain, simple "
    "English that a developer with NO security background understands - everyday "
    "words, short sentences, concrete examples.\n"
    "- If the target looks clean, return an empty findings array.\n\n"
    "Return ONLY a JSON object inside a fenced ```json code block with EXACTLY:\n"
    "{\n"
    '  "summary": "2-3 sentence overall security summary in plain language",\n'
    '  "findings": [\n'
    "    {\n"
    '      "id": "F-01",\n'
    '      "title": "short descriptive title",\n'
    '      "severity": "Critical | High | Medium | Low | Info",\n'
    '      "cwe": "CWE-89 (SQL Injection)",\n'
    '      "owasp": "A03:2021 - Injection",\n'
    '      "location": "file-or-component:line-or-endpoint",\n'
    '      "description": "what the flaw is and why it matters, in simple '
    'everyday words",\n'
    '      "proof_of_concept": "copy-paste payload or sample request",\n'
    '      "remediation": "concrete fix, with a code snippet if helpful",\n'
    '      "attack_scenario": "how an attacker would realistically abuse this '
    'in practice (1-2 sentences)"\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "Do NOT write anything outside the JSON block.\n\n"
    "TARGET:\n{target}"
)

def _render(template: str, **values: str) -> str:
    """Fill ``{placeholder}`` tokens without touching literal JSON braces."""
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _as_text(value: Any, fallback: str = "") -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ", ".join(str(x) for x in value)
    return fallback


def _parse_recon(result: str) -> Dict[str, str]:
    """Parse recon agent output into a dict (tolerates non-JSON answers)."""
    data = extract_json_object(result)
    if not isinstance(data, dict):
        return {"attack_surface": (result or "")[:4000]}

    return {
        "technologies": _as_text(data.get("technologies") or data.get("stack")),
        "entry_points": _as_text(data.get("entry_points") or data.get("entrypoints")),
        "attack_surface": _as_text(data.get("attack_surface") or data.get("summary")),
        "potential_vectors": _as_text(data.get("potential_vectors") or data.get("vectors")),
    }


def _parse_findings(result: str) -> Dict[str, Any]:
    """Parse a scan response into ``{"findings", "summary", "raw"}``."""
    data = extract_json_object(result)
    if not isinstance(data, dict):
        return {"findings": [], "summary": "", "raw": result}

    raw_findings = data.get("findings")
    if not isinstance(raw_findings, list):
        raw_findings = []

    findings: List[Dict[str, str]] = []
    for idx, f in enumerate(raw_findings, 1):
        if not isinstance(f, dict):
            continue
        findings.append({
            "id": str(f.get("id") or f"F-{idx:02d}"),
            "title": str(
                f.get("title") or f.get("name") or f.get("vulnerability") or "Untitled finding"
            )[:200],
            "severity": str(f.get("severity") or "Info").capitalize(),
            "cwe": str(f.get("cwe") or ""),
            "owasp": str(f.get("owasp") or ""),
            "location": str(f.get("location") or f.get("file") or f.get("endpoint") or "")[:160],
            "description": str(f.get("description") or ""),
            "proof_of_concept": str(f.get("proof_of_concept") or f.get("poc") or ""),
            "remediation": str(f.get("remediation") or f.get("fix") or ""),
            "attack_scenario": str(f.get("attack_scenario") or f.get("scenario") or ""),
        })

    findings.sort(key=lambda f: _SEV_RANK.get(f["severity"].lower(), 5))

    return {
        "findings": findings,
        "summary": str(data.get("summary") or ""),
        "raw": result,
    }

# ---------------------------------------------------------------------------
# AI-driven stages
# ---------------------------------------------------------------------------

def security_recon(
    target: str,
    *,
    model: str = "gpt_4_5",
    provider: Provider | None = None,
) -> Dict[str, str]:
    """Stage 1 — map the attack surface of *target* (code, config, or notes).

    Parameters
    ----------
    target : str
        Source code, configuration or endpoint documentation to analyse.
    model : str
        g4f model used for the analysis.
    provider : Provider, optional

    Returns
    -------
    dict
        ``{"technologies", "entry_points", "attack_surface", "potential_vectors"}``

    Example
    -------
    >>> from asimtool.developer import security_recon
    >>> recon = security_recon(open("app.py", encoding="utf-8").read())
    >>> print(recon["attack_surface"])
    """
    if not target or not target.strip():
        raise ValueError("Target cannot be empty.")
    if len(target) > MAX_TARGET_CHARS:
        raise ValueError(f"Target is too large (max {MAX_TARGET_CHARS:,} characters).")

    result = call_ai(_render(RECON_PROMPT, target=target), model=model, provider=provider)
    return _parse_recon(result)


def security_scan(
    target: str,
    *,
    mode: str = "quick",
    recon: Dict[str, Any] | str = "",
    model: str = "gpt_4_5",
    provider: Provider | None = None,
) -> Dict[str, Any]:
    """Stage 2 — Strix-style exploitation scan producing ranked findings.

    Parameters
    ----------
    target : str
        The code / configuration to scan.
    mode : str
        ``"quick"`` for a single pass, ``"deep"`` to feed a prior
        :func:`security_recon` result in as attack-surface context.
    recon : dict | str, optional
        Output of :func:`security_recon` (or a raw string of it).
    model : str
        g4f model used for the analysis.
    provider : Provider, optional

    Returns
    -------
    dict
        ``{"summary": str, "findings": [...sorted by severity...], "raw": str}``

    Example
    -------
    >>> from asimtool.developer import security_scan
    >>> report = security_scan(open("app.py", encoding="utf-8").read())
    >>> for f in report["findings"]:
    ...     print(f["severity"], "-", f["title"])
    """
    if not target or not target.strip():
        raise ValueError("Target cannot be empty.")
    if len(target) > MAX_TARGET_CHARS:
        raise ValueError(f"Target is too large (max {MAX_TARGET_CHARS:,} characters).")
    if mode not in ("quick", "deep"):
        mode = "quick"

    recon_context = ""
    if mode == "deep" and recon:
        if isinstance(recon, str):
            recon_text = recon
        else:
            recon_text = "\n".join(f"{k}: {v}" for k, v in recon.items() if v)
        recon_context = (
            "A prior reconnaissance agent produced this attack-surface map "
            f"(use it to guide your exploit):\n{recon_text[:8000]}\n\n"
        )

    result = call_ai(
        _render(SCAN_PROMPT, recon_context=recon_context, target=target),
        model=model,
        provider=provider,
    )
    parsed = _parse_findings(result)
    parsed["raw"] = parsed["raw"][:50_000]
    return parsed

# ---------------------------------------------------------------------------
# Live website helpers
# ---------------------------------------------------------------------------

def _is_safe_url(url: str) -> bool:
    """SSRF guard — reject non-HTTP(S) URLs and private/loopback hosts."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    host = parsed.hostname
    if not host:
        return False

    try:
        for info in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
    except (socket.gaierror, ValueError):
        return False

    return True


def sanitize_url(url: str) -> str:
    """Normalise and validate a scan target URL (adds https:// when missing).

    Returns
    -------
    str
        The cleaned URL.

    Raises
    ------
    ValueError
        When the URL is malformed or points at a private network.
    """
    url = (url or "").strip()
    if not url:
        raise ValueError("URL cannot be empty.")
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    if not _is_safe_url(url):
        raise ValueError("Unsafe URL: only public http(s) URLs can be scanned.")
    return url


def fetch_site(url: str, timeout: tuple[float, float] = (5, 12)) -> Dict[str, Any]:
    """Collect the basic HTTP profile of a live website.

    Returns
    -------
    dict
        ``{"url", "status", "headers", "server", "title", "cookies", "error"}``
    """
    try:
        resp = requests.get(
            url, headers={"User-Agent": _SCAN_UA}, timeout=timeout, allow_redirects=True
        )
    except requests.RequestException as exc:
        return {"url": url, "status": 0, "headers": {}, "server": "",
                "title": "", "cookies": [], "error": str(exc)}

    title = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.I | re.S)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:300]

    return {
        "url": resp.url,
        "status": resp.status_code,
        "headers": dict(resp.headers),
        "server": resp.headers.get("Server", ""),
        "title": title,
        "cookies": [c.name for c in resp.cookies],
        "error": "",
    }

def probe_paths(
    base_url: str,
    *,
    paths: list[str] | None = None,
    timeout: tuple[float, float] = (3, 6),
) -> List[Dict[str, Any]]:
    """Probe well-known sensitive paths on *base_url*.

    Parameters
    ----------
    base_url : str
        Validated public base URL.
    paths : list[str], optional
        Paths to probe; defaults to :data:`SECURITY_PROBE_PATHS`.
    timeout : tuple, optional
        ``(connect, read)`` timeouts in seconds.

    Returns
    -------
    list[dict]
        One entry per probe — ``{"path", "url", "status", "severity",
        "description", "exposed"}`` — sorted by severity.
    """
    base_url = sanitize_url(base_url).rstrip("/") + "/"
    targets = paths if paths is not None else [p for p, _, _ in SECURITY_PROBE_PATHS]
    severity_map = {p: sev for p, sev, _ in SECURITY_PROBE_PATHS}
    desc_map = {p: d for p, _, d in SECURITY_PROBE_PATHS}

    results: List[Dict[str, Any]] = []
    for path in targets:
        full = urljoin(base_url, path.lstrip("/"))
        try:
            resp = requests.get(
                full, headers={"User-Agent": _SCAN_UA}, timeout=timeout, allow_redirects=True
            )
            status = resp.status_code
        except requests.RequestException:
            status = 0

        # 2xx/3xx means the resource is really there; 401/403 also count as
        # "reachable" for admin-style paths.
        exposed = 200 <= status < 400 or status in (401, 403)
        results.append({
            "path": path,
            "url": full,
            "status": status,
            "severity": severity_map.get(path, "Info"),
            "description": desc_map.get(path, ""),
            "exposed": exposed,
        })

    results.sort(key=lambda r: (_SEV_RANK.get(r["severity"].lower(), 5), r["path"]))
    return results

def security_scan_site(
    url: str,
    *,
    probe: bool = True,
    model: str = "gpt_4_5",
    provider: Provider | None = None,
) -> Dict[str, Any]:
    """Full live-website scan — HTTP profile, path probes, then AI analysis.

    Parameters
    ----------
    url : str
        Public website URL.
    probe : bool
        Run the sensitive-path probe list (default ``True``).
    model : str
        g4f model for the AI stage.
    provider : Provider, optional

    Returns
    -------
    dict
        ``{"site", "probes", "findings", "summary", "raw"}``

    Example
    -------
    >>> from asimtool.developer import security_scan_site
    >>> report = security_scan_site("example.com", probe=False)
    >>> print(report["summary"])
    """
    safe_url = sanitize_url(url)

    site = fetch_site(safe_url)
    if site.get("error"):
        raise RuntimeError(f"Could not reach the target: {site['error']}")

    probes = probe_paths(safe_url) if probe else []
    auto_findings = [
        {
            "id": f"PROBE-{i:02d}",
            "title": p["description"] or p["path"],
            "severity": p["severity"],
            "cwe": "",
            "owasp": "",
            "location": p["url"],
            "description": f"HTTP {p['status']} — the path is reachable from the internet.",
            "proof_of_concept": f"curl -I {p['url']}",
            "remediation": "Remove or restrict access to this path (deny rule, auth, or delete the file).",
            "attack_scenario": p["description"],
        }
        for i, p in enumerate((r for r in probes if r["exposed"]), 1)
    ]

    context = (
        f"URL: {site['url']}\nStatus: {site['status']}\nServer: {site['server']}\n"
        f"Title: {site['title']}\nCookies: {', '.join(site['cookies']) or 'none'}\n"
        "Response headers:\n"
        + "\n".join(f"{k}: {v}" for k, v in site["headers"].items())
    )
    if auto_findings:
        context += "\n\nAutomatically detected exposures:\n" + "\n".join(
            f"- [{f['severity']}] {f['title']} ({f['location']})" for f in auto_findings
        )

    result = call_ai(
        _render(
            SCAN_PROMPT,
            recon_context=(
                "Automated recon of the live website below was already performed. "
                "Focus on the exposed items and any additional HTTP-level issues.\n\n"
            ),
            target=context,
        ),
        model=model,
        provider=provider,
    )
    parsed = _parse_findings(result)

    # Merge: automatic probe findings first, de-duplicated by location.
    seen = {f["location"] for f in auto_findings}
    merged = auto_findings + [f for f in parsed["findings"] if f["location"] not in seen]
    merged.sort(key=lambda f: _SEV_RANK.get(f["severity"].lower(), 5))

    return {
        "site": site,
        "probes": probes,
        "findings": merged,
        "summary": parsed["summary"],
        "raw": parsed["raw"][:50_000],
    }
