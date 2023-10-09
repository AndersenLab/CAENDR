from caendr.models.datastore import Entity



class DeletableEntity(Entity):
  '''
  '''
  # TODO: Documentation string (above) that explains what this class is for


  # TODO: __new__ function that prevents this subclass from being instantiated directly
  #       Hint: Take a look at UserOwnedEntity


  # TODO: __init__ function
  #       Should use super() to call the __init__ method of Entity,
  #       and initialize any properties unique to this subclass (from get_props_set)


  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      # TODO: List any properties that belong in this subclass
    }


  # TODO: Function to soft delete this object
  #       Hint: Take a look at Cart

  # TODO: Function to un-delete (restore?) this object?
  #       Might not be useful now, but it's a good idea to have one

  # TODO: Function to query only entities that haven't been deleted
  #       Hint: Take a look at Cart
