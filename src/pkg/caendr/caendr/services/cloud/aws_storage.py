import io
import os
import datetime
from enum import Enum
import requests
from typing import Optional, List
from werkzeug.utils import secure_filename

from boto3 import client
from botocore import exceptions

import pandas as pd

from caendr.services.logger import logger

from caendr.models.error import CloudStorageUploadError, NotFoundError
from caendr.services.cloud.secret import get_secret
from caendr.services.cloud.service_account import get_service_account_credentials
from caendr.utils.data import unique_id
from caendr.utils.env import get_env_var

AWS_OPEN_DATA_BUCKET = get_env_var('AWS_OPEN_DATA_BUCKET')
AWS_REGION = get_env_var('AWS_REGION')
AWS_ACCESS_KEY_ID = get_secret('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = get_secret('AWS_SECRET_ACCESS_KEY')

storageClient = client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

buffersize = 2 ** 20

#
# Check blobs
#

class AWSBlob():
  __buffersize = 10000000
  
  def __init__(self, name = None, bucket = None, path = None):
    self.name = name
    self.bucket = bucket
    self.path = path

  def exists(self):
    return self.name is not None
  
  def download_to_file(self, target_file):
    response = storageClient.get_object(Bucket=self.bucket, Key=join_path(self.path))
    buffer = response['body'].read(self.__buffersize)
    while buffer:
      target_file.write(buffer)
      buffer = response['body'].read(self.__buffersize)



def join_path(*path: str, sep: str = '/'):
  '''
    Join a list of path elements into a single path.
    Filters out empty elements, and strips the separator character (default `/`) before joining to avoid concatenating multiple separators.

    If all elements are empty, results in an empty string.
  '''
  return sep.join([ p.strip(sep) for p in path if p ])


def aws_get_blob(bucket_name: str, *path: str) -> dict:
  logger.debug(f'get_blob(bucket_name={bucket_name}, path={join_path(*path)})')
  try:
    blob = storageClient.head_object(Bucket=bucket_name, Key=join_path(*path))
    blob = AWSBlob(name=blob, bucket=bucket_name, path=path)
  except exceptions.ClientError:
    blob = AWSBlob()
  return blob


def aws_check_blob_exists(bucket_name: str, *path: str) -> bool:
  logger.debug(f'aws_check_blob_exists(bucket_name={bucket_name}, path={join_path(*path)})')
  try:
    blob = storageClient.head_object(Bucket=bucket_name, Key=join_path(*path))
    return True
  except exceptions.ClientError:
    return False
  

def aws_get_blob_if_exists(bucket_name: str, *path: str, fallback=None) -> Optional[dict]:
  '''
    Get the given blob if it exists, otherwise return the fallback value.
  '''
  try:
    blob = storageClient.head_object(Bucket=bucket_name, Key=join_path(*path))
    return AWSBlob(name=blob, bucket=bucket_name, path=path)
  except exceptions.ClientError:
    return fallback


def aws_get_blob_list(bucket_name: str, *prefix: str, filter=None) -> List[dict]:
  '''
    Returns a list of all blobs with `prefix` (directory) in `bucket_name`.
    If no `prefix` is provided (or all values are empty), lists all blobs in the bucket.
  '''

  # Get all the blobs in the given bucket
  items = storageClient.list_objects(Bucket=bucket_name, Prefix=join_path(*prefix))['Contents']
  items = [AWSBlob(name=item['Key'], bucket=bucket_name, path=prefix + (item['Key'],)) for item in items]

  # Apply the filter, if one was given
  if filter is not None:
    items = [ b for b in items if filter(b) ]

  # Return the items as a list
  return items


#
# Generate URIs
#


class AWSBlobURISchema(Enum):
  PATH   = ['', '']
  HTTP   = ['http://', '.s3.' + AWS_REGION + '.amazonaws.com']
  HTTPS  = ['https://', '.s3.' + AWS_REGION + '.amazonaws.com']
  GS     = ['s3://', '']
  SIGNED = 'SIGNED'

  @classmethod
  def http(cls, secure: bool):
    '''
      Convenience method to get http(s) based on boolean.
      If `secure` is True, returns HTTPS, else returns HTTP
    '''
    return cls.HTTPS if secure else cls.HTTP

  @classmethod
  def sign(cls, sign: bool, secure: bool = False):
    '''
      Convenience method to get signed URL based on boolean.
      If `sign` is True, returns SIGNED,
      Otherwise, if `secure` is True, returns HTTPS, else returns HTTP
    '''
    return cls.SIGNED if sign else cls.http(secure=secure)


def aws_generate_blob_uri(bucket: str, *path: str, schema: AWSBlobURISchema = AWSBlobURISchema.PATH):
    '''
      Generate a URI path for a blob.

      Arguments:
        bucket (`str`):
          The source bucket for the blob.
        *path (`str`):
          Some number of strings comprising the path to the blob within the bucket.
        schema (`AWSBlobURISchema`):
          Enum specifier for the format of the URI.
          Default `BlobURISchema.PATH` -- see Return section below.

      Returns:
        - If `schema` is `AWSBlobURISchema.PATH`, a tuple of strings containing the bucket and the full path within the bucket. (i.e. joins the path).
        - If any other schema is used, a single string comprising the full URI.
    '''

    # Use raw 'PATH' by default
    if schema is None:
      schema = AWSBlobURISchema.PATH

    # Join all the non-empty entries in the provided path
    path = '/'.join([ p for p in path if p ])

    # Raw path - return bucket and joined path
    if schema == AWSBlobURISchema.PATH:
      return bucket, path

    # Otherwise, use the prefix from the enum
    return f'{ schema.value[0] }{ bucket }{ schema.value[1]}/{ path }'


def make_secure_filename(*options):
  '''
    Loop through a list of possible filenames, returning the first that's safe.
    If no option in the list is safe, or if no options provided, returns a randomized (safe) string.
  '''
  for option in options:
    try:
      fname = secure_filename(option)
      if fname:
        return fname
    except:
      pass
  return secure_filename(unique_id())


def aws_download_blob_to_file(bucket_name, *path, destination='', filename=None):
  '''
    Downloads a blob and saves it locally.

    Validates the `filename` argument using Werkzeug `secure_filename`.
    Does NOT validate `destination` the same way.

    If you want to download a blob into a specific folder, use `destination`.
    You'll have to make sure the path is secure.

    Arguments:
      - `bucket_name`: The name of the bucket where the blob is located
      - `*path`: The path to the file within the bucket (incl. the filename itself)
      - `destination`: The local folder to download the blob to. Optional.
      - `filename`:
          A local name for the downloaded blob. May be changed by Werkzeug `secure_filename`.
          If not provided, uses the name of the file in datastore (i.e. the right-most component of the `path`).

    Returns:
      The local filepath / filename for the downloaded blob.
      Note that this may be different from the passed filename, if that name was not secure.

    Raises:
      NotFoundError: The desired blob does not exist.
  '''

  # If no filename provided, try using the final component of blob path
  target_filename = os.path.join(destination, make_secure_filename(filename, path[-1].split('/')[-1]))

  source_filename = "https://" + bucket_name + ".s3." + AWS_REGION + ".amazonaws.com/" + "/".join(path)
  try:
    with requests.get(source_filename, stream=True) as r:
      r.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

      # Open the local file in binary write mode.
      with open(target_filename, 'wb') as f:
        
        # Iterate over the response content in chunks and write to the file.
        for chunk in r.iter_content(chunk_size=buffersize):  # Adjust chunk_size as needed
          f.write(chunk)

  except requests.exceptions.RequestException as e:
    print(f"Error downloading file: {e}")

  # # Retrieve the blob, throwing an error if it doesn't exist
  # blob = aws_get_blob(bucket_name, *path)
  # if not (blob and blob.exists()):
  #   raise NotFoundError('blob', {'bucket': bucket_name, 'name': join_path(*path)})

  # # Download the blob to a file and return the filename
  # blob.download_to_file(open(target_filename, 'wb'))
  return target_filename

