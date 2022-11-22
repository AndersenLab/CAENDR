import os

from logzero import logger

from caendr.models.error import BadRequestError
from caendr.utils.file import download_file


def prefetch_all_external_dbs(self, use_cache: bool = True):
    '''
      Downloads all external DB files and saves them locally.
    '''
    logger.info('Downloading All External DBs...')

    # Download all files that depend on species
    for species_name in self.species_list.keys():
        for url_template_name in self.specific_template_names:
            self.fetch_external_db(url_template_name, species_name, use_cache=use_cache)

    # Download all files that don't depend on species
    for url_template_name in self.generic_template_names:
        self.fetch_external_db(url_template_name, use_cache=use_cache)

    logger.info('Done Downloading All External Data.')


def fetch_external_db(self, db_url_name: str, species_name: str = None, use_cache: bool = True):
    '''
      fetch_external_db [Downloads an external database file and stores it locally.]
        Args:
          db_url_name (str): [Name used as the key for the Dict of URLs.]
          species_name (str, optional): [Name of species to retrieve DB file for. Defaults to None. Optional, but must be provided for certain URLs.]
          use_cache (bool, optional): [Whether to use a local copy if it exists (True), or force a re-download of the file (False). Defaults to True.]
        Raises:
          BadRequestError: [Arguments missing or malformed]
        Returns:
          str: [The downloaded file's local filename.]
    '''

    # Construct the URL and filename
    url      = self.get_url(db_url_name, species_name)
    filename = self.get_filename(db_url_name, species_name)

    # Check if file already downloaded, if applicable
    if use_cache and os.path.exists(filename):
        species_name_string = f', {species_name}' if species_name is not None else ''
        logger.info(f'External DB already exists [{db_url_name}{species_name_string}]:\n\t{url}')
        fname = filename

    # Download the external file
    else:
        logger.info(f'Downloading External DB [{db_url_name}]:\n\t{url}')
        fname = download_file(url, filename)
        logger.info(f'Download Complete [{db_url_name}]:\n\t{fname} - {url}')

    # Return the resulting filename
    return fname



## Fetch specific URLs ##

def fetch_gene_gtf_db(self, species, use_cache: bool = True):
    '''
      Fetches WormBase gene .gtf.gz file.
        Args:
          species (str): [Name of species to retrieve DB file for.]
          use_cache (bool, optional): [Whether to use a local copy if it exists (True), or force a re-download of the file (False). Defaults to True.]
        Returns:
          gene_gtf_fname (str): [path of downloaded wormbase gene gtf.gz file]
    '''
    return self.fetch_external_db('GENE_GTF_URL', species, use_cache=use_cache)


def fetch_gene_gff_db(self, species, use_cache: bool = True):
    '''
      Fetches WormBase gene .gff file.
        Args:
          species (str): [Name of species to retrieve DB file for.]
          use_cache (bool, optional): [Whether to use a local copy if it exists (True), or force a re-download of the file (False). Defaults to True.]
        Returns:
          gene_gff_fname (str): [Path of downloaded wormbase gene gff file.]
    '''
    return self.fetch_external_db('GENE_GFF_URL', species, use_cache=use_cache)


def fetch_gene_ids_db(self, species, use_cache: bool = True):
    '''
      Fetches WormBase gene IDs file.
        Args:
          species (str): [Name of species to retrieve DB file for.]
          use_cache (bool, optional): [Whether to use a local copy if it exists (True), or force a re-download of the file (False). Defaults to True.]
        Returns:
          gene_ids_fname (str): [path of downloaded wormbase gene IDs file]
    '''
    return self.fetch_external_db('GENE_IDS_URL', species, use_cache=use_cache)


def fetch_ortholog_db(self, species, use_cache: bool = True):
    '''
      Fetches WormBase orthologs file.
        Args:
          species (str): [Name of species to retrieve DB file for.]
          use_cache (bool, optional): [Whether to use a local copy if it exists (True), or force a re-download of the file (False). Defaults to True.]
        Returns:
          ortholog_fname (str): [path of downloaded wormbase homologs file]
    '''
    return self.fetch_external_db('ORTHOLOG_URL', species, use_cache=use_cache)


def fetch_homologene_db(self, use_cache: bool = True):
    '''
      Fetches homologene file.
        Args:
          use_cache (bool, optional): [Whether to use a local copy if it exists (True), or force a re-download of the file (False). Defaults to True.]
        Returns:
          homologene_fname (str): [path of downloaded homologene file]
    '''
    return self.fetch_external_db('HOMOLOGENE_URL', use_cache=use_cache)


def fetch_taxon_id_db(self, use_cache: bool = True):
    '''
      Fetches taxon IDs file.
        Args:
          use_cache (bool, optional): [Whether to use a local copy if it exists (True), or force a re-download of the file (False). Defaults to True.]
        Returns:
          taxon_id_fname (str): [path of downloaded taxon IDs file]
    '''
    return self.fetch_external_db('TAXON_ID_URL', use_cache=use_cache)
