# traceharbor

<p align="center"><img src="traceharbor/web/mark.svg" width="72" alt="TraceHarbor logo"></p>
<h2 align="center">TraceHarbor 路 Evidence before inference.</h2>
<p align="center">A local-first investigation workspace for public-source research,<br>careful evidence review, and accountable findings.</p>

**v0.1.0 路 Research release 路 MIT licensed 路 Python + FastAPI 路 No frontend build step**

TraceHarbor brings case files, original-byte fingerprints, image metadata, local OCR,
source references, findings, timelines, and reports into one considered workspace.
It also works from a terminal. It is the renamed successor to the TraceForge concept.

> **Not a certified forensic or law-enforcement system.** This release is suitable for
> training and evaluation with non-sensitive material. Independent security, privacy,
> forensic, and organisational review are needed before any real police or sensitive
> casework. It does not establish identity, guilt, admissibility, authenticity, or lawful authority.

## What works now

| Capability | What it actually does |
| --- | --- |
| Case workspaces | Persist purpose, analyst label, evidence and findings in SQLite; search, archive and reopen cases |
| Evidence lab | SHA-256 and SHA-512 of original bytes; optional image dimensions, format, EXIF and 64-bit dHash |
| Local OCR | Tesseract English transcription with an execution timeout and explicit completion/error status |
| Original preservation | Store unchanged uploaded bytes by SHA-256; verify before download |
| Public source references | Record validated HTTP(S) links and collection context; no automatic page fetch |
| Public leads | Prepare three unverified candidate profile URLs for manual review; no account enumeration or identity inference |
| Link inspector | Offline URL parsing, IDN/HTTP/query/fragment notices; not a reputation or ownership lookup |
| Findings & timeline | Analyst-written assessments with same-case evidence references and UTC event times |
| File comparison | Exact-byte hash comparison and image dHash distance; never facial recognition |
| Local integrity checks | Compare stored record hashes, originals and a hash-linked activity log |
| Portable reports | ZIP containing printable HTML, structured JSON, audit entries and SHA-256 manifest; originals are opt-in |
| Terminal commands | Analyse files, inspect URLs, create/list cases, add files, verify and export |

All operational statistics come from your local records. The optional training case
is explicitly labelled and is created only when you request it.

## Quick start

