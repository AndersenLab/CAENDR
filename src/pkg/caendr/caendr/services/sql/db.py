import os
import datetime
import shutil

from logzero import logger

from string import Template
from logzero import logger
from diskcache import Cache

from caendr.models.error import BadRequestError
from caendr.models.sql import Homolog, Strain, StrainAnnotatedVariant, WormbaseGene, WormbaseGeneSummary
from caendr.services.cloud.storage import upload_blob_from_file_as_chunks, generate_blob_url, download_blob_to_file
from caendr.services.cloud.postgresql import db
from caendr.utils.file import download_file
from caendr.utils.data import remove_env_escape_chars

cache = Cache("cachedir")

wb_regex = r'^WS[0-9]*$'      # Match the expected format: 'WS276'

local_download_path = '.download'
local_path_prefix_length = len(local_download_path) + 1

MODULE_DB_OPERATIONS_BUCKET_NAME = os.environ.get('MODULE_DB_OPERATIONS_BUCKET_NAME')
STRAIN_VARIANT_ANNOTATION_PATH = os.environ.get('STRAIN_VARIANT_ANNOTATION_PATH')
SVA_CSVGZ_URL_TEMPLATE = f'{STRAIN_VARIANT_ANNOTATION_PATH}/WI.strain-annotation.bcsq.$SVA.csv.gz'


external_db_url_templates = {

  # URLs that depend on the species
  'specific': {
    'GENE_GTF_URL': remove_env_escape_chars(os.environ.get('GENE_GTF_URL')),
    'GENE_GFF_URL': remove_env_escape_chars(os.environ.get('GENE_GFF_URL')),
    'GENE_IDS_URL': remove_env_escape_chars(os.environ.get('GENE_IDS_URL')),
    'ORTHOLOG_URL': remove_env_escape_chars(os.environ.get('ORTHOLOG_URL')),
  },

  # URLs that don't depend on the species
  'generic': {
    'HOMOLOGENE_URL': remove_env_escape_chars(os.environ.get('HOMOLOGENE_URL')),
    'TAXON_ID_URL':   remove_env_escape_chars(os.environ.get('TAXON_ID_URL'))
  },
}

internal_db_blob_templates = {
  'SVA_CSVGZ_URL': SVA_CSVGZ_URL_TEMPLATE
}

# List of species, with associated project number(s) and wormbase version
# TODO: This information should probably be read from somewhere else
species_list = {
  'c_elegans': {
    'project_number':   'PRJNA13758',
    'wormbase_version': os.environ.get('WORMBASE_VERSION'),
  },
}

