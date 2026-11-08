# Serpentis 1.9.0

Choose the shape of your next flight, control your frame rate, and explore a fuller history of your best runs.

## Display and frame rate

- Added **Auto, 16:9, 16:10, 4:3 and 21:9** game aspect ratios. The playfield width changes without stretching the ships; menus retain their familiar layout.
- Auto follows the connected monitor's proportions, within a supported 4:3 to 32:9 range. Aspect changes apply to the next flight, including a retry. Existing settings keep the 16:9 default.
- Replaced integer-millisecond frame limiting with precise timing for **30, 60, 120, 144 and 240 FPS**, plus **No Limit**.
- FPS changes apply immediately. An optional live counter shows the measured frame rate in Settings and during play.
- A cap sets the maximum rendering rate; actual performance depends on the hardware and scene, while the monitor's refresh rate limits how many distinct frames it can display.
- Reorganized Settings so the resolution, aspect ratio, FPS, difficulty, fullscreen and counter controls fit together and remain accessible by keyboard.

## Personal records

- Expanded the saved leaderboard from **5 to 100 runs**, with a dedicated screen accessible from the main menu and run results.
- Filter by **ship** and **difficulty**, sort by **score**, **wave** or **date**, and browse eight runs per page with buttons, the keyboard or the mouse wheel.
- New records include the ship, difficulty, date, flight duration and game aspect ratio.
- Kept the compact top-five preview in the main menu and results screen, alongside an **All Records** action.
- Preserved existing scores and all-time bests. Legacy runs remain readable, and unknown durations display as `--:--`.
- Added validation and atomic saves to protect records from malformed data or interrupted writes.

## Startup and desktop releases

- Added consistent source launchers for **macOS, Windows and Linux**. They prepare and reuse a project-local environment, stop on setup errors, and support setup-only and environment-check modes.
- Resolved assets, configuration and source saves independently of the working directory, including when starting from PyCharm or a desktop shortcut.
- Added startup diagnostics, a silent-audio fallback when no audio device is available, and orderly music shutdown before SDL closes.
- Added a bounded startup check that renders **nine screens**, exercises gameplay and audio, and verifies disposable settings and score data without touching player saves.
- CI checks all three desktop platforms and the minimum supported Python version. Each release executable must pass the startup check from an unrelated directory before packaging and upload.
- Desktop downloads include **SHA256SUMS.txt** for file verification.

## Downloads

No Python installation is required for the desktop builds.

- **Windows:** `Serpentis-Windows.exe`
- **macOS:** `Serpentis-macOS.zip` — extract and open `Serpentis.app`.
- **Linux:** `Serpentis-Linux.tar.gz` — extract, then run `chmod +x Serpentis && ./Serpentis`.
- **Checksums:** `SHA256SUMS.txt`

Existing settings and scores remain compatible. This release keeps the refreshed Serpent, Viper and Hydra models introduced in 1.8.0 and 1.8.1.
