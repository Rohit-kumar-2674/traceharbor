"""Offline analysis. No URL fetching, face matching, or external API calls."""

import hashlib
import io
import ipaddress
import re
import shutil
import subprocess
import tempfile
import warnings
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

try:
    from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError

    Image.MAX_IMAGE_PIXELS = 20_000_000
    IMAGE_SUPPORT = True
except ImportError:
    IMAGE_SUPPORT = False

MAX_FILE_BYTES = 10 * 1024 * 1024
SUPPORTED_IMAGES = {"PNG", "JPEG", "WEBP", "TIFF", "BMP", "GIF"}


def capabilities():
    return {
        "images": IMAGE_SUPPORT,
        "ocr": IMAGE_SUPPORT and bool(shutil.which("tesseract")),
        "max_file_bytes": MAX_FILE_BYTES,
        "outbound_requests": False,
    }


def public_url(value):
    """Validate reference URLs; never resolve DNS or fetch their contents."""
    if not isinstance(value, str) or len(value) > 2048 or re.search(r"[\x00-\x20\x7f]", value):
        raise ValueError("Enter a valid public HTTP(S) URL without spaces.")
    try:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            raise ValueError
        host = parts.hostname.rstrip(".").encode("idna").decode("ascii").lower()
        port = parts.port
        if host == "localhost" or host.endswith((".local", ".localhost", ".internal")):
            raise ValueError
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            labels = host.split(".")
            if (
                len(host) > 253
                or len(labels) < 2
                or re.fullmatch(r"[0-9.]+", host)
                or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)
            ):
                raise ValueError("Invalid hostname")
        else:
            if not ip.is_global:
                raise ValueError("Private address")
        netloc = f"[{host}]" if ":" in host else host
        if port is not None:
            netloc += f":{port}"
        return urlunsplit((parts.scheme, netloc, parts.path or "/", parts.query, parts.fragment))
    except (ValueError, UnicodeError):
        raise ValueError("Use a public HTTP(S) address without credentials or a private IP.") from None


def inspect_url(value):
    url = public_url(value)
    parts = urlsplit(url)
    notices = ["Offline syntax inspection only. Domain ownership and content are not verified."]
    if parts.scheme == "http":
        notices.append("The URL uses unencrypted HTTP.")
    if "xn--" in parts.hostname:
        notices.append("Internationalized hostname: examine its spelling independently.")
    if parts.query:
        notices.append("Query parameters may contain personal data or access tokens. Review before saving.")
    if parts.fragment:
        notices.append("The fragment may contain sensitive client-side state.")
    return {
        "url": url,
        "scheme": parts.scheme,
        "hostname": parts.hostname,
        "port": parts.port,
        "path": parts.path,
        "query": parts.query,
        "fragment": parts.fragment,
        "notices": notices,
    }


def public_leads(username):
    if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,39}", username):
        raise ValueError("Use 1–39 letters, numbers, underscores or hyphens.")
    name = quote(username, safe="")
    return {
        "username": username,
        "status": "unverified",
        "notice": "Candidate public URLs only. No account existence or common identity is inferred.",
        "links": [
            {"label": label, "url": url, "status": "unverified"}
            for label, url in [
                ("GitHub", f"https://github.com/{name}"),
                ("Reddit", f"https://www.reddit.com/user/{name}/"),
                ("Hacker News", f"https://news.ycombinator.com/user?id={name}"),
            ]
        ],
    }


def _safe_value(value):
    if isinstance(value, bytes):
        return f"[binary EXIF: {len(value)} bytes]"
    if isinstance(value, (list, tuple)):
        return [_safe_value(v) for v in value[:100]]
    return str(value)[:3000]


def difference_hash(img):
    """64-bit dHash of orientation-corrected image; not an identity measure."""
    reduced = img.convert("L").resize((9, 8))
    pixels = [reduced.getpixel((x, y)) for y in range(8) for x in range(9)]
    number = 0
    for row in range(8):
        for col in range(8):
            number = (number << 1) | (pixels[row * 9 + col] > pixels[row * 9 + col + 1])
    return f"{number:016x}"


