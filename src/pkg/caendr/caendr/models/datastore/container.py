import os

from caendr.models.datastore import Entity

class Container(Entity):
  kind = 'container'

  def __init__(self, *args, **kwargs):
    super(Container, self).__init__(*args, **kwargs)
    self.set_properties(**kwargs)

  def set_properties(self, **kwargs):
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)

  @classmethod
  def get_props_set(cls):
    return {
      *super(Container, cls).get_props_set(),
      'repo',
      'container_name',
      'container_registry',
      'container_tag',
    }

  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<{self.kind}:{self.id}>"
    else:
      return f"<{self.kind}:no-id>"

  def full_string(self):
    s = f"{self['repo']}/{self['container_name']}"
    if self['container_tag']:
      s += ':' + self['container_tag']
    return s
