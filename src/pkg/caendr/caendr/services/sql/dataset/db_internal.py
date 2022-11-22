from string import Template
from logzero import logger

from caendr.models.error import BadRequestError
from caendr.services.cloud.storage import download_blob_to_file

from .env import MODULE_DB_OPERATIONS_BUCKET_NAME, internal_db_blob_templates


## General fetch functions ##

def prefetch_all_internal_dbs(self, use_cache: bool = True):
    '''
      Downloads all internal DB files and saves them locally.
    '''
    logger.info('Downloading All Internal DBs...')
    self.fetch_sva_db()


def fetch_internal_db(self, db_url_name: str, use_cache: bool = True):

    # Ensure a URL template was passed
    # TODO: If we look this up like we do for the external template names, this check won't be necessary
    if not db_url_name:
        raise BadRequestError()

    # Construct blob name
    t = Template(internal_db_blob_templates[db_url_name])
    blob_name = t.substitute({'SVA': self.sva_ver})

    # Construct URL
    url = f'gs://{MODULE_DB_OPERATIONS_BUCKET_NAME}/{blob_name}'

    # Download blob to file
    logger.info(f'Downloading Internal DB [{db_url_name}]:\n\t{url}')
    fname = blob_name.rsplit('/', 1)[-1]
    download_blob_to_file(MODULE_DB_OPERATIONS_BUCKET_NAME, blob_name, fname)

    logger.info(f'Download Complete [{db_url_name}]:\n\t{fname} - {url}')
    return fname


## Specific fetch functions ##

def fetch_sva_db(self, use_cache: bool = True):
    return self.fetch_internal_db('SVA_CSVGZ_URL', use_cache=use_cache)
