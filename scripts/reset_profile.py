#!/usr/bin/env python3
"""Reset Kopanito's first two controller layouts to known-good defaults."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import zlib
from pathlib import Path


DEFAULT_GAMEPAD_LAYOUT = {
    "trap": "button11",
    "toggleTeam": "button9",
    "up": "axisButton2",
    "right": "axisButton1",
    "down": "axisButton3",
    "left": "axisButton0",
    "up2": "button12",
    "right2": "button15",
    "down2": "button13",
    "left2": "button14",
    "passModifier": "button4",
    "sprint": "button4",
    "walk": "button5",
    "slide": "button2",
    "goalkeeperSlide": "button3",
    "togglePlayer": "button0",
    "pass": "button0",
    "lob": "button2",
    "header": "button1",
    "shoot": "button1",
    "swerveUp": "button4",
    "swerveDown": "button5",
    "powerup": "button6",
    "back": "button1",
    "altLeft": "button4",
    "altRight": "button5",
    "clearAssigment": "",
    "clearAssigment2": "",
    "enter": "button0",
    "pause": "button8",
}


def reset_profile(profile: Path, backup_root: Path) -> None:
    backup = backup_root / "profile" / profile.name
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(profile, backup)

    old_mode = profile.stat().st_mode
    data = json.loads(zlib.decompress(profile.read_bytes()))
    data["gamepadLayout1"] = DEFAULT_GAMEPAD_LAYOUT.copy()
    data["gamepadLayout2"] = DEFAULT_GAMEPAD_LAYOUT.copy()
    for index in range(1, 5):
        data["controls"][f"gamepadLayout{index}Enabled"] = index <= 2

    encoded = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
    handle, temporary_name = tempfile.mkstemp(prefix="player1.", dir=profile.parent)
    try:
        with os.fdopen(handle, "wb") as temporary:
            temporary.write(zlib.compress(encoded))
        os.chmod(temporary_name, old_mode)
        os.replace(temporary_name, profile)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    print(f"reset: {profile}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    parser.add_argument("--backup-root", required=True, type=Path)
    args = parser.parse_args()
    reset_profile(args.profile.resolve(), args.backup_root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
