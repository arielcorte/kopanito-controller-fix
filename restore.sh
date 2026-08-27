#!/usr/bin/env bash
set -euo pipefail

RESTORE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
RESET_PROFILE=0

usage() {
  cat <<'EOF'
Usage: ./restore.sh [--reset-profile]

Restores the GameSir Nova Lite fix for Kopanito v1.0.7.

Options:
  --reset-profile  Reset controller layouts 1 and 2 to Kopanito defaults.
  -h, --help       Show this help.

Environment overrides:
  STEAM_ROOT       Main Steam directory. Default: ~/.local/share/Steam
  KOPANITO_EXE     Full path to the Kopanito executable.
  KOPANITO_PROFILE Full path to player1.gz.
  KOPANITO_BACKUP_ROOT Directory for timestamped local backups.
EOF
}

while (($#)); do
  case "$1" in
    --reset-profile)
      RESET_PROFILE=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

for required_command in python3 unzip zip install; do
  if ! command -v "$required_command" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$required_command" >&2
    exit 1
  fi
done

DEFAULT_DATA_DIR=${XDG_DATA_HOME:-"$HOME/.local/share"}
STEAM_ROOT=${STEAM_ROOT:-"$DEFAULT_DATA_DIR/Steam"}
KOPANITO_EXE=${KOPANITO_EXE:-"$STEAM_ROOT/steamapps/common/Kopanito All-Stars Soccer/kopanito"}
KOPANITO_PROFILE=${KOPANITO_PROFILE:-"$(dirname -- "$KOPANITO_EXE")/data/profiles/player1.gz"}
KOPANITO_BACKUP_ROOT=${KOPANITO_BACKUP_ROOT:-"$DEFAULT_DATA_DIR/kopanito-controller-fix/backups"}

process_is_running() {
  ps -C "$1" -o stat= 2>/dev/null | grep -qv '^[[:space:]]*Z'
}

if [[ ${KOPANITO_SKIP_PROCESS_CHECK:-0} != 1 ]]; then
  if process_is_running kopanito; then
    echo "Kopanito is running. Close it before restoring the fix." >&2
    exit 1
  fi
  if process_is_running steam; then
    echo "Steam is running. Exit Steam completely before restoring the fix." >&2
    exit 1
  fi
fi

if [[ ! -f "$KOPANITO_EXE" ]]; then
  printf 'Kopanito executable not found: %s\n' "$KOPANITO_EXE" >&2
  echo "Set KOPANITO_EXE if the game is in another Steam library." >&2
  exit 1
fi
if [[ ! -d "$STEAM_ROOT" ]]; then
  printf 'Steam directory not found: %s\n' "$STEAM_ROOT" >&2
  exit 1
fi

BACKUP_STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="$KOPANITO_BACKUP_ROOT/$BACKUP_STAMP"
mkdir -p "$BACKUP_DIR/game"
cp --preserve=all "$KOPANITO_EXE" "$BACKUP_DIR/game/kopanito"
if [[ -f "$KOPANITO_PROFILE" ]]; then
  mkdir -p "$BACKUP_DIR/profile"
  cp --preserve=all "$KOPANITO_PROFILE" "$BACKUP_DIR/profile/player1.gz"
fi

python3 "$RESTORE_DIR/scripts/configure_steam.py" \
  --steam-root "$STEAM_ROOT" \
  --backup-root "$BACKUP_DIR"

PATCH_TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/kopanito-controller-fix.XXXXXX")
cleanup() {
  if [[ -n ${PATCH_TMP_DIR:-} && -d "$PATCH_TMP_DIR" ]]; then
    find "$PATCH_TMP_DIR" -depth -delete
  fi
}
trap cleanup EXIT

STAGED_EXE="$PATCH_TMP_DIR/kopanito.staged.zip"
cp --preserve=mode "$KOPANITO_EXE" "$STAGED_EXE"
if ! unzip -q "$STAGED_EXE" scripts/all.js -d "$PATCH_TMP_DIR/source"; then
  test -f "$PATCH_TMP_DIR/source/scripts/all.js"
fi
python3 "$RESTORE_DIR/scripts/patch_all_js.py" "$PATCH_TMP_DIR/source/scripts/all.js"
zip -A "$STAGED_EXE"
touch "$PATCH_TMP_DIR/source/scripts/all.js"
(
  cd "$PATCH_TMP_DIR/source"
  zip -q -u "$STAGED_EXE" scripts/all.js
)
chmod 755 "$STAGED_EXE"
unzip -tqq "$STAGED_EXE"
unzip -q "$STAGED_EXE" scripts/all.js -d "$PATCH_TMP_DIR/check"
python3 "$RESTORE_DIR/scripts/patch_all_js.py" \
  --check "$PATCH_TMP_DIR/check/scripts/all.js"

install -m 755 "$STAGED_EXE" "$KOPANITO_EXE"

if ((RESET_PROFILE)); then
  if [[ ! -f "$KOPANITO_PROFILE" ]]; then
    printf 'Kopanito profile not found: %s\n' "$KOPANITO_PROFILE" >&2
    exit 1
  fi
  python3 "$RESTORE_DIR/scripts/reset_profile.py" \
    "$KOPANITO_PROFILE" \
    --backup-root "$BACKUP_DIR"
fi

echo
echo "Restore complete."
printf 'Backup: %s\n' "$BACKUP_DIR"
echo "Start Steam, connect both controllers, then launch Kopanito."
