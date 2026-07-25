#!/usr/bin/env python3
"""
AL-MUKH Security Scanner v1.0
Scans vaults for secrets, permission issues, exposed files, and hardcoded credentials.
"""

import os
import sys
import re
import json
import stat
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# ─── Paths ────────────────────────────────────────────────────────────────────
MASTER_VAULT = os.environ.get("AL_MUKH_ROOT", "/home/kali/AL-MUKH")
SPOKE_ROOTS = ["/home/kali/Documents/Obsidian Vault"]
GITIGNORE_PATH = os.path.join(MASTER_VAULT, ".gitignore")

# All scan targets
SCAN_ROOTS = [MASTER_VAULT] + [r for r in SPOKE_ROOTS if os.path.isdir(r)]

# ─── Secret Patterns ─────────────────────────────────────────────────────────
PATTERNS = {
    "api_key": {
        "regex": re.compile(r"""(?i)(?:api[_-]?key|apikey)\s*[:=]\s*['"]?([A-Za-z0-9_\-]{20,})['"]?"""),
        "severity": "high",
        "description": "API key",
    },
    "aws_access_key": {
        "regex": re.compile(r"""AKIA[0-9A-Z]{16}"""),
        "severity": "critical",
        "description": "AWS access key",
    },
    "github_token": {
        "regex": re.compile(r"""ghp_[A-Za-z0-9]{36}"""),
        "severity": "critical",
        "description": "GitHub personal access token",
    },
    "github_fine_grained_token": {
        "regex": re.compile(r"""github_pat_[A-Za-z0-9_]{82}"""),
        "severity": "critical",
        "description": "GitHub fine-grained token",
    },
    "bearer_token": {
        "regex": re.compile(r"""Bearer\s+[A-Za-z0-9._\-]{20,}"""),
        "severity": "high",
        "description": "Bearer token",
    },
    "private_key": {
        "regex": re.compile(r"""-----BEGIN.*PRIVATE KEY-----"""),
        "severity": "critical",
        "description": "Private key",
    },
    "password_in_config": {
        "regex": re.compile(
            r"""(?i)(?:password|passwd|secret|token|credential)\s*[:=]\s*['"]?(\S{8,})['"]?"""
        ),
        "severity": "high",
        "description": "Password/secret in config",
    },
    "connection_string": {
        "regex": re.compile(
            r"""(?i)(?:mysql|postgres|postgresql|mongodb|redis|amqp)://[^\s'"<>]{10,}"""
        ),
        "severity": "high",
        "description": "Database connection string",
    },
    "slack_token": {
        "regex": re.compile(r"""xox[baprs]-[A-Za-z0-9\-]{10,}"""),
        "severity": "critical",
        "description": "Slack token",
    },
    "stripe_key": {
        "regex": re.compile(r"""(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{20,}"""),
        "severity": "critical",
        "description": "Stripe API key",
    },
    "generic_high_entropy": {
        "regex": re.compile(
            r"""(?i)(?:key|secret|token|password)\s*[:=]\s*['"]?([A-Za-z0-9+/=_\-]{32,})['"]?"""
        ),
        "severity": "medium",
        "description": "High-entropy secret candidate",
    },
}

# Sensitive file patterns
SENSITIVE_FILE_PATTERNS = [
    re.compile(r"^\.env$", re.IGNORECASE),
    re.compile(r"\.env\.\w+$", re.IGNORECASE),
    re.compile(r"\.pem$", re.IGNORECASE),
    re.compile(r"\.key$", re.IGNORECASE),
    re.compile(r"\.p12$", re.IGNORECASE),
    re.compile(r"\.pfx$", re.IGNORECASE),
    re.compile(r"id_rsa", re.IGNORECASE),
    re.compile(r"id_ed25519", re.IGNORECASE),
    re.compile(r"\.htpasswd$", re.IGNORECASE),
    re.compile(r"credentials", re.IGNORECASE),
    re.compile(r"\.secret$", re.IGNORECASE),
]

