"""Safe downloads, used for every audio file and transcript file U3 fetches.

A feed is written by someone else, so its links are not trusted. Every URL is checked before it
is opened and again at every redirect: only http and https, no user name or password in the
link, and the host must resolve only to public internet addresses. A link that points to this
Mac or to a private network (for example `http://127.0.0.1:11434`, where Ollama listens) is
refused. Sizes and times are capped, and nothing downloaded is ever run.

Known limit: the host is looked up once to check it and again by the operating system when it
connects. A hostile name server could answer differently the second time. For a single-user
tool on your own Mac this risk is accepted.
"""

from __future__ import annotations

import http.client
import ipaddress
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from podcast_recall.errors import ApiError

MAX_REDIRECTS = 5
CONNECT_TIMEOUT_S = 15
CHUNK_BYTES = 64 * 1024
USER_AGENT = "podcast-recall/0.0.1"

Resolver = Callable[[str, int], list[str]]
OpenUrl = Callable[[str, float], object]


class DownloadError(ApiError):
    """A download was refused or failed. The message never contains the full URL."""


@dataclass(frozen=True)
class FetchInfo:
    content_type: str
    size: int
    host: str


# ---------------------------------------------------------------------------- the safety check


def default_resolver(host: str, port: int) -> list[str]:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return sorted({info[4][0] for info in infos})


def is_public(address: str) -> bool:
    """True only for a normal public internet address."""
    try:
        ip = ipaddress.ip_address(address.split("%")[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return bool(
        ip.is_global
        and not ip.is_multicast
        and not ip.is_reserved
        and not ip.is_unspecified
        and not ip.is_loopback
        and not ip.is_link_local
    )


def check_url(url: str, resolver: Resolver = default_resolver) -> str:
    """Raise DownloadError unless the URL is safe to open. Returns the host."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise DownloadError("only http and https links are allowed")
    if parts.username or parts.password:
        raise DownloadError("links with a user name or password are refused")
    host = parts.hostname
    if not host:
        raise DownloadError("the link has no host name")
    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError:
        raise DownloadError("the link has an invalid port") from None
    try:
        addresses = resolver(host, port)
    except OSError:
        raise DownloadError(f"could not look up {host}") from None
    if not addresses:
        raise DownloadError(f"{host} has no address")
    for address in addresses:
        if not is_public(address):
            raise DownloadError(
                f"{host} points to this computer or a private network, so the download was refused"
            )
    return host


class _GuardedRedirect(urllib.request.HTTPRedirectHandler):
    """Check every redirect target before following it, and cap the number of redirects."""

    max_redirections = MAX_REDIRECTS

    def __init__(self, resolver: Resolver) -> None:
        super().__init__()
        self._resolver = resolver
        self.hops = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.hops += 1
        if self.hops > MAX_REDIRECTS:
            raise DownloadError("too many redirects")
        absolute = urllib.parse.urljoin(req.full_url, newurl)
        check_url(absolute, self._resolver)
        return super().redirect_request(req, fp, code, msg, headers, absolute)


# ---------------------------------------------------------------------------- downloading


class SafeFetcher:
    """Download one URL to one file, within limits. Both the host look-up and the opening of the
    URL can be replaced in tests, so no test needs the network."""

    def __init__(
        self,
        *,
        resolver: Resolver = default_resolver,
        open_url: OpenUrl | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._resolver = resolver
        self._open_url = open_url or self._default_open
        self._clock = clock

    def _default_open(self, url: str, timeout: float):
        opener = urllib.request.build_opener(_GuardedRedirect(self._resolver))
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        return opener.open(request, timeout=timeout)

    def fetch_to_file(
        self,
        url: str,
        dest: Path,
        *,
        max_bytes: int,
        total_timeout_s: float,
        accept: Callable[[str], bool] | None = None,
    ) -> FetchInfo:
        """Download `url` to `dest` (through a `.part` file renamed on success)."""
        host = check_url(url, self._resolver)
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        deadline = self._clock() + total_timeout_s
        try:
            response = self._open_url(url, CONNECT_TIMEOUT_S)
        except urllib.error.HTTPError as exc:
            raise DownloadError(f"{host} answered HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
            raise DownloadError(f"could not reach {host} ({type(exc).__name__})") from exc
        try:
            with response:  # type: ignore[attr-defined]
                content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()  # type: ignore[attr-defined]
                if accept is not None and not accept(content_type):
                    raise DownloadError(f"unexpected content type {content_type or 'none'}")
                length = response.headers.get("Content-Length")  # type: ignore[attr-defined]
                if length and length.isdigit() and int(length) > max_bytes:
                    raise DownloadError(f"the file is larger than the {max_bytes // 1_000_000} MB limit")
                size = 0
                with part.open("wb") as out:
                    while True:
                        if self._clock() > deadline:
                            raise DownloadError("the download took too long")
                        chunk = response.read(CHUNK_BYTES)  # type: ignore[attr-defined]
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > max_bytes:
                            raise DownloadError(
                                f"the file is larger than the {max_bytes // 1_000_000} MB limit"
                            )
                        out.write(chunk)
        except (OSError, TimeoutError, http.client.HTTPException) as exc:
            part.unlink(missing_ok=True)
            raise DownloadError(f"the download from {host} was interrupted ({type(exc).__name__})") from exc
        except BaseException:
            part.unlink(missing_ok=True)
            raise
        if size == 0:
            part.unlink(missing_ok=True)
            raise DownloadError("the file was empty")
        os.replace(part, dest)
        return FetchInfo(content_type, size, host)
