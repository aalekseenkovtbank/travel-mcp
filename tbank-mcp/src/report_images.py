"""Bounded image conversion for MCP output and in-memory travel reports.

Travel tools keep returning source HTTPS URLs.  The public conversion tool and
the report path can additionally embed those bytes as data URIs so chat and
sandboxed artifact previews do not need outbound network access.  Fetching is
deliberately limited to the known image CDNs used by T-Bank Hotels, T-Bank
Afisha and Yandex Maps and never changes the public page document.
"""
from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
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
_MAX_PUBLIC_BATCH_IMAGES = 16
_MAX_PARALLEL_DOWNLOADS = 6
_MAX_IMAGE_PIXELS = 30_000_000
_MAX_IMAGE_EDGE = 1280
_CONNECT_TIMEOUT_SECONDS = 3
_READ_TIMEOUT_SECONDS = 6


class ImageConversionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConvertedImage:
    source_url: str
    mime_type: str
    payload: bytes

    @property
    def base64_data(self) -> str:
        return base64.b64encode(self.payload).decode("ascii")

    @property
    def data_uri(self) -> str:
        return f"data:{self.mime_type};base64,{self.base64_data}"

    def public_dict(self) -> dict[str, str | int]:
        return {
            "sourceUrl": self.source_url,
            "mimeType": self.mime_type,
            "byteLength": len(self.payload),
            "dataUri": self.data_uri,
        }


@dataclass(frozen=True)
class FailedImageConversion:
    source_url: str
    error: str

    def public_dict(self) -> dict[str, str | bool]:
        return {
            "sourceUrl": self.source_url,
            "ok": False,
            "error": self.error,
        }


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
                raise ImageConversionError("image pixel limit exceeded")
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
        raise ImageConversionError("image resize failed") from exc
    raise ImageConversionError("image exceeds byte limit after resize")


def _download_image(session: requests.Session, url: str, byte_limit: int) -> tuple[str, bytes]:
    trusted_url = _trusted_image_url(url)
    if not trusted_url:
        raise ImageConversionError("untrusted image host")
    limit = min(_MAX_EMBEDDED_IMAGE_BYTES, byte_limit)
    if limit <= 0:
        raise ImageConversionError("report image budget exhausted")

    try:
        with session.get(
            trusted_url,
            allow_redirects=False,
            stream=True,
            timeout=(_CONNECT_TIMEOUT_SECONDS, _READ_TIMEOUT_SECONDS),
        ) as response:
            if response.status_code != 200:
                raise ImageConversionError(f"unexpected HTTP {response.status_code}")
            raw_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            content_type = _SUPPORTED_IMAGE_TYPES.get(raw_type)
            if not content_type:
                raise ImageConversionError("unsupported content type")
            try:
                content_length = int(response.headers.get("Content-Length", "0") or 0)
            except ValueError:
                content_length = 0
            if content_length > _MAX_SOURCE_IMAGE_BYTES:
                raise ImageConversionError("source image exceeds byte limit")

            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=32 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > _MAX_SOURCE_IMAGE_BYTES:
                    raise ImageConversionError("source image exceeds byte limit")
                chunks.append(chunk)
    except requests.RequestException as exc:
        raise ImageConversionError("image request failed") from exc

    payload = b"".join(chunks)
    if not payload or not _matches_image_signature(content_type, payload):
        raise ImageConversionError("invalid image payload")
    return _compact_image(content_type, payload, limit)


def convert_image_url(
    url: str,
    *,
    session: requests.Session | None = None,
    byte_limit: int = _MAX_EMBEDDED_IMAGE_BYTES,
) -> ConvertedImage:
    """Fetch one trusted travel image and return bounded base64-ready bytes."""
    source_url = _trusted_image_url(url)
    if not source_url:
        raise ImageConversionError("untrusted image host")
    own_session = session is None
    requester = session or requests.Session()
    if own_session:
        requester.headers.update({
            "Accept": "image/webp,image/png,image/jpeg,image/gif;q=0.8,*/*;q=0.1",
            "User-Agent": "Travel-Nova-Image/1.0",
        })
    try:
        content_type, payload = _download_image(
            requester, source_url, min(byte_limit, _MAX_EMBEDDED_IMAGE_BYTES))
    finally:
        if own_session:
            requester.close()
    return ConvertedImage(source_url, content_type, payload)