# File extensions to scan for code secrets
CODE_EXTENSIONS = {".py", ".sh", ".bash", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf", ".env"}
DOC_EXTENSIONS = {".md", ".txt", ".rst", ".json"}

# Files to skip during scanning
SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    ".mypy_cache", ".pytest_cache",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

class Finding:
    def __init__(self, file_path, line_no, pattern_name, severity, description, match_text, context=""):
        self.file_path = file_path
        self.line_no = line_no
        self.pattern_name = pattern_name
        self.severity = severity
        self.description = description
        self.match_text = self._redact(match_text)
        self.context = context

    def _redact(self, text):
        """Redact the middle portion of a matched secret."""
        if len(text) <= 8:
            return text
        show = min(4, len(text) // 4)
        return text[:show] + "..." + text[-show:]

    def to_dict(self):
        return {
            "file": self.file_path,
            "line": self.line_no,
            "pattern": self.pattern_name,
            "severity": self.severity,
            "description": self.description,
            "match": self.match_text,
            "context": self.context.strip() if self.context else "",
        }


def _should_skip(dir_name):
    return dir_name in SKIP_DIRS or dir_name.startswith(".")


def _is_sensitive_file(filename):
    return any(p.search(filename) for p in SENSITIVE_FILE_PATTERNS)


def _get_extension(filepath):
    _, ext = os.path.splitext(filepath)
    return ext.lower()


def _file_mode_octal(filepath):
    try:
        st = os.stat(filepath)
        return oct(stat.S_IMODE(st.st_mode))
    except OSError:
        return None


def _is_world_writable(filepath):
    try:
        st = os.stat(filepath)
        return bool(st.st_mode & stat.S_IWOTH)
    except OSError:
        return False


def _is_executable(filepath):
    try:
        st = os.stat(filepath)
        return bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    except OSError:
        return False


# ─── Scans ────────────────────────────────────────────────────────────────────

def scan_secrets_in_files(scan_roots):
    """1. Scan .md and code files for secrets."""
    findings = []
    files_scanned = 0

    for root in scan_roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune skip dirs in-place
            dirnames[:] = [d for d in dirnames if not _should_skip(d)]

            for fname in filenames:
                ext = _get_extension(fname)
                fp = os.path.join(dirpath, fname)

                # Skip binary, venv, large files
                if ext in {".pyc", ".pyo", ".so", ".o", ".bin", ".png", ".jpg",
                           ".gif", ".mp4", ".zip", ".gz", ".tar", ".sqlite", ".db"}:
                    continue

                # Only scan relevant extensions
                if ext not in CODE_EXTENSIONS and ext not in DOC_EXTENSIONS:
                    continue

                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                except (OSError, UnicodeDecodeError):
                    continue

                files_scanned += 1
                for i, line in enumerate(lines, 1):
                    for pname, pcfg in PATTERNS.items():
                        m = pcfg["regex"].search(line)
                        if m:
                            # Get context: the matched line
                            context = line if len(line) < 200 else line[:200] + "..."
                            # Try to get surrounding line for more context
                            if i > 1 and i < len(lines):
                                context = lines[i - 2].rstrip() + "\n" + context
                            findings.append(Finding(
                                file_path=fp,
                                line_no=i,
                                pattern_name=pname,
                                severity=pcfg["severity"],
                                description=pcfg["description"],
                                match_text=m.group(0),
                                context=context,
                            ))

    return findings, files_scanned


def check_file_permissions(scan_roots):
    """2. Check file permissions — no world-writable, no executable where not needed."""
    issues = []

    for root in scan_roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not _should_skip(d)]

            for fname in filenames:
                fp = os.path.join(dirpath, fname)
                ext = _get_extension(fname)

                # World-writable check
                if _is_world_writable(fp):
                    issues.append({
                        "file": fp,
                        "issue": "world_writable",
                        "severity": "high",
                        "message": f"World-writable: {_file_mode_octal(fp)}",
                    })

                # Executable check for non-script files
                if _is_executable(fp) and ext in {".py", ".md", ".txt", ".json",
                                                    ".yaml", ".yml", ".toml", ".cfg"}:
                    issues.append({
                        "file": fp,
                        "issue": "executable_not_needed",
                        "severity": "low",
                        "message": f"Unnecessary executable bit on {ext} file",
                    })

    return issues


def check_gitignore():
    """3. Verify .gitignore includes sensitive patterns."""
    required_patterns = [
        ".env",
        ".env.*",
        "*.pem",
        "*.key",
        ".git",
        "__pycache__",
    ]
    found = []
    missing = []

    if not os.path.isfile(GITIGNORE_PATH):
        return {
            "exists": False,
            "missing_required": required_patterns,
            "severity": "high",
        }

    try:
        with open(GITIGNORE_PATH, "r") as f:
            content = f.read()
    except OSError:
        return {
            "exists": True,
            "readable": False,
            "severity": "medium",
        }

    for pattern in required_patterns:
        # Check if the pattern (or close variant) exists
        if pattern in content:
            found.append(pattern)
        else:
            missing.append(pattern)

    return {
        "exists": True,
        "found": found,
        "missing": missing,
        "severity": "high" if missing else "pass",
    }


def check_exposed_env_files(scan_roots):
    """4. Check for exposed .env files that shouldn't be tracked."""
    exposed = []

    for root in scan_roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != ".git"]

            for fname in filenames:
                if not fname.startswith(".env"):
                    continue
                fp = os.path.join(dirpath, fname)

                # Check if it's inside a .git tracked area
                git_dir = os.path.join(dirpath, ".git")
                in_git = os.path.isdir(git_dir) or os.path.isdir(os.path.join(
                    *[os.path.dirname(dirpath)] * min(5, dirpath.count(os.sep))))

                # Check size — non-empty .env files are riskier
                try:
                    size = os.path.getsize(fp)
                except OSError:
                    size = 0

                # Check if file has actual content (not just example)
                has_real_content = False
                try:
                    with open(fp, "r", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                if "=" in line:
                                    _, _, val = line.partition("=")
                                    if val.strip() and val.strip() not in ('""', "''", ""):
                                        has_real_content = True
                                        break
                except OSError:
                    pass

                severity = "critical" if has_real_content else "low"
                exposed.append({
                    "file": fp,
                    "size_bytes": size,
                    "has_real_content": has_real_content,
                    "severity": severity,
                })

    return exposed


def scan_code_files_credentials(scan_roots):
    """5. Scan code files (.py, .sh, .yml) for hardcoded credentials."""
    findings = []
    code_files_scanned = 0

    code_exts = {".py", ".sh", ".bash", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf"}

    for root in scan_roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not _should_skip(d)]

            for fname in filenames:
                ext = _get_extension(fname)
                if ext not in code_exts:
                    continue

                fp = os.path.join(dirpath, fname)
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                except (OSError, UnicodeDecodeError):
                    continue

                code_files_scanned += 1
                for i, line in enumerate(lines, 1):
                    # Skip comments
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith("//"):
                        continue

                    for pname, pcfg in PATTERNS.items():
                        m = pcfg["regex"].search(line)
                        if m:
                            findings.append(Finding(
                                file_path=fp,
                                line_no=i,
                                pattern_name=pname,
                                severity=pcfg["severity"],
                                description=pcfg["description"],
                                match_text=m.group(0),
                                context=stripped[:200],
                            ))

    return findings, code_files_scanned


def get_vault_size(scan_roots):
    """Get total vault size."""
    total = 0
    file_count = 0
    for root in scan_roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not _should_skip(d)]
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                    file_count += 1
                except OSError:
                    pass
    return total, file_count


