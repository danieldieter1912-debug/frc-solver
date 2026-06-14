"""
examples/aktion_mensch.py
Friendly Captcha lösen für aktion-mensch-newsletter.de
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
from frc_solver import fetch_and_solve, get_backend

SITEKEY = "FCMSL4R2K6K0USOJ"
ORIGIN  = "https://aktion-mensch-newsletter.de"

def submit_newsletter(email: str, proxy: dict = None) -> dict:
    print(f"🔐 Löse Friendly Captcha [{get_backend()}] …")

    sol = fetch_and_solve(
        sitekey = SITEKEY,
        origin  = ORIGIN,
        proxies = proxy,
    )
    if not sol:
        return {"ok": False, "reason": "Captcha nicht gelöst"}

    print(f"✅ Gelöst in {sol.took}ms | {len(sol.nonces)} Sub-Puzzles")
    print(f"   Solution: {sol.to_solution_string()[:40]}…")

    # Formular submitten (URL ggf. anpassen)
    r = requests.post(
        "https://aktion-mensch-newsletter.de/subscribe",  # URL anpassen!
        data={
            "email":                   email,
            ".frc-captcha-solution":   sol.to_solution_string(),
        },
        proxies=proxy,
        timeout=15,
    )
    return {"ok": r.status_code in (200, 201), "status": r.status_code}


if __name__ == "__main__":
    result = submit_newsletter("test@example.com")
    print(f"\n{'✅' if result['ok'] else '❌'} {result}")
