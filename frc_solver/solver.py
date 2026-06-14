"""
frc_solver/solver.py
Hybrid Solver — Go wenn verfügbar, Python als Fallback.
"""
import json
from typing import Optional

from .py_backend import FRCPuzzle, FRCSolution, solve_py
from .go_backend  import solve_go, is_available as go_available, binary_path
# FRCPuzzle.from_string ist jetzt die primäre API

try:
    import requests as _requests
    _REQUESTS = True
except ImportError:
    _REQUESTS = False

PUZZLE_API = "https://eu-api.friendlycaptcha.eu/api/v1/puzzle"


def get_backend() -> str:
    return "go" if go_available() else "python"


def backend_info() -> dict:
    return {
        "backend":      get_backend(),
        "go_available": go_available(),
        "go_binary":    binary_path(),
    }


def solve(
    puzzle: "FRCPuzzle | str | dict",
    workers: int = 0,
    force_python: bool = False,
) -> Optional[FRCSolution]:
    """
    Löst ein Friendly Captcha Puzzle.

    Args:
        puzzle:       FRCPuzzle, base64-String oder API-Response-Dict
        workers:      Go-Worker-Anzahl (0 = auto)
        force_python: immer Python nutzen

    Returns:
        FRCSolution oder None

    Beispiel:
        >>> import requests
        >>> resp = requests.get("https://eu-api.friendlycaptcha.eu/api/v1/puzzle?sitekey=...")
        >>> sol = solve(resp.json())
        >>> print(sol.to_solution_string())
    """
    # Eingabe normalisieren
    if isinstance(puzzle, dict):
        puzzle = FRCPuzzle.from_string(puzzle.get("puzzle") or puzzle.get("data",{}).get("puzzle",""))
    elif isinstance(puzzle, str):
        puzzle = FRCPuzzle.from_string(puzzle)

    # Go-Backend versuchen
    if go_available() and not force_python:
        sol = solve_go(puzzle, workers=workers)
        if sol is not None:
            return sol

    # Python-Fallback
    return solve_py(puzzle)


def fetch_and_solve(
    sitekey:    str,
    origin:     str,
    referer:    str = "",
    proxies:    Optional[dict] = None,
    timeout:    int = 15,
    workers:    int = 0,
    session=None,
) -> Optional[FRCSolution]:
    """
    Holt Puzzle vom Friendly Captcha API und löst es.

    Args:
        sitekey:  Sitekey der Zielseite (z.B. "FCMSL4R2K6K0USOJ")
        origin:   Origin der Zielseite (z.B. "https://aktion-mensch-newsletter.de")
        referer:  Referer (optional, default = origin + "/")
        proxies:  Proxy-Dict
        timeout:  Timeout in Sekunden
        workers:  Go-Worker-Anzahl (0 = auto)
        session:  requests.Session (optional)

    Returns:
        FRCSolution oder None

    Beispiel:
        >>> sol = fetch_and_solve(
        ...     sitekey="FCMSL4R2K6K0USOJ",
        ...     origin="https://aktion-mensch-newsletter.de",
        ... )
        >>> print(sol.to_solution_string())
    """
    if not _REQUESTS:
        raise ImportError("pip install requests")

    import requests

    s = session or requests.Session()
    r = s.get(
        PUZZLE_API,
        params={"sitekey": sitekey},
        headers={
            "Accept":          "*/*",
            "Accept-Language": "de-DE,de;q=0.9",
            "Origin":          origin,
            "Referer":         referer or (origin + "/"),
            "x-frc-client":   "js-0.9.11",
        },
        proxies = proxies,
        timeout = timeout,
    )
    r.raise_for_status()

    data    = r.json()
    # API gibt manchmal {"puzzle": "..."} und manchmal {"data": {"puzzle": "..."}}
    pstr = (data.get("puzzle")
            or data.get("data", {}).get("puzzle")
            or "")
    if not pstr:
        raise ValueError(f"Kein Puzzle in Response: {data}")
    puzzle = FRCPuzzle.from_string(pstr)
    return solve(puzzle, workers=workers)


__all__ = [
    "solve",
    "fetch_and_solve",
    "get_backend",
    "backend_info",
    "FRCPuzzle",
    "FRCSolution",
]
