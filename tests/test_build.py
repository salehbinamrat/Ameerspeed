"""Tests for release packaging run BEFORE CI build job."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from scripts.build_portal import build, ROOT, _safe_files, _portal_files


class BuildTests(unittest.TestCase):
    def test_all_routeros_files_exist_and_exclude_developer_material(self):
        selected = _portal_files(_safe_files(ROOT))
        names = {p.as_posix() for p in selected}
        self.assertIn('login.html', names)
        self.assertIn('js/md5.js', names)
        self.assertIn('img/logo-fallback.png', names)
        self.assertFalse(any(name.startswith(('tests/', 'docs/', '.github/', 'scripts/')) for name in names))

    def test_reproducible_archives_and_integrity(self):
        with TemporaryDirectory() as a, TemporaryDirectory() as b:
            first = build(ROOT, Path(a), source_commit='test-commit')
            second = build(ROOT, Path(b), source_commit='test-commit')
            for left, right in zip(first['packages'], second['packages']):
                self.assertEqual(left['sha256'], right['sha256'])
                self.assertEqual([e['path'] for e in left['files']], [e['path'] for e in right['files']])
                with ZipFile(Path(a) / left['name']) as archive:
                    self.assertIsNone(archive.testzip())
                    self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))
                    for entry in left['files']:
                        self.assertEqual(hashlib.sha256(archive.read(entry['path'])).hexdigest(), entry['sha256'])
            with ZipFile(Path(a) / 'Ameerspeed_RouterOS_Portal.zip') as portal:
                self.assertNotIn('README.md', portal.namelist())
                self.assertNotIn('.github/workflows/portal-checks.yml', portal.namelist())
                self.assertNotIn('dist/SHA256SUMS', portal.namelist())
            sums = (Path(a) / 'SHA256SUMS').read_text().splitlines()
            self.assertEqual(len(sums), 2)
            self.assertTrue(all(len(line.split('  ')[0]) == 64 for line in sums))


if __name__ == '__main__':
    unittest.main()
