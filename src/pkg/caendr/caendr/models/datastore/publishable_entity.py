from caendr.models.datastore import Entity
from caendr.models.status    import PublishStatus



# TODO: Should this subclass UserOwnedEntity?
class PublishableEntity(Entity):
  '''
    An entity that can be submitted & published by public users.

    Tracks a property `publish_status` of Enum type `PublishStatus`.
    For the semantics of this value, see the `PublishStatus` class definition.
  '''

  #
  # Properties
  #

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'publish_status',
    }


  #
  # Publish status property
  #

  @property
  def publish_status(self):
    return self._get_enum_prop(PublishStatus, 'publish_status', None)

  @publish_status.setter
  def publish_status(self, val):
    return self._set_enum_prop(PublishStatus, 'publish_status', val)


  @property
  def is_public(self):
    return self.publish_status.is_public

  @property
  def is_private(self):
    return self.publish_status.is_private

  @property
  def from_caendr(self):
    return self.publish_status.from_caendr

  @property
  def from_public(self):
    return self.publish_status.from_public