# ─── Report Generation ────────────────────────────────────────────────────────

def generate_json_report(all_findings, perm_issues, gitignore_result,
                          env_files, code_findings, scan_stats):
    severity_counts = defaultdict(int)
    for f in all_findings:
        severity_counts[f.severity] += 1
    for f in code_findings:
        severity_counts[f.severity] += 1
    for f in perm_issues:
        severity_counts[f["severity"]] += 1

    report = {
        "scanner": "AL-MUKH Security Scanner v1.0",
        "generated": datetime.now(timezone.utc).isoformat(),
        "scan_roots": SCAN_ROOTS,
        "stats": scan_stats,
        "summary": {
            "secret_findings": len(all_findings) + len(code_findings),
            "permission_issues": len(perm_issues),
            "exposed_env_files": len(env_files),
            "gitignore_ok": gitignore_result["severity"] == "pass",
            "severity_breakdown": dict(severity_counts),
        },
        "findings": {
            "secrets_in_files": [f.to_dict() for f in all_findings],
            "secrets_in_code": [f.to_dict() for f in code_findings],
            "permission_issues": perm_issues,
            "gitignore": gitignore_result,
            "exposed_env_files": env_files,
        },
    }

    # Overall risk
    crit = severity_counts.get("critical", 0)
    high = severity_counts.get("high", 0)
    if crit > 0:
        report["summary"]["risk_level"] = "CRITICAL"
    elif high > 0:
        report["summary"]["risk_level"] = "HIGH"
    elif severity_counts.get("medium", 0) > 0:
        report["summary"]["risk_level"] = "MEDIUM"
    else:
        report["summary"]["risk_level"] = "LOW"

    return report


