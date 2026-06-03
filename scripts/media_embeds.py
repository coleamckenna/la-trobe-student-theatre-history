"""Classify external URLs and render inline embed HTML for wiki production pages."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse, urlunparse


MEDIA_SECTIONS = frozenset({"materials", "notes", "media"})
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")
PDF_EXTENSION = ".pdf"

LINK_ONLY_HOSTS = frozenset(
    {
        "facebook.com",
        "www.facebook.com",
        "instagram.com",
        "www.instagram.com",
        "issuu.com",
        "www.issuu.com",
        "linkedin.com",
        "www.linkedin.com",
    }
)

URL_PATTERN = re.compile(r"https?://[^\s\)<>\]\"']+", re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class EmbedSpec:
    kind: str  # image, iframe, iframe_pdf
    src: str
    title: str
    original_url: str


def transform_external_media(body: str) -> str:
    """Append embed blocks after URLs in Materials, Notes, and Media sections."""
    parts = SECTION_PATTERN.split(body)
    if len(parts) == 1:
        return body

    output: list[str] = [parts[0]]
    seen_urls: set[str] = set()

    for index in range(1, len(parts), 2):
        title = parts[index].strip()
        content = parts[index + 1] if index + 1 < len(parts) else ""
        section_key = title.casefold()

        if section_key in MEDIA_SECTIONS:
            content, seen_urls = _transform_section(content, seen_urls)

        output.append(f"## {title}")
        output.append(content)

    return "".join(output)


def _transform_section(content: str, seen_urls: set[str]) -> tuple[str, set[str]]:
    lines = content.splitlines(keepends=True)
    result: list[str] = []

    for line in lines:
        result.append(line)
        line_urls = extract_urls(line)
        for url in line_urls:
            normalized = normalize_url(url)
            if normalized in seen_urls:
                continue

            spec = classify_url(url)
            if spec is None:
                continue

            seen_urls.add(normalized)
            caption = caption_from_line(line, url)
            result.append(render_embed(spec, caption))

    return "".join(result), seen_urls


def extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    for match in URL_PATTERN.finditer(text):
        url = normalize_url(match.group(0))
        if url not in seen:
            seen.add(url)
            urls.append(url)

    return urls


def normalize_url(url: str) -> str:
    return url.rstrip(".,);]\"'")


def caption_from_line(line: str, url: str) -> str:
    stripped = line.strip()
    label_match = re.match(
        r"^[-*]?\s*(.+?)\s*:\s*" + re.escape(url) + r"\s*$",
        stripped,
        flags=re.IGNORECASE,
    )
    if label_match:
        return label_match.group(1).strip()

    link_match = re.match(r"^\[([^\]]+)\]\(" + re.escape(url) + r"\)\s*$", stripped)
    if link_match:
        return link_match.group(1).strip()

    return ""


def classify_url(url: str) -> EmbedSpec | None:
    url = normalize_url(url)
    parsed = urlparse(url)
    host = (parsed.netloc or "").casefold()
    path = parsed.path or ""
    path_lower = path.casefold()

    if not host:
        return None

    if host in LINK_ONLY_HOSTS or any(
        host.endswith("." + blocked) for blocked in LINK_ONLY_HOSTS
    ):
        return None

    if host == "images.humanitix.com":
        return EmbedSpec("image", url, "Humanitix image", url)

    if host == "events.humanitix.com":
        if "/embed" in path_lower or "w=true" in (parsed.query or "").casefold():
            return EmbedSpec("iframe", url, "Humanitix widget", url)
        return None

    if host == "web.archive.org" or host.endswith(".web.archive.org"):
        return _classify_wayback(url, path_lower)

    if host == "archive.org" or host.endswith(".archive.org"):
        return _classify_archive_org(url, parsed)

    youtube_id = _youtube_id(url, host, parsed)
    if youtube_id:
        embed = f"https://www.youtube.com/embed/{youtube_id}"
        return EmbedSpec("iframe", embed, "YouTube video", url)

    vimeo_id = _vimeo_id(host, path_lower)
    if vimeo_id:
        embed = f"https://player.vimeo.com/video/{vimeo_id}"
        return EmbedSpec("iframe", embed, "Vimeo video", url)

    if path_lower.endswith(IMAGE_EXTENSIONS):
        return EmbedSpec("image", url, "Image", url)

    if path_lower.endswith(PDF_EXTENSION):
        return EmbedSpec("iframe_pdf", url, "PDF document", url)

    return None


def _classify_archive_org(url: str, parsed) -> EmbedSpec | None:
    path = parsed.path or ""
    if path.startswith("/embed/"):
        return EmbedSpec("iframe", url, "Internet Archive", url)

    details_match = re.match(r"^/details/([^/]+)/?", path, flags=re.IGNORECASE)
    if details_match:
        identifier = details_match.group(1)
        embed = f"https://archive.org/embed/{identifier}"
        return EmbedSpec("iframe", embed, "Internet Archive", url)

    return None


def _classify_wayback(url: str, path_lower: str) -> EmbedSpec | None:
    if path_lower.endswith(PDF_EXTENSION):
        return EmbedSpec("iframe_pdf", url, "Archived PDF", url)

    if path_lower.endswith(IMAGE_EXTENSIONS):
        return EmbedSpec("image", _wayback_image_url(url), "Archived image", url)

    return None


def _wayback_image_url(url: str) -> str:
    """Use Wayback raw-image modifier when missing."""
    match = re.match(
        r"(https?://web\.archive\.org/web/)(\d+)([a-z_]*)(/https?://.+)",
        url,
        flags=re.IGNORECASE,
    )
    if not match:
        return url

    prefix, timestamp, modifier, remainder = match.groups()
    if modifier == "im_":
        return url

    return f"{prefix}{timestamp}im_{remainder}"


def _youtube_id(url: str, host: str, parsed) -> str | None:
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.lstrip("/").split("/")[0]
        return video_id or None

    if "youtube.com" not in host:
        return None

    if parsed.path.casefold() == "/watch":
        query = parse_qs(parsed.query)
        ids = query.get("v", [])
        return ids[0] if ids else None

    embed_match = re.match(r"^/embed/([^/?]+)", parsed.path, flags=re.IGNORECASE)
    if embed_match:
        return embed_match.group(1)

    return None


def _vimeo_id(host: str, path_lower: str) -> str | None:
    if "vimeo.com" not in host:
        return None

    match = re.match(r"^/(?:video/)?(\d+)", path_lower)
    return match.group(1) if match else None


def render_embed(spec: EmbedSpec, caption: str = "") -> str:
    title = html.escape(caption or spec.title, quote=True)
    original = html.escape(spec.original_url, quote=True)
    src = html.escape(spec.src, quote=True)

    if spec.kind == "image":
        figcaption = (
            f"<figcaption>{html.escape(caption)} — "
            f'<a href="{original}">source</a></figcaption>'
            if caption
            else f'<figcaption><a href="{original}">View original</a></figcaption>'
        )
        return (
            f'<figure class="wiki-embed wiki-embed--image">\n'
            f'  <img src="{src}" alt="{title}" loading="lazy" '
            f'referrerpolicy="no-referrer" />\n'
            f"  {figcaption}\n"
            f"</figure>\n"
        )

    if spec.kind in {"iframe", "iframe_pdf"}:
        aspect = " wiki-embed--pdf" if spec.kind == "iframe_pdf" else ""
        label = html.escape(caption or spec.title)
        return (
            f'<div class="wiki-embed wiki-embed--iframe{aspect}">\n'
            f'  <iframe src="{src}" title="{title}" loading="lazy" '
            f'sandbox="allow-scripts allow-same-origin allow-popups" '
            f'referrerpolicy="no-referrer"></iframe>\n'
            f'  <p class="wiki-embed-caption"><a href="{original}">{label} (opens original)</a></p>\n'
            f"</div>\n"
        )

    return ""
