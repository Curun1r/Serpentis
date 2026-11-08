# Serpentis 1.10.0

Three distinct mini-boss encounters, HD gameplay and smoother screen transitions.
Includes refreshed screenshots showing the current interface and correct object sizes.

## Mini-bosses with different fighting styles

- **Raider** (wave 3): changes lanes, marks a dive destination, commits to a fast dive and retreats. Fires a three-shot spread.
- **Hunter** (wave 8): follows your position, stops to aim and fires a quick three-round burst at the locked target. Moving after its warning dodges the burst.
- **Warden** (wave 13): patrols along an elliptical path and fires broad fans with alternating escape lanes.
- The roles repeat on waves 18, 23, 28 and onward. Each has its own hull silhouette, accent color and name on the health bar.
- Attack windups remain visible on every difficulty. Cooldowns vary slightly between attacks; low health increases pressure without removing the dodge window.
- Movement and attack timing are checked at 30, 60 and 144 FPS across 4:3, 16:10, 16:9 and 21:9 playfields.

## Display and transitions

- Gameplay geometry, ships and HUD text render directly in HD, starting at Full HD; a 16:10 playfield starts at 1920 × 1200. Explicit lower resolution presets still work.
- Fullscreen follows the connected display; Fill covers the screen and Fit preserves proportions with bars. MacBook displays default to 16:10 while respecting saved choices.
- Aliens and player projectiles retain their intended logical sizes across display modes.
- Screen fades dim the complete frame uniformly. Presentation buffers and HD fonts are reused to reduce allocations during transitions and retries.
- Combat, drawing and transient effects have separate modules, with mini-boss behavior isolated in `mini_boss.py`.

## Downloads

No Python installation is required. Every packaged executable runs a startup check, including all three mini-boss models and attacks, before publication.

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

Existing scores and settings remain compatible.
