# Serpentis 1.9.1

Fixes oversized aliens and player projectiles in desktop downloads and adds clear first-launch instructions for Mac.

## Consistent sprite sizes

- Matched the built-in sprite scales to the documented configuration used during development. Desktop builds now use the intended **44 × 44** standard alien and **9 × 9** player projectile in logical game pixels, instead of 51 × 51 and 22 × 22.
- All objects share the playfield's proportional display scale. Resolution and aspect changes keep their proportions and collision bounds, without repeatedly resizing the source images.
- Added regression checks across Auto, 16:9, 16:10, 4:3 and 21:9, including Mac Retina and ultrawide display sizes, repeated display changes and all three player ships.
- Release checks now inspect actual sprite dimensions from each built executable, including builds without a local `config.json`.

## Downloads

No Python installation is required.

- **macOS:** `Serpentis-macOS.zip` — extract the archive and move `Serpentis.app` to **Applications**. Follow the first-launch steps below.
- **Windows:** `Serpentis-Windows.exe`
- **Linux:** `Serpentis-Linux.tar.gz` — extract, then run `chmod +x Serpentis && ./Serpentis`.
- **Checksums:** `SHA256SUMS.txt`

### macOS: allow the first launch

The current Mac build is not signed with an Apple Developer ID or notarized by Apple. For the copy downloaded from this repository's release:

1. Open `Serpentis.app`. If macOS says **“Apple could not verify Serpentis”**, click **Done**.
2. Open **System Settings → Privacy & Security** and scroll down to **Security**.
3. Click **Open Anyway** beside the Serpentis notice, then confirm **Open** and authenticate if requested.

macOS remembers the exception for this copy of the app. See [Apple's instructions](https://support.apple.com/en-us/102445).

Existing scores and settings remain compatible. Includes all [1.9.0 features](https://github.com/Curun1r/Serpentis/releases/tag/serpentis_1.9.0): aspect choices, FPS controls and the expanded personal leaderboard.
