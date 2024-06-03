from caendr.models.datastore import Entity
from caendr.models.error     import PublishStatusError
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



  #
  # State change methods
  #


  def change_publish_state(self, to_state: PublishStatus):
    '''
      Change the publish state of this entity to `to_state`.

      Validates that the state transition from the entity's current state to the given one is allowed,
      based on the rules defined in `PublishStatus`.
    '''

    # Check that the current state can transition to the new one, if applicable
    # This function also handles type-checking for to_state
    if not PublishStatus.is_valid_transition(self['publish_status'], to_state):
      raise PublishStatusError(self['publish_status'], to_state)

    # Set the new state
    self['publish_status'] = to_state


  def publish_submit(self):
    '''
      Submit the current entity for review.
      Changes the state to `SUBMITTED` and turns over to the site admins, if that transition is valid.
    '''
    self.change_publish_state(PublishStatus.SUBMITTED)


  def publish_accept(self):
    '''
      Accept the current entity after review.
      Changes the state to `ACCEPTED`, making it public, if that transition is valid.
    '''
    self.change_publish_state(PublishStatus.ACCEPTED)


  def publish_reject(self):
    '''
      Reject the current entity after review.
      Changes the state back to `SUBMITTED` to return it to the owner, if that transition is valid.
    '''
    self.change_publish_state(PublishStatus.SUBMITTED)

  def publish_retract(self):
    '''
      Retract the current entity, after it has been made public.
      Changes the state to `RETRACTED`, if that transition is valid.
    '''
    self.change_publish_state(PublishStatus.RETRACTED)
