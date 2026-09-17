#!/usr/bin/env python3
"""Run a bounded compiler scenario and assert its observable result."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    spec = json.loads(Path(sys.argv[1]).read_text())
    compiler = os.environ.get("DRPERF_CC", spec["compiler"])
    resolved = shutil.which(compiler)
    if not resolved:
        raise SystemExit(f"required compiler not found: {compiler}")
    suffix = ".ll" if spec["phase"] == "ir-parsing" else (".c" if "-x" in spec["flags"] and spec["flags"][spec["flags"].index("-x") + 1] == "c" else ".cpp")
    with tempfile.TemporaryDirectory(prefix="drperf-cf-test-") as tmp:
        for item in spec.get("fixtures", [{"size": 1, "source": spec["fixture"]}]):
            if spec.get("harness_status") == "missing-custom-syntax-tree-harness":
                raise SystemExit("this pinned library target has no command-line syntax-tree harness; build a small client of clangToolingSyntax")
            source = Path(tmp) / (f"fixture_{item['size']}" + suffix)
            source.write_text(item["source"])
            flags = list(spec["flags"])
            command = None
            if spec["scenario"] == "code-completion":
                line = next(i for i, x in enumerate(item["source"].splitlines(), 1) if "__COMPLETE__" in x)
                col = item["source"].splitlines()[line - 1].index("__COMPLETE__") + 1
                flags = ["-fsyntax-only", "-x", "c++", "-std=c++20", "-Xclang", f"-code-completion-at={source}:{line}:{col}"]
            elif spec["phase"] == "formatting":
                flags = ["--style=LLVM"]
            elif spec["phase"] == "ir-parsing":
                flags = ["-S", "-x", "ir", "-o", "-"]
            elif spec["phase"] == "serialization":
                pch = Path(tmp) / f"fixture_{item['size']}.pch"
                write = subprocess.run([resolved, "-x", "c++-header", "-std=c++20", str(source), "-o", str(pch)],
                                       text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
                if write.returncode != 0:
                    raise SystemExit(f"PCH write failed at size {item['size']}\n{write.stderr}")
                consumer = Path(tmp) / f"consumer_{item['size']}.cpp"
                consumer.write_text("int pch_consumer;\n")
                command = [resolved, "-fsyntax-only", "-std=c++20", "-include-pch", str(pch), str(consumer)]
            elif Path(resolved).name == "clang-check":
                flags = ["--ast-dump", str(source), "--", "-std=c++20"]
            elif Path(resolved).name == "clang-scan-deps":
                database = Path(tmp) / "compile_commands.json"
                database.write_text(json.dumps([{"directory": tmp, "file": str(source), "command": f"clang++ -std=c++20 -c {source}"}]))
                flags = ["-compilation-database", tmp]
            elif Path(resolved).name == "clang-import-test":
                expression = Path(tmp) / f"expression_{item['size']}.cpp"
                expression.write_text("void imported_expression() {}\n")
                flags = ["-import", str(source), "-expression", str(expression)]
            no_trailing_source = {"clang-check", "clang-scan-deps", "clang-import-test"}
            if command is None:
                command = [resolved, *flags] if Path(resolved).name in no_trailing_source else [resolved, *flags, str(source)]
            result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            if result.returncode != 0:
                raise SystemExit(f"tool failed at size {item['size']} ({result.returncode})\n{result.stderr}")
            expected = "COMPLETION:" if spec["scenario"] == "code-completion" else spec.get("expected_stdout", "")
            combined = result.stdout + result.stderr
            if expected and expected not in combined:
                raise SystemExit(f"missing expected output at size {item['size']}: {expected!r}")
            if spec["phase"] == "ir-parsing" and "fold_" not in result.stdout:
                raise SystemExit(f"parsed IR function missing from assembly at size {item['size']}")
            if spec["scenario"] == "code-completion":
                for candidate in ("alpha", "beta", "method", f"field_{item['size'] - 1}"):
                    if candidate not in combined:
                        raise SystemExit(f"missing completion candidate at size {item['size']}: {candidate}")
            if spec["phase"] == "formatting":
                if not result.stdout.strip():
                    raise SystemExit(f"empty formatter output at size {item['size']}")
                second = subprocess.run([resolved, "--style=LLVM"], input=result.stdout, text=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
                if second.returncode or second.stdout != result.stdout:
                    raise SystemExit(f"formatter was not idempotent at size {item['size']}")
            if spec["scenario"] == "preprocess-macros" and "MUL_" in result.stdout:
                raise SystemExit("macro invocation remained in preprocessed output")
    print(f"PASS {spec['case']} {spec['scenario']} sizes=4,16,64 with {Path(resolved).name}")


if __name__ == "__main__": main()
