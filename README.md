# Kopanito GameSir Nova Lite fix

This repository restores working Bluetooth controls for two GameSir Nova Lite controllers in the native Linux release of Kopanito All-Stars Soccer v1.0.7 on Steam.

It contains patching code only. It does not contain Kopanito binaries, assets, profiles, Steam credentials, or account IDs.

## What it fixes

| Input problem | Correction |
| --- | --- |
| Kopanito sees two raw pads and two Steam virtual pads | Ignore the raw GameSir devices and reindex the two Steam Xbox pads |
| Start does not activate either player | Assign the virtual pads to Kopanito controller slots 1 and 2 |
| A/B and X/Y are reversed on one controller | Disable Steam's reversed button-diamond preference for matching GameSir devices |
| LT appears as right-stick input | Map LT from Linux axis 2 |
| RT appears as LT | Map RT from Linux axis 5 |
| Right stick uses trigger axes | Map the right stick from Linux axes 3 and 4 |
| D-pad up and left do nothing | Convert their negative axis values into positive button pressure |

## Restore the fix

First, install Kopanito through Steam and connect both controllers once. Exit Kopanito and quit Steam completely before running the restore.

```bash
git clone git@github.com:arielcorte/kopanito-controller-fix.git
cd kopanito-controller-fix
./restore.sh
```

The script will:

1. Make a timestamped local backup.
2. Force Steam Input for Kopanito AppID `399820`.
3. Select Steam's generic gamepad template for matching GameSir devices.
4. Disable reversed face buttons.
5. Patch and validate Kopanito's bundled `scripts/all.js`.

Start Steam again when the script finishes, then launch Kopanito.

## Reset corrupted in-game bindings

The normal restore leaves your Kopanito profile alone. If controller slots or bindings became corrupted while diagnosing the game, run:

```bash
./restore.sh --reset-profile
```

This enables the first two controller layouts, disables layouts 3 and 4, and restores Kopanito's default gamepad assignments.

## Verify the installation

Quit Steam first so it cannot rewrite controller configuration during the check, then run:

```bash
./verify.sh
```

## Non-default Steam libraries

The scripts expect the main Steam directory at `~/.local/share/Steam`. Set these variables if your setup differs:

```bash
STEAM_ROOT=/path/to/Steam \
KOPANITO_EXE='/path/to/SteamLibrary/steamapps/common/Kopanito All-Stars Soccer/kopanito' \
./restore.sh
```

Use `KOPANITO_PROFILE` as well if `player1.gz` is stored somewhere else.

## Backups and rollback

Each restore creates a directory under:

```text
~/.local/share/kopanito-controller-fix/backups/YYYYMMDD-HHMMSS/
```

The backup contains the executable, profile when present, and each Steam VDF file changed by the restore. To roll back, keep Steam and Kopanito closed and copy the files from one timestamped backup to their original paths.

## Important

Steam's "Verify integrity of game files" replaces the patched executable. Run `./restore.sh` again afterward.

The patch matches Kopanito v1.0.7's minified JavaScript exactly. It stops with an error instead of guessing if a future game build changes that code.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
