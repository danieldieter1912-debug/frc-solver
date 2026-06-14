"""
frc_solver/py_backend.py
━━━━━━━━━━━━━━━━━━━━━━━
Friendly Captcha v1 Proof-of-Work Solver — Pure Python.

Echtes Format (ermittelt aus Live-API-Analyse):
  Puzzle-String: "{hex_id}.{b64_params}"
  - hex_id    = 16 Bytes als Hex = Seed für SHA256
  - b64_params = 32 Bytes:
      [12] = n_puzzles
      [13] = difficulty (führende Null-Bits)

  Lösung pro Sub-Puzzle:
    Finde 4-Byte Nonce N (little-endian uint32) sodass:
    SHA256(hex_bytes + nonce_bytes) mindestens `difficulty` Null-Bits hat

  Solution-String: base64(nonce) + "." + original_puzzle_string
"""
import base64
import hashlib
import struct
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class FRCPuzzle:
    """Parsed Friendly Captcha Puzzle."""
    raw:        str    # Original Puzzle-String z.B. "abc123.base64=="
    hex_bytes:  bytes  # 16-Byte Seed (aus hex_part)
    hex_part:   str    # Hex-String (vor dem Punkt)
    b64_part:   str    # Base64-String (nach dem Punkt)
    b64_bytes:  bytes  # Dekodierter b64-Teil
    n_puzzles:  int    # Anzahl Sub-Puzzles (b64[12])
    difficulty: int    # Führende Null-Bits (b64[13])

    @classmethod
    def from_string(cls, puzzle_str: str) -> "FRCPuzzle":
        """
        Parst den Puzzle-String vom Server.
        Format: "hex_id.base64_params"
        """
        puzzle_str = puzzle_str.strip()

        if "." not in puzzle_str:
            raise ValueError(f"Unbekanntes Puzzle-Format (kein Punkt): {puzzle_str[:50]}")

        hex_part, _, b64_part = puzzle_str.partition(".")

        # Hex-Teil dekodieren
        try:
            hex_bytes = bytes.fromhex(hex_part)
        except ValueError as e:
            raise ValueError(f"Hex-Teil ungültig ('{hex_part[:20]}'): {e}")

        # Base64-Teil dekodieren
        try:
            padded    = b64_part + "=" * ((4 - len(b64_part) % 4) % 4)
            b64_bytes = base64.b64decode(padded)
        except Exception as e:
            raise ValueError(f"Base64-Teil ungültig: {e}")

        if len(b64_bytes) < 14:
            raise ValueError(f"b64-Teil zu kurz: {len(b64_bytes)} Bytes")

        n_puzzles  = b64_bytes[12]
        difficulty = b64_bytes[13]

        if n_puzzles == 0:
            n_puzzles = 1  # Fallback

        return cls(
            raw        = puzzle_str,
            hex_bytes  = hex_bytes,
            hex_part   = hex_part,
            b64_part   = b64_part,
            b64_bytes  = b64_bytes,
            n_puzzles  = n_puzzles,
            difficulty = difficulty,
        )

    def __str__(self) -> str:
        return (f"FRCPuzzle(n={self.n_puzzles}, diff={self.difficulty}, "
                f"seed={self.hex_part[:8]}...)")


@dataclass
class FRCSolution:
    """Gelöste Friendly Captcha Solution."""
    puzzle:  FRCPuzzle
    nonces:  list[int]   # 4-Byte Nonces (little-endian uint32)
    took:    int         # Millisekunden

    def to_solution_string(self) -> str:
        """
        Solution-String für .frc-captcha-solution Feld.
        Format: base64(nonce) + "." + original_puzzle_string
        """
        # Bei 1 Puzzle: einfach nonce direkt
        # Bei N Puzzles: alle Nonces concateniert
        nonce_bytes = b"".join(
            struct.pack("<I", n) for n in self.nonces
        )
        return base64.b64encode(nonce_bytes).decode() + "." + self.puzzle.raw

    def __str__(self) -> str:
        return self.to_solution_string()


def _has_leading_zero_bits(hash_bytes: bytes, n: int) -> bool:
    """Prüft ob hash_bytes mindestens n führende Null-Bits hat."""
    full_bytes    = n // 8
    remaining_bits= n % 8
    for i in range(full_bytes):
        if hash_bytes[i] != 0:
            return False
    if remaining_bits > 0:
        mask = 0xFF << (8 - remaining_bits) & 0xFF
        if hash_bytes[full_bytes] & mask != 0:
            return False
    return True


def _solve_one(seed: bytes, difficulty: int) -> int:
    """
    Löst ein Sub-Puzzle: findet Nonce N wo
    SHA256(seed + N_as_4_le_bytes) mit `difficulty` Null-Bits anfängt.
    """
    for n in range(2**32):
        nonce_bytes = struct.pack("<I", n)
        h = hashlib.sha256(seed + nonce_bytes).digest()
        if _has_leading_zero_bits(h, difficulty):
            return n
    raise RuntimeError(f"Keine Lösung gefunden (difficulty={difficulty})")


def solve_py(puzzle: FRCPuzzle) -> FRCSolution:
    """
    Löst alle Sub-Puzzles.
    Seed = puzzle.hex_bytes (16 Bytes vom hex_part).
    """
    t0     = time.perf_counter()
    nonces = []

    for i in range(puzzle.n_puzzles):
        # Bei mehreren Puzzles: Seed = hex_bytes + index
        if puzzle.n_puzzles > 1:
            seed = hashlib.sha256(
                puzzle.hex_bytes + struct.pack("<I", i)
            ).digest()[:16]
        else:
            seed = puzzle.hex_bytes

        nonce = _solve_one(seed, puzzle.difficulty)
        nonces.append(nonce)

    took = max(1, int((time.perf_counter() - t0) * 1000))
    return FRCSolution(puzzle=puzzle, nonces=nonces, took=took)
