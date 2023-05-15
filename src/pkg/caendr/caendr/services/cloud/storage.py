import io
import os
import google.auth
import google.auth.transport.requests as tr_requests
import datetime

import json
import pandas as pd

from google.oauth2 import service_account
from google.resumable_media.requests import ResumableUpload
from google.cloud import storage
from caendr.services.logger import logger

from caendr.models.error import CloudStorageUploadError, NotFoundError
from caendr.services.cloud.secret import get_secret
from caendr.services.cloud.service_account import get_service_account_credentials

GOOGLE_STORAGE_SERVICE_ACCOUNT_NAME = os.environ.get('GOOGLE_STORAGE_SERVICE_ACCOUNT_NAME')

storageClient = storage.Client()

def get_google_storage_credentials():
  """ Uses service account credentials to authorize access to google storage """
  json_account_info = get_service_account_credentials(get_secret(GOOGLE_STORAGE_SERVICE_ACCOUNT_NAME))
  credentials = service_account.Credentials.from_service_account_info(json_account_info)
  return credentials


def get_blob(bucket_name, blob_name):
  logger.debug(f'get_blob(bucket_name={bucket_name}, blob_name={blob_name})')
  bucket = storageClient.get_bucket(bucket_name)
  return bucket.get_blob(blob_name)


def check_blob_exists(bucket_name, blob_name):
  logger.debug(f'check_blob_exists(bucket_name={bucket_name}, blob_name={blob_name})')
  bucket = storageClient.get_bucket(bucket_name)
  blob = bucket.get_blob(blob_name)
  try:
    return blob.exists()
  except:
    return False


def get_blob_list(bucket_name, prefix):
  ''' Returns a list of all blobs with 'prefix' (directory) in 'bucket_name' '''
  bucket = storageClient.get_bucket(bucket_name)
  items = bucket.list_blobs(prefix=prefix)
  return list(items)


def generate_blob_url(bucket_name, blob_name, secure=True):
  ''' Generates the public https URL for a blob '''
  if secure:
    return f"https://storage.googleapis.com/{bucket_name}/{blob_name}" 
  else:
    return f"http://storage.googleapis.com/{bucket_name}/{blob_name}" 



def download_blob_to_file(bucket_name, blob_name, filename):
  ''' Downloads a blob and saves it locally '''   
  bucket = storageClient.get_bucket(bucket_name)
  blob = bucket.blob(blob_name)
  if blob.exists():
    blob.download_to_file(open(filename, 'wb'))
    return filename
  else:
    raise NotFoundError('blob', {'bucket': bucket_name, 'name': blob_name})

def upload_blob_from_file_object(bucket_name, file, blob_name):
  """Uploads a file to the bucket."""
  logger.debug(f'upload_blob_from_file_object: bucket_name:{bucket_name} file:{file} blob_name:{blob_name}')
  bucket = storageClient.get_bucket(bucket_name)
  blob = bucket.blob(blob_name)
  blob.upload_from_file(file)


def upload_blob_from_string(bucket_name, data, blob_name):
  """Uploads a string to the bucket as a file."""
  bucket = storageClient.get_bucket(bucket_name)
  blob = bucket.blob(blob_name)
  blob.upload_from_string(data)


def upload_blob_from_file(bucket_name, filename, blob_name):
  """Uploads a file to the bucket."""
  bucket = storageClient.get_bucket(bucket_name)
  blob = bucket.blob(blob_name)
  blob.upload_from_filename(filename)
  
  
def upload_blob_from_file_as_chunks(bucket_name: str, filename: str, blob_name: str):
  '''
    upload_blob_from_file_as_chunks [Uploads large files to cloud storage in 2MB chunks]
      Args:
        bucket_name (str): [the name of the bucket to upload the blob]
        filename (str): [local filename to be uploaded]
        blob_name (str): [full name to use for storing the blob]
      Raises:
        CloudStorageUploadError: [description]
        CloudStorageUploadError: [description]
      Returns:
        json_response (json): [description]
  '''  
  CHUNKSIZE = 2 * 1024 * 1024
  CONTENT_TYPE = 'application/octet-stream'
  
  rw_scope = 'https://www.googleapis.com/auth/devstorage.read_write'
  url_template = (
    'https://www.googleapis.com/upload/storage/v1/b/{bucket_name}/o?'
    'uploadType=resumable')

  credentials, _ = google.auth.default(scopes=(rw_scope))
  transport = tr_requests.AuthorizedSession(credentials)
  upload_url = url_template.format(bucket_name=bucket_name)
  upload = ResumableUpload(upload_url, CHUNKSIZE)
  
  with open(filename, 'rb') as fh:
    data = fh.read()
    stream = io.BytesIO(data)
    metadata = {'name': blob_name}
    logger.info(f'Starting Chunked Upload: {bucket_name} {filename} {blob_name}')
    response = upload.initiate(transport, stream, metadata, CONTENT_TYPE)
    assert(upload.resumable_url == response.headers['Location'])
    assert(upload.total_bytes == len(data))
    upload_id = response.headers['X-GUploader-UploadID']
    logger.info(f'UPLOADING: {bucket_name} {filename} {blob_name} {upload_id}')
    assert(upload.resumable_url == upload_url + '&upload_id=' + upload_id)
    while not upload.finished:
      logger.info(f'Bytes Uploaded: {upload.bytes_uploaded} / {upload.total_bytes}')
      response = upload.transmit_next_chunk(transport)
    
    if upload.bytes_uploaded != upload.total_bytes:
      raise CloudStorageUploadError()
    
    json_response = response.json()
    if json_response['bucket'] != bucket_name or json_response['name'] != blob_name:
      raise CloudStorageUploadError()
    
    logger.info(json_response)
    return json_response
  
  
def generate_download_signed_url_v4(bucket_name, blob_name, credentials=None, expiration=datetime.timedelta(minutes=15)):
  """Generates a v4 signed URL for downloading a blob. """
  if credentials is None:
    credentials = get_google_storage_credentials()
    
  bucket = storageClient.get_bucket(bucket_name)
  try: 
    blob = bucket.blob(blob_name)
    url = blob.generate_signed_url(
      expiration=expiration,
      method="GET",
      credentials=credentials
    )
    return url

  except Exception as inst:
    logger.error(type(inst))
    logger.error(inst.args)
    logger.error(inst)
    return None


def download_blob_as_json(blob, enc='utf-8'):
  '''
    Return the contents of a blob JSON file as a JSON object.

    Arguments:
      blob: The blob to read
      enc (string): The encoding of the file
  '''
  return json.loads(blob.download_as_string().decode(enc))


def download_blob_as_dataframe(blob, sep='\t', enc='utf-8', empty_as_none=True):
  '''
    Return the contents of a blob CSV file as a Pandas DataFrame.

    Arguments:
      blob: The blob to read
      sep (string): The separator character to use when parsing
      enc (string): The encoding of the file
      empty_as_none (bool): If True, return an empty file as None instead of an empty DataFrame
  '''

  # Download the blob (safely)
  try:
    result = blob.download_as_string().decode(enc)
  except Exception as ex:
    raise TypeError() from ex

  # Check for empty file
  if empty_as_none and len(result) == 0:
    return None

  # Convert to dataframe using desired separator
  return pd.read_csv(io.StringIO(result), sep=sep)
