from caendr.models.datastore import Entity
from caendr.models.status    import JobStatus



class StatusEntity(Entity):
  '''
    Subclass of Entity with a JobStatus field.

    Should never be instantiated directly -- in fact, this is prevented in this class's __new__ function.
    Instead, specific job types should be subclasses of this class.
  '''

  #
  # Initialization
  #

  def __new__(cls, *args, **kwargs):
    if cls is StatusEntity:
      raise TypeError(f"Class '{cls.__name__}' should never be instantiated directly -- subclasses should be used instead.")
    return super(StatusEntity, cls).__new__(cls)


  #
  # Properties List
  #

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'status',
    }


  #
  # Status Property
  #

  @property
  def status(self):
    return self._get_enum_prop(JobStatus, 'status')

  @status.setter
  def status(self, val):
    return self._set_enum_prop(JobStatus, 'status', val)


  #
  # Alternate setter/getter
  #

  def get_status(self) -> JobStatus:
    return self['status']
  
  def set_status(self, status: JobStatus):
    self['status'] = status


  #
  # Status Conditions
  # Convenience methods for checking against meaningful sets of status values
  #

  def is_finished(self) -> bool:
    return self['status'] in JobStatus.FINISHED

  def is_not_err(self) -> bool:
    return self['status'] in JobStatus.NOT_ERR
