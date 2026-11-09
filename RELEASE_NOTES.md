# Serpentis 1.11.1

A refreshed Serpent ship icon, with separate artwork and exports for each desktop platform.

## Application icons

- Replaces the old small ship and SPACE SHOOTER lettering with a large, recognizable Serpent mark.
- **macOS:** dark rounded artwork with transparent outer margins; standard and Retina ICNS representations from 16 to 1024 pixels. The packaged app preserves its native icon while running.
- **Windows:** a transparent multi-size ICO with 16, 20, 24, 32, 40, 48, 64, 128 and 256 pixel representations, including simplified small-size artwork.
- **Linux and running windows:** a bundled 512-pixel transparent PNG. The game sets its window icon before opening the display on supported platforms.
- Icon exports are reproducible with `scripts/build_icons.py` and validated during desktop builds.

## Optional Linux application-menu entry

After extracting the Linux download, run:

```bash
chmod +x Serpentis
./Serpentis --install-desktop
```

This installs the game, icon and application-menu entry into the current user's XDG data folder without administrator privileges or a separate Python installation. Scores and settings are preserved. Re-running the command from a new download updates the installed copy. The archive includes installation and removal instructions.

Paths containing spaces, Cyrillic and reserved characters are covered by real Linux desktop-parser tests. The packaged Linux binary also verifies installation and reinstallation before publication.

## Downloads

No Python installation is required.

- **Windows:** `Serpentis-Windows.exe`
- **macOS:** `Serpentis-macOS.zip` — extract and move `Serpentis.app` to **Applications**.
- **Linux:** `Serpentis-Linux.tar.gz` — extract, then launch `./Serpentis` or use the menu-installation command above.
- **Checksums:** `SHA256SUMS.txt`

Close the previous app before replacing it. If macOS retains an older Dock icon, add the updated app bundle to the Dock again. Source runs through PyCharm may retain the Python application's identity.

### macOS: allow the first launch

The Mac build is not signed with an Apple Developer ID or notarized by Apple. For the copy downloaded from this repository's release:

1. Open `Serpentis.app`. If macOS says **“Apple could not verify Serpentis”**, click **Done**.
2. Open **System Settings → Privacy & Security** and scroll down to **Security**.
3. Click **Open Anyway** beside the Serpentis notice, then confirm **Open** and authenticate if requested.

macOS remembers the exception for this copy of the app. See [Apple's instructions](https://support.apple.com/en-us/102445).

Existing scores and settings remain compatible. Includes all 1.11.0 hit-recovery, checkpoint-saving and FPS improvements. This release changes icons and desktop integration; signing and operating-system trust behavior are unchanged.
