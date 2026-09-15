# Installation

## Desktop Linux / Ubuntu / Debian

Install Python 3.10+ and a virtual environment. For complete image/OCR support:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git tesseract-ocr tesseract-ocr-eng
git clone https://github.com/Rohit-kumar-2674/traceharbor.git
cd traceharbor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps .
python -m traceharbor doctor
python -m traceharbor serve
```

Open the exact private session link from the terminal. Requests must use
`127.0.0.1` or `localhost` on the configured port. There is deliberately no remote
bind option. Keep your terminal session running.

The repository may be private. Use your normally configured GitHub authentication,
or use **Code → Download ZIP** while signed in, extract it, and start at `cd traceharbor`.

## Android with Termux and proot Debian

Use your existing proot Debian environment. These commands are for the **Debian
terminal**, not native Termux. A native Termux installation is not currently
validated; some Python binary dependencies can require additional build tools there.

If Debian is already installed, enter it from Termux:

```bash
proot-distro login debian
```

Inside Debian (usually a root session, so no `sudo`):

```bash
apt update
apt install python3 python3-venv python3-pip git tesseract-ocr tesseract-ocr-eng
git clone https://github.com/Rohit-kumar-2674/traceharbor.git
cd traceharbor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps .
python -m traceharbor doctor
python -m traceharbor serve
```

Open the printed localhost link in your phone's browser. Do not close Termux while
using the workspace. Android may stop background processes; if the server restarts,
use the new session link. Existing cases remain in the configured data directory.

No Node, npm, Vite, Rollup or JavaScript compilation is needed for normal use.
Low-memory phones should use small image files; the 10 MiB upload limit is a ceiling,
not a recommended file size.

Do not upgrade Termux's system pip using `pip install --upgrade pip`; the commands
above use Debian and an isolated Python virtual environment instead.

## OCR status

```bash
tesseract --version
tesseract --list-langs
python -m traceharbor doctor
```

The current interface requests English (`eng`). Other languages are future work.
If Tesseract is missing, install it with your OS package manager; core case and hash
functions remain usable.

## Updates

Preserve your data directory and back it up securely before updating. Stop the server.
For an unmodified Git checkout, pull the reviewed release changes, activate the virtual
environment, and reinstall dependencies and the package:

```bash
git pull --ff-only
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps .
```

This version has no automated schema migration or restore workflow. Do not try to
merge two SQLite databases manually.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Connection refused | Confirm the server is still running, and use the printed port |
| Locked after restart | Open the newly printed session link; keys are intentionally rotated |
| Missing image support | Install the locked requirements inside the active virtual environment |
| OCR unavailable/failed | Check Tesseract and the English language data |
| Port in use | Run `python -m traceharbor serve --port 8743` and use the new printed URL |
| Integrity check fails | Stop adding evidence; preserve the affected vault for review; do not overwrite it |
| Clone asks for login | The repository is private; use your GitHub authentication or download its ZIP |

Do not post session keys, case exports or unredacted terminal output in support issues.
