import os

from caendr.models.datastore import Entity

class Markdown(Entity):
  kind = 'markdown'
  
  def __init__(self, *args, **kwargs):
    super(Markdown, self).__init__(*args, **kwargs)
    self.set_properties(**kwargs)

  def set_properties(self, **kwargs):
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)
      
  @classmethod
  def get_props_set(cls):
    return {'username',
            'type',
            'title',
            'content'}
    
  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<{self.kind}:{self.id}>"
    else:
      return f"<{self.kind}:no-id>"
    