Use Python **3.10 or newer**. The release was tested here on Linux with Python 3.12.
For Android, see the [Termux/proot Debian instructions](docs/INSTALL.md#android-with-termux-and-proot-debian).

```bash
git clone https://github.com/Rohit-kumar-2674/traceharbor.git
cd traceharbor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps .
python -m traceharbor doctor
python -m traceharbor serve
```

If the repository is private, cloning requires your normal GitHub authentication.
Alternatively, download its ZIP while signed into GitHub and extract it. **Do not paste
GitHub tokens or passwords into chat, case notes, or source files.**

Open the private `http://127.0.0.1:8742/#token=鈥 link printed in your terminal.
The browser removes the token from the address bar and keeps it only in that tab's
session storage. The token changes on each server start. Keep the terminal running;
press **Ctrl+C** to stop. No JavaScript build tools are required to run the app.

Tesseract is optional. For Ubuntu/Debian, install it before requesting OCR:

```bash
sudo apt install tesseract-ocr tesseract-ocr-eng
```

Inside a root proot Debian session, omit `sudo`. Without Tesseract, hashing and the
other tools still work. Without Pillow, the standalone hash/record tools work, but
image decoding and OCR are unavailable. `doctor` reports the actual capabilities.

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install --no-deps .
python -m traceharbor serve
```

If execution policy prevents activation, use `.venv\Scripts\python.exe` directly
for the commands instead of weakening the system's execution policy. Windows and
Android installation steps are documented but were not device-tested in this build.

## A useful first workflow

1. Create a case and document the purpose and scope.
2. Open **Evidence lab**, choose a training file, and select its destination case.
3. Optionally enable OCR, then run analysis. Keep the original as your reference.
4. Add a source URL and write a finding referencing the relevant evidence records.
5. Add any reported events to the timeline; keep event time distinct from capture time.
6. Open **Audit**, run the integrity check, and inspect the result.
7. Export a report. Review it for personal information before sharing.

Records are append-only through the application. Correct a finding by adding a new
finding that cites the earlier record and explains the correction. Archiving never
deletes evidence. A separate retention/deletion workflow is not implemented yet.

## Terminal examples

```bash
python -m traceharbor analyze photo.jpg --ocr
python -m traceharbor inspect-url 'https://example.org/article?ref=training'
python -m traceharbor create-case 'Documentation review' --purpose 'Training with public material'
python -m traceharbor cases
python -m traceharbor add-file CASE_ID photo.jpg --notes 'Authorised training image' --ocr
python -m traceharbor verify CASE_ID
python -m traceharbor export CASE_ID --output report.zip
```

Replace `CASE_ID` with the ID returned by `create-case` or `cases`. Add
`--include-originals` to export original files deliberately. The CLI refuses to
overwrite an existing export. `verify` returns exit code `2` when checks fail.

To use a separate workspace, put the global data option before the command:

```bash
python -m traceharbor --data-dir ./training-vault serve
```

Do not put real case data inside the source repository. The default location is
`~/.local/share/traceharbor`. Set `TRACEHARBOR_DATA_DIR` to choose a different location.

## Security and limitations

- The service binds to **127.0.0.1 only**, rejects other Host values and cross-origin
  requests, and requires a per-session bearer token for case APIs.
- The frontend has a restrictive Content Security Policy and escapes record content.
- File uploads are limited to **10 MiB**, decoded images to **20 megapixels**, and OCR
  to **20 seconds**. Two analysis jobs can run concurrently.
- Up to **500 cases**, **500 records per case**, and **100 MiB of originals per export**.
- No analytics, telemetry, remote APIs, automatic scraping, external fonts or CDNs.
  Clicking source/lead links deliberately contacts the destination in your browser.
- Original files, SQLite records, exports and temporary OCR images are **not encrypted
  by the application**. Use an encrypted device and an organisation-approved process.
- The local activity log is **not** an independently anchored chain of custody.
  A privileged attacker can rewrite the entire database and recompute its hashes.
- An analyst label is not a verified user identity. There is no multi-user access
  control, trusted timestamp service, signed evidence sealing or automatic redaction.
- EXIF may be edited; OCR may be wrong; matching usernames may belong to different
  people. dHash is not an identity, confidence, guilt or authenticity score.
- No facial identification, private-account access, covert tracking, credential
  harvesting, surveillance feeds or bypassing access controls.

Read the [threat model](docs/SECURITY_MODEL.md), [responsible-use guide](docs/RESPONSIBLE_USE.md),
and [security reporting policy](SECURITY.md) before evaluation.

## Architecture

| Component | Location | Responsibility |
| --- | --- | --- |
| Browser workspace | `traceharbor/web/` | Responsive native JavaScript/CSS interface; no Node runtime required |
| HTTP API | `traceharbor/server.py` | FastAPI routes, request limits, same-origin and token checks |
| Evidence analysis | `traceharbor/analysis.py` | Original-byte hashing, optional Pillow/Tesseract, offline link helpers |
| Case store | `traceharbor/store.py` | SQLite records, content-addressed originals, hash-linked audit entries |
| Reports | `traceharbor/reports.py` | Escaped HTML, JSON, ZIP and export checksum manifest |
| Terminal | `traceharbor/cli.py` | Local analysis and case commands |

The earlier React/Vite idea was simplified to a dependency-free frontend for easier
phone-based setup and to avoid native JavaScript build-tool failures. FastAPI remains
the backend; OCR invokes Tesseract directly without a shell. Tools use the same analysis
and storage code from both browser and CLI.

## Repository structure

```text
traceharbor/
鈹溾攢鈹� traceharbor/
鈹�   鈹溾攢鈹� __init__.py          Package version
鈹�   鈹溾攢鈹� __main__.py          `python -m traceharbor` entry point
鈹�   鈹溾攢鈹� analysis.py          Hashing, image metadata, OCR, URL and lead helpers
鈹�   鈹溾攢鈹� cli.py               Terminal commands and loopback server launcher
鈹�   鈹溾攢鈹� reports.py            HTML/JSON/ZIP export generation
鈹�   鈹溾攢鈹� server.py            FastAPI app, authentication and API routes
鈹�   鈹溾攢鈹� store.py             SQLite case store and local audit chain
鈹�   鈹斺攢鈹� web/
鈹�       鈹溾攢鈹� index.html       Browser shell
鈹�       鈹溾攢鈹� app.js           Interface state, forms and API calls
鈹�       鈹溾攢鈹� style.css        All responsive styling in one file
鈹�       鈹斺攢鈹� mark.svg         TraceHarbor logo
鈹溾攢鈹� tests/
鈹�   鈹溾攢鈹� test_core.py         Analysis, persistence, integrity and export tests
鈹�   鈹斺攢鈹� test_api.py          Authentication, limits and workflow tests
鈹溾攢鈹� scripts/
鈹�   鈹斺攢鈹� browser_smoke.cjs    Optional synthetic Playwright browser test
鈹溾攢鈹� docs/
鈹�   鈹溾攢鈹� INSTALL.md           Desktop and Termux/proot setup
鈹�   鈹溾攢鈹� SECURITY_MODEL.md    Threat model and integrity boundaries
鈹�   鈹溾攢鈹� RESPONSIBLE_USE.md   Public-service and research limits
鈹�   鈹斺攢鈹� VALIDATION.md        Tests actually run and known gaps
鈹溾攢鈹� .github/                 CI checks, issue and pull-request templates
鈹溾攢鈹� pyproject.toml           Package metadata and development configuration
鈹溾攢鈹� requirements.lock        Tested Python runtime versions
鈹溾攢鈹� package.json              Optional browser-test dependency only
鈹溾攢鈹� SECURITY.md               Vulnerability-reporting policy
鈹溾攢鈹� CONTRIBUTING.md           Contributor rules
鈹溾攢鈹� ROADMAP.md                Planned work, not implemented features
鈹斺攢鈹� LICENSE                   MIT license
```

The runtime creates its private data directory separately from this tree:

```text
~/.local/share/traceharbor/
鈹溾攢鈹� traceharbor.sqlite3      Cases, entries and audit events
鈹斺攢鈹� originals/               Original bytes named by SHA-256
```

The data directory is created with restrictive permissions on POSIX systems. It is
not automatically encrypted, synced, uploaded or backed up. Never commit it to Git.

## How the system works

### Browser session

`traceharbor serve` creates a random session key and binds FastAPI to `127.0.0.1`.
The terminal prints one private link containing the key in its URL fragment. The
browser reads the fragment, stores the key in session storage, removes it from the
address bar, and sends it as a bearer token for protected API calls. The server
rejects a different Host header, cross-origin request, cross-site fetch, or missing
token. Restarting the process invalidates the previous key.

### Case and evidence flow

1. A case receives a random 32-character hex ID and a purpose, analyst label, status
   and UTC creation time.
2. A file is size-checked, hashed from the original bytes, optionally decoded through
   Pillow, and optionally sent to the local Tesseract executable.
3. When saving a file, the unchanged bytes are written to `originals/<sha256>` and the
   analysis JSON is stored in SQLite. The upload filename is display-only and never a
   filesystem path.
4. Sources, findings and events become separate records. Findings may reference only
   evidence from the same case. A corroborated assessment is rejected without a
   supporting reference.
5. Every case/record mutation appends a canonical JSON audit event containing the
   current record hash and the previous audit hash.
6. Verification recomputes record, audit and original-file hashes. A failed check
   blocks export so the operator has to review the vault first.

### Image analysis

The analyzer records file hashes even when a file is not an image. For supported
images it records format, width, height, colour mode, frame count, EXIF values, and a
64-bit dHash after orientation correction. dHash is a visual similarity hint only; it
does not identify a person, prove that two files came from the same source, or prove
authenticity. GPS EXIF is surfaced as sensitive and is not silently removed.

### OCR analysis

OCR is opt-in. Pillow first decodes and re-encodes the image as PNG; Tesseract then
runs with an argument list and a 20-second timeout. The output is labelled as a machine
transcription and stored as a derived result. It may omit, invent or misread text.

### Reports

The export is a ZIP containing `report.html`, `case.json`, `audit.json`,
`checksums.sha256` and `README.txt`. Original files are excluded by default and can
be deliberately included only after choosing the option. Reports contain raw notes,
metadata and OCR, so the application does not claim they are safe to share without
review.

## API reference

The API is local and token-protected. The browser is the supported client; these
endpoints are also useful for tests and small integrations. The API is not a promise
of a stable public service yet.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Unauthenticated liveness check |
| `GET` | `/api/status` | Version and optional capabilities |
| `GET` | `/api/cases` | List cases and record counts |
| `POST` | `/api/cases` | Create a case |
| `GET` | `/api/cases/{case_id}` | Read a case, records and audit events |
| `PATCH` | `/api/cases/{case_id}` | Archive or reopen a case |
| `POST` | `/api/analyze` | Analyse base64 data without retaining it |
| `POST` | `/api/cases/{case_id}/entries` | Add a source, finding, event or file |
| `GET` | `/api/entries/{entry_id}/original` | Verify and download a stored original |
| `GET` | `/api/cases/{case_id}/verify` | Verify hashes and the audit chain |
| `GET` | `/api/cases/{case_id}/export` | Download a report ZIP; `originals=true` is opt-in |
| `POST` | `/api/inspect-url` | Parse a public URL without fetching it |
| `POST` | `/api/public-leads` | Prepare unverified public profile candidates |
| `POST` | `/api/compare` | Compare two same-case file records |

Protected endpoints require:

```http
Authorization: Bearer <session-key>
Content-Type: application/json
```

File JSON uses a base64 value in `data_base64`. The browser handles this conversion;
do not put a file path in API JSON and expect the server to read it. The server never
accepts a path supplied by a client.

Example analysis request:

```json
{
  "filename": "training-note.png",
  "data_base64": "iVBORw0KGgoAAAANSUhEUg...",
  "ocr": true
}
```

The API deliberately does not expose arbitrary SQL, filesystem paths, shell commands,
remote URL fetching, account searches, face matching or private-data connectors.

## Troubleshooting

| Symptom | What it means | Fix |
| --- | --- | --- |
| `python: command not found` | Python is missing or the virtual environment is not active | Install Python 3.10+; run `source .venv/bin/activate` or use `.venv/bin/python` |
| `No module named traceharbor` | The package was not installed in the active environment | Run `python -m pip install --no-deps .` from the repository root |
| `Connection refused` | The server stopped, a wrong port was used, or the browser is not on the same device | Keep the terminal running and open the exact URL it printed |
| `401 Unlock this workspace` | The key is missing, expired or from an older server process | Restart/use the newest printed session link; never reuse an old one |
| `403 Host/origin` | The request is not loopback or came from another origin | Use `127.0.0.1`, not a phone LAN IP, public tunnel or guessed hostname |
| `Address already in use` | Another service owns the port | Run `python -m traceharbor serve --port 8743` and use its new link |
| Image support is unavailable | Pillow is missing in the active environment | Run `python -m pip install -r requirements.lock` and `doctor` again |
| OCR is unavailable | Tesseract or English language data is missing | Install `tesseract-ocr` and `tesseract-ocr-eng`, then run `doctor` |
| OCR is blank or wrong | Text is small, stylised, rotated, obscured or low contrast | Treat OCR as a lead; inspect the original and transcribe manually |
| `File exceeds the 10 MiB limit` | The upload guard rejected the file | Use a smaller authorised copy; do not weaken the limit for untrusted files |
| Image pixel-limit error | The decoded image is too large for safe processing | Resize a copy for analysis while retaining the original separately and documenting it |
| `Case not found` | The ID is incomplete, mistyped or belongs to another data directory | Copy the full ID from `cases`; check `TRACEHARBOR_DATA_DIR` |
| Cannot add to archived case | Archived cases are read-only | Reopen the case in the UI, or `PATCH` status back to `active` |
| Integrity check fails | A record, audit row or original changed/disappeared | Stop exporting, preserve the vault, record the issue and investigate; do not overwrite hashes |
| Export is blocked | Verification found an inconsistency | Fix the underlying storage issue or make a clearly labelled review copy; do not bypass the check |
| Export ZIP has no originals | Originals are opt-in | Export again with the UI checkbox or CLI `--include-originals` after reviewing sensitivity |
| `Permission denied` in Termux | The process lacks access to the selected Android path | Keep the vault inside Debian's home directory or grant storage permission before copying files |
| `pip` installation breaks in native Termux | Termux's system Python packaging differs from Debian | Use the documented proot Debian workflow; do not replace Termux's package-managed pip |
| Browser smoke test cannot start | Playwright browser binaries are not installed or network download failed | Run `npx playwright install chromium` in a normal development environment; core app tests do not require it |
| Browser cannot reach local app in this authoring environment | Some managed browser environments block loopback access | Test from the same device/browser where the server is running; see `docs/VALIDATION.md` |

Do not delete the SQLite database or `originals/` folder to 鈥渇ix鈥� an integrity error.
That destroys the material needed to understand the problem. Make a separately named,
read-only backup first, and use a copy for experiments.

## Backups and moving a workspace

Stop the server before copying. Copy the entire data directory, not only the SQLite
file. Preserve file permissions and use encrypted storage:

```bash
python -m traceharbor verify CASE_ID
cp -a ~/.local/share/traceharbor /encrypted/location/traceharbor-backup
```

The copy is not a signed or independently timestamped forensic backup. After moving
it to another device, start TraceHarbor with:

```bash
python -m traceharbor --data-dir /encrypted/location/traceharbor-backup serve
```

Only one server/CLI writer should use a vault at a time. There is no automatic
database migration, merge, cloud backup or restore wizard in v0.1.0.

## Naming and release notes

The working name is **TraceHarbor**. It replaces the earlier **TraceForge** project
name while keeping its original focus: local-first public-source analysis, OCR, EXIF,
hashes, evidence records and responsible research. Before a public production release,
check the name, domain and trademark availability yourself; this repository makes no
exclusivity claim.

## Development and verification

```bash
python -m pip install -e '.[images,dev]'
python -m pytest -q
ruff check traceharbor tests
ruff format --check traceharbor tests
node --check traceharbor/web/app.js
```

Optional full browser smoke test, using **synthetic data in its own temporary vault**:

```bash
npm install
npx playwright install chromium
npm run test:e2e
```

Set `TRACEHARBOR_PYTHON` if your Python executable is not `python3`. The browser suite
checks case creation, training data, finding escaping, file upload, audit checks,
URL/lead helpers, exports, archive/reopen, search, reload persistence and mobile navigation.

**Build verification:** 42 core/API tests passed, including real local OCR; lint and
syntax checks passed. Live browser testing was blocked by the authoring environment's
local-host access restriction; the browser script is included but has not been run
successfully here. See [validation notes](docs/VALIDATION.md). Test results are not a
security audit or forensic certification.

## Project status

See [ROADMAP.md](ROADMAP.md) for planned hardening and extensions. Features on the
roadmap are not claimed as implemented. The MIT license makes the code reusable;
the GitHub repository's public/private visibility is controlled separately by its owner.

Contributions are welcome through [CONTRIBUTING.md](CONTRIBUTING.md). Do not submit
real evidence, credentials or personally identifying case records in issues or PRs.

### Technical references

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Pillow image handling and limits](https://pillow.readthedocs.io/en/stable/reference/Image.html)
- [Python hashlib](https://docs.python.org/3/library/hashlib.html)
- [Tesseract documentation](https://tesseract-ocr.github.io/tessdoc/)

## License

[MIT](LICENSE). The license grants software rights; it does not grant authority to
collect, access or disclose data. 鈥淭raceHarbor鈥� is a working project name; no trademark
clearance or claim of exclusivity is implied.
