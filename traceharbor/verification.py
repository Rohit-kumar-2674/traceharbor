"""Verify portable export checksums without extracting or opening their contents."""

import hashlib
import re
import zipfile
from pathlib import Path

MAX_EXPORT_BYTES = 160 * 1024 * 1024
MAX_MEMBERS = 1_024
REQUIRED = {"case.json", "audit.json", "report.html", "README.txt", "checksums.sha256"}
ORIGINAL_NAME = re.compile(r"originals/[a-f0-9]{32}\.bin")


def verify_export(path):
    """Check bytes against the supplied manifest; this does not establish authenticity."""
    path = Path(path)
    if path.stat().st_size > MAX_EXPORT_BYTES:
        raise ValueError("Export exceeds the 160 MiB verification limit.")
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            names = [member.filename for member in members]
            if len(members) > MAX_MEMBERS or len(set(names)) != len(names):
                raise ValueError("Export has too many members or duplicate filenames.")
            if not REQUIRED.issubset(names):
                raise ValueError("Export is missing required report or checksum files.")
            if any(name not in REQUIRED and not ORIGINAL_NAME.fullmatch(name) for name in names):
                raise ValueError("Export contains an unexpected member path.")
            if any(member.flag_bits & 1 for member in members):
                raise ValueError("Encrypted ZIP members are not supported.")
            if sum(member.file_size for member in members) > MAX_EXPORT_BYTES:
                raise ValueError("Expanded export exceeds the 160 MiB verification limit.")
            manifest_info = archive.getinfo("checksums.sha256")
            if manifest_info.file_size > 128 * 1024:
                raise ValueError("Checksum manifest exceeds the 128 KiB limit.")
            expected = {}
            for line in archive.read(manifest_info).decode("utf-8").splitlines():
                match = re.fullmatch(r"([a-f0-9]{64})  (.+)", line)
                if not match or match[2] in expected:
                    raise ValueError("Checksum manifest has invalid or duplicate entries.")
                expected[match[2]] = match[1]
            if set(expected) != set(names) - {"checksums.sha256"}:
                raise ValueError("Checksum manifest and archive inventory differ.")
            issues, checked_bytes = [], 0
            for name, expected_hash in sorted(expected.items()):
                digest = hashlib.sha256()
                with archive.open(name) as stream:
                    while chunk := stream.read(64 * 1024):
                        checked_bytes += len(chunk)
                        if checked_bytes > MAX_EXPORT_BYTES:
                            raise ValueError("Expanded export exceeds the verification limit.")
                        digest.update(chunk)
                if digest.hexdigest() != expected_hash:
                    issues.append(f"Checksum mismatch: {name}")
            return {
                "valid": not issues,
                "scope": "archive-checksums",
                "files_checked": len(expected),
                "bytes_checked": checked_bytes,
                "issues": issues,
                "limitation": "Checksums detect changes relative to the included manifest. A party who rewrites both can pass this check. No authenticity, trusted timestamp, or case audit-chain validation is implied.",
            }
    except (zipfile.BadZipFile, UnicodeError, RuntimeError, NotImplementedError) as error:
        raise ValueError("Export is unreadable, corrupt, or uses an unsupported ZIP format.") from error
