import os

from caendr.models.datastore import Entity
from caendr.services.cloud.storage import generate_blob_url

MODULE_SITE_BUCKET_PUBLIC_NAME = os.environ.get('MODULE_SITE_BUCKET_PUBLIC_NAME')
PROFILE_PHOTO_PATH_PREFIX = 'profile/photos'


class Profile(Entity):
  kind = 'profile'
  __bucket_name = MODULE_SITE_BUCKET_PUBLIC_NAME
  __blob_prefix = PROFILE_PHOTO_PATH_PREFIX

  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name

  @classmethod
  def get_blob_prefix(cls):
    return cls.__blob_prefix

  @classmethod
  def get_props_set(cls):
    return {
      *super(Profile, cls).get_props_set(),
      'id',
      'first_name',
      'last_name',
      'title',
      'org',
      'prof_roles',
      'img_blob_path',
      'website',
      'email',
    }

  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'id', 'no-id')}>"


  ## Special Properties ##

  @property
  def prof_roles(self):
    # Prop should default to empty list if not set
    return self.__dict__.get('prof_roles', [])

  @prof_roles.setter
  def prof_roles(self, val):
    # Save prop in object's local dictionary
    self.__dict__['prof_roles'] = val



  @property
  def img_url(self):
    '''
      URL for profile image. Constructed from blob path, if one is provided.
    '''
    if self.img_blob_path:
      return generate_blob_url(Profile.get_bucket_name(), self.img_blob_path)

    return None
