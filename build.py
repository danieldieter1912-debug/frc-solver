#!/usr/bin/env python3
"""build.py — Kompiliert das Go-Binary."""
import argparse, os, platform, subprocess, sys
from pathlib import Path

GO_SRC  = Path(__file__).parent / "go"
BIN_DIR = Path(__file__).parent / "frc_solver" / "bin"

def build(goos, goarch, output):
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    out_path = BIN_DIR / output
    env = {**os.environ, "GOOS": goos, "GOARCH": goarch}
    print(f"  Building {goos}/{goarch} → {output} …")
    r = subprocess.run(
        ["go", "build", "-ldflags=-s -w", "-o", str(out_path), "./cmd/frc"],
        cwd=str(GO_SRC), env=env, capture_output=True, text=True,
    )
    if r.returncode == 0:
        print(f"  ✅ {output} ({out_path.stat().st_size/1024:.0f}KB)")
    else:
        print(f"  ❌ {r.stderr.strip()}")
    return r.returncode == 0

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--all",     action="store_true")
    p.add_argument("--windows", action="store_true")
    p.add_argument("--linux",   action="store_true")
    p.add_argument("--macos",   action="store_true")
    args = p.parse_args()

    print("🔨 FRC Solver — Go Binary Build\n")
    targets = []
    if args.all or args.windows:
        targets += [("windows","amd64","frc.exe"), ("windows","386","frc_x86.exe")]
    if args.all or args.linux:
        targets += [("linux","amd64","frc_linux"), ("linux","arm64","frc_linux_arm64")]
    if args.all or args.macos:
        targets += [("darwin","amd64","frc_macos"), ("darwin","arm64","frc_macos_arm64")]
    if not targets:
        sys_map = {"Windows":("windows","frc.exe"),"Linux":("linux","frc"),"Darwin":("darwin","frc")}
        goos, out = sys_map.get(platform.system(), ("linux","frc"))
        goarch = "amd64" if platform.machine() in ("x86_64","AMD64") else "arm64"
        targets = [(goos, goarch, out)]

    ok = all(build(g, a, o) for g, a, o in targets)
    print(f"\n{'✅ Fertig!' if ok else '❌ Fehler'}")
    print(f"Binaries in: {BIN_DIR}")

if __name__ == "__main__":
    main()
