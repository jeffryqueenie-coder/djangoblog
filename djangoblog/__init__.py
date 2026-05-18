try:
    import pymysql
except ImportError:
    pymysql = None

if pymysql is not None:
    pymysql.install_as_MySQLdb()

default_app_config = 'djangoblog.apps.DjangoblogAppConfig'
