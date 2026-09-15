import hashlib
import io
import json
import subprocess
import sys
import zipfile

import pytest
from PIL import Image, ImageDraw, ImageFont

from traceharbor.analysis import (
    MAX_FILE_BYTES,
    analyze_bytes,
    compare_analyses,
    inspect_url,
    public_leads,
    public_url,
)
from traceharbor.reports import export_case, report_html
from traceharbor.store import Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "vault")


@pytest.fixture
def case(store):
    return store.create_case({"title": "Test case", "purpose": "Unit test training evidence only"})


def png_bytes():
    image = Image.new("RGB", (800, 200), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 44)
    except OSError:
        font = ImageFont.load_default(size=40)
    draw.text((30, 65), "TRACEHARBOR TEST 12345", font=font, fill="black")
    stream = io.BytesIO()
    image.save(stream, "PNG")
    return stream.getvalue()


def test_file_hashes_are_original_bytes():
    data = b"known original\n"
    result = analyze_bytes(data, "../../sample.txt")
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert result["sha512"] == hashlib.sha512(data).hexdigest()
    assert result["filename"] == "sample.txt"
    assert result["image"] is None


def test_image_analysis():
    result = analyze_bytes(png_bytes(), "test.png")
    assert result["image"]["width"] == 800
    assert result["image"]["height"] == 200
    assert result["image"]["format"] == "PNG"
    assert len(result["image"]["dhash"]) == 16
    assert result["ocr"]["status"] == "not_requested"


def test_local_ocr():
    import shutil

    if not shutil.which("tesseract"):
        pytest.skip("Tesseract is optional")
    result = analyze_bytes(png_bytes(), "test.png", ocr=True)
    assert result["ocr"]["status"] == "complete"
    assert "TRACEHARBOR" in result["ocr"]["text"].upper()
    assert "12345" in result["ocr"]["text"]


def test_image_limits(monkeypatch):
    data = png_bytes()
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)
    with pytest.raises(ValueError, match="pixel"):
        analyze_bytes(data, "test.png")


@pytest.mark.parametrize("data", [b"", b"x" * (MAX_FILE_BYTES + 1)])
def test_empty_and_large_files(data):
    with pytest.raises(ValueError):
        analyze_bytes(data, "sample.bin")


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "https://localhost/a",
        "http://127.0.0.1/",
        "https://user:pass@example.com",
        "http://10.0.0.1",
        "http://[::1]",
        "https://example.com\nheader",
        "https://example.com:bad",
        "https://intranet.local",
        None,
    ],
)
def test_private_or_unsafe_urls(url):
    with pytest.raises(ValueError):
        public_url(url)


def test_url_inspection_does_not_fetch():
    result = inspect_url("https://example.org/path?token=test#part")
    assert result["hostname"] == "example.org"
    assert len(result["notices"]) == 3


def test_public_leads_never_claim_identity():
    result = public_leads("public_test")
    assert len(result["links"]) == 3
    assert all(link["status"] == "unverified" for link in result["links"])
    with pytest.raises(ValueError):
        public_leads("a@example.com")


def test_case_persistence(store, case):
    assert Store(store.directory).get_case(case["id"])["title"] == "Test case"
    assert store.verify(case["id"])["valid"]


def test_sources_findings_and_case_references(store, case):
    source = store.add_entry(
        case["id"], {"kind": "source", "title": "Documentation", "source_url": "https://example.org"}
    )
    finding = store.add_entry(
        case["id"],
        {
            "kind": "finding",
            "title": "Observation",
            "body": "A test note",
            "references": [source["id"]],
            "assessment": "corroborated",
        },
    )
    assert finding["assessment"] == "corroborated"
    assert store.verify(case["id"])["valid"]
    other = store.create_case({"title": "Other", "purpose": "Another test case"})
    with pytest.raises(ValueError, match="belong"):
        store.add_entry(
            other["id"],
            {"kind": "finding", "title": "Cross case", "body": "Test", "references": [source["id"]]},
        )


