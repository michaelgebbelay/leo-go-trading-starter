#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/vendor_into_project.py /path/to/project", file=sys.stderr)
        return 2

    repo = Path(__file__).resolve().parents[1]
    source = repo / "src" / "leo_go_trading"
    target_root = Path(sys.argv[1]).expanduser().resolve()
    target = target_root / "leo_go_trading"

    if not target_root.exists():
        print(f"target project does not exist: {target_root}", file=sys.stderr)
        return 2
    if target.exists():
        print(f"refusing to overwrite existing folder: {target}", file=sys.stderr)
        return 2

    shutil.copytree(source, target)
    print(f"copied {source} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
