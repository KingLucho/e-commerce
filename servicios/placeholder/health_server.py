"""HTTP placeholder used until each FastAPI service is implemented in phase 1."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os


SERVICE_NAME = os.environ.get("SERVICE_NAME", "servicio")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_error(404, "Not Found")
            return

        body = json.dumps({"status": "healthy", "service": SERVICE_NAME}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"[{SERVICE_NAME}] {format_string % args}", flush=True)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), HealthHandler).serve_forever()
