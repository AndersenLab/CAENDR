import os
import csv
import json

from caendr.services.logger import logger

from caendr.models.datastore import Container, IndelPrimer, HeritabilityReport, NemascanMapping, SPECIES_LIST
from caendr.models.error     import CachedDataError, DuplicateDataError, DataFormatError
from caendr.models.task      import IndelPrimerTask, HeritabilityTask, NemaScanTask

from caendr.services.cloud.storage import upload_blob_from_string, upload_blob_from_file

from caendr.utils.data import convert_data_table_to_tsv, get_object_hash
from caendr.utils.file import get_file_hash



INDEL_PRIMER_CONTAINER_NAME = os.environ.get('INDEL_PRIMER_CONTAINER_NAME')
HERITABILITY_CONTAINER_NAME = os.environ.get('HERITABILITY_CONTAINER_NAME')
NEMASCAN_NXF_CONTAINER_NAME = os.environ.get('NEMASCAN_NXF_CONTAINER_NAME')



def submit_job(entity_class, user, data, container_version=None, no_cache=False):
  '''
      Submit a job with the given data for the given user.
      Checks for cached submissions and cached results as defined in _Entity_Class.

      Arguments:
        entity_class: The subclass of Entity associated with this job.
        user: The user submitting the job.
        data: The user's input data. Will be run through SubmissionManager.parse_data() and used to populate
              the datastore Entity.
        no_cache (bool): Whether to skip checking cache (True) or not. Defaults to False.

      Returns:
        A newly-created Entity representing this job submission.  Type will be determined by entity_class.

      Raises:
        DuplicateDataError:
          If this user has already submitted this data. Contains existing Entity as first argument.
        CachedDataError:
          If another user has already submitted this job. Contains new Entity representing this user's
          submission, linked to the cached results.
    '''

  # Define mapping between Entity classes and Submission Manager classes
  entity_manager_mapping = {
    c._Entity_Class.kind: c
      for c in [
        IndelPrimerSubmissionManager,
        HeritabilitySubmissionManager,
        MappingSubmissionManager,
      ]
  }

  # If desired Entity class can't be found in mapping, raise error
  if getattr(entity_class, 'kind') not in entity_manager_mapping:
    raise ValueError(f'No submission manager defined for class "{entity_class.__name__}"')

  # Forward args to proper SubmissionManager subclass
  return entity_manager_mapping[entity_class.kind].submit(user, data, container_version=container_version, no_cache=no_cache)



