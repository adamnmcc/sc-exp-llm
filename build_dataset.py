"""Build one training record per DeFiHackLabs exploit PoC.

Replaces the month-grouping in downloader.py, which bundled every exploit in a
YYYY-MM directory into a single record. Here each `*_exp.sol` is one incident:
its header comment block becomes the analysis, the file becomes the PoC.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

REPO = "https://github.com/SunWeb3Sec/DeFiHackLabs.git"
CACHE = Path(".cache/DeFiHackLabs")
OUT = Path("raw_web3_data")
TEST_DIR = "src/test"

DECL = re.compile(r"^\s*(abstract\s+contract|contract|interface|library)\b")
SKIP = re.compile(r"^\s*(//\s*SPDX|pragma\b|import\b)")


def sync_repo():
    if CACHE.exists():
        subprocess.run(["git", "-C", str(CACHE), "pull", "--ff-only"], check=False,
                       capture_output=True)
    else:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", REPO, str(CACHE)], check=True)


def extract_analysis(text):
    """Header comment block (root cause + attack walkthrough), minus boilerplate."""
    out = []
    for line in text.splitlines():
        if DECL.match(line):
            break
        if SKIP.match(line):
            continue
        s = line.strip()
        if s.startswith("//"):
            out.append(s.lstrip("/").strip())
        elif s.startswith(("/*", "*", "*/")):
            out.append(s.lstrip("/*").rstrip("*/").strip())
    cleaned = "\n".join(l for l in out if l)
    return cleaned.strip()


def is_incident(path: Path):
    name = path.name.lower()
    if not name.endswith(".sol"):
        return False
    if name in {"interface.sol", "basetest.sol"}:
        return False
    if "template" in name or name.endswith("test.sol") and "_exp" not in name:
        return False
    return name.endswith("_exp.sol")


def build():
    sync_repo()
    test_root = CACHE / TEST_DIR
    sols = sorted(p for p in test_root.rglob("*.sol") if is_incident(p))
    if not sols:
        raise SystemExit(f"No exploit files under {test_root}")

    # fresh per-incident JSONs; remove old month-grouped ones
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()

    kept, skipped = 0, 0
    for sol in sols:
        code = sol.read_text(encoding="utf-8", errors="replace").strip()
        analysis = extract_analysis(code)
        if len(analysis) < 40:                      # no usable write-up in header
            analysis = "Root-cause write-up unavailable; Foundry PoC provided directly."
            skipped += 1
        rel = sol.relative_to(CACHE).as_posix()
        month = sol.parent.name
        incident = sol.stem[:-4] if sol.stem.endswith("_exp") else sol.stem
        payload = {
            "incident": incident,
            "month": month,
            "source_path": rel,
            "analysis": analysis,
            "poc_code": code,
        }
        (OUT / f"{month}__{incident}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False))
        kept += 1

    print(f"Built {kept} incident records ({skipped} lacked a header write-up).")
    return kept


if __name__ == "__main__":
    build()
