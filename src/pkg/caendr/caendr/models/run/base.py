from abc import ABC, abstractmethod

from caendr.models.datastore import DataJobEntity
from caendr.models.status    import JobStatus



class Runner(ABC):
  '''
    Abstract class for running a job.

    As a general rule of thumb, Runner objects should be unique up to kind + data ID.
    For example, two jobs submitted by different users on the same data should (mostly) have equivalent GCPRunners.

    However, a single runner may represent multiple *executions* of the same job on the same data.
    In this case:
      - The `run` function should return a unique identifier for the execution that it started.
      - The `check_status` function should accept this identifier to give the status of that specific execution.
  '''

  # String identifying the type of job being run
  # Should correspond with the report kind
  @property
  @abstractmethod
  def kind(self) -> str: pass

  # String uniquely identifying the job itself
  # Runners with the same data_id are considered to be running the same "computation"
  # Individual runs of this data are available as executions, meaning the execution ID is required
  # to distinguish between multiple executions with the same data_id
  data_id: str

  # The report field to use as the data ID
  # Defaults to data hash, but may be overwritten in subclasses
  _data_id_field: str = 'data_hash'

  # Storage class to record metadata about an execution
  _Record_Class: None


  def __init__(self, data_id: str = None, report: DataJobEntity = None):
    '''
      Create a new Runner object.

      Takes one of two mutually exclusive arguments: the data ID directly, or a job report
      containing that data ID in the appropriate field.

      Arguments:
        - data_id (str):
            Unique identifier for the job data.
            Runners with the same data ID are considered to be running the same "computation".
        - report (DataJobEntity):
            Job report to initialize the runner from. Must have the same kind as the Runner subclass.
            Must contain the appropriate data ID field (defaults to "data_hash")

      Raises:
        - ValueError:
            The incorrect number of arguments was provided, or the report was invalid.
    '''

    # Arguments are mutually exclusive
    if not ((data_id is None) ^ (report is None)):
      raise ValueError('Either "data_id" should be provided, or "report" should be provided.')

    # If report provided, validate its kind and extract the data ID from it
    if report is not None:
      if report.kind != self.kind:
        raise ValueError(f'Cannot initialize runner of kind {self.kind} from report with kind {report.kind}')
      data_id = getattr(report, self._data_id_field)
      if data_id is None:
        raise ValueError(f'Cannot initialize runner of kind {self.kind} from report with no "{self._data_id_field}" field')

    # Set the data ID
    self.data_id = data_id


  @abstractmethod
  def check_status(self, execution_id: str) -> JobStatus:
    '''
      Get the status of a specific execution of this job.
    '''
    pass


  @abstractmethod
  def run(self, report: DataJobEntity, run_if_exists: bool = False) -> str:
    '''
      Start a job to compute the given report.

      Args:
        - report: The report to read data from to start the new job. The report should have the same kind and data ID as this runner.
        - run_if_exists (bool, optional): If True, will still run the job even if the specified job container exists. Default False.

      Returns:
        An identifier for the execution that was created.  Will be unique within this Runner object.
    '''
    pass


  def _validate_report(self, report: DataJobEntity):
    '''
      Validate that a given report matches this Runner's kind and data ID.
      Raises a ValueError if the report is invalid.
    '''

    # Validate kind
    if report.kind != self.kind:
      raise ValueError(f'Cannot execute runner of kind {self.kind} on report with kind {report.kind}')

    # Validate data ID
    data_id = getattr(report, self._data_id_field)
    if data_id is None:
      raise ValueError(f'Cannot execute runner of kind {self.kind} on report with no "{self._data_id_field}" field')
    if data_id != self.data_id:
      raise ValueError(f'Cannot execute runner of kind {self.kind} on report with mismatching "{self._data_id_field}" field (expected {self.data_id}, got {data_id})')


  def get_full_execution_name(self, execution_id: str) -> str:
    '''
      Transform execution ID to a full name for storage.
      By default, returns the execution ID as-is. This behavior may be overwritten in subclasses.

      TODO: Arguably, we should store the execution ID as-is in the report, and look it up later.
            This would involve changing the 'operation_name' field in the JobEntity class.
    '''
    return execution_id
