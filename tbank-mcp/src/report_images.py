"""Bounded server-side image embedding for in-memory travel reports.

Travel tools keep returning source HTTPS URLs.  The report path may additionally
embed those bytes into its HTML so sandboxed artifact previews do not need
outbound network access.  Fetching is deliberately limited to the known image
CDNs used by T-Bank Hotels, T-Bank Afisha and Yandex Maps and never changes the
public page document.
"""
from __future__ import annotations

import base64
from io import BytesIO
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps, UnidentifiedImageError


_TRUSTED_IMAGE_HOSTS = frozenset({
    "cdn.tbank.ru",
    "avatars.mds.yandex.net",
    "cdn.kassir.ru",
    "kassa.rambler.ru",
    "media.ticketland.ru",
    "ticketscloud-prod.storage.yandexcloud.net",
})
_SUPPORTED_IMAGE_TYPES = {
    "image/gif": "image/gif",
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/webp": "image/webp",
}
_MAX_IMAGES_PER_HOTEL = 3
_MAX_IMAGES_PER_EVENT = 1
_MAX_IMAGES_PER_VENUE = 1
_MAX_SOURCE_IMAGE_BYTES = 5 * 1024 * 1024
_MAX_EMBEDDED_IMAGE_BYTES = 512 * 1024
_MAX_REPORT_IMAGE_BYTES = 5_000_000
_MAX_IMAGE_PIXELS = 30_000_000
_MAX_IMAGE_EDGE = 1280
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


def _event_photo_urls(event) -> list[str]:
    url = str(getattr(event, "image_url", "") or "").strip()
    return [url] if url else []


def _venue_photo_urls(venue) -> list[str]:
    urls: list[str] = []
    for photo in list(getattr(venue, "photos", []) or []):
        url = str(getattr(photo, "url", "") or "").strip()
        if url and url not in urls:
            urls.append(url)
    return urls[:_MAX_IMAGES_PER_VENUE]


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


def _compact_image(
    content_type: str, payload: bytes, byte_limit: int,
) -> tuple[str, bytes]:
    if len(payload) <= byte_limit:
        return content_type, payload
    try:
        with Image.open(BytesIO(payload)) as source:
            if source.width * source.height > _MAX_IMAGE_PIXELS:
                raise _ImageEmbeddingError("image pixel limit exceeded")
            source.seek(0)
            image = ImageOps.exif_transpose(source)
            image.thumbnail((_MAX_IMAGE_EDGE, _MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
            if image.mode not in ("RGB", "L"):
                background = Image.new("RGB", image.size, "white")
                if "A" in image.getbands():
                    background.paste(image, mask=image.getchannel("A"))
                else:
                    background.paste(image.convert("RGB"))
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")
            for quality in (82, 74, 66, 58, 50):
                output = BytesIO()
                image.save(
                    output, format="JPEG", quality=quality,
                    optimize=True, progressive=True,
                )
                compacted = output.getvalue()
                if len(compacted) <= byte_limit:
                    return "image/jpeg", compacted
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise _ImageEmbeddingError("image resize failed") from exc
    raise _ImageEmbeddingError("image exceeds byte limit after resize")


def _download_image(session: requests.Session, url: str, byte_limit: int) -> tuple[str, bytes]:
    trusted_url = _trusted_image_url(url)
    if not trusted_url:
        raise _ImageEmbeddingError("untrusted image host")
    limit = min(_MAX_EMBEDDED_IMAGE_BYTES, byte_limit)
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
            if content_length > _MAX_SOURCE_IMAGE_BYTES:
                raise _ImageEmbeddingError("source image exceeds byte limit")

            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=32 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > _MAX_SOURCE_IMAGE_BYTES:
                    raise _ImageEmbeddingError("source image exceeds byte limit")
                chunks.append(chunk)
    except requests.RequestException as exc:
        raise _ImageEmbeddingError("image request failed") from exc

    payload = b"".join(chunks)
    if not payload or not _matches_image_signature(content_type, payload):
        raise _ImageEmbeddingError("invalid image payload")
    return _compact_image(content_type, payload, limit)


def inline_report_images(
    hotels, events=(), venues=(),
) -> tuple[dict[str, str], list[str]]:
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
        groups = (
            ("отеля", hotels, _hotel_photo_urls),
            ("события", events, _event_photo_urls),
            ("заведения", venues, _venue_photo_urls),
        )
        for entity_kind, entities, url_getter in groups:
            for entity in entities:
                urls = url_getter(entity)
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
                    name = str(
                        getattr(entity, "name", "")
                        or getattr(entity, "id", entity_kind)
                    )
                    warnings.append(
                        f"Фото {entity_kind} «{name}»: встроено {embedded} "
                        f"из {len(urls)}; "
                        "остальные оставлены внешними HTTPS-ссылками."
                    )
    finally:
        session.close()
    return overrides, warnings


def inline_report_hotel_images(hotels) -> tuple[dict[str, str], list[str]]:
    """Backward-compatible hotel-only wrapper for local callers."""
    return inline_report_images(hotels)
