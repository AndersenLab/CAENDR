from caendr.services.logger import logger
from caendr.models.datastore import Entity



class HashableEntity(Entity):
  '''
    An entity with a data hash property.
  '''

  ## Initialization ##

  def __new__(cls, *args, **kwargs):
    if cls is HashableEntity:
      raise TypeError(f"Class '{cls.__name__}' should never be instantiated directly -- subclasses should be used instead.")
    return super(HashableEntity, cls).__new__(cls)


  ## Properties List ##

  @classmethod
  def get_props_set_meta(cls):
    return {
      *super().get_props_set_meta(),
      'data_hash',
    }

  # Include data hash when iterating
  def __iter__(self):
    yield from super().__iter__()
    yield ('data_hash', self.data_hash)


  ## Meta props ##

  @property
  def data_hash(self):
    '''
      A hash value generated from the data associated with this Entity.
    '''
    return self._get_meta_prop('data_hash')

  @data_hash.setter
  def data_hash(self, val):
    logger.debug(f'Setting data hash for Entity {self.id} to {val}.')
    self._set_meta_prop('data_hash', val)
