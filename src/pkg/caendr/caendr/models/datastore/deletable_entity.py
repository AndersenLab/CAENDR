from caendr.models.datastore import Entity
from caendr.models.error import NotFoundError, NonUniqueEntity



class DeletableEntity(Entity):
  '''
    Subclass of Entity for objects that need 'soft delete' functionality

    Should never be instantiated directly -- in fact, this is prevented in this class's __new__ function.
    Instead, specific entity types should be subclasses of this class.
  '''
  
  def __new__(cls, *args, **kwargs):
    if cls is DeletableEntity:
      raise TypeError(f"Class '{cls.__name__}' should never be instantiated directly -- subclasses should be used instead.")
    return super(DeletableEntity, cls).__new__(cls)


  def __init__(self, *args, **kwargs):
  # Initialize from superclass 
    super().__init__(*args, **kwargs)
    if not self['is_deleted']:
      self['is_deleted'] = False


  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'is_deleted'
    }
  


  @classmethod
  def query_ds_not_deleted(cls, key, val, unique=False, required=False):

    '''
      Query the datatstore for the entities that are 'not_deleted'.

      If 'unique' is set to True and multiple entities were found will raise NonUniqueEntity error with all matches in the `matches` field;
      otherwise return all entities that match the query

      If `required` is set to True, will raise an error if no such entity is found; otherwise returns None.

    '''

    # Run query with given key and val
    matches = cls.query_ds(filters=[(key, '=', val)])
    matches = [ el for el in matches if not el['is_deleted'] ]

    # If no matching entities found, return None
    if len(matches) == 0:
      if required:
        raise NotFoundError(cls.kind, {key: val})
      else:
        return None

    # If looking up for unique entity and multiple were found, raise an error
    elif len(matches) > 1 and unique:
      raise NonUniqueEntity( cls.kind, key, val, matches )
    
    # If one or more entities were found and 'unique' is set to False, return all of them
    else:
      return matches


  def soft_delete(self):
    ''' Flag the entity deleted '''
    self['is_deleted'] = True

  def undelete(self):
    ''' Flag the entity un-deleted '''
    self['is_deleted'] = False

