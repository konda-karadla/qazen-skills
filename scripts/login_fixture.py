"""Minimal /login app matching generated QAZen Playwright specs.

Serves Username/Password + Login, Dashboard on valid_user/valid_pass,
and a role=alert on invalid credentials. Used as QAZEN_BASE_URL for S6.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8765

LOGIN_PAGE = b"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Login</title></head>
<body>
  <h1>Login</h1>
  <div id="error" role="alert" hidden>Invalid credentials</div>
  <form id="login-form">
    <label>Username <input name="username" autocomplete="username"></label>
    <label>Password <input name="password" type="password" autocomplete="current-password"></label>
    <button type="submit">Login</button>
  </form>
  <script>
    document.getElementById("login-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const u = e.target.username.value;
      const p = e.target.password.value;
      if (u === "valid_user" && p === "valid_pass") {
        document.body.innerHTML = "<h1>Dashboard</h1>";
        return;
      }
      const err = document.getElementById("error");
      err.hidden = false;
    });
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/", "/login"):
            body = LOGIN_PAGE
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)


def main() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"login fixture http://{HOST}:{PORT}/login", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
