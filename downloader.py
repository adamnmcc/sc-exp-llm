import json
import os

import requests

# Configure target repository (DeFiHackLabs tracks hundreds of real protocol exploits)
REPO_OWNER = "SunWeb3Sec"
REPO_NAME = "DeFiHackLabs"
TARGET_DIRS = ("src/test", "src")
DEFAULT_BRANCH = "main"
GITHUB_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "sc-exp-llm-downloader/1.0",
}


def fetch_repo_files(path=""):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    try:
        response = requests.get(url, headers=GITHUB_HEADERS, timeout=30)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []
    except requests.RequestException as exc:
        print("Failed to fetch directory: {} ({})".format(path, exc))
        return []


def fetch_repo_tree_fallback(start_path=""):
    url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/tree/{DEFAULT_BRANCH}/{start_path}".rstrip("/") if start_path else f"https://github.com/{REPO_OWNER}/{REPO_NAME}"
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if response.status_code != 200:
            return []
    except requests.RequestException as exc:
        print("Failed to fetch repository HTML: {}".format(exc))
        return []

    try:
        import re
        pattern = re.compile(r"/SunWeb3Sec/DeFiHackLabs/(tree|blob)/main/([^\"?#]+)")
        matches = pattern.findall(response.text)
    except Exception:
        return []

    result = []
    seen = set()
    for kind, path in matches:
        if not path:
            continue
        normalized = path.strip().rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append({"path": normalized, "type": "tree" if kind == "tree" else "blob"})
    return result


def fetch_repo_tree():
    for branch in (DEFAULT_BRANCH, "master"):
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{branch}?recursive=1"
        try:
            response = requests.get(url, headers=GITHUB_HEADERS, timeout=30)
            if response.status_code == 404:
                continue
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict) and isinstance(payload.get("tree"), list):
                return payload["tree"]
        except requests.RequestException as exc:
            print("Failed to fetch repository tree for {}: {}".format(branch, exc))

    fallback_paths = ["src/test", "src"]
    for candidate in fallback_paths:
        fallback_tree = fetch_repo_tree_fallback(candidate)
        if fallback_tree:
            return fallback_tree
    return fetch_repo_tree_fallback()


def download_file_content(download_url):
    if not download_url:
        return ""

    try:
        response = requests.get(download_url, timeout=30)
        if response.status_code == 200:
            return response.text
    except requests.RequestException as exc:
        print("Failed to fetch file: {} ({})".format(download_url, exc))

    return ""


def infer_target_dir(repo_tree):
    if not repo_tree:
        return ""

    for candidate in TARGET_DIRS:
        if any(item.get("path") == candidate or item.get("path", "").startswith(f"{candidate}/") for item in repo_tree):
            return candidate
    return ""


def build_incident_map(repo_tree):
    incidents = {}
    for entry in repo_tree:
        path = entry.get("path", "")
        if entry.get("type") != "blob" or not path:
            continue

        target_dir = None
        for candidate in TARGET_DIRS:
            if path == candidate or path.startswith(f"{candidate}/"):
                target_dir = candidate
                break
        if target_dir is None:
            continue

        relative_path = path[len(target_dir) + 1 :] if path != target_dir else ""
        if not relative_path:
            continue

        incident = relative_path.split("/")[0]
        bucket = incidents.setdefault(
            incident,
            {
                "incident": incident,
                "repo_path": f"{target_dir}/{incident}",
                "analysis_files": [],
                "exploit_files": [],
            },
        )

        lower_name = os.path.basename(path).lower()
        if lower_name.endswith(".sol"):
            bucket["exploit_files"].append(path)
        elif lower_name.endswith((".md", ".txt", ".rst")):
            bucket["analysis_files"].append(path)

    return incidents


def select_analysis_text(analysis_files):
    if not analysis_files:
        return "Incident analysis unavailable; Solidity PoC is provided directly."

    candidates = sorted(analysis_files)
    preferred = [
        path for path in candidates
        if os.path.basename(path).lower() in {"readme.md", "exploit.md", "writeup.md", "analysis.md"}
        or "readme" in os.path.basename(path).lower()
        or "exploit" in os.path.basename(path).lower()
    ]
    chosen = preferred[0] if preferred else candidates[0]
    raw_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{chosen}"
    text = download_file_content(raw_url)
    return text.strip() if text.strip() else "Incident analysis unavailable; Solidity PoC is provided directly."


def combine_exploit_sources(exploit_files):
    if not exploit_files:
        return ""

    chunks = []
    for file_path in sorted(exploit_files):
        raw_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{file_path}"
        content = download_file_content(raw_url)
        if content.strip():
            chunks.append(f"// Source: {file_path}\n{content.strip()}\n")
    return "\n\n".join(chunks)


def write_raw_sol_files(incident_name, exploit_files, output_dir="./raw_web3_data"):
    sol_root = os.path.join(output_dir, "sol", incident_name)
    os.makedirs(sol_root, exist_ok=True)

    written = []
    for file_path in sorted(exploit_files):
        raw_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{file_path}"
        content = download_file_content(raw_url)
        if not content.strip():
            continue

        local_name = os.path.basename(file_path)
        local_path = os.path.join(sol_root, local_name)
        with open(local_path, "w") as handle:
            handle.write(content)
        written.append(local_path)

    return written


def harvest_exploit_data():
    print("Connecting to DeFiHackLabs repository...")
    repo_tree = fetch_repo_tree()
    if not repo_tree:
        print("Unable to fetch repository tree; scraping aborted.")
        return 0

    target_dir = infer_target_dir(repo_tree)
    if not target_dir:
        print("No supported exploit directory was found in the repository tree.")
        return 0

    incidents = build_incident_map(repo_tree)
    if not incidents:
        print("No exploit incidents were discovered under the expected directory tree.")
        return 0

    os.makedirs("./raw_web3_data", exist_ok=True)
    count = 0

    for incident_name in sorted(incidents):
        incident = incidents[incident_name]
        exploit_files = incident["exploit_files"]
        if not exploit_files:
            continue

        analysis_text = select_analysis_text(incident["analysis_files"])
        exploit_code = combine_exploit_sources(exploit_files)
        written_sol_files = write_raw_sol_files(incident_name, exploit_files)
        payload = {
            "incident": incident["incident"],
            "source_path": incident["repo_path"],
            "analysis": analysis_text,
            "poc_code": exploit_code,
            "analysis_files": sorted(incident["analysis_files"]),
            "exploit_files": sorted(exploit_files),
            "raw_sol_files": [os.path.relpath(path, "./raw_web3_data") for path in written_sol_files],
            "repo_owner": REPO_OWNER,
            "repo_name": REPO_NAME,
        }

        with open(f"./raw_web3_data/{incident_name}.json", "w") as f:
            json.dump(payload, f, indent=2)
        count += 1

    print(f"Successfully harvested {count} historical vulnerability profiles!")
    return count


if __name__ == "__main__":
    harvest_exploit_data()
