#!/usr/bin/env python
import argparse
import os
import sys
from pathlib import Path


def add_project_root_to_path(project_root):
    project_root = str(Path(project_root).resolve())
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description='Export the configured MySQL Django database to SQLite.'
    )
    parser.add_argument(
        '--sqlite-path',
        type=Path,
        required=True,
        help='Destination SQLite database file path.',
    )
    parser.add_argument(
        '--env-file',
        type=Path,
        default=None,
        help='Optional .env file. Defaults to .env in the project root when present.',
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Replace the SQLite file if it already exists.',
    )
    return parser.parse_args(argv)


def load_env_file(path):
    if not path or not path.exists():
        return

    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue

        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def build_sqlite_database_config(sqlite_path, timeout):
    return {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(sqlite_path),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
        'OPTIONS': {
            'timeout': timeout,
        },
        'TIME_ZONE': None,
        'CONN_HEALTH_CHECKS': False,
        'CONN_MAX_AGE': 0,
        'AUTOCOMMIT': True,
        'ATOMIC_REQUESTS': False,
        'TEST': {
            'CHARSET': None,
            'COLLATION': None,
            'MIGRATE': True,
            'MIRROR': None,
            'NAME': None,
        },
    }


def _configure_django(sqlite_path):
    project_root = Path(__file__).resolve().parent.parent
    add_project_root_to_path(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoblog.settings')
    os.environ['DJANGO_DATABASE_ENGINE'] = 'mysql'

    import django

    django.setup()

    from django.conf import settings
    from django.db import connections

    mysql_config = settings.DATABASES['default'].copy()
    sqlite_config = build_sqlite_database_config(
        sqlite_path,
        timeout=int(os.environ.get('DJANGO_SQLITE_TIMEOUT') or 30),
    )
    settings.DATABASES['mysql_source'] = mysql_config
    settings.DATABASES['sqlite_target'] = sqlite_config
    connections.databases['mysql_source'] = mysql_config
    connections.databases['sqlite_target'] = sqlite_config


def _prepare_destination(path, overwrite):
    path = path.expanduser().resolve()
    if path.exists():
        if not overwrite:
            raise SystemExit(
                f'{path} already exists. Pass --overwrite to replace it.'
            )
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _migrate_sqlite_database():
    from django.core.management import call_command

    call_command(
        'migrate',
        database='sqlite_target',
        interactive=False,
        verbosity=1,
    )
    call_command(
        'flush',
        database='sqlite_target',
        interactive=False,
        verbosity=0,
    )


def _copy_data_to_sqlite():
    from django.apps import apps
    from django.core import serializers
    from django.db import connections, transaction
    from django.core.management.color import no_style

    source = 'mysql_source'
    target = 'sqlite_target'
    total = 0

    with connections[target].cursor() as cursor:
        cursor.execute('PRAGMA foreign_keys = OFF;')

    try:
        for model in apps.get_models():
            if model._meta.proxy or not model._meta.managed:
                continue

            objects = list(model._default_manager.using(source).all())
            if not objects:
                continue

            payload = serializers.serialize('json', objects, use_natural_foreign_keys=False)
            deserialized = serializers.deserialize('json', payload, using=target)
            with transaction.atomic(using=target):
                for item in deserialized:
                    item.save(using=target)

            count = len(objects)
            total += count
            print(f'Copied {model._meta.label}: {count}')
    finally:
        with connections[target].cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = ON;')
            cursor.execute('PRAGMA foreign_key_check;')
            violations = cursor.fetchall()
            if violations:
                raise SystemExit(f'SQLite foreign key check failed: {violations[:10]}')

    sequence_sql = connections[target].ops.sequence_reset_sql(
        no_style(),
        [model for model in apps.get_models() if model._meta.managed and not model._meta.proxy],
    )
    if sequence_sql:
        with connections[target].cursor() as cursor:
            for statement in sequence_sql:
                cursor.execute(statement)

    print(f'Copied {total} rows into SQLite.')


def main(argv=None):
    args = parse_args(argv)
    project_root = Path(__file__).resolve().parent.parent
    load_env_file(args.env_file or project_root / '.env')
    sqlite_path = _prepare_destination(args.sqlite_path, args.overwrite)
    _configure_django(sqlite_path)
    _migrate_sqlite_database()
    _copy_data_to_sqlite()
    print(f'SQLite export complete: {sqlite_path}')


if __name__ == '__main__':
    main(sys.argv[1:])
