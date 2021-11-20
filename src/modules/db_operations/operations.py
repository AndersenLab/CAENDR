import os
from logzero import logger

from caendr.models.error import EnvVarError
from caendr.services.sql.db import (drop_tables, 
                                    download_all_external_dbs, 
                                    backup_external_db)
from caendr.services.sql.etl.strains import load_strains


def execute_operation(app, db, DB_OP):
  logger.info(f'Executing {DB_OP}')
  
  if DB_OP == 'DROP_AND_POPULATE_ALL_TABLES':
    WORMBASE_VERSION = os.environ.get('WORMBASE_VERSION')
    if not WORMBASE_VERSION:
      raise EnvVarError('ERROR: WORMBASE_VERSION is not defined.')
    drop_and_populate_all_tables(app, db, WORMBASE_VERSION)


def drop_and_populate_all_tables(app, db, wb_ver):
  logger.info(f'Dropping all tables and repopulating with WORMBASE_VERSION:{wb_ver}')
  drop_tables(app, db)
  load_strains(db)
  