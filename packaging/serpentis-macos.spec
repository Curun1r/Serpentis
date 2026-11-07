# PyInstaller recipe for a versioned Serpentis.app bundle.
from pathlib import Path
import sys

project_root = Path(SPECPATH).parent
sys.path.insert(0, str(project_root))
from app_info import APP_NAME, APP_VERSION

analysis = Analysis(
    [str(project_root / 'main.py')],
    pathex=[str(project_root)],
    datas=[(str(project_root / 'image'), 'image')],
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    console=False,
)
collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    name=APP_NAME,
)
app = BUNDLE(
    collection,
    name=f'{APP_NAME}.app',
    icon=str(project_root / 'serpentis.icns'),
    bundle_identifier='io.github.curun1r.serpentis',
    info_plist={
        'CFBundleShortVersionString': APP_VERSION,
        'CFBundleVersion': APP_VERSION,
    },
)
