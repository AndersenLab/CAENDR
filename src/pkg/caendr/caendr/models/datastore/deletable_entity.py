from caendr.models.datastore import Entity
from caendr.models.error import NotFoundError, NonUniqueEntity



class DeletableEntity(Entity):
  '''
  Subclass of Entity for entities that need 'soft delete' functionality
  '''
  # TODO: Documentation string (above) that explains what this class is for


  # TODO: __new__ function that prevents this subclass from being instantiated directly
  #       Hint: Take a look at UserOwnedEntity
  
  def __new__(cls, *args, **kwargs):
    if cls is DeletableEntity:
      raise TypeError(f"Class '{cls.__name__}' should never be instantiated directly -- subclasses should be used instead.")
    return super(DeletableEntity, cls).__new__(cls)

  # TODO: __init__ function
  #       Should use super() to call the __init__ method of Entity,
  #       and initialize any properties unique to this subclass (from get_props_set)

  def __init__(self, *args, **kwargs):
  # Initialize from superclass 
    super().__init__(*args, **kwargs)
    if not self['is_deleted']:
      self['is_deleted'] = False


  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      # TODO: List any properties that belong in this subclass
      'is_deleted'
    }
  

  # TODO: Function to query only entities that haven't been deleted
  #       Hint: Take a look at Cart

  @classmethod
  def query_ds_not_deleted(cls, key, val, unique=False, required=False):

    # Run query with given key and val
    matches = cls.query_ds(filters=[(key, '=', val)])
    matches = [ el for el in matches if not el['is_deleted'] ]

    # If no matching entities found, return None
    if len(matches) == 0:
      if required:
        raise NotFoundError(cls.kind, {key: val})
      else:
        return None

    # If exactly one entity found, return it
    elif len(matches) > 1 and unique:
      raise NonUniqueEntity( cls.kind, key, val, matches )
    
    # If more than one entity found, return all
    else:
      return matches


  # TODO: Function to soft delete this object
  #       Hint: Take a look at Cart
  def soft_delete(self):
    self['is_deleted'] = True

  # TODO: Function to un-delete (restore?) this object?
  #       Might not be useful now, but it's a good idea to have one
  def undelete(self):
    self['is_deleted'] = False