def generate_markdown_report(report):
    s = report["summary"]
    risk = s["risk_level"]

    lines = [
        "# AL-MUKH Security Report",
        "",
        f"**Generated:** {report['generated']}",
        f"**Scan Roots:** {len(report['scan_roots'])} directories",
        f"**Risk Level:** {risk}",
        "",
    ]

    # Summary table
    lines.extend([
        "## Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Secret findings | {s['secret_findings']} |",
        f"| Permission issues | {s['permission_issues']} |",
        f"| Exposed .env files | {s['exposed_env_files']} |",
        f"| Gitignore OK | {'Yes' if s['gitignore_ok'] else 'No'} |",
        "",
    ])

    # Severity breakdown
    if s["severity_breakdown"]:
        lines.append("### Severity Breakdown")
        lines.append("")
        for sev in ["critical", "high", "medium", "low"]:
            cnt = s["severity_breakdown"].get(sev, 0)
            if cnt > 0:
                lines.append(f"- **{sev.upper()}:** {cnt}")
        lines.append("")

    # Secret findings
    all_secrets = report["findings"]["secrets_in_files"] + report["findings"]["secrets_in_code"]
    if all_secrets:
        lines.extend([
            "## Secret Findings",
            "",
        ])
        # Group by file
        by_file = defaultdict(list)
        for f in all_secrets:
            by_file[f["file"]].append(f)

        for fpath, findings in list(by_file.items())[:30]:
            lines.append(f"### `{fpath}`")
            for f in findings:
                lines.append(
                    f"- Line {f['line']}: **[{f['severity'].upper()}]** "
                    f"{f['description']} — `{f['match']}`"
                )
            lines.append("")
    else:
        lines.extend(["## Secret Findings", "", "No secrets found.", ""])

    # Permission issues
    if report["findings"]["permission_issues"]:
        lines.extend([
            "## Permission Issues",
            "",
        ])
        for issue in report["findings"]["permission_issues"][:30]:
            lines.append(
                f"- `{issue['file']}`: [{issue['severity'].upper()}] {issue['message']}"
            )
        lines.append("")

    # Exposed .env files
    env_files = report["findings"]["exposed_env_files"]
    if env_files:
        lines.extend([
            "## Exposed .env Files",
            "",
        ])
        for ef in env_files:
            lines.append(
                f"- `{ef['file']}`: {ef['size_bytes']} bytes, "
                f"{'HAS CREDENTIALS' if ef['has_real_content'] else 'empty/example'} "
                f"[{ef['severity'].upper()}]"
            )
        lines.append("")

    # Gitignore
    gi = report["findings"]["gitignore"]
    if not gi.get("exists"):
        lines.extend([
            "## Gitignore Status",
            "",
            "⚠ `.gitignore` not found!",
            "",
            "**Missing patterns:**",
        ])
        for p in gi.get("missing_required", []):
            lines.append(f"- `{p}`")
        lines.append("")
    elif gi.get("missing"):
        lines.extend([
            "## Gitignore Status",
            "",
            f"⚠ Missing {len(gi['missing'])} recommended patterns:",
            "",
        ])
        for p in gi["missing"]:
            lines.append(f"- `{p}`")
        lines.append("")

    lines.extend([
        "---",
        f"*Generated by AL-MUKH Security Scanner v1.0*",
    ])
    return "\n".join(lines)


