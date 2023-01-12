import os
from logzero import logger

from google.cloud import datastore

from caendr.models.datastore import Container, Entity
from caendr.services.cloud.datastore import get_ds_entity



MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')
INDEL_REPORT_PATH_PREFIX = 'reports'
INDEL_INPUT_FILE = 'input.json'
INDEL_RESULT_FILE = 'results.tsv'


class IndelPrimer(Entity):
  kind = 'indel_primer'
  __bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
  __blob_prefix = INDEL_REPORT_PATH_PREFIX
  __input_file  = INDEL_INPUT_FILE
  __result_file = INDEL_RESULT_FILE

  # Map from Indel Primer container fields -> Container fields
  __container_prop_map = {
    'container_repo':     'repo',
    'container_name':     'container_name',
    # 'container_registry': 'container_registry',
    'container_version':  'container_tag',
  }

  
  def __init__(self, *args, **kwargs):
    super(IndelPrimer, self).__init__(*args, **kwargs)
    self._init_container(*args, **kwargs)
    self.set_properties(**kwargs)


  def set_properties(self, **kwargs):

    # Set normal props directly
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)

    # Pass container props to Container
    self._set_container_props_from(kwargs)


  ## Setting Container props ##

  def _init_container(self, *args, **kwargs):
    '''
      Initialize this Indel Primer result's source Container object.
      Accepts *args and **kwargs from __init__.
    '''

    # Initialize Container object
    self.__container = Container()

    # Copying an existing Entity object
    if len(args) > 0 and type(args[0]) == datastore.entity.Entity:
      self._set_container_props_from(args[0])

    # Downloading an existing Entity from datastore
    elif self._exists:
      item = get_ds_entity(self.kind, args[0])
      self._set_container_props_from(item)


  def _set_container_props_from(self, src):
    '''
      Set the Container object's properties from a source.

      Properties must be accessible in the source via __getitem__ (i.e. bracket notation).
      Properties in the source must be named by the *keys* in IndelPrimer.__container_prop_map.
    '''
    self.__container.set_properties(**{
        container_field_name: src[indel_field_name]
          for indel_field_name, container_field_name in self.__container_prop_map.items()
          if indel_field_name in src
      })



  ## Bucket ##

  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name
  
  def get_blob_path(self):
    return f'{self.__blob_prefix}/{self.container_name}/{self.data_hash}'
  
  def get_data_blob_path(self):
    return f'{self.get_blob_path()}/{self.__input_file}'
  
  def get_result_blob_path(self):
    return f'{self.get_blob_path()}/{self.__result_file}'



  ## Container object ##

  def get_container(self) -> Container:
    '''
      Get the Container for this object.
    '''
    return self.__container


  def set_container(self, c: Container):
    '''
      Set the Container for this object. Implicitly sets all container fields.
    '''
    if type(c) != Container:
      raise TypeError()
    self.__container = c


  def container_equals(self, c: Container) -> bool:
    '''
      Check whether this object was generated in a given Container.

      TODO: Should this be equivalent to two Containers being equal (__eq__)?
            Currently ignores container registry, since existing Indel Primer
            results don't store that field.
    '''
    if type(c) != Container:
      return False

    # Check whether repo + name + tag is the same for both Containers
    return self.__container.full_string() == c.full_string()



  ## Container properties ##

  # Make these explicitly properties of Indel Primer object so that getting/setting
  # redirects to Container object -- single source of truth

  @property
  def container_repo(self):
    return self.__container[ self.__container_prop_map['container_repo'] ]

  @container_repo.setter
  def container_repo(self, v):
    self.__container[ self.__container_prop_map['container_repo'] ] = v

  @property
  def container_name(self):
    return self.__container[ self.__container_prop_map['container_name'] ]

  @container_name.setter
  def container_name(self, v):
    self.__container[ self.__container_prop_map['container_name'] ] = v

  @property
  def container_version(self):
    return self.__container[ self.__container_prop_map['container_version'] ]

  @container_version.setter
  def container_version(self, v):
    self.__container[ self.__container_prop_map['container_version'] ] = v



  ## All Properties ##

  @classmethod
  def get_props_set(cls):
    return {
      # Submission
      'id',
      'data_hash',
      'username',
      'operation_name',

      # Status
      'status',
      'no_result',

      # Query
      'site',
      'strain_1',
      'strain_2',

      # Container
      'container_repo',
      'container_name',
      'container_version',

      # Files
      'sv_bed_filename',
      'sv_vcf_filename',
    }


  def __getitem__(self, prop):
    '''
      Make properties listed in props_set accessible with bracket notation.
      Properties that are not set will return as None.

      Container properties are taken from Container object.

      Raises:
        KeyError: prop not found in props_set
    '''

    # Lookup prop in dictionary
    if prop in IndelPrimer.get_props_set():
      return self.__dict__.get(prop)

    # If prop not in list, raise an error
    raise KeyError()



  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<{self.kind}:{self.id}>"
    else:
      return f"<{self.kind}:no-id>"
