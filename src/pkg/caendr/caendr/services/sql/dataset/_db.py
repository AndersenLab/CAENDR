import os

from logzero import logger

from caendr.models.error import InternalError
from caendr.services.cloud.storage import download_blob_to_file
from caendr.utils.file import download_file

from ._env import MODULE_DB_OPERATIONS_BUCKET_NAME



## Local vars that differ based on internal/external fetch ##

def get_fetch_params_internal(manager, db_url_name: str, species_name: str):
    '''
      get_fetch_params_internal [
        Get certain variables for an internal DB fetch. See fetch_db.
      ]
        Returns:
          url (str): [The URL to download from.]
          filename (str): [The local filename to download to.]
          dl_func (function): [A function that downloads a file from its first argument (a URL) to its second (a filepath).]
    '''

    # Construct blob name
    blob_name = manager.get_blob(db_url_name, species_name)

    # Construct URL
    url = f'gs://{MODULE_DB_OPERATIONS_BUCKET_NAME}/{blob_name}'

    # Construct filename
    filename = f'{manager.get_download_path(species_name)}/{blob_name.rsplit("/", 1)[-1]}'
    if filename[-3:] == '.gz':
        filename = filename[:-3]

    # Construct download function as lambda
    # To download, we just use the filename as the last argument to download_blob_to_file
    dl_func = lambda _, fname: download_blob_to_file(MODULE_DB_OPERATIONS_BUCKET_NAME, blob_name, fname)

    return url, filename, dl_func


def get_fetch_params_external(manager, db_url_name: str, species_name: str):
    '''
      get_fetch_params_external [
        Get certain variables for an external DB fetch. See fetch_db.
      ]
        Returns:
          url (str): [The URL to download from.]
          filename (str): [The local filename to download to.]
          dl_func (function): [A function that downloads a file from its first argument (a URL) to its second (a filepath).]
    '''

    url      = manager.get_url(db_url_name, species_name)
    filename = manager.get_filename(db_url_name, species_name)

    return url, filename, download_file



## Fetch DBs ##

def fetch_external_db(self, *args, **kwargs):
    '''
      fetch_external_db [
        Downloads an external (WormBase, etc.) database file and stores it locally.
        Takes the same positional and keyword arguments as fetch_db, except for db_type.
      ]  
        Returns:
          str: [The downloaded file's local filename.]
    '''
    return self.fetch_db('external', *args, **kwargs)


def fetch_internal_db(self, *args, **kwargs):
    '''
      fetch_internal_db [
        Downloads an internal (GCP) database file and stores it locally.
        Takes the same positional and keyword arguments as fetch_db, except for db_type.
      ]  
        Returns:
          str: [The downloaded file's local filename.]
    '''

    # Unzip downloaded files, unless caller explicitly asks not to
    kwargs['unzip'] = kwargs.get('unzip', True)

    return self.fetch_db('internal', *args, **kwargs)


def fetch_db(
        self,
        db_type: str,
        db_url_name: str,
        species_name: str = None,
        use_cache: bool = True,
        unzip: bool = False,
    ):
    '''
      fetch_db [
        Downloads an external database file and stores it locally.
        This function usually should not be called directly; see fetch_external_db and fetch_internal_db.
      ]
        Args:
          db_type (str): [The type of the database ('external' or 'internal').]
          db_url_name (str): [Name used as the key for the Dict of URLs.]
        Keyword Args:
          species_name (str, optional): [Name of species to retrieve DB file for. Defaults to None. Optional, but must be provided for certain URLs.]
          use_cache (bool, optional): [Whether to use a local copy if it exists (True), or force a re-download of the file (False). Defaults to True.]
          unzip (bool, optional): [Whether to unzip a .gz file. Defaults to False.]
        Raises:
          BadRequestError: [Arguments missing or malformed]
          InternalError: [Unrecognized db_type argument]
        Returns:
          str: [The downloaded file's local filename.]
    '''

    # Set local variables based on whether the db is external or internal
    if db_type == 'external':
        url, filename, dl_func = get_fetch_params_external(self, db_url_name, species_name)
    elif db_type == 'internal':
        url, filename, dl_func = get_fetch_params_internal(self, db_url_name, species_name)
    else:
        logger.warn(f'Unrecognized DB type "{db_type}"')
        raise InternalError()

    # Create species name string for logger messages
    species_name_string = f', {species_name}' if species_name is not None else ''

    # Determine whether the source file is zipped (GZ format)
    is_zipped = url[-3:] == '.gz'

    # Check if file already downloaded and unzipped
    if use_cache and os.path.exists(filename):
        logger.info(f'Already downloaded {db_type} DB [{db_url_name}{species_name_string}]:\n\t{url}')
        is_zipped = False

    # Check if file already downloaded and zipped
    elif use_cache and os.path.exists(filename + '.gz'):
        logger.info(f'Already downloaded {db_type} DB [{db_url_name}{species_name_string}] (zipped):\n\t{url}')
        filename += '.gz'

    # Download the external file
    else:
        logger.info(f'Downloading {db_type} DB [{db_url_name}{species_name_string}]:\n\t{url}')

        # Append the '.gz' suffix if the source file is zipped
        if is_zipped:
          filename += '.gz'

        # Download the file using the given download function
        dl_func(url, filename)
        logger.info(f'Download Complete [{db_url_name}{species_name_string}]:\n\t{filename} - {url}')

    # Unzip the downloaded file, if applicable
    if is_zipped and unzip:
        self.unzip_gz(filename, keep_zipped_file=False)
        filename = filename[:-3]

    # Return the resulting filename
    return filename
