from collections import defaultdict
from werkzeug.security import safe_str_cmp

from caendr.models.datastore import Entity
from caendr.services.cloud.datastore import query_ds_entities
from caendr.utils.data import get_password_hash


class User(Entity):
  kind = 'user'
  
  def __init__(self, *args, **kwargs):
    super(User, self).__init__(*args, **kwargs)
    self.set_properties(**kwargs)


  def set_properties(self, **kwargs):
    ''' Sets allowed properties for the User instance '''
    if 'username' in kwargs:
      self.username = kwargs.get('username')
    if 'full_name' in kwargs:
      self.full_name = kwargs.get('full_name')
    if 'password' and 'salt' in kwargs:
      self.set_password(kwargs.get('password'), kwargs.get('salt'))
    if 'email' in kwargs:
      self.set_email(kwargs.get('email'))
    if 'roles' in kwargs:
      self.roles = kwargs.get('roles')
    if 'last_login' in kwargs:
      self.last_login = kwargs.get('last_login')


  def save(self, *args, **kwargs):
    ''' Saves the User entity to the datastore'''
    super(User, self).save(*args, **kwargs)


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

  @classmethod
  def from_email(self, email):
    filters = [ ('email', '=', email) ]    
    results = query_ds_entities(self.kind, filters=filters)
    if len(results):
      return results[0]    
    return None