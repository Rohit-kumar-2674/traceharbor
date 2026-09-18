# Verify a portable report

TraceHarbor exports include an HTML report, JSON records, the recorded audit trail, and a SHA-256 checksum manifest. Original files are optional.

After transferring a ZIP to another device, verify its file bytes before reviewing it:

```bash
python -m traceharbor verify-export case-report.zip
```

This command works without a running server or a local case vault. It does not extract the archive, execute its contents, render its HTML, or contact a website. It returns JSON with `valid`, `files_checked`, `bytes_checked`, and `issues`. Exit code 0 means the checksums match; exit code 2 means verification failed or the ZIP could not be read.

The verifier rejects missing or duplicate files, unexpected paths, encrypted members, manifest/inventory differences, and exports beyond its limits. It streams payloads in 64 KiB chunks with a 160 MiB total expanded-size ceiling, a 128 KiB manifest ceiling, and a 1,024-member ceiling.

**What this verifies:** archive bytes match the supplied checksum manifest. Someone who can replace both the files and the manifest can produce a matching archive. This is not authenticity verification, a trusted timestamp, or a revalidation of the case's audit chain. For live case records and audit linkage, use `traceharbor verify CASE_ID` before exporting and retain an independently trusted copy of the export hash.

Exports retain the notes and metadata you selected, including potentially sensitive source URLs and EXIF. Review the contents and the intended recipients before sharing a report.
