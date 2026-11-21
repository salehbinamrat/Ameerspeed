#!/usr/bin/env python3
"""Deterministic, offline MikroTik HotSpot portal packaging.

Builds two distributables: deployable HotSpot files and a source+test archive.
Neither archive contains local cache files or build output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    'index.html', 'login.html', 'alogin.html', 'status.html',
    'logout.html', 'flogin.html', 'fstatus.html', 'redirect.html',
    'css/portal.css', 'js/main.min.js', 'js/md5.js',
    'img/logo.webp', 'img/logo-fallback.png',
)
ASSET_DIRS = ('css', 'font', 'img', 'js')
EXCLUDED_DIRS = {'.git', '.pytest_cache', '.mypy_cache', '__pycache__', 'dist', 'node_modules', '.venv', 'venv'}
EXCLUDED_FILES = {'.DS_Store', 'Thumbs.db'}
# Intentionally fixed ZIP timestamp to make byte-for-byte reproducible builds.
ZIP_DATE = (2026, 11, 21, 0, 0, 0)


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_files(root: Path) -> list[Path]:
    root = root.resolve()
    output = []
    for path in root.rglob('*'):
        rel = path.relative_to(root)
        if any(s in EXCLUDED_DIRS for s in rel.parts):
            continue
        if path.name in EXCLUDED_FILES or path.name.endswith(('.pyc', '.pyo', '.swp', '~')):
            continue
        if any(s.startswith('.env') for s in rel.parts):
            continue
        if path.is_symlink():
            raise ValueError(f'Symlinks are not allowed in deliverables: {rel}')
        if path.is_file():
            output.append(rel)
    return sorted(output, key=lambda p: p.as_posix())


def _portal_files(source: list[Path]) -> list[Path]:
    selected = [p for p in source if (len(p.parts) == 1 and p.suffix.lower() == '.html') or p.parts[0] in ASSET_DIRS]
    names = {p.as_posix() for p in selected}
    missing = sorted(set(REQUIRED) - names)
    if missing:
        raise ValueError('Missing mandatory RouterOS portal files: ' + ', '.join(missing))
    return selected


def _write_zip(source_root: Path, files: list[Path], destination: Path) -> dict:
    records = []
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9, strict_timestamps=True) as archive:
        for rel in files:
            binary = (source_root / rel).read_bytes()
            name = rel.as_posix()
            zi = zipfile.ZipInfo(filename=name, date_time=ZIP_DATE)
            zi.create_system = 3
            zi.external_attr = 0o100644 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(zi, binary, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            records.append({'path': name, 'size': len(binary), 'sha256': _hash(binary)})
    # Verify archive CRC, paths, and exact original contents after writing.
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None or archive.namelist() != [x['path'] for x in records]:
            raise ValueError('Archive failed integrity/ordering checks')
        for row in records:
            if _hash(archive.read(row['path'])) != row['sha256']:
                raise ValueError(f"Archive hash mismatch: {row['path']}")
    return {'name': destination.name, 'files': records, 'sha256': _hash(destination.read_bytes()), 'size': destination.stat().st_size}


def build(source_root: Path = ROOT, out_dir: Path | None = None, source_commit: str = '') -> dict:
    source_root = source_root.resolve()
    out_dir = (out_dir or source_root / 'dist').resolve()
    if out_dir == source_root:
        raise ValueError('Output directory must not be the project root')
    out_dir.mkdir(parents=True, exist_ok=True)
    files = _safe_files(source_root)
    portal = _portal_files(files)
    if any('test' in p.parts or 'docs' in p.parts for p in portal):
        raise ValueError('RouterOS archive contains development-only files')
    package = _write_zip(source_root, portal, out_dir / 'Ameerspeed_RouterOS_Portal.zip')
    source = _write_zip(source_root, files, out_dir / 'Ameerspeed_Source.zip')
    manifest = {
        'project': 'Ameerspeed', 'target': 'MikroTik RouterOS v6 HotSpot (HTML/CSS/JS)',
        'source_commit': source_commit,
        'packages': [package, source],
        'notes': ['Deploy only the content of the RouterOS ZIP to the HotSpot files directory.',
                  'Automated tests cannot verify RouterOS authentication or camera licensing on real devices.'],
    }
    (out_dir / 'MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out_dir / 'SHA256SUMS').write_text(''.join(f"{obj['sha256']}  {obj['name']}\n" for obj in [package, source]), encoding='ascii')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path, default=None)
    parser.add_argument('--commit', default='')
    args = parser.parse_args()
    result = build(args.source, args.out, args.commit)
    for item in result['packages']:
        print(f"BUILT {item['name']}: {len(item['files'])} files, {item['size']} bytes, sha256={item['sha256']}")
