"""Write SHA-256 checksums for the three desktop release downloads."""
import argparse
import hashlib
from pathlib import Path

ARTIFACT_NAMES = ('Serpentis-Linux.tar.gz', 'Serpentis-Windows.exe', 'Serpentis-macOS.zip')


def write_checksums(directory: Path) -> Path:
    """Validate every expected artifact before replacing the checksum manifest."""
    directory = Path(directory)
    lines = []
    for name in sorted(ARTIFACT_NAMES):
        artifact = directory / name
        if not artifact.is_file() or artifact.stat().st_size == 0:
            raise ValueError(f'Missing or empty release artifact: {name}')
        digest = hashlib.sha256()
        with artifact.open('rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(chunk)
        # Bare names let a download folder verify the manifest with sha256sum -c.
        lines.append(f'{digest.hexdigest()}  {name}\n')
    output = directory / 'SHA256SUMS.txt'
    output.write_text(''.join(lines), encoding='ascii', newline='\n')
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, help='Folder containing all three release artifacts')
    args = parser.parse_args()
    try:
        output = write_checksums(args.directory)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Cannot generate checksums: {exc}\n')
    print(f'Wrote {output}')


if __name__ == '__main__':
    main()
