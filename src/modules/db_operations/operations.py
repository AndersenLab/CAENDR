import os
from caendr.services.cloud.postgresql import health_database_status
from logzero import logger

from caendr.models.error import EnvVarError
from caendr.models.sql import WormbaseGene, WormbaseGeneSummary, Strain, Homolog, StrainAnnotatedVariant
from caendr.services.sql.db import drop_tables, backup_external_db
from caendr.services.sql.etl import ETLManager, load_strains



def execute_operation(app, db, DB_OP):
  WORMBASE_VERSION = os.environ.get('WORMBASE_VERSION')
  STRAIN_VARIANT_ANNOTATION_VERSION = os.environ.get('STRAIN_VARIANT_ANNOTATION_VERSION')
  
  logger.info(f'Executing {DB_OP}: WORMBASE_VERSION:{WORMBASE_VERSION} STRAIN_VARIANT_ANNOTATION_VERSION:{STRAIN_VARIANT_ANNOTATION_VERSION}')

  if DB_OP == 'DROP_AND_POPULATE_ALL_TABLES':
    if not WORMBASE_VERSION or not STRAIN_VARIANT_ANNOTATION_VERSION:
      raise EnvVarError()
    drop_and_populate_all_tables(app, db, WORMBASE_VERSION, STRAIN_VARIANT_ANNOTATION_VERSION)
    
  elif DB_OP == 'DROP_AND_POPULATE_STRAINS':
    drop_and_populate_strains(app, db)
    
  elif DB_OP == 'DROP_AND_POPULATE_WORMBASE_GENES':
    if not WORMBASE_VERSION:
      raise EnvVarError()
    drop_and_populate_wormbase_genes(app, db, WORMBASE_VERSION)

  elif DB_OP == 'DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS':
    if not STRAIN_VARIANT_ANNOTATION_VERSION:
      raise EnvVarError()
    drop_and_populate_strain_annotated_variants(app, db, STRAIN_VARIANT_ANNOTATION_VERSION)
  
  elif DB_OP == 'TEST_ECHO':
    result, message = health_database_status()
    if not result:
      raise Exception(f"DB Connection is: { ('OK' if result else 'ERROR') }. {message}")

  elif DB_OP == 'TEST_MOCK_DATA':
    os.environ["USE_MOCK_DATA"] = "1"
    os.environ["MODULE_DB_OPERATIONS_CONNECTION_TYPE"] = "memory"
    logger.info("Using MOCK DATA")
    drop_and_populate_all_tables(app, db, WORMBASE_VERSION, STRAIN_VARIANT_ANNOTATION_VERSION)


def drop_and_populate_strains(app, db):
  drop_tables(app, db, tables=[Strain.__table__])
  load_strains(db)


def drop_and_populate_wormbase_genes(app, db, wb_ver: str):
  logger.info(f"Running Drop and Populate wormbase genes with version: {wb_ver}")

  # Initialize ETL Manager
  etl_manager = ETLManager(wb_ver=wb_ver)

  # Drop relevant tables
  drop_tables(app, db, tables=[Homolog.__table__, WormbaseGene.__table__])
  drop_tables(app, db, tables=[WormbaseGeneSummary.__table__])

  # Fetch and load data using ETL Manager
  etl_manager.load_genes_summary(db)
  etl_manager.load_genes(db)
  etl_manager.load_homologs(db)
  etl_manager.load_orthologs(db)


def drop_and_populate_strain_annotated_variants(app, db, sva_ver: str):

  # Initialize ETL Manager
  etl_manager = ETLManager(sva_ver=sva_ver)

  # Drop relevant table
  logger.info(f"Dropping table...")
  db.session.commit()
  drop_tables(app, db, tables=[StrainAnnotatedVariant.__table__])

  # Fetch and load data using ETL Manager
  logger.info("Loading strain annotated variants...")
  etl_manager.load_strain_annotated_variants(db)


def drop_and_populate_all_tables(app, db, wb_ver: str, sva_ver: str):
  logger.info(f'Dropping and populating all tables - WORMBASE_VERSION: {wb_ver} STRAIN_VARIANT_ANNOTATION_VERSION: {sva_ver}')

  logger.info("[1/8] Downloading databases...eta ~0:15")
  etl_manager = ETLManager(wb_ver=wb_ver, sva_ver=sva_ver)

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
  