from abc import ABC, abstractmethod

from caendr.models.status import JobStatus



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
  _kind: str

  @property
  def kind(self) -> str:
    return self._kind


  # String uniquely identifying the job itself
  # Runners with the same data_id are considered to be running the same "computation"
  # Individual runs of this data are available as executions, meaning the execution ID is required
  # to distinguish between multiple executions with the same data_id
  _data_id: str

  @property
  def data_id(self):
    return self._data_id


  # Storage class to record metadata about an execution
  _Record_Class = None


  def __init__(self, kind: str, data_id: str):
    '''
      Create a new Runner object.

      Arguments:
        - kind (str):
            Unique identifier for the job type.
        - data_id (str):
            Unique identifier for the job data.
            Runners with the same data ID are considered to be running the same "computation".
    '''

    # Set the kind and data ID
    self._kind    = kind
    self._data_id = data_id


  @abstractmethod
  def check_status(self, execution_id: str) -> JobStatus:
    '''
      Get the status of a specific execution of this job.
    '''
    pass


  @abstractmethod
  def run(self, command: list, env: dict, container_uri: str, params: dict, run_if_exists: bool = False) -> str:
    '''
      Start a job to compute the given report.

      Args:
        - report: The report to read data from to start the new job. The report should have the same kind and data ID as this runner.
        - run_if_exists (bool, optional): If True, will still run the job even if the specified job container exists. Default False.

      Returns:
        An identifier for the execution that was created.  Will be unique within this Runner object.
    '''
    pass


  def get_full_execution_name(self, execution_id: str) -> str:
    '''
      Transform execution ID to a full name for storage.
      By default, returns the execution ID as-is. This behavior may be overwritten in subclasses.

      TODO: Arguably, we should store the execution ID as-is in the report, and look it up later.
            This would involve changing the 'operation_name' field in the JobEntity class.
    '''
    return execution_id



  @classmethod
  @abstractmethod
  def default_environment(cls):
    return {}

  @classmethod
  @abstractmethod
  def default_run_params(cls):
    return {}
