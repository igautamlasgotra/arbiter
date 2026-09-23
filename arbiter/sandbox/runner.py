"""Isolated execution of model-generated code.

Security posture, stated plainly (brief section 10):

  - Local research runs: separate process, no network reachable code path,
    temp working directory, wall-clock timeout, and POSIX resource limits
    where the platform provides them.
  - Windows has no `resource` module, so CPU/memory rlimits are unavailable
    there. The timeout still applies. For the final experiment runs, execute
    on WSL/Linux or in Docker to get the full limits. This is a real weakness
    of running the benchmark on Windows and is recorded in the report rather
    than glossed over.
  - The public deployment never calls this. Arbitrary code execution is not
    exposed on a public host under any circumstances.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:  # POSIX only
    import resource  # type: ignore
except ImportError:  # pragma: no cover - Windows
    resource = None  # type: ignore

DEFAULT_TIMEOUT = 5.0
DEFAULT_MEMORY_MB = 512


@dataclass
class ExecResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_s: float


def _limits(memory_mb: int, cpu_seconds: int):  # pragma: no cover - POSIX only
    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        nbytes = memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (nbytes, nbytes))
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
        resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 8 * 1024 * 1024))

    return apply


def run_python(
    source: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    memory_mb: int = DEFAULT_MEMORY_MB,
    stdin: Optional[str] = None,
) -> ExecResult:
    """Execute `source` in a fresh interpreter and capture the outcome."""
    import time

    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        # deliberately NOT inheriting the parent environment: no API keys,
        # no proxy settings, nothing the generated code could exfiltrate
    }
    if sys.platform == "win32":
        env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")

    popen_kwargs: dict = {}
    if resource is not None and sys.platform != "win32":  # pragma: no cover
        popen_kwargs["preexec_fn"] = _limits(memory_mb, int(timeout) + 1)

    with tempfile.TemporaryDirectory(prefix="arbiter_") as tmp:
        script = Path(tmp) / "solution.py"
        script.write_text(source, encoding="utf-8")
        started = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-S", str(script)],
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmp,
                env=env,
                **popen_kwargs,
            )
        except subprocess.TimeoutExpired:
            return ExecResult(
                ok=False,
                returncode=-1,
                stdout="",
                stderr=f"execution exceeded {timeout}s and was killed",
                timed_out=True,
                duration_s=timeout,
            )
        except OSError as exc:
            return ExecResult(False, -1, "", f"failed to launch: {exc}", False, 0.0)

        duration = time.perf_counter() - started
        return ExecResult(
            ok=proc.returncode == 0,
            returncode=proc.returncode,
            stdout=proc.stdout[-8000:],
            stderr=proc.stderr[-8000:],
            timed_out=False,
            duration_s=duration,
        )
