from google.cloud import datastore

class Settings(datastore.Entity):
  
  def __init__(self, name):
    super().__init__(kind="settings"*args, **kwargs)
    self.set_properties(**kwargs)

  def set_properties(self, **kwargs):
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)
      
  @classmethod
  def get_props_set(cls):
    return {
      'default_dataset_release_version'
    }
    
  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<{self.kind}:{self.id}>"
    else:
      return f"<{self.kind}:no-id>"
    