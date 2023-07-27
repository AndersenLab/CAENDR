from curses.ascii import alt
import psycopg2
import pg8000

from caendr.services.logger import logger
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, exc

from caendr.services.cloud.secret import get_secret
from caendr.utils.env import load_env, get_env_var



# Load the env file
load_env('.env')

db = SQLAlchemy()

# GCP Variables
GOOGLE_CLOUD_PROJECT_ID              = get_env_var('GOOGLE_CLOUD_PROJECT_ID')
GOOGLE_CLOUD_REGION                  = get_env_var('GOOGLE_CLOUD_REGION')
GOOGLE_CLOUDSQL_SERVICE_ACCOUNT_NAME = get_env_var('GOOGLE_CLOUDSQL_SERVICE_ACCOUNT_NAME')

# Module Variables
SOCKET_PATH   = get_env_var('MODULE_DB_OPERATIONS_SOCKET_PATH')
INSTANCE_NAME = get_env_var('MODULE_DB_OPERATIONS_INSTANCE_NAME')
DB_NAME       = get_env_var('MODULE_DB_OPERATIONS_DB_NAME')
DB_STAGE_NAME = get_env_var('MODULE_DB_OPERATIONS_DB_STAGE_NAME')
DB_USER_NAME  = get_env_var('MODULE_DB_OPERATIONS_DB_USER_NAME')

DB_PASSWORD   = get_secret('POSTGRES_DB_PASSWORD')


db_instance_uri = f'{GOOGLE_CLOUD_PROJECT_ID}:{GOOGLE_CLOUD_REGION}:{INSTANCE_NAME}'

db_conn_uri     = f'postgresql+psycopg2://{DB_USER_NAME}:{DB_PASSWORD}@/{DB_NAME}?host=/cloudsql/{db_instance_uri}'
alt_db_conn_uri = f'postgresql+pg8000://{DB_USER_NAME}:{DB_PASSWORD}@/{DB_NAME}?unix_sock={SOCKET_PATH}/{db_instance_uri}/.s.PGSQL.5432'



def get_db_conn_uri():
    connection_type = get_env_var('MODULE_DB_OPERATIONS_CONNECTION_TYPE', "host")

    if connection_type == "localhost":
        return f'postgresql+psycopg2://{DB_USER_NAME}:{DB_PASSWORD}@localhost/{DB_NAME}'

    if connection_type == "host":
        return db_conn_uri

    if connection_type == "memory":
        return "sqlite://"

    if connection_type == "file":
        target_file = get_env_var('MODULE_DB_OPERATIONS_CONNECTION_FILE', can_be_none=True)

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
    return get_env_var('MODULE_DB_TIMEOUT', 30, var_type=int)


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


def rollback_on_error(func):
    '''
        Decorator for functions which access the SQLAlchemy database.
        Intercepts SQLAlchemyErrors, rolls back the session, then continues propagation.
    '''
    def inner(*args, **kwargs):

        # Try running & returning from the decorated function
        try:
            return func(*args, **kwargs)

        # Catch & log SQLAlchemy errors
        except exc.SQLAlchemyError as e:
            logger.error(f'Caught SQLAlchemy Error: {e}')
            logger.error('Rolling back session...')

            # Try to rollback the session
            try:
                db.session.rollback()
            except Exception as rollback_err:
                logger.error(f'Exception rolling back session: {rollback_err}')
                raise

            # Re-raise the original error
            raise
    return inner