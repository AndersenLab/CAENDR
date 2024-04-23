import os

from caendr.services.cloud.postgresql import health_database_status
from caendr.services.logger import logger

from caendr.models.datastore import Species, PhenotypeReport
from caendr.models.sql       import DbOp, WormbaseGene, WormbaseGeneSummary, Strain, StrainAnnotatedVariant, PhenotypeDatabase, PhenotypeMetadata
from caendr.services.sql     import DatabaseManager

from seed_trait_files import populate_andersenlab_trait_files


def execute_operation(db, db_op: DbOp, species=None, reload_files=True):
  '''
    Execute a database operation.

    The given database object (`db`) should be initialized with a Flask app object. That app will be used as the context for the db operation(s).
  '''
  logger.info(f'Executing {db_op.name}...')

  if db_op == DbOp.DROP_AND_POPULATE_ALL_TABLES:
    drop_and_populate_all_tables(db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_STRAINS:
    drop_and_populate_strains(db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_WORMBASE_GENES:
    drop_and_populate_wormbase_genes(db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS:
    drop_and_populate_strain_annotated_variants(db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_PHENOTYPE_DB:
    drop_and_populate_phenotype_db(db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_PHENOTYPE_METADATA:
    drop_and_populate_phenotype_metadata(db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_PHENOTYPES:
    drop_and_populate_phenotypes(db, species, reload_files=reload_files)

  elif db_op == DbOp.POPULATE_PHENOTYPES_DATASTORE:
    populate_andersenlab_trait_files()

  elif db_op == DbOp.TEST_ECHO:
    result, message = health_database_status()
    if not result:
      raise Exception(f"DB Connection is: { ('OK' if result else 'ERROR') }. {message}")

  elif db_op == DbOp.TEST_MOCK_DATA:
    os.environ["USE_MOCK_DATA"] = "1"
    os.environ["MODULE_DB_OPERATIONS_CONNECTION_TYPE"] = "memory"
    logger.info("Using MOCK DATA")
    drop_and_populate_all_tables(db, species)

  elif db_op == DbOp.RECOMPUTE_PHENOTYPE_REPORT_CACHED_NAMES:
    PhenotypeReport.recompute_cached_display_names()



def drop_and_populate_strains(db, species, reload_files=True):

  # Initialize ETL Manager
  db_manager = DatabaseManager(db, reload_files=reload_files)

  # Drop relevant tables
  db_manager.clear_tables( Strain, species_list=species )

  # Fetch and load data using ETL Manager
  db_manager.load_tables( Strain, species_list=species )


def drop_and_populate_wormbase_genes(db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (wb_ver = {val.wb_ver})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating wormbase genes. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  db_manager = DatabaseManager(db, reload_files=reload_files)

  # Drop relevant tables
  logger.info(f"Dropping tables...")
  db_manager.clear_tables( WormbaseGeneSummary, WormbaseGene, species_list=species )

  # Fetch and load data using ETL Manager
  logger.info("Loading wormbase genes...")
  db_manager.load_tables(WormbaseGeneSummary, WormbaseGene, species_list=species)
  # db_manager.load_homologs(db)
  # db_manager.load_orthologs(db)


def drop_and_populate_strain_annotated_variants(db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating strain annotated variants. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  db_manager = DatabaseManager(db, reload_files=reload_files)

  # Drop relevant table
  logger.info(f"Dropping table...")
  db_manager.clear_tables(StrainAnnotatedVariant, species_list=species)

  # Fetch and load data using ETL Manager
  logger.info("Loading strain annotated variants...")
  db_manager.load_tables(StrainAnnotatedVariant, species_list=species)


def drop_and_populate_phenotype_db(db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating phenotype database. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  db_manager = DatabaseManager(db, reload_files=reload_files)

  # Drop relevant table
  logger.info(f"Dropping table...")
  db_manager.clear_tables(PhenotypeDatabase, species_list=species)

  # Fetch and load data using ETL Manager
  logger.info("Loading phenotypes...")
  db_manager.load_tables(PhenotypeDatabase, species_list=species)

def drop_and_populate_phenotype_metadata(db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating phenotype metadata. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  db_manager = DatabaseManager(db, reload_files=reload_files)

  # Drop relevant table
  logger.info(f"Dropping table...")
  db_manager.clear_tables(PhenotypeMetadata, species_list=species)

  # Fetch and load data using ETL Manager
  logger.info("Loading phenotypes...")
  db_manager.load_tables(PhenotypeMetadata, species_list=species)

def drop_and_populate_phenotypes(db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating phenotypes. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  db_manager = DatabaseManager(db, reload_files=reload_files)

  # Drop relevant table
  logger.info(f"Dropping table...")
  db_manager.clear_tables(PhenotypeMetadata, PhenotypeDatabase, species_list=species)

  # Fetch and load data using ETL Manager
  logger.info("Loading phenotypes...")
  db_manager.load_tables(PhenotypeMetadata, PhenotypeDatabase, species_list=species)


def drop_and_populate_all_tables(db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (wb_ver = {val.wb_ver}, release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating all tables. Species list: [ {", ".join(spec_strings)} ]')

  logger.info("[1/8] Downloading databases...eta ~0:15")
  db_manager = DatabaseManager(db, reload_files=reload_files)

  logger.info("[2/8] Dropping tables...eta ~0:01")
  db_manager.clear_tables(species_list=species)

  logger.info("[3/8] Load Strains...eta ~0:24")
  db_manager.load_tables(Strain, species_list=species)

  logger.info("[4/8] Load genes summary...eta ~3:15")
  db_manager.load_tables(WormbaseGeneSummary, species_list=species)

  logger.info("[5/8] Load genes...eta ~12:37")
  db_manager.load_tables(WormbaseGene, species_list=species)

  # logger.info("[6/8] Load Homologs...eta ~3:10")
  # db_manager.load_homologs(db)

  # logger.info("[7/8] Load Horthologs...eta ~17:13")
  # db_manager.load_orthologs(db)

  logger.info("[6/8] Load Strains Annotated Variants...eta ~26:47")
  db_manager.load_tables(StrainAnnotatedVariant, species_list=species)

  logger.info("[7/8] Load Phenotype Database...")
  db_manager.load_tables(PhenotypeDatabase, species_list=species)

  logger.info("[8/8] Load Phenotype Metadata...")
  db_manager.load_tables(PhenotypeMetadata, species_list=species)
