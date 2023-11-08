from logzero import logger

from ._db import fetch_db



## General fetch functions ##

def fetch_internal_db(self, *args, **kwargs):
    '''
      Downloads an internal (GCP) database file and stores it locally.
      Takes the same positional and keyword arguments as fetch_db, except for db_type.
        Returns:
          str: [The downloaded file's local filename.]
    '''

    # Keep downloaded file zipped, unless caller explicitly asks for unzipped
    kwargs['unzip'] = kwargs.get('unzip', False)

    return fetch_db(self, 'internal', *args, **kwargs)


def prefetch_all_internal_dbs(self, **kwargs):
    '''
      Downloads all internal DB files and saves them locally.
      Accepts all keyword args of fetch_external_db, except species_name.
    '''
    logger.info('Downloading All Internal DBs...')

    kwargs_copy = { key: val for key, val in kwargs.items() }
    kwargs_copy['unzip'] = kwargs_copy.get('unzip', False)

    # Download all files that depend on species
    for species_name in self.species_list.keys():

      # TODO: can we loop through them instead of listing them all out?
      # for url_template_name in self.specific_template_names:
      #   self.fetch_internal_db(url_template_name, species_name, **kwargs)

      self.fetch_gene_gtf_db(species_name, **kwargs_copy)
      self.fetch_gene_gff_db(species_name, **kwargs_copy)
      self.fetch_gene_ids_db(species_name, **kwargs_copy)

    # TODO: Briggsae data
    self.fetch_sva_db('c_elegans',  **kwargs)
    # self.fetch_sva_db('c_briggsae', **kwargs)

    logger.info('Finished Downloading All Internal Data.')



## Specific fetch functions ##

def fetch_gene_gtf_db(self, species, **kwargs):
    '''
      Fetches WormBase gene GTF file. Accepts all keyword args of fetch_internal_db, except species_name.
        Args:
          species (str): [Name of species to retrieve DB file for.]
        Returns:
          gene_gtf_fname (str): [path of downloaded wormbase gene gtf.gz file]
    '''
    kwargs['unzip'] = kwargs.get('unzip', False)
    return self.fetch_internal_db('GENE_GTF', species, **kwargs)


def fetch_gene_gff_db(self, species, **kwargs):
    '''
      Fetches WormBase gene GFF file. Accepts all keyword args of fetch_internal_db, except species_name.
        Args:
          species (str): [Name of species to retrieve DB file for.]
        Returns:
          gene_gff_fname (str): [Path of downloaded wormbase gene gff file.]
    '''
    kwargs['unzip'] = kwargs.get('unzip', False)
    return self.fetch_internal_db('GENE_GFF', species, **kwargs)


def fetch_gene_ids_db(self, species, **kwargs):
    '''
      Fetches WormBase gene IDs file. Accepts all keyword args of fetch_internal_db, except species_name.
        Args:
          species (str): [Name of species to retrieve DB file for.]
        Returns:
          gene_ids_fname (str): [path of downloaded wormbase gene IDs file]
    '''
    kwargs['unzip'] = kwargs.get('unzip', False)
    return self.fetch_internal_db('GENE_IDS', species, **kwargs)


def fetch_sva_db(self, species: str, **kwargs):
    '''
      Fetches strain annotation variant file. Accepts all keyword args of fetch_internal_db, except species_name.
        Returns:
          sva_fname (str): [path of downloaded strain variant annotations file]
    '''
    return self.fetch_internal_db('SVA_CSVGZ', species, **kwargs)


# TODO: make a fetch function for EACH trait file
#       Template for a single file:
def fetch_FILENAME_GOES_HERE(self, species: str, **kwargs):
    return self.fetch_internal_db(FILENAME_GOES_HERE , species, **kwargs)