def convert_image_urls(
    urls: list[str],
    *,
    total_byte_limit: int = _MAX_REPORT_IMAGE_BYTES,
    max_images: int | None = None,
) -> list[ConvertedImage | FailedImageConversion]:
    """Convert unique image URLs concurrently and preserve their input order."""
    unique_urls: list[str] = []
    for value in urls:
        url = str(value or "").strip()
        if url and url not in unique_urls:
            unique_urls.append(url)
    if not unique_urls:
        raise ImageConversionError("at least one image URL is required")
    if max_images is not None and len(unique_urls) > max_images:
        raise ImageConversionError(
            f"too many image URLs: maximum is {max_images}")
    if total_byte_limit <= 0:
        raise ImageConversionError("image batch budget exhausted")

    per_image_limit = min(
        _MAX_EMBEDDED_IMAGE_BYTES,
        max(1, total_byte_limit // len(unique_urls)),
    )
    converted: dict[str, ConvertedImage | FailedImageConversion] = {}
    workers = min(_MAX_PARALLEL_DOWNLOADS, len(unique_urls))
    with ThreadPoolExecutor(
        max_workers=workers,
        thread_name_prefix="travel-image",
    ) as executor:
        pending = {
            executor.submit(
                convert_image_url, url, byte_limit=per_image_limit,
            ): url
            for url in unique_urls
        }
        for future in as_completed(pending):
            url = pending[future]
            try:
                converted[url] = future.result()
            except ImageConversionError as exc:
                converted[url] = FailedImageConversion(url, str(exc))
            except Exception:
                converted[url] = FailedImageConversion(
                    url, "unexpected image conversion failure")
    return [converted[url] for url in unique_urls]


def convert_public_image_urls(urls: list[str]) -> dict[str, object]:
    """Return the bounded public batch response used by the MCP tool."""
    requested_count = len(urls)
    results = convert_image_urls(
        urls,
        total_byte_limit=_MAX_REPORT_IMAGE_BYTES,
        max_images=_MAX_PUBLIC_BATCH_IMAGES,
    )
    items: list[dict[str, object]] = []
    converted_count = 0
    for result in results:
        if isinstance(result, ConvertedImage):
            item: dict[str, object] = {"ok": True, **result.public_dict()}
            converted_count += 1
        else:
            item = result.public_dict()
        items.append(item)
    return {
        "requestedCount": requested_count,
        "uniqueCount": len(results),
        "convertedCount": converted_count,
        "failedCount": len(results) - converted_count,
        "images": items,
    }


def inline_report_images(
    hotels, events=(), venues=(),
) -> tuple[dict[str, str], list[str]]:
    """Return source-URL to data-URI overrides and fail-soft report warnings."""
    overrides: dict[str, str] = {}
    warnings: list[str] = []
    groups = (
        ("отеля", hotels, _hotel_photo_urls),
        ("события", events, _event_photo_urls),
        ("заведения", venues, _venue_photo_urls),
    )
    entities_with_urls: list[tuple[str, object, list[str]]] = []
    all_urls: list[str] = []
    for entity_kind, entities, url_getter in groups:
        for entity in entities:
            urls = url_getter(entity)
            if urls:
                entities_with_urls.append((entity_kind, entity, urls))
                all_urls.extend(urls)
    if not all_urls:
        return overrides, warnings

    for result in convert_image_urls(
        all_urls, total_byte_limit=_MAX_REPORT_IMAGE_BYTES,
    ):
        if isinstance(result, ConvertedImage):
            overrides[result.source_url] = result.data_uri
        else:
            # Fail closed for rendered HTML: the source URL remains in
            # documentJson, but never becomes a network-dependent <img src>.
            overrides[result.source_url] = ""

    for entity_kind, entity, urls in entities_with_urls:
        embedded = sum(bool(overrides.get(url)) for url in urls)
        if embedded < len(urls):
            name = str(
                getattr(entity, "name", "")
                or getattr(entity, "id", entity_kind)
            )
            warnings.append(
                f"Фото {entity_kind} «{name}»: встроено {embedded} "
                f"из {len(urls)}; остальные не включены в HTML."
            )
    return overrides, warnings


def inline_report_hotel_images(hotels) -> tuple[dict[str, str], list[str]]:
    """Backward-compatible hotel-only wrapper for local callers."""
    return inline_report_images(hotels)
