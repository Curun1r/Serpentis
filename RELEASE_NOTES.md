# Serpentis 1.7.4

This release unifies the game's identity around **Serpentis** and prepares consistent desktop builds.

## Changes

- Centralized the application name, tagline, version, and release tag.
- Updated the menu and loading screen to use the shared identity and display version 1.7.4.
- Standardized the application icon name across desktop builds.
- Fixed Windows icon generation to use a file included in the repository.
- Updated source launchers to install all required dependencies, including NumPy.
- Enabled release builds for `serpentis_*` tags and required lint, tests, and version verification before building.

## Downloads

- **Windows:** `Serpentis-Windows.exe`
- **macOS:** `Serpentis-macOS.zip` — extract and open `Serpentis.app`.
- **Linux:** `Serpentis-Linux.tar.gz` — extract, then run `chmod +x Serpentis && ./Serpentis`.

Gameplay and existing Serpentis save locations are unchanged in this release.
