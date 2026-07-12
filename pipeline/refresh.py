#!/usr/bin/env python3
"""Daily refresh runner: rebuild the draft dataset, then regenerate the CSV.

Runs build_players.py, and only if that succeeds, preview.py. All output is
appended to pipeline/logs/refresh.log with a timestamp so a scheduled run
leaves an inspectable trail. Exit code is non-zero if the build failed.

Intended for Windows Task Scheduler (see register_refresh_task.ps1), but also
runnable by hand:  python pipeline/refresh.py
"""
import os, sys, subprocess, datetime

HERE   = os.path.dirname(os.path.abspath(__file__))
LOGDIR = os.path.join(HERE, "logs")
LOG    = os.path.join(LOGDIR, "refresh.log")
PY     = sys.executable or "python"

def run(script):
    """Run a sibling pipeline script with the same interpreter; capture output."""
    p = subprocess.run([PY, os.path.join(HERE, script)], capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")

def main():
    os.makedirs(LOGDIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = [f"\n===== refresh {stamp} ====="]

    rc, log = run("build_players.py")
    out.append(log.rstrip())
    if rc == 0:
        rc2, log2 = run("preview.py")
        out.append(log2.rstrip())
        rc = rc2
    else:
        out.append(f"build_players.py FAILED (rc={rc}) - keeping previous data, skipping preview")
    out.append(f"===== done (rc={rc}) =====")

    text = "\n".join(out) + "\n"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(text)
    print(text)
    sys.exit(rc)

if __name__ == "__main__":
    main()
