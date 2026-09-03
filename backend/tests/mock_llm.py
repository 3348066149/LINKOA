# -*- coding: utf-8 -*-
"""本地 mock LLM，供回归测试免真实 API 调用。

支持 OpenAI 兼容路径：
- /chat/completions：Chat Completions 流式 SSE（data: ... / data: [DONE]）

用法：python tests/mock_llm.py [port]，默认 8899。
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _read_body(handler) -> dict:
    length = int(handler.headers.get("Content-Length", 0))
    raw = handler.rfile.read(length).decode("utf-8", "ignore")
    try:
        return json.loads(raw)
    except Exception:
        return {}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = _read_body(self)
        self._handle_chat_completions(body)

    def _send_sse_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

    def _handle_chat_completions(self, req: dict):
        try:
            prompt = req.get("messages", [{}])[-1].get("content", "")[:20]
        except Exception:
            prompt = "?"
        self._send_sse_headers()
        for piece in ["【mock】", f"收到问题：{prompt}"]:
            data = json.dumps({"choices": [{"delta": {"content": piece}}]}, ensure_ascii=False)
            self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"mock llm on http://127.0.0.1:{port}", flush=True)
    srv.serve_forever()
