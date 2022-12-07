import os

from logzero import logger

from caendr.models.error import BadRequestError
from caendr.utils.file import download_file


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



## Fetch specific URLs ##

def fetch_gene_gtf_db(self, species, **kwargs):
    '''
      Fetches WormBase gene GTF file. Accepts all keyword args of fetch_external_db, except species_name.
        Args:
          species (str): [Name of species to retrieve DB file for.]
        Returns:
          gene_gtf_fname (str): [path of downloaded wormbase gene gtf.gz file]
    '''
    return self.fetch_external_db('GENE_GTF_URL', species, **kwargs)


def fetch_gene_gff_db(self, species, **kwargs):
    '''
      Fetches WormBase gene GFF file. Accepts all keyword args of fetch_external_db, except species_name.
        Args:
          species (str): [Name of species to retrieve DB file for.]
        Returns:
          gene_gff_fname (str): [Path of downloaded wormbase gene gff file.]
    '''
    return self.fetch_external_db('GENE_GFF_URL', species, **kwargs)


def fetch_gene_ids_db(self, species, **kwargs):
    '''
      Fetches WormBase gene IDs file. Accepts all keyword args of fetch_external_db, except species_name.
        Args:
          species (str): [Name of species to retrieve DB file for.]
        Returns:
          gene_ids_fname (str): [path of downloaded wormbase gene IDs file]
    '''
    return self.fetch_external_db('GENE_IDS_URL', species, **kwargs)


def fetch_ortholog_db(self, species, **kwargs):
    '''
      Fetches WormBase orthologs file. Accepts all keyword args of fetch_external_db, except species_name.
        Args:
          species (str): [Name of species to retrieve DB file for.]
        Returns:
          ortholog_fname (str): [path of downloaded wormbase homologs file]
    '''
    return self.fetch_external_db('ORTHOLOG_URL', species, **kwargs)


def fetch_homologene_db(self, species = None, **kwargs):
    '''
      Fetches homologene file. Accepts all keyword args of fetch_external_db, except species_name.
        Returns:
          homologene_fname (str): [path of downloaded homologene file]
    '''
    if species is not None:
      logger.warn(f'Homologene does not take a species; discarding argument "{species}".')
    return self.fetch_external_db('HOMOLOGENE_URL', None, **kwargs)


def fetch_taxon_id_db(self, species = None, **kwargs):
    '''
      Fetches taxonomic IDs file. Accepts all keyword args of fetch_external_db, except species_name.
        Returns:
          taxon_id_fname (str): [path of downloaded taxonomic IDs file]
    '''
    if species is not None:
      logger.warn(f'Homologene does not take a species; discarding argument "{species}".')
    return self.fetch_external_db('TAXON_ID_URL', None, **kwargs)
