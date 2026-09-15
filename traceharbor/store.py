"""SQLite case records, preserved originals, and hash-linked local audit entries."""

import hashlib
import json
import os
import re
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .analysis import analyze_bytes, public_url


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def text(value, label, limit, required=True):
    if not isinstance(value, str) or len(value) > limit or "\x00" in value:
        raise ValueError(f"{label} must be text with at most {limit} characters.")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{label} is required.")
    return value


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{32}", value):
        raise ValueError("Invalid record ID.")
    return value


class Store:
    def __init__(self, directory):
        self.directory = Path(directory).expanduser().resolve()
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.blobs = self.directory / "originals"
        self.blobs.mkdir(mode=0o700, exist_ok=True)
        self.database = self.directory / "traceharbor.sqlite3"
        self.lock = threading.RLock()
        with self.connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS cases (
                    id TEXT PRIMARY KEY, body TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS entries (
                    id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), body TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS entries_case ON entries(case_id);
                CREATE TABLE IF NOT EXISTS audit (
                    case_id TEXT NOT NULL REFERENCES cases(id), seq INTEGER NOT NULL,
                    body TEXT NOT NULL, hash TEXT NOT NULL, PRIMARY KEY(case_id, seq)
                );
                PRAGMA user_version = 1;
            """)
        if os.name != "nt":
            self.database.chmod(0o600)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.database, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _case(self, conn, case_id):
        row = conn.execute("SELECT body FROM cases WHERE id=?", (identifier(case_id),)).fetchone()
        if not row:
            raise KeyError("Case not found.")
        return json.loads(row["body"])

    def _audit(self, conn, case_id, action, record):
        last = conn.execute(
            "SELECT seq, hash FROM audit WHERE case_id=? ORDER BY seq DESC LIMIT 1", (case_id,)
        ).fetchone()
        event = {
            "seq": last["seq"] + 1 if last else 1,
            "case_id": case_id,
            "at": now(),
            "actor": "local-operator",
            "action": action,
            "record_id": record["id"],
            "record_hash": digest(record),
            "previous": last["hash"] if last else "0" * 64,
        }
        conn.execute(
            "INSERT INTO audit VALUES (?,?,?,?)", (case_id, event["seq"], canonical(event), digest(event))
        )

    def create_case(self, payload):
        case = {
            "id": uuid.uuid4().hex,
            "title": text(payload.get("title"), "Title", 120),
            "purpose": text(payload.get("purpose", ""), "Purpose", 4000),
            "analyst": text(payload.get("analyst", "Local analyst"), "Analyst label", 120),
            "status": "active",
            "created_at": now(),
            "updated_at": now(),
        }
        with self.lock, self.connect() as conn:
            if conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0] >= 500:
                raise ValueError("This workspace supports up to 500 cases.")
            conn.execute("INSERT INTO cases VALUES (?,?)", (case["id"], canonical(case)))
            self._audit(conn, case["id"], "case.created", case)
        return case

    def change_status(self, case_id, status):
        if not isinstance(status, str) or status not in {"active", "archived"}:
            raise ValueError("Case status must be active or archived.")
        with self.lock, self.connect() as conn:
            case = self._case(conn, case_id)
            case.update(status=status, updated_at=now())
            conn.execute("UPDATE cases SET body=? WHERE id=?", (canonical(case), case_id))
            self._audit(conn, case_id, "case.status_changed", case)
        return case

    def list_cases(self):
        with self.connect() as conn:
            result = []
            for row in conn.execute("SELECT body FROM cases"):
                case = json.loads(row["body"])
                entries = [
                    json.loads(r["body"])
                    for r in conn.execute("SELECT body FROM entries WHERE case_id=?", (case["id"],))
                ]
                case["counts"] = {
                    kind: sum(e["kind"] == kind for e in entries)
                    for kind in ["file", "source", "finding", "event"]
                }
                case["last_activity"] = max([case["updated_at"]] + [e["created_at"] for e in entries])
                result.append(case)
            return sorted(result, key=lambda c: c["last_activity"], reverse=True)

    def get_case(self, case_id):
        with self.connect() as conn:
            case = self._case(conn, case_id)
            case["entries"] = [
                json.loads(r["body"])
                for r in conn.execute("SELECT body FROM entries WHERE case_id=? ORDER BY rowid", (case_id,))
            ]
            case["audit"] = [
                dict(json.loads(r["body"]), hash=r["hash"])
                for r in conn.execute("SELECT body, hash FROM audit WHERE case_id=? ORDER BY seq", (case_id,))
            ]
            return case

    def add_entry(self, case_id, payload, data=None, ocr=False):
        kind = payload.get("kind")
        if not isinstance(kind, str) or kind not in {"file", "source", "finding", "event"}:
            raise ValueError("Choose a supported evidence type.")
        entry = {
            "id": uuid.uuid4().hex,
            "case_id": identifier(case_id),
            "kind": kind,
            "title": text(payload.get("title"), "Title", 200),
            "created_at": now(),
            "body": text(payload.get("body", ""), "Notes", 12000, required=False),
            "assessment": "unverified",
            "source_url": "",
            "references": [],
        }
        if payload.get("source_url"):
            entry["source_url"] = public_url(payload["source_url"])
        if kind == "source" and not entry["source_url"]:
            raise ValueError("A public source URL is required.")
        if kind in {"finding", "event"}:
            if not entry["body"]:
                raise ValueError("A finding or event needs explanatory notes.")
            references = payload.get("references", [])
            if not isinstance(references, list) or len(references) > 50:
                raise ValueError("Supply up to 50 evidence references.")
            entry["references"] = list(dict.fromkeys(identifier(ref) for ref in references))
            assessment = payload.get("assessment", "unverified")
            if not isinstance(assessment, str) or assessment not in {
                "unverified",
                "corroborated",
                "disputed",
            }:
                raise ValueError("Invalid analyst assessment.")
            if assessment == "corroborated" and not entry["references"]:
                raise ValueError("A corroborated finding needs an evidence reference.")
            entry["assessment"] = assessment
        if kind == "event":
            event_at = text(payload.get("event_at"), "Event time", 64)
            try:
                parsed = datetime.fromisoformat(event_at.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError
                entry["event_at"] = parsed.astimezone(timezone.utc).isoformat()
            except ValueError:
                raise ValueError(
                    "Event time must include a timezone, for example 2026-01-01T12:00:00Z."
                ) from None
        if kind == "file":
            if data is None:
                raise ValueError("File bytes are required.")
            entry["analysis"] = analyze_bytes(data, payload.get("filename", entry["title"]), ocr)
            entry["collection_method"] = text(
                payload.get("collection_method", "Manual upload"), "Collection method", 200
            )
        with self.lock, self.connect() as conn:
            case = self._case(conn, case_id)
            if case["status"] == "archived":
                raise ValueError("Reopen this archived case before adding evidence.")
            if conn.execute("SELECT COUNT(*) FROM entries WHERE case_id=?", (case_id,)).fetchone()[0] >= 500:
                raise ValueError("Each case supports up to 500 records in this release.")
            for ref in entry["references"]:
                if not conn.execute(
                    "SELECT 1 FROM entries WHERE id=? AND case_id=?", (ref, case_id)
                ).fetchone():
                    raise ValueError("Evidence references must belong to this case.")
            if kind == "file":
                blob = self.blobs / entry["analysis"]["sha256"]
                if blob.exists():
                    if hashlib.sha256(blob.read_bytes()).hexdigest() != entry["analysis"]["sha256"]:
                        raise ValueError(
                            "An existing original failed integrity verification. Stop and review the vault."
                        )
                else:
                    with os.fdopen(
                        os.open(blob, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
                    ) as handle:
                        handle.write(data)
                        handle.flush()
                        os.fsync(handle.fileno())
            conn.execute("INSERT INTO entries VALUES (?,?,?)", (entry["id"], case_id, canonical(entry)))
            self._audit(conn, case_id, f"{kind}.added", entry)
        return entry

    def get_entry(self, entry_id):
        with self.connect() as conn:
            row = conn.execute("SELECT body FROM entries WHERE id=?", (identifier(entry_id),)).fetchone()
            if not row:
                raise KeyError("Evidence not found.")
            return json.loads(row["body"])

    def read_original(self, entry_id):
        entry = self.get_entry(entry_id)
        if entry["kind"] != "file":
            raise ValueError("This record does not contain a file.")
        sha = entry["analysis"]["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise ValueError("Invalid stored digest.")
        try:
            data = (self.blobs / sha).read_bytes()
        except FileNotFoundError:
            raise ValueError("Original file is missing.") from None
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError("Original file hash mismatch. Do not rely on this copy.")
        return data

    def verify(self, case_id):
        with self.lock:
            case = self.get_case(case_id)
            issues, previous, latest = [], "0" * 64, {}
            for index, event in enumerate(case["audit"], 1):
                body = {key: value for key, value in event.items() if key != "hash"}
                if (
                    event["seq"] != index
                    or event["previous"] != previous
                    or digest(body) != event["hash"]
                    or event["case_id"] != case_id
                ):
                    issues.append(f"Audit chain mismatch at entry {index}.")
                previous = event["hash"]
                latest[event["record_id"]] = event["record_hash"]
            if not case["audit"]:
                issues.append("Audit trail is missing.")
            records = [e for e in case["entries"]]
            records.append({k: v for k, v in case.items() if k not in {"entries", "audit"}})
            existing = {r["id"] for r in records}
            for record in records:
                if latest.get(record["id"]) != digest(record):
                    issues.append(f"Record hash mismatch: {record['id']}.")
                if record.get("kind") == "file":
                    try:
                        self.read_original(record["id"])
                    except (ValueError, OSError) as exc:
                        issues.append(f"File {record['id']}: {exc}")
            if set(latest) != existing:
                issues.append("The audit trail and record inventory differ.")
            return {
                "valid": not issues,
                "issues": issues,
                "checked_at": now(),
                "audit_entries": len(case["audit"]),
                "records": len(records),
                "files": sum(e["kind"] == "file" for e in case["entries"]),
                "head_hash": previous,
                "limitation": "Local hash linkage is not a trusted timestamp or independently anchored chain of custody. A privileged attacker can rewrite records and hashes.",
            }
