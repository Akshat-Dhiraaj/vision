from __future__ import annotations

import argparse
from pathlib import Path

from vision_assistant import __version__
from vision_assistant.src.config_loader import DEFAULT_CONFIG_DIR, ConfigError, load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vision-assistant",
        description="Local vision gesture assistant.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--config-dir",
        default=DEFAULT_CONFIG_DIR,
        type=Path,
        help="Directory containing settings.yaml and actions.yaml.",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Load and validate config without opening a camera.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.check_config:
        try:
            config = load_config(args.config_dir)
        except ConfigError as exc:
            parser.exit(2, f"Config error: {exc}\n")

        print(f"Config OK: {len(config.actions)} action(s) loaded.")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
