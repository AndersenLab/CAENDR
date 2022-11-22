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

local_download_path = '.download'
local_path_prefix_length = len(local_download_path) + 1


# TODO: Move to DatasetManager class
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

