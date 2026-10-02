#!/usr/bin/env python3
"""Cute Channel: one command line for the whole pipeline.

python cc.py doctor            check Blender, ffmpeg, Python and secrets
python cc.py doctor --deep     also render a test scene with each engine (1-5 min)
python cc.py --help            every command, and the phase that builds it
"""

import sys

# Deliberately "outdated" check: it must run on old Pythons to print a friendly message.
if sys.version_info < (3, 10):  # noqa: UP036
    sys.exit(
        f"Cute Channel needs Python 3.10 or newer; this is {sys.version.split()[0]}. "
        "Install Python 3.11+ and run it again, e.g. `python3.11 cc.py doctor`."
    )

import argparse  # noqa: E402

# Commands that later phases will implement: (name, phase, what it will do).
PLANNED = (
    ("validate", 1, "check brand/*.json against their schemas"),
    ("brand-sheets", 1, "draw the character sheet, turnaround and expression sheet"),
    ("build-character", 2, "build the 3D character .blend from brand/character.json"),
    ("emotion-sheet", 3, "render every emotion as a contact sheet per character"),
    ("new-episode", 4, "turn a one-line idea into storyboard.md + episode.yaml"),
    ("compile", 4, "episode.yaml -> animated .blend + events.json"),
    ("render", 5, "render an episode (--preview in CI, --final overnight on your laptop)"),
    ("mix", 6, "place sound effects from events.json and mix to -14 LUFS"),
    ("finish", 7, "encode the MP4s, burn in captions, make the cover, check the loop"),
    ("qa", 7, "automatic checks: specs, safe zones, loudness, licences, originality"),
    ("ideas", 8, "generate and score fresh episode ideas"),
    ("package", 9, "phone-ready folder for posting by hand"),
    ("publish", 9, "approval-gated upload to Instagram / YouTube"),
    ("report", 10, "weekly analytics report"),
)


def cmd_doctor(args: argparse.Namespace) -> int:
    from pipeline import doctor

    return doctor.main(deep=args.deep, output_format=args.format)


def planned_command(name: str, phase: int, description: str):
    def run(args: argparse.Namespace) -> int:
        print(
            f"`cc.py {name}` is planned for Phase {phase}: {description}.\n"
            "It isn't built yet; see docs/ROADMAP.md for progress.",
            file=sys.stderr,
        )
        return 2

    return run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cc.py",
        description="Cute Channel pipeline. Start with: python cc.py doctor",
    )
    sub = parser.add_subparsers(title="commands", metavar="<command>")

    doctor = sub.add_parser("doctor", help="check that this machine can make episodes")
    doctor.add_argument(
        "--deep", action="store_true", help="also test-render with every engine (1-5 min)"
    )
    doctor.add_argument(
        "--format", choices=("text", "json", "markdown"), default="text", help="output format"
    )
    doctor.set_defaults(func=cmd_doctor)

    for name, phase, description in PLANNED:
        planned = sub.add_parser(name, help=f"(Phase {phase}) {description}", add_help=False)
        planned.add_argument("rest", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
        planned.set_defaults(func=planned_command(name, phase, description))
    return parser


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")  # never crash on emoji in an old console
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
