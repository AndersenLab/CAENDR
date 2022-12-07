from string import Template
from logzero import logger

from caendr.models.error import BadRequestError
from caendr.services.cloud.storage import download_blob_to_file

from ._env import MODULE_DB_OPERATIONS_BUCKET_NAME


## General fetch functions ##

def prefetch_all_internal_dbs(self, use_cache: bool = True):
    '''
      Downloads all internal DB files and saves them locally.
    '''
    logger.info('Downloading All Internal DBs...')
    self.fetch_sva_db('c_elegans',  use_cache=use_cache)
    # self.fetch_sva_db('c_briggsae', use_cache=use_cache)


def fetch_internal_db(self, db_url_name: str, species_name: str, use_cache: bool = True, unzip: bool = True):

    # Construct blob name
    blob_name = self.get_blob(db_url_name, species_name)

    # Construct URL
    url = f'gs://{MODULE_DB_OPERATIONS_BUCKET_NAME}/{blob_name}'

    # Download blob to file
    logger.info(f'Downloading Internal DB [{db_url_name}]:\n\t{url}')
    fname = f'{self.get_download_path(species_name)}/{blob_name.rsplit("/", 1)[-1]}'
    download_blob_to_file(MODULE_DB_OPERATIONS_BUCKET_NAME, blob_name, fname)
    logger.info(f'Download Complete [{db_url_name}]:\n\t{fname} - {url}')

    # Unzip the downloaded file, if applicable
    if fname[-3:] == '.gz' and unzip:
        self.unzip_gz(fname, keep_zipped_file=False)
        fname = fname[:-3]

    return fname


## Specific fetch functions ##

def fetch_sva_db(self, species_name: str, use_cache: bool = True):
    return self.fetch_internal_db('SVA_CSVGZ_URL', species_name, use_cache=use_cache)
