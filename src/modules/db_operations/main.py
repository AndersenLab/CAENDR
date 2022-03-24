import os
import traceback
from flask import Flask
from logzero import logger
from dotenv import load_dotenv
import time
from caendr.services.email import send_email
from caendr.models.datastore.database_operation import DatabaseOperation
from caendr.utils import monitor
from google.cloud import storage

from caendr.services.cloud.postgresql import get_db_conn_uri, get_db_timeout, db
from caendr.models.error import EnvVarError
from operations import execute_operation

dotenv_file = '.env'
load_dotenv(dotenv_file)

monitor.init_sentry("db_operations")


MODULE_DB_OPERATIONS_BUCKET_NAME = os.environ.get('MODULE_DB_OPERATIONS_BUCKET_NAME')
ETL_LOGS_BUCKET_NAME = os.environ.get('ETL_LOGS_BUCKET_NAME')
EXTERNAL_DB_BACKUP_PATH = os.environ.get('EXTERNAL_DB_BACKUP_PATH')
DB_OP = os.environ.get('DATABASE_OPERATION')
EMAIL = os.environ.get('EMAIL', None)
OPERATION_ID = os.environ.get('OPERATION_ID', None)

client = storage.Client()

if not DB_OP or not MODULE_DB_OPERATIONS_BUCKET_NAME or not EXTERNAL_DB_BACKUP_PATH:
    raise EnvVarError()


def etl_operation_append_log(message=""):
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
    d = DatabaseOperation(OPERATION_ID)
    d.set_properties(logs=uri)
    d.save()


logger.info('Initializing Flask App')
app = Flask(__name__)
app.app_context().push()
app.config['SQLALCHEMY_DATABASE_URI'] = get_db_conn_uri()
track_modifications = os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() == 'true'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = track_modifications

if not os.getenv("MODULE_DB_OPERATIONS_CONNECTION_TYPE"):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 300}
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = get_db_timeout()

logger.info('Initializing Flask SQLAlchemy')
db.init_app(app)


def run():
    start = time.perf_counter()
    use_mock_data = os.getenv('USE_MOCK_DATA', False)
    text = ""

    try:
        execute_operation(app, db, DB_OP)
        text = text + "\n\nStatus: OK"
        text = text + f"\nOperation: {DB_OP}"
        text = text + f"\nOperation ID: {OPERATION_ID}"
        text = text + f"\nEnvironment: { os.getenv('ENV', 'n/a') }"
    except Exception as e:
        text = text + "\nStatus: ERROR"
        text = text + f"\nOperation: {DB_OP}"
        text = text + f"\nOperation ID: {OPERATION_ID}"
        text = text + f"\nEnvironment: { os.getenv('ENV', 'n/a') }"
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
        text = text + "\nLOGS: not available"

    etl_operation_append_log(text)
    logger.info(text)

    if EMAIL is not None:
        logger.info(f"Sending email to: {EMAIL}")
        send_email({"from": "no-reply@elegansvariation.org",
                    "to": EMAIL,
                    "subject": f"ETL finished for operation: {DB_OP} in {elapsed} seconds",
                    "text": text})


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logger.error(e)
        etl_operation_append_log(e)
