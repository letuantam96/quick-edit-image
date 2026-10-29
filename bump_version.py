"""Read or bump the app version in quick_edit_image/__init__.py. Used by build.bat.

python bump_version.py              -> prints the current version
python bump_version.py patch        -> 1.2.3 -> 1.2.4 (also minor -> 1.3.0, major -> 2.0.0), prints it
"""

import re
import sys
from pathlib import Path

INIT = Path(__file__).parent / "quick_edit_image" / "__init__.py"
PATTERN = r'__version__ = "(\d+)\.(\d+)\.(\d+)"'


def main() -> None:
    text = INIT.read_text(encoding="utf-8")
    major, minor, patch = map(int, re.search(PATTERN, text).groups())
    part = sys.argv[1] if len(sys.argv) > 1 else None
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    elif part == "patch":
        patch += 1
    elif part is not None:
        sys.exit(f"Unknown part: {part} (use major, minor or patch)")
    version = f"{major}.{minor}.{patch}"
    if part:
        INIT.write_text(re.sub(PATTERN, f'__version__ = "{version}"', text), encoding="utf-8")
    print(version)


if __name__ == "__main__":
    main()
