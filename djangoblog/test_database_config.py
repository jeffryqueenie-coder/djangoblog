from pathlib import Path
from unittest import TestCase

from djangoblog.database_config import build_database_config


class DatabaseConfigTest(TestCase):
    def test_defaults_to_mysql_configuration(self):
        env = {}

        config = build_database_config(Path('/app'), env)

        self.assertEqual(config['ENGINE'], 'django.db.backends.mysql')
        self.assertEqual(config['NAME'], 'djangoblog')
        self.assertEqual(config['USER'], 'root')
        self.assertEqual(config['PASSWORD'], 'root')
        self.assertEqual(config['HOST'], '127.0.0.1')
        self.assertEqual(config['PORT'], 3306)
        self.assertEqual(config['OPTIONS'], {'charset': 'utf8mb4'})

    def test_builds_sqlite_configuration_from_env_path(self):
        env = {
            'DJANGO_DATABASE_ENGINE': 'sqlite',
            'DJANGO_SQLITE_PATH': '/data/blog.sqlite3',
        }

        config = build_database_config(Path('/app'), env)

        self.assertEqual(config['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(config['NAME'], '/data/blog.sqlite3')
        self.assertEqual(config['OPTIONS']['timeout'], 30)

    def test_builds_sqlite_configuration_relative_to_base_dir(self):
        env = {
            'DJANGO_DATABASE_ENGINE': 'sqlite',
            'DJANGO_SQLITE_PATH': 'var/blog.sqlite3',
        }

        config = build_database_config(Path('/app'), env)

        self.assertEqual(config['NAME'], '/app/var/blog.sqlite3')

    def test_rejects_unknown_database_engine(self):
        with self.assertRaisesRegex(ValueError, 'DJANGO_DATABASE_ENGINE'):
            build_database_config(Path('/app'), {'DJANGO_DATABASE_ENGINE': 'postgres'})
