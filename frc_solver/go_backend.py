"""
frc_solver/go_backend.py
Go-Binary Interface für den Friendly Captcha Solver.
"""
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .py_backend import FRCPuzzle, FRCSolution, solve_py


def _find_binary() -> Optional[str]:
    env_path = os.environ.get("FRC_GO_BINARY")
    if env_path and os.path.isfile(env_path):
        return env_path

    bin_name = "frc.exe" if platform.system() == "Windows" else "frc"

    found = shutil.which(bin_name)
    if found:
        return found

    pkg_dir = Path(__file__).parent
    for candidate in [
        pkg_dir / "bin" / bin_name,
        pkg_dir.parent / "bin" / bin_name,
        Path.cwd() / "bin" / bin_name,
        Path.cwd() / bin_name,
    ]:
        if candidate.is_file():
            return str(candidate)

    return None


_GO_BINARY = _find_binary()


def is_available() -> bool:
    return _GO_BINARY is not None


def binary_path() -> Optional[str]:
    return _GO_BINARY


def solve_go(puzzle: FRCPuzzle, workers: int = 0) -> Optional[FRCSolution]:
    if not _GO_BINARY:
        return None

    # Puzzle-Response als JSON an Go Binary
    puzzle_json = json.dumps({
        "puzzle":    puzzle.raw,
        "signature": "",
        "expires":   "",
    })

    cmd = [_GO_BINARY]
    if workers > 0:
        cmd += ["-workers", str(workers)]

    try:
        result = subprocess.run(
            cmd,
            input=puzzle_json.encode(),
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            return None

        solution_str = result.stdout.decode().strip()
        if not solution_str:
            return None

        # Solution-String parsen: base64_nonces.puzzle_b64
        parts = solution_str.split(".")
        if len(parts) < 2:
            return None

        import base64, struct
        nonce_bytes = base64.urlsafe_b64decode(parts[0] + "==")
        nonces = [
            struct.unpack("<i", nonce_bytes[i*4:(i+1)*4])[0]
            for i in range(len(nonce_bytes) // 4)
        ]

        return FRCSolution(puzzle=puzzle, nonces=nonces, took=0)

    except Exception:
        return None
