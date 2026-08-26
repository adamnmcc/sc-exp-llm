"""Merge DeFiHackLabs + Sherlock records into train.jsonl with per-source templates.

DeFiHackLabs (raw_web3_data/*.json): incident -> root-cause analysis + Foundry PoC.
Sherlock    (raw_sherlock/*.json):   vulnerable code -> root-cause analysis (code-in).

Different task shapes get different chat templates so the model learns both
behaviours cleanly instead of a blur.
"""
import glob
import json
import re

OUT = "train.jsonl"

SYS_POC = ("You are an expert Web3 security auditor. Provide a precise root-cause "
           "analysis and a working Foundry PoC exploit.")
SYS_AUDIT = ("You are an expert Web3 security auditor. Given contract code, identify "
             "the vulnerability and explain its root cause.")


def wrap(system, user, assistant):
    return ("<|im_start|>system\n" + system + "\n<|im_end|>\n"
            "<|im_start|>user\n" + user + "\n<|im_end|>\n"
            "<|im_start|>assistant\n" + assistant + "\n<|im_end|>\n")


def clean_sherlock(analysis):
    lines = analysis.splitlines()
    out, skip_found_by = [], False
    for ln in lines:
        s = ln.strip()
        if s.startswith("Source:"):
            continue
        if s.startswith("## Found by"):
            skip_found_by = True
            continue
        if s.startswith("_Submitted by") and s.endswith("_"):
            continue
        if skip_found_by:
            if not s:
                skip_found_by = False
            continue  # drop the watson-names line(s)
        out.append(ln)
    return "\n".join(out).strip()


def defihacklabs_records():
    recs = []
    for f in glob.glob("raw_web3_data/*.json"):
        d = json.load(open(f))
        incident = str(d.get("incident", "unknown-incident")).strip()
        analysis = str(d.get("analysis", "")).strip()
        poc = str(d.get("poc_code", "")).strip()
        if not poc:
            continue
        user = (f"Audit the protocol incident: {incident}\n"
                "Explain the vulnerability and give a minimal executable Foundry "
                "exploit that demonstrates it.")
        assistant = ("### 1. VULNERABILITY EXPLANATION\n" + analysis +
                     "\n\n### 2. FOUNDRY PROOF OF CONCEPT EXPLOIT\n"
                     "```solidity\n" + poc + "\n```")
        recs.append(wrap(SYS_POC, user, assistant))
    return recs


def audit_records():
    recs = []
    for f in glob.glob("raw_sherlock/*.json") + glob.glob("raw_code4rena/*.json"):
        d = json.load(open(f))
        code = str(d.get("code", "")).strip()
        analysis = clean_sherlock(str(d.get("analysis", "")).strip())
        if not code or len(analysis) < 60:
            continue
        sev = d.get("severity", "unknown")
        user = (f"Audit the following Solidity from a {sev}-severity issue. "
                "Identify the vulnerability and explain the root cause.\n"
                "```solidity\n" + code + "\n```")
        recs.append(wrap(SYS_AUDIT, user, analysis))
    return recs


def build():
    a = defihacklabs_records()
    b = audit_records()
    with open(OUT, "w", encoding="utf-8") as out:
        for text in a + b:
            out.write(json.dumps({"text": text}, ensure_ascii=False) + "\n")
    print(f"train.jsonl: {len(a)} DeFiHackLabs (PoC) + {len(b)} audit (code-in) "
          f"= {len(a) + len(b)} records")
    return len(a), len(b)


if __name__ == "__main__":
    build()
