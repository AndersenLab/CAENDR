from caendr.models.datastore import Entity


class UserToken(Entity):
  kind = 'user_token'

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'username',
      'revoked',
    }

  def revoke(self, *args, **kwargs):
    '''
      Sets the UserToken revoked to True and saves.
    '''
    self['revoked'] = True
    self.save()
