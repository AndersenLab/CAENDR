import os

from caendr.models.datastore import Entity, DatasetRelease
from caendr.services.cloud.storage import generate_blob_url
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
    # TODO: add /browser_tracks to end of path, once all track files are in this folder
    return (DatasetRelease.get_bucket_name(), DatasetRelease.get_path_template())

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
    return path.update_template_string( generate_blob_url(bucket, f'{ path.raw_string }/{ self["filename"] }') )


  ## FASTA ##

  @staticmethod
  def get_fasta_filename():
    return TokenizedString('browser_tracks/c_${SPECIES}.${PRJ}.${WB}.genome.fa')

  @staticmethod
  def get_fasta_path_full():
    bucket, path   = BrowserTrack.release_path()
    fasta_filename = BrowserTrack.get_fasta_filename()
    return path.update_template_string( generate_blob_url(bucket, f'{ path.raw_string }/{ fasta_filename.raw_string }') )


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
      return super().get_path()

  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'template_name', 'no-name')}>"
