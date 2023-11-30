from enum import Enum



class JobStatus:
  '''
    The set of possible values for the status of a job.

    The normal life cycle of a job will put it through the following chain:
      `CREATED` -> `SUBMITTED` -> `RUNNING` -> (`ERROR` or `COMPLETE`)

    The status values are ordered, and can be compared using `is_earlier_than`. The order follows the above chain.
    Note that `COMPLETE` is considered "greater than" `ERROR` for this purpose.

    The status values have the following meanings:
      - CREATED:   The job has been parsed, a record object has been created storing its metadata, and any relevant input files have been uploaded to the cloud
      - SUBMITTED: The job has been scheduled in the appropriate queue
      - RUNNING:   An execution has been created for the job and is running in the cloud
      - COMPLETE:  The job execution finished successfully, and output any relevant files in the cloud
      - ERROR:     The job execution failed, and may have output any relevant files / logs in the cloud
  '''

  # Basic JobStatus values
  CREATED   = "CREATED"
  ERROR     = "ERROR"
  RUNNING   = "RUNNING"
  COMPLETE  = "COMPLETE"
  SUBMITTED = "SUBMITTED"

  # Meaningful sets of JobStatus values
  ALL       = { CREATED, SUBMITTED, RUNNING, ERROR, COMPLETE }
  FINISHED  = { COMPLETE, ERROR }
  NOT_ERR   = ALL - { ERROR }

  # Check whether a variable is a valid JobStatus
  @staticmethod
  def is_valid(value):
    return value in {
      JobStatus.CREATED,
      JobStatus.ERROR,
      JobStatus.RUNNING,
      JobStatus.COMPLETE,
      JobStatus.SUBMITTED,
    }

  @staticmethod
  def is_earlier_than(a, b):
    '''
      Compare two JobStatus values based on where they are in a job's life cycle.

      Order:
        `CREATED` < `SUBMITTED` < `RUNNING` < `ERROR` < `COMPLETE`
    '''

    # Validate arguments
    if not (JobStatus.is_valid(a) and JobStatus.is_valid(b)):
      raise ValueError(f'Cannot compare invalid JobStatus values "{a}" and "{b}"')

    # Define the absolute order
    order = [
      JobStatus.CREATED,
      JobStatus.SUBMITTED,
      JobStatus.RUNNING,
      JobStatus.ERROR,
      JobStatus.COMPLETE,
    ]

    return order.index(a) < order.index(b)



class PublishStatus(Enum):
  '''
    States for an object that can be published on the site by public users or by CaeNDR admins (on behalf of the CaeNDR project).
  '''

  # Private status values for public users
  UPLOADED  = 'UPLOADED'   # Owner has not yet submitted for review
  SUBMITTED = 'SUBMITTED'  # Owner has submitted for review
  REVISING  = 'REVISING'   # Admin has asked for revisions
  REJECTED  = 'REJECTED'   # Admin has rejected outright

  # Private status value for CaeNDR admins
  HIDDEN    = 'HIDDEN'     # Item is submitted by CaeNDR admin, but is kept private

  # Public status value for public users
  ACCEPTED  = 'ACCEPTED'   # Admin has approved, item is public

  # Public status value for CaeNDR admins
  CANONICAL = 'CANONICAL'  # Item is submitted by CaeNDR admin, bypassing approval process


  @property
  def is_public(self):
    return self in { PublishStatus.ACCEPTED, PublishStatus.CANONICAL }

  @property
  def is_private(self):
    return not self.is_public

  @property
  def from_caendr(self):
    return self in { PublishStatus.HIDDEN, PublishStatus.CANONICAL }

  @property
  def from_public(self):
    return not self.from_caendr