class DatasetManager:

  def __init__(self,
    wb_ver: str = None,
    sva_ver: str = None,
    local_download_path: str = local_download_path,
    species_list = species_list,
    reload_files: bool = False,
  ):
    '''
      Args:
        wb_ver (str, optional): [Version of Wormbase Data to use (ie: WS276). Optional for initialization, but required for some operations.]
        sva_ver (str, optional): [Strain Variant Annotation version to use. Optional for initialization, but required for some operations.]
        local_download_path (str, optional): [Local directory path to store downloaded files. Defaults to '.download'.]
        species_list (dict(str), optional): [Dictionary mapping species IDs to species-specific values. Default provided.]
        reload_files (bool, optional): [Whether to clear the current contents of the download directory and re-download all files. Defaults to False.]
    '''

    self.set_wb_ver(wb_ver)
    self.set_sva_ver(sva_ver)

    self.local_download_path = local_download_path
    self.species_list = species_list

    # Locate directory
    if reload_files:
      self.reset_directory()
    self.ensure_directory_exists()


  # TODO: confirm correct format for wormbase_version
  def set_wb_ver(self, wb_ver: str):
    self.wb_ver = wb_ver
  
  def set_sva_ver(self, sva_ver: str):
    self.sva_ver = sva_ver


  ## Directory ##

  def ensure_directory_exists(self):
    '''
      Ensures the local download directory exists and has the correct subfolders.
    '''
    # Create a folder at the desired path if one does not yet exist
    if not os.path.exists(self.local_download_path):
      os.mkdir(self.local_download_path)

    # Make sure a subfolder exists for each species in the list
    for species_name in self.species_list.keys():
      species_path = f'{self.local_download_path}/{species_name}'
      if not os.path.exists(species_path):
        os.mkdir(species_path)


  # Create a local directory to store the downloads
  def reset_directory(self):
    '''
      Deletes the local download directory and all its contents.
    '''
    logger.info('Creating empty directory to store downloaded files')
    if os.path.exists(self.local_download_path):
      shutil.rmtree(self.local_download_path)


  ## URLs and Filenames ##

  def url_template_type(self, db_url_name: str):
    '''
      Determines whether a URL is 'generic' (same for all species) or 'specific' (different for different species).
        Args:
          db_url_name (str): [Name of the URL template to check.]
        Raises:
          BadRequestError: [Provided URL name is not recognized.]
        Returns:
          str: ['generic' or 'specific']
    '''
    if db_url_name in external_db_url_templates['generic']:
      return 'generic'
    elif db_url_name in external_db_url_templates['specific']:
      return 'specific'
    else:
      logger.warning(f'Unrecognized URL template name "{db_url_name}".')
      raise BadRequestError()


  def get_url_template(self, db_url_name: str):
    '''
      Gets the URL template associated with a given template name.
        Args:
          db_url_name (str): [The name of the template to retrieve.]
        Returns:
          str: [The URL template associated with the given name.]
    '''
    return external_db_url_templates[self.url_template_type(db_url_name)][db_url_name]


  def get_url(self, db_url_name: str, species_name: str = None):
    '''
      Fills in the specified URL template with version & species information.  Some templates do not require a species.
        Args:
          db_url_name (str): [The name of the template to retrieve.]
          species_name (str, optional): [The species to fill in the template with. Defaults to None. Optional, but must be provided for certain templates.]
        Raises:
          BadRequestError: [Class-level WormBase version not set; URL template requires species, but none provided; Unknown species name.]
        Returns:
          str: [The desired URL filled in with information for the given species.]
    '''
    # Make sure wormbase version is set
    if not self.wb_ver:
      logger.warning("E_NOT_SET: 'wb_ver'")
      raise BadRequestError()

    # Make sure a species name was provided if the URL requires one
    if (self.url_template_type(db_url_name) == 'specific') and species_name is None:
      logger.warning(f'URL template "{db_url_name}" requires a species, but none was provided.')
      raise BadRequestError()

    # Make sure the species name is valid
    if species_name is not None and species_name not in self.species_list.keys():
      logger.warning(f'Cannot construct URL for unknown species "{species_name}".')
      raise BadRequestError()

    # Get the desired template an fill in species information, if applicable
    t = Template(self.get_url_template(db_url_name))
    if species_name is not None:
      return t.substitute({
        'WB':      self.wb_ver,
        'SPECIES': species_name,
        'PRJ':     self.species_list[species_name]['project_number'],
      })
    else:
      return t.substitute({
        'WB':      self.wb_ver,
      })


  def get_filename(self, db_url_name: str, species_name: str = ''):
    '''
      Gets the local filename for a URL template and species.  Does NOT guarantee that this file exists.
        Args:
          db_url_name (str): [The name of the template to retrieve.]
          species_name (str, optional): [The species to fill in the template with. Defaults to None. Optional, but must be provided for certain templates.]
        Returns:
          str: [The location in the local downloads folder where the downloaded file belongs.]
    '''
    if (self.url_template_type(db_url_name) == 'generic'):
      url_path = ''
    else:
      url_path = species_name + '/'
    return f'{self.local_download_path}/{url_path}{db_url_name}'


  ## Download external databases ##

  def prefetch_all_external_dbs(self):
    '''
      Downloads all external DB files and saves them locally.
    '''
    logger.info('Downloading All External DBs...')

    # Make sure wormbase version is set
    if not self.wb_ver:
      logger.warning("E_NOT_SET: 'wb_ver'")
      raise BadRequestError()

    # Download all files that depend on species
    for species_name in species_list.keys():
      for url_template_name in external_db_url_templates['specific'].keys():
        self.fetch_external_db(url_template_name, species_name)

    # Download all files that don't depend on species
    for url_template_name in external_db_url_templates['generic'].keys():
      self.fetch_external_db(url_template_name)

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
    # TODO: confirm correct format for wormbase_version
    if not db_url_name:
      raise BadRequestError()

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


  def fetch_internal_db(self, db_url_name: str):
    if not self.sva_ver:
      logger.warning("E_NOT_SET: 'sva_ver'")
      raise BadRequestError()
    if not db_url_name:
      raise BadRequestError()

    t = Template(internal_db_blob_templates[db_url_name])
    blob_name = t.substitute({'SVA': self.sva_ver})
    url = f'gs://{MODULE_DB_OPERATIONS_BUCKET_NAME}/{blob_name}'
    logger.info(f'Downloading Internal DB [{db_url_name}]:\n\t{url}')
    fname = blob_name.rsplit('/', 1)[-1]
    download_blob_to_file(MODULE_DB_OPERATIONS_BUCKET_NAME, blob_name, fname)

    logger.info(f'Download Complete [{db_url_name}]:\n\t{fname} - {url}')
    return fname



def backup_external_db(downloaded_files, bucket_name: str, path_prefix: str):
  '''
    backup_external_db [Saves locally downloaded DB files to google storage]
      Args:
        downloaded_files (List of str, str): [the filenames of the downloaded DB files and their URLs]
        bucket_name (str): [Name of the bucket to store backups]
        path_prefix (str): [Path within the bucket to store backups]
      Returns:
        results (List of json results): [A list of the JSON responses returned by google storage for each uploaded blob]
  '''
  dt = datetime.datetime.today()
  dt_string = dt.strftime('%Y%m%d')
  results = []
  logger.info('Uploading external DB files to Google Cloud Storage')
  for path, url in downloaded_files:
    filename = path[local_path_prefix_length:]    # strip the local path
    url = url.replace('/', '_').replace(':','|')
    blob_name = f'{path_prefix}/{dt_string}/{filename}/{url}'
    response = upload_blob_from_file_as_chunks(bucket_name, path, blob_name)
    results.append(response)
  logger.info('Uploads Complete')
  return results


def drop_tables(app, db, tables=None):
  '''
    drop_tables [Drops tables from the SQL db. Drops all tables if non are provided. ]
      Args:
        app : Flask app instance
        db : SQLAlchemy db registered with the Flask App
        tables (optional): List of tables to be dropped. Defaults to None (ie: all tables)
  '''  
  if tables is None:
    logger.info('Dropping all tables...')
    db.drop_all(app=app)
    logger.info('Creating all tables...')
    db.create_all(app=app)
  else:
    logger.info(f'Dropping tables: ${tables}')
    db.metadata.drop_all(bind=db.engine, checkfirst=True, tables=tables)
    logger.info(f'Creating tables: ${tables}')
    db.metadata.create_all(bind=db.engine, tables=tables)
  db.session.commit()

