import io
import json
import zipfile

import pytest

from traceharbor.cli import main
from traceharbor.reports import export_case
from traceharbor.store import Store
from traceharbor.verification import verify_export


@pytest.fixture
def exported(tmp_path):
    store = Store(tmp_path / "vault")
    case = store.create_case({"title": "Training", "purpose": "Export regression tests"})
    store.add_entry(case["id"], {"kind": "file", "title": "example.txt"}, b"sample evidence")
    path = tmp_path / "case.zip"
    path.write_bytes(export_case(store, case["id"], originals=True))
    return path


def rewrite(path, transform):
    with zipfile.ZipFile(path) as archive:
        files = [(item.filename, archive.read(item)) for item in archive.infolist()]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in transform(files):
            archive.writestr(name, data)
    path.write_bytes(buffer.getvalue())


def test_valid_export_and_originals_are_verified_without_extraction(exported):
    before = set(exported.parent.iterdir())
    result = verify_export(exported)
    assert result["valid"]
    assert result["scope"] == "archive-checksums"
    assert result["files_checked"] == 5
    assert set(exported.parent.iterdir()) == before


def test_modified_report_is_reported(exported):
    rewrite(
        exported,
        lambda files: [(name, b"modified" if name == "report.html" else data) for name, data in files],
    )
    result = verify_export(exported)
    assert not result["valid"]
    assert result["issues"] == ["Checksum mismatch: report.html"]


@pytest.mark.parametrize("name", ["../outside.txt", "/absolute.txt", "extra.txt"])
def test_unexpected_archive_paths_are_rejected(exported, name):
    rewrite(exported, lambda files: files + [(name, b"untrusted")])
    with pytest.raises(ValueError, match="unexpected member"):
        verify_export(exported)


def test_missing_manifest_is_rejected(exported):
    rewrite(exported, lambda files: [(name, data) for name, data in files if name != "checksums.sha256"])
    with pytest.raises(ValueError, match="missing required"):
        verify_export(exported)


def test_duplicate_members_are_rejected(exported):
    with pytest.warns(UserWarning, match="Duplicate name"):
        rewrite(exported, lambda files: files + [files[0]])
    with pytest.raises(ValueError, match="duplicate filenames"):
        verify_export(exported)


def test_expanded_size_limit_is_enforced(exported, monkeypatch):
    from traceharbor import verification

    with zipfile.ZipFile(exported) as archive:
        expanded = sum(member.file_size for member in archive.infolist())
    monkeypatch.setattr(verification, "MAX_EXPORT_BYTES", expanded - 1)
    with pytest.raises(ValueError, match="Expanded export"):
        verify_export(exported)


def test_cli_verifies_without_creating_a_live_vault(exported, tmp_path, capsys):
    unused = tmp_path / "unused-vault"
    assert main(["--data-dir", str(unused), "verify-export", str(exported)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"]
    assert not unused.exists()
    rewrite(
        exported,
        lambda files: [(name, b"modified" if name == "report.html" else data) for name, data in files],
    )
    assert main(["verify-export", str(exported)]) == 2


def test_corrupt_zip_has_a_clean_cli_error(tmp_path, capsys):
    path = tmp_path / "bad.zip"
    path.write_bytes(b"not a zip")
    assert main(["verify-export", str(path)]) == 2
    assert "unreadable" in capsys.readouterr().err
