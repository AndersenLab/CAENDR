# Application Configuration
import os
from re import U
from caendr.services.logger import logger

from caendr.services.cloud.secret import get_secret
from caendr.services.cloud.postgresql import get_db_conn_uri, get_db_timeout, health_database_status
from caendr.utils.json import json_encoder
from caendr.utils.env  import list_env_vars, convert_env_bool, convert_env_template

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

MODULE_ENV_VARS = [
  'MODULE_SITE_CONTAINER_NAME',
  'MODULE_SITE_CONTAINER_VERSION',
  'MODULE_SITE_SERVING_STATUS',
  'MODULE_SITE_CLOUDRUN_SA_NAME',
  'MODULE_SITE_BUCKET_PHOTOS_NAME',
  'MODULE_SITE_BUCKET_ASSETS_NAME',
  'MODULE_SITE_BUCKET_PUBLIC_NAME',
  'MODULE_SITE_BUCKET_PRIVATE_NAME',
  'MODULE_SITE_BUCKET_DATASET_RELEASE_NAME',
  'MODULE_SITE_SENTRY_NAME',
  'MODULE_SITE_CART_COOKIE_NAME',
  'MODULE_SITE_CART_COOKIE_AGE_SECONDS',
  'MODULE_SITE_CART_COOKIE_NAME',
  'MODULE_SITE_STRAIN_SUBMISSION_URL',
  'MODULE_SITE_PASSWORD_RESET_EXPIRATION_SECONDS'
]

TEMPLATE_PROPS = []

def get_config():
  ''' Load configuration data from environment variables and the cloud secret store '''
  config = dict()

  # Load environment config values
  config.update(list_env_vars('.env'))
  config.update(list_env_vars('module.env'))

  # ENV vars come from CloudRun, If they exist, override all other envs from .env and module.env
  for key in MODULE_ENV_VARS:
    value = os.getenv(key, None)
    if value is not None:
      config[key] = value


  config['PERMANENT_SESSION_LIFETIME'] = int(config.get('PERMANENT_SESSION_LIFETIME', '86400'))

  for prop in BOOL_PROPS:
    config[prop] = convert_env_bool(config.get(prop))

  for prop in TEMPLATE_PROPS:
    if config.get(prop):
      config[prop] = convert_env_template(config.get(prop))

  config['CAENDR_VERSION'] = f"{config['MODULE_NAME']}-{config['MODULE_VERSION']}"
  config['JWT_TOKEN_LOCATION'] = ['cookies', 'json', 'headers']

  # TODO: clean these up eventually
  config['json_encoder'] = json_encoder

  config['SQLALCHEMY_DATABASE_URI'] = get_db_conn_uri()
  if not os.getenv("MODULE_DB_OPERATIONS_CONNECTION_TYPE") == 'file':
    config['SQLALCHEMY_ENGINE_OPTIONS'] = {
      "pool_pre_ping": True,
      "pool_recycle": 300,
      "pool_reset_on_return": 'commit',
    }
    config['SQLALCHEMY_POOL_TIMEOUT'] = get_db_timeout()

  # Load secret config values
  for id in SECRETS_IDS:
    config[id] = get_secret(id)

  return config


config = get_config()
