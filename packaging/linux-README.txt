Serpentis for Linux

Extract the complete archive, then launch:
    chmod +x Serpentis
    ./Serpentis

Optional application-menu installation (no administrator privileges or system
Python installation required):
    ./Serpentis --install-desktop

This copies the executable, icon and menu entry into your per-user XDG data
folder (normally ~/.local/share). You can then open Serpentis from your desktop
environment's application menu. It does not create a desktop shortcut or modify
your scores/settings. Running the command again updates that installed copy.

To remove the optional menu installation, delete these application files:
    ~/.local/share/Serpentis/app/
    ~/.local/share/applications/io.github.curun1r.serpentis.desktop
    ~/.local/share/icons/hicolor/512x512/apps/io.github.curun1r.serpentis.png

If XDG_DATA_HOME is configured, use that directory instead of ~/.local/share.
Keep the rest of the Serpentis data directory to preserve scores and settings.
