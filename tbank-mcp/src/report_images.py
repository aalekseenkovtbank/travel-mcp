"""Bounded server-side image embedding for in-memory travel reports.

Hotel tools keep returning source HTTPS URLs.  The report path may additionally
embed those bytes into its HTML so sandboxed artifact previews do not need
outbound network access.  Fetching is deliberately limited to the T-Bank image
proxy and never changes the public page document.
"""
from __future__ import annotations

import base64
from urllib.parse import urlparse

import requests


_TRUSTED_IMAGE_HOSTS = frozenset({"cdn.tbank.ru"})
_SUPPORTED_IMAGE_TYPES = {
    "image/gif": "image/gif",
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/webp": "image/webp",
}
_MAX_IMAGES_PER_HOTEL = 3
_MAX_IMAGE_BYTES = 512 * 1024
_MAX_REPORT_IMAGE_BYTES = 2_500_000
_CONNECT_TIMEOUT_SECONDS = 3
_READ_TIMEOUT_SECONDS = 6


class _ImageEmbeddingError(RuntimeError):
    pass


def _trusted_image_url(value) -> str:
    url = str(value or "").strip()
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError:
        return ""
    if (parsed.scheme.lower() != "https" or not parsed.hostname
            or parsed.hostname.lower() not in _TRUSTED_IMAGE_HOSTS
            or parsed.username is not None or parsed.password is not None
            or port not in (None, 443)):
        return ""
    return url


def _hotel_photo_urls(hotel) -> list[str]:
    urls: list[str] = []
    for photo in list(getattr(hotel, "photos", []) or []):
        url = str(getattr(photo, "url", "") or "").strip()
        if url and url not in urls:
            urls.append(url)
    fallback = str(getattr(hotel, "image_url", "") or "").strip()
    if fallback and fallback not in urls:
        urls.append(fallback)
    return urls[:_MAX_IMAGES_PER_HOTEL]


def _matches_image_signature(content_type: str, payload: bytes) -> bool:
    if content_type == "image/jpeg":
        return payload.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return payload.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/gif":
        return payload.startswith((b"GIF87a", b"GIF89a"))
    if content_type == "image/webp":
        return (len(payload) >= 12 and payload.startswith(b"RIFF")
                and payload[8:12] == b"WEBP")
    return False


def _download_image(session: requests.Session, url: str, byte_limit: int) -> tuple[str, bytes]:
    trusted_url = _trusted_image_url(url)
    if not trusted_url:
        raise _ImageEmbeddingError("untrusted image host")
    limit = min(_MAX_IMAGE_BYTES, byte_limit)
    if limit <= 0:
        raise _ImageEmbeddingError("report image budget exhausted")

    try:
        with session.get(
            trusted_url,
            allow_redirects=False,
            stream=True,
            timeout=(_CONNECT_TIMEOUT_SECONDS, _READ_TIMEOUT_SECONDS),
        ) as response:
            if response.status_code != 200:
                raise _ImageEmbeddingError(f"unexpected HTTP {response.status_code}")
            raw_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            content_type = _SUPPORTED_IMAGE_TYPES.get(raw_type)
            if not content_type:
                raise _ImageEmbeddingError("unsupported content type")
            try:
                content_length = int(response.headers.get("Content-Length", "0") or 0)
            except ValueError:
                content_length = 0
            if content_length > limit:
                raise _ImageEmbeddingError("image exceeds byte limit")

            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=32 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > limit:
                    raise _ImageEmbeddingError("image exceeds byte limit")
                chunks.append(chunk)
    except requests.RequestException as exc:
        raise _ImageEmbeddingError("image request failed") from exc

    payload = b"".join(chunks)
    if not payload or not _matches_image_signature(content_type, payload):
        raise _ImageEmbeddingError("invalid image payload")
    return content_type, payload


def inline_report_hotel_images(hotels) -> tuple[dict[str, str], list[str]]:
    """Return source-URL to data-URI overrides and fail-soft report warnings."""
    overrides: dict[str, str] = {}
    warnings: list[str] = []
    total_bytes = 0
    session = requests.Session()
    session.headers.update({
        "Accept": "image/webp,image/png,image/jpeg,image/gif;q=0.8,*/*;q=0.1",
        "User-Agent": "Travel-Nova-Report/1.0",
    })
    try:
        for hotel in hotels:
            urls = _hotel_photo_urls(hotel)
            if not urls:
                continue
            embedded = 0
            failed = 0
            for url in urls:
                if url in overrides:
                    embedded += 1
                    continue
                try:
                    content_type, payload = _download_image(
                        session, url, _MAX_REPORT_IMAGE_BYTES - total_bytes)
                except _ImageEmbeddingError:
                    failed += 1
                    continue
                total_bytes += len(payload)
                encoded = base64.b64encode(payload).decode("ascii")
                overrides[url] = f"data:{content_type};base64,{encoded}"
                embedded += 1
            if failed:
                name = str(getattr(hotel, "name", "") or getattr(hotel, "id", "отель"))
                warnings.append(
                    f"Фото отеля «{name}»: встроено {embedded} из {len(urls)}; "
                    "остальные оставлены внешними HTTPS-ссылками."
                )
    finally:
        session.close()
    return overrides, warnings
