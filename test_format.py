import json
import os
import tempfile
import unittest

import format


class FormatTests(unittest.TestCase):
    def test_qwen_template_aligns_with_chat_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            os.makedirs("raw_web3_data", exist_ok=True)

            payload = {
                "incident": "2024-01",
                "analysis": "The protocol drained funds because the reentrancy guard was bypassed.",
                "poc_code": "pragma solidity ^0.8.0; contract Exploit { function run() external {} }",
            }
            with open("raw_web3_data/2024-01.json", "w") as handle:
                json.dump(payload, handle)

            format.generate_dual_output_dataset()

            with open("train.jsonl", "r") as handle:
                line = handle.readline().strip()

            row = json.loads(line)
            self.assertIn("<|im_start|>system", row["text"])
            self.assertNotIn("<|im_start| >system", row["text"])
            self.assertIn("<|im_start|>assistant", row["text"])
            self.assertIn("### 1. VULNERABILITY EXPLANATION", row["text"])
            self.assertIn("### 2. FOUNDRY PROOF OF CONCEPT EXPLOIT", row["text"])


if __name__ == "__main__":
    unittest.main()
