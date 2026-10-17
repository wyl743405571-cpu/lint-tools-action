#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lint GitHub Action entrypoint (stdlib only — no pip install needed on runner).

Reads inputs from INPUT_* env vars, scans matched files against the Lint
code-aware grammar + security APIs, posts a PR comment, and optionally fails.
"""
import os
import sys
import json
import glob
import urllib.request

API_BASE = os.environ.get("LINT_API_BASE", "https://tools.aicreditsapi.com").rstrip("/")
API_KEY = os.environ.get("INPUT_LINT_API_KEY", "")
# Cloudflare blocks the default urllib UA (403/1010); send a browser UA so the
# Action's requests are not mistaken for a bot.
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
GITHUB_TOKEN = os.environ.get("INPUT_GITHUB_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
SCAN_PATHS = os.environ.get("INPUT_SCAN_PATHS", "**/*.py **/*.js **/*.ts **/*.go **/*.rb **/*.php **/*.md").split()
CHECK_GRAMMAR = os.environ.get("INPUT_CHECK_GRAMMAR", "true").lower() == "true"
CHECK_SECURITY = os.environ.get("INPUT_CHECK_SECURITY", "true").lower() == "true"
FAIL_ON_FINDINGS = os.environ.get("INPUT_FAIL_ON_FINDINGS", "false").lower() == "true"
try:
    MAX_CHARS = int(os.environ.get("INPUT_MAX_CHARS", "4000"))
except ValueError:
    MAX_CHARS = 4000

CODE_EXT = {".py", ".js", ".ts", ".go", ".rb", ".php"}


def call(endpoint, text):
    url = "%s/tools/api/%s" % (API_BASE, endpoint)
    payload = json.dumps({"text": text, "api_key": API_KEY}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json", "User-Agent": UA}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        if isinstance(d, dict) and d.get("success"):
            return d.get("result", "")
    except Exception as e:  # noqa: BLE001
        return "[error calling %s: %s]" % (endpoint, e)
    return ""


def collect_files():
    out = []
    seen = set()
    for pat in SCAN_PATHS:
        pat = pat.strip()
        if not pat:
            continue
        for f in glob.glob(pat, recursive=True):
            if os.path.isfile(f) and f not in seen:
                seen.add(f)
                out.append(f)
    return out[:50]


def main():
    files = collect_files()
    findings = []  # (file, kind, text)
    for f in files:
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except Exception:  # noqa: BLE001
            continue
        if len(content) > MAX_CHARS:
            content = content[:MAX_CHARS]
        ext = os.path.splitext(f)[1].lower()
        if CHECK_SECURITY and ext in CODE_EXT:
            res = call("security-scan", content)
            if res and "finding" in res.lower():
                findings.append((f, "security", res))
        if CHECK_GRAMMAR:
            res = call("grammar-check", content)
            if res and res.strip() and res.strip() != content.strip():
                findings.append((f, "grammar", res))

    report = ["## 🔍 Lint scan results", ""]
    if not findings:
        report.append("✅ No grammar or security findings on the scanned files.")
    else:
        for f, kind, res in findings:
            report.append("### `%s` — %s" % (f, kind))
            report.append(res[:1500])
            report.append("")
    report_md = "\n".join(report)
    print(report_md)

    # Post as a PR comment when running in a PR context.
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if GITHUB_TOKEN and event_path and os.path.exists(event_path):
        try:
            with open(event_path, encoding="utf-8") as fh:
                ev = json.load(fh)
            pr = ev.get("pull_request") or ev.get("issue")
            if pr and pr.get("number"):
                repo = os.environ.get("GITHUB_REPOSITORY", "")
                num = pr["number"]
                url = "https://api.github.com/repos/%s/issues/%s/comments" % (repo, num)
                req = urllib.request.Request(
                    url, data=json.dumps({"body": report_md}).encode("utf-8"),
                    headers={
                        "Authorization": "Bearer %s" % GITHUB_TOKEN,
                        "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json",
                    }, method="POST")
                urllib.request.urlopen(req, timeout=20)
        except Exception as e:  # noqa: BLE001
            print("PR comment post failed: %s" % e)

    if FAIL_ON_FINDINGS and findings:
        sys.exit(1)


if __name__ == "__main__":
    main()
