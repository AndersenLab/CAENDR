import os
from caendr.services.cloud.postgresql import health_database_status
from caendr.services.logger import logger

from caendr.models.error import EnvVarError
from caendr.models.datastore import SPECIES_LIST
from caendr.models.sql import WormbaseGene, WormbaseGeneSummary, Strain, StrainAnnotatedVariant
from caendr.services.sql.db import drop_tables, backup_external_db
from caendr.services.sql.etl import ETLManager, load_strains



def execute_operation(app, db, DB_OP):
  logger.info(f'Executing {DB_OP}...')

  if DB_OP == 'DROP_AND_POPULATE_ALL_TABLES':
    drop_and_populate_all_tables(app, db, SPECIES_LIST)

  elif DB_OP == 'DROP_AND_POPULATE_STRAINS':
    drop_and_populate_strains(app, db)

  elif DB_OP == 'DROP_AND_POPULATE_WORMBASE_GENES':
    drop_and_populate_wormbase_genes(app, db, SPECIES_LIST)

  elif DB_OP == 'DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS':
    drop_and_populate_strain_annotated_variants(app, db, SPECIES_LIST)

  elif DB_OP == 'TEST_ECHO':
    result, message = health_database_status()
    if not result:
      raise Exception(f"DB Connection is: { ('OK' if result else 'ERROR') }. {message}")

  elif DB_OP == 'TEST_MOCK_DATA':
    os.environ["USE_MOCK_DATA"] = "1"
    os.environ["MODULE_DB_OPERATIONS_CONNECTION_TYPE"] = "memory"
    logger.info("Using MOCK DATA")
    drop_and_populate_all_tables(app, db, SPECIES_LIST)



def drop_and_populate_strains(app, db):
  drop_tables(app, db, tables=[Strain.__table__])
  load_strains(db)


def drop_and_populate_wormbase_genes(app, db, species_list):

  # Print operation & species info
  spec_strings = [ f'{key} (wb_ver = {val.wb_ver})' for key, val in species_list.items() ]
  logger.info(f'Dropping and populating wormbase genes. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  etl_manager = ETLManager(species_list)

  # Drop relevant tables
  logger.info(f"Dropping tables...")
  drop_tables(app, db, tables=[
    WormbaseGeneSummary.__table__,
    WormbaseGene.__table__,
    # Homolog.__table__,
  ])

  # Fetch and load data using ETL Manager
  logger.info("Loading wormbase genes...")
  etl_manager.load_genes_summary(db)
  etl_manager.load_genes(db)
  # etl_manager.load_homologs(db)
  # etl_manager.load_orthologs(db)


def drop_and_populate_strain_annotated_variants(app, db, species_list):

  # Print operation & species info
  spec_strings = [ f'{key} (sva_ver = {val.sva_ver})' for key, val in species_list.items() ]
  logger.info(f'Dropping and populating strain annotated variants. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  etl_manager = ETLManager(species_list)

  # Drop relevant table
  logger.info(f"Dropping table...")
  db.session.commit()
  drop_tables(app, db, tables=[StrainAnnotatedVariant.__table__])

  # Fetch and load data using ETL Manager
  logger.info("Loading strain annotated variants...")
  etl_manager.load_strain_annotated_variants(db)


def drop_and_populate_all_tables(app, db, species_list):

  # Print operation & species info
  spec_strings = [ f'{key} (wb_ver = {val.wb_ver}, sva_ver = {val.sva_ver})' for key, val in species_list.items() ]
  logger.info(f'Dropping and populating all tables. Species list: [ {", ".join(spec_strings)} ]')

  logger.info("[1/6] Downloading databases...eta ~0:15")
  etl_manager = ETLManager(species_list)

  logger.info("[2/6] Dropping tables...eta ~0:01")
  drop_tables(app, db)

  logger.info("[3/6] Load Strains...eta ~0:24")
  load_strains(db)

  logger.info("[4/6] Load genes summary...eta ~3:15")
  etl_manager.load_genes_summary(db)

  logger.info("[5/6] Load genes...eta ~12:37")
  etl_manager.load_genes(db)

  # logger.info("[6/8] Load Homologs...eta ~3:10")
  # etl_manager.load_homologs(db)

  # logger.info("[7/8] Load Horthologs...eta ~17:13")
  # etl_manager.load_orthologs(db)

  logger.info("[6/6] Load Strains Annotated Variants...eta ~26:47")
  etl_manager.load_strain_annotated_variants(db)
  