from string import Template
from logzero import logger

from caendr.models.error import BadRequestError
from caendr.services.cloud.storage import download_blob_to_file

from ._env import MODULE_DB_OPERATIONS_BUCKET_NAME


## General fetch functions ##

def prefetch_all_internal_dbs(self, **kwargs):
    '''
      Downloads all internal DB files and saves them locally.
    '''
    logger.info('Downloading All Internal DBs...')
    self.fetch_sva_db('c_elegans',  **kwargs)
    # self.fetch_sva_db('c_briggsae', **kwargs)

    logger.info('Finished Downloading All Internal Data.')



## Specific fetch functions ##

def fetch_sva_db(self, species_name: str, **kwargs):
    return self.fetch_internal_db('SVA_CSVGZ_URL', species_name, **kwargs)
