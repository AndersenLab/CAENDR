from caendr.models.datastore import Entity
from caendr.utils.data       import unique_id



class Announcement(Entity):
  kind = 'announcement'

  exclude_from_indexes = ('content', 'url_list')


  def __init__(self, name_or_obj = None, *args, **kwargs):

    # If nothing passed for name_or_obj, create a new ID to use for this object
    if name_or_obj is None:
      name_or_obj = unique_id()
      self.set_properties_meta(id = name_or_obj)

    # Initialize from superclass
    super().__init__(name_or_obj, *args, **kwargs)


  ## Props ##

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'active',
      'content',
      'url_list',
    }


  @property
  def active(self):
    return self._get_raw_prop('active', False)

  @active.setter
  def active(self, val):
    self._set_raw_prop('active', bool(val))
