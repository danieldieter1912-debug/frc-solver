"""
tests/test_solver.py
━━━━━━━━━━━━━━━━━━━
Tests für den Friendly Captcha Solver.
Nutzt ein synthetisches Puzzle da kein Live-API-Zugang nötig.
"""
import base64
import hashlib
import struct
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from frc_solver import solve, get_backend, FRCPuzzle
from frc_solver.py_backend import _has_leading_zero_bits, _solve_sub_puzzle


def build_test_puzzle(difficulty: int = 5, n_puzzles: int = 2) -> FRCPuzzle:
    """Baut ein synthetisches Puzzle für Tests."""
    import os as _os
    sub_puzzles = [_os.urandom(8) for _ in range(n_puzzles)]

    raw = bytes([
        1,            # version
        difficulty,   # difficulty
        0, 0, 0, 0,  # timestamp
        0, 0, 0, 0,  # account_id
        0, 0, 0, 0,  # app_id
        0, 60,        # expiry_min = 60
        n_puzzles,    # puzzle_count
    ])
    for p in sub_puzzles:
        raw += p

    b64 = base64.b64encode(raw).decode().rstrip("=")
    return FRCPuzzle.from_b64(b64)


def test_leading_zero_bits():
    # Byte 0x00 hat 8 führende Null-Bits
    assert _has_leading_zero_bits(bytes([0x00, 0xFF]), 8)
    assert _has_leading_zero_bits(bytes([0x00, 0x00, 0xFF]), 16)
    # Byte 0x0F hat 4 führende Null-Bits
    assert _has_leading_zero_bits(bytes([0x0F, 0xFF]), 4)
    assert not _has_leading_zero_bits(bytes([0x0F, 0xFF]), 5)
    # Byte 0x80 hat 0 führende Null-Bits
    assert not _has_leading_zero_bits(bytes([0x80]), 1)
    print("✅ test_leading_zero_bits")


def test_solve_sub_puzzle():
    """Löst ein Sub-Puzzle und verifiziert das Ergebnis."""
    import os as _os
    difficulty  = 8  # 1 führendes Null-Byte → schnell
    puzzle_bytes= _os.urandom(8)

    nonce = _solve_sub_puzzle(puzzle_bytes, difficulty)

    # Verifizieren
    nonce_bytes = struct.pack("<i", nonce)
    h = hashlib.sha256(puzzle_bytes + nonce_bytes).digest()
    assert _has_leading_zero_bits(h, difficulty), f"Hash {h.hex()} hat nicht {difficulty} Null-Bits"
    print(f"✅ test_solve_sub_puzzle | nonce={nonce} | hash={h.hex()[:16]}...")


def test_parse_puzzle():
    puzzle = build_test_puzzle(difficulty=5, n_puzzles=2)
    assert puzzle.version == 1
    assert puzzle.difficulty == 5
    assert len(puzzle.puzzles) == 2
    assert all(len(p) == 8 for p in puzzle.puzzles)
    print(f"✅ test_parse_puzzle | {puzzle}")


def test_solve_full():
    """Löst ein vollständiges Puzzle mit niedrigem Difficulty."""
    puzzle = build_test_puzzle(difficulty=8, n_puzzles=2)
    sol    = solve(puzzle, force_python=True)

    assert sol is not None
    assert len(sol.nonces) == 2
    assert sol.took >= 1

    # Alle Sub-Puzzles verifizieren
    for i, (sub_puzzle, nonce) in enumerate(zip(puzzle.puzzles, sol.nonces)):
        nonce_bytes = struct.pack("<i", nonce)
        h = hashlib.sha256(sub_puzzle + nonce_bytes).digest()
        assert _has_leading_zero_bits(h, puzzle.difficulty), \
            f"Sub-Puzzle {i} nicht korrekt: hash={h.hex()[:16]}..."

    print(f"✅ test_solve_full [{get_backend()}] | nonces={sol.nonces} | took={sol.took}ms")


def test_solution_string():
    puzzle = build_test_puzzle(difficulty=8, n_puzzles=1)
    sol    = solve(puzzle, force_python=True)
    s      = sol.to_solution_string()

    assert "." in s, "Solution string muss '.' enthalten"
    parts = s.split(".")
    assert len(parts) >= 2, f"Erwartet 2+ Teile, got {len(parts)}"

    # Nonce-Teil dekodierbar?
    nonce_bytes = base64.b64decode(parts[0] + "==")
    assert len(nonce_bytes) % 4 == 0
    print(f"✅ test_solution_string | {s[:40]}...")


def test_backend():
    backend = get_backend()
    assert backend in ("go", "python")
    print(f"✅ Backend: {backend}")


if __name__ == "__main__":
    print("Friendly Captcha Solver Tests")
    print("=" * 40)
    test_backend()
    test_leading_zero_bits()
    test_parse_puzzle()
    test_solve_sub_puzzle()
    test_solve_full()
    test_solution_string()
    print("=" * 40)
    print("✅ All tests passed!")
