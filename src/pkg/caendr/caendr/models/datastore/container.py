import os

from caendr.models.datastore import Entity

class Container(Entity):
  kind = 'container'

  @classmethod
  def get_props_set(cls):
    return {
      *super(Container, cls).get_props_set(),
      'repo',
      'container_name',
      'container_registry',
      'container_tag',
    }

  def full_string(self):
    s = f"{self['repo']}/{self['container_name']}"
    if self['container_tag']:
      s += ':' + self['container_tag']
    return s
