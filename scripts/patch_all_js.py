#!/usr/bin/env python3
"""Patch Kopanito v1.0.7's bundled Linux gamepad remapper."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Patch:
    name: str
    old: tuple[str, ...]
    new: str


PATCHES = (
    Patch(
        "filter raw GameSir pads and reindex Steam virtual pads",
        (
            'function o(e,t){for(var n,r=0;r<e.length;r++)if(n=e[r]){var a=s(n);a?(_(n),a.lastChecked=t):(n=_(n),n.lastChecked=t,',
            'function o(e,t){for(var n,r=0;r<e.length;r++)if(n=e[r]){var a=s(n);n=_(n),a?a.lastChecked=t:(n.lastChecked=t,',
        ),
        'function o(e,t){for(var n,r=0,u=0;r<e.length;r++)if(n=e[r],n&&"string"==typeof n.id&&-1!==n.id.indexOf("GameSir-Nova Lite"))continue;else if(n){var a=s(n);n=_(n),n.index=u++,a?a.lastChecked=t:(n.lastChecked=t,',
    ),
    Patch(
        "select the modern six-axis Linux layout",
        ('t||(t=r(e),e.axes[2]<=-.9&&e.axes[5]<=-.9&&(t.mode="ubuntu15"))',),
        't||(t=r(e),t.mode="ubuntu15")',
    ),
    Patch(
        "move the right stick off the trigger axes",
        ('t.axes[2]=e.axes[2],t.axes[3]=e.axes[3]',),
        't.axes[2]=e.axes[3],t.axes[3]=e.axes[4]',
    ),
    Patch(
        "map LT and RT to their real axes",
        ('t.buttons[6].value=.5*(e.axes[5]+1),t.buttons[7].value=.5*(e.axes[4]+1)',),
        't.buttons[6].value=.5*(e.axes[2]+1),t.buttons[7].value=.5*(e.axes[5]+1)',
    ),
    Patch(
        "make negative D-pad directions pressable",
        ('t.buttons[12].value=Math.min(0,e.axes[7]),t.buttons[13].value=Math.max(0,e.axes[7]),t.buttons[14].value=Math.min(0,e.axes[6]),t.buttons[15].value=Math.max(0,e.axes[6])',),
        't.buttons[12].value=Math.max(0,-e.axes[7]),t.buttons[13].value=Math.max(0,e.axes[7]),t.buttons[14].value=Math.max(0,-e.axes[6]),t.buttons[15].value=Math.max(0,e.axes[6])',
    ),
)


def check_text(text: str) -> list[str]:
    errors: list[str] = []
    if 'define("nebula/input/gamepad"' not in text:
        errors.append("nebula/input/gamepad module was not found")

    for patch in PATCHES:
        if any(old in text for old in patch.old):
            errors.append(f"old code remains: {patch.name}")
        if patch.new not in text:
            errors.append(f"patched code is missing: {patch.name}")
    return errors


def apply_patches(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    changed = False

    if 'define("nebula/input/gamepad"' not in text:
        raise RuntimeError("This does not look like Kopanito v1.0.7 scripts/all.js")

    for patch in PATCHES:
        old_counts = [(old, text.count(old)) for old in patch.old]
        old_count = sum(count for _, count in old_counts)
        new_count = text.count(patch.new)

        if old_count == 1:
            old = next(old for old, count in old_counts if count == 1)
            text = text.replace(old, patch.new, 1)
            changed = True
            print(f"patched: {patch.name}")
        elif old_count == 0 and new_count >= 1:
            print(f"already patched: {patch.name}")
        elif old_count == 0:
            raise RuntimeError(
                f"Could not find either version of the code for: {patch.name}. "
                "The installed game may not be Kopanito v1.0.7."
            )
        else:
            raise RuntimeError(
                f"Found {old_count} copies of an expected unique block: {patch.name}"
            )

    errors = check_text(text)
    if errors:
        raise RuntimeError("Patch verification failed:\n" + "\n".join(errors))

    if changed:
        path.write_text(text, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path, help="Extracted scripts/all.js")
    parser.add_argument(
        "--check", action="store_true", help="Check the patch without changing the file"
    )
    args = parser.parse_args()

    if args.check:
        errors = check_text(args.file.read_text(encoding="utf-8"))
        if errors:
            for error in errors:
                print(f"error: {error}")
            return 1
        print("Kopanito gamepad patch is present")
        return 0

    apply_patches(args.file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
