import os
import psycopg2
import pg8000

from logzero import logger
from flask_sqlalchemy import SQLAlchemy
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

alt_db_conn_uri = f'postgresql+pg8000://{MODULE_DB_OPERATIONS_DB_USER_NAME}:{POSTGRES_DB_PASSWORD}@/{MODULE_DB_OPERATIONS_DB_NAME}?unix_sock=/cloudsql/{db_instance_uri}/.s.PGSQL.5432'
