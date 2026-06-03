import os

from caendr.utils.env import get_env_var

from caendr.models.datastore import Entity

AWS_OPEN_DATA_BUCKET = get_env_var('AWS_OPEN_DATA_BUCKET')
PROTOCOL_PDF_PATH_PREFIX = 'protocol/pdf'


class Protocol(Entity):
  kind = 'protocol'
  __bucket_name = AWS_OPEN_DATA_BUCKET
  __blob_prefix = PROTOCOL_PDF_PATH_PREFIX

  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name

  @classmethod
  def get_blob_prefix(cls):
    return cls.__blob_prefix

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'id',
      'group',
      'title',
      'pdf_blob_path',
    }