def test_unsupported_assessment_and_missing_support(store, case):
    for assessment in ["guilty", [], "corroborated"]:
        with pytest.raises(ValueError):
            store.add_entry(
                case["id"],
                {"kind": "finding", "title": "Unsupported", "body": "Test", "assessment": assessment},
            )


def test_event_timezone_is_required(store, case):
    payload = {"kind": "event", "title": "Event", "body": "Test", "event_at": "2026-01-01T12:00:00"}
    with pytest.raises(ValueError, match="timezone"):
        store.add_entry(case["id"], payload)
    payload["event_at"] += "+05:30"
    event = store.add_entry(case["id"], payload)
    assert event["event_at"] == "2026-01-01T06:30:00+00:00"


def test_archive_is_reversible_and_retains_records(store, case):
    entry = store.add_entry(case["id"], {"kind": "file", "title": "Test file"}, b"original")
    store.change_status(case["id"], "archived")
    assert store.read_original(entry["id"]) == b"original"
    with pytest.raises(ValueError, match="archived"):
        store.add_entry(case["id"], {"kind": "source", "title": "Test", "source_url": "https://example.org"})
    store.change_status(case["id"], "active")
    assert store.verify(case["id"])["valid"]


def test_file_tampering_is_detected(store, case):
    e = store.add_entry(case["id"], {"kind": "file", "title": "Test file"}, b"original")
    (store.blobs / e["analysis"]["sha256"]).write_bytes(b"tampered")
    assert not store.verify(case["id"])["valid"]
    with pytest.raises(ValueError, match="hash mismatch"):
        store.read_original(e["id"])
    with pytest.raises(ValueError, match="blocked"):
        export_case(store, case["id"])


def test_record_tampering_is_detected(store, case):
    with store.connect() as conn:
        row = json.loads(conn.execute("SELECT body FROM cases").fetchone()[0])
        row["title"] = "Modified outside app"
        conn.execute("UPDATE cases SET body=?", (json.dumps(row),))
    assert not store.verify(case["id"])["valid"]


def test_audit_removal_is_detected(store, case):
    with store.connect() as conn:
        conn.execute("DELETE FROM audit")
    assert not store.verify(case["id"])["valid"]


def test_export_manifest_and_originals_opt_in(store, case):
    e = store.add_entry(case["id"], {"kind": "file", "title": "Test file"}, b"original")
    for originals in [False, True]:
        with zipfile.ZipFile(io.BytesIO(export_case(store, case["id"], originals))) as z:
            assert (f"originals/{e['id']}.bin" in z.namelist()) == originals
            for line in z.read("checksums.sha256").decode().splitlines():
                expected, name = line.split("  ", 1)
                assert hashlib.sha256(z.read(name)).hexdigest() == expected
            assert json.loads(z.read("case.json"))["verification"]["valid"]


def test_report_escapes_user_text(store):
    c = store.create_case({"title": "<script>alert(1)</script>", "purpose": "<img src=x onerror=alert(1)>"})
    report = report_html(store.get_case(c["id"]), store.verify(c["id"]))
    assert "<script>" not in report and "<img src=x" not in report
    assert "&lt;script&gt;" in report


def test_hash_comparison():
    left = analyze_bytes(png_bytes(), "first.png")
    right = analyze_bytes(png_bytes(), "second.png")
    result = compare_analyses(left, right)
    assert result["exact_bytes_match"] and result["dhash_distance"] == 0


def test_cli_analyze_and_nonzero_error(tmp_path):
    path = tmp_path / "file.txt"
    path.write_bytes(b"CLI test")
    result = subprocess.run(
        [sys.executable, "-m", "traceharbor", "analyze", str(path)], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["sha256"] == hashlib.sha256(b"CLI test").hexdigest()
    invalid = subprocess.run(
        [sys.executable, "-m", "traceharbor", "analyze", str(path) + "missing"], capture_output=True
    )
    assert invalid.returncode == 2
