# Serpentis 1.11.0

Fairer hit recovery, fewer disk writes during combat, and the FPS optimizations from the latest source updates are now included in the desktop downloads.

## Hit recovery

- Taking a hit grants **0.7 seconds of protection** against projectiles and direct enemy contact, including bosses and mini-bosses.
- A visible recovery indicator shows when protection is active. Its duration uses game time, remains consistent across FPS settings and freezes while paused.
- Breaking a shield also grants recovery time, so overlapping projectiles cannot immediately consume a life in the same frame.
- Recovery resets for each new flight. Enemies that escape still cost a life; recovery protects against physical hits rather than missed enemies.

## Record saving

- The HUD updates a new best score immediately in memory; every defeated enemy no longer triggers a synchronous file write.
- Pending best scores are saved at wave transitions, pause, restart/menu, normal exit and the end of a flight.
- Completed flights still produce one leaderboard entry, with atomic file replacement and compatible existing scores.
- A forced process termination or power loss can discard an unsaved improvement from the current wave. Normal exits flush pending progress.

## Performance included in the desktop builds

- Nebula layers are precomposed and reused instead of repeatedly blending dozens of large transparent images.
- Warning effects draw narrow edge strips; pause artwork and scaled sprites are cached.
- Uniform screen tints use direct RGB operations. The HD pixel-art world uses fast final scaling, while menus retain smooth scaling.
- Rendering resolution, fullscreen coverage, playfield proportions and collision geometry remain independent.

## Reproducible setup

- Runtime, development and build dependency versions are pinned, including compatible Python-version markers.
- CI and desktop builds use the same dependency files documented for local development.
- README includes installation, test, lint and release-build commands. Source environment checks verify the required package versions and work offline after setup.

## Downloads

No Python installation is required for these desktop downloads. Each packaged executable must pass its startup check before publication.

- **Windows:** `Serpentis-Windows.exe` — download and run.
- **macOS:** `Serpentis-macOS.zip` — extract and move `Serpentis.app` to **Applications**. Follow the first-launch instructions below.
- **Linux:** `Serpentis-Linux.tar.gz` — extract, then run `chmod +x Serpentis && ./Serpentis`.
- **Checksums:** `SHA256SUMS.txt`

### macOS: allow the first launch

The Mac build is not signed with an Apple Developer ID or notarized by Apple. For the copy downloaded from this repository's release:

1. Open `Serpentis.app`. If macOS says **“Apple could not verify Serpentis”**, click **Done**.
2. Open **System Settings → Privacy & Security** and scroll down to **Security**.
3. Click **Open Anyway** beside the Serpentis notice, then confirm **Open** and authenticate if requested.

macOS remembers the exception for this copy of the app. See [Apple's instructions](https://support.apple.com/en-us/102445).

Existing scores and settings remain compatible. Includes Raider, Hunter and Warden mini-boss encounters from 1.10.0.
