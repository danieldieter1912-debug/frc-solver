# frc-solver

**Hybrid Friendly Captcha v1 Proof-of-Work Solver** — Go Binary + Python Fallback.

---

## Protokoll

Friendly Captcha nutzt mehrere SHA-256 Sub-Puzzles:

```
Server → {puzzle: base64, signature: hex}
         ↓ Parse binary:
           [0]     version
           [1]     difficulty  ← Anzahl führender Null-Bits
           [16]    n_puzzles   ← Anzahl Sub-Puzzles
           [17+]   n × 8 Bytes Sub-Puzzle-Daten
         ↓ Für jedes Sub-Puzzle:
           Finde 4-Byte Nonce wo SHA256(8_bytes + nonce) mit difficulty Null-Bits anfängt
         ↓
Client → solution_string = base64(alle_nonces) + "." + puzzle_b64
         → als .frc-captcha-solution Form-Feld senden
```

---

## Installation

```bash
pip install frc-solver
# oder:
pip install git+https://github.com/yourusername/frc-solver.git
```

---

## Schnellstart

```python
from frc_solver import fetch_and_solve, get_backend

print(get_backend())  # "go" oder "python"

sol = fetch_and_solve(
    sitekey = "FCMSL4R2K6K0USOJ",
    origin  = "https://aktion-mensch-newsletter.de",
)

print(sol.to_solution_string())  # → als .frc-captcha-solution senden
print(sol.took)                  # → ms
print(len(sol.nonces))           # → Anzahl gelöster Sub-Puzzles
```

---

## In Formular einbauen

```python
import requests
from frc_solver import fetch_and_solve

sol = fetch_and_solve(sitekey="DEIN_SITEKEY", origin="https://example.com")

requests.post("https://example.com/subscribe", data={
    "email":                 "user@example.com",
    ".frc-captcha-solution": sol.to_solution_string(),
})
```

---

## API

### `fetch_and_solve(sitekey, origin, referer, proxies, timeout, workers)`
Holt Puzzle und löst es in einem Aufruf.

### `solve(puzzle, workers, force_python)`
Löst ein FRCPuzzle-Objekt direkt.

### `get_backend() → "go" | "python"`

### `FRCPuzzle`
```python
FRCPuzzle.from_b64(b64_str)   # aus base64-String
puzzle.difficulty              # Anzahl Null-Bits
puzzle.puzzles                 # Liste der 8-Byte Sub-Puzzles
```

### `FRCSolution`
```python
sol.to_solution_string()   # → .frc-captcha-solution Wert
sol.nonces                 # Liste der gefundenen Nonces
sol.took                   # ms
```

---

## Go Binary bauen

```bash
python build.py              # aktuelle Plattform
python build.py --windows    # Windows .exe
python build.py --all        # alle Plattformen
```

---

## Tests

```bash
python tests/test_solver.py
```

---

## Bekannte Seiten

| Seite | Sitekey |
|---|---|
| aktion-mensch-newsletter.de | `FCMSL4R2K6K0USOJ` |

---

## Lizenz

MIT
