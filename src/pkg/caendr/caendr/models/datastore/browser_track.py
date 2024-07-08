from caendr.utils.env              import get_env_var

from caendr.models.datastore       import FileRecordEntity, DatasetRelease
from caendr.services.cloud.storage import BlobURISchema
from caendr.utils.data             import unique_id
from caendr.utils.tokens           import TokenizedString


MODULE_SITE_BUCKET_PRIVATE_NAME = get_env_var('MODULE_SITE_BUCKET_PRIVATE_NAME')



class BrowserTrack(FileRecordEntity):

  ## Default Release Path ##

  @staticmethod
  def release_bucket():
    '''
      Get the default bucket for the browser track files, determined by dataset release.
    '''
    return DatasetRelease.get_bucket_name()

  @staticmethod
  def release_prefix():
    '''
      Get the default prefix for the browser track files, within a dataset release folder.
    '''
    return DatasetRelease.get_path_template() + '/browser_tracks'


  ## Props ##

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'display_name',
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
      'name':  self['display_name'],
      'order': self['order'],
      'url':   self.get_filepath_template(schema=BlobURISchema.HTTPS).raw_string,
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

  def _format_props_for_ds(self):
    props = super()._format_props_for_ds()
    props['params'] = self.__dict__['params']
    return props


  



class BrowserTrackDefault(BrowserTrack):
  kind = 'browser_track_default'


  def __init__(self, name_or_obj = None, *args, **kwargs):

    # If nothing passed for name_or_obj, create a new ID to use for this object
    if name_or_obj is None:
      name_or_obj = unique_id()
      self.set_properties_meta(id = name_or_obj)

    # Initialize from superclass
    super().__init__(name_or_obj, *args, **kwargs)


  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'checked',
      'used_in_tools',
    }

  @property
  def used_in_tools(self):
    # Empty list if not set
    return self.__dict__.get('used_in_tools', [])

  @used_in_tools.setter
  def used_in_tools(self, val):

    # Only allow list to be set
    if not isinstance(val, list):
      raise TypeError('Must set used_in_tools to a list.')

    # Save prop in object's local dictionary
    self.__dict__['used_in_tools'] = val


  @property
  def bucket(self) -> str:
    return super().release_bucket()

  @property
  def prefix(self) -> TokenizedString:
    return super().release_prefix()

  def available_in_release(self, release: DatasetRelease) -> bool:
    return (self['display_name'] in release['browser_tracks'])



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

  @property
  def bucket(self) -> str:
    if self['is_bam']:
      return MODULE_SITE_BUCKET_PRIVATE_NAME
    else:
      return super().release_bucket()

  @property
  def prefix(self) -> TokenizedString:
    if self['is_bam']:
      return TokenizedString('bam')
    else:
      return DatasetRelease.get_path_template()

  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'template_name', 'no-name')}>"
