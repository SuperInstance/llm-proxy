#!/usr/bin/env python3

import os
import json
import re
import time
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import deque
from datetime import datetime

DEEPINFRA_API_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
MODEL_NAME = "ByteDance/Seed-2.0-mini"
PORT = int(os.environ.get("LLM_PROXY_PORT", 8866))
RATE_LIMIT = 10  # max requests per second
RATE_WINDOW = 1.0  # seconds

request_timestamps = deque()

def get_api_key():
    api_key = os.environ.get("DEEPINFRA_API_KEY", "")
    if not api_key:
        try:
            vault_path = os.path.expanduser("~/.credentials_vault")
            with open(vault_path) as f:
                vault = json.load(f)
                api_key = vault.get("DEEPINFRA_API_KEY", "")
        except Exception:
            pass
    return api_key

def check_rate_limit():
    now = time.time()
    while request_timestamps and now - request_timestamps[0] > RATE_WINDOW:
        request_timestamps.popleft()
    if len(request_timestamps) >= RATE_LIMIT:
        return False
    request_timestamps.append(now)
    return True

def parse_llm_response(response_text):
    try:
        data = json.loads(response_text)
        if "value" in data:
            return float(data["value"])
        if "choices" in data:
            content = data["choices"][0]["message"]["content"]
            match = re.search(r'\{[^}]+\}', content)
            if match:
                inner = json.loads(match.group())
                if "value" in inner:
                    return float(inner["value"])
    except Exception:
        pass
    floats = re.findall(r'-?[\d.]+', response_text)
    if floats:
        return max(-1.0, min(1.0, float(floats[0])))
    return None

def call_deepinfra(prompt):
    api_key = get_api_key()
    if not api_key:
        raise ValueError("DEEPINFRA_API_KEY not found")
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 50,
        "temperature": 0.85
    }
    req = urllib.request.Request(
        DEEPINFRA_API_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode())

class LLMProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[llm_proxy] {datetime.now().isoformat()} {format % args}")

    def send_json_response(self, data, status_code=200):
        response = json.dumps(data).encode()
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_json_response({
                "status": "ok",
                "model": MODEL_NAME,
                "requests_per_second": len(request_timestamps)
            })
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")

    def do_POST(self):
        if not check_rate_limit():
            self.send_json_response({
                "error": "rate_limit_exceeded",
                "message": f"Max {RATE_LIMIT} requests per second"
            }, 429)
            return

        if self.path == "/oracle":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(content_length).decode())
                cell_id = body.get("cell_id", 0)
                tick = body.get("tick", 0)
                value = body.get("value", 0.0)
                neighbors = body.get("neighbors", [])
                phase = body.get("phase", 0.0)

                neighbors_json = json.dumps(neighbors)
                prompt = (
                    f"You are a cell in a spreadsheet simulation. Cell {cell_id} has value {value:.4f}. "
                    f"Neighbors: {neighbors_json}. Phase: {phase:.4f}. "
                    f"Suggest a next value (float, range -1.0 to 1.0) that continues an interesting pattern. "
                    f"Respond with ONLY a JSON object: {{\"value\": <float>}}"
                )

                start_time = time.time()
                response_data = call_deepinfra(prompt)
                latency_ms = int((time.time() - start_time) * 1000)

                content = response_data["choices"][0]["message"]["content"]
                oracle_value = parse_llm_response(content)

                if oracle_value is None:
                    self.send_json_response({
                        "cell_id": cell_id,
                        "tick": tick,
                        "oracle_value": None,
                        "error": "parse_error",
                        "model": MODEL_NAME,
                        "latency_ms": latency_ms
                    }, 500)
                else:
                    self.send_json_response({
                        "cell_id": cell_id,
                        "tick": tick,
                        "oracle_value": oracle_value,
                        "model": MODEL_NAME,
                        "latency_ms": latency_ms
                    })
            except urllib.error.URLError as e:
                self.send_json_response({
                    "error": "api_error",
                    "message": str(e.reason) if hasattr(e, 'reason') else str(e)
                }, 502)
            except TimeoutError:
                self.send_json_response({
                    "error": "timeout"
                }, 504)
            except Exception as e:
                self.send_json_response({
                    "error": "server_error",
                    "message": str(e)
                }, 500)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), LLMProxyHandler)
    print(f"[llm_proxy] Starting server on port {PORT}")
    print(f"[llm_proxy] Model: {MODEL_NAME}")
    print(f"[llm_proxy] Rate limit: {RATE_LIMIT} req/sec")
    server.serve_forever()