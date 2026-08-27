#!/usr/bin/env python3
"""Restore Steam Input settings used by the GameSir Nova Lite fix."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


APP_ID = "399820"
TEMPLATE = "controller_generic_gamepad_joystick.vdf"
GAMESIR_ID = "3537-1041-189266d5"


def backup_file(path: Path, backup_root: Path, steam_root: Path) -> None:
    relative = path.relative_to(steam_root)
    destination = backup_root / "steam" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)


def matching_brace(text: str, opening: int) -> int:
    depth = 0
    quoted = False
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("Unbalanced VDF braces")


def named_blocks(text: str, key: str, start: int = 0, end: int | None = None):
    limit = len(text) if end is None else end
    pattern = re.compile(rf'"{re.escape(key)}"\s*\{{')
    for match in pattern.finditer(text, start, limit):
        opening = text.find("{", match.start(), match.end())
        closing = matching_brace(text, opening)
        if closing <= limit:
            yield match.start(), opening, closing


def set_app_template(text: str) -> str:
    blocks = list(named_blocks(text, APP_ID))
    app_block = (
        f'\t"{APP_ID}"\n'
        "\t{\n"
        f'\t\t"template"\t\t"{TEMPLATE}"\n'
        "\t}\n"
    )
    if not blocks:
        closing = text.rfind("}")
        if closing < 0:
            raise ValueError("Controller config is not valid VDF")
        return text[:closing] + app_block + text[closing:]

    start, opening, closing = blocks[-1]
    block = text[start : closing + 1]
    template_pattern = re.compile(r'("template"\s*)"[^"]*"')
    if template_pattern.search(block):
        block = template_pattern.sub(rf'\1"{TEMPLATE}"', block, count=1)
    else:
        block = block[:-1] + f'\t\t"template"\t\t"{TEMPLATE}"\n\t' + "}"
    return text[:start] + block + text[closing + 1 :]


def set_controller_preference(text: str) -> str:
    replacements = (
        ("reverse_button_diamond_layout_v2", "-1"),
        ("use_universal_face_button_glyphs", "0"),
    )
    for key, value in replacements:
        pattern = re.compile(rf'("{key}"\s*)"[^"]*"')
        if not pattern.search(text):
            raise ValueError(f"Missing controller preference: {key}")
        text = pattern.sub(rf'\1"{value}"', text, count=1)
    return text


def set_steam_input_in_localconfig(text: str) -> str:
    app_sections = list(named_blocks(text, "apps"))
    if not app_sections:
        raise ValueError('Could not find the "apps" section in localconfig.vdf')

    apps_start, apps_opening, apps_closing = app_sections[-1]
    game_blocks = list(named_blocks(text, APP_ID, apps_opening + 1, apps_closing))
    if not game_blocks:
        raise ValueError(f"Could not find AppID {APP_ID} in the Steam apps section")

    game_start, game_opening, game_closing = game_blocks[0]
    block = text[game_start : game_closing + 1]
    setting = re.compile(r'("UseSteamControllerConfig"\s*)"[^"]*"')
    if setting.search(block):
        block = setting.sub(r'\1"2"', block, count=1)
    else:
        block = block[:-1] + '\t\t\t"UseSteamControllerConfig"\t\t"2"\n\t\t' + "}"
    return text[:game_start] + block + text[game_closing + 1 :]


def write_if_changed(
    path: Path, new_text: str, backup_root: Path, steam_root: Path, check: bool
) -> bool:
    old_text = path.read_text(encoding="utf-8")
    if old_text == new_text:
        print(f"ok: {path}")
        return False
    if check:
        print(f"needs repair: {path}")
        return True
    backup_file(path, backup_root, steam_root)
    path.write_text(new_text, encoding="utf-8")
    print(f"updated: {path}")
    return True


def configure(steam_root: Path, backup_root: Path, check: bool) -> int:
    failures = 0
    controller_root = steam_root / "steamapps/common/Steam Controller Configs"
    config_dirs = sorted(controller_root.glob("*/config"))
    if not config_dirs:
        print(f"error: no Steam controller config directories under {controller_root}")
        return 1

    preference_count = 0
    configset_count = 0
    for config_dir in config_dirs:
        for preference in sorted(config_dir.glob(f"preferences_{GAMESIR_ID}*.vdf")):
            preference_count += 1
            try:
                updated = set_controller_preference(
                    preference.read_text(encoding="utf-8")
                )
                needs_change = write_if_changed(
                    preference, updated, backup_root, steam_root, check
                )
                if check and needs_change:
                    failures += 1
            except ValueError as error:
                print(f"error: {preference}: {error}")
                failures += 1

        primary = config_dir / f"configset_{GAMESIR_ID}.vdf"
        configsets = [primary] if primary.exists() else []
        generic = config_dir / "configset_controller_generic.vdf"
        if generic.exists():
            configsets.append(generic)
        for configset in sorted(set(configsets)):
            configset_count += 1
            try:
                updated = set_app_template(configset.read_text(encoding="utf-8"))
                needs_change = write_if_changed(
                    configset, updated, backup_root, steam_root, check
                )
                if check and needs_change:
                    failures += 1
            except ValueError as error:
                print(f"error: {configset}: {error}")
                failures += 1

    if preference_count == 0:
        print("error: no GameSir Nova Lite preference files were found")
        failures += 1
    if configset_count == 0:
        print("error: no matching Steam Input configset files were found")
        failures += 1

    localconfigs = sorted((steam_root / "userdata").glob("*/config/localconfig.vdf"))
    relevant_localconfigs = [
        path
        for path in localconfigs
        if f'"{APP_ID}"' in path.read_text(encoding="utf-8", errors="replace")
    ]
    if not relevant_localconfigs:
        print(f"error: no Steam user localconfig contains AppID {APP_ID}")
        failures += 1
    for localconfig in relevant_localconfigs:
        try:
            updated = set_steam_input_in_localconfig(
                localconfig.read_text(encoding="utf-8")
            )
            needs_change = write_if_changed(
                localconfig, updated, backup_root, steam_root, check
            )
            if check and needs_change:
                failures += 1
        except ValueError as error:
            print(f"error: {localconfig}: {error}")
            failures += 1

    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steam-root", required=True, type=Path)
    parser.add_argument("--backup-root", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return configure(args.steam_root.resolve(), args.backup_root.resolve(), args.check)


if __name__ == "__main__":
    raise SystemExit(main())