class SubmissionManager():

  # The associated Entity and Task subclasses
  # Should be overridden in SubmissionManager subclasses
  _Entity_Class = None
  _Task_Class   = None


  @classmethod
  def create_entity(cls, *args, **kwargs):
    '''
      Create an Entity of the appropriate subclass type.
    '''
    return cls._Entity_Class(*args, **kwargs)

  @classmethod
  def create_task(cls, *args, **kwargs):
    '''
      Create a Task of the appropriate subclass type.
    '''
    return cls._Task_Class(*args, **kwargs)

  # Forward cache check to Entity class
  @classmethod
  def check_cached_submission(cls, *args, **kwargs):
    '''
      Check whether this user has submitted this job before.
    '''
    return cls._Entity_Class.check_cached_submission(*args, **kwargs)


  @classmethod
  def container_name(cls):
    '''
      Retrieve the container name to use to run this job.
      Should be overridden by subclasses.
    '''
    if cls is SubmissionManager:
      raise TypeError(f'Cannot run method "container_name" on {cls.__name__}. Please run with subclass instead.')
    elif issubclass(cls, SubmissionManager):
      raise NotImplementedError(f'Class "{cls.__name__}" should override the definition of "container_name".')

  @classmethod
  def upload_data_file(cls, entity, data_file):
    '''
      Upload the given data file at the location specified by the given Entity.
      Should be overridden by subclasses.
    '''
    if cls is SubmissionManager:
      raise TypeError(f'Cannot run method "upload_data_file" on {cls.__name__}. Please run with subclass instead.')
    elif issubclass(cls, SubmissionManager):
      raise NotImplementedError(f'Class "{cls.__name__}" should override the definition of "upload_data_file".')

  @classmethod
  def parse_data(cls, data):
    '''
      Parse a data object representing the raw form input into a set of props for the Entity subclass.
      Should be overridden by subclasses.
    '''
    if cls is SubmissionManager:
      raise TypeError(f'Cannot run method "parse_data" on {cls.__name__}. Please run with subclass instead.')
    elif issubclass(cls, SubmissionManager):
      raise NotImplementedError(f'Class "{cls.__name__}" should override the definition of "parse_data".')


  @classmethod
  def submit(cls, user, data, container_version=None, no_cache=False):
    '''
      Submit a job with the given data for the given user.
      Checks for cached submissions and cached results as defined in _Entity_Class.

      Arguments:
        user: The user submitting the job.
        data: The user's input data. Will be run through SubmissionManager.parse_data() and used to populate
              the datastore Entity.
        container_version:
          The version of the tool container to use. If None is provided, uses the most recent version.
          Defaults to None.
        no_cache (bool): Whether to skip checking cache (True) or not. Defaults to False.

      Returns:
        A newly-created Entity representing this job. The subclass of this Entity will depend on the subclass of
        SubmissionManager used to submit.

      Raises:
        DuplicateDataError:
          If this user has already submitted this data. Contains existing Entity as first argument.
        CachedDataError:
          If another user has already submitted this job. Contains new Entity representing this user's
          submission, linked to the cached results.
    '''

    # Ensure this is being run on a subclass of SubmissionManager, not SubmissionManager itself
    if cls is SubmissionManager:
      raise TypeError(f'Cannot run method "submit" on {cls.__name__}. Please run with subclass instead.')

    logger.debug(f'Submitting new {cls._Entity_Class.__name__} for user "{user.name}".')

    # Load container version info
    container = Container.get(cls.container_name(), version = container_version)
    logger.debug(f"Creating {cls._Entity_Class.__name__} with Container {container.uri()}")
    if container_version is not None:
      logger.warn(f'Container version {container_version} was specified manually - this may not be the most recent version.')

    # Parse the input data
    data_file, data_hash, data_vals = cls.parse_data(data)

    # Check if user has already submitted this job, and "return" it in a duplicate data error if so
    if not no_cache:
      cached_entity = cls.check_cached_submission(data_hash, user.name, container)
      if cached_entity:
        raise DuplicateDataError(cached_entity)

    # Create entity to represent this job and set data fields
    entity = cls.create_entity(**data_vals)
    entity.data_hash = data_hash

    # Set entity's container & user fields
    entity.set_container(container)
    entity.set_user(user)

    # Upload the new entity to datastore
    entity['status'] = 'SUBMITTED' # TODO: Is this an OK initial value? What if there's an error before the task is submitted?
    entity.save()

    # Check if there is already a cached result, and skip creating a job if so
    if not no_cache:
      cached_result = entity.check_cached_result()
      if cached_result:

        # If cache check returned a status, use it; otherwise, default to "COMPLETE"
        entity['status'] = cached_result if isinstance(cached_result, str) else 'COMPLETE'
        entity.save()

        # Save the entity and "return" in a cached data error
        raise CachedDataError(entity)

    # Upload source data file to data store
    cls.upload_data_file(entity, data_file)

    # Schedule job in task queue
    task   = cls.create_task(entity)
    result = task.submit()

    # Update entity status to reflect whether task was submitted successfully
    entity['status'] = 'SUBMITTED' if result else 'ERROR'
    entity.save()

    # Return resulting Indel Primer entity
    return entity



