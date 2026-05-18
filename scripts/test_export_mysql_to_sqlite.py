import os
import sys
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from scripts.export_mysql_to_sqlite import (
    add_project_root_to_path,
    build_sqlite_database_config,
    load_env_file,
    parse_args,
)


class ExportMysqlToSqliteScriptTest(TestCase):
    def test_parse_args_requires_sqlite_path(self):
        with self.assertRaises(SystemExit):
            parse_args([])

    def test_parse_args_accepts_sqlite_path(self):
        args = parse_args(['--sqlite-path', '/tmp/blog.sqlite3'])

        self.assertEqual(args.sqlite_path, Path('/tmp/blog.sqlite3'))
        self.assertIsNone(args.env_file)
        self.assertFalse(args.overwrite)

    def test_parse_args_supports_overwrite(self):
        args = parse_args(['--sqlite-path', '/tmp/blog.sqlite3', '--overwrite'])

        self.assertTrue(args.overwrite)

    def test_parse_args_accepts_env_file(self):
        args = parse_args([
            '--sqlite-path', '/tmp/blog.sqlite3',
            '--env-file', '/tmp/djangoblog.env',
        ])

        self.assertEqual(args.env_file, Path('/tmp/djangoblog.env'))

    def test_load_env_file_sets_values_without_overriding_existing_env(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / '.env'
            env_path.write_text(
                'DJANGO_MYSQL_USER=file_user\n'
                'DJANGO_MYSQL_PASSWORD=\"quoted password\"\n'
                '# ignored comment\n',
                encoding='utf-8',
            )

            with patch.dict(os.environ, {'DJANGO_MYSQL_USER': 'existing_user'}, clear=False):
                load_env_file(env_path)

                self.assertEqual(os.environ['DJANGO_MYSQL_USER'], 'existing_user')
                self.assertEqual(os.environ['DJANGO_MYSQL_PASSWORD'], 'quoted password')

    def test_add_project_root_to_path_prepends_missing_project_root(self):
        project_root = Path('/tmp/project').resolve()
        with patch.object(sys, 'path', [str(project_root / 'scripts')]):
            add_project_root_to_path(project_root)

            self.assertEqual(sys.path[0], str(project_root))

    def test_add_project_root_to_path_does_not_duplicate_existing_project_root(self):
        project_root = Path('/tmp/project').resolve()
        with patch.object(sys, 'path', [str(project_root), str(project_root / 'scripts')]):
            add_project_root_to_path(project_root)

            self.assertEqual(sys.path, [str(project_root), str(project_root / 'scripts')])

    def test_build_sqlite_database_config_uses_no_database_timezone(self):
        config = build_sqlite_database_config(Path('/tmp/blog.sqlite3'), timeout=30)

        self.assertIsNone(config['TIME_ZONE'])
