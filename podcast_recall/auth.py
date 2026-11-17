"""Google sign-in helpers: token storage, scope checks, the browser flow and token revocation.

Google libraries and `keyring` are imported only inside the functions that need them, so the
rest of the app (and the tests) work without them.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from podcast_recall import paths
from podcast_recall.errors import ConfigError
from podcast_recall.youtube_client import SCOPE

KEYCHAIN_SERVICE = "podcast-recall"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
_USER_ID = re.compile(r"^[a-z0-9_-]{1,32}$")


def validate_user_id(user_id: str) -> str:
    if not isinstance(user_id, str) or not _USER_ID.match(user_id):
        raise ConfigError(
            f"Invalid user name {user_id!r}. Use 1-32 characters from a-z, 0-9, '_' and '-'."
        )
    return user_id


class TokenStore(ABC):
    """Where a user's Google credentials are kept. The Keychain is the real store. A web sign-in
    for testers (Week 6) can supply another implementation without changing sync."""

    @abstractmethod
    def get(self, user_id: str) -> str | None: ...

    @abstractmethod
    def save(self, user_id: str, credentials_json: str) -> None: ...

    @abstractmethod
    def delete(self, user_id: str) -> None: ...


class InMemoryTokenStore(TokenStore):
    """For tests."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, user_id: str) -> str | None:
        return self._data.get(user_id)

    def save(self, user_id: str, credentials_json: str) -> None:
        self._data[user_id] = credentials_json

    def delete(self, user_id: str) -> None:
        self._data.pop(user_id, None)


class KeychainTokenStore(TokenStore):
    """macOS Keychain via `keyring`: service `podcast-recall`, account `youtube:<user_id>`."""

    def _keyring(self):
        try:
            import keyring
        except ImportError as exc:
            raise ConfigError("The 'keyring' package is not installed. Run `uv sync`.") from exc
        return keyring

    @staticmethod
    def _account(user_id: str) -> str:
        return f"youtube:{validate_user_id(user_id)}"

    def get(self, user_id: str) -> str | None:
        kr = self._keyring()
        try:
            return kr.get_password(KEYCHAIN_SERVICE, self._account(user_id))
        except Exception as exc:
            raise ConfigError(
                "Could not read the macOS Keychain (locked or access denied). "
                "Unlock it and try again."
            ) from exc

    def save(self, user_id: str, credentials_json: str) -> None:
        kr = self._keyring()
        try:
            kr.set_password(KEYCHAIN_SERVICE, self._account(user_id), credentials_json)
        except Exception as exc:
            raise ConfigError(
                "Could not write to the macOS Keychain (locked or access denied)."
            ) from exc

    def delete(self, user_id: str) -> None:
        kr = self._keyring()
        try:
            kr.delete_password(KEYCHAIN_SERVICE, self._account(user_id))
        except Exception as exc:
            if type(exc).__name__ == "PasswordDeleteError":
                return  # nothing stored: fine
            raise ConfigError("Could not delete the Keychain entry (locked or access denied).") from exc


@dataclass
class FlowResult:
    credentials_json: str
    granted_scopes: set[str]
    has_refresh_token: bool


def verify_flow_result(result: FlowResult) -> None:
    """Refuse a sign-in that has no refresh token or that granted anything but read-only access."""
    if not result.has_refresh_token:
        raise ConfigError(
            "Google did not return a refresh token, so sign-in cannot be kept. "
            "Remove the app at https://myaccount.google.com/connections and sign in again."
        )
    if result.granted_scopes != {SCOPE}:
        raise ConfigError(
            "Google granted a different permission than the read-only YouTube access this app "
            f"asks for ({sorted(result.granted_scopes)}). Sign-in refused and nothing was saved."
        )


def run_installed_flow(client_secret: Path | None = None) -> FlowResult:
    """Open the browser for Google sign-in (Desktop-app flow). Always asks for offline access and
    consent so Google returns a refresh token every time."""
    path = Path(client_secret) if client_secret else paths.client_secret_path()
    if not path.is_file():
        raise ConfigError(
            f"Google client file not found at {path}. Download it from Google Cloud "
            "(OAuth client of type 'Desktop app') or set CLIENT_SECRET_PATH."
        )
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise ConfigError("Google libraries are not installed. Run `uv sync`.") from exc
    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(path), scopes=[SCOPE])
        creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    except Exception as exc:
        raise ConfigError(
            f"Google sign-in did not complete ({type(exc).__name__}). "
            "If you approved a different permission than 'View your YouTube account', try again."
        ) from exc
    # The scope Google actually granted is in the token response. `creds.scopes` may only echo
    # what was requested, so prefer the token response and fall back to it.
    token = getattr(getattr(flow, "oauth2session", None), "token", None) or {}
    scope = token.get("scope")
    if isinstance(scope, str):
        scope = scope.split()
    return FlowResult(
        credentials_json=creds.to_json(),
        granted_scopes=set(scope or creds.scopes or []),
        has_refresh_token=bool(creds.refresh_token),
    )


def _default_post(url: str, params: dict[str, str]) -> int:
    data = urllib.parse.urlencode(params).encode()
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def revoke_at_google(
    credentials_json: str, http_post: Callable[[str, dict[str, str]], int] = _default_post
) -> bool:
    """Tell Google to revoke the grant. Returns True on success, False if it could not be done
    (offline, unreadable credentials). Never logs the token."""
    try:
        info = json.loads(credentials_json)
        token = info.get("refresh_token") or info.get("token")
        if not token:
            return False
        return http_post(REVOKE_URL, {"token": token}) == 200
    except (AttributeError, OSError, ValueError):
        return False
