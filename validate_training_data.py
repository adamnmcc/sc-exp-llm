import json
from pathlib import Path


def validate_data():
    raw_dir = Path("./raw_web3_data")
    train_file = Path("./train.jsonl")

    if not raw_dir.exists():
        raise FileNotFoundError("raw_web3_data directory not found. Run downloader.py first.")

    json_files = sorted(raw_dir.glob("*.json"))
    if not json_files:
        raise FileNotFoundError("No harvested JSON files found in raw_web3_data.")

    examples = []
    for file_path in json_files[:3]:
        with file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        examples.append({
            "incident": data.get("incident"),
            "analysis_len": len(str(data.get("analysis", ""))),
            "poc_len": len(str(data.get("poc_code", ""))),
        })

    with train_file.open("w", encoding="utf-8") as out:
        for file_path in json_files:
            with file_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)

            prompt = (
                "<|im_start|>system\n"
                "You are an expert Web3 security auditor. Provide a precise root-cause analysis and a working Foundry PoC exploit.\n"
                "<|im_end|>\n"
                "<|im_start|>user\n"
                f"Audit the protocol incident: {data.get('incident', 'unknown-incident')}\n"
                "Explain the vulnerability and give a minimal executable Foundry exploit that demonstrates it.\n"
                "<|im_end|>\n"
                "<|im_start|>assistant\n"
                "### 1. VULNERABILITY EXPLANATION\n"
                f"{data.get('analysis', '')}\n\n"
                "### 2. FOUNDRY PROOF OF CONCEPT EXPLOIT\n"
                "```solidity\n"
                f"{data.get('poc_code', '')}\n"
                "```\n"
                "<|im_end|>\n"
            )
            out.write(json.dumps({"text": prompt}, ensure_ascii=False) + "\n")

    print(f"Validated {len(json_files)} training examples.")
    for item in examples:
        print(item)


if __name__ == "__main__":
    validate_data()
