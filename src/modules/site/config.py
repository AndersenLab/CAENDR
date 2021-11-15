# Application Configuration
from dotenv import dotenv_values
from logzero import logger

from caendr.services.cloud.secret import get_secret, SECRETS_IDS
from caendr.services.cloud.postgresql import DB_CONN_URI
from caendr.utils.data import json_encoder


def get_config():
  ''' Load configuration data from environment variables and the cloud secret store '''
  config = dict()

  # Load environment config values
  config.update(dotenv_values('.env'))
  config['CAENDR_VERSION'] = f"{config['MODULE_NAME']}-{config['MODULE_VERSION']}"

  # TODO: clean these up eventually
  config['json_encoder'] = json_encoder

  config['HERITABILITY_CALC_URL'] =  ''
  config['HERITABILITY_CALC_TASK_QUEUE'] = ''
  config['INDEL_PRIMER_URL'] =  ''
  config['INDEL_PRIMER_TASK_QUEUE'] = ''
  config['NEMASCAN_PIPELINE_URL'] =  ''
  config['NEMASCAN_PIPELINE_TASK_QUEUE'] = ''

  config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
  config['SQLALCHEMY_DATABASE_URI'] = DB_CONN_URI
  config['SQLALCHEMY_ENGINE_OPTIONS'] = { "pool_pre_ping": True, "pool_recycle": 300 }
  config['SQLALCHEMY_POOL_TIMEOUT'] = 20

  logger.debug(config)

  # Load secret config values
  for id in SECRETS_IDS:
    config[id] = get_secret(id)

  return config


config = get_config()
