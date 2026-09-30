#!/usr/bin/env python3
"""Native Messaging host, CLI and MCP proxy for Tampermonkey Editors.

The browser extension starts this process through Native Messaging. The
process then exposes a token-protected loopback HTTP endpoint. The endpoint is
intentionally local-only; script operations still pass through the extension
and Tampermonkey's existing permission checks.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import secrets
import shlex
import signal
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


HOST_NAME = "com.ctyx.tampermonkey_bridge"
PROTOCOL_VERSION = 1
BRIDGE_VERSION = "0.1.0"
MAX_NATIVE_MESSAGE_BYTES = 4 * 1024 * 1024
MAX_HTTP_BODY_BYTES = 8 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 60
EXTENSION_ACTIONS = {"list", "get", "patch", "put", "delete"}


def state_directory() -> Path:
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Tampermonkey Bridge"
    if platform.system() == "Windows":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Tampermonkey Bridge"
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "tampermonkey-bridge"


def state_path() -> Path:
    return state_directory() / "state.json"


def lock_path() -> Path:
    return state_directory() / "bridge.lock"


def native_launcher_path() -> Path:
    return state_directory() / "native-host"


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class SingleInstance:
    """Keep accidental duplicate native hosts from serving two bridge states."""

    def __init__(self, path: Path):
        self.path = path
        self.handle = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+")
        try:
            import fcntl

            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:
            # Native Messaging is primarily tested on macOS/Linux. On a
            # platform without flock, exclusive creation still avoids the
            # common duplicate-start case.
            try:
                self.handle.seek(0)
                self.handle.truncate()
                self.handle.write(str(os.getpid()))
                self.handle.flush()
            except OSError:
                self.release()
                return False
        except OSError:
            # A held advisory lock means another native host already owns the
            # bridge. Never overwrite its PID or create a second endpoint.
            self.release()
            return False
        self.handle.seek(0)
        self.handle.truncate()
        self.handle.write(str(os.getpid()))
        self.handle.flush()
        return True

    def release(self) -> None:
        if self.handle is None:
            return
        try:
            import fcntl

            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        except (ImportError, OSError):
            pass
        self.handle.close()
        self.handle = None


def read_native_message(stream) -> dict[str, Any] | None:
    header = stream.buffer.read(4)
    if not header:
        return None
    if len(header) != 4:
        raise RuntimeError("native message header is truncated")
    length = int.from_bytes(header, "little")
    if length <= 0 or length > MAX_NATIVE_MESSAGE_BYTES:
        raise RuntimeError(f"invalid native message length: {length}")
    payload = stream.buffer.read(length)
    if len(payload) != length:
        raise RuntimeError("native message payload is truncated")
    return json.loads(payload.decode("utf-8"))


def write_native_message(stream, message: dict[str, Any], lock: threading.Lock) -> None:
    payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(payload) > MAX_NATIVE_MESSAGE_BYTES:
        raise RuntimeError("native message is too large")
    with lock:
        stream.buffer.write(len(payload).to_bytes(4, "little"))
        stream.buffer.write(payload)
        stream.buffer.flush()


class Bridge:
    def __init__(self, stdin, stdout, instance: SingleInstance):
        self.stdin = stdin
        self.stdout = stdout
        self.instance = instance
        self.write_lock = threading.Lock()
        self.pending: dict[str, tuple[threading.Event, dict[str, Any] | None]] = {}
        self.pending_lock = threading.Lock()
        self.closed = threading.Event()
        self.token = secrets.token_urlsafe(32)
        self.http_server: ThreadingHTTPServer | None = None
        self.http_thread: threading.Thread | None = None
        self.extension_id = ""
        self.cleaned = False

    def start(self, hello: dict[str, Any]) -> None:
        if hello.get("type") != "hello" or hello.get("protocol") != PROTOCOL_VERSION:
            raise RuntimeError("unsupported native bridge handshake")
        extension_id = hello.get("extensionId")
        if not isinstance(extension_id, str) or not re.fullmatch(r"[a-p]{32}", extension_id):
            raise RuntimeError("invalid extension id in native bridge handshake")
        self.extension_id = extension_id

        handler = self.make_http_handler()
        self.http_server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.http_server.daemon_threads = True
        self.http_thread = threading.Thread(target=self.http_server.serve_forever, name="tm-bridge-http", daemon=True)
        self.http_thread.start()
        port = self.http_server.server_address[1]
        write_json(
            state_path(),
            {
                "hostName": HOST_NAME,
                "pid": os.getpid(),
                "extensionId": extension_id,
                "port": port,
                "token": self.token,
                "mcpUrl": f"http://127.0.0.1:{port}/mcp",
                "startedAt": int(time.time()),
            },
        )
        write_native_message(
            self.stdout,
            {"type": "ready", "protocol": PROTOCOL_VERSION, "bridgeVersion": BRIDGE_VERSION},
            self.write_lock,
        )

    def send_request(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.closed.is_set():
            raise RuntimeError("native bridge is closed")
        request_id = uuid.uuid4().hex
        event = threading.Event()
        with self.pending_lock:
            self.pending[request_id] = (event, None)
        payload = {
            "type": "request",
            "id": request_id,
            "request": {"method": "userscripts", **request, "messageId": request_id},
        }
        try:
            write_native_message(self.stdout, payload, self.write_lock)
            if not event.wait(REQUEST_TIMEOUT_SECONDS):
                raise TimeoutError("Tampermonkey request timed out")
            with self.pending_lock:
                result = self.pending[request_id][1]
            if result is None:
                raise RuntimeError("Tampermonkey returned no response")
            return result
        finally:
            with self.pending_lock:
                self.pending.pop(request_id, None)

    def receive(self, message: dict[str, Any]) -> None:
        if message.get("type") != "response":
            return
        request_id = message.get("id")
        if not isinstance(request_id, str):
            return
        with self.pending_lock:
            pending = self.pending.get(request_id)
            if pending is None:
                return
            event, _ = pending
            self.pending[request_id] = (event, message.get("response"))
            event.set()

    def run(self, hello: dict[str, Any]) -> None:
        self.start(hello)
        try:
            while not self.closed.is_set():
                message = read_native_message(self.stdin)
                if message is None:
                    break
                self.receive(message)
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        if self.cleaned:
            return
        self.cleaned = True
        self.closed.set()
        if self.http_server is not None:
            self.http_server.shutdown()
            self.http_server.server_close()
        try:
            state_path().unlink(missing_ok=True)
        except OSError:
            pass
        self.instance.release()

    def make_http_handler(self):
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "TampermonkeyBridge/" + BRIDGE_VERSION

            def log_message(self, format: str, *args: Any) -> None:
                print("[tm-bridge] " + (format % args), file=sys.stderr)

            def send_json(self, status: int, value: Any, extra_headers: dict[str, str] | None = None) -> None:
                payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                if extra_headers:
                    for key, value in extra_headers.items():
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(payload)

            def authorized(self) -> bool:
                expected = "Bearer " + bridge.token
                return self.headers.get("Authorization") == expected

            def do_OPTIONS(self) -> None:  # noqa: N802
                self.send_response(204)
                self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, MCP-Session-Id")
                self.send_header("Access-Control-Allow-Methods", "POST, GET, DELETE, OPTIONS")
                self.end_headers()

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/health":
                    self.send_json(200, {"ok": True, "bridgeVersion": BRIDGE_VERSION, "pid": os.getpid()})
                    return
                self.send_json(404, {"error": "not found"})

            def do_DELETE(self) -> None:  # noqa: N802
                if self.path.startswith("/mcp") and self.authorized():
                    self.send_json(200, {"ok": True})
                    return
                self.send_json(401, {"error": "unauthorized"})

            def do_POST(self) -> None:  # noqa: N802
                if not self.authorized():
                    self.send_json(401, {"error": "unauthorized"})
                    return
                if self.path == "/api/userscripts":
                    self.handle_api()
                    return
                if self.path.startswith("/mcp"):
                    self.handle_mcp()
                    return
                self.send_json(404, {"error": "not found"})

            def read_body(self) -> dict[str, Any]:
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError as exc:
                    raise ValueError("invalid content length") from exc
                if length <= 0 or length > MAX_HTTP_BODY_BYTES:
                    raise ValueError("invalid request body size")
                return json.loads(self.rfile.read(length).decode("utf-8"))

            def handle_api(self) -> None:
                try:
                    request = self.read_body()
                    action = request.get("action")
                    if action not in EXTENSION_ACTIONS:
                        raise ValueError("unsupported userscript action")
                    response = bridge.send_request({key: value for key, value in request.items() if key != "messageId"})
                    self.send_json(200, response)
                except (ValueError, RuntimeError, TimeoutError, json.JSONDecodeError) as exc:
                    self.send_json(400, {"error": str(exc)})

            def handle_mcp(self) -> None:
                try:
                    message = self.read_body()
                    response = mcp_dispatch(bridge, message)
                    if response is None:
                        self.send_response(202)
                        self.end_headers()
                        return
                    self.send_json(
                        200,
                        response,
                        {"MCP-Protocol-Version": "2025-06-18", "Mcp-Session-Id": "tm-bridge"},
                    )
                except (ValueError, RuntimeError, TimeoutError, json.JSONDecodeError) as exc:
                    self.send_json(400, {"error": str(exc)})

        return Handler


def mcp_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "tampermonkey_list",
            "description": "列出当前 Tampermonkey 中可访问的 userscript。",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "tampermonkey_get",
            "description": "读取一个 userscript 的完整源码。",
            "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        },
        {
            "name": "tampermonkey_patch",
            "description": "按 path 更新一个已有 userscript；value 必须是完整源码。",
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "value": {"type": "string"}, "lastModified": {"type": "number"}},
                "required": ["path", "value"],
            },
        },
        {
            "name": "tampermonkey_put",
            "description": "创建一个 userscript；value 必须包含完整 metadata block。",
            "inputSchema": {"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]},
        },
        {
            "name": "tampermonkey_delete",
            "description": "删除一个 userscript。调用前应先备份并确认 path。",
            "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        },
    ]


def jsonrpc_error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def mcp_dispatch(bridge: Bridge, message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    message_id = message.get("id")
    if not isinstance(method, str):
        return jsonrpc_error(message_id, -32600, "invalid JSON-RPC request")
    if method.startswith("notifications/"):
        return None
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "tampermonkey-native-bridge", "version": BRIDGE_VERSION},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": message_id, "result": {"tools": mcp_tools()}}
    if method != "tools/call":
        return jsonrpc_error(message_id, -32601, f"method not found: {method}")

    params = message.get("params") or {}
    name = params.get("name")
    arguments = params.get("arguments") or {}
    tool_to_action = {
        "tampermonkey_list": "list",
        "tampermonkey_get": "get",
        "tampermonkey_patch": "patch",
        "tampermonkey_put": "put",
        "tampermonkey_delete": "delete",
    }
    action = tool_to_action.get(name)
    if action is None:
        return jsonrpc_error(message_id, -32602, f"unknown tool: {name}")
    try:
        result = bridge.send_request({"action": action, **arguments})
        is_error = "error" in result
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                "isError": is_error,
                "structuredContent": result,
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            },
        }
    except (RuntimeError, TimeoutError) as exc:
        return jsonrpc_error(message_id, -32000, str(exc))


def http_request(path: str, payload: dict[str, Any] | None = None) -> Any:
    state = read_json(state_path())
    url = f"http://127.0.0.1:{int(state['port'])}{path}"
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib_request.Request(
        url,
        data=data,
        headers={"Authorization": "Bearer " + str(state["token"]), "Content-Type": "application/json"},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib_request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"bridge HTTP {exc.code}: {body}") from exc


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def run_cli(args: argparse.Namespace) -> int:
    if args.command == "status":
        if not state_path().exists():
            print_json({"running": False})
            return 1
        try:
            state = read_json(state_path())
            health = http_request("/health")
            print_json({"running": True, **{key: value for key, value in state.items() if key != "token"}, "health": health})
            return 0
        except (OSError, ValueError, KeyError, RuntimeError, urllib_error.URLError) as exc:
            print_json({"running": False, "error": str(exc)})
            return 1

    if args.command in {"list", "get", "patch", "put", "delete"}:
        payload: dict[str, Any] = {"action": args.command}
        if getattr(args, "path", None) is not None:
            payload["path"] = args.path
        if getattr(args, "value", None) is not None:
            payload["value"] = Path(args.value).read_text(encoding="utf-8") if args.value_file else args.value
        if getattr(args, "last_modified", None) is not None:
            payload["lastModified"] = args.last_modified
        print_json(http_request("/api/userscripts", payload))
        return 0

    if args.command == "mcp-stdio":
        for line in sys.stdin:
            if not line.strip():
                continue
            message = json.loads(line)
            response = http_request("/mcp", message)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
        return 0

    if args.command == "print-mcp-config":
        state = read_json(state_path())
        print_json(
            {
                "mcpServers": {
                    "tampermonkey-native-bridge": {
                        "command": str(Path(__file__).resolve()),
                        "args": ["mcp-stdio"],
                        "env": {},
                    }
                },
                "http": {"url": state.get("mcpUrl"), "tokenFile": str(state_path())},
            }
        )
        return 0

    raise RuntimeError("unsupported command")


def native_host() -> int:
    instance = SingleInstance(lock_path())
    if not instance.acquire():
        write_native_message(sys.stdout, {"type": "error", "message": "native bridge is already running"}, threading.Lock())
        return 2
    bridge: Bridge | None = None

    def stop(_signum, _frame) -> None:
        if bridge is not None:
            bridge.cleanup()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    try:
        hello = read_native_message(sys.stdin)
        if hello is None:
            return 1
        bridge = Bridge(sys.stdin, sys.stdout, instance)
        bridge.run(hello)
        return 0
    except Exception as exc:  # Native Messaging requires diagnostics on stderr.
        print(f"[tm-bridge] {exc}", file=sys.stderr)
        try:
            write_native_message(sys.stdout, {"type": "error", "message": str(exc)}, threading.Lock())
        except Exception:
            pass
        instance.release()
        return 1


def install_host(args: argparse.Namespace) -> int:
    if not re.fullmatch(r"[a-p]{32}", args.extension_id):
        raise ValueError("extension id must be 32 lowercase letters from a-p")
    browser_paths = {
        "edge": {
            "darwin": Path.home() / "Library" / "Application Support" / "Microsoft Edge" / "NativeMessagingHosts",
            "linux": Path.home() / ".config" / "microsoft-edge" / "NativeMessagingHosts",
        },
        "chrome": {
            "darwin": Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "NativeMessagingHosts",
            "linux": Path.home() / ".config" / "google-chrome" / "NativeMessagingHosts",
        },
    }
    system = "darwin" if platform.system() == "Darwin" else "linux"
    if args.browser not in browser_paths or system not in browser_paths[args.browser]:
        raise RuntimeError("automatic host registration currently supports Chrome/Edge on macOS and Linux")
    destination = browser_paths[args.browser][system] / (HOST_NAME + ".json")
    launcher = native_launcher_path()
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(
        "#!/bin/sh\n"
        f"exec {shlex.quote(str(Path(sys.executable).resolve()))} "
        f"{shlex.quote(str(Path(__file__).resolve()))}\n",
        encoding="utf-8",
    )
    launcher.chmod(0o700)

    manifest = {
        "name": HOST_NAME,
        "description": "Local Tampermonkey Editors bridge",
        "path": str(launcher),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{args.extension_id}/"],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_json(destination, manifest)
    print_json({"installed": True, "browser": args.browser, "manifest": str(destination), "host": manifest})
    return 0


def uninstall_host(args: argparse.Namespace) -> int:
    browser_paths = {
        "edge": {
            "darwin": Path.home() / "Library" / "Application Support" / "Microsoft Edge" / "NativeMessagingHosts",
            "linux": Path.home() / ".config" / "microsoft-edge" / "NativeMessagingHosts",
        },
        "chrome": {
            "darwin": Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "NativeMessagingHosts",
            "linux": Path.home() / ".config" / "google-chrome" / "NativeMessagingHosts",
        },
    }
    system = "darwin" if platform.system() == "Darwin" else "linux"
    destination = browser_paths[args.browser][system] / (HOST_NAME + ".json")
    destination.unlink(missing_ok=True)
    print_json({"uninstalled": True, "manifest": str(destination)})
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Tampermonkey Editors native bridge CLI")
    subparsers = result.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    subparsers.add_parser("list")
    get = subparsers.add_parser("get")
    get.add_argument("path")
    for name in ("patch", "put"):
        command = subparsers.add_parser(name)
        command.add_argument("value", help="源码文本，或配合 --value-file 使用的文件路径")
        command.add_argument("--value-file", action="store_true")
        if name == "patch":
            command.add_argument("--path", required=True)
            command.add_argument("--last-modified", type=int)
    delete = subparsers.add_parser("delete")
    delete.add_argument("path")
    subparsers.add_parser("mcp-stdio")
    subparsers.add_parser("print-mcp-config")
    install = subparsers.add_parser("install-host")
    install.add_argument("--browser", choices=("edge", "chrome"), required=True)
    install.add_argument("--extension-id", required=True)
    uninstall = subparsers.add_parser("uninstall-host")
    uninstall.add_argument("--browser", choices=("edge", "chrome"), required=True)
    return result


def main() -> int:
    if len(sys.argv) == 1:
        return native_host()
    args = parser().parse_args()
    if args.command == "install-host":
        return install_host(args)
    if args.command == "uninstall-host":
        return uninstall_host(args)
    return run_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
