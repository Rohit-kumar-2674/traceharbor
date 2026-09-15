"""Loopback-only FastAPI service. Secrets never appear in request URLs or logs."""

import base64
import binascii
import hmac
import secrets
import threading
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from . import __version__
from .analysis import MAX_FILE_BYTES, analyze_bytes, capabilities, compare_analyses, inspect_url, public_leads
from .reports import export_case
from .store import Store

MAX_REQUEST_BYTES = 14 * 1024 * 1024
WEB = Path(__file__).parent / "web"
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class SecurityGate:
    def __init__(self, app, token, port):
        self.app, self.token = app, token
        self.hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin1").lower(): v.decode("latin1") for k, v in scope["headers"]}

        async def secured_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [
                    (k.lower().encode(), v.encode()) for k, v in SECURITY_HEADERS.items()
                ]
            await send(message)

        async def reject(code, detail):
            return await JSONResponse({"detail": detail}, status_code=code)(scope, receive, secured_send)

        if headers.get("host") not in self.hosts:
            return await reject(403, "Only the configured loopback host is allowed.")
        origin = headers.get("origin")
        if origin and origin not in {f"http://{host}" for host in self.hosts}:
            return await reject(403, "Cross-origin requests are not accepted.")
        if headers.get("sec-fetch-site") == "cross-site":
            return await reject(403, "Cross-site requests are not accepted.")
        if scope["path"].startswith("/api/") and scope["path"] != "/api/health":
            auth = headers.get("authorization", "")
            if not hmac.compare_digest(auth.encode("utf-8"), f"Bearer {self.token}".encode("utf-8")):
                return await reject(401, "Unlock this workspace using the link printed in your terminal.")
        if scope["method"] in {"POST", "PUT", "PATCH"}:
            if headers.get("content-type", "").split(";")[0] != "application/json":
                return await reject(415, "Send application/json.")
            try:
                declared = int(headers.get("content-length", "0"))
                if declared < 0 or declared > MAX_REQUEST_BYTES:
                    return await reject(413, "Request exceeds the 14 MiB limit.")
            except ValueError:
                return await reject(400, "Invalid Content-Length.")
            chunks, total = [], 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > MAX_REQUEST_BYTES:
                    return await reject(413, "Request exceeds the 14 MiB limit.")
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break
            body = b"".join(chunks)
            delivered = False

            async def buffered_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()

            return await self.app(scope, buffered_receive, secured_send)
        return await self.app(scope, receive, secured_send)


def decode_file(payload):
    value = payload.get("data_base64")
    if not isinstance(value, str) or len(value) > ((MAX_FILE_BYTES + 2) // 3) * 4:
        raise ValueError("Supply a base64 file of at most 10 MiB.")
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Invalid base64 file.") from None


async def read_json(request):
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError
        return payload
    except (ValueError, UnicodeError):
        raise ValueError("Send a valid JSON object.") from None


def make_app(directory, token=None, port=8742):
    token = token or secrets.token_urlsafe(32)
    store = Store(directory)
    app = FastAPI(title="TraceHarbor", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store, app.state.token = store, token
    app.add_middleware(SecurityGate, token=token, port=port)
    analysis_slots = threading.BoundedSemaphore(2)

    @app.exception_handler(ValueError)
    async def invalid(_request, error):
        return JSONResponse({"detail": str(error)}, status_code=400)

    @app.exception_handler(KeyError)
    async def missing(_request, _error):
        return JSONResponse({"detail": "Record not found."}, status_code=404)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": __version__}

    @app.get("/api/status")
    def status():
        return {"version": __version__, "capabilities": capabilities(), "mode": "local-single-user"}

    @app.get("/api/cases")
    def cases():
        return {"cases": store.list_cases()}

    @app.post("/api/cases", status_code=201)
    async def create_case(request: Request):
        return store.create_case(await read_json(request))

    @app.get("/api/cases/{case_id}")
    def case(case_id: str):
        return store.get_case(case_id)

    @app.patch("/api/cases/{case_id}")
    async def update_case(case_id: str, request: Request):
        return store.change_status(case_id, (await read_json(request)).get("status"))

    # Blocking image processing is explicitly placed in the worker pool.
    async def analyse_in_worker(function):
        from starlette.concurrency import run_in_threadpool

        if not analysis_slots.acquire(blocking=False):
            return JSONResponse(
                {"detail": "Two analyses are already running. Try again shortly."}, status_code=429
            )
        try:
            return await run_in_threadpool(function)
        finally:
            analysis_slots.release()

    @app.post("/api/analyze")
    async def analyze(request: Request):
        payload = await read_json(request)
        filename = payload.get("filename", "evidence.bin")
        if not isinstance(filename, str) or len(filename) > 300:
            raise ValueError("Invalid filename.")
        data = decode_file(payload)
        return await analyse_in_worker(lambda: analyze_bytes(data, filename, payload.get("ocr") is True))

    @app.post("/api/cases/{case_id}/entries", status_code=201)
    async def add_entry(case_id: str, request: Request):
        payload = await read_json(request)
        data = decode_file(payload) if payload.get("kind") == "file" else None
        if data is not None:
            filename = payload.get("filename", "evidence.bin")
            if not isinstance(filename, str) or len(filename) > 300:
                raise ValueError("Invalid filename.")
        return await analyse_in_worker(
            lambda: store.add_entry(case_id, payload, data, payload.get("ocr") is True)
        )

    @app.get("/api/entries/{entry_id}/original")
    def original(entry_id: str):
        return Response(
            store.read_original(entry_id),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{entry_id}.bin"'},
        )

    @app.get("/api/cases/{case_id}/verify")
    def verify(case_id: str):
        return store.verify(case_id)

    @app.get("/api/cases/{case_id}/export")
    def export(case_id: str, originals: bool = False):
        return Response(
            export_case(store, case_id, originals),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="traceharbor-{case_id[:8]}.zip"'},
        )

    @app.post("/api/inspect-url")
    async def url_inspector(request: Request):
        return inspect_url((await read_json(request)).get("url"))

    @app.post("/api/public-leads")
    async def leads(request: Request):
        return public_leads((await read_json(request)).get("username"))

    @app.post("/api/compare")
    async def compare(request: Request):
        payload = await read_json(request)
        left, right = store.get_entry(payload.get("left")), store.get_entry(payload.get("right"))
        if left["kind"] != "file" or right["kind"] != "file":
            raise ValueError("Choose two file records.")
        if left["case_id"] != right["case_id"]:
            raise ValueError("Compare files within the same case.")
        store.read_original(left["id"])
        store.read_original(right["id"])
        return compare_analyses(left["analysis"], right["analysis"])

    @app.get("/api/schema")
    def schema():
        return app.openapi()

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html")

    @app.get("/{asset}")
    def asset(asset: str):
        if asset not in {"app.js", "style.css", "mark.svg"}:
            return JSONResponse({"detail": "Not found"}, status_code=404)
        return FileResponse(WEB / asset)

    return app
