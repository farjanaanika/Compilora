
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import subprocess
import tempfile
import uuid
import threading
import time
import queue
from C_compiler.lexer import Lexer, LexerError
from C_compiler.parser import Parser, ParserError
from C_compiler.semantic_analyzer import SemanticAnalyzer, SemanticError
from C_compiler.intermediate_code import (
    IntermediateCodeGenerator,
    IntermediateCodeError
)
from C_compiler.code_generator import CodeGenerator, CodeGeneratorError
from CPP_compiler.lexer import Lexer as CPPLexer
from CPP_compiler.parser import Parser as CPPParser
from CPP_compiler.semantic_analyzer import SemanticAnalyzer as CPPSemanticAnalyzer
from CPP_compiler.intermediate_code import IntermediateCodeGenerator as CPPIntermediateCodeGenerator
from CPP_compiler.code_optimizer import CodeOptimizer as CPPCodeOptimizer
from CPP_compiler.code_generator import CodeGenerator as CPPCodeGenerator
PROJECT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"

TIMEOUT_SECONDS = 5

active_processes = {}


process_lock = threading.Lock()




def read_process_output(process_id, process):
    try:
        while True:
            chunk = process.stdout.read(1)

            if not chunk:
                break

            with process_lock:
                if process_id in active_processes:
                    active_processes[process_id]["output"].append(chunk)

        process.wait()

    finally:
        process.stdout.close()

        with process_lock:
            if process_id in active_processes:
                active_processes[process_id]["finished"] = True

def run_cpp_compiler_phases(source_code):
    tokens = CPPLexer(source_code).tokenize()

    ast = CPPParser(tokens).parse()

    CPPSemanticAnalyzer().analyze(ast)

    intermediate_generator = CPPIntermediateCodeGenerator()

    intermediate_code = intermediate_generator.generate_from_ast(ast)

    optimized_code = CPPCodeOptimizer().optimize(intermediate_code)

    target_code = CPPCodeGenerator().generate(optimized_code)

    return {
        "tokens": tokens,
        "ast": ast,
        "intermediate_code": intermediate_code,
        "optimized_code": optimized_code,
        "target_code": target_code
    }

def create_process_record(process, workdir):
    process_id = str(uuid.uuid4())

    with process_lock:
        active_processes[process_id] = {
            "process": process,
            "workdir": workdir,
            "output": [],
            "finished": False
        }

    return process_id


class CompilerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    
    def launch_program(self, language, code):
        workdir = tempfile.TemporaryDirectory(
            prefix="compilora_"
        )

        directory = Path(workdir.name)

        try:
            if language == "c":
                source = directory / "main.c"
                executable = directory / "main.exe"

                source.write_text(code, encoding="utf-8")

                buffering_code = """
                #include <stdio.h>
                __attribute__((constructor))
                void setup_buffering() {
                    setvbuf(stdout, NULL, _IONBF, 0);
                }
                """

                support_file = directory / "buffering.c"
                support_file.write_text(
                    buffering_code,
                    encoding="utf-8"
                )

                compile_cmd = [
                    "gcc",
                    str(source),
                    str(support_file),
                    "-o",
                    str(executable)
                ]

                run_cmd = [str(executable)]
            elif language == "cpp":
                source = directory / "main.cpp"
                generated_source = directory / "generated.cpp"
                executable = directory / "main.exe"

                source.write_text(
                    code,
                    encoding="utf-8"
                )

                syntax_check = subprocess.run(
                    [
                        "g++",
                        "-fsyntax-only",
                        str(source)
                    ],
                    cwd=directory,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_SECONDS
                )

                if syntax_check.returncode != 0:
                    workdir.cleanup()
                    return None, syntax_check.stderr or syntax_check.stdout

                compiler_result = run_cpp_compiler_phases(code)

                generated_code = compiler_result["target_code"]

                generated_source.write_text(
                    generated_code,
                    encoding="utf-8"
                )

                compile_cmd = [
                    "g++",
                    str(generated_source),
                    "-o",
                    str(executable)
                ]

                run_cmd = [str(executable)]

            else:
                source = directory / "Main.java"

                source.write_text(code, encoding="utf-8")

                compile_cmd = ["javac", str(source)]

                run_cmd = [
                    "java",
                    "-cp",
                    str(directory),
                    "Main"
                ]

            compiled = subprocess.run(
                compile_cmd,
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS
            )

            if compiled.returncode != 0:
                workdir.cleanup()
                return None, compiled.stderr or compiled.stdout

            process = subprocess.Popen(
                run_cmd,
                cwd=directory,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0
            )

            process_id = create_process_record(
                process,
                workdir
            )

            threading.Thread(
                target=read_process_output,
                args=(process_id, process),
                daemon=True
            ).start()

            return process_id, None

        except Exception:
            workdir.cleanup()
            raise

    def send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def start_program(self, language, code):
        process_id = str(uuid.uuid4())

        with tempfile.TemporaryDirectory(prefix="compilora_") as temp:
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

            compiled = subprocess.run(
                compile_cmd,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS
            )

            if compiled.returncode != 0:
                return None, compiled.stderr or compiled.stdout

            return "Compilation successful", None

    
    def do_POST(self):
        if self.path == "/api/start":
            try:
                length = int(
                    self.headers.get("Content-Length", "0")
                )
                request = json.loads(self.rfile.read(length))

                language = request.get("language")
                code = request.get("code", "")

                if language not in ("c", "cpp", "java"):
                    self.send_json(400, {
                        "error": "Invalid language"
                    })
                    return

                if not isinstance(code, str) or not code.strip():
                    self.send_json(400, {
                        "error": "Please enter code"
                    })
                    return

                try:
                    process_id, error = self.launch_program(
                        language,
                        code
                    )
                except subprocess.TimeoutExpired:
                    self.send_json(200, {
                        "status": "error",
                        "output": "Compilation timed out."
                    })
                    return

                if error:
                    self.send_json(200, {
                        "status": "error",
                        "output": error
                    })
                    return

                self.send_json(200, {
                    "status": "success",
                    "process_id": process_id,
                    "output": "Program started.\n"
                })
                return

            except Exception as exc:
                self.send_json(500, {
                    "error": str(exc)
                })
                return

        if self.path == "/api/input":
            try:
                length = int(
                    self.headers.get("Content-Length", "0")
                )
                request = json.loads(self.rfile.read(length))

                process_id = request.get("process_id")
                user_input = request.get("input", "")

                with process_lock:
                    record = active_processes.get(process_id)

                    if not record:
                        self.send_json(404, {
                            "error": "Program not found"
                        })
                        return

                    process = record["process"]

                    if process.poll() is not None:
                        self.send_json(400, {
                            "error": "Program has already finished"
                        })
                        return

                    process.stdin.write(user_input + "\n")
                    process.stdin.flush()

                self.send_json(200, {
                    "status": "success"
                })
                return

            except Exception as exc:
                self.send_json(500, {
                    "error": str(exc)
                })
                return

        self.send_json(404, {
            "error": "Endpoint not found"
        })

    
    def get_program_output(self):
        from urllib.parse import parse_qs, urlparse

        query = parse_qs(urlparse(self.path).query)
        process_id = query.get("process_id", [""])[0]

        with process_lock:
            record = active_processes.get(process_id)

            if not record:
                self.send_json(404, {
                    "status": "error",
                    "output": "Program not found."
                })
                return

            output = "".join(record["output"])
            record["output"].clear()

            process = record["process"]
            finished = process.poll() is not None

            self.send_json(200, {
                "status": "finished" if finished else "running",
                "output": output
            })


    def do_GET(self):
        if self.path.startswith("/api/output"):
            self.get_program_output()
            return
        if self.path == "/api/health":
            self.send_json(200, {
                "status": "ok",
                "message": "Compiler backend is running!"
            })
            return

        if self.path == "/":
            self.path = "/index.html"

        super().do_GET()

if __name__ == "__main__":
    server = ThreadingHTTPServer(
        ("127.0.0.1", 8000),
        CompilerHandler
    )
    print("Compiler server running at http://127.0.0.1:8000")
    print("Press Ctrl+C to stop the server.")
    server.serve_forever()
