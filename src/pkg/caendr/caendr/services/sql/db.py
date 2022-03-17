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
  'GENE_GTF_URL': remove_env_escape_chars(os.environ.get('GENE_GTF_URL')),
  'GENE_GFF_URL': remove_env_escape_chars(os.environ.get('GENE_GFF_URL')),
  'GENE_IDS_URL': remove_env_escape_chars(os.environ.get('GENE_IDS_URL')),
  'ORTHOLOG_URL': remove_env_escape_chars(os.environ.get('ORTHOLOG_URL')),
  'HOMOLOGENE_URL': remove_env_escape_chars(os.environ.get('HOMOLOGENE_URL')),
  'TAXON_ID_URL': remove_env_escape_chars(os.environ.get('TAXON_ID_URL'))
}

internal_db_blob_templates = {
  'SVA_CSVGZ_URL': SVA_CSVGZ_URL_TEMPLATE
}

@cache.memoize()
def download_all_external_dbs(wb_ver: str):
  '''
    download_all_external_dbs [Downloads all external DB files to save them locally]
      Args:
        wb_ver (str, optional): [description]. Defaults to None.
      Returns:
        dict(str): [A dictionary of all downloaded filenames]
  '''  
  # TODO: confirm correct format for wormbase_version
  if not wb_ver:
    logger.warning("E_NOT_SET: 'wb_ver'")    
    raise BadRequestError()
  
  # Create a local directory to store the downloads
  logger.info('Creating empty directory to store downloaded files')
  if os.path.exists(local_download_path):
    shutil.rmtree(local_download_path)
  os.mkdir(local_download_path)
  
  logger.info('Downloading All External DBs...')
  downloaded_files = {}
  for key, val in external_db_url_templates.items():
    downloaded_files[key] = download_external_db(key, wb_ver)
  logger.info('Done Downloading External Data.')
  return downloaded_files
  
@cache.memoize()
def download_external_db(db_url_name: str, wb_ver: str=''):
  '''
    download_external_db [Downloads an external database file and stores it locally]
      Args:
        db_url_name (str): [Name used as the key for the Dict of URLs].
        wb_ver (str, optional): [Version of Wormbase Data to use (ie: WS276)].
      Raises:
        BadRequestError: [Arguments missing or malformed]
      Returns:
        str: [The downloaded file's local filename]
  '''  
  # TODO: confirm correct format for wormbase_version
  if not db_url_name:
    raise BadRequestError()

  # Modify the URL template with correct wormbase version and download it
  # TODO: make template args optional
  if not os.path.exists(local_download_path):
    os.mkdir(local_download_path)

  t = Template(external_db_url_templates[db_url_name])
  url = t.substitute({'WB': wb_ver})
  logger.info(f'Downloading External DB [{db_url_name}]:\n\t{url}')
  fname = download_file(url, f'{local_download_path}/{db_url_name}')
  logger.info(f'Download Complete [{db_url_name}]:\n\t{fname} - {url}')
  return fname


def fetch_internal_db(db_url_name: str, sva_ver: str=''):
  # TODO: confirm correct format for wormbase_version
  if not db_url_name:
    raise BadRequestError()

  # Modify the URL template with correct wormbase version and download it
  # TODO: make template args optional
  if not os.path.exists(local_download_path):
    os.mkdir(local_download_path)

  t = Template(internal_db_blob_templates[db_url_name])
  blob_name = t.substitute({'SVA': sva_ver})
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

