from logzero import logger

from caendr.models.sql import WormbaseGeneSummary, WormbaseGene, Homolog, StrainAnnotatedVariant

from .wormbase import parse_gene_gtf, parse_gene_gff_summary, parse_orthologs
from .homologs import parse_homologene
from .strain_annotated_variants import parse_strain_variant_annotation_data


# https://github.com/phil-bergmann/2016_DLRW_brain/blob/3f69c945a40925101c58a3d77c5621286ad8d787/brain/data.py



## Generic Table ##

def load_table(self, db, table, generator, fetch_funcs):
    '''
      Generalized function to extract information from one or more downloaded files and load them into
      the CaeNDR database.  Specifically, calls 'fetch_funcs' to generate a list of local filenames,
      passes these to 'generator', and inserts the generated results into 'table'.

      Usually should not be called directly; see other 'load_' functions in this module.

      Args:
        db (SQLAlchemy): [SQLAlchemy db instance to insert into.]
        table (PostGres table): [PostGres table to insert data into.]
        generator (function): [
            A function that takes a species object and a list of local filenames, and generates
            rows of data based on the file(s).
        ]
        fetch_funcs (list): [
            A list of functions that each take a species name and return the name of a local file.
        ]
    '''

    # Initialize a count for the number of entries added
    initial_count = table.query.count()

    # Loop through the name & Species object for each species
    for name, species in self.species_list.items():

        # Fetch relevant dataset(s) and append '.gz' to the names
        filenames = [ fetch(name) for fetch in fetch_funcs ]

        # Load gene table data
        db.session.bulk_insert_mappings(table, generator(species, *filenames, start_idx=table.query.count()))
        db.session.commit()

    # Print how many entries were added
    total_records = table.query.count() - initial_count
    logger.info(f'Inserted {total_records} entries into table {table.__tablename__}')



## Specific Tables ##

def load_genes_summary(self, db):
    '''
      Extracts gene summary from WormBase GFF file and loads it into the CaeNDR database.

      Args:
        db (SQLAlchemy): [SQLAlchemy db instance to insert into.]
    '''
    logger.info('Loading WormBase Gene Summary table')
    self.load_table(
        db,
        table       = WormbaseGeneSummary,
        generator   = parse_gene_gff_summary,
        fetch_funcs = [ self.dataset_manager.fetch_gene_gff_db ]
    )


def load_genes(self, db):
    '''
      Extracts gene information from WormBase GTF and gene ID files, and loads it into the CaeNDR database.

      Args:
        db (SQLAlchemy): [SQLAlchemy db instance to insert into.]
    '''
    logger.info('Loading WormBase Gene table')
    self.load_table(
        db,
        table       = WormbaseGene,
        generator   = parse_gene_gtf,
        fetch_funcs = [ self.dataset_manager.fetch_gene_gtf_db, self.dataset_manager.fetch_gene_ids_db ]
    )
    # Print a summary of the new table
    results = db.session.query(WormbaseGene.feature, db.func.count(WormbaseGene.feature)) \
                              .group_by(WormbaseGene.feature) \
                              .all()
    result_summary = '\n'.join([f"{k}: {v}" for k, v in results])
    logger.info(f'Gene Summary: {result_summary}')


# def load_orthologs(self, db):
#     '''
#       Extracts ortholog information from WormBase ortholog file and loads it into the CaeNDR database.

#       Args:
#         db (SQLAlchemy): [SQLAlchemy db instance to insert into.]
#     '''
#     logger.info('Loading orthologs from WormBase')
#     self.load_table(
#         db,
#         table       = Homolog,
#         generator   = parse_orthologs,
#         fetch_funcs = [ self.dataset_manager.fetch_ortholog_db ]
#     )


# def load_homologs(self, db):
#     '''
#       Extracts homolog information from NIH file and loads it into the CaeNDR database.

#       Args:
#         db (SQLAlchemy): [SQLAlchemy db instance to insert into.]
#     '''
#     logger.info('Loading homologenes from NIH homologene.data file')
#     self.load_table(
#         db,
#         table       = Homolog,
#         generator   = parse_homologene,
#         fetch_funcs = [ self.dataset_manager.fetch_homologene_db ]
#     )


def load_strain_annotated_variants(self, db):
    '''
      Extracts strain variant annotation information from GCP file and loads it into the CaeNDR database.

      Args:
        db (SQLAlchemy): [SQLAlchemy db instance to insert into.]
    '''
    logger.info('Loading strain variant annotated csv')
    self.load_table(
        db,
        table       = StrainAnnotatedVariant,
        generator   = parse_strain_variant_annotation_data,
        fetch_funcs = [ self.dataset_manager.fetch_sva_db ]
    )
