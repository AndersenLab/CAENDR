from time import time

from caendr.models.datastore import Entity, User
from caendr.utils.env import get_env_var


USER_OWNED_ENTITY_CACHE_AGE_SECONDS = get_env_var('USER_OWNED_ENTITY_CACHE_AGE_SECONDS', var_type=int)



class UserOwnedEntity(Entity):
  '''
    Subclass of Entity for objects owned by a specific user.

    Should never be instantiated directly -- in fact, this is prevented in this class's __new__ function.
    Instead, specific entity types should be subclasses of this class.
  '''

  __user_cache = {}

  # @cache.memoize(60*60)
  @staticmethod
  def fetch_user(username):
    '''
      Get a User object from this class's cache.
    '''
    if username is None:
      return None
    curr_time = time()
    cached_val = UserOwnedEntity.__user_cache.get(username)
    if cached_val is None or cached_val['age'] + USER_OWNED_ENTITY_CACHE_AGE_SECONDS < curr_time:
      UserOwnedEntity.__user_cache[username] = {
        'age': curr_time,
        'val': User.get_ds(username),
      }
    return UserOwnedEntity.__user_cache[username]['val']


  def __new__(cls, *args, **kwargs):
    if cls is UserOwnedEntity:
      raise TypeError(f"Class '{cls.__name__}' should never be instantiated directly -- subclasses should be used instead.")
    return super(UserOwnedEntity, cls).__new__(cls)


  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'user_id',
      'username',
    }


  ## User Object ##

  def get_user(self) -> User:
    '''
      Look up the user associated with this submission.
    '''
    # return UserOwnedEntity.fetch_user(self['user_id'])
    return UserOwnedEntity.fetch_user(self['username'])


  def set_user(self, user: User):
    '''
      Set user properties from a User object.
      By default, sets username to match provided user.
    '''
    # self['user_id'] = user.name
    self['username'] = user.name


  ## User Fields ##

  def get_user_name(self):
    user = self.get_user()
    return user['username'] if user is not None else None
  
  def get_user_email(self):
    user = self.get_user()
    return user['email'] if user is not None else None
  
  def get_user_full_name(self):
    user = self.get_user()
    return user['full_name'] if user is not None else None


  ## Misc ##

  def get_display_name(self):
    return self.get_user_full_name() or self.get_user_name() or self.get_user_email() or 'UNKNOWN'
