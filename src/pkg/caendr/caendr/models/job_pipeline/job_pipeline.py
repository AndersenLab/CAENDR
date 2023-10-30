# Built-in libraries
from abc    import ABC, abstractmethod
from typing import Type, Any, Dict, List

from google.cloud.storage.blob import Blob

# Logging
from caendr.services.logger import logger

# CaeNDR package
from caendr.models.datastore  import User, Container
from caendr.models.error      import (
  NotFoundError,
  CachedDataError,
  DuplicateDataError,
  DataFormatError,
  EmptyReportResultsError,
  UnschedulableJobTypeError,
  JobAlreadyScheduledError
)
from caendr.models.report     import Report
from caendr.models.run        import Runner
from caendr.models.status     import JobStatus
from caendr.models.task       import Task



class JobPipeline(ABC):
  '''
    Template class for pipeline jobs.

    Serves as a manager for the following classes:
      - Report: Controls storage for a job (metadata + input/output data)
      - Task:   Controls scheduling of a job (submission to queue)
      - Runner: Controls running of a job
  '''

  # Custom class that defines storage
  # See abstract base class Report for the interface this class must define
  _Report_Class : Type[Report] = None

  # Defines submission of a job from the site to the appropriate queue
  # If left undefined, scheduling of this job type is considered impossible
  # See abstract base class Task for the interface this class must define
  _Task_Class   : Type[Task]   = None

  # Defines running a job container in the cloud service provider
  # See abstract base class Runner for the interface this class must define
  _Runner_Class : Type[Runner] = None

  # Associated data classes
  _Container_Class = Container
  _User_Class      = User

  _Container_Name = None


  #
  # Initialization
  #

  def __init__(self, report: Report):
    '''
      JobPipeline objects should NOT be directly instantiated. Instead, new objects should be created using one of the following class methods:
        - create: Create a new Job, storing it in the cloud
        - lookup: Retrieve an existing Job from the cloud
    '''

    # Confirm the report kind and JobPipeline kind match
    if report.kind != self.kind:
      raise ValueError(f'Report with incorrect kind "{report.kind}" provided to JobPipeline class "{self.kind}".')

    # Save the report to this object
    self._report = report


  @classmethod
  def lookup(cls, job_id):
    '''
      Lookup an existing job by ID.

      Arguments:
        job_id: The unique ID of the job.

      Returns:
        A newly-created JobPipeline representing the given job.

      Raises:
        ValueError: No job with this ID could be found.
    '''
    return cls( cls.lookup_report(job_id) )


  @classmethod
  def create(cls, user, data, container_version=None, no_cache=False, valid_file_extensions=None):
    '''
      Create a job with the given data for the given user.
      Checks for cached submissions and cached results as defined in _Report_Class.

      Arguments:
        user: The user submitting the job.
        data: The user's input data. Will be run through subclass .parse() and used to populate the report.
        container_version:
          The version of the tool container to use. If None is provided, uses the most recent version.
          Defaults to None.
        no_cache (bool): Whether to skip checking cache (True) or not. Defaults to False.

      Returns:
        A newly-created JobPipeline representing this job.

      Raises:
        DuplicateDataError:
          If this user has already submitted this data. Contains existing Entity as first argument.
        CachedDataError:
          If another user has already submitted this job. Contains new Entity representing this user's
          submission, linked to the cached results.
    '''

    # Log the start of the creation process
    logger.debug(f'Creating new {cls.__name__} job for user "{user.name}".')

    # Load container version info
    container = Container.get(cls._Container_Name, version = container_version)
    logger.debug(f"Creating {cls.__name__} with Container {container.uri()}")
    if container_version is not None:
      logger.warn(f'Container version {container_version} was specified manually - this may not be the most recent version.')

    # Parse the input data
    parsed_data = cls.parse(data, valid_file_extensions=valid_file_extensions)

    # Check if user has already submitted this job, and "return" it in a duplicate data error if so
    if parsed_data.get('hash') and not no_cache:
      cached_report = cls.check_cached_submission(parsed_data['hash'], user.name, container, status=JobStatus.NOT_ERR)
      if cached_report:
        raise DuplicateDataError(cls.lookup(cached_report.id))

    # Create a new report to represent this job, and set data fields based on the parsed input
    report = cls.create_report(**parsed_data['props'])

    # Set the data hash for the new report based on the parsed input, if applicable
    if parsed_data.get('hash'):
      report.data_hash = parsed_data['hash']

    # Set the new report's container & user
    report.set_container(container)
    report.set_user(user)

    # Initialize the report status
    report.set_status(JobStatus.CREATED)

    # Upload the new report to the cloud storage provider
    report.save()

    # Wrap the new report in a new JobPipeline object, upload the input data file(s) to data store, and return the new job
    job = cls(report=report)
    job.report.upload( *parsed_data.get('files', []) )
    return job



  #
  # Creating managed classes
  #

  @classmethod
  def create_report(cls, *args, **kwargs) -> Report:
    return cls._Report_Class.create(*args, **kwargs)

  @classmethod
  def lookup_report(cls, *args, **kwargs) -> Report:
    return cls._Report_Class.lookup(*args, **kwargs)

  @classmethod
  def create_task(cls, *args, **kwargs) -> Task:
    return cls._Task_Class(*args, **kwargs)
  
  @classmethod
  def create_runner(cls, *args, **kwargs) -> Runner:
    return cls._Runner_Class(*args, **kwargs)



  #
  # Basic Properties
  # Mostly convenience functions for lookups, which prevent setting values
  #

  @property
  def report(self) -> Report:
    '''
      Managed Report object.
    '''
    return self._report

  @property
  def runner(self) -> Runner:
    '''
      Managed Runner object. Only computed as needed.
    '''
    if getattr(self, '_runner', None) is None:
      self._runner = self.create_runner( self.report.kind, self.report.get_data_id(as_str=True) )
    return self._runner


  @property
  def kind(self):
    '''
      Get the unique kind specified by the associated Report class.
    '''
    return self._Report_Class.get_kind()

  @classmethod
  def get_kind(cls):
    '''
      Class-level method for getting kind.
    '''
    return cls._Report_Class.get_kind()

  @property
  def queue(self):
    '''
      Get the queue name specified by the associated Task class.
    '''
    return self._Task_Class.queue

  @classmethod
  def get_queue(cls):
    '''
      Class-level method for getting queue name.
    '''
    return cls._Task_Class.queue



  #
  # Container Image Properties
  # Lookup / construct information about the container used to run this job
  #

  @property
  def container_uri(self) -> str:
    '''
      The URI for this job's container image. Used to look up & create the container.
    '''
    return self.report.get_container().uri()

  @property
  def container_version(self) -> str:
    '''
      The version of this job's container image.
    '''
    return self.report.get_container()['tag']



  #
  # Parsing
  # Convert user input into a report
  #

  @classmethod
  @abstractmethod
  def parse(cls, data: dict, valid_file_extensions = None) -> dict:
    '''
      Parse user input into properties to be stored in the report object (in the cloud).
      If any validation is required, it should be performed here.

      By default, uses the data dictionary as the set of props with no modification.

      Args:
        - data (dict): The input data.

      Returns:
        A dictionary with the following fields:
          - props (dict): A dict of fields to save to the Report object.
          - hash (str):   A unique hash for this input data. Optional.
          - files (list): A list of files to upload to cloud storage. These will be handled by the `upload` method. Optional.

      Raises:
        - PreflightCheckError: One or more required files were not found in cloud storage.
        - DataFormatError:     Validation of the input failed.
    '''
    return { 'props': data }



  #
  # Caching
  #

  @classmethod
  def check_cached_submission(cls, *args, **kwargs):
    '''
      Check whether this user has submitted this job before.
    '''
    # Forward cache check to Report class
    return cls._Report_Class.check_cached_submission(*args, **kwargs)



  #
  # File Storage
  # Fetching & optionally parsing files from the storage provider
  #

  def fetch(self, raw: bool = False):
    '''
      Fetch all data for this job from the file storage provider, using the managed `Report` object.
      Equivalent to calling `fetch_input` and `fetch_output` with this object.

      Arguments:
        - `raw` (`bool`): If `true`, return the raw blob(s); otherwise, parse into a Python object. Default `false`.

      Returns:
        - `input` (format specified by `raw`)
        - `output` (format specified by `raw`)

      Raises:
        - EmptyReportDataError:    An input data file exists, but is empty (i.e. invalid)
        - EmptyReportResultsError: An output data file exists, but is empty (i.e. invalid)
    '''
    return self.fetch_input(raw=raw), self.fetch_output(raw=raw)


  def fetch_input(self, raw: bool = False):
    '''
      Fetch the input data for this job from the file storage provider, using the managed `Report` object.

      If data file does not (yet) exist, returns `None`.
      If data file does exist but is empty, should raise `EmptyReportDataError`.

      Arguments:
        - `raw` (`bool`): If `true`, return the raw blob(s); otherwise, parse into a Python object. Default `false`.

      Raises:
        - EmptyReportDataError: An input data file exists, but is empty (i.e. invalid)
    '''

    # Use the Report object to fetch the raw input blob
    blob = self.report.fetch_input()

    # If blob is desired or if no blob exists, return here
    if raw or blob is None:
      return blob

    # Delegate parsing to the subclass
    # TODO: If this raises an EmptyReportDataError, should we mark the job status as error?
    return self._parse_input(blob)


  def fetch_output(self, raw: bool = False):
    '''
      Fetch the output data for this job from the file storage provider, using the managed `Report` object.

      If data file does not (yet) exist, returns `None`.
      If data file does exist but is empty, should raise `EmptyReportResultsError`.

      Arguments:
        - `raw` (`bool`): If `true`, return the raw blob(s); otherwise, parse into a Python object. Default `false`.

      Raises:
        - EmptyReportResultsError: An output data file exists, but is empty (i.e. invalid)
    '''

    # Use the Report object to fetch the raw output blob
    blob = self.report.fetch_output()

    # If blob is desired or if no blob exists, return here
    if raw or blob is None:
      return blob

    # Delegate parsing to the subclass
    try:
      result = self._parse_output(blob)

    # If result file is invalid, mark the report status as error
    except EmptyReportResultsError:
      self.report.set_status( JobStatus.ERROR )
      self.report.save()
      raise

    # If result exists and report status hasn't been updated yet, update it
    if result is not None:
      if self.report.get_status() != JobStatus.ERROR:
        self.report.set_status( JobStatus.COMPLETE )
        self.report.save()

    # Return the result object
    return result


  @abstractmethod
  def _parse_input(self, blob: Blob):
    '''
      Parse the input blob uploaded to the job pipeline into a Python object.
    '''
    pass


  @abstractmethod
  def _parse_output(self, blob: Blob):
    '''
      Parse the result blob output by the job pipeline into a Python object.
    '''
    pass



  #
  # Scheduling
  #

  @property
  def is_schedulable(self) -> bool:
    '''
      Whether jobs of this type can be scheduled.
      Checks whether this subclass defines a Task class.
    '''
    return self._Task_Class is not None


  def schedule(self, no_cache=False, force=False) -> JobStatus:
    '''
      Submit a job to the appropriate queue, using the assigned Task class.

      Returns:
        The new JobStatus of this job, with one of the following values:
          - SUBMITTED: The task was successfully submitted to the appropriate queue
          - ERROR: There was a problem submitting the task to the appropriate queue

      Raises:
        - UnschedulableJobTypeError:
            This job's subclass does not assign a Task class, i.e. scheduling is impossible.
        - JobAlreadyScheduledError:
            This specific job has already been scheduled. Will not re-schedule the job.
            This behavior can be disabled by setting `force` to True. Note that this may re-schedule an existing job.
        - CachedDataError:
            Results have already been computed for this job's input data. Will not re-schedule the job.
            This behavior can be disabled by setting `no_cache` to True. Note that this may re-schedule a job.
    '''

    # If Task class is not defined, scheduling is not supported for this job type
    if not self.is_schedulable:
      raise UnschedulableJobTypeError()

    # Check whether this specific job has already been scheduled
    # If force is True, this check will not be run
    if not force and self.report.get_status() != JobStatus.CREATED:
      raise JobAlreadyScheduledError()
    
    # If using cache, check whether this job already has results and short-circuit the computation if so
    # If no_cache is True, this check will not be run
    if not no_cache and self._check_cached_result():
      raise CachedDataError()

    # Schedule job in task queue
    task   = self.create_task(self.report)
    result = task.submit()

    # Update entity status to reflect whether task was submitted successfully
    self.report.set_status( JobStatus.SUBMITTED if result else JobStatus.ERROR )
    self.report.save()

    # Return the status
    # TODO: Raise an error if submission fails?
    return self.report.get_status()



  #
  # Running
  #

  @property
  def data_id(self):
    '''
      The data ID for this job's report, as specified in the associated `Report` subclass.
    '''
    return self.report.get_data_id()


  def run(self, **kwargs):
    '''
      Run this job using the specified Runner class.
    '''

    # Check if this report is already associated with an operation
    if self.report['operation_name'] is not None:
      logger.warn(f'Report { self.report.id } (data ID { self.data_id }) is already associated with operation { self.report["operation_name"] }. Running again...')

    # Forward run call to Runner object
    exec_id = self.runner.run( self.construct_command(), self.construct_environment(), self.container_uri, self.construct_run_params(), **kwargs )

    # Save the full execution name to the report object, so it can be looked up later
    self.report['operation_name'] = self.runner.get_full_execution_name(exec_id)
    self.report.save()

    # Return the execution ID
    return exec_id


  @abstractmethod
  def construct_command(self) -> List[str]:
    '''
      Define the initial command to use to start running the job.
      Result should be a list of individual terms to be used in the command line.
    '''
    return []


  @abstractmethod
  def construct_environment(self) -> Dict[str, Any]:
    '''
      Define the environment variables to make available when running the job.
      Result should map variable names to values.
    '''
    return {
      **self.runner.default_environment(),
    }


  @abstractmethod
  def construct_run_params(self) -> Dict[str, Any]:
    '''
      Define the run parameters to use when constructing the machine to run the job.
      Result should map parameter names to values.
    '''
    return {
      **self.runner.default_run_params(),
    }



  #
  # Status
  #

  def _check_cached_result(self):
    cached_result = self.report.check_cached_result()

    # If cache check returned a status, use it; otherwise, default to "COMPLETE"
    if cached_result:
      self.report.set_status( cached_result if isinstance(cached_result, str) else JobStatus.COMPLETE )
      self.report.save()

    return cached_result


# def has_results
  def is_finished(self) -> bool:
    '''
      Check for results.

      Returns:
        status (JobStatus): The current status of the job
        result: The results if the job is complete, or None if no result exists.
    '''

    cached_result = self.check_cached_result()
    if cached_result:

      # If cache check returned a status, use it; otherwise, default to "COMPLETE"
      self.report.set_status( cached_result if isinstance(cached_result, str) else JobStatus.COMPLETE )
      self.report.save()

    return self.report.get_status() in JobStatus.FINISHED
