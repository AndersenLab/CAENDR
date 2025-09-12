import io
import os
import datetime
from enum import Enum
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

AWS_OPEN_DATA_BUCKET = os.environ.get('AWS_OPEN_DATA_BUCKET')
AWS_REGION = os.environ.get('AWS_REGION')

storageClient = client('s3')

#
# Check blobs
#

def join_path(*path: str, sep: str = '/'):
  '''
    Join a list of path elements into a single path.
    Filters out empty elements, and strips the separator character (default `/`) before joining to avoid concatenating multiple separators.

    If all elements are empty, results in an empty string.
  '''
  return sep.join([ p.strip(sep) for p in path if p ])


def aws_get_blob(bucket_name: str, *path: str) -> dict:
  logger.debug(f'get_blob(bucket_name={bucket_name}, path={path})')
  blob = storageClient.head_object(Bucket=bucket_name, Key=path)
  return blob


def check_blob_exists(bucket_name: str, *path: str) -> bool:
  logger.debug(f'check_blob_exists(bucket_name={bucket_name}, path={path})')
  try:
    blob = storageClient.head_object(Bucket=bucket_name, Key=path)
    return True
  except exceptions.ClientError:
    return False
  

def aws_get_blob_if_exists(bucket_name: str, *path: str, fallback=None) -> Optional[dict]:
  '''
    Get the given blob if it exists, otherwise return the fallback value.
  '''
  try:
    blob = storageClient.head_object(Bucket=bucket_name, Key=path)
    return blob
  except exceptions.ClientError:
    return fallback


def aws_get_blob_list(bucket_name: str, *prefix: str, filter=None) -> List[dict]:
  '''
    Returns a list of all blobs with `prefix` (directory) in `bucket_name`.
    If no `prefix` is provided (or all values are empty), lists all blobs in the bucket.
  '''

  # Get all the blobs in the given bucket
  items = storageClient.list_objects(Bucket=bucket_name, Prefix=prefix)

  # Apply the filter, if one was given
  if filter is not None:
    items = [ b for b in items if filter(b) ]

  # Return the items as a list
  return list(items)


#
# Generate URIs
#


class AWSBlobURISchema(Enum):
  PATH   = ['', '']
  HTTP   = ['http://', '.' + AWS_REGION + '.amazonaws.com']
  HTTPS  = ['https://', '.' + AWS_REGION + '.amazonaws.com']
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
