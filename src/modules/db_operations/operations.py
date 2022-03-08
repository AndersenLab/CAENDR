import os
from logzero import logger

from caendr.models.error import EnvVarError
from caendr.models.sql import WormbaseGene, WormbaseGeneSummary, Strain, Homolog, StrainAnnotatedVariant
from caendr.services.sql.db import (drop_tables,
                                    download_all_external_dbs,
                                    download_external_db,
                                    backup_external_db,
                                    fetch_internal_db)
from caendr.services.sql.etl import (load_strains, 
                                      load_genes_summary, 
                                      load_genes, 
                                      load_homologs,
                                      load_orthologs,
                                      load_strain_annotated_variants)



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


def drop_and_populate_strains(app, db):
  drop_tables(app, db, tables=[Strain.__table__])
  load_strains(db)

def drop_and_populate_wormbase_genes(app, db, wb_ver: str):
  logger.info(f"Running Drop and Populate wormbase genes with version: {wb_ver}")
  gene_gff_fname = download_external_db('GENE_GFF_URL', wb_ver=wb_ver)
  gene_gtf_fname = download_external_db('GENE_GTF_URL', wb_ver=wb_ver)
  gene_ids_fname = download_external_db('GENE_IDS_URL', wb_ver=wb_ver)
  homologene_fname = download_external_db('HOMOLOGENE_URL')
  ortholog_fname = download_external_db('ORTHOLOG_URL')
  
  drop_tables(app, db, tables=[Homolog.__table__, WormbaseGene.__table__])
  drop_tables(app, db, tables=[WormbaseGeneSummary.__table__])
  load_genes_summary(db, gene_gff_fname)
  load_genes(db, gene_gtf_fname, gene_ids_fname)
  load_homologs(db, homologene_fname)
  load_orthologs(db, ortholog_fname)


def drop_and_populate_strain_annotated_variants(app, db, sva_ver: str):
  sva_fname = fetch_internal_db('SVA_CSVGZ_URL', sva_ver=sva_ver)
  db.session.commit()
  logger.info(f"Dropping table...")
  drop_tables(app, db, tables=[StrainAnnotatedVariant.__table__])
  logger.info("Loading strain annotated variants...")
  load_strain_annotated_variants(db, sva_fname)


def drop_and_populate_all_tables(app, db, wb_ver: str, sva_ver: str):
  logger.info(f'Dropping and populating all tables - WORMBASE_VERSION: {wb_ver} STRAIN_VARIANT_ANNOTATION_VERSION: {sva_ver}')
  logger.info("[1/8] Downloading databases...")
  filenames = download_all_external_dbs(wb_ver)
  gene_gff_fname = filenames['GENE_GFF_URL']
  gene_gtf_fname = filenames['GENE_GTF_URL']
  gene_ids_fname = filenames['GENE_IDS_URL']
  homologene_fname = filenames['HOMOLOGENE_URL']
  ortholog_fname = filenames['ORTHOLOG_URL']
  
  filenames['SVA_CSVGZ_URL'] = fetch_internal_db('SVA_CSVGZ_URL', sva_ver)
  sva_fname = filenames['SVA_CSVGZ_URL']

  logger.info("[2/8] Dropping tables...")
  drop_tables(app, db)

  logger.info("[3/8] Load Strains...")
  load_strains(db)

  logger.info("[4/8] Load Strains...")
  load_genes_summary(db, gene_gff_fname)

  logger.info("[5/8] Load Strains...")
  load_genes(db, gene_gtf_fname, gene_ids_fname)

  logger.info("[6/8] Load Strains...")
  load_homologs(db, homologene_fname)

  logger.info("[7/8] Load Strains...")
  load_orthologs(db, ortholog_fname)

  logger.info("[8/8] Load Strains...")
  load_strain_annotated_variants(db, sva_fname)
  