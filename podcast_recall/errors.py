"""Typed errors. They are raised only when nothing could be done; otherwise a partial result
is returned (see specs/features/u1-youtube-connector/requirements.md)."""

from __future__ import annotations


class PodcastRecallError(Exception):
    """Base class for all expected errors."""


class NotSignedIn(PodcastRecallError):
    """No usable sign-in: never signed in, revoked, or the token expired."""


class QuotaExceeded(PodcastRecallError):
    """YouTube's daily quota ran out."""


class ApiError(PodcastRecallError):
    """YouTube (or the network) failed in a way that is not a sign-in or quota problem."""


class ConfigError(PodcastRecallError):
    """Something is set up wrong: missing client secret, bad user name, Keychain locked, and so on."""


class SyncAlreadyRunning(PodcastRecallError):
    """Another sync for this user is already running."""


class TransientError(PodcastRecallError):
    """A retryable failure (network error, HTTP 5xx or 429). Never escapes the client."""
