from __future__ import annotations
import argparse

from .prompts import build_run_config_interactive
from .pipeline import run


def main():
    ap = argparse.ArgumentParser(description="Backing Track Generator (freeflow + tempo).")
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--audio", help="Audio path")
    args = ap.parse_args()

    if args.interactive or not args.audio:
        cfg = build_run_config_interactive(audio_path=args.audio)
    else:
        raise SystemExit("Run with --interactive. Example:\n  python -m freeflow_harmonizer.cli --interactive")

    run(cfg)


if __name__ == "__main__":
    main()
