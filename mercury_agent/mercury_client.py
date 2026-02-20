"""Thin wrapper around the Mercury Playground HTTP API."""

from __future__ import annotations

import requests


class MercuryClient:
    def __init__(self, base_url: str = "http://localhost:8080", timeout: float = 10) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def send_code(self, code: str) -> dict:
        resp = requests.post(
            f"{self._base}/api/code",
            json={"code": code},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def silence(self) -> dict:
        resp = requests.post(
            f"{self._base}/api/silence",
            json={},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def get_current_code(self) -> str:
        """Fetch the last code that Mercury is playing (from API or browser editor)."""
        try:
            resp = requests.get(f"{self._base}/api/code", timeout=self._timeout)
            resp.raise_for_status()
            return resp.json().get("code", "")
        except requests.RequestException:
            return ""

    def health_check(self) -> bool:
        try:
            resp = requests.get(self._base, timeout=self._timeout)
            return resp.status_code == 200
        except requests.RequestException:
            return False