def analyze_bytes(data, filename, ocr=False):
    if not data:
        raise ValueError("Empty files are not accepted.")
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("File exceeds the 10 MiB limit.")
    result = {
        "filename": Path(filename.replace("\\", "/")).name[:200] or "evidence.bin",
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "sha512": hashlib.sha512(data).hexdigest(),
        "image": None,
        "ocr": {"status": "not_requested", "text": ""},
        "warnings": [],
    }
    if not IMAGE_SUPPORT:
        result["warnings"].append("Install the images extra (Pillow) for image metadata and dHash.")
        if ocr:
            result["ocr"]["status"] = "unavailable"
        return result
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as original:
                if original.format not in SUPPORTED_IMAGES:
                    result["warnings"].append("This image format is not decoded by the image module.")
                    return result
                original.load()
                exif = original.getexif()
                metadata = {
                    str(ExifTags.TAGS.get(k, k)): _safe_value(v)
                    for k, v in list(exif.items())[:200]
                    if k != 34853
                }
                gps = exif.get_ifd(34853) if 34853 in exif else {}
                if gps:
                    metadata["GPSInfo"] = {
                        str(ExifTags.GPSTAGS.get(k, k)): _safe_value(v) for k, v in gps.items()
                    }
                    result["warnings"].append(
                        "Location metadata is present. Treat it as sensitive and unverified."
                    )
                oriented = ImageOps.exif_transpose(original).convert("RGB")
                result["image"] = {
                    "format": original.format,
                    "width": original.width,
                    "height": original.height,
                    "mode": original.mode,
                    "frames": getattr(original, "n_frames", 1),
                    "dhash": difference_hash(oriented),
                    "exif": metadata,
                }
                result["warnings"].append(
                    "EXIF can be edited. dHash compares image appearance, not people or truth."
                )
                if result["image"]["frames"] > 1:
                    result["warnings"].append("Only the first frame is analysed.")
                if ocr:
                    result["ocr"] = run_ocr(oriented)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError("Image exceeds the safe decoded-pixel limit.") from None
    except UnidentifiedImageError:
        result["warnings"].append("Not a supported image. File hashes are still available.")
        if ocr:
            result["ocr"]["status"] = "not_an_image"
    except (OSError, ValueError, SyntaxError, TypeError, OverflowError):
        raise ValueError("The image is damaged or cannot be safely decoded.") from None
    return result


def run_ocr(img):
    engine = shutil.which("tesseract")
    if not engine:
        return {"status": "unavailable", "text": "", "notice": "Install Tesseract for local OCR."}
    # Decode/re-encode first: do not pass arbitrary submitted formats to the executable.
    with tempfile.TemporaryDirectory(prefix="traceharbor-ocr-") as directory:
        source = Path(directory) / "input.png"
        img.thumbnail((3200, 3200))
        img.save(source, "PNG")
        try:
            process = subprocess.run(
                [engine, str(source), "stdout", "-l", "eng", "--psm", "3"],
                capture_output=True,
                timeout=20,
                check=False,
            )
            if process.returncode:
                return {
                    "status": "failed",
                    "text": "",
                    "notice": "Check Tesseract and English language data.",
                }
            text = process.stdout.decode("utf-8", "replace")[:100_000].strip()
            return {
                "status": "complete",
                "text": text,
                "notice": "Machine transcription; independently check against the original.",
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "text": "", "notice": "OCR stopped after 20 seconds."}


def compare_analyses(left, right):
    a, b = left.get("image"), right.get("image")
    distance = None
    if a and b:
        distance = (int(a["dhash"], 16) ^ int(b["dhash"], 16)).bit_count()
    return {
        "exact_bytes_match": left["sha256"] == right["sha256"],
        "dhash_distance": distance,
        "dhash_bits": 64,
        "notice": "dHash distance is not a probability, identity match or authenticity assessment.",
    }
