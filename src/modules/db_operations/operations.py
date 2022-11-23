import os
from caendr.services.cloud.postgresql import health_database_status
from logzero import logger

from caendr.models.error import EnvVarError
from caendr.models.sql import WormbaseGene, WormbaseGeneSummary, Strain, Homolog, StrainAnnotatedVariant
from caendr.services.sql.db import drop_tables, backup_external_db
from caendr.services.sql.etl import ETLManager, load_strains
from caendr.services.sql.species import Species



def execute_operation(app, db, DB_OP):
  
  # Get the path to the JSON file containing the list of species and their attributes
  SPECIES_LIST_FILE = os.environ['SPECIES_LIST_FILE']
  logger.info(f'Executing {DB_OP} -- SPECIES_LIST_FILE: "{SPECIES_LIST_FILE}"')

  if DB_OP == 'DROP_AND_POPULATE_ALL_TABLES':
    species_list = parse_species_list(SPECIES_LIST_FILE)
    drop_and_populate_all_tables(app, db, species_list)

  elif DB_OP == 'DROP_AND_POPULATE_STRAINS':
    drop_and_populate_strains(app, db)

  elif DB_OP == 'DROP_AND_POPULATE_WORMBASE_GENES':
    species_list = parse_species_list(SPECIES_LIST_FILE)
    drop_and_populate_wormbase_genes(app, db, species_list)

  elif DB_OP == 'DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS':
    species_list = parse_species_list(SPECIES_LIST_FILE)
    drop_and_populate_strain_annotated_variants(app, db, species_list)

  elif DB_OP == 'TEST_ECHO':
    result, message = health_database_status()
    if not result:
      raise Exception(f"DB Connection is: { ('OK' if result else 'ERROR') }. {message}")

  elif DB_OP == 'TEST_MOCK_DATA':
    os.environ["USE_MOCK_DATA"] = "1"
    os.environ["MODULE_DB_OPERATIONS_CONNECTION_TYPE"] = "memory"
    logger.info("Using MOCK DATA")
    species_list = parse_species_list(SPECIES_LIST_FILE)
    drop_and_populate_all_tables(app, db, species_list)


def parse_species_list(species_list_file):
  if not species_list_file:
    raise EnvVarError()
  return Species.parse_json_file(species_list_file)


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
  drop_tables(app, db, tables=[Homolog.__table__, WormbaseGene.__table__])
  drop_tables(app, db, tables=[WormbaseGeneSummary.__table__])

  # Fetch and load data using ETL Manager
  logger.ingo("Loading wormbase genes...")
  etl_manager.load_genes_summary(db)
  etl_manager.load_genes(db)
  etl_manager.load_homologs(db)
  etl_manager.load_orthologs(db)


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

  logger.info("[1/8] Downloading databases...eta ~0:15")
  etl_manager = ETLManager(species_list)

  logger.info("[2/8] Dropping tables...eta ~0:01")
  drop_tables(app, db)

  logger.info("[3/8] Load Strains...eta ~0:24")
  load_strains(db)

  logger.info("[4/8] Load genes summary...eta ~3:15")
  etl_manager.load_genes_summary(db)

  logger.info("[5/8] Load genes...eta ~12:37")
  etl_manager.load_genes(db)

  logger.info("[6/8] Load Homologs...eta ~3:10")
  etl_manager.load_homologs(db)

  logger.info("[7/8] Load Horthologs...eta ~17:13")
  etl_manager.load_orthologs(db)

  logger.info("[8/8] Load Strains Annotated Variants...eta ~26:47")
  etl_manager.load_strain_annotated_variants(db)
  