class IndelPrimerSubmissionManager(SubmissionManager):

  _Entity_Class = IndelPrimer
  _Task_Class   = IndelPrimerTask

  @classmethod
  def container_name(cls):
    return INDEL_PRIMER_CONTAINER_NAME

  @classmethod
  def upload_data_file(cls, entity, data_file):
    bucket = entity.get_bucket_name()
    blob   = entity.get_data_blob_path()
    upload_blob_from_string(bucket, data_file, blob)

  @classmethod
  def parse_data(cls, data):
    data_file = json.dumps(data)
    data_hash = get_object_hash(data, length=32)

    # TODO: Pull this value from somewhere
    release = SPECIES_LIST[ data['species'] ].indel_primer_ver

    # Add release information to data object
    data.update({
      'release':         release,
      'sv_bed_filename': IndelPrimer.get_source_filename(data['species'], release) + '.bed.gz',
      'sv_vcf_filename': IndelPrimer.get_source_filename(data['species'], release) + '.vcf.gz',
    })

    return data_file, data_hash, data



class HeritabilitySubmissionManager(SubmissionManager):

  _Entity_Class = HeritabilityReport
  _Task_Class   = HeritabilityTask

  @classmethod
  def container_name(cls):
    return HERITABILITY_CONTAINER_NAME

  @classmethod
  def upload_data_file(cls, entity, data_file):
    bucket = entity.get_bucket_name()
    blob   = entity.get_data_blob_path()
    upload_blob_from_string(bucket, data_file, blob)

  @classmethod
  def parse_data(cls, data):

    # Pull table_data out of the data object
    # Note that we don't change the underlying object itself, as this would
    # affect the data dict in calling functions
    table_data = data['table_data']
    data = { k: v for k, v in data.items() if k != 'table_data' }

    # Extract table data
    table_data = json.loads(table_data)
    table_data = [x for x in table_data[1:] if x[0] is not None]

    # Create TSV file for upload
    columns = ["AssayNumber", "Strain", "TraitName", "Replicate", "Value"]
    data_file = convert_data_table_to_tsv(table_data, columns)

    # Compute hash from table data
    data_hash = get_object_hash(table_data, length=32)

    # Extract trait from table data
    data['trait'] = table_data[0][2]

    return data_file, data_hash, data



class MappingSubmissionManager(SubmissionManager):

  _Entity_Class = NemascanMapping
  _Task_Class   = NemaScanTask

  @classmethod
  def container_name(cls):
    return NEMASCAN_NXF_CONTAINER_NAME

  @classmethod
  def upload_data_file(cls, entity, data_file):
    bucket = entity.get_bucket_name()
    blob   = entity.get_data_blob_path()
    upload_blob_from_file(bucket, data_file, blob)

  @classmethod
  def parse_data(cls, data):

    # Extract local filepath from the data object
    # Note that we don't change the underlying object itself, as this would
    # affect the data dict in calling functions
    local_path = data['filepath']
    data = { k: v for k, v in data.items() if k != 'filepath' }

    # Validate file upload
    # TODO: Further validation. Parse file into object, validating along the way?
    #       This might also allow better data hashing? Since e.g. blank spaces in the file would be ignored.
    logger.debug(f'Validating Nemascan Mapping data format: {local_path}')

    # Read first line from tsv
    with open(local_path, 'r') as f:
      csv_reader = csv.reader(f, delimiter='\t')
      try:
        csv_headings = next(csv_reader)
      except StopIteration:
        raise DataFormatError('Empty file.')

    # Check first line for column headers (strain, {TRAIT})
    if csv_headings[0].lower() != 'strain':
      raise DataFormatError('First column should be "strain".')
    if len(csv_headings) != 2:
      raise DataFormatError('File should have exactly two columns.')
    if len(csv_headings[1]) == 0:
      raise DataFormatError('Second column header should be trait name.')

    # Compute data hash using entire file
    data_hash = get_file_hash(local_path, length=32)

    # Add prop(s) from file to data object
    data['trait'] = csv_headings[1].lower()

    return local_path, data_hash, data
