import os
import datetime
import shutil

from caendr.services.logger import logger

from string import Template
from caendr.services.logger import logger
from diskcache import Cache

from caendr.models.error import BadRequestError

# from caendr.models.sql import TABLES_LIST
from caendr.services.cloud.storage import upload_blob_from_file_as_chunks, download_blob_to_file
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
