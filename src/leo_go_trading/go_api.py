from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

from .models import TradeSignal


DEFAULT_GW_BASE = "https://gandalf.gammawizard.com"


def sanitize_token(token: str | None) -> str:
    value = (token or "").strip().strip('"').strip("'")
    if value.lower().startswith("bearer "):
        return value.split(None, 1)[1]
    return value


def normalize_endpoint(endpoint: str) -> str:
    value = (endpoint or "").strip()
    if value.startswith("/"):
        value = value[1:]
    if not value.lower().startswith("rapi/"):
        value = f"rapi/{value}"
    return value


@dataclass
class GammaWizardClient:
    base_url: str = DEFAULT_GW_BASE
    token: str = ""
    email: str = ""
    password: str = ""
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "GammaWizardClient":
        return cls(
            base_url=os.environ.get("GW_BASE", DEFAULT_GW_BASE),
            token=os.environ.get("GW_TOKEN", ""),
            email=os.environ.get("GW_EMAIL", ""),
            password=os.environ.get("GW_PASSWORD", ""),
            timeout=int(os.environ.get("GW_TIMEOUT", "30")),
        )

    def authenticate(self) -> str:
        if not (self.email and self.password):
            raise RuntimeError("Set GW_TOKEN, or set both GW_EMAIL and GW_PASSWORD.")
        response = requests.post(
            f"{self.base_url.rstrip('/')}/goauth/authenticateFireUser",
            data={"email": self.email, "password": self.password},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json() or {}
        token = sanitize_token(payload.get("token") or payload.get("Token") or "")
        if not token:
            raise RuntimeError("GO API authentication succeeded but no token was returned.")
        self.token = token
        return token

    def get_json(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        path = normalize_endpoint(endpoint)

        def hit(token: str | None) -> requests.Response:
            headers = {"Accept": "application/json"}
            if token:
                headers["Authorization"] = f"Bearer {sanitize_token(token)}"
            return requests.get(
                f"{self.base_url.rstrip('/')}/{path}",
                headers=headers,
                params=params or {},
                timeout=self.timeout,
            )

        token = sanitize_token(self.token)
        response = hit(token if token else None)
        if response.status_code in (401, 403):
            token = self.authenticate()
            response = hit(token)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return {"raw": response.text}

    def fetch_signal(self, endpoint: str) -> TradeSignal:
        payload = self.get_json(endpoint)
        return TradeSignal.from_payload(payload, endpoint=normalize_endpoint(endpoint))
