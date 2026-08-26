"""Harvest Sherlock audit findings into (code + root-cause) training records.

Each `sherlock-audit/*-judging` repo has a README.md that is the consolidated,
validated, deduplicated final report. Findings are headed `# Issue H-N:` /
`# Issue M-N:` (severity in the id). We parse those blocks: the prose is the
analysis, embedded ```solidity blocks are the vulnerable code.

Uses the `gh` CLI (authenticated: 5000 req/hr, no throttling).
"""
import argparse
import base64
import json
import re
import subprocess
from pathlib import Path

OUT = Path("raw_sherlock")
FINDING = re.compile(r"^#{1,2}\s*Issue\s+([HM])-(\d+)\s*:?\s*(.*)$", re.MULTILINE)
SOLIDITY = re.compile(r"```(?:solidity|sol)?\s*\n(.*?)```", re.DOTALL)


def gh_json(path, paginate=False):
    cmd = ["gh", "api", path, "--jq", "."]
    if paginate:
        cmd.insert(3, "--paginate")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return r.stdout


def judging_repos(limit=None):
    out = subprocess.run(
        ["gh", "repo", "list", "sherlock-audit", "--limit", "1000",
         "--json", "name", "--jq", ".[].name"],
        capture_output=True, text=True)
    names = [n for n in out.stdout.splitlines() if n.endswith("-judging")]
    return names[:limit] if limit else names


def fetch_readme(repo):
    r = subprocess.run(
        ["gh", "api", f"repos/sherlock-audit/{repo}/contents/README.md",
         "--jq", ".content"], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return base64.b64decode(r.stdout).decode("utf-8", errors="replace")
    except Exception:
        return None


def parse_findings(readme, contest):
    hits = list(FINDING.finditer(readme))
    records = []
    for i, m in enumerate(hits):
        sev = "High" if m.group(1) == "H" else "Medium"
        title = m.group(3).strip()
        start = m.end()
        end = hits[i + 1].start() if i + 1 < len(hits) else len(readme)
        body = readme[start:end].strip()
        code = "\n\n".join(b.strip() for b in SOLIDITY.findall(body) if b.strip())
        records.append({
            "source": "sherlock",
            "contest": contest,
            "severity": sev,
            "title": title,
            "analysis": body,
            "code": code,
        })
    return records


def build(limit=None):
    repos = judging_repos(limit)
    OUT.mkdir(exist_ok=True)
    total, with_code, no_readme = 0, 0, 0
    for repo in repos:
        contest = repo[:-len("-judging")]
        readme = fetch_readme(repo)
        if not readme:
            no_readme += 1
            continue
        for rec in parse_findings(readme, contest):
            total += 1
            if rec["code"]:
                with_code += 1
            fname = f"{contest}__{rec['severity'][0]}_{total}.json"
            (OUT / fname).write_text(json.dumps(rec, indent=2, ensure_ascii=False))
    print(f"repos={len(repos)} no_readme={no_readme} findings={total} with_code={with_code}")
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="max repos (test with a few)")
    args = ap.parse_args()
    build(args.limit)
