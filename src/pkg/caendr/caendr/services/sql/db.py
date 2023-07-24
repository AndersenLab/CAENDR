import os
import datetime
import shutil

from caendr.services.logger import logger

from string import Template
from caendr.services.logger import logger
from diskcache import Cache

from caendr.models.error import BadRequestError
from caendr.models.sql import Homolog, Strain, StrainAnnotatedVariant, WormbaseGene, WormbaseGeneSummary
from caendr.services.cloud.storage import upload_blob_from_file_as_chunks, generate_blob_url, download_blob_to_file
from caendr.services.cloud.postgresql import db
from caendr.utils.file import download_file

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


def drop_tables(app, db, species=None, tables=None):
  '''
    Drops tables from the SQL db. Drops all tables if none are provided.
    Expects tables to be provided in dependency order:
    E.g., if table B contains a foreign key into table A, they should be provided as [... A, ..., B, ...]

      Args:
        app : Flask app instance
        db : SQLAlchemy db registered with the Flask App
        tables (optional): List of tables to be dropped. Defaults to None (ie: all tables)
  '''

  if species is None:
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

  else:
    if tables is None:
      logger.info(f'Dropping species [{", ".join(species)}] from all tables...')
      tables = list(db.metadata.tables.values())
    else:
      logger.info(f'Dropping species [{", ".join(species)}] from tables: {tables}')

    db.metadata.create_all(bind=db.engine, tables=tables)

    # Loop through tables in reverse order, so rows that depend on earlier tables are
    # dropped first
    for table in tables[::-1]:
      for species_name in species:
        del_statement = table.delete().where(table.c.species_name == species_name)
        db.engine.execute(del_statement)

  db.session.commit()

