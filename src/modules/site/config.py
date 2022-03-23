# Application Configuration
from dotenv import dotenv_values

from caendr.services.cloud.secret import get_secret
from caendr.services.cloud.postgresql import get_db_conn_uri, get_db_timeout
from caendr.utils.json import json_encoder
from caendr.utils.data import convert_env_bool

SECRETS_IDS = [
    'ANDERSEN_LAB_STRAIN_SHEET',
    'CENDR_PUBLICATIONS_SHEET',
    'ELEVATION_API_KEY',
    'GOOGLE_CLIENT_ID',
    'GOOGLE_CLIENT_SECRET',
    'JWT_SECRET_KEY',
    'PASSWORD_PEPPER',
    'POSTGRES_DB_PASSWORD',
    'RECAPTCHA_PUBLIC_KEY',
    'RECAPTCHA_PRIVATE_KEY',
    'SECRET_KEY',
    'MAILGUN_API_KEY',
    'CC_EMAILS'
]

BOOL_PROPS = [
    'DEBUG',
    'TESTING',
    'SQLALCHEMY_ECHO',
    'SQLALCHEMY_TRACK_MODIFICATIONS',
    'JSON_SORT_KEYS',
    'SESSION_COOKIE_HTTPONLY',
    'SESSION_COOKIE_SECURE',
    'DEBUG_TB_INTERCEPT_REDIRECTS',
    'TEMPLATE_AUTO_RELOAD',
    'JWT_COOKIE_SECURE',
    'JWT_CSRF_IN_COOKIES',
    'JWT_COOKIE_CSRF_PROTECT',
    'JWT_CSRF_CHECK_FORM'
]


def get_config():
    ''' Load configuration data from environment variables and the cloud secret store '''
    config = dict()

    # Load environment config values
    config.update(dotenv_values('.env'))
    config['PERMANENT_SESSION_LIFETIME'] = int(config.get('PERMANENT_SESSION_LIFETIME', '86400'))

    for prop in BOOL_PROPS:
        config[prop] = convert_env_bool(config.get(prop))

    config['CAENDR_VERSION'] = f"{config['MODULE_NAME']}-{config['MODULE_VERSION']}"
    config['JWT_TOKEN_LOCATION'] = ['cookies', 'json', 'headers']

    # TODO: clean these up eventually
    config['json_encoder'] = json_encoder

    config['SQLALCHEMY_DATABASE_URI'] = get_db_conn_uri()
    config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 300}
    config['SQLALCHEMY_POOL_TIMEOUT'] = get_db_timeout()

    # Load secret config values
    for id in SECRETS_IDS:
        config[id] = get_secret(id)

    return config


config = get_config()