def save_report(report, fmt="json"):
    report_dir = os.path.join(MASTER_VAULT, "refs")
    os.makedirs(report_dir, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if fmt == "json":
        path = os.path.join(report_dir, f"security_{ts}.json")
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
    else:
        md = generate_markdown_report(report)
        path = os.path.join(report_dir, f"security_{ts}.md")
        with open(path, "w") as f:
            f.write(md)

    print(f"  Report saved: {path}")
    return path


# ─── Runner ───────────────────────────────────────────────────────────────────

def run_full_scan():
    print("─── AL-MUKH Security Scanner v1.0 ───")
    print()

    print("  [1/5] Scanning for secrets in documents...")
    secrets_in_docs, docs_scanned = scan_secrets_in_files(SCAN_ROOTS)
    print(f"         Found {len(secrets_in_docs)} findings in {docs_scanned} files")

    print("  [2/5] Checking file permissions...")
    perm_issues = check_file_permissions(SCAN_ROOTS)
    print(f"         Found {len(perm_issues)} permission issues")

    print("  [3/5] Checking .gitignore...")
    gi_result = check_gitignore()
    gi_status = "OK" if gi_result["severity"] == "pass" else f"Missing {len(gi_result.get('missing', []))} patterns"
    print(f"         {gi_status}")

    print("  [4/5] Checking exposed .env files...")
    env_files = check_exposed_env_files(SCAN_ROOTS)
    print(f"         Found {len(env_files)} .env files")

    print("  [5/5] Scanning code files for credentials...")
    secrets_in_code, code_scanned = scan_code_files_credentials(SCAN_ROOTS)
    print(f"         Found {len(secrets_in_code)} findings in {code_scanned} files")

    print()

    # Merge all findings
    all_findings = secrets_in_docs + secrets_in_code

    scan_stats = {
        "docs_scanned": docs_scanned,
        "code_files_scanned": code_scanned,
        "scan_roots": SCAN_ROOTS,
        "total_secrets": len(all_findings),
    }

    report = generate_json_report(
        secrets_in_docs, perm_issues, gi_result,
        env_files, secrets_in_code, scan_stats,
    )

    return report


def print_summary(report):
    s = report["summary"]
    risk = s["risk_level"]

    icon = {"CRITICAL": "✗✗", "HIGH": "✗", "MEDIUM": "⚠", "LOW": "✓"}.get(risk, "?")

    print(f"  Risk Level: {icon} {risk}")
    print(f"  Secrets: {s['secret_findings']}")
    print(f"  Permission Issues: {s['permission_issues']}")
    print(f"  Exposed .env Files: {s['exposed_env_files']}")
    print(f"  Gitignore OK: {'Yes' if s['gitignore_ok'] else 'No'}")

    if s["severity_breakdown"]:
        print()
        print("  Severity Breakdown:")
        for sev in ["critical", "high", "medium", "low"]:
            cnt = s["severity_breakdown"].get(sev, 0)
            if cnt:
                print(f"    {sev.upper():10s}: {cnt}")


# ─── CLI ──────────────────────────────────────────────────────────────────────

USAGE = """
AL-MUKH Security Scanner v1.0

Usage:
  python security.py scan      Scan all files for security issues
  python security.py report    Scan and generate markdown report
  python security.py json      Scan and output JSON report
  python security.py --help    Show this help

Examples:
  python security.py scan
  python security.py report
"""


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print(USAGE)
        return

    cmd = args[0].lower()

    if cmd == "scan":
        report = run_full_scan()
        print_summary(report)
        save_report(report, "json")

    elif cmd == "report":
        report = run_full_scan()
        print_summary(report)
        print()
        md = generate_markdown_report(report)
        print(md)
        save_report(report, "md")

    elif cmd == "json":
        report = run_full_scan()
        print_summary(report)
        print()
        print(json.dumps(report, indent=2))
        save_report(report, "json")

    else:
        print(f"Unknown command: {cmd}")
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
