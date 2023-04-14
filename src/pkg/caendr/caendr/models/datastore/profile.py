import os

from caendr.services.logger import logger

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


  ## Roles ##

  # Define local Profile Role class to track possible roles
  class Role:
    def __init__(self, code, display):
      self.code    = code
      self.display = display

    # Validate a role object or role code string
    @staticmethod
    def validate(role):
      if not isinstance(role, Profile.Role):
        Profile.Role.lookup(role)

    # Look up a role object by its code string
    @staticmethod
    def lookup(role_code):
      for role in Profile.all_roles():
        if role.code == role_code:
          return role
      raise TypeError(f'Could not find role with code "{role_code}"')

  # Define profile roles
  STAFF    = Role('staff',  'Staff')
  COMMITEE = Role('sac',    'Scientific Advisory Committee')
  COLLAB   = Role('collab', 'Collaborators')

  @staticmethod
  def all_roles():
    """
      Get a list of all Profile roles, in the order they should be displayed.
    """
    return [ Profile.STAFF, Profile.COMMITEE, Profile.COLLAB ]


  ## Props ##

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
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


  ## Special Properties ##

  # Prop should default to empty list if not set
  @property
  def prof_roles(self):
    return [
      Profile.Role.lookup(role_code) for role_code in self.__dict__.get('prof_roles', [])
    ]

  @prof_roles.setter
  def prof_roles(self, val):

    # Only allow list to be set
    if not isinstance(val, list):
      raise TypeError('Must set prof_roles to a list.')

    # Validate each role in the list
    for role in val:
      Profile.Role.validate(role)

    # Save prop in object's local dictionary
    # Make sure to save as code strings instead of Role objects
    self.__dict__['prof_roles'] = [
      role.code if isinstance(role, Profile.Role) else role
        for role in val
    ]



  @property
  def img_url(self):
    '''
      URL for profile image. Constructed from blob path, if one is provided.
    '''
    if self.img_blob_path:
      return generate_blob_url(Profile.get_bucket_name(), self.img_blob_path)

    return None


  ## Querying ##

  @classmethod
  def query_ds_roles(cls, roles):

    # Accept single role by converting to singleton array
    if isinstance(roles, Profile.Role):
      roles = [roles]

    # Validate roles in query
    for role in roles:
      try:
        Profile.Role.validate(role)
      except TypeError as ex:
        raise TypeError(f'Cannot query profiles for role "{role}": {ex}.')

    # Log query
    logger.debug(f'Retrieving {[role.code for role in roles]} profiles from datastore')

    # Query by role(s)
    # Filtering against a list property returns a result if any value in the list matches
    return cls.query_ds(filters = [
      ('prof_roles', '=', role.code) for role in roles
    ])
