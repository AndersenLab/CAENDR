from enum import Enum

from caendr.models.datastore import DeletableEntity
from caendr.utils.data       import unique_id



class AnnouncementType(Enum):
  GENERAL     = 'General'
  MAINTENANCE = 'Maintenance'
  ERROR       = 'Error'

  def get_bootstrap_color(self):
    __BOOTSTRAP_COLOR_MAP = {
      AnnouncementType.GENERAL:     'success',
      AnnouncementType.MAINTENANCE: 'warning',
      AnnouncementType.ERROR:       'danger',
    }
    return __BOOTSTRAP_COLOR_MAP[self]




class Announcement(DeletableEntity):
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
      'style',
    }


  @property
  def active(self):
    return self._get_raw_prop('active', False)

  @active.setter
  def active(self, val):
    self._set_raw_prop('active', bool(val))


  @property
  def style(self):
    return self._get_enum_prop(AnnouncementType, 'style', None)

  @style.setter
  def style(self, val):
    return self._set_enum_prop(AnnouncementType, 'style', val)
