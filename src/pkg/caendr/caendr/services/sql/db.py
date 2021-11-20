import os
import datetime

from logzero import logger

from string import Template
from logzero import logger

from caendr.models.error import BadRequestError
from caendr.models.sql import Homologs, Strain, StrainAnnotatedVariants, WormbaseGene, WormbaseGeneSummary
from caendr.services.cloud.storage import upload_blob_from_file_as_chunks
from caendr.services.cloud.postgresql import db
from caendr.utils.file import download_file
from caendr.utils.data import remove_env_escape_chars

wb_regex = r'^WS[0-9]*$'      # Match the expected format: 'WS276'

local_download_path = '.download'
local_path_prefix_length = len(local_download_path) + 1


external_db_url_templates = {
  'GENE_GTF_URL': remove_env_escape_chars(os.environ.get('GENE_GTF_URL')),
  'GENE_GFF_URL': remove_env_escape_chars(os.environ.get('GENE_GFF_URL')),
  'GENE_IDS_URL': remove_env_escape_chars(os.environ.get('GENE_IDS_URL')),
  'ORTHOLOG_URL': remove_env_escape_chars(os.environ.get('ORTHOLOG_URL')),
  'HOMOLOGENE_URL': remove_env_escape_chars(os.environ.get('HOMOLOGENE_URL')),
  'TAXON_ID_URL': remove_env_escape_chars(os.environ.get('TAXON_ID_URL')),
}


def download_all_external_dbs(wb_ver: str):
  '''
    download_all_external_dbs [Downloads all external DB files to save them locally]
      Args:
        wb_ver (str, optional): [description]. Defaults to None.
      Returns:
        list(str): [A list of all downloaded filenames]
  '''  
  # TODO: confirm correct format for wormbase_version
  if not wb_ver:
    raise BadRequestError()
  
  # Create a local directory to store the downloads
  logger.info('Creating empty directory to store downloaded files')
  if os.path.exists(local_download_path):
    os.rmdir(local_download_path)
  os.mkdir(local_download_path)
  
  logger.info('Downloading All External DBs...')
  downloaded_files = []
  for key, val in external_db_url_templates.items():
    filename, url = download_external_db(wb_ver, key, val)
    downloaded_files.append((filename, url))
  logger.info('Done Downloading External Data.')
  return downloaded_files


def download_external_db(wb_ver: str, db_url_name: str, url_template: str):
  '''
    download_external_data [Downloads an external database file and stores it locally]
      Args:
        wb_ver (str, optional): [Version of Wormbase Data to use (ie: WS276)]. Defaults to None.
        db_url_name (str, optional): [Name used as the key for the Dict of DB URLs]. Defaults to None.
        url_template (str, optional): [Template string for the DBs URL]. Defaults to None.
      Raises:
        BadRequestError: [Arguments missing or malformed]
      Returns:
        str, str: [The downloaded file's local filename and original URL]
  '''  
  # TODO: confirm correct format for wormbase_version
  if not wb_ver or not url_template or not db_url_name:
    raise BadRequestError()

  # Modify the URL template with correct wormbase version and download it
  t = Template(url_template)
  url = t.substitute({'WB': wb_ver})
  logger.info(f'Downloading DB [{db_url_name}]:\n\t{url}')
  fname = download_file(url, f'{local_download_path}/{db_url_name}')
  logger.info(f'Download Complete [{db_url_name}]:\n\t{fname} - {url}')
  return fname, url


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

