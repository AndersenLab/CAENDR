import os
from caendr.services.cloud.postgresql import health_database_status
from caendr.services.logger import logger

from caendr.models.datastore import Species
from caendr.models.sql import WormbaseGene, WormbaseGeneSummary, Strain, StrainAnnotatedVariant, PhenotypeDatabase
from caendr.services.sql.db import backup_external_db
from caendr.services.sql.etl import ETLManager

from caendr.services.sql.seed_trait_files import populate_andersenlab_trait_files



def execute_operation(app, db, DB_OP, species=None, reload_files=True):
  logger.info(f'Executing {DB_OP}...')

  if DB_OP == 'DROP_AND_POPULATE_ALL_TABLES':
    drop_and_populate_all_tables(app, db, species, reload_files=reload_files)

  elif DB_OP == 'DROP_AND_POPULATE_STRAINS':
    drop_and_populate_strains(app, db, species, reload_files=reload_files)

  elif DB_OP == 'DROP_AND_POPULATE_WORMBASE_GENES':
    drop_and_populate_wormbase_genes(app, db, species, reload_files=reload_files)

  elif DB_OP == 'DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS':
    drop_and_populate_strain_annotated_variants(app, db, species, reload_files=reload_files)

  elif DB_OP == 'DROP_AND_POPULATE_PHENOTYPE_DB':
    drop_and_populate_phenotype_db(app, db, species, reload_files=reload_files)

  elif DB_OP == 'TEST_ECHO':
    result, message = health_database_status()
    if not result:
      raise Exception(f"DB Connection is: { ('OK' if result else 'ERROR') }. {message}")

  elif DB_OP == 'POPULATE_PHENOTYPES_DATASTORE':
    populate_andersenlab_trait_files()

  elif DB_OP == 'TEST_MOCK_DATA':
    os.environ["USE_MOCK_DATA"] = "1"
    os.environ["MODULE_DB_OPERATIONS_CONNECTION_TYPE"] = "memory"
    logger.info("Using MOCK DATA")
    drop_and_populate_all_tables(app, db, species)



def drop_and_populate_strains(app, db, species, reload_files=True):

  # Initialize ETL Manager
  etl_manager = ETLManager(app, db, reload_files=reload_files)

  # Drop relevant tables
  etl_manager.clear_tables( Strain, species_list=species )

  # Fetch and load data using ETL Manager
  etl_manager.load_tables( Strain, species_list=species )


def drop_and_populate_wormbase_genes(app, db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (wb_ver = {val.wb_ver})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating wormbase genes. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  etl_manager = ETLManager(app, db, reload_files=reload_files)

  # Drop relevant tables
  logger.info(f"Dropping tables...")
  etl_manager.clear_tables( WormbaseGeneSummary, WormbaseGene, species_list=species )

  # Fetch and load data using ETL Manager
  logger.info("Loading wormbase genes...")
  etl_manager.load_tables(WormbaseGeneSummary, WormbaseGene, species_list=species)
  # etl_manager.load_homologs(db)
  # etl_manager.load_orthologs(db)


def drop_and_populate_strain_annotated_variants(app, db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating strain annotated variants. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  etl_manager = ETLManager(app, db, reload_files=reload_files)

  # Drop relevant table
  logger.info(f"Dropping table...")
  etl_manager.clear_tables(StrainAnnotatedVariant, species_list=species)

  # Fetch and load data using ETL Manager
  logger.info("Loading strain annotated variants...")
  etl_manager.load_tables(StrainAnnotatedVariant, species_list=species)


def drop_and_populate_phenotype_db(app, db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating phenotype database. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  etl_manager = ETLManager(app, db, reload_files=reload_files)

  # Drop relevant table
  logger.info(f"Dropping table...")
  etl_manager.clear_tables(PhenotypeDatabase, species_list=species)

  # Fetch and load data using ETL Manager
  logger.info("Loading phenotypes...")
  etl_manager.load_tables(PhenotypeDatabase, species_list=species)


def drop_and_populate_all_tables(app, db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (wb_ver = {val.wb_ver}, release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating all tables. Species list: [ {", ".join(spec_strings)} ]')

  logger.info("[1/7] Downloading databases...eta ~0:15")
  etl_manager = ETLManager(app, db, reload_files=reload_files)

  logger.info("[2/7] Dropping tables...eta ~0:01")
  etl_manager.clear_tables(species_list=species)

  logger.info("[3/7] Load Strains...eta ~0:24")
  etl_manager.load_tables(Strain, species_list=species)

  logger.info("[4/7] Load genes summary...eta ~3:15")
  etl_manager.load_tables(WormbaseGeneSummary, species_list=species)

  logger.info("[5/7] Load genes...eta ~12:37")
  etl_manager.load_tables(WormbaseGene, species_list=species)

  # logger.info("[6/8] Load Homologs...eta ~3:10")
  # etl_manager.load_homologs(db)

  # logger.info("[7/8] Load Horthologs...eta ~17:13")
  # etl_manager.load_orthologs(db)

  logger.info("[6/7] Load Strains Annotated Variants...eta ~26:47")
  etl_manager.load_tables(StrainAnnotatedVariant, species_list=species)

  logger.info("[7/7] Load Phenotype Database...")
  # etl_manager.load_phenotype_db(db, species)
  etl_manager.load_tables(PhenotypeDatabase, species_list=species)
