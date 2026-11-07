# Serpentis 1.8.0

A refreshed fleet, cohesive menus, automatic Mac display sizing, and more reliable gameplay.

## New Viper design

- Redesigned the green Viper as an emerald interceptor with swept wings, a brighter canopy, layered armour, and twin engine nozzles.
- Added matching paired exhaust trails in flight and updated the hangar and fleet previews.
- Kept Viper's speed, weapons, dash timing, and collision dimensions unchanged.

## Interface

- Unified the main menu, hangar, settings, pause, and results with readable panels and shared button styles.
- Added keyboard navigation, visible focus, an explicit launch button, and an in-game How to Play guide.
- Improved text contrast and replaced unsupported symbols with reliable artwork.
- Updated screenshots and controls documentation.

## Display and macOS

- Enabled Auto resolution by default on macOS, following the current monitor's desktop mode and system scaling.
- Windowed Auto leaves room for system panels; fullscreen uses the monitor's desktop resolution.
- Preserved game proportions on Mac, 4:3 and ultrawide displays, with matching mouse coordinates.
- Fixed the native crash when opening Settings by removing unsafe temporary SDL window wrappers.

## Gameplay fixes

- Movement keys released while paused no longer leave the ship moving after resume.
- Fatal collisions stop further damage and record one result per run.
- Pickups survive wave transitions, including hearts dropped by bosses.
- Shield rams correctly defeat bosses and award their rewards.
- Dash cooldown and distance are consistent across frame rates; movement stays inside the screen.

## Downloads

- **Windows:** `Serpentis-Windows.exe`
- **macOS:** `Serpentis-macOS.zip` — extract and open `Serpentis.app`.
- **Linux:** `Serpentis-Linux.tar.gz` — extract, then run `chmod +x Serpentis && ./Serpentis`.

Existing Serpentis scores and preferences are preserved. Manual display resolution remains available in Settings.
