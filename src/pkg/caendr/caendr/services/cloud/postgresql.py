from curses.ascii import alt
import os
import psycopg2
import pg8000

from caendr.services.logger import logger
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from dotenv import load_dotenv

from caendr.services.cloud.secret import get_secret

dotenv_file = '.env'
load_dotenv(dotenv_file)

db = SQLAlchemy()

GOOGLE_CLOUD_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT_ID')
GOOGLE_CLOUD_REGION = os.environ.get('GOOGLE_CLOUD_REGION')
GOOGLE_CLOUDSQL_SERVICE_ACCOUNT_NAME = os.environ.get('GOOGLE_CLOUDSQL_SERVICE_ACCOUNT_NAME')

MODULE_DB_OPERATIONS_SOCKET_PATH = os.environ.get('MODULE_DB_OPERATIONS_SOCKET_PATH')
MODULE_DB_OPERATIONS_INSTANCE_NAME = os.environ.get('MODULE_DB_OPERATIONS_INSTANCE_NAME')
MODULE_DB_OPERATIONS_DB_NAME = os.environ.get('MODULE_DB_OPERATIONS_DB_NAME')
MODULE_DB_OPERATIONS_DB_STAGE_NAME = os.environ.get('MODULE_DB_OPERATIONS_DB_STAGE_NAME')
MODULE_DB_OPERATIONS_DB_USER_NAME = os.environ.get('MODULE_DB_OPERATIONS_DB_USER_NAME')

POSTGRES_DB_PASSWORD = get_secret('POSTGRES_DB_PASSWORD')


db_instance_uri = f'{GOOGLE_CLOUD_PROJECT_ID}:{GOOGLE_CLOUD_REGION}:{MODULE_DB_OPERATIONS_INSTANCE_NAME}'


db_conn_uri = f'postgresql+psycopg2://{MODULE_DB_OPERATIONS_DB_USER_NAME}:{POSTGRES_DB_PASSWORD}@/{MODULE_DB_OPERATIONS_DB_NAME}?host=/cloudsql/{db_instance_uri}'

alt_db_conn_uri = f'postgresql+pg8000://{MODULE_DB_OPERATIONS_DB_USER_NAME}:{POSTGRES_DB_PASSWORD}@/{MODULE_DB_OPERATIONS_DB_NAME}?unix_sock={MODULE_DB_OPERATIONS_SOCKET_PATH}/{db_instance_uri}/.s.PGSQL.5432'

def get_db_conn_uri():
    connection_type = os.getenv('MODULE_DB_OPERATIONS_CONNECTION_TYPE', "host")
    if connection_type == "localhost":
        return f'postgresql+psycopg2://{MODULE_DB_OPERATIONS_DB_USER_NAME}:{POSTGRES_DB_PASSWORD}@localhost/{MODULE_DB_OPERATIONS_DB_NAME}'
    if connection_type == "host.docker.internal":
        return f'postgresql+psycopg2://{MODULE_DB_OPERATIONS_DB_USER_NAME}:{POSTGRES_DB_PASSWORD}@host.docker.internal/{MODULE_DB_OPERATIONS_DB_NAME}'
    if connection_type == "host":
        return db_conn_uri
    if connection_type == "memory":
        return "sqlite://"
    if connection_type == "file":
        target_file = os.getenv('MODULE_DB_OPERATIONS_CONNECTION_FILE')

        # If filename is provided, use it as the database
        if (target_file != None):
            logger.info(f"SQLITE3 sqlite:///{target_file}")
            return f"sqlite:///{target_file}"

        # Otherwise, create a new temp file
        else:
            import tempfile
            filepath = tempfile.TemporaryFile()
            # file = tempfile.NamedTemporaryFile(delete=False)
            # filepath = file.name
            # file.close()
            logger.info(f"SQLITE3 sqlite:///{filepath.name}")
            return f"sqlite:///{filepath.name}"
    return alt_db_conn_uri


def get_db_timeout():
    timeout = int(os.getenv("MODULE_DB_TIMEOUT", "30" ))
    return timeout

def health_database_status():
    conn_uri = get_db_conn_uri()
    engine = create_engine(conn_uri)
    Session = sessionmaker(bind=engine)
    is_database_working = True
    output = ""

    try:
        # to check database we will execute raw query
        session = Session()
        session.execute('SELECT 1')
    except Exception as e:
        output = str(e)
        is_database_working = False

    return is_database_working, output