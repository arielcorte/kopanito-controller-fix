#!/usr/bin/env bash
set -euo pipefail

VERIFY_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
DEFAULT_DATA_DIR=${XDG_DATA_HOME:-"$HOME/.local/share"}
STEAM_ROOT=${STEAM_ROOT:-"$DEFAULT_DATA_DIR/Steam"}
KOPANITO_EXE=${KOPANITO_EXE:-"$STEAM_ROOT/steamapps/common/Kopanito All-Stars Soccer/kopanito"}

if [[ ! -f "$KOPANITO_EXE" ]]; then
  printf 'Kopanito executable not found: %s\n' "$KOPANITO_EXE" >&2
  exit 1
fi

VERIFY_TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/kopanito-controller-check.XXXXXX")
cleanup() {
  if [[ -n ${VERIFY_TMP_DIR:-} && -d "$VERIFY_TMP_DIR" ]]; then
    find "$VERIFY_TMP_DIR" -depth -delete
  fi
}
trap cleanup EXIT

unzip -tqq "$KOPANITO_EXE"
unzip -q "$KOPANITO_EXE" scripts/all.js -d "$VERIFY_TMP_DIR"
python3 "$VERIFY_DIR/scripts/patch_all_js.py" \
  --check "$VERIFY_TMP_DIR/scripts/all.js"
python3 "$VERIFY_DIR/scripts/configure_steam.py" \
  --steam-root "$STEAM_ROOT" \
  --backup-root "$VERIFY_TMP_DIR/unused-backup" \
  --check

echo "Kopanito controller fix is installed."
