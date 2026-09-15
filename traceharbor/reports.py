"""Portable, escaped reports with explicit uncertainty and export checksums."""

import hashlib
import html
import io
import json
import zipfile

from . import __version__
from .store import now


def report_html(case, verification):
    def esc(value):
        return html.escape(str(value), quote=True)

    sections = []
    for entry in case["entries"]:
        details = ""
        if entry.get("source_url"):
            details += f"<p>Source: {esc(entry['source_url'])}</p>"
        if entry.get("references"):
            details += f"<p>References: {esc(', '.join(entry['references']))}</p>"
        if entry.get("event_at"):
            details += f"<p>Reported event time (UTC): {esc(entry['event_at'])}</p>"
        if entry.get("analysis"):
            details += f"<pre>{esc(json.dumps(entry['analysis'], indent=2, ensure_ascii=False))}</pre>"
        sections.append(
            f"<section><span>{esc(entry['kind'].upper())} · {esc(entry['id'])}</span>"
            f"<h2>{esc(entry['title'])}</h2><p>Recorded: {esc(entry['created_at'])}</p>"
            f"<p>Analyst assessment: {esc(entry['assessment'])}</p>"
            f'<p class="notes">{esc(entry["body"])}</p>{details}</section>'
        )
    status = "No inconsistencies detected" if verification["valid"] else "INTEGRITY CHECK FAILED"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>{esc(case["title"])} — TraceHarbor report</title><style>
body{{font:15px/1.6 system-ui,sans-serif;color:#182639;max-width:900px;margin:50px auto;padding:0 24px}}
h1{{font-size:34px;line-height:1.15}}h2{{font-size:21px}}header{{border-bottom:4px solid #287a69;padding-bottom:24px}}
section{{border-top:1px solid #d8dee4;margin-top:24px;padding-top:16px;break-inside:avoid}}
pre,.notes{{white-space:pre-wrap;overflow-wrap:anywhere}}pre{{font:12px/1.5 monospace;background:#f0f3f5;padding:18px}}
span{{color:#536575;font-size:12px}}.notice{{padding:18px;background:#fff4dc;border-left:4px solid #bc862a}}
@media print{{body{{margin:0;font-size:11px}}header{{break-after:avoid}}}}
</style></head><body><header><p>TRACEHARBOR / INVESTIGATION REPORT / v{__version__}</p>
<h1>{esc(case["title"])}</h1><p>{esc(case["purpose"])}</p>
<p>Case {esc(case["id"])} · Analyst label: {esc(case["analyst"])} · Status: {esc(case["status"])}</p>
<p>Exported {esc(now())}</p></header><div class="notice">
Research output, not a verified determination, certified forensic report or legal conclusion.
Sources, metadata and OCR require independent corroboration. Analyst labels are not authenticated identities.
Review for sensitive data before sharing. Raw metadata can contain location information.</div>
<h2>Local integrity check: {status}</h2><pre>{esc(json.dumps(verification, indent=2))}</pre>
{"".join(sections) or "<p>No evidence recorded.</p>"}
<footer><p>Evidence before inference. This report does not establish lawful collection, authenticity,
admissibility or an independently anchored chain of custody.</p></footer></body></html>"""


def export_case(store, case_id, originals=False):
    with store.lock:
        case = store.get_case(case_id)
        verification = store.verify(case_id)
        if not verification["valid"]:
            raise ValueError(
                "Export blocked: integrity checks failed. Use the verify command to review the issues."
            )
        file_entries = [e for e in case["entries"] if e["kind"] == "file"]
        if originals and sum(e["analysis"]["size_bytes"] for e in file_entries) > 100 * 1024 * 1024:
            raise ValueError(
                "Originals exceed the 100 MiB export limit. Export the report without originals."
            )
        payload = {
            "schema": "traceharbor.case.v1",
            "version": __version__,
            "exported_at": now(),
            "includes_originals": originals,
            "case": case,
            "verification": verification,
        }
        files = {
            "case.json": json.dumps(payload, ensure_ascii=False, indent=2).encode(),
            "report.html": report_html(case, verification).encode(),
            "audit.json": json.dumps(case["audit"], ensure_ascii=False, indent=2).encode(),
        }
        if originals:
            for entry in file_entries:
                files[f"originals/{entry['id']}.bin"] = store.read_original(entry["id"])
        files["README.txt"] = (
            "TraceHarbor portable report\n\nOpen report.html in a browser; print to PDF if needed.\n"
            "case.json contains the full records and links. audit.json contains the local hash chain.\n"
            "Originals, if requested, use record IDs with .bin suffixes to discourage accidental execution.\n"
            "Check checksums.sha256 before opening the report. On Linux: sha256sum -c checksums.sha256\n"
            "A checksum does not prove authenticity unless compared with an independently retained baseline.\n"
            "Reports include notes, source URLs, metadata and OCR. They are NOT automatically redacted.\n"
        ).encode()
        files["checksums.sha256"] = "".join(
            f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(files.items())
        ).encode()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        return buffer.getvalue()
