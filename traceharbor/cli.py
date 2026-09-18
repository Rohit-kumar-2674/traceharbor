"""Terminal interface, with no shell execution and no remote bind option."""

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

from . import __version__
from .analysis import MAX_FILE_BYTES, analyze_bytes, capabilities, inspect_url
from .reports import export_case
from .store import Store
from .verification import verify_export


def default_directory():
    return os.environ.get("TRACEHARBOR_DATA_DIR", str(Path.home() / ".local" / "share" / "traceharbor"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="TraceHarbor — evidence before inference.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--data-dir", default=default_directory(), help="Private local case storage directory"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Start the loopback-only browser workspace")
    serve.add_argument("--port", type=int, default=8742)
    commands.add_parser("doctor", help="Check optional analysis capabilities")
    analyze = commands.add_parser("analyze", help="Analyse a local file without retaining it")
    analyze.add_argument("file", type=Path)
    analyze.add_argument("--ocr", action="store_true")
    inspect = commands.add_parser("inspect-url", help="Inspect URL syntax offline")
    inspect.add_argument("url")
    commands.add_parser("cases", help="List local cases as JSON")
    create = commands.add_parser("create-case", help="Create a case with a documented purpose")
    create.add_argument("title")
    create.add_argument("--purpose", required=True)
    create.add_argument("--analyst", default="Local analyst")
    add = commands.add_parser("add-file", help="Preserve and analyse a file in a case")
    add.add_argument("case_id")
    add.add_argument("file", type=Path)
    add.add_argument("--source-url", default="")
    add.add_argument("--notes", default="")
    add.add_argument("--ocr", action="store_true")
    verify = commands.add_parser("verify", help="Verify local records, originals and audit linkage")
    verify.add_argument("case_id")
    export = commands.add_parser("export", help="Create a report ZIP (never overwrites a file)")
    export.add_argument("case_id")
    export.add_argument("--output", required=True, type=Path)
    export.add_argument("--include-originals", action="store_true")
    verify_archive = commands.add_parser(
        "verify-export", help="Check export ZIP checksums without extraction"
    )
    verify_archive.add_argument("archive", type=Path)
    args = parser.parse_args(argv)

    def load_file():
        if args.file.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("File exceeds the 10 MiB limit.")
        return args.file.read_bytes()

    try:
        if args.command == "doctor":
            result = {
                "version": __version__,
                "python": sys.version.split()[0],
                "capabilities": capabilities(),
            }
        elif args.command == "serve":
            if not 1024 <= args.port <= 65535:
                raise ValueError("Choose a port between 1024 and 65535.")
            import uvicorn

            from .server import make_app

            token = secrets.token_urlsafe(32)
            app = make_app(args.data_dir, token, args.port)
            print(
                f"\nTraceHarbor {__version__} · local single-user workspace\n"
                f"Open this private session link in your browser:\n"
                f"http://127.0.0.1:{args.port}/#token={token}\n\n"
                "Do not share this link. The key expires when the server stops.\n"
                "Data is not encrypted at rest. Do not expose this server to a network.\n",
                flush=True,
            )
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=args.port,
                access_log=False,
                limit_concurrency=12,
                timeout_keep_alive=5,
                proxy_headers=False,
            )
            return
        elif args.command == "analyze":
            result = analyze_bytes(load_file(), args.file.name, args.ocr)
        elif args.command == "inspect-url":
            result = inspect_url(args.url)
        elif args.command == "verify-export":
            result = verify_export(args.archive)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["valid"] else 2
        else:
            store = Store(args.data_dir)
            if args.command == "cases":
                result = store.list_cases()
            elif args.command == "create-case":
                result = store.create_case(vars(args))
            elif args.command == "add-file":
                result = store.add_entry(
                    args.case_id,
                    {
                        "kind": "file",
                        "title": args.file.name,
                        "filename": args.file.name,
                        "source_url": args.source_url,
                        "body": args.notes,
                    },
                    load_file(),
                    args.ocr,
                )
            elif args.command == "verify":
                result = store.verify(args.case_id)
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0 if result["valid"] else 2
            elif args.command == "export":
                data = export_case(store, args.case_id, args.include_originals)
                with args.output.open("xb") as handle:
                    handle.write(data)
                result = {
                    "export": str(args.output),
                    "bytes": len(data),
                    "includes_originals": args.include_originals,
                }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(f"TraceHarbor: {exc}", file=sys.stderr)
        return 2
    except ImportError:
        print('Install dependencies with: python -m pip install ".[images]"', file=sys.stderr)
        return 2
