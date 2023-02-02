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

    # Unzip downloaded files, unless caller explicitly asks not to
    kwargs['unzip'] = kwargs.get('unzip', True)

    return fetch_db(self, 'internal', *args, **kwargs)


def prefetch_all_internal_dbs(self, **kwargs):
    '''
      Downloads all internal DB files and saves them locally.
      Accepts all keyword args of fetch_external_db, except species_name.
    '''
    logger.info('Downloading All Internal DBs...')

    self.fetch_sva_db('c_elegans',  **kwargs)
    # self.fetch_sva_db('c_briggsae', **kwargs)

    logger.info('Finished Downloading All Internal Data.')



## Specific fetch functions ##

def fetch_sva_db(self, species: str, **kwargs):
    '''
      Fetches strain annotation variant file. Accepts all keyword args of fetch_internal_db, except species_name.
        Returns:
          sva_fname (str): [path of downloaded strain variant annotations file]
    '''
    return self.fetch_internal_db('SVA_CSVGZ', species, **kwargs)
