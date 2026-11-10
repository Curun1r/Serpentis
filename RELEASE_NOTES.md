# Serpentis 2.0.0

The finished desktop edition of Serpentis: a Python/pygame space shooter with three ships, distinct boss encounters, a compact flight interface and standalone downloads for macOS, Windows and Linux.

## New in 2.0.0

- **Custom cursor:** a compact interceptor pointer with smooth pale edges, a blue canopy and small engine lights matches the fleet artwork. It is visible in menus, ship selection, settings, results and pause; hidden during combat and the death animation. Pausing brings it back. Native color cursors are preferred, with an in-game fallback where unsupported.
- **Fullscreen app switching:** Command + Tab on macOS and Alt + Tab on Windows/Linux remain available. Switching away pauses the flight and clears movement input. Returning keeps the flight paused until Resume Flight is selected.
- **Minimize:** use the pause-menu button, Command + M on macOS or Alt + M on Windows/Linux. The run and fullscreen preference are preserved.
- **Less obstructive HUD:** a smaller score/wave/lives panel stays in the upper-left corner. Compact wave and boss announcements sit near the bottom, above boss health bars.
- **Smaller standard enemies:** purple aliens are 20% smaller, with matching collision bounds. Other enemy models retain their sizes, consistently across resolutions and aspect ratios.
- **Rebalanced bonuses:** standard purple enemies have a 10% drop chance; Armoured, Zigzag and Shooter enemies have 25%. Bonus types retain their existing distribution, and bosses/mini-bosses still drop a Heart.
- Updated README screenshots and regression coverage for enemy balance, HUD layout, cursor visibility, pause and window focus.

## Included in this edition

Three detailed playable ships; Raider, Hunter and Warden mini-boss roles; multi-phase full bosses; Full HD gameplay rendering and selectable aspect ratios, including MacBook 16:10; measured FPS caps; cached rendering; hit recovery; checkpoint saves; an expanded local leaderboard; and platform-specific application icons.

## Downloads

No Python installation is required.

- **Windows:** `Serpentis-Windows.exe`
- **macOS:** `Serpentis-macOS.zip` — extract and move `Serpentis.app` to **Applications**.
- **Linux:** `Serpentis-Linux.tar.gz` — extract, then launch `./Serpentis`. Optionally run `./Serpentis --install-desktop` to install the application-menu entry and icon for your user.
- **Checksums:** `SHA256SUMS.txt`

Close the previous app before replacing it. Existing scores and settings remain compatible. This release does not add code signing or notarization.

### macOS: allow the first launch

The Mac build is not signed with an Apple Developer ID or notarized by Apple. For the copy downloaded from this repository's release:

1. Open `Serpentis.app`. If macOS says **“Apple could not verify Serpentis”**, click **Done**.
2. Open **System Settings → Privacy & Security** and scroll down to **Security**.
3. Click **Open Anyway** beside the Serpentis notice, then confirm **Open** and authenticate if requested.

macOS remembers the exception for this copy of the app. See [Apple's instructions](https://support.apple.com/en-us/102445).
