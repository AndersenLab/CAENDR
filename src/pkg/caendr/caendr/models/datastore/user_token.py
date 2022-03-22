from caendr.models.datastore import Entity


class UserToken(Entity):
  kind = 'user_token'
  
  def __init__(self, *args, **kwargs):
    super(UserToken, self).__init__(*args, **kwargs)
    self.set_properties(**kwargs)


  def set_properties(self, **kwargs):
    ''' Sets allowed properties for the UserToken instance '''
    if 'username' in kwargs:
      self.username = kwargs.get('username')
    if 'revoked' in kwargs:
      self.revoked = kwargs.get('revoked')


  def save(self, *args, **kwargs):
    ''' Saves the UserToken entity to the datastore'''
    super(UserToken, self).save(*args, **kwargs)

  def revoke(self, *args, **kwargs):
    ''' Sets the UserToken revoked to True and saves'''
    self.set_properties(revoked=True)
    self.save()

    
