"""Harvest Code4rena audit findings into (code + root-cause) training records.

Each `code-423n4/*-findings` repo has a report.md: the consolidated, curated,
deduplicated official report. High/Medium findings are headed
`## [[H-01] title](issue-link)`. Prose is the analysis; embedded ```solidity
blocks are the vulnerable code. Low/QA/Gas (L-/G-/Q-) are excluded by the
[HM] severity match.

Uses the `gh` CLI (authenticated).
"""
import argparse
import base64
import json
import re
import subprocess
from pathlib import Path

OUT = Path("raw_code4rena")
FINDING = re.compile(r"^##\s*\[+\s*([HM])-0*(\d+)\s*\]\s*(.+?)\]\([^)]*\)", re.MULTILINE)
SECTION = re.compile(r"^#\s", re.MULTILINE)
SOLIDITY = re.compile(r"```(?:solidity|sol)?\s*\n(.*?)```", re.DOTALL)


def findings_repos(limit=None):
    out = subprocess.run(
        ["gh", "repo", "list", "code-423n4", "--limit", "2000",
         "--json", "name", "--jq", ".[].name"],
        capture_output=True, text=True)
    names = [n for n in out.stdout.splitlines() if n.endswith("-findings")]
    return names[:limit] if limit else names


def fetch_report(repo):
    r = subprocess.run(
        ["gh", "api", f"repos/code-423n4/{repo}/contents/report.md", "--jq", ".content"],
        capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return base64.b64decode(r.stdout).decode("utf-8", errors="replace")
    except Exception:
        return None


def parse_findings(report, contest):
    hits = list(FINDING.finditer(report))
    records = []
    for i, m in enumerate(hits):
        sev = "High" if m.group(1) == "H" else "Medium"
        title = m.group(3).strip()
        start = m.end()
        end = hits[i + 1].start() if i + 1 < len(hits) else len(report)
        body = report[start:end].strip()
        code = "\n\n".join(b.strip() for b in SOLIDITY.findall(body) if b.strip())
        records.append({
            "source": "code4rena", "contest": contest, "severity": sev,
            "title": title, "analysis": body, "code": code,
        })
    return records


def build(limit=None):
    repos = findings_repos(limit)
    OUT.mkdir(exist_ok=True)
    total, with_code, no_report = 0, 0, 0
    for repo in repos:
        contest = repo[:-len("-findings")]
        report = fetch_report(repo)
        if not report:
            no_report += 1
            continue
        for rec in parse_findings(report, contest):
            total += 1
            if rec["code"]:
                with_code += 1
            (OUT / f"{contest}__{rec['severity'][0]}_{total}.json").write_text(
                json.dumps(rec, indent=2, ensure_ascii=False))
    print(f"repos={len(repos)} no_report={no_report} findings={total} with_code={with_code}")
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    build(args.limit)
