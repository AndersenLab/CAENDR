import os
import traceback
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from logzero import logger
from dotenv import load_dotenv
from logzero import logger
import time
from caendr.services.email import send_email

dotenv_file = '.env'
load_dotenv(dotenv_file)

import monitor
monitor.init_sentry()

from caendr.services.cloud.postgresql import get_db_conn_uri, get_db_timeout, db, health_database_status
from caendr.models.error import EnvVarError
from operations import execute_operation

MODULE_DB_OPERATIONS_BUCKET_NAME = os.environ.get('MODULE_DB_OPERATIONS_BUCKET_NAME')
EXTERNAL_DB_BACKUP_PATH = os.environ.get('EXTERNAL_DB_BACKUP_PATH')
DB_OP = os.environ.get('DATABASE_OPERATION')
EMAIL = os.environ.get('EMAIL', None)

if not DB_OP or not MODULE_DB_OPERATIONS_BUCKET_NAME or not EXTERNAL_DB_BACKUP_PATH:
  raise EnvVarError()

logger.info('Initializing Flask App')
app = Flask(__name__)
app.app_context().push()
app.config['SQLALCHEMY_DATABASE_URI'] = get_db_conn_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() == 'true'

if not os.getenv("MODULE_DB_OPERATIONS_CONNECTION_TYPE"):
  app.config['SQLALCHEMY_ENGINE_OPTIONS'] = { "pool_pre_ping": True, "pool_recycle": 300 }
  app.config['SQLALCHEMY_POOL_TIMEOUT'] = get_db_timeout()

logger.info('Initializing Flask SQLAlchemy')
db.init_app(app)

# test SQL connection
# status, message = health_database_status()
# logger.info(f"SQL Connectivity: { 'OK' if status else 'ERROR ' }. {message}")

start = time.perf_counter()
use_mock_data = os.getenv('USE_MOCK_DATA', False)
text = f"Mock Data: { 'yes' if use_mock_data else 'no' }. (Production should NOT use mock data.)"

elapsed = "{:2f}".format(time.perf_counter() - start)

try:
  # execute_operation(app, db, DB_OP)
  text = text + f"\n\nStatus: OK"
  text = text + f"\nOperation: {DB_OP}"
  text = text + f"\nSite url: {os.getenv('SITE_BASE_URL', 'n/a')}"
  text = text + f"\nProcessed in {elapsed} seconds."
  logger.info(text)
except Exception as e:
  text = text + f"\nStatus: ERROR"
  text = text + f"\nOperation: {DB_OP}"
  text = text + f"\nSite url: {os.getenv('SITE_BASE_URL', 'n/a')}"
  text = text + f"\nProcessed in {elapsed} seconds."
  text = text + f"\n\nError: {e}\n{traceback.format_exc()}"
  logger.error(text)


if EMAIL is not None:
  logger.info(f"Sending email to: {EMAIL}")    
  send_email({"from": "no-reply@elegansvariation.org",
                  "to": EMAIL,
                  "subject": f"ETL finished for operation: {DB_OP} in {elapsed} seconds",
                  "text": text })