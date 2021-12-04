import os

from caendr.models.datastore import Entity

MODULE_SITE_BUCKET_PUBLIC_NAME = os.environ.get('MODULE_SITE_BUCKET_PUBLIC_NAME')
PROFILE_PHOTO_PATH_PREFIX = 'profile/photos'


class Profile(Entity):
  kind = 'profile'
  __bucket_name = MODULE_SITE_BUCKET_PUBLIC_NAME
  __blob_prefix = PROFILE_PHOTO_PATH_PREFIX
  
  def __init__(self, *args, **kwargs):
    super(Profile, self).__init__(*args, **kwargs)
    self.set_properties(**kwargs)

  def set_properties(self, **kwargs):
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)
    if not hasattr(self, 'prof_roles'):
      self.prof_roles = []
      
  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name
  
  @classmethod
  def get_blob_prefix(cls):
    return cls.__blob_prefix

  @classmethod
  def get_props_set(cls):
    return {'id',
            'first_name', 
            'last_name', 
            'title', 
            'org', 
            'prof_roles',
            'img_blob_path', 
            'website',
            'email'}
    
  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<{self.kind}:{self.id}>"
    else:
      return f"<{self.kind}:no-id>"
