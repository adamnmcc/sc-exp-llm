"""Harvest the SWC registry (canonical weakness taxonomy) into records.

entries/docs/SWC-*.md: each has # Title, ## Description, ## Remediation,
## Samples (```solidity). Small (~37), canonical, but unmaintained since 2020
and Solidity 0.5-era. Kept opt-in in the final mix. Excludes *_fixed samples so
we never label patched code as vulnerable.

Uses the `gh` CLI.
"""
import base64
import json
import re
import subprocess
from pathlib import Path

REPO = "SmartContractSecurity/SWC-registry"
OUT = Path("raw_swc")
SECT = re.compile(r"^##\s+(.*)$", re.MULTILINE)
SAMPLE_FILE = re.compile(r"^###\s+(.*)$", re.MULTILINE)
SOLIDITY = re.compile(r"```(?:solidity|sol)?\s*\n(.*?)```", re.DOTALL)


def gh_content(path):
    r = subprocess.run(["gh", "api", f"repos/{REPO}/contents/{path}", "--jq", ".content"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return base64.b64decode(r.stdout).decode("utf-8", errors="replace")
    except Exception:
        return None


def section(md, name):
    heads = list(SECT.finditer(md))
    for i, h in enumerate(heads):
        if h.group(1).strip().lower() == name:
            end = heads[i + 1].start() if i + 1 < len(heads) else len(md)
            return md[h.end():end].strip()
    return ""


def title_of(md):
    m = re.search(r"^#\s+Title\s*\n+(.+)$", md, re.MULTILINE)
    return m.group(1).strip() if m else ""


def build():
    listing = subprocess.run(
        ["gh", "api", f"repos/{REPO}/contents/entries/docs", "--jq", ".[].name"],
        capture_output=True, text=True).stdout
    entries = [n for n in listing.splitlines() if re.match(r"SWC-\d+\.md", n)]
    OUT.mkdir(exist_ok=True)
    kept = 0
    for name in entries:
        md = gh_content(f"entries/docs/{name}")
        if not md:
            continue
        title = title_of(md)
        desc = section(md, "description")
        remediation = section(md, "remediation")
        samples = section(md, "samples")
        # take the first sample whose ### filename isn't a fixed/secure variant
        code = ""
        parts = re.split(r"^###\s+(.*)$", samples, flags=re.MULTILINE)
        for j in range(1, len(parts), 2):
            fname, block = parts[j].lower(), parts[j + 1]
            if any(x in fname for x in ("fixed", "secure", "remediat")):
                continue
            sols = SOLIDITY.findall(block)
            if sols:
                code = sols[0].strip()
                break
        if not (title and desc):
            continue
        analysis = f"Vulnerability class: {title}\n\n{desc}\n\nRemediation:\n{remediation}".strip()
        rec = {"source": "swc", "id": name[:-3], "severity": "taxonomy",
               "title": title, "analysis": analysis, "code": code}
        (OUT / f"{name[:-3]}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False))
        kept += 1
    print(f"SWC entries: {kept} (with code: {sum(1 for f in OUT.glob('*.json') if json.load(open(f))['code'])})")
    return kept


if __name__ == "__main__":
    build()
