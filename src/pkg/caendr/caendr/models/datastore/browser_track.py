import os

from caendr.models.datastore import Entity, DatasetRelease
from caendr.services.cloud.storage import BlobURISchema, generate_blob_uri
from caendr.utils.tokens import TokenizedString


MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')
MODULE_SITE_BUCKET_PUBLIC_NAME  = os.environ.get('MODULE_SITE_BUCKET_PUBLIC_NAME')



class BrowserTrack(Entity):


  ## Initialization ##

  def __new__(cls, *args, **kwargs):
    if cls is BrowserTrack:
      raise TypeError(f"Class '{cls.__name__}' should never be instantiated directly -- subclasses should be used instead.")
    return super(BrowserTrack, cls).__new__(cls)


  ## Filepaths ##

  @staticmethod
  def release_path():
    return (DatasetRelease.get_bucket_name(), DatasetRelease.get_path_template() + '/browser_tracks')

  @staticmethod
  def bam_bai_path():
    return (MODULE_SITE_BUCKET_PRIVATE_NAME, TokenizedString('bam'))

  def get_path(self):
    '''
      Get the path in GCP to this specific Browser Track. Overwritten in subclass(es).
    '''
    return BrowserTrack.release_path()

  def get_url_template(self):
    bucket, path = self.get_path()
    return path.update_template_string( generate_blob_uri(bucket, path.raw_string, self['filename'], schema=BlobURISchema.HTTPS) )


  ## Props ##

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'filename',
      'name',
      'order',
      'params',
    }


  @property
  def params(self):
    '''
      The params object includes some fields stored elsewhere in the Entity. These are included in
      params when getting and filtered out when setting, to maintain one source of truth.
    '''

    # Include name, order, URL in params dict
    params = {
      **self.__dict__.get('params', {}),
      'name':  self['name'],
      'order': self['order'],
      'url':   self.get_url_template().raw_string,
    }

    # Add indexURL if defined
    if self.__class__ == BrowserTrackTemplate and self['index_suffix']:
      params['indexURL'] = params['url'] + self['index_suffix']

    return params


  @params.setter
  def params(self, val):
    # Filter out params that draw from object props
    self.__dict__['params'] = {
      k: v for k, v in val.items() if k not in ['name', 'order', 'url', 'indexURL']
    }


  



class BrowserTrackDefault(BrowserTrack):
  kind = 'browser_track_default'

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'checked',
    }



class BrowserTrackTemplate(BrowserTrack):
  kind = 'browser_track_template'

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'template_name',
      'index_suffix',
      'is_bam',
    }

  def get_path(self):
    if self['is_bam']:
      return BrowserTrack.bam_bai_path()
    else:
      return (DatasetRelease.get_bucket_name(), DatasetRelease.get_path_template())

  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'template_name', 'no-name')}>"
