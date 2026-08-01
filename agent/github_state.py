import base64
import json
from typing import Optional

import requests

from agent.config import CONFIG
from agent.logger import LOGGER

API_ROOT = "https://api.github.com"
STATE_PATH_IN_REPO = "state/state.json"


class GitHubStateManager:
    def __init__(self):
        self.repo = CONFIG.GITHUB_REPO
        self.branch = CONFIG.GITHUB_BRANCH
        self.token = CONFIG.GITHUB_TOKEN

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }

    def _contents_url(self) -> str:
        return f"{API_ROOT}/repos/{self.repo}/contents/{STATE_PATH_IN_REPO}"

    def push(self, state: dict) -> bool:
        if not (self.repo and self.token):
            LOGGER.warning("GitHub not configured; skipping push")
            return False

        sha = None
        try:
            resp = requests.get(
                self._contents_url(), headers=self._headers(), params={"ref": self.branch}, timeout=15
            )
            if resp.status_code == 200:
                sha = resp.json().get("sha")
        except requests.RequestException as e:
            LOGGER.warning(f"GitHub GET failed: {e}")

        balance = state.get("bank_balance", 0.0)
        iteration = state.get("iteration_count", 0)
        status_emoji = "\U0001F7E2" if state.get("alive") else "\U0001F480"
        message = f"state: ${balance:.2f} | iter {iteration} | {status_emoji}"

        content_b64 = base64.b64encode(json.dumps(state, indent=2).encode()).decode()
        payload = {"message": message, "content": content_b64, "branch": self.branch}
        if sha:
            payload["sha"] = sha

        try:
            resp = requests.put(self._contents_url(), headers=self._headers(), json=payload, timeout=15)
            if resp.status_code in (200, 201):
                LOGGER.info(f"State pushed to GitHub ({message})")
                return True
            LOGGER.error(f"GitHub push failed: {resp.status_code} {resp.text}")
            return False
        except requests.RequestException as e:
            LOGGER.error(f"GitHub PUT failed: {e}")
            return False

    def pull(self) -> Optional[dict]:
        if not (self.repo and self.token):
            return None
        try:
            resp = requests.get(
                self._contents_url(), headers=self._headers(), params={"ref": self.branch}, timeout=15
            )
            if resp.status_code != 200:
                return None
            content = resp.json().get("content", "")
            decoded = base64.b64decode(content).decode()
            return json.loads(decoded)
        except (requests.RequestException, ValueError) as e:
            LOGGER.warning(f"GitHub pull failed: {e}")
            return None

    def get_raw_url(self) -> str:
        return f"https://raw.githubusercontent.com/{self.repo}/{self.branch}/{STATE_PATH_IN_REPO}"


GITHUB = GitHubStateManager()
