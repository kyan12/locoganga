import os

# Vercel exposes serverless functions from /api. Keep Flask happy behind proxy.
os.environ.setdefault('VERCEL', '1')

try:
    import pymysql
    pymysql.install_as_MySQLdb()
except Exception:
    pass

from app import create_app

app = create_app()
