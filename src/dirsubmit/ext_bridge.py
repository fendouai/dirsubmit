"""Chrome 扩展桥：本地 WebSocket 服务器，与 dirsubmit 扩展通信。

扩展（background.js）作为客户端连入本服务器；`dirsubmit` 通过 `call()` 下发
navigate / fill / click / wait 命令，并同步等待扩展返回结果。
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None


class ExtBridge:
    """本地 WebSocket 服务器，等待扩展连入，提供同步 call()。"""

    def __init__(self, host: str = "127.0.0.1", port: int = 8721):
        self.host = host
        self.port = port
        self.conn = None
        self.pending: dict = {}
        self.loop = None
        self._server = None
        self._thread = None
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._startup_error = None

    # ---------- 服务端 ----------

    async def _handler(self, ws):
        request = getattr(ws, "request", None)
        headers = request.headers if request is not None else getattr(ws, "request_headers", {})
        origin = headers.get("Origin", "")
        if not origin.startswith("chrome-extension://"):
            await ws.close(code=1008, reason="Chrome extension origin required")
            return
        if self.conn is not None:
            await ws.close(code=1008, reason="Bridge already has an executor")
            return
        async with ws:
            self.conn = ws
            try:
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    rid = data.get("id")
                    if not rid or rid == "hb":
                        continue  # 心跳，不响应
                    with self._lock:
                        q = self.pending.get(rid)
                    if q is not None:
                        q.put(data)
            finally:
                if self.conn is ws:
                    self.conn = None

    async def _serve(self):
        self._server = await websockets.serve(self._handler, self.host, self.port)

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._serve())
        except Exception as exc:
            self._startup_error = exc
        finally:
            self._ready.set()
        if self._startup_error is None:
            self.loop.run_forever()
        self.loop.close()

    def start(self, wait: float = 15.0) -> bool:
        """启动服务器，并等待扩展连入。返回是否已连上。"""
        if websockets is None:
            raise RuntimeError("扩展模式需要 websockets 库：pip install websockets")
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        if not self._ready.wait(5):
            raise RuntimeError("扩展桥启动超时")
        if self._startup_error:
            raise RuntimeError(f"扩展桥启动失败：{self._startup_error}")
        return self.wait_for_client(wait)

    def wait_for_client(self, timeout: float = 15.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.conn is not None:
                return True
            time.sleep(0.2)
        return False

    def connected(self) -> bool:
        return self.conn is not None

    # ---------- 客户端（dirsubmit 调用） ----------

    def call(self, cmd: str, timeout: float = 30.0, **kwargs) -> dict:
        import queue

        if self.conn is None:
            return {"status": "error", "error": "扩展未连接（浏览器里加载扩展了吗？）"}
        rid = uuid.uuid4().hex
        q = queue.Queue()
        with self._lock:
            self.pending[rid] = q
        payload = {"id": rid, "cmd": cmd, **kwargs}
        try:
            future = asyncio.run_coroutine_threadsafe(self._send(payload), self.loop)
            future.result(timeout=min(timeout, 5))
        except Exception as e:  # noqa: BLE001
            with self._lock:
                self.pending.pop(rid, None)
            return {"status": "error", "error": str(e)}
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return {"status": "error", "error": f"{cmd} 超时（{timeout}s）"}
        finally:
            with self._lock:
                self.pending.pop(rid, None)

    async def _send(self, payload: dict):
        if self.conn is None:
            return
        await self.conn.send(json.dumps(payload))

    def stop(self):
        if self.loop is None or not self.loop.is_running():
            return
        async def shutdown():
            if self._server is not None:
                self._server.close()
                await self._server.wait_closed()
        try:
            asyncio.run_coroutine_threadsafe(shutdown(), self.loop).result(timeout=5)
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            if self._thread is not None:
                self._thread.join(timeout=5)
