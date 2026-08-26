import glob
import json


def generate_dual_output_dataset():
    json_files = glob.glob("./raw_web3_data/*.json")
    mlx_records = []

    for file_path in json_files:
        with open(file_path, "r") as f:
            data = json.load(f)

        incident = str(data.get("incident", "unknown-incident")).strip()
        analysis = str(data.get("analysis", "")).strip()
        poc_code = str(data.get("poc_code", "")).strip()

        prompt = (
            "<|im_start|>system\n"
            "You are an expert Web3 security auditor. Provide a precise root-cause analysis and a working Foundry PoC exploit.\n"
            "<|im_end|>\n"
            "<|im_start|>user\n"
            f"Audit the protocol incident: {incident}\n"
            "Explain the vulnerability and give a minimal executable Foundry exploit that demonstrates it.\n"
            "<|im_end|>\n"
            "<|im_start|>assistant\n"
            "### 1. VULNERABILITY EXPLANATION\n"
            f"{analysis}\n\n"
            "### 2. FOUNDRY PROOF OF CONCEPT EXPLOIT\n"
            "```solidity\n"
            f"{poc_code}\n"
            "```\n"
            "<|im_end|>\n"
        )

        mlx_records.append({"text": prompt})

    with open("train.jsonl", "w") as out:
        for record in mlx_records:
            out.write(json.dumps(record) + "\n")

    print(f"Compiled {len(mlx_records)} structured dual-output training targets.")


if __name__ == "__main__":
    generate_dual_output_dataset()

