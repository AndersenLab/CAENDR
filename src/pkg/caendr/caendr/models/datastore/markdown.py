import os

from caendr.models.datastore import Entity



class Markdown(Entity):
  kind = 'markdown'

  @classmethod
  def get_props_set(cls):
    return {
      *super(Markdown, cls).get_props_set(),
      'username',
      'type',
      'title',
      'content',
    }

  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'id', 'no-id')}>"
