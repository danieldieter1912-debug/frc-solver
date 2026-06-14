"""
frc-solver — Hybrid Friendly Captcha Proof-of-Work Solver
"""
from .solver import solve, fetch_and_solve, get_backend, backend_info, FRCPuzzle, FRCSolution

__version__ = "1.0.0"
__all__ = ["solve", "fetch_and_solve", "get_backend", "backend_info", "FRCPuzzle", "FRCSolution"]
