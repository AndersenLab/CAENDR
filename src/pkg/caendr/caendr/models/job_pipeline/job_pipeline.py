# Built-in libraries
from abc    import ABC, abstractmethod
from typing import Type, Any, Dict, List, Optional

from google.cloud.storage.blob import Blob

# Logging
from caendr.services.logger import logger

# CaeNDR package
from caendr.models.datastore  import User, Container
from caendr.models.error      import (
  NotFoundError,
  DuplicateDataError,
  DataFormatError,
  EmptyReportResultsError,
  UnschedulableJobTypeError,
  JobAlreadyScheduledError,
  UnrunnableJobTypeError,
)
from caendr.models.report     import Report
from caendr.models.run        import Runner, GCPRunner
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
          This user has already submitted this data. Contains JobPipeline referencing that report as first argument.
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
      cached_report = cls._find_cached_report(parsed_data['hash'], user, container, status=JobStatus.NOT_ERR)
      if cached_report is not None:
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

    # # Check if input has already been uploaded
    # # This would occur if a different user has uploaded the same data to run the same job
    # # TODO: Should we check if the two files are equal? What if there was a bug uploading it the first time?
    # if not no_cache and not job.report.check_input_exists():
    job.report.upload( *parsed_data.get('files', []) )

    # Check whether output data already exists for this data
    if not no_cache:
      job._check_existing_job_execution()

    # Return the new JobPipeline object
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
    if cls._Runner_Class is None:
      return None
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
    return self.report.get_container()['container_tag']



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
          - hash (str):   A unique hash for this input data. Will be used to check cache if provided. Optional.
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
  def _find_cached_submissions(cls, *args, **kwargs):
    '''
      Check whether this user has submitted this job before.
    '''
    # Forward cache check to Report class
    return cls._Report_Class.find_cached_submissions(*args, **kwargs)

  @classmethod
  def _find_cached_report(cls, *args, **kwargs):

    # Perform the cache check
    matches = cls._find_cached_submissions(*args, **kwargs)

    # Return first element if it exists
    return matches[0] if len(matches) else None


  def _check_existing_job_execution(self):
    '''
      Look for a job execution computing this report's data, and point the report to it if found.
    '''

    # Collect the set of Status values to search for
    # We can only attach to a COMPLETE job if the output file(s) exist, otherwise we can only attach to a job in progress
    # TODO: We should be able to copy a SUBMITTED job, since we only want to submit the data once.
    #       However, since the operation_name isn't assigned until the Task is handled, we'd just be assigning it to None here,
    #       and then it wouldn't be picked up by the status_update check.
    statuses = { JobStatus.RUNNING }
    if self.report.check_output_exists():
      statuses.add(JobStatus.COMPLETE)

    # Get cached submissions based on the container and status value
    matches = self._find_cached_submissions(
      self.report.get_data_id(), container = self.report.get_container(), status = statuses
    )

    # Filter out all matching submissions by this user
    user = self.report.get_user()
    matches = [ match for match in matches if not match.belongs_to_user(user) ]

    # Find the matching the report with the "best" status, i.e. the status furthest along in the pipeline
    # Skip any incomplete reports without an associated operation_name,
    # since we need an operation name to be visible to the API status update
    best_match = None
    for match in matches:
      if match.get_status() != JobStatus.COMPLETE and match['operation_name'] is None:
        continue
      if best_match is None or JobStatus.is_earlier_than(best_match.get_status(), match.get_status()):
        best_match = match

    # If no match was found, nothing to do - this job stays as CREATED
    if best_match is None:
      return

    # If a match was found, point this new report to the existing job (through its execution record)
    # By setting the operation_name, we make this report visible in the periodic API status check
    self.report.set_status(best_match.get_status())
    self.report['operation_name'] = best_match['operation_name']
    self.report.save()

    # Now that the operation_name has been set, run a manual check using the managed Runner object
    # This prevents race conditions like the following:
    #   - The matching report found above is queried while it's RUNNING
    #   - The associated job finishes, and all reports with the given operation_name are updated to COMPLETE
    #   - This report's operation_name is set. Because it wasn't set when the update happened, it is still marked as RUNNING
    #   - This report is never updated
    self._update_status_directly()



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
        - `raw` (`bool`):
          If `true`, return the raw input object(s) as defined by the `Report` class;
          otherwise, parse into a Python object.
          Default `false`.

      Raises:
        - EmptyReportDataError: An input data file exists, but is empty (i.e. invalid)
    '''

    # Use the Report object to fetch the raw input
    raw_input = self.report.fetch_input()

    # If raw input is desired, or if no input exists, return here
    if raw or raw_input is None:
      return raw_input

    # Delegate parsing to the subclass
    # TODO: If this raises an EmptyReportDataError, should we mark the job status as error?
    return self._parse_input(raw_input)


  def fetch_output(self, raw: bool = False):
    '''
      Fetch the output data for this job from the file storage provider, using the managed `Report` object.

      If data file does not (yet) exist, returns `None`.
      If data file does exist but is empty, should raise `EmptyReportResultsError`.

      Arguments:
        - `raw` (`bool`):
          If `true`, return the raw output object(s) as defined by the `Report` class;
          otherwise, parse into a Python object.
          Default `false`.

      Raises:
        - EmptyReportResultsError: An output data file exists, but is empty (i.e. invalid)
    '''

    # Use the Report object to fetch the raw output
    raw_output = self.report.fetch_output()

    # If blob is desired or if no blob exists, return here
    if raw or raw_output is None:
      return raw_output

    # Delegate parsing to the subclass & return the result
    try:
      return self._parse_output(raw_output)

    # If result file is invalid, mark the report status as error
    except EmptyReportResultsError:
      self.report.set_status( JobStatus.ERROR )
      self.report.save()
      raise


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


  def schedule(self, no_cache=False) -> JobStatus:
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
            A job to compute this report's data has already been scheduled. Will not re-schedule the job.
            This behavior can be disabled by setting `no_cache` to True. Note that this may re-schedule a job.
    '''

    # If Task class is not defined, scheduling is not supported for this job type
    if not self.is_schedulable:
      raise UnschedulableJobTypeError()

    # Check whether a job for this data has already been scheduled
    # If no_cache is True, this check will not be run
    # The direct status check isn't strictly necessary, since it's also run during initialization,
    # but running it here provides extra assurance that the status is correct
    if not no_cache and self.report.get_status() != JobStatus.CREATED:
      self._update_status_directly()
      raise JobAlreadyScheduledError( self.kind, self.data_id )

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

    if self.runner is None:
      raise UnrunnableJobTypeError()

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
    if self.runner is None:
      return {}
    return {
      **self.runner.default_environment(),
    }


  @abstractmethod
  def construct_run_params(self) -> Dict[str, Any]:
    '''
      Define the run parameters to use when constructing the machine to run the job.
      Result should map parameter names to values.
    '''
    if self.runner is None:
      return {}
    return {
      **self.runner.default_run_params(),
    }



  #
  # Status
  #

  def _update_status_directly(self):
    '''
      Directly check if this job is complete, using the managed Runner object.

      Running this check manually after creating the job makes sure the job status is checked *after* the operation_name is assigned,
      avoiding any race conditions where an existing job changes status before it's linked to this report.
    '''
    try:
      exec_id = self.runner.get_execution_id_from_operation_name( self.report['operation_name'] )
      self.report.set_status( self.runner.check_status( exec_id ) )
      self.report.save()
    except Exception as ex:
      logger.debug(f'Failed to manually check job execution status for report {self.report.id}, ignoring: {ex}')


  def is_finished(self) -> bool:
    '''
      Check for results.

      Returns:
        status (JobStatus): The current status of the job
        result: The results if the job is complete, or None if no result exists.
    '''
    # Check whether this report's status is FINISHED
    return self.report.get_status() in JobStatus.FINISHED


  # TODO: It would be better to rewrite this so it doesn't need to check against Runner subclasses
  def get_error(self) -> Optional[str]:
    '''
      Get the error message associated with this job, if it is in the ERROR state.
      Returns None if this job does not have an error message (i.e. if it is not in the ERROR state.)
    '''
    if self.runner is None:
      return None
    if isinstance(self.runner, GCPRunner):
      return self.runner.get_err_msg( operation_name = self.report['operation_name'] )
    raise NotImplementedError('Getting error message for non-GCP Runner.')
