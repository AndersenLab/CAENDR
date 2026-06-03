import bleach
from   enum import Enum
import markdown
import re

from markupsafe import Markup

from caendr.models.datastore import DeletableEntity, OrderableEntity
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




class Announcement(DeletableEntity, OrderableEntity):
  kind = 'announcement'

  exclude_from_indexes = ('content', 'url_list')


  def __init__(self, name_or_obj = None, *args, **kwargs):

    # If nothing passed for name_or_obj, create a new ID to use for this object
    if name_or_obj is None:
      name_or_obj = unique_id()
      self.set_properties_meta(id = name_or_obj)

    # Initialize from superclass
    super().__init__(name_or_obj, *args, **kwargs)



  #
  # Props
  #

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
  def content(self):
    return bleach.clean( self._get_raw_prop('content', '') )

  @content.setter
  def content(self, val):
    if not isinstance(val, str):
      raise ValueError(f'Prop "content" must be a string, got: {val}')
    return self._set_raw_prop( 'content', bleach.clean( val ) )


  @property
  def style(self):
    return self._get_enum_prop(AnnouncementType, 'style', None)

  @style.setter
  def style(self, val):
    return self._set_enum_prop(AnnouncementType, 'style', val)


  @property
  def url_list(self):
    return self._get_raw_prop('url_list', '')

  @url_list.setter
  def url_list(self, val):
    '''
      Validate the list of URL patterns before saving.
    '''

    # Accept newline-separated string or iterable of patterns
    # Convert to a list for validating
    if isinstance(val, str):
      val = [ pattern.strip() for pattern in val.split('\n') ]
    if not isinstance(val, list):
      try:
        val = [*val]
      except:
        raise ValueError('URL list must be an iterable or a newline-separated string')

    # Validate each pattern
    for idx, path in enumerate(val):
      if not self.validate_path(path):
        raise ValueError(f'Invalid pattern on line {idx}: "{path}"')

    # If validation succeeded, convert to newline-separated string and save
    return self._set_raw_prop('url_list', '\n'.join(val))



  #
  # Extra Props
  #

  @property
  def content_html(self):
    '''
      The content of this announcement as HTML.
    '''
    return Markup(markdown.markdown( self['content'] ))


  def serialize(self, **kwargs):
    props = super().serialize(**kwargs)
    props['content_html'] = self.content_html
    return props



  #
  # URL Paths
  #

  @classmethod
  def validate_path(cls, path: str) -> bool:
    '''
      Each path must meet the following constraints:
        - The first character is a forward slash
        - If there is an asterisk (wildcard), it must:
          - be the final character
          - be preceded by a forward slash

      Sample valid paths:
        /
        /*
        /foo/bar/baz/*

      Sample invalid paths:
        foo/bar
        /foo*
        /foo*/bar
    '''
    return path.startswith("/") and ("*" not in path or path.endswith("/*"))


  def matches_path(self, path: str) -> bool:

    # Loop through each line in the URL list
    for pattern in self['url_list'].split('\n'):

      # Turn our wildcard into a Regex wildcard, if given
      if pattern.endswith('/*'):
        pattern = pattern[:-2]
        suffix  = '(/.*)?'
      else:
        suffix  = ''

      # Check this pattern
      if re.match(f'^{ pattern }{ suffix }$', path):
        return True

    # If no patterns matched, path does not match
    return False
