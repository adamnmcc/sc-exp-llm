import json
import os
import tempfile
import unittest
from unittest.mock import patch

import downloader


class FakeResponse:
    def __init__(self, *, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or []
        self.text = text

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class DownloaderTests(unittest.TestCase):
    def test_repo_layout_matches_expected_target(self):
        repo_tree = [
            {"path": "src/test", "type": "tree"},
            {"path": "src/test/2024-01", "type": "tree"},
            {"path": "src/test/2024-01/Exploit.sol", "type": "blob"},
        ]
        self.assertEqual(downloader.infer_target_dir(repo_tree), "src/test")

    def test_harvest_creates_at_least_one_dataset_file(self):
        def fake_get(url, *args, **kwargs):
            if url.endswith("/git/trees/main?recursive=1"):
                return FakeResponse(json_data={
                    "tree": [
                        {"path": "src/test/2024-01", "type": "tree"},
                        {"path": "src/test/2024-01/README.md", "type": "blob"},
                        {"path": "src/test/2024-01/Exploit.sol", "type": "blob"},
                    ]
                })
            if url.endswith("/README.md"):
                return FakeResponse(text="# Incident summary\nThe protocol drained funds.")
            if url.endswith("/Exploit.sol"):
                return FakeResponse(text="pragma solidity ^0.8.0; contract Exploit { function run() external {} }")
            return FakeResponse(status_code=404)

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            with patch.object(downloader, "fetch_repo_tree", return_value=[
                {"path": "src/test/2024-01", "type": "tree"},
                {"path": "src/test/2024-01/README.md", "type": "blob"},
                {"path": "src/test/2024-01/Exploit.sol", "type": "blob"},
            ]), patch.object(downloader, "download_file_content", side_effect=lambda url: {
                "https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/main/src/test/2024-01/README.md": "# Incident summary\nThe protocol drained funds.",
                "https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/main/src/test/2024-01/Exploit.sol": "pragma solidity ^0.8.0; contract Exploit { function run() external {} }",
            }.get(url, "")):
                downloader.harvest_exploit_data()

            files = [name for name in os.listdir("raw_web3_data") if name.endswith(".json")]
            self.assertTrue(files, "Harvest should create at least one dataset JSON payload")

            with open(os.path.join("raw_web3_data", files[0]), "r") as handle:
                payload = json.load(handle)
            self.assertEqual(payload["incident"], "2024-01")
            self.assertIn("contract Exploit", payload["poc_code"])
            self.assertIn("Incident summary", payload["analysis"])

            self.assertTrue(os.path.exists(os.path.join("raw_web3_data", "sol", "2024-01", "Exploit.sol")))
            with open(os.path.join("raw_web3_data", "sol", "2024-01", "Exploit.sol"), "r") as handle:
                self.assertIn("contract Exploit", handle.read())


if __name__ == "__main__":
    unittest.main()
