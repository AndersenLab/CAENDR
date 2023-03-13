import os

from caendr.models.datastore import Entity



class Markdown(Entity):
  kind = 'markdown'

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'username',
      'type',
      'title',
      'content',
    }
