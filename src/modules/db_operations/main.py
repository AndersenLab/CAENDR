from re import T
import traceback
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from caendr.services.logger import logger
import time
import json
from caendr.services.email import send_email
from caendr.models.datastore import DatabaseOperation, Species
from caendr.models.error import NotFoundError
from caendr.utils import monitor
from google.cloud import storage

from caendr.utils.env import load_env, get_env_var
load_env('.env')

monitor.init_sentry("db_operations")

from caendr.services.cloud.postgresql import get_db_conn_uri, get_db_timeout, db, health_database_status
from caendr.services.cloud.secret import get_secret
from operations import execute_operation


# Load environment variables
MODULE_DB_OPERATIONS_BUCKET_NAME = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')
ETL_LOGS_BUCKET_NAME             = get_env_var('ETL_LOGS_BUCKET_NAME')
EXTERNAL_DB_BACKUP_PATH          = get_env_var('EXTERNAL_DB_BACKUP_PATH')
DB_OP                            = get_env_var('DATABASE_OPERATION')
EMAIL                            = get_env_var('EMAIL',        can_be_none=True)
OPERATION_ID                     = get_env_var('OPERATION_ID', can_be_none=True)

NO_REPLY_EMAIL = get_secret('NO_REPLY_EMAIL')

client = storage.Client()



def etl_operation_append_log(message = ""):
  if OPERATION_ID is None:
    logger.warning(f"Unable to update database_operation with id: {OPERATION_ID}")    
    return

  bucket = client.get_bucket(ETL_LOGS_BUCKET_NAME)
  filepath = f"logs/etl/{OPERATION_ID}/output"
  uri = f"gs://{ETL_LOGS_BUCKET_NAME}/{filepath}"

  CRLF = "\n"
  blob = bucket.get_blob(filepath)
  if blob is not None:
    old_content = blob.download_as_string()
    new_content = f"{old_content}{CRLF}{message}"
  else:
    blob = storage.Blob(filepath, bucket)
    new_content = f"{message}"

  blob.upload_from_string(new_content)

  # update db operation object
  db_op = DatabaseOperation(OPERATION_ID)
  logger.info(f"Appending logs to database_operation - {db_op.id}")
  db_op.set_properties(logs=uri)
  db_op.save()


logger.info('Initializing Flask App')
app = Flask(__name__)
app.app_context().push()
app.config['SQLALCHEMY_DATABASE_URI'] = get_db_conn_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = get_env_var('SQLALCHEMY_TRACK_MODIFICATIONS', False, var_type=bool)

if not get_env_var("MODULE_DB_OPERATIONS_CONNECTION_TYPE", can_be_none=True):
  app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_reset_on_return": 'commit',
  }
  app.config['SQLALCHEMY_POOL_TIMEOUT'] = get_db_timeout()

logger.info('Initializing Flask SQLAlchemy')
db.init_app(app)


def parse_species_list(species_list):

  # If nothing provided, return None
  if not species_list:
    return None

  # Split on semicolons, strip whitespace, and validate that each element maps to a Species object
  try:
    l = [ s.strip() for s in species_list.split(';') if len(s.strip()) > 0 ]
    for name in l:
      Species.from_name(name)
    return l

  # Intercept Species not found errors to log
  except NotFoundError as ex:
    logger.error(f'Invalid species name in SPECIES_LIST: {ex}')
    raise


def run():
  start = time.perf_counter()
  use_mock_data = get_env_var('USE_MOCK_DATA', False, var_type=bool)

  # Parse species list
  species = parse_species_list( get_env_var('SPECIES_LIST', can_be_none=True) )
  species_string = '[' + ', '.join(species) + ']' if species else 'all'

  text = ""

  try:
    execute_operation(app, db, DB_OP, species=species)
    text = text + f"\n\nStatus: OK"
    text = text + f"\nOperation: {DB_OP}"
    text = text + f"\nOperation ID: {OPERATION_ID}"
    text = text + f"\nEnvironment: { get_env_var('ENV', 'n/a') }"
    text = text + f"\nSpecies: {species_string}"

  except Exception as e:
    text = text + f"\nStatus: ERROR"
    text = text + f"\nOperation: {DB_OP}"
    text = text + f"\nOperation ID: {OPERATION_ID}"
    text = text + f"\nEnvironment: { get_env_var('ENV', 'n/a') }"
    text = text + f"\nSpecies: {species_string}"
    text = text + f"\n\nError: {e}\n{traceback.format_exc()}"
    logger.error(text)

  elapsed = "{:2f}".format(time.perf_counter() - start)
  text = text + f"\nProcessed in {elapsed} seconds."
  text = text + f"\nMock Data: { 'yes' if use_mock_data else 'no' }. (Production should NOT use mock data.)"

  log_filepath = "/google/logs/output"
  try:
    with open(log_filepath, mode='r') as f:
      log_data = f.read()
      text = text + f"\nLOGS: { log_data}"
  except Exception as e:
    logger.warning(f"E_UNABLE_TO_ACCESS_LOGS: {e}")
    text = text + f"\nLOGS: not available"

  etl_operation_append_log(text)
  logger.info(text)

  if EMAIL is not None:
    logger.info(f"Sending email to: {EMAIL}")
    send_email({
      "from": f'CaeNDR <{NO_REPLY_EMAIL}>',
      "to": EMAIL,
      "subject": f"ETL finished for operation: {DB_OP} in {elapsed} seconds",
      "text": text,
    })

if __name__ == "__main__":
  try:    
    run()
  except Exception as e:
    etl_operation_append_log(e)