# Application Configuration
from dotenv import dotenv_values
from logzero import logger

from caendr.services.cloud.secret import get_secret
from caendr.services.cloud.postgresql import db_conn_uri
from caendr.utils.json import json_encoder
from caendr.utils.data import convert_env_bool

SECRETS_IDS = [
  'ANDERSEN_LAB_STRAIN_SHEET',
  'CENDR_PUBLICATIONS_SHEET',
  'ELEVATION_API_KEY',
  'GOOGLE_CLIENT_ID',
  'GOOGLE_CLIENT_SECRET',
  'JWT_SECRET_KEY',
  'PASSWORD_SALT',
  'POSTGRES_DB_PASSWORD',
  'RECAPTCHA_PUBLIC_KEY',
  'RECAPTCHA_PRIVATE_KEY',
  'SECRET_KEY',
  'MAILGUN_API_KEY'
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
  
  config['PERMANENT_SESSION_LIFETIME'] = int(config['PERMANENT_SESSION_LIFETIME'])
  
  for prop in BOOL_PROPS:
    config[prop] = convert_env_bool(config.get(prop))

  config['CAENDR_VERSION'] = f"{config['MODULE_NAME']}-{config['MODULE_VERSION']}"
  config['JWT_TOKEN_LOCATION'] = ['cookies', 'json', 'headers']

  # TODO: clean these up eventually
  config['json_encoder'] = json_encoder

  config['HERITABILITY_CALC_URL'] =  ''
  config['HERITABILITY_CALC_TASK_QUEUE'] = ''
  config['INDEL_PRIMER_URL'] =  ''
  config['INDEL_PRIMER_TASK_QUEUE'] = ''
  config['NEMASCAN_PIPELINE_URL'] =  ''
  config['NEMASCAN_PIPELINE_TASK_QUEUE'] = ''

  config['SQLALCHEMY_DATABASE_URI'] = db_conn_uri
  config['SQLALCHEMY_ENGINE_OPTIONS'] = { "pool_pre_ping": True, "pool_recycle": 300 }
  config['SQLALCHEMY_POOL_TIMEOUT'] = 20

  logger.debug(config)

  # Load secret config values
  for id in SECRETS_IDS:
    config[id] = get_secret(id)

  return config


config = get_config()
