import os
from caendr.services.cloud.postgresql import health_database_status
from caendr.services.logger import logger

from caendr.models.datastore import Species, PhenotypeReport
from caendr.models.sql import DbOp, WormbaseGene, WormbaseGeneSummary, Strain, Variant, AnnovarAnnotatedVariant, CsqAnnotatedVariant, SnpEffAnnotatedVariant, VepAnnotatedVariant, PhenotypeDatabase, PhenotypeMetadata
from caendr.services.sql.etl import ETLManager

from seed_trait_files import populate_andersenlab_trait_files



def execute_operation(app, db, db_op: DbOp, species=None, reload_files=True):
  logger.info(f'Executing {db_op.name}...')

  if db_op == DbOp.DROP_AND_POPULATE_ALL_TABLES:
    drop_and_populate_all_tables(app, db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_STRAINS:
    drop_and_populate_strains(app, db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_WORMBASE_GENES:
    drop_and_populate_wormbase_genes(app, db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_VARIANTS:
    drop_and_populate_variants(app, db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_ANNOVAR_VARIANTS:
    drop_and_populate_annovar_variants(app, db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_CSQ_VARIANTS:
    drop_and_populate_csq_variants(app, db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_SNPEFF_VARIANTS:
    drop_and_populate_snpeff_variants(app, db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_VEP_VARIANTS:
    drop_and_populate_vep_variants(app, db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_PHENOTYPE_DB:
    drop_and_populate_phenotype_db(app, db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_PHENOTYPE_METADATA:
    drop_and_populate_phenotype_metadata(app, db, species, reload_files=reload_files)

  elif db_op == DbOp.DROP_AND_POPULATE_PHENOTYPES:
    drop_and_populate_phenotypes(app, db, species, reload_files=reload_files)

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
    drop_and_populate_all_tables(app, db, species)

  elif db_op == DbOp.RECOMPUTE_PHENOTYPE_REPORT_CACHED_NAMES:
    PhenotypeReport.recompute_cached_display_names()



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
  etl_manager.clear_tables( AnnovarAnnotatedVariant, CsqAnnotatedVariant, SnpEffAnnotatedVariant, VepAnnotatedVariant, WormbaseGeneSummary, WormbaseGene, species_list=species )

  # Fetch and load data using ETL Manager
  logger.info("Loading wormbase genes...")
  etl_manager.load_tables(WormbaseGeneSummary, WormbaseGene, species_list=species)


def drop_and_populate_variants(app, db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (wb_ver = {val.wb_ver})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating variants. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  etl_manager = ETLManager(app, db, reload_files=reload_files)

  # Drop relevant tables
  logger.info(f"Dropping tables...")
  etl_manager.clear_tables( AnnovarAnnotatedVariant, CsqAnnotatedVariant, SnpEffAnnotatedVariant, VepAnnotatedVariant, Variant, species_list=species )

  # Fetch and load data using ETL Manager
  logger.info("Loading variants...")
  etl_manager.load_tables(Variant, species_list=species)


def drop_and_populate_annovar_variants(app, db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating Annovar variants. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  etl_manager = ETLManager(app, db, reload_files=reload_files)

  # Drop relevant table
  logger.info(f"Dropping table...")
  etl_manager.clear_tables(AnnovarAnnotatedVariant, species_list=species)

  # Fetch and load data using ETL Manager
  logger.info("Loading Annovar annotated variants...")
  etl_manager.load_tables(AnnovarAnnotatedVariant, species_list=species)


def drop_and_populate_csq_variants(app, db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating CSQ variants. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  etl_manager = ETLManager(app, db, reload_files=reload_files)

  # Drop relevant table
  logger.info(f"Dropping table...")
  etl_manager.clear_tables(CsqAnnotatedVariant, species_list=species)

  # Fetch and load data using ETL Manager
  logger.info("Loading CSQ annotated variants...")
  etl_manager.load_tables(CsqAnnotatedVariant, species_list=species)


def drop_and_populate_snpeff_variants(app, db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating SnpEff variants. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  etl_manager = ETLManager(app, db, reload_files=reload_files)

  # Drop relevant table
  logger.info(f"Dropping table...")
  etl_manager.clear_tables(SnpEffAnnotatedVariant, species_list=species)

  # Fetch and load data using ETL Manager
  logger.info("Loading SnpEff annotated variants...")
  etl_manager.load_tables(SnpEffAnnotatedVariant, species_list=species)


def drop_and_populate_vep_variants(app, db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating VEP variants. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  etl_manager = ETLManager(app, db, reload_files=reload_files)

  # Drop relevant table
  logger.info(f"Dropping table...")
  etl_manager.clear_tables(VepAnnotatedVariant, species_list=species)

  # Fetch and load data using ETL Manager
  logger.info("Loading VEP annotated variants...")
  etl_manager.load_tables(VepAnnotatedVariant, species_list=species)


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

def drop_and_populate_phenotype_metadata(app, db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating phenotype metadata. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  etl_manager = ETLManager(app, db, reload_files=reload_files)

  # Drop relevant table
  logger.info(f"Dropping table...")
  etl_manager.clear_tables(PhenotypeMetadata, species_list=species)

  # Fetch and load data using ETL Manager
  logger.info("Loading phenotypes...")
  etl_manager.load_tables(PhenotypeMetadata, species_list=species)

def drop_and_populate_phenotypes(app, db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating phenotypes. Species list: [ {", ".join(spec_strings)} ]')

  # Initialize ETL Manager
  etl_manager = ETLManager(app, db, reload_files=reload_files)

  # Drop relevant table
  logger.info(f"Dropping table...")
  etl_manager.clear_tables(PhenotypeMetadata, PhenotypeDatabase, species_list=species)

  # Fetch and load data using ETL Manager
  logger.info("Loading phenotypes...")
  etl_manager.load_tables(PhenotypeMetadata, PhenotypeDatabase, species_list=species)


def drop_and_populate_all_tables(app, db, species, reload_files=True):

  # Print operation & species info
  spec_strings = [ f'{key} (wb_ver = {val.wb_ver}, release_sva = {val.release_sva})' for key, val in Species.all().items() if (species is None or key in species) ]
  logger.info(f'Dropping and populating all tables. Species list: [ {", ".join(spec_strings)} ]')

  logger.info("[1/12] Downloading databases...eta ~0:15")
  etl_manager = ETLManager(app, db, reload_files=reload_files)

  logger.info("[2/12] Dropping tables...eta ~0:01")
  etl_manager.clear_tables(species_list=species)

  logger.info("[3/12] Load Strains...eta ~0:24")
  etl_manager.load_tables(Strain, species_list=species)

  logger.info("[4/12] Load genes summary...eta ~3:15")
  etl_manager.load_tables(WormbaseGeneSummary, species_list=species)

  logger.info("[5/12] Load genes...eta ~12:37")
  etl_manager.load_tables(WormbaseGene, species_list=species)

  logger.info("[6/12] Load Variants...eta ~26:47")
  etl_manager.load_tables(Variant, species_list=species)

  logger.info("[7/12] Load Annovar Annotated Variants...eta ~26:47")
  etl_manager.load_tables(AnnovarAnnotatedVariant, species_list=species)

  logger.info("[8/12] Load CSQ Annotated Variants...eta ~26:47")
  etl_manager.load_tables(CsqAnnotatedVariant, species_list=species)

  logger.info("[9/12] Load SnpEff Annotated Variants...eta ~26:47")
  etl_manager.load_tables(SnpEffAnnotatedVariant, species_list=species)

  logger.info("[10/12] Load VEP Annotated Variants...eta ~26:47")
  etl_manager.load_tables(VepAnnotatedVariant, species_list=species)

  logger.info("[11/12] Load Phenotype Metadata...")
  # etl_manager.load_phenotype_db(db, species)
  etl_manager.load_tables(PhenotypeMetadata, species_list=species)

  logger.info("[12/12] Load Phenotype Database...")
  # etl_manager.load_phenotype_db(db, species)
  etl_manager.load_tables(PhenotypeDatabase, species_list=species)
  