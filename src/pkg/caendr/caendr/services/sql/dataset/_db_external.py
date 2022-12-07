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

    logger.info('Done Downloading All External Data.')


def fetch_external_db(self, db_url_name: str, species_name: str = None, use_cache: bool = True, unzip: bool = False):
    '''
      fetch_external_db [Downloads an external database file and stores it locally.]
        Args:
          db_url_name (str): [Name used as the key for the Dict of URLs.]
        Keyword Args:
          species_name (str, optional): [Name of species to retrieve DB file for. Defaults to None. Optional, but must be provided for certain URLs.]
          use_cache (bool, optional): [Whether to use a local copy if it exists (True), or force a re-download of the file (False). Defaults to True.]
          unzip (bool, optional): [Whether to unzip a .gz file. Defaults to False.]
        Raises:
          BadRequestError: [Arguments missing or malformed]
        Returns:
          str: [The downloaded file's local filename.]
    '''

    # Construct the URL and filename
    url      = self.get_url(db_url_name, species_name)
    filename = self.get_filename(db_url_name, species_name)

    # Determine whether the URL is zipped
    is_zipped = url[-3:] == '.gz'

    # Check if file already downloaded and unzipped
    if use_cache and os.path.exists(filename):
        species_name_string = f', {species_name}' if species_name is not None else ''
        logger.info(f'External DB already exists [{db_url_name}{species_name_string}]:\n\t{url}')
        fname = filename

    # Check if file already downloaded and zipped
    elif use_cache and os.path.exists(filename + '.gz'):
        species_name_string = f', {species_name}' if species_name is not None else ''
        logger.info(f'External DB already exists [{db_url_name}.gz{species_name_string}]:\n\t{url}')
        fname = filename + '.gz'

    # Download the external file
    else:
        logger.info(f'Downloading External DB [{db_url_name}]:\n\t{url}')

        # Append the '.gz' suffix if the file is a GZ zipped file
        if is_zipped:
          filename = f'{filename}.gz'

        # Download the file
        fname = download_file(url, filename)
        logger.info(f'Download Complete [{db_url_name}]:\n\t{fname} - {url}')

    # Unzip the file, if applicable
    if is_zipped and unzip:
        self.unzip_gz(fname, keep_zipped_file=False)

    # Return the resulting filename
    return fname



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
