import os
from caendr.services.cloud.postgresql import health_database_status
from caendr.services.logger import logger

from caendr.models.datastore import SPECIES_LIST
from caendr.models.sql import WormbaseGene, WormbaseGeneSummary, Strain, StrainAnnotatedVariant
from caendr.services.sql.db import drop_tables, backup_external_db
from caendr.services.sql.etl import ETLManager, load_strains



def execute_operation(app, db, DB_OP, species=None):
  logger.info(f'Executing {DB_OP}...')

  if DB_OP == 'DROP_AND_POPULATE_ALL_TABLES':
    drop_and_populate_all_tables(app, db, species)

  elif DB_OP == 'DROP_AND_POPULATE_STRAINS':
    drop_and_populate_strains(app, db, species)

  elif DB_OP == 'DROP_AND_POPULATE_WORMBASE_GENES':
    drop_and_populate_wormbase_genes(app, db, species)

  elif DB_OP == 'DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS':
    drop_and_populate_strain_annotated_variants(app, db, species)

  elif DB_OP == 'TEST_ECHO':
    result, message = health_database_status()
    if not result:
      raise Exception(f"DB Connection is: { ('OK' if result else 'ERROR') }. {message}")

  elif DB_OP == 'TEST_MOCK_DATA':
    os.environ["USE_MOCK_DATA"] = "1"
    os.environ["MODULE_DB_OPERATIONS_CONNECTION_TYPE"] = "memory"
    logger.info("Using MOCK DATA")
    drop_and_populate_all_tables(app, db, species)



def drop_and_populate_strains(app, db, species):
  drop_tables(app, db, species=species, tables=[Strain.__table__])
  load_strains(db, species)


def drop_and_populate_wormbase_genes(app, db, species):

  # Print operation & species info
  spec_strings = [ f'{key} (wb_ver = {val.wb_ver})' for key, val in SPECIES_LIST.items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating wormbase genes. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  etl_manager = ETLManager(db, SPECIES_LIST, reload_files=True)

  # Drop relevant tables
  logger.info(f"Dropping tables...")
  drop_tables(app, db, species=species, tables=[
    WormbaseGeneSummary.__table__,
    WormbaseGene.__table__,
    # Homolog.__table__,
  ])

  # Fetch and load data using ETL Manager
  logger.info("Loading wormbase genes...")
  etl_manager.load_tables(WormbaseGeneSummary, WormbaseGene, species_list=species)
  # etl_manager.load_homologs(db)
  # etl_manager.load_orthologs(db)


def drop_and_populate_strain_annotated_variants(app, db, species):

  # Print operation & species info
  spec_strings = [ f'{key} (release_sva = {val.release_sva})' for key, val in SPECIES_LIST.items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating strain annotated variants. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  etl_manager = ETLManager(db, SPECIES_LIST, reload_files=True)

  # Drop relevant table
  logger.info(f"Dropping table...")
  db.session.commit()
  drop_tables(app, db, species=species, tables=[StrainAnnotatedVariant.__table__])

  # Fetch and load data using ETL Manager
  logger.info("Loading strain annotated variants...")
  etl_manager.load_tables(StrainAnnotatedVariant, species_list=species)


def drop_and_populate_all_tables(app, db, species):

  # Print operation & species info
  spec_strings = [ f'{key} (wb_ver = {val.wb_ver}, release_sva = {val.release_sva})' for key, val in SPECIES_LIST.items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating all tables. Species list: [ {", ".join(spec_strings)} ]')

  logger.info("[1/6] Downloading databases...eta ~0:15")
  etl_manager = ETLManager(db, SPECIES_LIST, reload_files=True)

  logger.info("[2/6] Dropping tables...eta ~0:01")
  drop_tables(app, db, species=species)

  logger.info("[3/6] Load Strains...eta ~0:24")
  load_strains(db, species)

  logger.info("[4/6] Load genes summary...eta ~3:15")
  etl_manager.load_tables(WormbaseGeneSummary, species_list=species)

  logger.info("[5/6] Load genes...eta ~12:37")
  etl_manager.load_tables(WormbaseGene, species_list=species)

  # logger.info("[6/8] Load Homologs...eta ~3:10")
  # etl_manager.load_homologs(db)

  # logger.info("[7/8] Load Horthologs...eta ~17:13")
  # etl_manager.load_orthologs(db)

  logger.info("[6/6] Load Strains Annotated Variants...eta ~26:47")
  etl_manager.load_tables(StrainAnnotatedVariant, species_list=species)
  