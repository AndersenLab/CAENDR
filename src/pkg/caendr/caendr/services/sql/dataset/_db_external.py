from logzero import logger

from ._db import fetch_db



## General fetch functions ##

def fetch_external_db(self, *args, **kwargs):
    '''
      Downloads an external (WormBase, etc.) database file and stores it locally.
      Takes the same positional and keyword arguments as fetch_db, except for db_type.
        Returns:
          str: [The downloaded file's local filename.]
    '''
    return fetch_db(self, 'external', *args, **kwargs)


def prefetch_all_external_dbs(self, **kwargs):
    '''
      Downloads all external DB files and saves them locally.
      Accepts all keyword args of fetch_external_db, except species_name.
    '''
    logger.info('Downloading All External DBs...')

    # Download all files that depend on species
    for species_name in self.species_list.keys():
        for url_template_name in self.specific_template_names:
            self.fetch_external_db(url_template_name, species_name, **kwargs)

    # Download all files that don't depend on species
    for url_template_name in self.generic_template_names:
        self.fetch_external_db(url_template_name, None, **kwargs)

    logger.info('Finished Downloading All External Data.')



## Specific fetch functions ##

def fetch_gene_gtf_db(self, species, **kwargs):
    '''
      Fetches WormBase gene GTF file. Accepts all keyword args of fetch_external_db, except species_name.
        Args:
          species (str): [Name of species to retrieve DB file for.]
        Returns:
          gene_gtf_fname (str): [path of downloaded wormbase gene gtf.gz file]
    '''
    return self.fetch_external_db('GENE_GTF', species, **kwargs)


def fetch_gene_gff_db(self, species, **kwargs):
    '''
      Fetches WormBase gene GFF file. Accepts all keyword args of fetch_external_db, except species_name.
        Args:
          species (str): [Name of species to retrieve DB file for.]
        Returns:
          gene_gff_fname (str): [Path of downloaded wormbase gene gff file.]
    '''
    return self.fetch_external_db('GENE_GFF', species, **kwargs)


def fetch_gene_ids_db(self, species, **kwargs):
    '''
      Fetches WormBase gene IDs file. Accepts all keyword args of fetch_external_db, except species_name.
        Args:
          species (str): [Name of species to retrieve DB file for.]
        Returns:
          gene_ids_fname (str): [path of downloaded wormbase gene IDs file]
    '''
    return self.fetch_external_db('GENE_IDS', species, **kwargs)


# def fetch_ortholog_db(self, species, **kwargs):
#     '''
#       Fetches WormBase orthologs file. Accepts all keyword args of fetch_external_db, except species_name.
#         Args:
#           species (str): [Name of species to retrieve DB file for.]
#         Returns:
#           ortholog_fname (str): [path of downloaded wormbase homologs file]
#     '''
#     return self.fetch_external_db('ORTHOLOG', species, **kwargs)


# def fetch_homologene_db(self, species = None, **kwargs):
#     '''
#       Fetches homologene file. Accepts all keyword args of fetch_external_db, except species_name.
#         Returns:
#           homologene_fname (str): [path of downloaded homologene file]
#     '''
#     if species is not None:
#       logger.warn(f'Homologene does not take a species; discarding argument "{species}".')
#     return self.fetch_external_db('HOMOLOGENE', None, **kwargs)


# def fetch_taxon_id_db(self, species = None, **kwargs):
#     '''
#       Fetches taxonomic IDs file. Accepts all keyword args of fetch_external_db, except species_name.
#         Returns:
#           taxon_id_fname (str): [path of downloaded taxonomic IDs file]
#     '''
#     if species is not None:
#       logger.warn(f'Homologene does not take a species; discarding argument "{species}".')
#     return self.fetch_external_db('TAXON_ID', None, **kwargs)
