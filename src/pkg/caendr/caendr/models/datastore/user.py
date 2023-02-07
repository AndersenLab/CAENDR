from collections import defaultdict
from werkzeug.security import safe_str_cmp

from caendr.models.datastore import Entity
from caendr.services.cloud.datastore import query_ds_entities
from caendr.utils.data import get_password_hash


class User(Entity):
  kind = 'user'


  ## Initialization ##
  
  def __init__(self, *args, **kwargs):

    # Initialize roles to an empty list
    # Prevents site from failing if not defined in initialization
    self.roles = []

    # Pass args to super
    super(User, self).__init__(*args, **kwargs)


  @classmethod
  def from_email(self, email):
    '''
      Get a user by email.

      TODO: Should this return as a User object?
    '''
    filters = [ ('email', '=', email) ]
    results = query_ds_entities(self.kind, filters=filters)
    if len(results):
      return results[0]
    return None



  ## Properties List ##

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'username',
      'full_name',
      'password',
      'email',
      'roles',
      'last_login',
      'user_type',
    }



  ## Set Properties ##

  def __setitem__(self, prop, val):

    # Require password and salt to be set together
    # TODO: Technically, we could save both (e.g. as 'raw_password' and 'salt') and make password a property
    #       computed on the fly.  Would this be safe?
    if prop == 'password' or prop == 'salt':
      raise KeyError(f'Cannot set property {prop} alone; use User.set_password(password, salt) instead.')

    # Set email using special method
    # TODO: Is this necessary?
    elif prop == 'email':
      self.set_email(val)

    # Handle other props with default method
    else:
      return super().__setitem__( prop, val )



  def set_properties(self, **kwargs):

    # Set non-container props through super method
    super().set_properties(**{
      k: v for k, v in kwargs.items() if k not in ['password', 'salt']
    })

    # Set password and salt together
    if 'password' and 'salt' in kwargs:
      self.set_password(kwargs.get('password'), kwargs.get('salt'))



  ## Other ##

  def reports(self):
    ''' Gets a sorted list of the User's reports '''
    filters = [('user_id', '=', self.name)]
    # Note this requires a composite index defined very precisely.
    results = query_ds_entities(self.kind, filters=filters, order=['user_id', '-created_on'])
    results = sorted(results, key=lambda x: x['created_on'], reverse=True)
    results_out = defaultdict(list)
    for row in results:
      results_out[row['report_slug']].append(row)
    return results_out


  def set_password(self, password, salt):
    ''' Sets the User's password property to the salted and hashed version of their updated password '''
    if (isinstance(password, str) and len(password) > 0):
      self.password = get_password_hash(password + salt)
  

  def set_email(self, email, verified=False):
    ''' Updates the User's email and optionally marks it as verified '''
    self.email = email
    self.verified_email = verified


  def check_password(self, password, salt):
    ''' Checks the User's password using the saved salted and hashed password'''
    return safe_str_cmp(self.password, get_password_hash(password + salt))
