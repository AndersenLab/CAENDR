import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from logzero import logger
from dotenv import load_dotenv

from caendr.services.cloud.postgresql import get_db_conn_uri, get_db_timeout, db
from caendr.models.error import EnvVarError
from operations import execute_operation

import monitor

dotenv_file = '.env'
load_dotenv(dotenv_file)

monitor.init_sentry()


MODULE_DB_OPERATIONS_BUCKET_NAME = os.environ.get('MODULE_DB_OPERATIONS_BUCKET_NAME')
EXTERNAL_DB_BACKUP_PATH = os.environ.get('EXTERNAL_DB_BACKUP_PATH')
DB_OP = os.environ.get('DATABASE_OPERATION')

if not DB_OP or not MODULE_DB_OPERATIONS_BUCKET_NAME or not EXTERNAL_DB_BACKUP_PATH:
  raise EnvVarError()

logger.info('Initializing Flask App')
app = Flask(__name__)
app.app_context().push()
app.config['SQLALCHEMY_DATABASE_URI'] = get_db_conn_uri()
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = { "pool_pre_ping": True, "pool_recycle": 300 }
app.config['SQLALCHEMY_POOL_TIMEOUT'] = get_db_timeout()

logger.info('Initializing Flask SQLAlchemy')
db.init_app(app)

execute_operation(app, db, DB_OP)

