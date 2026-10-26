
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import subprocess
import tempfile
import uuid

PROJECT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"

# Maximum time allowed for compilation and execution.
TIMEOUT_SECONDS = 5


class CompilerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            self.send_json(200, {
                "status": "ok",
                "message": "Compiler backend is running!"
            })
            return

        if self.path == "/":
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self):
        if self.path != "/api/run":
            self.send_json(404, {"error": "Endpoint not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 100_000:
                self.send_json(400, {"error": "Invalid request size"})
                return

            request = json.loads(self.rfile.read(length))
            language = request.get("language")
            code = request.get("code", "")
            stdin = request.get("input", "")

            if language not in ("c", "cpp", "java"):
                self.send_json(400, {"error": "Choose C, C++, or Java"})
                return

            if not isinstance(code, str) or not code.strip():
                self.send_json(400, {"error": "Please enter some code"})
                return

            if not isinstance(stdin, str) or len(stdin) > 20_000:
                self.send_json(400, {"error": "Invalid program input"})
                return

            with tempfile.TemporaryDirectory(prefix="my_compiler_") as temp:
                workdir = Path(temp)

                if language == "c":
                    source = workdir / "main.c"
                    executable = workdir / "main.exe"
                    source.write_text(code, encoding="utf-8")

                    compile_cmd = ["gcc", str(source), "-o", str(executable)]
                    run_cmd = [str(executable)]

                elif language == "cpp":
                    source = workdir / "main.cpp"
                    executable = workdir / "main.exe"
                    source.write_text(code, encoding="utf-8")

                    compile_cmd = ["g++", str(source), "-o", str(executable)]
                    run_cmd = [str(executable)]

                else:
                    source = workdir / "Main.java"
                    source.write_text(code, encoding="utf-8")

                    compile_cmd = ["javac", str(source)]
                    run_cmd = ["java", "-cp", str(workdir), "Main"]

                try:
                    compiled = subprocess.run(
                        compile_cmd,
                        cwd=workdir,
                        capture_output=True,
                        text=True,
                        timeout=TIMEOUT_SECONDS
                    )
                except subprocess.TimeoutExpired:
                    self.send_json(200, {
                        "status": "error",
                        "output": "Compilation timed out."
                    })
                    return
                except OSError as exc:
                    self.send_json(200, {
                        "status": "error",
                        "output": f"Could not start compiler: {exc}"
                    })
                    return

                if compiled.returncode != 0:
                    self.send_json(200, {
                        "status": "error",
                        "output": compiled.stderr or compiled.stdout
                    })
                    return

                try:
                    result = subprocess.run(
                        run_cmd,
                        cwd=workdir,
                        input=stdin,
                        capture_output=True,
                        text=True,
                        timeout=TIMEOUT_SECONDS
                    )
                except subprocess.TimeoutExpired:
                    self.send_json(200, {
                        "status": "error",
                        "output": "Program timed out."
                    })
                    return

                output = result.stdout
                if result.stderr:
                    output += result.stderr

                self.send_json(200, {
                    "status": "success" if result.returncode == 0 else "error",
                    "output": output or (
                        "Program finished with no output."
                        if result.returncode == 0
                        else f"Program exited with code {result.returncode}."
                    )
                })

        except (ValueError, json.JSONDecodeError):
            self.send_json(400, {"error": "Invalid JSON request"})
        except Exception as exc:
            self.send_json(500, {"error": f"Server error: {exc}"})


if __name__ == "__main__":
    server = ThreadingHTTPServer(
        ("127.0.0.1", 8000),
        CompilerHandler
    )
    print("Compiler server running at http://127.0.0.1:8000")
    print("Press Ctrl+C to stop the server.")
    server.serve_forever()
